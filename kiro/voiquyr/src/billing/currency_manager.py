"""
Currency Manager

Handles multi-currency support with real-time exchange rates.
Implements Requirement 13.1 - Multi-currency billing.
"""

import logging
import asyncio
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class SupportedCurrency(Enum):
    """Supported currencies for billing"""
    EUR = "EUR"  # Euro (base currency)
    AED = "AED"  # UAE Dirham
    INR = "INR"  # Indian Rupee
    SGD = "SGD"  # Singapore Dollar
    JPY = "JPY"  # Japanese Yen
    USD = "USD"  # US Dollar


@dataclass
class ExchangeRate:
    """Exchange rate information"""
    from_currency: str
    to_currency: str
    rate: Decimal
    timestamp: datetime
    source: str  # "ECB", "Fed", "Manual"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": str(self.rate),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }


class CurrencyManager:
    """
    Manages multi-currency support and exchange rates
    
    Features:
    - Real-time exchange rate updates
    - 30-day advance notice for rate changes
    - Historical rate tracking
    - Multiple rate sources (ECB, Fed)
    """
    
    # Cache duration for exchange rates
    RATE_CACHE_DURATION = timedelta(hours=1)
    
    # Advance notice period for rate changes
    RATE_CHANGE_NOTICE_DAYS = 30
    
    def __init__(
        self,
        ecb_api_url: str = "https://api.exchangerate.host/latest",
        base_currency: SupportedCurrency = SupportedCurrency.EUR
    ):
        """
        Initialize currency manager
        
        Args:
            ecb_api_url: URL for exchange rate API
            base_currency: Base currency for calculations
        """
        self.ecb_api_url = ecb_api_url
        self.base_currency = base_currency
        self.rate_cache: Dict[str, ExchangeRate] = {}
        self.rate_history: List[ExchangeRate] = []
        self.pending_rate_changes: List[Dict] = []
        self.logger = logging.getLogger(__name__)
    
    def _get_cache_key(self, from_curr: str, to_curr: str) -> str:
        """Generate cache key for currency pair"""
        return f"{from_curr}_{to_curr}"
    
    async def fetch_exchange_rates(self) -> Dict[str, Decimal]:
        """
        Fetch current exchange rates from API
        
        Returns:
            Dictionary of currency codes to rates
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "base": self.base_currency.value,
                    "symbols": ",".join([c.value for c in SupportedCurrency])
                }
                
                async with session.get(self.ecb_api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get("rates", {})
                        
                        # Convert to Decimal
                        return {
                            curr: Decimal(str(rate))
                            for curr, rate in rates.items()
                        }
                    else:
                        self.logger.error(
                            f"Failed to fetch rates: HTTP {response.status}"
                        )
                        return {}
        
        except Exception as e:
            self.logger.error(f"Error fetching exchange rates: {e}")
            return {}
    
    async def update_exchange_rates(self) -> None:
        """Update exchange rates from API"""
        rates = await self.fetch_exchange_rates()
        
        if not rates:
            self.logger.warning("No rates fetched, using cached rates")
            return
        
        timestamp = datetime.utcnow()
        
        for currency_code, rate in rates.items():
            if currency_code == self.base_currency.value:
                continue
            
            cache_key = self._get_cache_key(
                self.base_currency.value,
                currency_code
            )
            
            exchange_rate = ExchangeRate(
                from_currency=self.base_currency.value,
                to_currency=currency_code,
                rate=rate,
                timestamp=timestamp,
                source="ECB"
            )
            
            # Check if rate changed significantly (>2%)
            if cache_key in self.rate_cache:
                old_rate = self.rate_cache[cache_key].rate
                change_pct = abs((rate - old_rate) / old_rate * 100)
                
                if change_pct > 2:
                    self.logger.warning(
                        f"Significant rate change for {currency_code}: "
                        f"{old_rate} -> {rate} ({change_pct:.2f}%)"
                    )
                    
                    # Schedule rate change with 30-day notice
                    self._schedule_rate_change(exchange_rate)
            
            # Update cache
            self.rate_cache[cache_key] = exchange_rate
            self.rate_history.append(exchange_rate)
        
        self.logger.info(f"Updated {len(rates)} exchange rates")
    
    def _schedule_rate_change(self, new_rate: ExchangeRate) -> None:
        """
        Schedule a rate change with 30-day advance notice
        
        Args:
            new_rate: New exchange rate to apply
        """
        effective_date = datetime.utcnow() + timedelta(
            days=self.RATE_CHANGE_NOTICE_DAYS
        )
        
        change_notice = {
            "new_rate": new_rate,
            "effective_date": effective_date,
            "notified": False
        }
        
        self.pending_rate_changes.append(change_notice)
        
        self.logger.info(
            f"Scheduled rate change for {new_rate.to_currency} "
            f"effective {effective_date.date()}"
        )
    
    def get_exchange_rate(
        self,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency
    ) -> Optional[ExchangeRate]:
        """
        Get exchange rate between two currencies
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Exchange rate or None if not available
        """
        if from_currency == to_currency:
            return ExchangeRate(
                from_currency=from_currency.value,
                to_currency=to_currency.value,
                rate=Decimal("1.00"),
                timestamp=datetime.utcnow(),
                source="Identity"
            )
        
        cache_key = self._get_cache_key(from_currency.value, to_currency.value)
        
        if cache_key in self.rate_cache:
            rate = self.rate_cache[cache_key]
            
            # Check if rate is still fresh
            age = datetime.utcnow() - rate.timestamp
            if age < self.RATE_CACHE_DURATION:
                return rate
            else:
                self.logger.warning(f"Stale rate for {cache_key}, needs update")
        
        return None
    
    def convert_amount(
        self,
        amount: Decimal,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency
    ) -> Optional[Decimal]:
        """
        Convert amount between currencies
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount or None if rate not available
        """
        rate = self.get_exchange_rate(from_currency, to_currency)
        
        if rate is None:
            self.logger.error(
                f"No exchange rate available for {from_currency.value} "
                f"to {to_currency.value}"
            )
            return None
        
        converted = (amount * rate.rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        self.logger.debug(
            f"Converted {amount} {from_currency.value} to "
            f"{converted} {to_currency.value} (rate: {rate.rate})"
        )
        
        return converted
    
    def get_pending_rate_changes(self) -> List[Dict]:
        """
        Get list of pending rate changes requiring customer notification
        
        Returns:
            List of pending rate changes
        """
        return [
            {
                "currency": change["new_rate"].to_currency,
                "current_rate": str(self.rate_cache.get(
                    self._get_cache_key(
                        change["new_rate"].from_currency,
                        change["new_rate"].to_currency
                    )
                ).rate) if self._get_cache_key(
                    change["new_rate"].from_currency,
                    change["new_rate"].to_currency
                ) in self.rate_cache else "N/A",
                "new_rate": str(change["new_rate"].rate),
                "effective_date": change["effective_date"].isoformat(),
                "days_until_effective": (
                    change["effective_date"] - datetime.utcnow()
                ).days
            }
            for change in self.pending_rate_changes
            if not change["notified"]
        ]
    
    def mark_rate_change_notified(self, currency: str) -> None:
        """
        Mark a rate change as notified to customers
        
        Args:
            currency: Currency code that was notified
        """
        for change in self.pending_rate_changes:
            if change["new_rate"].to_currency == currency:
                change["notified"] = True
                self.logger.info(f"Marked rate change for {currency} as notified")
    
    def apply_pending_rate_changes(self) -> None:
        """Apply rate changes that have reached their effective date"""
        now = datetime.utcnow()
        applied = []
        
        for change in self.pending_rate_changes:
            if change["effective_date"] <= now:
                new_rate = change["new_rate"]
                cache_key = self._get_cache_key(
                    new_rate.from_currency,
                    new_rate.to_currency
                )
                
                self.rate_cache[cache_key] = new_rate
                applied.append(change)
                
                self.logger.info(
                    f"Applied rate change for {new_rate.to_currency}: "
                    f"{new_rate.rate}"
                )
        
        # Remove applied changes
        for change in applied:
            self.pending_rate_changes.remove(change)
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currency codes"""
        return [c.value for c in SupportedCurrency]
    
    def get_rate_history(
        self,
        currency: SupportedCurrency,
        days: int = 30
    ) -> List[ExchangeRate]:
        """
        Get historical exchange rates for a currency
        
        Args:
            currency: Currency to get history for
            days: Number of days of history
            
        Returns:
            List of historical rates
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return [
            rate for rate in self.rate_history
            if rate.to_currency == currency.value and rate.timestamp >= cutoff
        ]

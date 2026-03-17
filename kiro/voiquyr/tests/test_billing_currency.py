import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime
import asyncio
from src.billing.currency_manager import CurrencyManager, SupportedCurrency, ExchangeRate

class TestCurrencyManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = CurrencyManager()

    @patch('aiohttp.ClientSession.get')
    async def test_fetch_exchange_rates(self, mock_get):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "rates": {
                "USD": 1.1,
                "GBP": 0.85
            }
        })
        mock_get.return_value.__aenter__.return_value = mock_response

        rates = await self.manager.fetch_exchange_rates()
        self.assertEqual(rates["USD"], Decimal("1.1"))
        self.assertEqual(rates["GBP"], Decimal("0.85"))

    def test_convert_amount(self):
        # Manually populate cache for testing
        self.manager.rate_cache["EUR_USD"] = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.10"),
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        converted = self.manager.convert_amount(
            Decimal("100.00"),
            SupportedCurrency.EUR,
            SupportedCurrency.USD
        )
        self.assertEqual(converted, Decimal("110.00"))

    def test_get_exchange_rate_identity(self):
        rate = self.manager.get_exchange_rate(SupportedCurrency.EUR, SupportedCurrency.EUR)
        self.assertEqual(rate.rate, Decimal("1.00"))

if __name__ == '__main__':
    unittest.main()

"""
Billing Service

Main billing service integrating UCPM, currency, and refund systems.
Implements Requirement 13 - Complete billing system.
"""

import logging
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

from .ucpm_calculator import UCPMCalculator, UsageRecord, ServiceType, VolumeTier
from .currency_manager import CurrencyManager, SupportedCurrency
from .refund_engine import RefundEngine, RefundReason, RefundStatus
from .stripe_service import StripeService

logger = logging.getLogger(__name__)


class PaymentMethod(Enum):
    """Supported payment methods"""
    CREDIT_CARD = "credit_card"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    INVOICE = "invoice"


@dataclass
class BillingAccount:
    """Customer billing account"""
    account_id: str
    user_id: str
    currency: SupportedCurrency
    payment_method: PaymentMethod
    volume_tier: VolumeTier
    total_minutes_used: int = 0
    current_balance: Decimal = Decimal("0.00")
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['currency'] = self.currency.value
        data['payment_method'] = self.payment_method.value
        data['volume_tier'] = self.volume_tier.value
        data['current_balance'] = str(self.current_balance)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class LineItem:
    """Invoice line item"""
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    service_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "service_type": self.service_type or ""
        }


@dataclass
class Invoice:
    """Customer invoice"""
    invoice_id: str
    account_id: str
    period_start: datetime
    period_end: datetime
    total_minutes: int
    subtotal: Decimal
    refunds: Decimal
    total: Decimal
    currency: str
    line_items: List[LineItem]
    status: str = "draft"  # draft, sent, paid, overdue
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "invoice_id": self.invoice_id,
            "account_id": self.account_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_minutes": self.total_minutes,
            "subtotal": str(self.subtotal),
            "refunds": str(self.refunds),
            "total": str(self.total),
            "currency": self.currency,
            "line_items": [item.to_dict() for item in self.line_items],
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None
        }


class BillingService:
    """
    Main billing service
    
    Integrates UCPM calculator, currency manager, and refund engine
    to provide complete billing functionality.
    """
    
    def __init__(
        self,
        postgres_url: Optional[str] = None,
        redis_url: Optional[str] = None
    ):
        """
        Initialize billing service
        
        Args:
            postgres_url: PostgreSQL connection URL
            redis_url: Redis connection URL
        """
        self.ucpm_calculator = UCPMCalculator()
        self.currency_manager = CurrencyManager()
        self.refund_engine = RefundEngine()
        self.stripe_service = StripeService()
        
        self.accounts: Dict[str, BillingAccount] = {}
        self.invoices: Dict[str, Invoice] = {}
        self.usage_records: Dict[str, List[UsageRecord]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize billing service"""
        # Update exchange rates
        await self.currency_manager.update_exchange_rates()
        self.logger.info("Billing service initialized")
    
    def create_account(
        self,
        user_id: str,
        currency: SupportedCurrency = SupportedCurrency.EUR,
        payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    ) -> BillingAccount:
        """
        Create a new billing account
        
        Args:
            user_id: User ID
            currency: Preferred currency
            payment_method: Payment method
            
        Returns:
            Created billing account
        """
        account = BillingAccount(
            account_id=str(uuid.uuid4()),
            user_id=user_id,
            currency=currency,
            payment_method=payment_method,
            volume_tier=VolumeTier.FREE
        )
        
        self.accounts[account.account_id] = account
        self.usage_records[account.account_id] = []
        
        self.logger.info(f"Created billing account {account.account_id} for user {user_id}")
        
        return account
    
    def record_usage(
        self,
        account_id: str,
        usage: UsageRecord
    ) -> None:
        """
        Record usage for billing
        
        Args:
            account_id: Account ID
            usage: Usage record
        """
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        
        self.usage_records[account_id].append(usage)
        
        # Update account totals
        account = self.accounts[account_id]
        account.total_minutes_used += int(usage.duration_minutes)
        
        # Update volume tier
        new_tier = self.ucpm_calculator.get_volume_tier(account.total_minutes_used)
        if new_tier != account.volume_tier:
            self.logger.info(
                f"Account {account_id} upgraded to {new_tier.value} tier"
            )
            account.volume_tier = new_tier
        
        # Check if refund needed
        if not usage.success or usage.quality_score < 0.7:
            should_refund, reason = self.refund_engine.should_refund(
                usage.quality_score,
                usage.error_type
            )
            
            if should_refund and reason:
                # Calculate cost first
                breakdown = self.ucpm_calculator.calculate_cost(
                    usage,
                    account.volume_tier
                )
                
                # Create refund
                self.refund_engine.create_refund(
                    session_id=usage.session_id,
                    user_id=usage.user_id,
                    original_amount=breakdown.total_cost,
                    currency=account.currency.value,
                    reason=reason,
                    quality_score=usage.quality_score
                )
    
    def calculate_account_charges(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> tuple[Decimal, List[LineItem]]:
        """
        Calculate charges for an account in a period
        
        Args:
            account_id: Account ID
            period_start: Period start date
            period_end: Period end date
            
        Returns:
            Tuple of (total_amount, line_items)
        """
        account = self.accounts[account_id]
        usage_list = self.usage_records.get(account_id, [])
        
        # Filter usage by period
        period_usage = [
            u for u in usage_list
            if period_start <= u.start_time <= period_end
        ]
        
        if not period_usage:
            return Decimal("0.00"), []
        
        # Calculate costs
        total_cost, breakdowns = self.ucpm_calculator.calculate_batch_cost(
            period_usage,
            account.volume_tier
        )
        
        # Create line items
        line_items = []
        
        # Group by service type
        service_totals = {
            "STT": Decimal("0.00"),
            "LLM": Decimal("0.00"),
            "TTS": Decimal("0.00"),
            "Telephony": Decimal("0.00"),
            "Platform": Decimal("0.00"),
        }
        
        total_minutes = sum(int(u.duration_minutes) for u in period_usage)
        
        for breakdown in breakdowns:
            service_totals["STT"] += breakdown.stt_cost
            service_totals["LLM"] += breakdown.llm_cost
            service_totals["TTS"] += breakdown.tts_cost
            service_totals["Telephony"] += breakdown.telephony_cost
            service_totals["Platform"] += breakdown.platform_cost
        
        # Create line items for each service
        ucpm = self.ucpm_calculator.calculate_ucpm(
            account.volume_tier,
            [ServiceType.STT, ServiceType.LLM, ServiceType.TTS, ServiceType.TELEPHONY]
        )
        
        for service, amount in service_totals.items():
            if amount > 0:
                line_items.append(LineItem(
                    description=f"{service} Service ({total_minutes} minutes)",
                    quantity=Decimal(total_minutes),
                    unit_price=ucpm,
                    amount=amount,
                    service_type=service.lower()
                ))
        
        return total_cost, line_items
    
    def generate_invoice(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Invoice:
        """
        Generate invoice for an account
        
        Args:
            account_id: Account ID
            period_start: Billing period start
            period_end: Billing period end
            
        Returns:
            Generated invoice
        """
        account = self.accounts[account_id]
        
        # Calculate charges
        subtotal, line_items = self.calculate_account_charges(
            account_id,
            period_start,
            period_end
        )
        
        # Calculate refunds
        user_refunds = self.refund_engine.get_user_refunds(
            account.user_id,
            days=(period_end - period_start).days
        )
        
        total_refunds = sum(
            r.refund_amount for r in user_refunds
            if period_start <= r.created_at <= period_end
        )
        
        # Calculate total
        total = subtotal - total_refunds
        
        # Get total minutes
        usage_list = self.usage_records.get(account_id, [])
        period_usage = [
            u for u in usage_list
            if period_start <= u.start_time <= period_end
        ]
        total_minutes = sum(int(u.duration_minutes) for u in period_usage)
        
        # Create invoice
        invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            total_minutes=total_minutes,
            subtotal=subtotal,
            refunds=total_refunds,
            total=total,
            currency=account.currency.value,
            line_items=line_items,
            status="draft",
            due_date=period_end + timedelta(days=30)
        )
        
        self.invoices[invoice.invoice_id] = invoice
        
        self.logger.info(
            f"Generated invoice {invoice.invoice_id} for account {account_id}: "
            f"{total} {account.currency.value}"
        )
        
        return invoice
    
    def get_usage_report(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Get detailed usage report
        
        Args:
            account_id: Account ID
            period_start: Period start
            period_end: Period end
            
        Returns:
            Usage report dictionary
        """
        account = self.accounts[account_id]
        usage_list = self.usage_records.get(account_id, [])
        
        # Filter by period
        period_usage = [
            u for u in usage_list
            if period_start <= u.start_time <= period_end
        ]
        
        # Calculate statistics
        total_sessions = len(period_usage)
        successful_sessions = sum(1 for u in period_usage if u.success)
        failed_sessions = total_sessions - successful_sessions
        
        total_minutes = sum(u.duration_minutes for u in period_usage)
        avg_quality = (
            sum(u.quality_score for u in period_usage) / total_sessions
            if total_sessions > 0 else 0
        )
        
        # Calculate costs
        total_cost, _ = self.calculate_account_charges(
            account_id,
            period_start,
            period_end
        )
        
        # Get refunds
        user_refunds = self.refund_engine.get_user_refunds(
            account.user_id,
            days=(period_end - period_start).days
        )
        period_refunds = [
            r for r in user_refunds
            if period_start <= r.created_at <= period_end
        ]
        
        return {
            "account_id": account_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "volume_tier": account.volume_tier.value,
            "currency": account.currency.value,
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "total_minutes": float(total_minutes),
            "average_quality_score": avg_quality,
            "total_cost": str(total_cost),
            "total_refunds": str(sum(r.refund_amount for r in period_refunds)),
            "refund_count": len(period_refunds),
            "net_cost": str(total_cost - sum(r.refund_amount for r in period_refunds))
        }
    
    async def process_payments(self) -> Dict[str, int]:
        """
        Process pending payments and refunds
        
        Returns:
            Processing statistics
        """
        # Process refunds
        refund_stats = {
            "processed": 0,
            "failed": 0
        }
        
        # Get pending refunds from queue
        # We access the queue directly to process with Stripe
        # In a cleaner implementation, we might pass a callback to RefundEngine
        pending_refunds = list(self.refund_engine.refund_queue)
        
        for refund in pending_refunds:
            # Skip if already processing
            if refund.status == "processing":
                continue
                
            refund.status = "processing" # Use string as enum might be tricky to import here if not careful, but we have RefundStatus
            
            # Process with Stripe
            # We assume the transaction_id is available in metadata or we do a direct refund
            # For now, we just simulate it or use a mock transaction ID
            transaction_id = refund.metadata.get("original_transaction_id", "tx_mock")
            
            success = await self.stripe_service.process_refund(
                transaction_id=transaction_id,
                amount=refund.refund_amount,
                reason=refund.reason.value
            )
            
            if success:
                refund.status = RefundStatus.COMPLETED
                refund.processed_at = datetime.utcnow()
                self.refund_engine.processed_refunds.append(refund)
                self.refund_engine.refund_queue.remove(refund)
                refund_stats["processed"] += 1
            else:
                refund.status = RefundStatus.FAILED
                refund_stats["failed"] += 1
        
        # Apply pending rate changes
        self.currency_manager.apply_pending_rate_changes()
        
        return {
            "refunds_processed": refund_stats["processed"],
            "refunds_failed": refund_stats["failed"]
        }
    
    def get_account(self, account_id: str) -> Optional[BillingAccount]:
        """Get billing account by ID"""
        return self.accounts.get(account_id)
    
    async def pay_invoice(self, invoice_id: str) -> bool:
        """
        Pay an invoice using the account's payment method
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            True if payment successful
        """
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            self.logger.error(f"Invoice {invoice_id} not found")
            return False
            
        if invoice.status == "paid":
            self.logger.info(f"Invoice {invoice_id} already paid")
            return True
            
        account = self.accounts.get(invoice.account_id)
        if not account:
            self.logger.error(f"Account {invoice.account_id} not found")
            return False
            
        # Get customer ID (mock or real)
        # In a real app, we'd store the stripe_customer_id on the BillingAccount
        customer_id = account.metadata.get("stripe_customer_id")
        if not customer_id:
            # Create customer if missing
            customer_id = await self.stripe_service.create_customer(
                user_id=account.user_id,
                email=account.metadata.get("email", f"{account.user_id}@voiquyr.local"),
                name=account.metadata.get("name", f"Account {account.user_id}")
            )
            account.metadata["stripe_customer_id"] = customer_id
            
        # Process charge
        result = await self.stripe_service.charge_customer(
            customer_id=customer_id,
            amount=invoice.total,
            currency=invoice.currency,
            description=f"Invoice {invoice_id}"
        )
        
        if result.success:
            invoice.status = "paid"
            invoice.paid_date = datetime.utcnow()
            self.logger.info(f"Invoice {invoice_id} paid successfully: {result.transaction_id}")
            return True
        else:
            self.logger.error(f"Payment failed for invoice {invoice_id}: {result.error_message}")
            return False

import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
from src.billing.billing_service import BillingService, PaymentMethod, SupportedCurrency
from src.billing.ucpm_calculator import UsageRecord, ServiceType

class TestBillingService(unittest.TestCase):
    def setUp(self):
        self.service = BillingService()
        # Mock currency manager to avoid network calls
        self.service.currency_manager.update_exchange_rates = MagicMock()

    def test_create_account(self):
        account = self.service.create_account("user123")
        self.assertEqual(account.user_id, "user123")
        self.assertIn(account.account_id, self.service.accounts)

    def test_record_usage_and_invoice(self):
        account = self.service.create_account("user123")
        
        # Record usage
        usage = UsageRecord(
            session_id="sess1",
            user_id="user123",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(minutes=10),
            duration_seconds=600,
            services_used=[ServiceType.STT, ServiceType.LLM]
        )
        self.service.record_usage(account.account_id, usage)
        
        # Check account totals
        self.assertEqual(account.total_minutes_used, 10)
        
        # Generate invoice
        start = datetime.utcnow() - timedelta(days=1)
        end = datetime.utcnow() + timedelta(days=1)
        
        invoice = self.service.generate_invoice(account.account_id, start, end)
        
        self.assertEqual(invoice.total_minutes, 10)
        # Cost calculation: 10 mins * (0.10 * (1 + 0.15 + 0.50)) = 10 * 0.165 = 1.65
        self.assertEqual(invoice.total, Decimal("1.65"))

    def test_refund_integration(self):
        account = self.service.create_account("user123")
        
        # Record failed usage (should trigger refund)
        usage = UsageRecord(
            session_id="sess_fail",
            user_id="user123",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(minutes=10),
            duration_seconds=600,
            services_used=[ServiceType.STT],
            success=False,
            error_type="system_error"
        )
        
        self.service.record_usage(account.account_id, usage)
        
        # Check refund created
        refunds = self.service.refund_engine.get_user_refunds("user123")
        self.assertEqual(len(refunds), 1)
        self.assertEqual(refunds[0].refund_amount, Decimal("1.15")) # 10 * 0.10 * 1.15 = 1.15

if __name__ == '__main__':
    unittest.main()

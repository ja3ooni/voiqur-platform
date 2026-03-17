import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
from src.billing.billing_service import BillingService, PaymentMethod, SupportedCurrency
from src.billing.ucpm_calculator import UsageRecord, ServiceType
from src.billing.refund_engine import RefundReason, RefundStatus

class TestBillingStripeIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = BillingService()
        # Mock currency manager
        self.service.currency_manager.update_exchange_rates = MagicMock()
        
        # Mock Stripe service (it already has mocks, but we can verify calls)
        # We'll use the internal mock implementation of StripeService for this test

    async def test_pay_invoice(self):
        account = self.service.create_account("user_stripe")
        
        # Create invoice
        invoice = self.service.generate_invoice(
            account.account_id,
            datetime.utcnow(),
            datetime.utcnow()
        )
        # Force total > 0 for test
        invoice.total = Decimal("10.00")
        
        # Pay invoice
        success = await self.service.pay_invoice(invoice.invoice_id)
        
        self.assertTrue(success)
        self.assertEqual(invoice.status, "paid")
        self.assertIsNotNone(invoice.paid_date)
        
        # Check customer created
        self.assertIn("stripe_customer_id", account.metadata)

    async def test_process_refund_via_stripe(self):
        account = self.service.create_account("user_refund")
        
        # Create a refund in queue
        refund = self.service.refund_engine.create_refund(
            session_id="sess_refund",
            user_id="user_refund",
            original_amount=Decimal("10.00"),
            currency="EUR",
            reason=RefundReason.LLM_HALLUCINATION
        )
        
        # Add mock transaction ID
        refund.metadata["original_transaction_id"] = "tx_123"
        
        # Mock the payment in Stripe service so refund succeeds
        self.service.stripe_service._mock_payments["tx_123"] = {
            "customer_id": "cus_mock",
            "amount": Decimal("10.00"),
            "currency": "EUR",
            "status": "succeeded"
        }
        
        # Process payments
        stats = await self.service.process_payments()
        
        self.assertEqual(stats["refunds_processed"], 1)
        self.assertEqual(stats["refunds_failed"], 0)
        
        # Check refund status
        self.assertEqual(refund.status, RefundStatus.COMPLETED)
        self.assertIn(refund, self.service.refund_engine.processed_refunds)

if __name__ == '__main__':
    unittest.main()

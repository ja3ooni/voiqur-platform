import unittest
from decimal import Decimal
from src.billing.refund_engine import RefundEngine, RefundReason

class TestRefundEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RefundEngine()

    def test_should_refund(self):
        # Low quality score
        should, reason = self.engine.should_refund(0.2)
        self.assertTrue(should)
        self.assertEqual(reason, RefundReason.LOW_QUALITY_SCORE)

        # High quality score
        should, reason = self.engine.should_refund(0.9)
        self.assertFalse(should)
        self.assertIsNone(reason)

        # Specific error
        should, reason = self.engine.should_refund(0.8, error_type="hallucination")
        self.assertTrue(should)
        self.assertEqual(reason, RefundReason.LLM_HALLUCINATION)

    def test_calculate_refund_amount(self):
        # Full refund for hallucination
        amount = self.engine.calculate_refund_amount(
            Decimal("10.00"),
            RefundReason.LLM_HALLUCINATION
        )
        self.assertEqual(amount, Decimal("10.00"))

        # Partial refund for STT low confidence (50%)
        amount = self.engine.calculate_refund_amount(
            Decimal("10.00"),
            RefundReason.STT_LOW_CONFIDENCE
        )
        self.assertEqual(amount, Decimal("5.00"))

        # Quality score based refund
        # < 0.3 -> 100%
        amount = self.engine.calculate_refund_amount(
            Decimal("10.00"),
            RefundReason.LOW_QUALITY_SCORE,
            quality_score=0.2
        )
        self.assertEqual(amount, Decimal("10.00"))

if __name__ == '__main__':
    unittest.main()

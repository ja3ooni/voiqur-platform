import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from src.billing.ucpm_calculator import UCPMCalculator, ServiceType, VolumeTier, UsageRecord

class TestUCPMCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = UCPMCalculator()

    def test_get_volume_tier(self):
        self.assertEqual(self.calculator.get_volume_tier(500), VolumeTier.FREE)
        self.assertEqual(self.calculator.get_volume_tier(5000), VolumeTier.STARTER)
        self.assertEqual(self.calculator.get_volume_tier(50000), VolumeTier.PROFESSIONAL)
        self.assertEqual(self.calculator.get_volume_tier(150000), VolumeTier.ENTERPRISE)

    def test_calculate_ucpm(self):
        # Free tier, only STT
        ucpm = self.calculator.calculate_ucpm(VolumeTier.FREE, [ServiceType.STT])
        # Base 0.10 * (1 + 0.15) = 0.115
        self.assertEqual(ucpm, Decimal("0.1150"))

        # Starter tier, STT + LLM + TTS
        ucpm = self.calculator.calculate_ucpm(VolumeTier.STARTER, [ServiceType.STT, ServiceType.LLM, ServiceType.TTS])
        # Base 0.06 * (1 + 0.15 + 0.50 + 0.25) = 0.06 * 1.90 = 0.114
        self.assertEqual(ucpm, Decimal("0.1140"))

    def test_calculate_cost(self):
        usage = UsageRecord(
            session_id="test_session",
            user_id="test_user",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=10),
            duration_seconds=600,
            services_used=[ServiceType.STT, ServiceType.LLM]
        )
        
        breakdown = self.calculator.calculate_cost(usage, VolumeTier.FREE)
        
        # Minutes = 10
        # Base rate = 0.10
        # STT cost = 0.10 * 0.15 * 10 = 0.15
        # LLM cost = 0.10 * 0.50 * 10 = 0.50
        # Platform cost = 0.10 * 10 = 1.00
        # Total = 1.65
        
        self.assertEqual(breakdown.stt_cost, Decimal("0.15"))
        self.assertEqual(breakdown.llm_cost, Decimal("0.50"))
        self.assertEqual(breakdown.platform_cost, Decimal("1.00"))
        self.assertEqual(breakdown.total_cost, Decimal("1.65"))

if __name__ == '__main__':
    unittest.main()

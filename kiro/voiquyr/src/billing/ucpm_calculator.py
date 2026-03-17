"""
UCPM (Unified Cost Per Minute) Calculator

Bundles STT, LLM, TTS, and telephony costs into a single predictable metric.
Implements Requirement 13.2 - Unified Cost Per Minute calculation.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Types of services included in UCPM"""
    STT = "stt"
    LLM = "llm"
    TTS = "tts"
    TELEPHONY = "telephony"
    EMOTION = "emotion"
    ACCENT = "accent"
    LIP_SYNC = "lip_sync"


class VolumeTier(Enum):
    """Volume-based pricing tiers"""
    FREE = "free"  # 0-1000 minutes
    STARTER = "starter"  # 1001-10000 minutes
    PROFESSIONAL = "professional"  # 10001-100000 minutes
    ENTERPRISE = "enterprise"  # 100000+ minutes


@dataclass
class CostBreakdown:
    """Detailed cost breakdown by service"""
    stt_cost: Decimal = Decimal("0.00")
    llm_cost: Decimal = Decimal("0.00")
    tts_cost: Decimal = Decimal("0.00")
    telephony_cost: Decimal = Decimal("0.00")
    emotion_cost: Decimal = Decimal("0.00")
    accent_cost: Decimal = Decimal("0.00")
    lip_sync_cost: Decimal = Decimal("0.00")
    platform_cost: Decimal = Decimal("0.00")
    total_cost: Decimal = Decimal("0.00")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary with string values"""
        return {k: str(v) for k, v in asdict(self).items()}


@dataclass
class UsageRecord:
    """Record of service usage for billing"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    services_used: List[ServiceType]
    stt_duration: int = 0
    llm_tokens: int = 0
    tts_characters: int = 0
    telephony_duration: int = 0
    quality_score: float = 1.0  # 0.0-1.0, affects refunds
    success: bool = True
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_minutes(self) -> Decimal:
        """Get duration in minutes"""
        return Decimal(self.duration_seconds) / Decimal(60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['services_used'] = [s.value for s in self.services_used]
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data


class UCPMCalculator:
    """
    Unified Cost Per Minute Calculator
    
    Bundles all service costs (STT, LLM, TTS, Telephony) into a single
    predictable per-minute rate based on volume tier.
    """
    
    # Base UCPM rates by tier (in EUR)
    BASE_RATES = {
        VolumeTier.FREE: Decimal("0.10"),  # €0.10/min
        VolumeTier.STARTER: Decimal("0.06"),  # €0.06/min
        VolumeTier.PROFESSIONAL: Decimal("0.04"),  # €0.04/min
        VolumeTier.ENTERPRISE: Decimal("0.03"),  # €0.03/min (negotiable)
    }
    
    # Volume thresholds (in minutes)
    VOLUME_THRESHOLDS = {
        VolumeTier.FREE: 0,
        VolumeTier.STARTER: 1000,
        VolumeTier.PROFESSIONAL: 10000,
        VolumeTier.ENTERPRISE: 100000,
    }
    
    # Service cost multipliers (relative to base rate)
    SERVICE_MULTIPLIERS = {
        ServiceType.STT: Decimal("0.15"),  # 15% of base
        ServiceType.LLM: Decimal("0.50"),  # 50% of base
        ServiceType.TTS: Decimal("0.25"),  # 25% of base
        ServiceType.TELEPHONY: Decimal("0.10"),  # 10% of base
        ServiceType.EMOTION: Decimal("0.00"),  # Included
        ServiceType.ACCENT: Decimal("0.00"),  # Included
        ServiceType.LIP_SYNC: Decimal("0.00"),  # Included
    }
    
    def __init__(self):
        """Initialize UCPM calculator"""
        self.logger = logging.getLogger(__name__)
    
    def get_volume_tier(self, total_minutes: int) -> VolumeTier:
        """
        Determine volume tier based on total usage
        
        Args:
            total_minutes: Total minutes used in billing period
            
        Returns:
            Appropriate volume tier
        """
        if total_minutes >= self.VOLUME_THRESHOLDS[VolumeTier.ENTERPRISE]:
            return VolumeTier.ENTERPRISE
        elif total_minutes >= self.VOLUME_THRESHOLDS[VolumeTier.PROFESSIONAL]:
            return VolumeTier.PROFESSIONAL
        elif total_minutes >= self.VOLUME_THRESHOLDS[VolumeTier.STARTER]:
            return VolumeTier.STARTER
        else:
            return VolumeTier.FREE
    
    def calculate_ucpm(
        self,
        volume_tier: VolumeTier,
        services_used: List[ServiceType]
    ) -> Decimal:
        """
        Calculate unified cost per minute
        
        Args:
            volume_tier: Current volume tier
            services_used: List of services used
            
        Returns:
            Cost per minute in EUR
        """
        base_rate = self.BASE_RATES[volume_tier]
        
        # Calculate total multiplier
        total_multiplier = sum(
            self.SERVICE_MULTIPLIERS.get(service, Decimal("0.00"))
            for service in services_used
        )
        
        # UCPM = base_rate * (1 + total_multiplier)
        ucpm = base_rate * (Decimal("1.00") + total_multiplier)
        
        return ucpm.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    
    def calculate_cost(
        self,
        usage: UsageRecord,
        volume_tier: VolumeTier
    ) -> CostBreakdown:
        """
        Calculate detailed cost breakdown for usage
        
        Args:
            usage: Usage record
            volume_tier: Current volume tier
            
        Returns:
            Detailed cost breakdown
        """
        base_rate = self.BASE_RATES[volume_tier]
        minutes = usage.duration_minutes
        
        breakdown = CostBreakdown()
        
        # Calculate cost for each service
        for service in usage.services_used:
            multiplier = self.SERVICE_MULTIPLIERS.get(service, Decimal("0.00"))
            service_cost = (base_rate * multiplier * minutes).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            if service == ServiceType.STT:
                breakdown.stt_cost = service_cost
            elif service == ServiceType.LLM:
                breakdown.llm_cost = service_cost
            elif service == ServiceType.TTS:
                breakdown.tts_cost = service_cost
            elif service == ServiceType.TELEPHONY:
                breakdown.telephony_cost = service_cost
            elif service == ServiceType.EMOTION:
                breakdown.emotion_cost = service_cost
            elif service == ServiceType.ACCENT:
                breakdown.accent_cost = service_cost
            elif service == ServiceType.LIP_SYNC:
                breakdown.lip_sync_cost = service_cost
        
        # Calculate platform cost (base rate * minutes)
        breakdown.platform_cost = (base_rate * minutes).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Calculate total
        breakdown.total_cost = (
            breakdown.stt_cost +
            breakdown.llm_cost +
            breakdown.tts_cost +
            breakdown.telephony_cost +
            breakdown.emotion_cost +
            breakdown.accent_cost +
            breakdown.lip_sync_cost +
            breakdown.platform_cost
        )
        
        self.logger.info(
            f"Calculated cost for session {usage.session_id}: "
            f"€{breakdown.total_cost} ({minutes} minutes, tier: {volume_tier.value})"
        )
        
        return breakdown
    
    def calculate_batch_cost(
        self,
        usage_records: List[UsageRecord],
        volume_tier: VolumeTier
    ) -> tuple[Decimal, List[CostBreakdown]]:
        """
        Calculate costs for multiple usage records
        
        Args:
            usage_records: List of usage records
            volume_tier: Current volume tier
            
        Returns:
            Tuple of (total_cost, list of breakdowns)
        """
        breakdowns = []
        total_cost = Decimal("0.00")
        
        for usage in usage_records:
            breakdown = self.calculate_cost(usage, volume_tier)
            breakdowns.append(breakdown)
            total_cost += breakdown.total_cost
        
        self.logger.info(
            f"Calculated batch cost: €{total_cost} "
            f"({len(usage_records)} sessions)"
        )
        
        return total_cost, breakdowns
    
    def estimate_monthly_cost(
        self,
        estimated_minutes: int,
        services: List[ServiceType]
    ) -> Dict[str, Any]:
        """
        Estimate monthly cost based on expected usage
        
        Args:
            estimated_minutes: Expected monthly minutes
            services: Services to be used
            
        Returns:
            Cost estimate with breakdown
        """
        tier = self.get_volume_tier(estimated_minutes)
        ucpm = self.calculate_ucpm(tier, services)
        total_cost = (ucpm * Decimal(estimated_minutes)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        return {
            "estimated_minutes": estimated_minutes,
            "volume_tier": tier.value,
            "ucpm": str(ucpm),
            "total_cost": str(total_cost),
            "services": [s.value for s in services],
            "currency": "EUR"
        }

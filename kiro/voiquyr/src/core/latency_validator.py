"""
Latency Validator - Synthetic benchmarking and deployment gate.

Runs synthetic test suite every 5 minutes, tracks p50/p95/p99 latency,
and enforces SLA with deployment gates.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class Region(str, Enum):
    """Deployment regions."""
    EU_CENTRAL = "eu-central-1"
    ME_DUBAI = "me-dubai-1"
    ASIA_MUMBAI = "asia-mumbai-1"
    ASIA_SINGAPORE = "asia-singapore-1"


class Component(str, Enum):
    """System components."""
    STT = "stt"
    LLM = "llm"
    TTS = "tts"
    TOTAL = "total"


@dataclass
class LatencyMeasurement:
    """Single latency measurement."""
    region: Region
    component: Component
    latency_ms: float
    is_synthetic: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None


@dataclass
class RegionLatencyReport:
    """Latency report for a region."""
    region: Region
    p50_ms: float
    p95_ms: float
    p99_ms: float
    component_breakdown: Dict[Component, Dict[str, float]]
    measurement_count: int
    period_start: datetime
    period_end: datetime


@dataclass
class DeploymentGateResult:
    """Result of deployment gate check."""
    gate_passed: bool
    region: Region
    p95_latency_ms: float
    sla_threshold_ms: float = 500.0
    failure_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LatencyValidator:
    """Synthetic benchmarking and deployment gate."""
    
    def __init__(self, sla_threshold_ms: float = 500.0):
        self.sla_threshold_ms = sla_threshold_ms
        self.measurements: List[LatencyMeasurement] = []
        self.retention_days = 90
        self.synthetic_utterances = self._load_synthetic_utterances()
        self.alert_sent = {}
    
    def _load_synthetic_utterances(self) -> List[str]:
        """Load 50 fixed utterances for synthetic testing."""
        # Simplified - production would load from file
        return [f"Test utterance {i}" for i in range(50)]
    
    async def run_synthetic_suite(self, region: Region) -> List[LatencyMeasurement]:
        """Run synthetic test suite for region."""
        logger.info(f"Running synthetic suite for {region}")
        
        measurements = []
        
        for utterance in self.synthetic_utterances:
            # Simulate call with OpenTelemetry tracing
            trace_id = f"trace-{region}-{datetime.utcnow().timestamp()}"
            
            # Measure component latencies
            stt_latency = await self._measure_stt(utterance, region)
            llm_latency = await self._measure_llm(utterance, region)
            tts_latency = await self._measure_tts(utterance, region)
            total_latency = stt_latency + llm_latency + tts_latency
            
            # Record measurements
            for component, latency in [
                (Component.STT, stt_latency),
                (Component.LLM, llm_latency),
                (Component.TTS, tts_latency),
                (Component.TOTAL, total_latency)
            ]:
                measurement = LatencyMeasurement(
                    region=region,
                    component=component,
                    latency_ms=latency,
                    is_synthetic=True,
                    trace_id=trace_id
                )
                measurements.append(measurement)
                self.measurements.append(measurement)
        
        # Cleanup old measurements
        self._cleanup_old_measurements()
        
        logger.info(f"Synthetic suite completed for {region}: {len(measurements)} measurements")
        return measurements
    
    async def _measure_stt(self, utterance: str, region: Region) -> float:
        """Measure STT latency."""
        # Simulate STT processing
        await asyncio.sleep(0.05)  # 50ms
        return 50.0 + (hash(utterance) % 50)  # 50-100ms
    
    async def _measure_llm(self, utterance: str, region: Region) -> float:
        """Measure LLM latency."""
        await asyncio.sleep(0.15)  # 150ms
        return 150.0 + (hash(utterance) % 100)  # 150-250ms
    
    async def _measure_tts(self, utterance: str, region: Region) -> float:
        """Measure TTS latency."""
        await asyncio.sleep(0.08)  # 80ms
        return 80.0 + (hash(utterance) % 70)  # 80-150ms
    
    def _cleanup_old_measurements(self):
        """Remove measurements older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        self.measurements = [
            m for m in self.measurements
            if m.timestamp >= cutoff
        ]
    
    def get_region_report(self, region: Region, hours: int = 24) -> RegionLatencyReport:
        """Get latency report for region."""
        period_start = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter measurements
        region_measurements = [
            m for m in self.measurements
            if m.region == region and m.timestamp >= period_start
        ]
        
        if not region_measurements:
            return RegionLatencyReport(
                region=region,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                component_breakdown={},
                measurement_count=0,
                period_start=period_start,
                period_end=datetime.utcnow()
            )
        
        # Calculate percentiles for total latency
        total_latencies = sorted([
            m.latency_ms for m in region_measurements
            if m.component == Component.TOTAL
        ])
        
        p50 = self._percentile(total_latencies, 50)
        p95 = self._percentile(total_latencies, 95)
        p99 = self._percentile(total_latencies, 99)
        
        # Component breakdown
        component_breakdown = {}
        for component in [Component.STT, Component.LLM, Component.TTS]:
            comp_latencies = sorted([
                m.latency_ms for m in region_measurements
                if m.component == component
            ])
            if comp_latencies:
                component_breakdown[component] = {
                    "p50": self._percentile(comp_latencies, 50),
                    "p95": self._percentile(comp_latencies, 95),
                    "p99": self._percentile(comp_latencies, 99)
                }
        
        return RegionLatencyReport(
            region=region,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            component_breakdown=component_breakdown,
            measurement_count=len(region_measurements),
            period_start=period_start,
            period_end=datetime.utcnow()
        )
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        
        k = (len(values) - 1) * percentile / 100
        f = int(k)
        c = f + 1
        
        if c >= len(values):
            return values[-1]
        
        return values[f] + (k - f) * (values[c] - values[f])
    
    async def check_sla_breach(self, region: Region) -> bool:
        """Check for SLA breach and fire alert."""
        report = self.get_region_report(region, hours=1)
        
        if report.p95_ms > self.sla_threshold_ms:
            # Fire alert
            alert_key = f"{region}-{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
            
            if alert_key not in self.alert_sent:
                logger.critical(
                    f"SLA BREACH: {region} p95={report.p95_ms:.1f}ms > {self.sla_threshold_ms}ms"
                )
                self.alert_sent[alert_key] = datetime.utcnow()
                
                # Retry delivery 5x (simplified)
                for attempt in range(5):
                    try:
                        await self._send_alert(region, report.p95_ms)
                        break
                    except Exception as e:
                        logger.error(f"Alert delivery failed (attempt {attempt + 1}): {e}")
                        await asyncio.sleep(2 ** attempt)
                
                return True
        
        return False
    
    async def _send_alert(self, region: Region, p95_ms: float):
        """Send SLA breach alert."""
        # Placeholder for actual alert delivery (PagerDuty, Slack, etc.)
        logger.info(f"Alert sent for {region}: p95={p95_ms:.1f}ms")
    
    async def run_deployment_gate(self, region: Region) -> DeploymentGateResult:
        """Run deployment gate validation."""
        logger.info(f"Running deployment gate for {region}")
        
        # Run validation suite
        try:
            measurements = await asyncio.wait_for(
                self.run_synthetic_suite(region),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            return DeploymentGateResult(
                gate_passed=False,
                region=region,
                p95_latency_ms=0.0,
                failure_reason="Validation suite timeout"
            )
        
        # Get report
        report = self.get_region_report(region, hours=1)
        
        # Check p95 threshold
        if report.p95_ms > self.sla_threshold_ms:
            return DeploymentGateResult(
                gate_passed=False,
                region=region,
                p95_latency_ms=report.p95_ms,
                failure_reason=f"p95 {report.p95_ms:.1f}ms exceeds SLA {self.sla_threshold_ms}ms"
            )
        
        return DeploymentGateResult(
            gate_passed=True,
            region=region,
            p95_latency_ms=report.p95_ms
        )
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data for all regions."""
        dashboard = {}
        
        for region in Region:
            report = self.get_region_report(region, hours=24)
            dashboard[region.value] = {
                "p50_ms": report.p50_ms,
                "p95_ms": report.p95_ms,
                "p99_ms": report.p99_ms,
                "components": {
                    comp.value: breakdown
                    for comp, breakdown in report.component_breakdown.items()
                },
                "measurement_count": report.measurement_count
            }
        
        return dashboard


# Global instance
_latency_validator: Optional[LatencyValidator] = None


def get_latency_validator() -> LatencyValidator:
    """Get global latency validator instance."""
    global _latency_validator
    if _latency_validator is None:
        _latency_validator = LatencyValidator()
    return _latency_validator


def set_latency_validator(validator: LatencyValidator) -> None:
    """Set global latency validator instance."""
    global _latency_validator
    _latency_validator = validator

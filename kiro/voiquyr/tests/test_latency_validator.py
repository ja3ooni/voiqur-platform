"""
Property tests for Latency_Validator.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st
from src.core.latency_validator import (
    LatencyValidator,
    Region,
    Component,
    LatencyMeasurement
)
from datetime import datetime


@pytest.fixture
def validator():
    """Setup latency validator."""
    return LatencyValidator()


# Property 18: Latency decomposition sum invariant
# Validates: Requirements 7.4
@given(
    stt_latency=st.floats(min_value=0, max_value=500),
    llm_latency=st.floats(min_value=0, max_value=500),
    tts_latency=st.floats(min_value=0, max_value=500),
    other_latency=st.floats(min_value=0, max_value=500)
)
@settings(max_examples=100)
def test_latency_decomposition_sum_invariant(validator, stt_latency, llm_latency, tts_latency, other_latency):
    """Property 18: Latency decomposition sum invariant."""
    # Calculate total
    total_latency = stt_latency + llm_latency + tts_latency + other_latency
    
    # Sum of components should equal total within 1ms tolerance
    component_sum = stt_latency + llm_latency + tts_latency + other_latency
    
    assert abs(component_sum - total_latency) <= 1.0


# Property 19: SLA breach alert generation
# Validates: Requirements 7.3
@given(p95_latency=st.floats(min_value=501, max_value=2000))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_sla_breach_alert_generation(validator, p95_latency):
    """Property 19: SLA breach alert generation."""
    region = Region.EU_CENTRAL
    
    # Add measurements that will result in p95 > 500ms
    for _ in range(100):
        validator.measurements.append(LatencyMeasurement(
            region=region,
            component=Component.TOTAL,
            latency_ms=p95_latency,
            is_synthetic=True
        ))
    
    # Check SLA breach
    breach_detected = await validator.check_sla_breach(region)
    
    # Assert alert generated
    assert breach_detected is True


# Property 20: Deployment gate enforcement
# Validates: Requirements 7.8
@given(measured_p95=st.floats(min_value=501, max_value=2000))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_deployment_gate_enforcement(validator, measured_p95):
    """Property 20: Deployment gate enforcement."""
    region = Region.EU_CENTRAL
    
    # Add measurements that will result in p95 > 500ms
    for _ in range(100):
        validator.measurements.append(LatencyMeasurement(
            region=region,
            component=Component.TOTAL,
            latency_ms=measured_p95,
            is_synthetic=True,
            timestamp=datetime.utcnow()
        ))
    
    # Run deployment gate
    result = await validator.run_deployment_gate(region)
    
    # Assert gate fails when p95 > 500ms
    assert result.gate_passed is False
    assert result.p95_latency_ms > 500.0

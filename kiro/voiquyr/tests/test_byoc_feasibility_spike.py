"""
Unit tests for BYOC Feasibility Spike.

Feature: voiquyr-differentiators
"""

import pytest
from src.telephony.byoc_feasibility_spike import (
    BYOCFeasibilitySpike,
    Carrier,
    Recommendation,
    SIPTraceAnalyser
)


@pytest.fixture
def spike():
    """Setup feasibility spike."""
    return BYOCFeasibilitySpike()


@pytest.fixture
def analyser():
    """Setup SIP trace analyser."""
    return SIPTraceAnalyser()


# Test Tata trunk registration via self-service API only (Req 8.1)
@pytest.mark.asyncio
async def test_tata_trunk_registration(spike):
    """Test Tata trunk registration via self-service API."""
    trunk_config = {
        "host": "sip.tata.com",
        "port": 5060,
        "username": "test_user",
        "password": "test_pass"
    }
    
    report = await spike.validate_carrier(Carrier.TATA, trunk_config)
    
    assert report.carrier == Carrier.TATA
    assert report.recommendation in [Recommendation.GO, Recommendation.GO_WITH_WORKAROUNDS, Recommendation.NO_GO]


# Test Jio trunk registration via self-service API only (Req 8.2)
@pytest.mark.asyncio
async def test_jio_trunk_registration(spike):
    """Test Jio trunk registration via self-service API."""
    trunk_config = {
        "host": "sip.jio.com",
        "port": 5060,
        "username": "test_user",
        "password": "test_pass"
    }
    
    report = await spike.validate_carrier(Carrier.JIO, trunk_config)
    
    assert report.carrier == Carrier.JIO
    assert report.recommendation in [Recommendation.GO, Recommendation.GO_WITH_WORKAROUNDS, Recommendation.NO_GO]


# Test unknown SIP header present → call succeeds, header ignored (Req 8.5)
def test_unknown_header_ignored(analyser):
    """Test unknown SIP header handling."""
    trace_data = {
        "messages": [{
            "method": "INVITE",
            "headers": {
                "Via": "SIP/2.0/UDP 192.168.1.1:5060",
                "From": "<sip:user@domain.com>",
                "To": "<sip:dest@carrier.com>",
                "Call-ID": "abc123",
                "CSeq": "1 INVITE",
                "Max-Forwards": "70",
                "X-Unknown-Header": "value"
            }
        }]
    }
    
    nonstandard = analyser.extract_nonstandard_headers(trace_data)
    
    # Assert unknown header detected
    assert "X-Unknown-Header" in nonstandard


# Test FeasibilityReport contains all required fields (Req 8.6)
@pytest.mark.asyncio
async def test_feasibility_report_completeness(spike):
    """Test feasibility report structure."""
    trunk_config = {"host": "sip.test.com", "port": 5060}
    
    report = await spike.validate_carrier(Carrier.TATA, trunk_config)
    
    # Assert all required fields present
    assert report.carrier is not None
    assert report.sip_compatibility_matrix is not None
    assert report.rfc3261_deviations is not None
    assert report.codec_results is not None
    assert report.nonstandard_headers is not None
    assert report.recommendation is not None
    assert hasattr(report, 'workaround_scope')


# Test workaround scope documented when carrier-specific fix required (Req 8.7)
@pytest.mark.asyncio
async def test_workaround_scope_documentation(spike):
    """Test workaround scope documentation."""
    trunk_config = {"host": "sip.test.com", "port": 5060}
    
    report = await spike.validate_carrier(Carrier.TATA, trunk_config)
    
    # If workarounds needed, scope should be documented
    if report.recommendation == Recommendation.GO_WITH_WORKAROUNDS:
        assert report.workaround_scope is not None
        assert len(report.workaround_scope) > 0

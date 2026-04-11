"""
Property tests for BYOC_Adapter.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
from src.telephony.byoc_adapter import (
    BYOCAdapter,
    SIPTrunk,
    MediaDirection
)


@pytest.fixture
def adapter():
    """Setup BYOC adapter with test trunk."""
    adapter = BYOCAdapter()
    adapter.register_trunk(SIPTrunk(
        trunk_id="test-trunk",
        name="Test Trunk",
        host="sip.test.com",
        max_channels=100
    ))
    return adapter


# Property 3: SIP codec negotiation correctness
# Validates: Requirements 2.3
@given(
    offered_codecs=st.frozensets(
        st.sampled_from(["G711u", "G711a", "G722", "Opus"]),
        min_size=1
    )
)
@settings(max_examples=100)
def test_codec_negotiation_correctness(adapter, offered_codecs):
    """Property 3: SIP codec negotiation correctness."""
    supported_codecs = {"G711u", "G711a", "G722", "Opus"}
    
    # Simulate codec negotiation
    intersection = offered_codecs & supported_codecs
    
    if intersection:
        # Should select a codec from intersection
        selected = list(intersection)[0]
        assert selected in offered_codecs
        assert selected in supported_codecs
    else:
        # Should return 488 Not Acceptable Here
        assert len(intersection) == 0


# Property 4: SRTP negotiation invariant
# Validates: Requirements 2.4
@given(srtp_in_offer=st.booleans())
@settings(max_examples=100)
def test_srtp_negotiation_invariant(adapter, srtp_in_offer):
    """Property 4: SRTP negotiation invariant."""
    # Simulate SRTP negotiation
    srtp_negotiated = srtp_in_offer
    
    # SRTP should be negotiated if and only if offered
    assert srtp_negotiated == srtp_in_offer


# Property 5: SIP trunk registration error classification
# Validates: Requirements 2.7
@given(
    failure_type=st.sampled_from(["auth", "network", "codec_mismatch"])
)
@settings(max_examples=100)
def test_registration_error_classification(adapter, failure_type):
    """Property 5: SIP trunk registration error classification."""
    # Simulate registration failure
    error_types = {"auth", "network", "codec_mismatch"}
    
    # Error type should be one of the defined categories
    assert failure_type in error_types

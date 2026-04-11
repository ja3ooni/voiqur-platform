"""
Property tests for Flash_Mode.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
from src.core.flash_mode import FlashMode, SpeculativeStatus


class MockLLMAgent:
    """Mock LLM agent for testing."""
    async def infer(self, transcript: str) -> str:
        return f"Response to: {transcript}"


@pytest.fixture
def flash_mode():
    """Setup flash mode instance."""
    return FlashMode()


@pytest.fixture
def llm_agent():
    """Setup mock LLM agent."""
    return MockLLMAgent()


# Property 8: Flash_Mode speculative hit reuse
# Validates: Requirements 4.3
@given(transcript=st.text(min_size=10, max_size=100))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_speculative_hit_reuse(flash_mode, llm_agent, transcript):
    """Property 8: Flash_Mode speculative hit reuse."""
    call_id = "test-call-001"
    tenant_id = "tenant-001"
    
    # Trigger speculative inference with high confidence
    await flash_mode.on_partial_transcript(
        call_id=call_id,
        partial_transcript=transcript,
        confidence=0.9,
        tenant_id=tenant_id,
        llm_agent=llm_agent
    )
    
    # Use same transcript as final
    result = await flash_mode.on_final_transcript(
        call_id=call_id,
        final_transcript=transcript,
        llm_agent=llm_agent
    )
    
    # Assert speculative hit
    assert result.was_speculative_hit is True
    assert result.final_response is not None


# Property 9: Flash_Mode speculative miss discard
# Validates: Requirements 4.2
@given(
    partial=st.text(min_size=10, max_size=50),
    final=st.text(min_size=10, max_size=50)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_speculative_miss_discard(flash_mode, llm_agent, partial, final):
    """Property 9: Flash_Mode speculative miss discard."""
    assume(partial != final)
    
    call_id = "test-call-002"
    tenant_id = "tenant-001"
    
    # Trigger speculative inference
    state = await flash_mode.on_partial_transcript(
        call_id=call_id,
        partial_transcript=partial,
        confidence=0.9,
        tenant_id=tenant_id,
        llm_agent=llm_agent
    )
    
    # Use different transcript as final
    result = await flash_mode.on_final_transcript(
        call_id=call_id,
        final_transcript=final,
        llm_agent=llm_agent
    )
    
    # Assert speculative miss
    assert result.was_speculative_hit is False
    if result.speculative_state:
        assert result.speculative_state.status == SpeculativeStatus.DISCARDED


# Property 10: Flash_Mode trigger threshold
# Validates: Requirements 4.1, 4.5
@given(confidence=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_trigger_threshold(flash_mode, llm_agent, confidence):
    """Property 10: Flash_Mode trigger threshold."""
    call_id = f"test-call-{confidence}"
    tenant_id = "tenant-001"
    
    state = await flash_mode.on_partial_transcript(
        call_id=call_id,
        partial_transcript="test transcript",
        confidence=confidence,
        tenant_id=tenant_id,
        llm_agent=llm_agent
    )
    
    # Assert speculative inference triggered iff confidence >= 0.85
    if confidence >= 0.85:
        assert state is not None
    else:
        assert state is None


# Property 11: Flash_Mode hit rate logging
# Validates: Requirements 4.7
@given(hit_miss_sequence=st.lists(st.booleans(), min_size=1, max_size=200))
@settings(max_examples=100)
def test_hit_rate_logging_accuracy(flash_mode, hit_miss_sequence):
    """Property 11: Flash_Mode hit rate logging."""
    # Reset counters
    flash_mode.hit_count = 0
    flash_mode.miss_count = 0
    
    # Simulate hit/miss sequence
    for is_hit in hit_miss_sequence:
        if is_hit:
            flash_mode.hit_count += 1
        else:
            flash_mode.miss_count += 1
    
    # Calculate expected rate
    hits = sum(1 for x in hit_miss_sequence if x)
    total = len(hit_miss_sequence)
    expected_rate = hits / total
    
    # Get actual rate
    actual_rate = flash_mode.get_hit_rate()
    
    # Assert accuracy within 0.1%
    assert abs(actual_rate - expected_rate) < 0.001

"""
Property tests for Semantic_VAD.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from src.core.semantic_vad import (
    SemanticVAD,
    AudioFrame,
    VADMode
)


# Property 6: Semantic VAD processing latency
# Validates: Requirements 3.5
@given(
    audio_data=st.binary(min_size=640, max_size=640),  # 320 int16 samples
    timestamp=st.integers(min_value=0, max_value=1000000),
    sequence=st.integers(min_value=0, max_value=10000)
)
@settings(max_examples=100)
def test_vad_processing_latency(audio_data, timestamp, sequence):
    """Property 6: Semantic VAD processing latency."""
    vad = SemanticVAD()
    frame = AudioFrame(
        samples=audio_data,
        timestamp_ms=timestamp,
        sequence_number=sequence
    )
    
    result = vad.process_frame(frame)
    
    # Assert processing latency < 50ms
    assert result.processing_latency_ms < 50.0


# Property 7: VAD end-of-turn suppression window
# Validates: Requirements 3.2
@given(
    intent_score=st.floats(min_value=0.0, max_value=0.29),
    pause_duration=st.integers(min_value=0, max_value=3000)
)
@settings(max_examples=100)
def test_vad_eot_suppression_window(intent_score, pause_duration):
    """Property 7: VAD end-of-turn suppression window."""
    vad = SemanticVAD()
    # Simulate low intent score with silence
    vad.suppression_threshold = 0.3
    
    # Create silent frame
    frame = AudioFrame(
        samples=b'\x00' * 640,
        timestamp_ms=pause_duration,
        sequence_number=0
    )
    
    # Mock intent score
    prosody = {
        "is_speech": False,
        "f0": 0.0,
        "rms_energy": 0.0,
        "speaking_rate": 0.0,
        "pause_duration_ms": float(pause_duration)
    }
    
    is_eot = vad._detect_eot(prosody, intent_score)
    
    # Assert no EOT signal when intent score below threshold
    if pause_duration <= 2000:
        assert not is_eot

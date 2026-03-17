"""
Pytest test scaffold for STT agent — Wave 0 prerequisite.

All tests are marked xfail because the real STT implementation
(Deepgram + Voxtral API calls) is not wired up until Wave 1/2.
This file exists solely to be pytest-discoverable and to define
the acceptance contract for STT-01 through STT-05.
"""

import os
import pytest
import numpy as np
from src.agents.stt_agent import VoxtralModelManager, AudioChunk, LanguageDetector


@pytest.mark.xfail(reason="Not yet implemented — Wave 1/2")
async def test_transcribe_returns_real_string():
    """STT-01: VoxtralModelManager.transcribe() must return real STT output, not mock string."""
    mgr = VoxtralModelManager()

    # 1-second 440Hz sine wave at 16 kHz
    sample_rate = 16000
    t = np.linspace(0, 1.0, sample_rate, endpoint=False)
    audio = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    chunk = AudioChunk(data=audio, sample_rate=sample_rate, timestamp=0.0, chunk_id=0)
    result = await mgr.transcribe(chunk)

    # Must NOT be the hardcoded mock string produced by current placeholder implementation
    assert result.text != f"Transcribed audio chunk {chunk.chunk_id}"
    assert isinstance(result.text, str) and len(result.text) > 0


@pytest.mark.xfail(reason="Not yet implemented — Wave 1/2")
@pytest.mark.skipif(not os.getenv("MISTRAL_API_KEY"), reason="MISTRAL_API_KEY not set")
async def test_voxtral_fallback(monkeypatch):
    """STT-02: When DEEPGRAM_API_KEY is absent, Voxtral (Mistral) must be used as fallback STT."""
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)

    mgr = VoxtralModelManager()

    sample_rate = 16000
    t = np.linspace(0, 1.0, sample_rate, endpoint=False)
    audio = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    chunk = AudioChunk(data=audio, sample_rate=sample_rate, timestamp=0.0, chunk_id=0)
    result = await mgr.transcribe(chunk)

    mock_string = f"Transcribed audio chunk {chunk.chunk_id}"
    assert isinstance(result.text, str) and len(result.text) > 0
    assert result.text != mock_string


@pytest.mark.xfail(reason="Not yet implemented — Wave 1/2")
async def test_language_detection_returns_code():
    """STT-03: LanguageDetector.detect_language(text) must return correct ISO 639-1 language code."""
    detector = LanguageDetector()

    result_en = await detector.detect_language("This is a test sentence in English")
    assert result_en.language == "en"

    result_fr = await detector.detect_language("Bonjour le monde")
    assert result_fr.language == "fr"


@pytest.mark.xfail(reason="Not yet implemented — Wave 1/2")
async def test_pipeline_stt_integration():
    """STT-04: ProcessingPipeline._process_stt() must return real transcription, not hardcoded mock strings."""
    from src.core.processing_pipeline import ProcessingPipeline, ProcessingContext
    from datetime import datetime

    pipeline = ProcessingPipeline()

    context = ProcessingContext(
        session_id="test-session-01",
        user_id=None,
        conversation_id=None,
        language="en",
        accent=None,
        emotion_context=None,
        conversation_history=[],
        user_preferences={},
        processing_metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    audio_bytes = b"\x00" * 10000  # 10 KB of silence-like bytes

    transcription, _confidence = await pipeline._process_stt(audio_bytes, context)

    # Must not be one of the known hardcoded mock strings
    mock_strings = {
        "Hello",
        "Hello, how can I help you today?",
        "Hello, how can I help you today? I'm here to assist with any questions you might have.",
    }
    assert transcription not in mock_strings


@pytest.mark.xfail(reason="Full suite depends on all other tests passing — Wave 1/2", strict=False)
async def test_full_stt_suite_passes():
    """STT-05: Meta-test confirming the file collects and the full suite will pass once implemented."""
    pytest.xfail("Placeholder — full suite not yet implemented")

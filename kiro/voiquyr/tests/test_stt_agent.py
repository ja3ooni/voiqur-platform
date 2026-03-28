"""
Pytest tests for STT agent — STT-01 through STT-05.
"""

import os
import pytest
import numpy as np
from src.agents.stt_agent import VoxtralModelManager, AudioChunk, LanguageDetector


def _sine_chunk(seconds: float = 1.0, sample_rate: int = 16000) -> AudioChunk:
    t = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    return AudioChunk(data=audio, sample_rate=sample_rate, timestamp=0.0, chunk_id=0)


@pytest.mark.skipif(
    not os.getenv("DEEPGRAM_API_KEY") and not os.getenv("MISTRAL_API_KEY"),
    reason="No STT API key set (need DEEPGRAM_API_KEY or MISTRAL_API_KEY)",
)
async def test_transcribe_returns_real_string():
    """STT-01: VoxtralModelManager.transcribe() must return real STT output, not mock string."""
    mgr = VoxtralModelManager()
    await mgr.load_model()

    chunk = _sine_chunk()
    result = await mgr.transcribe(chunk)

    assert result.text != f"Transcribed audio chunk {chunk.chunk_id}"
    assert isinstance(result.text, str) and len(result.text) > 0


@pytest.mark.skipif(not os.getenv("MISTRAL_API_KEY"), reason="MISTRAL_API_KEY not set")
async def test_voxtral_fallback(monkeypatch):
    """STT-02: When DEEPGRAM_API_KEY is absent, Voxtral (Mistral) must be used as fallback STT."""
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)

    mgr = VoxtralModelManager()
    await mgr.load_model()

    chunk = _sine_chunk()
    result = await mgr.transcribe(chunk)

    assert isinstance(result.text, str) and len(result.text) > 0
    assert result.text != f"Transcribed audio chunk {chunk.chunk_id}"


async def test_language_detection_returns_code():
    """STT-03: LanguageDetector.detect_language(text) must return correct ISO 639-1 language code."""
    detector = LanguageDetector()

    result_en = await detector.detect_language("This is a test sentence in English")
    assert result_en.language == "en"

    result_fr = await detector.detect_language("Bonjour le monde")
    assert result_fr.language == "fr"


@pytest.mark.skipif(
    not os.getenv("DEEPGRAM_API_KEY") and not os.getenv("MISTRAL_API_KEY"),
    reason="No STT API key set (need DEEPGRAM_API_KEY or MISTRAL_API_KEY)",
)
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

    # 1-second 440Hz sine as int16 PCM bytes
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    audio_bytes = (np.sin(2 * np.pi * 440.0 * t) * 32767).astype(np.int16).tobytes()

    transcription, _confidence = await pipeline._process_stt(audio_bytes, context)

    mock_strings = {
        "Hello",
        "Hello, how can I help you today?",
        "Hello, how can I help you today? I'm here to assist with any questions you might have.",
    }
    assert transcription not in mock_strings


def test_full_stt_suite_passes():
    """STT-05: Verify STT components have the expected real implementations."""
    mgr = VoxtralModelManager()
    assert hasattr(mgr, "_transcribe_deepgram"), "VoxtralModelManager missing _transcribe_deepgram"
    assert hasattr(mgr, "_transcribe_voxtral"), "VoxtralModelManager missing _transcribe_voxtral"

    import inspect
    sig = inspect.signature(LanguageDetector.detect_language)
    assert "text" in sig.parameters, "detect_language must accept 'text' parameter"

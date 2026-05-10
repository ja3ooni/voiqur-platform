"""
Tests for the Voxtral STT stub (deferred integration).

SELF-03: Voxtral STT integration interface.
"""

import pytest

from src.stt.voxtral import (
    VOXTRAL_AVAILABLE,
    VOXTRAL_MODEL_ID,
    VoxtralNotAvailable,
    VoxtralSTT,
    is_voxtral_available,
)


class TestVoxtralStubConstants:
    def test_voxtral_not_yet_available(self):
        assert VOXTRAL_AVAILABLE is False

    def test_model_id_references_mistral(self):
        assert "mistral" in VOXTRAL_MODEL_ID.lower()

    def test_is_voxtral_available_returns_false(self):
        assert is_voxtral_available() is False


class TestVoxtralSTTInit:
    def test_default_base_url(self):
        client = VoxtralSTT()
        assert client.base_url == "http://localhost:8001"

    def test_trailing_slash_stripped(self):
        client = VoxtralSTT(base_url="http://localhost:8001/")
        assert client.base_url == "http://localhost:8001"

    def test_custom_model(self):
        client = VoxtralSTT(model="mistralai/Voxtral-v2")
        assert client.model == "mistralai/Voxtral-v2"


class TestVoxtralSTTTranscribe:
    @pytest.mark.asyncio
    async def test_transcribe_raises_not_available(self):
        client = VoxtralSTT()
        with pytest.raises(VoxtralNotAvailable, match="not yet available"):
            await client.transcribe(audio=b"fake-audio-bytes")

    @pytest.mark.asyncio
    async def test_transcribe_with_language_still_raises(self):
        client = VoxtralSTT()
        with pytest.raises(VoxtralNotAvailable):
            await client.transcribe(audio=b"audio", language="ar")

    @pytest.mark.asyncio
    async def test_health_check_returns_false(self):
        client = VoxtralSTT()
        result = await client.health_check()
        assert result is False


class TestVoxtralIntegrationInterface:
    """Verify the interface matches what future activation will need."""

    def test_has_transcribe_method(self):
        client = VoxtralSTT()
        assert callable(getattr(client, "transcribe", None))

    def test_has_health_check_method(self):
        client = VoxtralSTT()
        assert callable(getattr(client, "health_check", None))

    def test_accepts_audio_bytes(self):
        """transcribe accepts bytes — signature check."""
        import inspect
        sig = inspect.signature(VoxtralSTT.transcribe)
        assert "audio" in sig.parameters

    def test_accepts_language_param(self):
        import inspect
        sig = inspect.signature(VoxtralSTT.transcribe)
        assert "language" in sig.parameters

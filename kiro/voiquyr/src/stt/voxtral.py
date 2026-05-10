"""
Voxtral STT Integration — Deferred stub.

Requirements: SELF-03

Voxtral is Mistral's upcoming speech-to-text model.
This module provides the integration interface that will be activated
once Mistral releases Voxtral publicly.

Current status: DEFERRED — Voxtral not yet released as of 2026-05-10.

Integration point:
  - Drop-in replacement for the existing Deepgram STT provider
  - Same `transcribe(audio: bytes, language: str) -> str` interface
  - OpenAI-compatible /v1/audio/transcriptions endpoint
  - Expected to run on self-hosted vLLM server alongside Mistral-7B
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Voxtral model ID — will be updated when Mistral releases the model.
VOXTRAL_MODEL_ID = "mistralai/Voxtral-v1"

# Integration status flag — set to True when Voxtral is available.
VOXTRAL_AVAILABLE = False


class VoxtralNotAvailable(Exception):
    """Raised when Voxtral STT is called but not yet available."""
    pass


class VoxtralSTT:
    """
    Voxtral STT client stub.

    Implements the same interface as other STT providers so the
    integration can be activated by swapping the provider class.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        model: str = VOXTRAL_MODEL_ID,
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio bytes to text using Voxtral.

        Args:
            audio: Raw audio bytes (WAV/MP3/OGG).
            language: BCP-47 language code (e.g., "en", "ar"). None = auto-detect.
            prompt: Optional context prompt to improve accuracy.

        Returns:
            Transcribed text.

        Raises:
            VoxtralNotAvailable: Always — until Mistral releases Voxtral.
        """
        if not VOXTRAL_AVAILABLE:
            raise VoxtralNotAvailable(
                "Voxtral STT is not yet available. "
                "Monitor https://mistral.ai for release announcements. "
                "Falling back to configured STT provider."
            )

        # Implementation placeholder — will use vLLM's audio endpoint:
        # POST {base_url}/v1/audio/transcriptions
        # multipart/form-data: file=<audio_bytes>, model=<model>, language=<lang>
        raise NotImplementedError("Voxtral integration pending model release")

    async def health_check(self) -> bool:
        """Return False until Voxtral is available."""
        return VOXTRAL_AVAILABLE


def is_voxtral_available() -> bool:
    """Check whether Voxtral STT integration is active."""
    return VOXTRAL_AVAILABLE

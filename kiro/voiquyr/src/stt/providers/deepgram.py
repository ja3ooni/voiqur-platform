"""
Deepgram Provider - Speech-to-Text using Deepgram Cloud API
"""

import os
import io
from typing import Optional
from deepgram import DeepgramClient


class ConfigurationError(Exception):
    """Configuration error for missing API keys"""
    pass


class DeepgramProvider:
    """Deepgram SDK integration for speech-to-text"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self._client: Optional[DeepgramClient] = None
        
    async def initialize(self) -> None:
        """Initialize Deepgram client"""
        if not self.api_key:
            raise ConfigurationError("DEEPGRAM_API_KEY is required")
        self._client = DeepgramClient(self.api_key)
        
    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> dict:
        """Transcribe audio using Deepgram"""
        if not self._client:
            await self.initialize()
            
        response = self._client.transcription.prerecorded(
            {"buffer": audio_data, "mimetype": "audio/wav"},
            {"model": "nova-2", "smart_format": True}
        )
        
        result = response["results"]["channels"][0]["alternatives"][0]
        return {
            "text": result["transcript"],
            "confidence": result.get("confidence", 0.0),
            "language": result.get("language", "en"),
            "dialect": None,
            "timestamps": [],
            "is_partial": False,
            "chunk_id": 0
        }
        
    async def close(self) -> None:
        """Clean up resources"""
        self._client = None
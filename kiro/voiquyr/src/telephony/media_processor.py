"""
Media Processing Pipeline

Handles codec negotiation, audio format conversion, and media processing.
Implements Requirement 14.1 - Media processing pipeline.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from .base import Codec

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats"""
    PCM = "pcm"
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"
    FLAC = "flac"


@dataclass
class AudioConfig:
    """Audio configuration"""
    sample_rate: int = 8000  # Hz
    channels: int = 1  # Mono
    bit_depth: int = 16  # bits
    codec: Codec = Codec.PCMU
    format: AudioFormat = AudioFormat.PCM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "codec": self.codec.value,
            "format": self.format.value
        }


class CodecNegotiator:
    """
    Handles codec negotiation between endpoints
    
    Selects the best codec based on capabilities and preferences.
    """
    
    # Codec preference order (higher = better)
    CODEC_PREFERENCES = {
        Codec.OPUS: 100,
        Codec.G722: 90,
        Codec.PCMU: 80,
        Codec.PCMA: 75,
        Codec.GSM: 60,
        Codec.G729: 50,
        Codec.SPEEX: 40,
    }
    
    def __init__(self):
        """Initialize codec negotiator"""
        self.logger = logging.getLogger(__name__)
    
    def negotiate_codec(
        self,
        local_codecs: List[Codec],
        remote_codecs: List[Codec]
    ) -> Optional[Codec]:
        """
        Negotiate codec between local and remote endpoints
        
        Args:
            local_codecs: Locally supported codecs
            remote_codecs: Remotely supported codecs
            
        Returns:
            Selected codec or None if no match
        """
        # Find common codecs
        common_codecs = set(local_codecs) & set(remote_codecs)
        
        if not common_codecs:
            self.logger.warning(
                f"No common codecs found. Local: {local_codecs}, "
                f"Remote: {remote_codecs}"
            )
            return None
        
        # Select best codec based on preference
        best_codec = max(
            common_codecs,
            key=lambda c: self.CODEC_PREFERENCES.get(c, 0)
        )
        
        self.logger.info(
            f"Negotiated codec: {best_codec.value} from "
            f"common codecs: {[c.value for c in common_codecs]}"
        )
        
        return best_codec
    
    def get_codec_info(self, codec: Codec) -> Dict[str, Any]:
        """
        Get information about a codec
        
        Args:
            codec: Codec to get info for
            
        Returns:
            Codec information dictionary
        """
        codec_info = {
            Codec.PCMU: {
                "name": "G.711 μ-law",
                "sample_rate": 8000,
                "bit_rate": 64000,
                "quality": "good",
                "bandwidth": "high"
            },
            Codec.PCMA: {
                "name": "G.711 A-law",
                "sample_rate": 8000,
                "bit_rate": 64000,
                "quality": "good",
                "bandwidth": "high"
            },
            Codec.OPUS: {
                "name": "Opus",
                "sample_rate": 48000,
                "bit_rate": 32000,
                "quality": "excellent",
                "bandwidth": "medium"
            },
            Codec.G722: {
                "name": "G.722",
                "sample_rate": 16000,
                "bit_rate": 64000,
                "quality": "very good",
                "bandwidth": "high"
            },
            Codec.G729: {
                "name": "G.729",
                "sample_rate": 8000,
                "bit_rate": 8000,
                "quality": "fair",
                "bandwidth": "low"
            },
            Codec.GSM: {
                "name": "GSM",
                "sample_rate": 8000,
                "bit_rate": 13000,
                "quality": "fair",
                "bandwidth": "low"
            },
            Codec.SPEEX: {
                "name": "Speex",
                "sample_rate": 8000,
                "bit_rate": 24600,
                "quality": "good",
                "bandwidth": "medium"
            }
        }
        
        return codec_info.get(codec, {
            "name": codec.value,
            "sample_rate": 8000,
            "bit_rate": 64000,
            "quality": "unknown",
            "bandwidth": "unknown"
        })


class MediaProcessor:
    """
    Media processing pipeline
    
    Handles audio format conversion, resampling, and processing.
    """
    
    def __init__(self):
        """Initialize media processor"""
        self.logger = logging.getLogger(__name__)
        self.codec_negotiator = CodecNegotiator()
    
    async def convert_audio(
        self,
        audio_data: bytes,
        source_config: AudioConfig,
        target_config: AudioConfig
    ) -> bytes:
        """
        Convert audio from one format to another
        
        Args:
            audio_data: Source audio data
            source_config: Source audio configuration
            target_config: Target audio configuration
            
        Returns:
            Converted audio data
        """
        # TODO: Implement actual audio conversion
        # For now, return as-is
        self.logger.info(
            f"Converting audio from {source_config.codec.value} "
            f"to {target_config.codec.value}"
        )
        return audio_data
    
    async def resample_audio(
        self,
        audio_data: bytes,
        source_rate: int,
        target_rate: int
    ) -> bytes:
        """
        Resample audio to different sample rate
        
        Args:
            audio_data: Source audio data
            source_rate: Source sample rate (Hz)
            target_rate: Target sample rate (Hz)
            
        Returns:
            Resampled audio data
        """
        # TODO: Implement actual resampling
        self.logger.info(
            f"Resampling audio from {source_rate}Hz to {target_rate}Hz"
        )
        return audio_data
    
    async def apply_echo_cancellation(
        self,
        audio_data: bytes,
        config: AudioConfig
    ) -> bytes:
        """
        Apply echo cancellation to audio
        
        Args:
            audio_data: Audio data
            config: Audio configuration
            
        Returns:
            Processed audio data
        """
        # TODO: Implement echo cancellation
        self.logger.debug("Applying echo cancellation")
        return audio_data
    
    async def apply_noise_reduction(
        self,
        audio_data: bytes,
        config: AudioConfig
    ) -> bytes:
        """
        Apply noise reduction to audio
        
        Args:
            audio_data: Audio data
            config: Audio configuration
            
        Returns:
            Processed audio data
        """
        # TODO: Implement noise reduction
        self.logger.debug("Applying noise reduction")
        return audio_data
    
    async def process_audio(
        self,
        audio_data: bytes,
        config: AudioConfig,
        apply_echo_cancel: bool = True,
        apply_noise_reduce: bool = True
    ) -> bytes:
        """
        Process audio with full pipeline
        
        Args:
            audio_data: Audio data
            config: Audio configuration
            apply_echo_cancel: Whether to apply echo cancellation
            apply_noise_reduce: Whether to apply noise reduction
            
        Returns:
            Processed audio data
        """
        processed = audio_data
        
        if apply_echo_cancel:
            processed = await self.apply_echo_cancellation(processed, config)
        
        if apply_noise_reduce:
            processed = await self.apply_noise_reduction(processed, config)
        
        return processed
    
    def get_supported_codecs(self) -> List[Codec]:
        """Get list of supported codecs"""
        return list(Codec)
    
    def get_supported_formats(self) -> List[AudioFormat]:
        """Get list of supported audio formats"""
        return list(AudioFormat)

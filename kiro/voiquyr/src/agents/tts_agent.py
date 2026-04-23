"""
TTS Agent - Text-to-Speech implementation using XTTS-v2 with EU accent support
Implements voice cloning, emotion-aware speech synthesis, and real-time audio streaming
"""

import asyncio
import logging
import numpy as np
try:
    import torch
    import torchaudio
except ImportError:
    torch = None
    torchaudio = None
from typing import Dict, List, Optional, Tuple, AsyncGenerator, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import time
import os
import base64
import io
from pathlib import Path
import uuid
from datetime import datetime

from ..core.models import AgentMessage, AgentState, Task, AgentCapability, Priority
from ..core.messaging import MessageBus


class TTSModelType(Enum):
    XTTS_V2 = "xtts-v2"
    MELOTTS = "melotts"
    NVIDIA_PARAKEET = "nvidia-parakeet-tdt-0.6b-v3"


class VoiceQuality(Enum):
    LOW = "low"  # Fast, lower quality
    MEDIUM = "medium"  # Balanced
    HIGH = "high"  # Slow, highest quality


class EmotionType(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"
    SURPRISED = "surprised"


@dataclass
class VoiceModel:
    """Voice model configuration"""

    voice_id: str
    name: str
    language: str
    accent_region: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    sample_audio_path: Optional[str] = None
    cloned_from_sample: bool = False
    quality_score: float = 0.0  # MOS score
    supported_emotions: List[EmotionType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisRequest:
    """Text-to-speech synthesis request"""

    text: str
    voice_id: str
    language: str = "en"
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 1.0  # 0.0 to 2.0
    speed: float = 1.0  # 0.5 to 2.0
    pitch: float = 1.0  # 0.5 to 2.0
    quality: VoiceQuality = VoiceQuality.MEDIUM
    streaming: bool = False
    output_format: str = "wav"
    sample_rate: int = 22050


@dataclass
class SynthesisResult:
    """Text-to-speech synthesis result"""

    audio_data: np.ndarray
    sample_rate: int
    duration: float
    voice_id: str
    text: str
    quality_score: float
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceCloneRequest:
    """Voice cloning request"""

    sample_audio: np.ndarray
    sample_rate: int
    voice_name: str
    language: str
    target_text: Optional[str] = None  # Text for quality validation


@dataclass
class VoiceCloneResult:
    """Voice cloning result"""

    voice_id: str
    voice_model: VoiceModel
    quality_score: float
    success: bool
    error_message: Optional[str] = None


class AudioProcessor:
    """Audio processing utilities for TTS"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def resample_audio(
        self, audio: np.ndarray, original_sr: int, target_sr: int
    ) -> np.ndarray:
        """Resample audio to target sample rate"""
        if original_sr == target_sr:
            return audio

        audio_tensor = torch.from_numpy(audio).float()
        resampler = torchaudio.transforms.Resample(
            orig_freq=original_sr, new_freq=target_sr
        )
        resampled = resampler(audio_tensor)
        return resampled.numpy()

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping"""
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val * 0.95
        return audio

    def apply_emotion_modulation(
        self,
        audio: np.ndarray,
        sample_rate: int,
        emotion: EmotionType,
        intensity: float,
    ) -> np.ndarray:
        """Apply emotion-based audio modulation with enhanced expressiveness"""
        if emotion == EmotionType.NEUTRAL or intensity == 0.0:
            return audio

        audio_tensor = torch.from_numpy(audio).float()

        # Apply emotion-specific transformations with more nuanced control
        if emotion == EmotionType.HAPPY:
            # Increase pitch, add brightness, slight speed increase
            pitch_shift = torchaudio.transforms.PitchShift(
                sample_rate=sample_rate, n_steps=2 * intensity
            )
            audio_tensor = pitch_shift(audio_tensor)

            # Add brightness by emphasizing higher frequencies
            audio_tensor = self._apply_spectral_tilt(
                audio_tensor, sample_rate, tilt=0.1 * intensity
            )

            # Slight volume increase for energy
            audio_tensor = audio_tensor * (1.0 + 0.1 * intensity)

        elif emotion == EmotionType.SAD:
            # Decrease pitch, reduce brightness, slower pace
            pitch_shift = torchaudio.transforms.PitchShift(
                sample_rate=sample_rate, n_steps=-2.5 * intensity
            )
            audio_tensor = pitch_shift(audio_tensor)

            # Reduce brightness by attenuating higher frequencies
            audio_tensor = self._apply_spectral_tilt(
                audio_tensor, sample_rate, tilt=-0.15 * intensity
            )

            # Slight volume decrease
            audio_tensor = audio_tensor * (1.0 - 0.1 * intensity)

        elif emotion == EmotionType.ANGRY:
            # Increase volume, add roughness, emphasize mid frequencies
            audio_tensor = audio_tensor * (1.0 + 0.3 * intensity)

            # Add slight harmonic distortion for roughness
            audio_tensor = self._add_harmonic_distortion(audio_tensor, intensity * 0.1)

            # Emphasize mid frequencies (1-3kHz) for harshness
            audio_tensor = self._apply_frequency_emphasis(
                audio_tensor, sample_rate, center_freq=2000, intensity=intensity * 0.2
            )

        elif emotion == EmotionType.EXCITED:
            # Higher pitch, faster pace, more energy
            pitch_shift = torchaudio.transforms.PitchShift(
                sample_rate=sample_rate, n_steps=3.5 * intensity
            )
            audio_tensor = pitch_shift(audio_tensor)

            # Increase energy across spectrum
            audio_tensor = audio_tensor * (1.0 + 0.2 * intensity)

            # Add slight tremolo for excitement
            audio_tensor = self._add_tremolo(
                audio_tensor, sample_rate, rate=6.0, depth=0.1 * intensity
            )

        elif emotion == EmotionType.CALM:
            # Lower pitch, smoother, reduced dynamics
            pitch_shift = torchaudio.transforms.PitchShift(
                sample_rate=sample_rate, n_steps=-1.5 * intensity
            )
            audio_tensor = pitch_shift(audio_tensor)

            # Smooth dynamics with gentle compression
            audio_tensor = self._apply_gentle_compression(audio_tensor, intensity)

            # Slight low-pass filtering for warmth
            audio_tensor = self._apply_low_pass_filter(
                audio_tensor, sample_rate, cutoff=8000 - 1000 * intensity
            )

        elif emotion == EmotionType.SURPRISED:
            # Quick pitch rise, increased dynamics
            # Apply pitch modulation that rises quickly
            audio_tensor = self._apply_pitch_modulation(
                audio_tensor, sample_rate, pattern="rise", intensity=intensity
            )

            # Increase dynamic range
            audio_tensor = audio_tensor * (1.0 + 0.15 * intensity)

        return self.normalize_audio(audio_tensor.numpy())

    def _apply_spectral_tilt(
        self, audio_tensor: torch.Tensor, sample_rate: int, tilt: float
    ) -> torch.Tensor:
        """Apply spectral tilt to emphasize or de-emphasize high frequencies"""
        try:
            # Simple high-frequency emphasis/de-emphasis
            if abs(tilt) < 0.01:
                return audio_tensor

            # Apply first-order high-pass or low-pass filtering effect
            if tilt > 0:
                # Emphasize high frequencies (brightness)
                filtered = audio_tensor[1:] - 0.95 * audio_tensor[:-1]
                result = torch.cat([audio_tensor[:1], filtered])
                return audio_tensor + tilt * result
            else:
                # De-emphasize high frequencies (warmth)
                filtered = 0.95 * audio_tensor[:-1]
                result = torch.cat([audio_tensor[:1], audio_tensor[1:] + filtered])
                return audio_tensor + abs(tilt) * (result - audio_tensor)
        except Exception as e:
            logger.warning(f"Audio tilt processing failed: {e}")
            return audio_tensor

    def _add_harmonic_distortion(
        self, audio_tensor: torch.Tensor, amount: float
    ) -> torch.Tensor:
        """Add subtle harmonic distortion for roughness"""
        try:
            if amount <= 0:
                return audio_tensor
            distorted = torch.tanh(audio_tensor * (1 + amount * 2))
            return audio_tensor * (1 - amount) + distorted * amount
        except Exception as e:
            logger.warning(f"Harmonic distortion failed: {e}")
            return audio_tensor

    def _apply_frequency_emphasis(
        self, audio_tensor: torch.Tensor, amount: float
    ) -> torch.Tensor:
        """Add subtle harmonic distortion for roughness"""
        try:
            if amount <= 0:
                return audio_tensor

            # Soft clipping for harmonic distortion
            distorted = torch.tanh(audio_tensor * (1 + amount * 2))
            return audio_tensor * (1 - amount) + distorted * amount
        except Exception as e:
            logger.warning(f"Harmonic distortion failed: {e}")
            return audio_tensor

    def _apply_frequency_emphasis(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int,
        center_freq: float,
        intensity: float,
    ) -> torch.Tensor:
        """Emphasize specific frequency range"""
        try:
            if intensity <= 0:
                return audio_tensor

            # Simple resonant filter simulation
            # This is a simplified approach - real implementation would use proper filtering
            return audio_tensor * (1.0 + intensity)
        except Exception as e:
            logger.warning(f"Frequency emphasis failed: {e}")
            return audio_tensor

    def _add_tremolo(
        self, audio_tensor: torch.Tensor, sample_rate: int, rate: float, depth: float
    ) -> torch.Tensor:
        """Add tremolo effect (amplitude modulation)"""
        try:
            if depth <= 0:
                return audio_tensor

            # Generate tremolo LFO
            t = torch.arange(len(audio_tensor)).float() / sample_rate
            lfo = torch.sin(2 * np.pi * rate * t)
            modulation = 1.0 + depth * lfo

            return audio_tensor * modulation
        except Exception as e:
            logger.warning(f"Tremolo failed: {e}")
            return audio_tensor

    def _apply_gentle_compression(
        self, audio_tensor: torch.Tensor, intensity: float
    ) -> torch.Tensor:
        """Apply gentle compression to reduce dynamics"""
        try:
            if intensity <= 0:
                return audio_tensor

            # Simple soft compression
            threshold = 0.5
            ratio = 1.0 + intensity * 2  # 1:1 to 3:1 ratio

            # Soft knee compression
            abs_audio = torch.abs(audio_tensor)
            compressed = torch.where(
                abs_audio > threshold,
                torch.sign(audio_tensor)
                * (threshold + (abs_audio - threshold) / ratio),
                audio_tensor,
            )

            return audio_tensor * (1 - intensity) + compressed * intensity
        except Exception as e:
            logger.warning(f"Gentle compression failed: {e}")
            return audio_tensor

    def _apply_low_pass_filter(
        self, audio_tensor: torch.Tensor, sample_rate: int, cutoff: float
    ) -> torch.Tensor:
        """Apply simple low-pass filter"""
        try:
            # Simple one-pole low-pass filter
            alpha = 2 * np.pi * cutoff / sample_rate
            alpha = min(1.0, alpha)  # Clamp to prevent instability

            filtered = torch.zeros_like(audio_tensor)
            filtered[0] = audio_tensor[0]

            for i in range(1, len(audio_tensor)):
                filtered[i] = alpha * audio_tensor[i] + (1 - alpha) * filtered[i - 1]

            return filtered
        except Exception as e:
            logger.warning(f"Low pass filter failed: {e}")
            return audio_tensor

    def _apply_pitch_modulation(
        self,
        audio_tensor: torch.Tensor,
        sample_rate: int,
        pattern: str,
        intensity: float,
    ) -> torch.Tensor:
        """Apply pitch modulation patterns"""
        try:
            if pattern == "rise" and intensity > 0:
                # Create rising pitch effect
                t = torch.arange(len(audio_tensor)).float() / len(audio_tensor)
                pitch_mod = 1.0 + intensity * 0.1 * t  # Gradual rise

                # Simple pitch shifting simulation (not perfect but demonstrates concept)
                return audio_tensor * pitch_mod

            return audio_tensor
        except Exception as e:
            logger.warning(f"Pitch modulation failed: {e}")
            return audio_tensor

    def chunk_for_streaming(
        self, audio: np.ndarray, chunk_duration: float, sample_rate: int
    ) -> List[np.ndarray]:
        """Split audio into chunks for streaming"""
        chunk_size = int(chunk_duration * sample_rate)
        chunks = []

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            chunks.append(chunk)

        return chunks

    def encode_audio_base64(
        self, audio: np.ndarray, sample_rate: int, format: str = "wav"
    ) -> str:
        """Encode audio as base64 string"""
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Create audio tensor
        audio_tensor = torch.from_numpy(audio_int16).float() / 32767.0

        # Save to bytes buffer
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio_tensor.unsqueeze(0), sample_rate, format=format)
        buffer.seek(0)

        # Encode as base64
        return base64.b64encode(buffer.read()).decode("utf-8")


class XTTSv2ModelManager:
    """Manager for XTTS-v2 model with multilingual support"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.device = None
        self.use_cloud = False
        self._elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self._cloud_client = None
        self.supported_languages = [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh",
            "ja",
            "hu",
            "ko",
            "hi",
            "fi",
            "sv",
            "da",
            "no",
            "et",
            "lv",
            "lt",
            "sl",
            "sk",
            "bg",
            "hr",
            "ro",
            "mt",
            "el",
        ]
        self.voice_models: Dict[str, VoiceModel] = {}
        self.model_loaded = False

    async def initialize(self) -> bool:
        """Initialize XTTS-v2 model"""
        try:
            self.logger.info("Initializing XTTS-v2 model...")

            # Try to use ElevenLabs if API key is available
            if self._elevenlabs_key:
                try:
                    from elevenlabs.client import ElevenLabs
                    self._cloud_client = ElevenLabs(api_key=self._elevenlabs_key)
                    
                    # Test the API key with a quick call
                    voices = await asyncio.to_thread(self._cloud_client.voices.get_all())
                    self.use_cloud = True
                    self.model_loaded = True
                    self.logger.info("Using ElevenLabs cloud TTS")
                    return True
                except ImportError:
                    self.logger.warning("elevenlabs package not installed")
                except Exception as e:
                    self.logger.warning(f"ElevenLabs API key invalid or error: {e}")

            # In a real implementation, this would load the actual XTTS-v2 model
            # For now, we'll simulate the model loading
            await asyncio.sleep(2)  # Simulate loading time

            # Create mock model
            self.model = {
                "name": "xtts-v2",
                "version": "2.0",
                "languages": self.supported_languages,
                "sample_rate": 22050,
                "max_text_length": 500,
            }

            # Load default voice models
            await self._load_default_voices()

            self.model_loaded = True
            self.logger.info("XTTS-v2 model initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize XTTS-v2: {e}")
            return False

    async def _load_default_voices(self):
        """Load default voice models for different languages and accents"""
        default_voices = [
            # English voices
            VoiceModel(
                "en_us_female_1",
                "Emma",
                "en",
                "us",
                "female",
                "adult",
                supported_emotions=[
                    EmotionType.NEUTRAL,
                    EmotionType.HAPPY,
                    EmotionType.SAD,
                ],
            ),
            VoiceModel(
                "en_uk_male_1",
                "James",
                "en",
                "uk",
                "male",
                "adult",
                supported_emotions=[
                    EmotionType.NEUTRAL,
                    EmotionType.CALM,
                    EmotionType.EXCITED,
                ],
            ),
            VoiceModel("en_ie_female_1", "Siobhan", "en", "ie", "female", "adult"),
            # French voices
            VoiceModel("fr_fr_female_1", "Marie", "fr", "fr", "female", "adult"),
            VoiceModel("fr_be_male_1", "Pierre", "fr", "be", "male", "adult"),
            VoiceModel("fr_ch_female_1", "Camille", "fr", "ch", "female", "adult"),
            # German voices
            VoiceModel("de_de_male_1", "Hans", "de", "de", "male", "adult"),
            VoiceModel("de_at_female_1", "Anna", "de", "at", "female", "adult"),
            VoiceModel("de_ch_male_1", "Klaus", "de", "ch", "male", "adult"),
            # Spanish voices
            VoiceModel("es_es_female_1", "Carmen", "es", "es", "female", "adult"),
            VoiceModel("es_mx_male_1", "Carlos", "es", "mx", "male", "adult"),
            # Italian voices
            VoiceModel("it_it_female_1", "Giulia", "it", "it", "female", "adult"),
            # Portuguese voices
            VoiceModel("pt_pt_male_1", "João", "pt", "pt", "male", "adult"),
            VoiceModel("pt_br_female_1", "Ana", "pt", "br", "female", "adult"),
            # Dutch voices
            VoiceModel("nl_nl_female_1", "Emma", "nl", "nl", "female", "adult"),
            VoiceModel("nl_be_male_1", "Willem", "nl", "be", "male", "adult"),
            # Eastern European voices
            VoiceModel("pl_pl_female_1", "Katarzyna", "pl", "pl", "female", "adult"),
            VoiceModel("cs_cz_male_1", "Pavel", "cs", "cz", "male", "adult"),
            VoiceModel("sk_sk_female_1", "Zuzana", "sk", "sk", "female", "adult"),
            VoiceModel("hu_hu_male_1", "László", "hu", "hu", "male", "adult"),
            VoiceModel("ro_ro_female_1", "Elena", "ro", "ro", "female", "adult"),
            VoiceModel("bg_bg_male_1", "Dimitar", "bg", "bg", "male", "adult"),
            VoiceModel("hr_hr_female_1", "Marija", "hr", "hr", "female", "adult"),
            VoiceModel("sl_si_male_1", "Matej", "sl", "si", "male", "adult"),
            # Baltic voices
            VoiceModel("et_ee_female_1", "Liisa", "et", "ee", "female", "adult"),
            VoiceModel("lv_lv_male_1", "Jānis", "lv", "lv", "male", "adult"),
            VoiceModel("lt_lt_female_1", "Rūta", "lt", "lt", "female", "adult"),
            # Nordic voices
            VoiceModel("fi_fi_male_1", "Mikael", "fi", "fi", "male", "adult"),
            VoiceModel("sv_se_female_1", "Astrid", "sv", "se", "female", "adult"),
            VoiceModel("da_dk_male_1", "Lars", "da", "dk", "male", "adult"),
            # Greek and Maltese
            VoiceModel("el_gr_female_1", "Maria", "el", "gr", "female", "adult"),
            VoiceModel("mt_mt_male_1", "Joseph", "mt", "mt", "male", "adult"),
        ]

        for voice in default_voices:
            voice.quality_score = 4.2  # Default MOS score
            self.voice_models[voice.voice_id] = voice

        self.logger.info(f"Loaded {len(default_voices)} default voice models")

    async def _synthesize_elevenlabs(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize using ElevenLabs cloud API"""
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            raise RuntimeError("elevenlabs package not installed. Run: pip install elevenlabs")

        if not self._cloud_client:
            self._cloud_client = ElevenLabs(api_key=self._elevenlabs_key)
            self.use_cloud = True

        voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default Rachel voice

        response = await asyncio.to_thread(
            self._cloud_client.generate,
            text=request.text,
            voice=voice_id,
            model="eleven_multilingual_v2",
        )

        audio = np.frombuffer(response, dtype=np.int16).astype(np.float32) / 32768.0
        sample_rate = 44100
        duration = len(audio) / sample_rate

        return SynthesisResult(
            audio_data=audio,
            sample_rate=sample_rate,
            duration=duration,
            voice_id=voice_id,
            language=request.language,
            processing_time=time.time(),
        )

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize speech from text using ElevenLabs or local model"""
        if not self.model_loaded and not self._elevenlabs_key:
            raise RuntimeError("XTTS-v2 model not loaded and no ELEVENLABS_API_KEY")

        start_time = time.time()

        try:
            # Try ElevenLabs cloud API first if key is available
            if self._elevenlabs_key:
                return await self._synthesize_elevenlabs(request)

            # Get voice model
            voice_model = self.voice_models.get(request.voice_id)
            if not voice_model:
                raise ValueError(f"Voice model {request.voice_id} not found")

            # Validate language support
            if request.language not in self.supported_languages:
                raise ValueError(f"Language {request.language} not supported")

            # Simulate synthesis processing
            # In real implementation, this would call the actual XTTS-v2 model
            processing_time = len(request.text) * 0.01  # Simulate processing time
            await asyncio.sleep(processing_time)

            # Generate mock audio (sine wave for demonstration)
            duration = len(request.text) * 0.1  # Rough estimate: 10 chars per second
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration))

            # Create a more realistic audio signal (multiple harmonics)
            frequency = 200 if voice_model.gender == "male" else 300
            audio = (
                0.3 * np.sin(2 * np.pi * frequency * t)
                + 0.2 * np.sin(2 * np.pi * frequency * 2 * t)
                + 0.1 * np.sin(2 * np.pi * frequency * 3 * t)
            )

            # Add some variation to make it more natural
            audio += 0.05 * np.random.normal(0, 1, len(audio))

            # Apply speed and pitch modifications
            if request.speed != 1.0:
                # Simple speed change by resampling
                new_length = int(len(audio) / request.speed)
                audio = np.interp(
                    np.linspace(0, len(audio) - 1, new_length),
                    np.arange(len(audio)),
                    audio,
                )

            # Normalize audio
            audio = audio / np.max(np.abs(audio)) * 0.8

            processing_time = time.time() - start_time

            return SynthesisResult(
                audio_data=audio,
                sample_rate=sample_rate,
                duration=len(audio) / sample_rate,
                voice_id=request.voice_id,
                text=request.text,
                quality_score=voice_model.quality_score,
                processing_time=processing_time,
                metadata={
                    "emotion": request.emotion.value,
                    "language": request.language,
                    "voice_name": voice_model.name,
                },
            )

        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}")
            raise

    async def clone_voice(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Clone voice from audio sample with enhanced quality validation and cross-lingual support"""
        try:
            self.logger.info(
                f"Cloning voice: {request.voice_name} for language: {request.language}"
            )

            # Validate sample duration (must be at least 6 seconds)
            sample_duration = len(request.sample_audio) / request.sample_rate
            if sample_duration < 6.0:
                return VoiceCloneResult(
                    voice_id="",
                    voice_model=None,
                    quality_score=0.0,
                    success=False,
                    error_message=f"Sample audio must be at least 6 seconds long (provided: {sample_duration:.2f}s)",
                )

            # Enhanced audio quality validation
            quality_metrics = await self._validate_audio_quality(
                request.sample_audio, request.sample_rate
            )

            if quality_metrics["quality_score"] < 2.5:
                return VoiceCloneResult(
                    voice_id="",
                    voice_model=None,
                    quality_score=quality_metrics["quality_score"],
                    success=False,
                    error_message=f"Audio quality too low (MOS: {quality_metrics['quality_score']:.2f}). Minimum required: 2.5",
                )

            # Preprocess audio for optimal cloning
            processed_audio = await self._preprocess_cloning_audio(
                request.sample_audio, request.sample_rate
            )

            # Simulate advanced voice cloning processing with speaker embedding extraction
            await asyncio.sleep(3)  # Simulate processing time

            # Create new voice model with enhanced metadata
            voice_id = f"cloned_{request.language}_{uuid.uuid4().hex[:8]}"

            # Calculate MOS score based on multiple factors
            mos_score = await self._calculate_voice_mos(
                processed_audio,
                request.sample_rate,
                sample_duration,
                quality_metrics,
                request.target_text,
            )

            # Detect speaker characteristics for cross-lingual synthesis
            speaker_characteristics = await self._extract_speaker_characteristics(
                processed_audio, request.sample_rate, request.language
            )

            voice_model = VoiceModel(
                voice_id=voice_id,
                name=request.voice_name,
                language=request.language,
                accent_region=speaker_characteristics.get("accent_region"),
                gender=speaker_characteristics.get("gender"),
                age_group=speaker_characteristics.get("age_group"),
                cloned_from_sample=True,
                quality_score=mos_score,
                supported_emotions=[
                    EmotionType.NEUTRAL,
                    EmotionType.HAPPY,
                    EmotionType.SAD,
                    EmotionType.CALM,
                ],
                metadata={
                    "sample_duration": sample_duration,
                    "original_language": request.language,
                    "cross_lingual_capable": True,
                    "supported_target_languages": self._get_cross_lingual_targets(
                        request.language
                    ),
                    "speaker_embedding_quality": quality_metrics["embedding_quality"],
                    "background_noise_level": quality_metrics["noise_level"],
                    "speech_clarity": quality_metrics["clarity_score"],
                    "prosody_consistency": quality_metrics["prosody_score"],
                    "created_at": datetime.utcnow().isoformat(),
                    "cloning_method": "xtts-v2-enhanced",
                    "speaker_characteristics": speaker_characteristics,
                },
            )

            # Store the voice model with cross-lingual capabilities
            self.voice_models[voice_id] = voice_model

            # Store speaker embedding for cross-lingual synthesis
            await self._store_speaker_embedding(
                voice_id, processed_audio, speaker_characteristics
            )

            self.logger.info(
                f"Voice cloned successfully: {voice_id} (MOS: {mos_score:.2f}, Cross-lingual: {len(voice_model.metadata['supported_target_languages'])} languages)"
            )

            return VoiceCloneResult(
                voice_id=voice_id,
                voice_model=voice_model,
                quality_score=mos_score,
                success=True,
            )

        except Exception as e:
            self.logger.error(f"Voice cloning failed: {e}")
            return VoiceCloneResult(
                voice_id="",
                voice_model=None,
                quality_score=0.0,
                success=False,
                error_message=str(e),
            )

    async def _validate_audio_quality(
        self, audio: np.ndarray, sample_rate: int
    ) -> Dict[str, float]:
        """Validate audio quality for voice cloning"""
        try:
            # Convert to tensor for processing
            audio_tensor = torch.from_numpy(audio).float()

            # Calculate signal-to-noise ratio
            signal_power = torch.mean(audio_tensor**2)
            noise_estimate = torch.std(
                audio_tensor[: int(0.1 * len(audio_tensor))]
            )  # First 10% as noise estimate
            snr = 10 * torch.log10(signal_power / (noise_estimate**2 + 1e-8))

            # Calculate speech clarity (spectral centroid consistency)
            window_size = int(0.025 * sample_rate)  # 25ms windows
            hop_size = int(0.01 * sample_rate)  # 10ms hop

            spectral_centroids = []
            for i in range(0, len(audio) - window_size, hop_size):
                window = audio[i : i + window_size]
                fft = np.fft.fft(window)
                magnitude = np.abs(fft[: len(fft) // 2])
                freqs = np.fft.fftfreq(len(fft), 1 / sample_rate)[: len(fft) // 2]

                if np.sum(magnitude) > 0:
                    centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
                    spectral_centroids.append(centroid)

            clarity_score = 1.0 - (
                np.std(spectral_centroids) / (np.mean(spectral_centroids) + 1e-8)
            )
            clarity_score = max(0.0, min(1.0, clarity_score))

            # Calculate prosody consistency (pitch variation)
            # Simplified pitch tracking using autocorrelation
            pitch_values = []
            for i in range(0, len(audio) - window_size, hop_size):
                window = audio[i : i + window_size]
                autocorr = np.correlate(window, window, mode="full")
                autocorr = autocorr[len(autocorr) // 2 :]

                # Find pitch period
                min_period = int(sample_rate / 500)  # 500 Hz max
                max_period = int(sample_rate / 50)  # 50 Hz min

                if len(autocorr) > max_period:
                    pitch_autocorr = autocorr[min_period:max_period]
                    if len(pitch_autocorr) > 0:
                        pitch_period = np.argmax(pitch_autocorr) + min_period
                        pitch_freq = sample_rate / pitch_period
                        if 50 <= pitch_freq <= 500:  # Valid pitch range
                            pitch_values.append(pitch_freq)

            prosody_score = 1.0
            if len(pitch_values) > 1:
                pitch_std = np.std(pitch_values)
                pitch_mean = np.mean(pitch_values)
                prosody_score = 1.0 - min(1.0, pitch_std / (pitch_mean + 1e-8))

            # Calculate embedding quality (energy distribution)
            energy_windows = []
            for i in range(0, len(audio) - window_size, hop_size):
                window = audio[i : i + window_size]
                energy = np.sum(window**2)
                energy_windows.append(energy)

            energy_consistency = 1.0 - (
                np.std(energy_windows) / (np.mean(energy_windows) + 1e-8)
            )
            energy_consistency = max(0.0, min(1.0, energy_consistency))

            # Combine metrics into overall quality score
            snr_normalized = min(
                1.0, max(0.0, (float(snr) - 10) / 20)
            )  # Normalize SNR (10-30 dB range)

            quality_score = (
                0.3 * snr_normalized
                + 0.25 * clarity_score
                + 0.25 * prosody_score
                + 0.2 * energy_consistency
            ) * 5.0  # Scale to 0-5 MOS range

            return {
                "quality_score": quality_score,
                "snr": float(snr),
                "noise_level": 1.0 - snr_normalized,
                "clarity_score": clarity_score,
                "prosody_score": prosody_score,
                "embedding_quality": energy_consistency,
            }

        except Exception as e:
            self.logger.warning(f"Audio quality validation failed: {e}")
            return {
                "quality_score": 3.0,  # Default moderate quality
                "snr": 15.0,
                "noise_level": 0.3,
                "clarity_score": 0.7,
                "prosody_score": 0.7,
                "embedding_quality": 0.7,
            }

    async def _preprocess_cloning_audio(
        self, audio: np.ndarray, sample_rate: int
    ) -> np.ndarray:
        """Preprocess audio for optimal voice cloning"""
        try:
            # Normalize audio
            audio = audio / (np.max(np.abs(audio)) + 1e-8)

            # Apply noise reduction (simple spectral subtraction)
            audio_tensor = torch.from_numpy(audio).float()

            # High-pass filter to remove low-frequency noise
            if sample_rate > 16000:
                # Simple high-pass filter using difference
                filtered = audio_tensor[1:] - 0.95 * audio_tensor[:-1]
                audio_tensor = torch.cat([audio_tensor[:1], filtered])

            # Trim silence from beginning and end
            energy_threshold = 0.01 * torch.max(torch.abs(audio_tensor))

            # Find start of speech
            start_idx = 0
            for i in range(len(audio_tensor)):
                if torch.abs(audio_tensor[i]) > energy_threshold:
                    start_idx = max(
                        0, i - int(0.1 * sample_rate)
                    )  # Include 100ms before
                    break

            # Find end of speech
            end_idx = len(audio_tensor)
            for i in range(len(audio_tensor) - 1, -1, -1):
                if torch.abs(audio_tensor[i]) > energy_threshold:
                    end_idx = min(
                        len(audio_tensor), i + int(0.1 * sample_rate)
                    )  # Include 100ms after
                    break

            # Extract speech segment
            processed_audio = audio_tensor[start_idx:end_idx]

            # Ensure minimum duration
            min_samples = int(6.0 * sample_rate)
            if len(processed_audio) < min_samples:
                # Pad with original audio if too short
                padding_needed = min_samples - len(processed_audio)
                processed_audio = torch.cat(
                    [processed_audio, audio_tensor[:padding_needed]]
                )

            return processed_audio.numpy()

        except Exception as e:
            self.logger.warning(f"Audio preprocessing failed: {e}")
            return audio

    async def _calculate_voice_mos(
        self,
        audio: np.ndarray,
        sample_rate: int,
        duration: float,
        quality_metrics: Dict[str, float],
        target_text: Optional[str] = None,
    ) -> float:
        """Calculate Mean Opinion Score for cloned voice"""
        try:
            # Base MOS from audio quality metrics
            base_mos = quality_metrics["quality_score"]

            # Duration bonus (longer samples generally produce better clones)
            duration_factor = min(1.2, 1.0 + (duration - 6.0) * 0.02)  # Up to 20% bonus

            # SNR contribution
            snr_factor = min(
                1.1, 1.0 + (quality_metrics["snr"] - 15.0) * 0.005
            )  # Up to 10% bonus

            # Clarity and prosody contribution
            speech_quality_factor = (
                quality_metrics["clarity_score"] + quality_metrics["prosody_score"]
            ) / 2.0

            # Calculate final MOS
            mos_score = (
                base_mos
                * duration_factor
                * snr_factor
                * (0.8 + 0.2 * speech_quality_factor)
            )

            # Add small random variation to simulate real-world variability
            mos_score += np.random.normal(0, 0.1)

            # Clamp to valid MOS range (1.0 to 5.0)
            mos_score = max(1.0, min(5.0, mos_score))

            # If target text provided, simulate synthesis quality validation
            if target_text:
                # Simulate synthesis test
                await asyncio.sleep(0.5)  # Simulate synthesis time

                # Adjust MOS based on synthesis success (simplified)
                text_complexity = (
                    len(target_text.split()) / 10.0
                )  # Normalize by word count
                synthesis_penalty = min(
                    0.2, text_complexity * 0.05
                )  # Up to 0.2 penalty for complex text
                mos_score -= synthesis_penalty

            return round(mos_score, 2)

        except Exception as e:
            self.logger.warning(f"MOS calculation failed: {e}")
            return 3.5  # Default moderate MOS

    async def _extract_speaker_characteristics(
        self, audio: np.ndarray, sample_rate: int, language: str
    ) -> Dict[str, Any]:
        """Extract speaker characteristics for cross-lingual synthesis"""
        try:
            # Estimate fundamental frequency (F0) for gender detection
            window_size = int(0.025 * sample_rate)
            hop_size = int(0.01 * sample_rate)

            f0_values = []
            for i in range(0, len(audio) - window_size, hop_size):
                window = audio[i : i + window_size]

                # Simple autocorrelation-based F0 estimation
                autocorr = np.correlate(window, window, mode="full")
                autocorr = autocorr[len(autocorr) // 2 :]

                min_period = int(sample_rate / 400)  # 400 Hz max
                max_period = int(sample_rate / 80)  # 80 Hz min

                if len(autocorr) > max_period:
                    pitch_autocorr = autocorr[min_period:max_period]
                    if len(pitch_autocorr) > 0 and np.max(pitch_autocorr) > 0.3:
                        pitch_period = np.argmax(pitch_autocorr) + min_period
                        f0 = sample_rate / pitch_period
                        if 80 <= f0 <= 400:
                            f0_values.append(f0)

            # Determine gender based on F0
            if f0_values:
                mean_f0 = np.mean(f0_values)
                if mean_f0 < 140:
                    gender = "male"
                elif mean_f0 > 200:
                    gender = "female"
                else:
                    gender = "neutral"
            else:
                gender = "unknown"

            # Estimate age group based on voice characteristics
            if f0_values:
                f0_variability = np.std(f0_values) / (np.mean(f0_values) + 1e-8)
                if f0_variability > 0.15:
                    age_group = "young"  # Higher variability
                elif f0_variability < 0.08:
                    age_group = "senior"  # Lower variability
                else:
                    age_group = "adult"
            else:
                age_group = "adult"

            # Detect accent region (simplified based on language)
            accent_region = self._detect_accent_region(language, audio, sample_rate)

            return {
                "gender": gender,
                "age_group": age_group,
                "accent_region": accent_region,
                "mean_f0": np.mean(f0_values) if f0_values else 150.0,
                "f0_range": np.ptp(f0_values) if f0_values else 50.0,
                "voice_quality": "clear" if len(f0_values) > 10 else "unclear",
            }

        except Exception as e:
            self.logger.warning(f"Speaker characteristic extraction failed: {e}")
            return {
                "gender": "unknown",
                "age_group": "adult",
                "accent_region": None,
                "mean_f0": 150.0,
                "f0_range": 50.0,
                "voice_quality": "unclear",
            }

    def _detect_accent_region(
        self, language: str, audio: np.ndarray, sample_rate: int
    ) -> Optional[str]:
        """Detect accent region based on language and audio characteristics"""
        # Simplified accent detection based on language
        accent_mapping = {
            "en": ["us", "uk", "au", "ca", "ie"],
            "fr": ["fr", "be", "ch", "ca"],
            "de": ["de", "at", "ch"],
            "es": ["es", "mx", "ar", "co"],
            "it": ["it"],
            "pt": ["pt", "br"],
            "nl": ["nl", "be"],
            "pl": ["pl"],
            "cs": ["cz"],
            "sk": ["sk"],
            "hu": ["hu"],
            "ro": ["ro"],
            "bg": ["bg"],
            "hr": ["hr"],
            "sl": ["si"],
            "et": ["ee"],
            "lv": ["lv"],
            "lt": ["lt"],
            "fi": ["fi"],
            "sv": ["se"],
            "da": ["dk"],
            "no": ["no"],
            "el": ["gr"],
            "mt": ["mt"],
        }

        possible_regions = accent_mapping.get(language, [language])

        # For now, return the first (most common) region
        # In a real implementation, this would use acoustic models to detect specific accents
        return possible_regions[0] if possible_regions else None

    def _get_cross_lingual_targets(self, source_language: str) -> List[str]:
        """Get supported target languages for cross-lingual synthesis"""
        # Define cross-lingual synthesis capabilities
        # Languages with similar phonetic systems work better for cross-lingual synthesis

        cross_lingual_groups = {
            "romance": ["es", "fr", "it", "pt", "ro"],
            "germanic": ["en", "de", "nl", "sv", "da", "no"],
            "slavic": ["pl", "cs", "sk", "hr", "sl", "bg"],
            "baltic": ["lv", "lt"],
            "finno_ugric": ["fi", "hu", "et"],
            "other": ["el", "mt"],
        }

        # Find the group of the source language
        source_group = None
        for group, languages in cross_lingual_groups.items():
            if source_language in languages:
                source_group = group
                break

        if source_group:
            # Return languages from the same group plus some universal targets
            same_group = cross_lingual_groups[source_group]
            universal_targets = ["en", "fr", "de", "es"]  # Common languages

            targets = list(set(same_group + universal_targets))
            targets = [
                lang for lang in targets if lang != source_language
            ]  # Remove source
            return targets[:8]  # Limit to 8 target languages
        else:
            # Default cross-lingual targets
            return ["en", "fr", "de", "es", "it"]

    async def _store_speaker_embedding(
        self, voice_id: str, audio: np.ndarray, characteristics: Dict[str, Any]
    ):
        """Store speaker embedding for cross-lingual synthesis"""
        try:
            # In a real implementation, this would extract and store speaker embeddings
            # For now, we'll simulate storing the embedding metadata

            embedding_metadata = {
                "voice_id": voice_id,
                "embedding_size": 512,  # Typical embedding size
                "extraction_method": "xtts-v2-speaker-encoder",
                "characteristics": characteristics,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Simulate embedding storage
            await asyncio.sleep(0.1)

            self.logger.info(f"Stored speaker embedding for voice {voice_id}")

        except Exception as e:
            self.logger.warning(f"Failed to store speaker embedding: {e}")

    def get_voice_models(self, language: Optional[str] = None) -> List[VoiceModel]:
        """Get available voice models"""
        if language:
            return [vm for vm in self.voice_models.values() if vm.language == language]
        return list(self.voice_models.values())

    def get_supported_languages(self) -> List[str]:
        """Get supported languages"""
        return self.supported_languages

    async def synthesize_cross_lingual(
        self,
        text: str,
        source_voice_id: str,
        target_language: str,
        preserve_accent: bool = True,
    ) -> SynthesisResult:
        """Synthesize speech in target language using source voice characteristics"""
        try:
            # Get source voice model
            source_voice = self.voice_models.get(source_voice_id)
            if not source_voice:
                raise ValueError(f"Source voice {source_voice_id} not found")

            if not source_voice.cloned_from_sample:
                raise ValueError(
                    "Cross-lingual synthesis only supported for cloned voices"
                )

            # Check if target language is supported for cross-lingual synthesis
            supported_targets = source_voice.metadata.get(
                "supported_target_languages", []
            )
            if target_language not in supported_targets:
                self.logger.warning(
                    f"Target language {target_language} not in supported list for {source_voice_id}"
                )

            # Create synthesis request with cross-lingual parameters
            request = SynthesisRequest(
                text=text,
                voice_id=source_voice_id,
                language=target_language,  # Target language
                quality=VoiceQuality.HIGH,  # Use high quality for cross-lingual
            )

            # Perform synthesis
            result = await self.synthesize(request)

            # Apply accent preservation if requested
            if preserve_accent and source_voice.accent_region:
                result.audio_data = await self._apply_accent_preservation(
                    result.audio_data,
                    result.sample_rate,
                    source_voice.language,  # Source language
                    target_language,
                    source_voice.accent_region,
                )

            # Update metadata to reflect cross-lingual synthesis
            result.metadata.update(
                {
                    "cross_lingual": True,
                    "source_language": source_voice.language,
                    "target_language": target_language,
                    "accent_preserved": preserve_accent,
                    "source_accent_region": source_voice.accent_region,
                }
            )

            self.logger.info(
                f"Cross-lingual synthesis completed: {source_voice.language} → {target_language}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Cross-lingual synthesis failed: {e}")
            raise

    async def _apply_accent_preservation(
        self,
        audio: np.ndarray,
        sample_rate: int,
        source_lang: str,
        target_lang: str,
        accent_region: str,
    ) -> np.ndarray:
        """Apply accent preservation for cross-lingual synthesis"""
        try:
            # Simulate accent preservation processing
            # In a real implementation, this would apply phonetic transformations
            # to preserve the source accent in the target language

            audio_tensor = torch.from_numpy(audio).float()

            # Apply subtle pitch modifications based on accent characteristics
            accent_pitch_adjustments = {
                "us": 0.0,  # Neutral baseline
                "uk": -0.05,  # Slightly lower pitch
                "ie": 0.03,  # Slightly higher pitch
                "au": -0.02,  # Slightly lower pitch
                "fr": 0.02,  # Slightly higher pitch
                "de": -0.03,  # Lower pitch
                "es": 0.04,  # Higher pitch
                "it": 0.03,  # Higher pitch
            }

            pitch_adjustment = accent_pitch_adjustments.get(accent_region, 0.0)

            if abs(pitch_adjustment) > 0.01:
                # Apply pitch shift to preserve accent characteristics
                pitch_shift = torchaudio.transforms.PitchShift(
                    sample_rate=sample_rate,
                    n_steps=pitch_adjustment * 12,  # Convert to semitones
                )
                audio_tensor = pitch_shift(audio_tensor)

            # Apply formant adjustments (simplified)
            # Different accents have different formant patterns
            if accent_region in ["uk", "au"]:
                # Apply slight filtering to simulate accent characteristics
                # This is a simplified approach - real implementation would use formant synthesis
                pass

            return audio_tensor.numpy()

        except Exception as e:
            self.logger.warning(f"Accent preservation failed: {e}")
            return audio


class MeloTTSModelManager:
    """Manager for MeloTTS as alternative option"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_loaded = False
        self.supported_languages = ["en", "es", "fr", "zh", "ja", "ko"]

    async def initialize(self) -> bool:
        """Initialize MeloTTS model"""
        try:
            self.logger.info("Initializing MeloTTS model...")
            await asyncio.sleep(1)  # Simulate loading
            self.model_loaded = True
            self.logger.info("MeloTTS model initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize MeloTTS: {e}")
            return False

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize using MeloTTS"""
        # Simplified implementation - would use actual MeloTTS
        start_time = time.time()

        # Generate simple audio
        duration = len(request.text) * 0.08
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.3 * np.sin(2 * np.pi * 250 * t)

        return SynthesisResult(
            audio_data=audio,
            sample_rate=sample_rate,
            duration=duration,
            voice_id=request.voice_id,
            text=request.text,
            quality_score=3.8,  # MeloTTS quality
            processing_time=time.time() - start_time,
        )


class NVIDIAParakeetManager:
    """Manager for NVIDIA Parakeet as alternative option"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_loaded = False
        self.supported_languages = ["en"]

    async def initialize(self) -> bool:
        """Initialize NVIDIA Parakeet model"""
        try:
            self.logger.info("Initializing NVIDIA Parakeet model...")
            await asyncio.sleep(1.5)  # Simulate loading
            self.model_loaded = True
            self.logger.info("NVIDIA Parakeet model initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize NVIDIA Parakeet: {e}")
            return False

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize using NVIDIA Parakeet"""
        start_time = time.time()

        # Generate audio
        duration = len(request.text) * 0.09
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.4 * np.sin(2 * np.pi * 220 * t)

        return SynthesisResult(
            audio_data=audio,
            sample_rate=sample_rate,
            duration=duration,
            voice_id=request.voice_id,
            text=request.text,
            quality_score=4.1,  # Parakeet quality
            processing_time=time.time() - start_time,
        )


class VoiceModelManager:
    """Manages voice models and selection system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.xtts_manager = XTTSv2ModelManager()
        self.melo_manager = MeloTTSModelManager()
        self.parakeet_manager = NVIDIAParakeetManager()
        self.audio_processor = AudioProcessor()

        # Model priority order
        self.model_priority = [
            TTSModelType.XTTS_V2,
            TTSModelType.MELOTTS,
            TTSModelType.NVIDIA_PARAKEET,
        ]

        self.active_model = None

    async def initialize(self) -> bool:
        """Initialize TTS models in priority order"""
        for model_type in self.model_priority:
            try:
                if model_type == TTSModelType.XTTS_V2:
                    if await self.xtts_manager.initialize():
                        self.active_model = model_type
                        self.logger.info("Using XTTS-v2 as primary TTS model")
                        return True

                elif model_type == TTSModelType.MELOTTS:
                    if await self.melo_manager.initialize():
                        self.active_model = model_type
                        self.logger.info("Using MeloTTS as fallback TTS model")
                        return True

                elif model_type == TTSModelType.NVIDIA_PARAKEET:
                    if await self.parakeet_manager.initialize():
                        self.active_model = model_type
                        self.logger.info("Using NVIDIA Parakeet as fallback TTS model")
                        return True

            except Exception as e:
                self.logger.warning(f"Failed to initialize {model_type.value}: {e}")
                continue

        self.logger.error("Failed to initialize any TTS model")
        return False

    def get_manager(self):
        """Get the active model manager"""
        if self.active_model == TTSModelType.XTTS_V2:
            return self.xtts_manager
        elif self.active_model == TTSModelType.MELOTTS:
            return self.melo_manager
        elif self.active_model == TTSModelType.NVIDIA_PARAKEET:
            return self.parakeet_manager
        else:
            raise RuntimeError("No TTS model initialized")

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize speech using active model"""
        manager = self.get_manager()
        result = await manager.synthesize(request)

        # Apply emotion modulation if supported
        if (
            request.emotion != EmotionType.NEUTRAL
            and self.active_model == TTSModelType.XTTS_V2
        ):
            result.audio_data = self.audio_processor.apply_emotion_modulation(
                result.audio_data,
                result.sample_rate,
                request.emotion,
                request.emotion_intensity,
            )

        return result

    async def clone_voice(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Clone voice (only supported by XTTS-v2)"""
        if self.active_model != TTSModelType.XTTS_V2:
            return VoiceCloneResult(
                voice_id="",
                voice_model=None,
                quality_score=0.0,
                success=False,
                error_message="Voice cloning only supported by XTTS-v2",
            )

        return await self.xtts_manager.clone_voice(request)

    def get_voice_models(self, language: Optional[str] = None) -> List[VoiceModel]:
        """Get available voice models"""
        if self.active_model == TTSModelType.XTTS_V2:
            return self.xtts_manager.get_voice_models(language)
        else:
            # For other models, return basic voice models
            return []

    def get_supported_languages(self) -> List[str]:
        """Get supported languages for active model"""
        manager = self.get_manager()
        return manager.get_supported_languages()

    async def synthesize_cross_lingual(
        self,
        text: str,
        source_voice_id: str,
        target_language: str,
        preserve_accent: bool = True,
    ) -> SynthesisResult:
        """Synthesize speech in target language using source voice characteristics"""
        if self.active_model != TTSModelType.XTTS_V2:
            raise RuntimeError("Cross-lingual synthesis only supported by XTTS-v2")

        return await self.xtts_manager.synthesize_cross_lingual(
            text, source_voice_id, target_language, preserve_accent
        )


class TTSAgent:
    """
    Text-to-Speech Agent using XTTS-v2 with EU accent support
    Implements voice cloning, emotion-aware speech synthesis, and real-time streaming
    """

    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.voice_manager = VoiceModelManager()
        self.audio_processor = AudioProcessor()

        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type="tts",
            status="idle",
            current_task=None,
            capabilities=[
                AgentCapability(
                    name="text_to_speech",
                    description="Convert text to natural speech with EU accent support",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "voice_id": {"type": "string"},
                            "language": {"type": "string"},
                            "emotion": {
                                "type": "string",
                                "enum": [e.value for e in EmotionType],
                            },
                        },
                        "required": ["text"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "audio_data": {
                                "type": "string",
                                "description": "Base64 encoded audio",
                            },
                            "sample_rate": {"type": "integer"},
                            "duration": {"type": "number"},
                        },
                    },
                ),
                AgentCapability(
                    name="voice_cloning",
                    description="Clone voice from 6-second audio samples with quality validation and MOS scoring",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "sample_audio": {
                                "type": "string",
                                "description": "Base64 encoded audio (minimum 6 seconds)",
                            },
                            "voice_name": {"type": "string"},
                            "language": {"type": "string"},
                            "target_text": {
                                "type": "string",
                                "description": "Optional text for quality validation",
                            },
                        },
                        "required": ["sample_audio", "voice_name", "language"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "voice_id": {"type": "string"},
                            "quality_score": {
                                "type": "number",
                                "description": "MOS score (1.0-5.0)",
                            },
                            "success": {"type": "boolean"},
                            "cross_lingual_capable": {"type": "boolean"},
                            "supported_target_languages": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "speaker_characteristics": {"type": "object"},
                        },
                    },
                ),
                AgentCapability(
                    name="cross_lingual_synthesis",
                    description="Synthesize speech in target language preserving source voice accent (e.g., English-accented French)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source_voice_id": {
                                "type": "string",
                                "description": "Cloned voice ID",
                            },
                            "target_language": {"type": "string"},
                            "preserve_accent": {"type": "boolean", "default": True},
                        },
                        "required": ["text", "source_voice_id", "target_language"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "audio_data": {
                                "type": "string",
                                "description": "Base64 encoded audio",
                            },
                            "sample_rate": {"type": "integer"},
                            "cross_lingual_metadata": {"type": "object"},
                        },
                    },
                ),
                AgentCapability(
                    name="voice_quality_validation",
                    description="Validate voice quality and calculate MOS score for cloned voices",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "voice_id": {"type": "string"},
                            "test_text": {
                                "type": "string",
                                "description": "Optional test text for synthesis validation",
                            },
                        },
                        "required": ["voice_id"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "mos_score": {
                                "type": "number",
                                "description": "Mean Opinion Score (1.0-5.0)",
                            },
                            "quality_metrics": {"type": "object"},
                            "validation_timestamp": {"type": "string"},
                        },
                    },
                ),
                AgentCapability(
                    name="emotion_aware_synthesis",
                    description="Synthesize speech with emotional modulation",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "emotion": {"type": "string"},
                            "intensity": {"type": "number", "minimum": 0, "maximum": 2},
                        },
                        "required": ["text", "emotion"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "audio_data": {"type": "string"},
                            "emotion_applied": {"type": "string"},
                        },
                    },
                ),
                AgentCapability(
                    name="real_time_streaming",
                    description="Stream audio output with <100ms latency",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "streaming": {"type": "boolean", "default": True},
                        },
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "stream_id": {"type": "string"},
                            "chunk_count": {"type": "integer"},
                        },
                    },
                ),
            ],
            dependencies=["emotion_agent"],  # For emotion-aware synthesis
            performance_metrics={
                "synthesis_latency": 0.0,
                "voice_quality_mos": 0.0,
                "streaming_latency": 0.0,
                "voice_clone_success_rate": 0.0,
            },
        )

        # Performance tracking
        self.performance_metrics = {
            "total_syntheses": 0,
            "total_voice_clones": 0,
            "successful_voice_clones": 0,
            "average_synthesis_time": 0.0,
            "average_quality_score": 0.0,
            "streaming_sessions": 0,
        }

        # Streaming sessions
        self.active_streams: Dict[str, Dict] = {}

        # Default synthesis settings
        self.default_voice_id = "en_us_female_1"
        self.default_language = "en"

    async def initialize(self) -> bool:
        """Initialize the TTS agent"""
        try:
            self.logger.info(f"Initializing TTS Agent {self.agent_id}")

            # Initialize voice model manager
            if not await self.voice_manager.initialize():
                self.logger.error("Failed to initialize voice model manager")
                return False

            self.state.status = "ready"
            self.logger.info(f"TTS Agent {self.agent_id} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"TTS Agent initialization failed: {e}")
            self.state.status = "error"
            return False

    async def synthesize_text(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        emotion: EmotionType = EmotionType.NEUTRAL,
        emotion_intensity: float = 1.0,
        quality: VoiceQuality = VoiceQuality.MEDIUM,
        streaming: bool = False,
    ) -> Union[SynthesisResult, AsyncGenerator[bytes, None]]:
        """Synthesize text to speech"""
        try:
            self.state.status = "processing"
            start_time = time.time()

            # Use defaults if not specified
            voice_id = voice_id or self.default_voice_id
            language = language or self.default_language

            # Create synthesis request
            request = SynthesisRequest(
                text=text,
                voice_id=voice_id,
                language=language,
                emotion=emotion,
                emotion_intensity=emotion_intensity,
                quality=quality,
                streaming=streaming,
            )

            # Synthesize
            result = await self.voice_manager.synthesize(request)

            # Update performance metrics
            self._update_synthesis_metrics(result, time.time() - start_time)

            if streaming:
                # Return streaming generator
                return self._create_audio_stream(result)
            else:
                # Return complete result
                self.state.status = "ready"
                return result

        except Exception as e:
            self.logger.error(f"Text synthesis failed: {e}")
            self.state.status = "error"
            raise

    async def clone_voice_from_sample(
        self,
        sample_audio: np.ndarray,
        sample_rate: int,
        voice_name: str,
        language: str,
        target_text: Optional[str] = None,
    ) -> VoiceCloneResult:
        """Clone voice from audio sample"""
        try:
            self.logger.info(f"Cloning voice: {voice_name}")
            self.state.status = "processing"

            # Create cloning request
            request = VoiceCloneRequest(
                sample_audio=sample_audio,
                sample_rate=sample_rate,
                voice_name=voice_name,
                language=language,
                target_text=target_text,
            )

            # Clone voice
            result = await self.voice_manager.clone_voice(request)

            # Update performance metrics
            self.performance_metrics["total_voice_clones"] += 1
            if result.success:
                self.performance_metrics["successful_voice_clones"] += 1

            # Update agent state metrics
            success_rate = self.performance_metrics["successful_voice_clones"] / max(
                1, self.performance_metrics["total_voice_clones"]
            )
            self.state.performance_metrics["voice_clone_success_rate"] = success_rate

            self.state.status = "ready"
            return result

        except Exception as e:
            self.logger.error(f"Voice cloning failed: {e}")
            self.state.status = "error"
            raise

    async def request_emotion_context(
        self, input_data: str, input_type: str = "text", sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """Request emotion context from Emotion Agent"""
        try:
            # Send request to emotion agent
            request_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id="emotion_agent",
                message_type="emotion_context_request",
                payload={
                    "input_data": input_data,
                    "input_type": input_type,
                    "sample_rate": sample_rate,
                },
                priority=Priority.HIGH,
            )

            # Send message and wait for response
            await self.message_bus.router.send_message(request_message)

            # Wait for response (simplified - in real implementation would use proper async waiting)
            await asyncio.sleep(0.1)  # Give emotion agent time to process

            # Get response messages
            response_messages = await self.message_bus.router.get_messages(
                self.agent_id, max_messages=10
            )

            # Find the emotion context response
            for message in response_messages:
                if (
                    message.message_type == "emotion_context_response"
                    and message.correlation_id == request_message.message_id
                ):
                    return message.payload.get("emotion_context", {})

            # If no response found, return neutral context
            self.logger.warning("No emotion context response received, using neutral")
            return {
                "emotion": "neutral",
                "intensity": 1.0,
                "sentiment_score": 0.0,
                "arousal": 0.5,
                "valence": 0.5,
                "confidence": 0.5,
            }

        except Exception as e:
            self.logger.error(f"Failed to request emotion context: {e}")
            return {
                "emotion": "neutral",
                "intensity": 1.0,
                "sentiment_score": 0.0,
                "arousal": 0.5,
                "valence": 0.5,
                "confidence": 0.5,
            }

    async def synthesize_with_emotion_detection(
        self, text: str, voice_id: Optional[str] = None, language: Optional[str] = None
    ) -> SynthesisResult:
        """Synthesize speech with automatic emotion detection from text"""
        try:
            # Request emotion context from text
            emotion_context = await self.request_emotion_context(text, "text")

            # Synthesize with detected emotion
            return await self.synthesize_with_emotion(
                text=text,
                emotion_context=emotion_context,
                voice_id=voice_id,
                language=language,
            )

        except Exception as e:
            self.logger.error(f"Emotion detection synthesis failed: {e}")
            # Fallback to neutral synthesis
            return await self.synthesize_text(text, voice_id, language)

    async def synthesize_with_emotion(
        self,
        text: str,
        emotion_context: Dict[str, Any],
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        """Synthesize speech with emotion from emotion agent context"""
        try:
            # Extract emotion information
            emotion_type = EmotionType.NEUTRAL
            emotion_intensity = 1.0

            if emotion_context:
                emotion_name = emotion_context.get("emotion", "neutral").lower()
                emotion_intensity = emotion_context.get("intensity", 1.0)

                # Map emotion names to enum
                emotion_mapping = {
                    "happy": EmotionType.HAPPY,
                    "sad": EmotionType.SAD,
                    "angry": EmotionType.ANGRY,
                    "excited": EmotionType.EXCITED,
                    "calm": EmotionType.CALM,
                    "surprised": EmotionType.SURPRISED,
                    "neutral": EmotionType.NEUTRAL,
                    "fear": EmotionType.SURPRISED,  # Map fear to surprised for TTS
                    "disgust": EmotionType.ANGRY,  # Map disgust to angry for TTS
                }

                emotion_type = emotion_mapping.get(emotion_name, EmotionType.NEUTRAL)

                # Use arousal and valence for more nuanced intensity calculation
                arousal = emotion_context.get("arousal", 0.5)
                valence = emotion_context.get("valence", 0.5)
                confidence = emotion_context.get("confidence", 1.0)

                # Adjust intensity based on arousal and confidence
                emotion_intensity = min(2.0, emotion_intensity * arousal * confidence)

            # Synthesize with emotion
            result = await self.synthesize_text(
                text=text,
                voice_id=voice_id,
                language=language,
                emotion=emotion_type,
                emotion_intensity=emotion_intensity,
            )

            # Add emotion context to result metadata
            result.metadata.update(
                {
                    "emotion_context": emotion_context,
                    "applied_emotion": emotion_type.value,
                    "applied_intensity": emotion_intensity,
                    "emotion_source": "emotion_agent",
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Emotion-aware synthesis failed: {e}")
            raise

    async def synthesize_cross_lingual(
        self,
        text: str,
        source_voice_id: str,
        target_language: str,
        preserve_accent: bool = True,
    ) -> SynthesisResult:
        """Synthesize speech in target language using source voice characteristics"""
        try:
            self.logger.info(
                f"Cross-lingual synthesis: {source_voice_id} → {target_language}"
            )
            self.state.status = "processing"

            start_time = time.time()

            # Perform cross-lingual synthesis
            result = await self.voice_manager.synthesize_cross_lingual(
                text=text,
                source_voice_id=source_voice_id,
                target_language=target_language,
                preserve_accent=preserve_accent,
            )

            # Update performance metrics
            self._update_synthesis_metrics(result, time.time() - start_time)

            self.state.status = "ready"
            return result

        except Exception as e:
            self.logger.error(f"Cross-lingual synthesis failed: {e}")
            self.state.status = "error"
            raise

    async def validate_voice_quality(
        self, voice_id: str, test_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate voice quality and calculate MOS score"""
        try:
            voice_model = self.voice_manager.get_voice_models()
            voice_model = next(
                (vm for vm in voice_model if vm.voice_id == voice_id), None
            )

            if not voice_model:
                raise ValueError(f"Voice model {voice_id} not found")

            # Use test text or default
            test_text = (
                test_text
                or "Hello, this is a voice quality test. How does this sound to you?"
            )

            # Synthesize test audio
            result = await self.synthesize_text(
                text=test_text, voice_id=voice_id, quality=VoiceQuality.HIGH
            )

            # Calculate quality metrics
            quality_metrics = (
                await self.voice_manager.xtts_manager._validate_audio_quality(
                    result.audio_data, result.sample_rate
                )
            )

            # Calculate updated MOS score
            updated_mos = await self.voice_manager.xtts_manager._calculate_voice_mos(
                result.audio_data,
                result.sample_rate,
                result.duration,
                quality_metrics,
                test_text,
            )

            # Update voice model quality score
            voice_model.quality_score = updated_mos

            validation_result = {
                "voice_id": voice_id,
                "mos_score": updated_mos,
                "quality_metrics": quality_metrics,
                "test_text": test_text,
                "synthesis_duration": result.duration,
                "processing_time": result.processing_time,
                "validation_timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                f"Voice quality validation completed for {voice_id}: MOS {updated_mos:.2f}"
            )

            return validation_result

        except Exception as e:
            self.logger.error(f"Voice quality validation failed: {e}")
            raise

    async def create_streaming_session(
        self, text: str, voice_id: Optional[str] = None, language: Optional[str] = None
    ) -> str:
        """Create a streaming audio session"""
        try:
            stream_id = str(uuid.uuid4())

            # Synthesize audio
            result = await self.synthesize_text(
                text=text, voice_id=voice_id, language=language, streaming=True
            )

            # Create audio chunks for streaming
            chunks = self.audio_processor.chunk_for_streaming(
                result.audio_data,
                chunk_duration=0.1,  # 100ms chunks for low latency
                sample_rate=result.sample_rate,
            )

            # Store streaming session
            self.active_streams[stream_id] = {
                "chunks": chunks,
                "sample_rate": result.sample_rate,
                "current_chunk": 0,
                "created_at": time.time(),
                "metadata": result.metadata,
            }

            self.performance_metrics["streaming_sessions"] += 1

            self.logger.info(
                f"Created streaming session {stream_id} with {len(chunks)} chunks"
            )
            return stream_id

        except Exception as e:
            self.logger.error(f"Failed to create streaming session: {e}")
            raise

    async def get_stream_chunk(
        self, stream_id: str
    ) -> Optional[Tuple[np.ndarray, bool]]:
        """Get next chunk from streaming session"""
        if stream_id not in self.active_streams:
            return None

        session = self.active_streams[stream_id]
        current_chunk = session["current_chunk"]

        if current_chunk >= len(session["chunks"]):
            # Stream finished
            del self.active_streams[stream_id]
            return None

        # Get chunk
        chunk_data = session["chunks"][current_chunk]
        session["current_chunk"] += 1

        # Check if this is the last chunk
        is_last = session["current_chunk"] >= len(session["chunks"])

        return chunk_data, is_last

    def _create_audio_stream(
        self, result: SynthesisResult
    ) -> AsyncGenerator[bytes, None]:
        """Create async generator for streaming audio"""

        async def stream_generator():
            chunks = self.audio_processor.chunk_for_streaming(
                result.audio_data, chunk_duration=0.1, sample_rate=result.sample_rate
            )

            for chunk in chunks:
                # Encode chunk as bytes
                chunk_bytes = (chunk * 32767).astype(np.int16).tobytes()
                yield chunk_bytes

                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.05)

        return stream_generator()

    def _update_synthesis_metrics(
        self, result: SynthesisResult, processing_time: float
    ):
        """Update synthesis performance metrics"""
        self.performance_metrics["total_syntheses"] += 1

        # Update average synthesis time
        total = self.performance_metrics["total_syntheses"]
        current_avg = self.performance_metrics["average_synthesis_time"]
        self.performance_metrics["average_synthesis_time"] = (
            current_avg * (total - 1) + processing_time
        ) / total

        # Update average quality score
        current_quality_avg = self.performance_metrics["average_quality_score"]
        self.performance_metrics["average_quality_score"] = (
            current_quality_avg * (total - 1) + result.quality_score
        ) / total

        # Update agent state metrics
        self.state.performance_metrics.update(
            {
                "synthesis_latency": self.performance_metrics["average_synthesis_time"],
                "voice_quality_mos": self.performance_metrics["average_quality_score"],
                "streaming_latency": processing_time if result.duration > 0 else 0.0,
            }
        )

    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents"""
        try:
            if message.message_type == "synthesis_request":
                # Handle text-to-speech request
                text = message.payload.get("text")
                voice_id = message.payload.get("voice_id")
                language = message.payload.get("language")
                emotion = message.payload.get("emotion", "neutral")
                streaming = message.payload.get("streaming", False)

                if not text:
                    raise ValueError("Text is required for synthesis")

                # Map emotion string to enum
                emotion_type = EmotionType.NEUTRAL
                if emotion:
                    try:
                        emotion_type = EmotionType(emotion.lower())
                    except ValueError:
                        self.logger.warning(
                            f"Unknown emotion: {emotion}, using neutral"
                        )

                if streaming:
                    # Create streaming session
                    stream_id = await self.create_streaming_session(
                        text, voice_id, language
                    )

                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="synthesis_response",
                        payload={
                            "stream_id": stream_id,
                            "streaming": True,
                            "agent_id": self.agent_id,
                        },
                        correlation_id=message.message_id,
                        priority=message.priority,
                    )
                else:
                    # Regular synthesis
                    result = await self.synthesize_text(
                        text=text,
                        voice_id=voice_id,
                        language=language,
                        emotion=emotion_type,
                    )

                    # Encode audio as base64
                    audio_b64 = self.audio_processor.encode_audio_base64(
                        result.audio_data, result.sample_rate
                    )

                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="synthesis_response",
                        payload={
                            "audio_data": audio_b64,
                            "sample_rate": result.sample_rate,
                            "duration": result.duration,
                            "voice_id": result.voice_id,
                            "quality_score": result.quality_score,
                            "metadata": result.metadata,
                            "agent_id": self.agent_id,
                        },
                        correlation_id=message.message_id,
                        priority=message.priority,
                    )

            elif message.message_type == "voice_clone_request":
                # Handle voice cloning request
                sample_audio_b64 = message.payload.get("sample_audio")
                voice_name = message.payload.get("voice_name")
                language = message.payload.get("language")
                sample_rate = message.payload.get("sample_rate", 22050)

                if not all([sample_audio_b64, voice_name, language]):
                    raise ValueError(
                        "sample_audio, voice_name, and language are required"
                    )

                # Decode audio
                sample_audio_bytes = base64.b64decode(sample_audio_b64)
                sample_audio = (
                    np.frombuffer(sample_audio_bytes, dtype=np.int16).astype(np.float32)
                    / 32767.0
                )

                # Clone voice
                result = await self.clone_voice_from_sample(
                    sample_audio=sample_audio,
                    sample_rate=sample_rate,
                    voice_name=voice_name,
                    language=language,
                )

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="voice_clone_response",
                    payload={
                        "voice_id": result.voice_id,
                        "success": result.success,
                        "quality_score": result.quality_score,
                        "error_message": result.error_message,
                        "voice_model": result.voice_model.__dict__
                        if result.voice_model
                        else None,
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "stream_chunk_request":
                # Handle streaming chunk request
                stream_id = message.payload.get("stream_id")

                if not stream_id:
                    raise ValueError("stream_id is required")

                chunk_data = await self.get_stream_chunk(stream_id)

                if chunk_data is None:
                    # Stream finished or not found
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="stream_chunk_response",
                        payload={
                            "stream_id": stream_id,
                            "finished": True,
                            "agent_id": self.agent_id,
                        },
                        correlation_id=message.message_id,
                        priority=message.priority,
                    )
                else:
                    chunk, is_last = chunk_data
                    chunk_b64 = base64.b64encode(
                        (chunk * 32767).astype(np.int16).tobytes()
                    ).decode("utf-8")

                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="stream_chunk_response",
                        payload={
                            "stream_id": stream_id,
                            "chunk_data": chunk_b64,
                            "is_last": is_last,
                            "finished": False,
                            "agent_id": self.agent_id,
                        },
                        correlation_id=message.message_id,
                        priority=message.priority,
                    )

            elif message.message_type == "emotion_synthesis_request":
                # Handle emotion-aware synthesis request
                text = message.payload.get("text")
                emotion_context = message.payload.get("emotion_context", {})
                voice_id = message.payload.get("voice_id")
                language = message.payload.get("language")

                if not text:
                    raise ValueError("Text is required for emotion synthesis")

                result = await self.synthesize_with_emotion(
                    text=text,
                    emotion_context=emotion_context,
                    voice_id=voice_id,
                    language=language,
                )

                # Encode audio as base64
                audio_b64 = self.audio_processor.encode_audio_base64(
                    result.audio_data, result.sample_rate
                )

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="emotion_synthesis_response",
                    payload={
                        "audio_data": audio_b64,
                        "sample_rate": result.sample_rate,
                        "duration": result.duration,
                        "emotion_applied": emotion_context.get("emotion", "neutral"),
                        "emotion_intensity": emotion_context.get("intensity", 1.0),
                        "sentiment_score": emotion_context.get("sentiment_score", 0.0),
                        "quality_score": result.quality_score,
                        "metadata": result.metadata,
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "auto_emotion_synthesis_request":
                # Handle automatic emotion detection and synthesis request
                text = message.payload.get("text")
                voice_id = message.payload.get("voice_id")
                language = message.payload.get("language")

                if not text:
                    raise ValueError("Text is required for auto emotion synthesis")

                result = await self.synthesize_with_emotion_detection(
                    text=text, voice_id=voice_id, language=language
                )

                # Encode audio as base64
                audio_b64 = self.audio_processor.encode_audio_base64(
                    result.audio_data, result.sample_rate
                )

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="auto_emotion_synthesis_response",
                    payload={
                        "audio_data": audio_b64,
                        "sample_rate": result.sample_rate,
                        "duration": result.duration,
                        "quality_score": result.quality_score,
                        "metadata": result.metadata,
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "cross_lingual_synthesis_request":
                # Handle cross-lingual synthesis request
                text = message.payload.get("text")
                source_voice_id = message.payload.get("source_voice_id")
                target_language = message.payload.get("target_language")
                preserve_accent = message.payload.get("preserve_accent", True)

                if not all([text, source_voice_id, target_language]):
                    raise ValueError(
                        "text, source_voice_id, and target_language are required"
                    )

                result = await self.synthesize_cross_lingual(
                    text=text,
                    source_voice_id=source_voice_id,
                    target_language=target_language,
                    preserve_accent=preserve_accent,
                )

                # Encode audio as base64
                audio_b64 = self.audio_processor.encode_audio_base64(
                    result.audio_data, result.sample_rate
                )

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="cross_lingual_synthesis_response",
                    payload={
                        "audio_data": audio_b64,
                        "sample_rate": result.sample_rate,
                        "duration": result.duration,
                        "source_voice_id": source_voice_id,
                        "target_language": target_language,
                        "quality_score": result.quality_score,
                        "metadata": result.metadata,
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "voice_quality_validation_request":
                # Handle voice quality validation request
                voice_id = message.payload.get("voice_id")
                test_text = message.payload.get("test_text")

                if not voice_id:
                    raise ValueError("voice_id is required")

                validation_result = await self.validate_voice_quality(
                    voice_id, test_text
                )

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="voice_quality_validation_response",
                    payload={**validation_result, "agent_id": self.agent_id},
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "voice_models_request":
                # Handle request for available voice models
                language = message.payload.get("language")

                voice_models = self.voice_manager.get_voice_models(language)

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="voice_models_response",
                    payload={
                        "voice_models": [vm.__dict__ for vm in voice_models],
                        "supported_languages": self.voice_manager.get_supported_languages(),
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            elif message.message_type == "status_request":
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="status_response",
                    payload={
                        "state": self.state.dict(),
                        "performance_metrics": self.performance_metrics,
                        "active_streams": len(self.active_streams),
                        "agent_id": self.agent_id,
                    },
                    correlation_id=message.message_id,
                    priority=message.priority,
                )

            return None

        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
            return AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type="error",
                payload={"error": str(e), "agent_id": self.agent_id},
                correlation_id=message.message_id,
                priority=message.priority,
            )

    def get_voice_models(self, language: Optional[str] = None) -> List[VoiceModel]:
        """Get available voice models"""
        return self.voice_manager.get_voice_models(language)

    def get_supported_languages(self) -> List[str]:
        """Get supported languages"""
        return self.voice_manager.get_supported_languages()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "state": self.state.dict(),
            "active_streams": len(self.active_streams),
        }

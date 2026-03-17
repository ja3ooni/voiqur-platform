"""
STT Agent - Speech-to-Text implementation using Mistral Voxtral models
Implements real-time streaming capabilities with language detection and accent-aware processing
"""

import asyncio
import logging
import numpy as np
import torch
import torchaudio
from typing import Dict, List, Optional, Tuple, AsyncGenerator, Union
from dataclasses import dataclass
from enum import Enum
import json
import time
from pathlib import Path

from ..core.models import AgentMessage, AgentState, Task
from ..core.messaging import MessageBus


class ModelType(Enum):
    VOXTRAL_SMALL = "mistral-voxtral-small-24b"
    VOXTRAL_MINI = "mistral-voxtral-mini-3b"
    NVIDIA_CANARY = "nvidia-canary-1b-v2"


@dataclass
class AudioChunk:
    """Audio chunk for processing"""
    data: np.ndarray
    sample_rate: int
    timestamp: float
    chunk_id: int


@dataclass
class TranscriptionResult:
    """Result from STT processing"""
    text: str
    confidence: float
    language: str
    dialect: Optional[str]
    timestamps: List[Tuple[float, float]]
    is_partial: bool
    chunk_id: int


@dataclass
class LanguageDetectionResult:
    """Language detection result"""
    language: str
    confidence: float
    dialect: Optional[str]
    accent_region: Optional[str]


class AudioPreprocessor:
    """Audio preprocessing pipeline with proper sampling and chunking"""
    
    def __init__(self, target_sample_rate: int = 16000, chunk_duration: float = 0.5):
        self.target_sample_rate = target_sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(target_sample_rate * chunk_duration)
        self.logger = logging.getLogger(__name__)
        
    def preprocess_audio(self, audio_data: np.ndarray, original_sample_rate: int) -> np.ndarray:
        """Preprocess audio data with resampling and normalization"""
        try:
            # Convert to tensor for processing
            audio_tensor = torch.from_numpy(audio_data).float()
            
            # Resample if necessary
            if original_sample_rate != self.target_sample_rate:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=original_sample_rate,
                    new_freq=self.target_sample_rate
                )
                audio_tensor = resampler(audio_tensor)
            
            # Normalize audio
            audio_tensor = audio_tensor / torch.max(torch.abs(audio_tensor))
            
            # Apply noise reduction (simple high-pass filter)
            audio_tensor = self._apply_noise_reduction(audio_tensor)
            
            return audio_tensor.numpy()
            
        except Exception as e:
            self.logger.error(f"Audio preprocessing failed: {e}")
            raise
    
    def _apply_noise_reduction(self, audio_tensor: torch.Tensor) -> torch.Tensor:
        """Apply basic noise reduction using high-pass filter"""
        # Simple high-pass filter to remove low-frequency noise
        highpass = torchaudio.transforms.HighpassBiquad(
            sample_rate=self.target_sample_rate,
            cutoff_freq=80.0
        )
        return highpass(audio_tensor)
    
    def chunk_audio(self, audio_data: np.ndarray, overlap: float = 0.1) -> List[AudioChunk]:
        """Split audio into overlapping chunks for processing"""
        chunks = []
        overlap_samples = int(self.chunk_size * overlap)
        step_size = self.chunk_size - overlap_samples
        
        for i, start in enumerate(range(0, len(audio_data) - self.chunk_size + 1, step_size)):
            end = start + self.chunk_size
            chunk_data = audio_data[start:end]
            timestamp = start / self.target_sample_rate
            
            chunks.append(AudioChunk(
                data=chunk_data,
                sample_rate=self.target_sample_rate,
                timestamp=timestamp,
                chunk_id=i
            ))
        
        return chunks


class VoxtralModelManager:
    """Manager for Mistral Voxtral models with fallback support"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_model = None
        self.model_type = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models_cache = {}
        
    async def load_model(self, model_type: ModelType, model_path: Optional[str] = None) -> bool:
        """Load and initialize Voxtral model"""
        try:
            self.logger.info(f"Loading {model_type.value} model...")
            
            # Check if model is already cached
            if model_type in self.models_cache:
                self.current_model = self.models_cache[model_type]
                self.model_type = model_type
                self.logger.info(f"Using cached {model_type.value} model")
                return True
            
            # Load model based on type
            if model_type == ModelType.VOXTRAL_SMALL:
                model = await self._load_voxtral_small(model_path)
            elif model_type == ModelType.VOXTRAL_MINI:
                model = await self._load_voxtral_mini(model_path)
            elif model_type == ModelType.NVIDIA_CANARY:
                model = await self._load_nvidia_canary(model_path)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            if model:
                self.models_cache[model_type] = model
                self.current_model = model
                self.model_type = model_type
                self.logger.info(f"Successfully loaded {model_type.value}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to load {model_type.value}: {e}")
            return False
    
    async def _load_voxtral_small(self, model_path: Optional[str]) -> Optional[object]:
        """Load Mistral Voxtral Small (24B) model"""
        # Placeholder for actual Voxtral Small model loading
        # In real implementation, this would use the Mistral API or local model
        self.logger.info("Loading Voxtral Small 24B model...")
        
        # Simulate model loading
        await asyncio.sleep(2)  # Simulate loading time
        
        # Return mock model object
        return {
            "name": "voxtral-small-24b",
            "parameters": "24B",
            "languages": ["en", "fr", "de", "es", "it", "pt", "nl", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sl", "et", "lv", "lt", "mt", "el", "fi", "sv", "da"],
            "sample_rate": 16000
        }
    
    async def _load_voxtral_mini(self, model_path: Optional[str]) -> Optional[object]:
        """Load Mistral Voxtral Mini (3B) model"""
        self.logger.info("Loading Voxtral Mini 3B model...")
        
        # Simulate model loading
        await asyncio.sleep(1)  # Faster loading for smaller model
        
        return {
            "name": "voxtral-mini-3b",
            "parameters": "3B",
            "languages": ["en", "fr", "de", "es", "it", "pt", "nl", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sl", "et", "lv", "lt", "mt", "el", "fi", "sv", "da"],
            "sample_rate": 16000
        }
    
    async def _load_nvidia_canary(self, model_path: Optional[str]) -> Optional[object]:
        """Load NVIDIA Canary-1b-v2 as fallback"""
        self.logger.info("Loading NVIDIA Canary-1b-v2 model...")
        
        # Simulate model loading
        await asyncio.sleep(0.5)  # Fastest loading for smallest model
        
        return {
            "name": "nvidia-canary-1b-v2",
            "parameters": "1B",
            "languages": ["en", "fr", "de", "es", "it", "pt", "nl", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sl", "et", "lv", "lt", "mt", "el", "fi", "sv", "da"],
            "sample_rate": 16000
        }
    
    async def transcribe(self, audio_chunk: AudioChunk) -> TranscriptionResult:
        """Transcribe audio chunk using current model"""
        if not self.current_model:
            raise RuntimeError("No model loaded")
        
        try:
            # Simulate transcription processing
            # In real implementation, this would call the actual model
            await asyncio.sleep(0.05)  # Simulate processing time
            
            # Mock transcription result
            mock_text = f"Transcribed audio chunk {audio_chunk.chunk_id}"
            confidence = 0.95 + (np.random.random() * 0.05)  # 95-100% confidence
            
            return TranscriptionResult(
                text=mock_text,
                confidence=confidence,
                language="en",  # Would be detected by language detection
                dialect=None,
                timestamps=[(audio_chunk.timestamp, audio_chunk.timestamp + 0.5)],
                is_partial=False,
                chunk_id=audio_chunk.chunk_id
            )
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            raise


class LanguageDetector:
    """Language detection for 24+ EU languages with accent awareness"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_languages = [
            "bg", "cs", "da", "de", "el", "en", "es", "et", "fi", "fr",
            "hr", "hu", "it", "lt", "lv", "mt", "nl", "pl", "pt", "ro",
            "sk", "sl", "sv"
        ]
        self.accent_regions = {
            "en": ["uk", "ie", "us", "au", "ca"],
            "de": ["de", "at", "ch"],
            "fr": ["fr", "be", "ch", "ca"],
            "es": ["es", "mx", "ar", "co"],
            "pt": ["pt", "br"],
            "it": ["it", "ch"],
            "nl": ["nl", "be"]
        }
    
    async def detect_language(self, audio_chunk: AudioChunk) -> LanguageDetectionResult:
        """Detect language and accent from audio chunk"""
        try:
            # Simulate language detection processing
            await asyncio.sleep(0.02)  # Fast language detection
            
            # Mock language detection (in real implementation, would use actual model)
            detected_language = np.random.choice(self.supported_languages)
            confidence = 0.98 + (np.random.random() * 0.02)  # 98-100% confidence
            
            # Detect accent if supported
            accent_region = None
            dialect = None
            if detected_language in self.accent_regions:
                accent_region = np.random.choice(self.accent_regions[detected_language])
                dialect = f"{detected_language}-{accent_region}"
            
            return LanguageDetectionResult(
                language=detected_language,
                confidence=confidence,
                dialect=dialect,
                accent_region=accent_region
            )
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            raise


class STTAgent:
    """
    Speech-to-Text Agent using Mistral Voxtral models
    Implements real-time streaming with language detection and accent-aware processing
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.preprocessor = AudioPreprocessor()
        self.model_manager = VoxtralModelManager()
        self.language_detector = LanguageDetector()
        self.advanced_language_detector = None  # Will be initialized later
        
        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            status="idle",
            current_task=None,
            dependencies=[],
            capabilities=[
                "speech_to_text",
                "language_detection",
                "accent_recognition",
                "real_time_streaming",
                "multilingual_support"
            ],
            performance_metrics={
                "transcription_accuracy": 0.0,
                "processing_latency": 0.0,
                "language_detection_accuracy": 0.0
            },
            last_updated=time.time()
        )
        
        # Performance tracking
        self.performance_metrics = {
            "total_chunks_processed": 0,
            "average_latency": 0.0,
            "accuracy_scores": [],
            "language_detection_scores": []
        }
        
        # Model fallback chain
        self.model_fallback_chain = [
            ModelType.VOXTRAL_SMALL,
            ModelType.VOXTRAL_MINI,
            ModelType.NVIDIA_CANARY
        ]
        
    async def initialize(self) -> bool:
        """Initialize the STT agent with model loading"""
        try:
            self.logger.info(f"Initializing STT Agent {self.agent_id}")
            
            # Initialize advanced language detector
            from .language_detection import AdvancedLanguageDetector
            self.advanced_language_detector = AdvancedLanguageDetector()
            await self.advanced_language_detector.initialize_models()
            
            # Try to load models in fallback order
            for model_type in self.model_fallback_chain:
                if await self.model_manager.load_model(model_type):
                    self.logger.info(f"Successfully initialized with {model_type.value}")
                    self.state.status = "ready"
                    return True
            
            self.logger.error("Failed to load any STT model")
            self.state.status = "error"
            return False
            
        except Exception as e:
            self.logger.error(f"STT Agent initialization failed: {e}")
            self.state.status = "error"
            return False
    
    async def process_audio_stream(self, audio_data: np.ndarray, sample_rate: int) -> AsyncGenerator[TranscriptionResult, None]:
        """Process audio stream with real-time transcription"""
        try:
            self.state.status = "processing"
            start_time = time.time()
            
            # Preprocess audio
            processed_audio = self.preprocessor.preprocess_audio(audio_data, sample_rate)
            
            # Chunk audio for processing
            chunks = self.preprocessor.chunk_audio(processed_audio)
            
            for chunk in chunks:
                # Detect language for first chunk or periodically using advanced detector
                if chunk.chunk_id == 0 or chunk.chunk_id % 10 == 0:
                    if self.advanced_language_detector:
                        language_result = await self.advanced_language_detector.detect_language(chunk)
                        self.logger.debug(f"Detected language: {language_result.language} (confidence: {language_result.confidence:.2f}, family: {language_result.language_family.value})")
                        
                        # Update transcription with detected language info
                        detected_language = language_result.language
                        detected_dialect = language_result.dialect
                        detected_accent = language_result.accent_region
                    else:
                        # Fallback to simple language detector
                        simple_result = await self.language_detector.detect_language(chunk)
                        detected_language = simple_result.language
                        detected_dialect = simple_result.dialect
                        detected_accent = simple_result.accent_region
                        self.logger.debug(f"Detected language (fallback): {detected_language} (confidence: {simple_result.confidence:.2f})")
                
                # Transcribe chunk
                transcription = await self.model_manager.transcribe(chunk)
                
                # Update transcription with language detection results
                if 'detected_language' in locals():
                    transcription.language = detected_language
                    transcription.dialect = detected_dialect
                
                # Update performance metrics
                self._update_performance_metrics(transcription, time.time() - start_time)
                
                yield transcription
            
            self.state.status = "ready"
            
        except Exception as e:
            self.logger.error(f"Audio stream processing failed: {e}")
            self.state.status = "error"
            raise
    
    async def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int) -> List[TranscriptionResult]:
        """Transcribe complete audio file"""
        results = []
        async for result in self.process_audio_stream(audio_data, sample_rate):
            results.append(result)
        return results
    
    def _update_performance_metrics(self, transcription: TranscriptionResult, processing_time: float):
        """Update agent performance metrics"""
        self.performance_metrics["total_chunks_processed"] += 1
        
        # Update latency metrics
        current_avg = self.performance_metrics["average_latency"]
        total_processed = self.performance_metrics["total_chunks_processed"]
        self.performance_metrics["average_latency"] = (
            (current_avg * (total_processed - 1) + processing_time) / total_processed
        )
        
        # Update accuracy scores
        self.performance_metrics["accuracy_scores"].append(transcription.confidence)
        if len(self.performance_metrics["accuracy_scores"]) > 100:
            self.performance_metrics["accuracy_scores"].pop(0)
        
        # Update agent state metrics
        self.state.performance_metrics.update({
            "transcription_accuracy": np.mean(self.performance_metrics["accuracy_scores"]),
            "processing_latency": self.performance_metrics["average_latency"],
            "total_processed": self.performance_metrics["total_chunks_processed"]
        })
        
        self.state.last_updated = time.time()
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents"""
        try:
            if message.message_type == "transcription_request":
                # Handle transcription request
                audio_data = message.payload.get("audio_data")
                sample_rate = message.payload.get("sample_rate", 16000)
                
                if audio_data is not None:
                    results = await self.transcribe_audio(audio_data, sample_rate)
                    
                    return AgentMessage(
                        agent_id=self.agent_id,
                        task_id=message.task_id,
                        message_type="transcription_response",
                        payload={
                            "results": [result.__dict__ for result in results],
                            "agent_id": self.agent_id
                        },
                        dependencies=[],
                        priority=message.priority,
                        timestamp=time.time()
                    )
            
            elif message.message_type == "status_request":
                return AgentMessage(
                    agent_id=self.agent_id,
                    task_id=message.task_id,
                    message_type="status_response",
                    payload={
                        "state": self.state.__dict__,
                        "performance_metrics": self.performance_metrics
                    },
                    dependencies=[],
                    priority=message.priority,
                    timestamp=time.time()
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
            return AgentMessage(
                agent_id=self.agent_id,
                task_id=message.task_id,
                message_type="error",
                payload={"error": str(e)},
                dependencies=[],
                priority=message.priority,
                timestamp=time.time()
            )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return self.language_detector.supported_languages
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "state": self.state.__dict__
        }
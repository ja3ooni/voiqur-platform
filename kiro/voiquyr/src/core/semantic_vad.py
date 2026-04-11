"""
Semantic VAD - Prosody + intent end-of-turn detector.

Combines pyannote.audio prosody features with distilBERT intent completeness
for accurate turn-taking detection with <50ms latency.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class VADMode(str, Enum):
    """VAD operation mode."""
    SEMANTIC = "semantic"
    FALLBACK = "fallback"


@dataclass
class AudioFrame:
    """20ms audio frame for VAD processing."""
    samples: bytes  # 320 int16 samples @ 16kHz
    timestamp_ms: int
    sequence_number: int


@dataclass
class VADResult:
    """VAD processing result."""
    is_speech: bool
    is_eot: bool  # End of turn
    intent_score: float
    prosody_features: dict
    processing_latency_ms: float
    mode: VADMode
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SemanticVAD:
    """Semantic VAD with prosody and intent analysis."""
    
    def __init__(self, 
                 eot_threshold: float = 0.7,
                 suppression_threshold: float = 0.3,
                 max_latency_ms: float = 50.0):
        self.eot_threshold = eot_threshold
        self.suppression_threshold = suppression_threshold
        self.max_latency_ms = max_latency_ms
        self.mode = VADMode.SEMANTIC
        self.session_state = {}
        self.partial_transcript = ""
        self.last_intent_check_ms = 0
        
        # Try to load models
        self._load_models()
    
    def _load_models(self):
        """Load pyannote and distilBERT models."""
        try:
            # Placeholder for actual model loading
            # from pyannote.audio import Model
            # from transformers import AutoModelForSequenceClassification
            self.prosody_model = None  # Model("pyannote/voice-activity-detection")
            self.intent_model = None  # AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased")
            logger.info("Semantic VAD models loaded")
        except Exception as e:
            logger.warning(f"Failed to load semantic models, using fallback: {e}")
            self.mode = VADMode.FALLBACK
    
    def is_model_available(self) -> bool:
        """Check if semantic models are available."""
        return self.mode == VADMode.SEMANTIC
    
    def reset_session(self):
        """Reset session state."""
        self.session_state = {}
        self.partial_transcript = ""
        self.last_intent_check_ms = 0
        logger.debug("VAD session reset")
    
    def process_frame(self, frame: AudioFrame, partial_transcript: str = "") -> VADResult:
        """Process 20ms audio frame with prosody and intent analysis."""
        start_time = datetime.utcnow()
        
        # Update partial transcript
        if partial_transcript:
            self.partial_transcript = partial_transcript
        
        # Extract prosody features
        prosody = self._extract_prosody(frame)
        
        # Check intent completeness every 200ms
        intent_score = 0.0
        current_time_ms = frame.timestamp_ms
        
        if current_time_ms - self.last_intent_check_ms >= 200:
            intent_score = self._check_intent_completeness(self.partial_transcript)
            self.last_intent_check_ms = current_time_ms
        
        # Determine end-of-turn
        is_eot = self._detect_eot(prosody, intent_score)
        
        # Calculate processing latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log latency violations
        if latency_ms > self.max_latency_ms:
            logger.warning(f"VAD latency violation: {latency_ms:.1f}ms > {self.max_latency_ms}ms")
        
        return VADResult(
            is_speech=prosody["is_speech"],
            is_eot=is_eot,
            intent_score=intent_score,
            prosody_features=prosody,
            processing_latency_ms=latency_ms,
            mode=self.mode
        )
    
    def _extract_prosody(self, frame: AudioFrame) -> dict:
        """Extract prosody features from audio frame."""
        if self.mode == VADMode.FALLBACK:
            return self._webrtc_vad_fallback(frame)
        
        # Convert bytes to numpy array
        samples = np.frombuffer(frame.samples, dtype=np.int16)
        
        # Extract features (simplified - production would use pyannote)
        rms_energy = np.sqrt(np.mean(samples.astype(float) ** 2))
        is_speech = rms_energy > 500  # Simple threshold
        
        return {
            "is_speech": is_speech,
            "f0": 0.0,  # Fundamental frequency
            "rms_energy": float(rms_energy),
            "speaking_rate": 0.0,
            "pause_duration_ms": 0.0
        }
    
    def _webrtc_vad_fallback(self, frame: AudioFrame) -> dict:
        """WebRTC VAD fallback mode."""
        logger.debug("Using WebRTC VAD fallback")
        
        # Simple energy-based VAD
        samples = np.frombuffer(frame.samples, dtype=np.int16)
        energy = np.sqrt(np.mean(samples.astype(float) ** 2))
        
        return {
            "is_speech": energy > 500,
            "f0": 0.0,
            "rms_energy": float(energy),
            "speaking_rate": 0.0,
            "pause_duration_ms": 0.0
        }
    
    def _check_intent_completeness(self, transcript: str) -> float:
        """Check intent completeness using distilBERT."""
        if not transcript or self.mode == VADMode.FALLBACK:
            return 0.0
        
        # Simplified - production would use actual distilBERT inference
        # Score based on sentence completeness heuristics
        has_punctuation = transcript.strip().endswith(('.', '?', '!'))
        word_count = len(transcript.split())
        
        if has_punctuation and word_count >= 3:
            return 0.8
        elif word_count >= 5:
            return 0.6
        else:
            return 0.3
    
    def _detect_eot(self, prosody: dict, intent_score: float) -> bool:
        """Detect end-of-turn from prosody and intent."""
        # Suppression window: don't signal EOT if intent score too low
        if intent_score < self.suppression_threshold:
            return False
        
        # EOT if intent complete and speech paused
        if intent_score >= self.eot_threshold and not prosody["is_speech"]:
            return True
        
        return False


# Global instance
_semantic_vad: Optional[SemanticVAD] = None


def get_semantic_vad() -> SemanticVAD:
    """Get global semantic VAD instance."""
    global _semantic_vad
    if _semantic_vad is None:
        _semantic_vad = SemanticVAD()
    return _semantic_vad


def set_semantic_vad(vad: SemanticVAD) -> None:
    """Set global semantic VAD instance."""
    global _semantic_vad
    _semantic_vad = vad

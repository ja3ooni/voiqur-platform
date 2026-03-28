"""
Core Processing Pipeline

Integrated voice processing pipeline that connects STT, LLM, and TTS agents
in a cohesive multi-agent system with context sharing and error handling.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
import numpy as np

logger = logging.getLogger(__name__)


class ProcessingStage(str, Enum):
    """Processing pipeline stages."""
    AUDIO_INPUT = "audio_input"
    SPEECH_TO_TEXT = "speech_to_text"
    LANGUAGE_MODEL = "language_model"
    TEXT_TO_SPEECH = "text_to_speech"
    AUDIO_OUTPUT = "audio_output"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingContext:
    """Shared context across processing agents."""
    session_id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    language: str
    accent: Optional[str]
    emotion_context: Optional[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "language": self.language,
            "accent": self.accent,
            "emotion_context": self.emotion_context,
            "conversation_history": self.conversation_history,
            "user_preferences": self.user_preferences,
            "processing_metadata": self.processing_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ProcessingRequest:
    """Voice processing request."""
    request_id: str
    audio_data: Optional[bytes]
    text_input: Optional[str]
    context: ProcessingContext
    processing_options: Dict[str, Any]
    priority: int = 5  # 1-10, higher is more priority
    timeout_seconds: int = 30
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


@dataclass
class ProcessingResult:
    """Voice processing result."""
    request_id: str
    status: ProcessingStatus
    stage: ProcessingStage
    transcribed_text: Optional[str]
    generated_response: Optional[str]
    synthesized_audio: Optional[bytes]
    processing_time_ms: float
    stage_timings: Dict[str, float]
    confidence_scores: Dict[str, float]
    error_message: Optional[str]
    context: ProcessingContext
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "stage": self.stage.value,
            "transcribed_text": self.transcribed_text,
            "generated_response": self.generated_response,
            "synthesized_audio": self.synthesized_audio is not None,
            "processing_time_ms": self.processing_time_ms,
            "stage_timings": self.stage_timings,
            "confidence_scores": self.confidence_scores,
            "error_message": self.error_message,
            "context": self.context.to_dict()
        }


class ProcessingPipeline:
    """
    Core voice processing pipeline that orchestrates STT, LLM, and TTS agents.
    
    Features:
    - Sequential processing through STT → LLM → TTS
    - Context sharing between agents
    - Error handling and graceful degradation
    - Performance monitoring and optimization
    - State management across processing stages
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processing pipeline."""
        self.config = config or {}
        
        # Agent configurations
        self.stt_config = self.config.get("stt", {})
        self.llm_config = self.config.get("llm", {})
        self.tts_config = self.config.get("tts", {})
        
        # Processing state
        self.active_requests: Dict[str, ProcessingRequest] = {}
        self.processing_results: Dict[str, ProcessingResult] = {}
        
        # Performance tracking
        self.stage_performance: Dict[str, List[float]] = {
            stage.value: [] for stage in ProcessingStage
        }
        
        # Error handling configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay_ms = self.config.get("retry_delay_ms", 1000)
        self.enable_graceful_degradation = self.config.get("graceful_degradation", True)
        
        # Context management
        self.context_cache: Dict[str, ProcessingContext] = {}
        self.context_ttl_minutes = self.config.get("context_ttl_minutes", 30)

        # STT manager (lazily initialized to avoid circular import)
        self._stt_manager = None
        self._stt_initialized = False

        logger.info("Processing Pipeline initialized")
    
    async def process_voice_request(
        self,
        request: ProcessingRequest,
        progress_callback: Optional[Callable] = None
    ) -> ProcessingResult:
        """
        Process a complete voice request through the pipeline.
        
        Args:
            request: Processing request with audio data or text
            progress_callback: Optional callback for progress updates
            
        Returns:
            Processing result with transcription, response, and audio
        """
        logger.info(f"Starting voice processing for request: {request.request_id}")
        
        start_time = time.time()
        stage_timings = {}
        confidence_scores = {}
        
        # Store active request
        self.active_requests[request.request_id] = request
        
        try:
            # Update context cache
            self._update_context_cache(request.context)
            
            # Stage 1: Speech-to-Text (if audio input provided)
            transcribed_text = None
            if request.audio_data:
                if progress_callback:
                    await progress_callback(ProcessingStage.SPEECH_TO_TEXT, 0.1)
                
                stt_start = time.time()
                transcribed_text, stt_confidence = await self._process_stt(
                    request.audio_data, request.context
                )
                stage_timings["stt"] = (time.time() - stt_start) * 1000
                confidence_scores["stt"] = stt_confidence
                
                if progress_callback:
                    await progress_callback(ProcessingStage.SPEECH_TO_TEXT, 1.0)
            else:
                transcribed_text = request.text_input
                confidence_scores["stt"] = 1.0  # Direct text input
            
            if not transcribed_text:
                raise ValueError("No text available for processing")
            
            # Stage 2: Language Model Processing
            if progress_callback:
                await progress_callback(ProcessingStage.LANGUAGE_MODEL, 0.1)
            
            llm_start = time.time()
            generated_response, llm_confidence = await self._process_llm(
                transcribed_text, request.context
            )
            stage_timings["llm"] = (time.time() - llm_start) * 1000
            confidence_scores["llm"] = llm_confidence
            
            if progress_callback:
                await progress_callback(ProcessingStage.LANGUAGE_MODEL, 1.0)
            
            # Stage 3: Text-to-Speech
            if progress_callback:
                await progress_callback(ProcessingStage.TEXT_TO_SPEECH, 0.1)
            
            tts_start = time.time()
            synthesized_audio, tts_confidence = await self._process_tts(
                generated_response, request.context
            )
            stage_timings["tts"] = (time.time() - tts_start) * 1000
            confidence_scores["tts"] = tts_confidence
            
            if progress_callback:
                await progress_callback(ProcessingStage.TEXT_TO_SPEECH, 1.0)
            
            # Update conversation history
            await self._update_conversation_history(
                request.context, transcribed_text, generated_response
            )
            
            # Create successful result
            total_time = (time.time() - start_time) * 1000
            
            result = ProcessingResult(
                request_id=request.request_id,
                status=ProcessingStatus.COMPLETED,
                stage=ProcessingStage.COMPLETED,
                transcribed_text=transcribed_text,
                generated_response=generated_response,
                synthesized_audio=synthesized_audio,
                processing_time_ms=total_time,
                stage_timings=stage_timings,
                confidence_scores=confidence_scores,
                error_message=None,
                context=request.context
            )
            
            # Store result and update performance tracking
            self.processing_results[request.request_id] = result
            self._update_performance_tracking(stage_timings)
            
            if progress_callback:
                await progress_callback(ProcessingStage.COMPLETED, 1.0)
            
            logger.info(f"Voice processing completed for request: {request.request_id} in {total_time:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Voice processing failed for request {request.request_id}: {e}")
            
            # Create error result
            total_time = (time.time() - start_time) * 1000
            
            result = ProcessingResult(
                request_id=request.request_id,
                status=ProcessingStatus.FAILED,
                stage=ProcessingStage.FAILED,
                transcribed_text=transcribed_text,
                generated_response=None,
                synthesized_audio=None,
                processing_time_ms=total_time,
                stage_timings=stage_timings,
                confidence_scores=confidence_scores,
                error_message=str(e),
                context=request.context
            )
            
            self.processing_results[request.request_id] = result
            
            if progress_callback:
                await progress_callback(ProcessingStage.FAILED, 1.0)
            
            return result
        
        finally:
            # Clean up active request
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
    
    async def _ensure_stt_ready(self):
        """Lazily initialize VoxtralModelManager if not yet loaded."""
        if not self._stt_initialized:
            from ..agents.stt_agent import VoxtralModelManager  # lazy import avoids circular
            self._stt_manager = VoxtralModelManager()
            await self._stt_manager.load_model()
            self._stt_initialized = True

    async def _process_stt(
        self,
        audio_data: bytes,
        context: ProcessingContext
    ) -> tuple[str, float]:
        """Process audio through Speech-to-Text using VoxtralModelManager."""
        try:
            await self._ensure_stt_ready()

            # Convert raw bytes (int16 PCM) to float32 AudioChunk
            from ..agents.stt_agent import AudioChunk  # lazy import avoids circular
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
            chunk = AudioChunk(
                data=audio_array,
                sample_rate=16000,
                timestamp=0.0,
                chunk_id=0,
            )

            result = await self._stt_manager.transcribe(chunk)

            logger.debug(f"STT processed: '{result.text}' (confidence: {result.confidence:.2f})")
            return result.text, result.confidence

        except Exception as e:
            logger.error(f"STT processing failed: {e}")
            if self.enable_graceful_degradation:
                return "[STT_ERROR] Could not transcribe audio", 0.0
            raise
    
    async def _process_llm(
        self, 
        text: str, 
        context: ProcessingContext
    ) -> tuple[str, float]:
        """Process text through Language Model agent."""
        try:
            # Simulate LLM processing (replace with actual LLM agent call)
            await asyncio.sleep(0.2)  # Simulate processing time
            
            # Generate response based on input and context
            if "[STT_ERROR]" in text:
                response = "I'm sorry, I couldn't understand the audio clearly. Could you please try again?"
                confidence = 0.9
            elif "hello" in text.lower():
                if context.conversation_history:
                    response = "Hello again! How else can I assist you today?"
                else:
                    response = "Hello! I'm your AI voice assistant. How can I help you today?"
                confidence = 0.95
            elif "help" in text.lower():
                response = "I'm here to help! I can assist with information, answer questions, or have a conversation. What would you like to know?"
                confidence = 0.93
            else:
                response = f"I understand you said: '{text}'. That's interesting! Is there anything specific you'd like to know or discuss?"
                confidence = 0.85
            
            # Apply emotion context if available
            if context.emotion_context:
                emotion = context.emotion_context.get("primary_emotion", "neutral")
                if emotion == "sad":
                    response = f"I sense you might be feeling down. {response} I'm here to listen."
                elif emotion == "happy":
                    response = f"You sound cheerful! {response}"
                elif emotion == "angry":
                    response = f"I understand you might be frustrated. {response} Let me try to help."
            
            # Apply language context
            if context.language != "en":
                response = f"[Response in {context.language}] {response}"
                confidence *= 0.9
            
            logger.debug(f"LLM processed: '{response}' (confidence: {confidence:.2f})")
            return response, confidence
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            if self.enable_graceful_degradation:
                return "I apologize, but I'm having trouble processing your request right now. Please try again.", 0.5
            raise
    
    async def _process_tts(
        self, 
        text: str, 
        context: ProcessingContext
    ) -> tuple[bytes, float]:
        """Process text through Text-to-Speech agent."""
        try:
            # Simulate TTS processing (replace with actual TTS agent call)
            await asyncio.sleep(0.15)  # Simulate processing time
            
            # Generate mock audio data based on text length
            text_length = len(text)
            audio_size = max(1000, text_length * 50)  # Rough audio size estimation
            
            # Create mock audio data
            audio_data = b"MOCK_AUDIO_DATA_" + text.encode()[:100] + b"_" + b"0" * (audio_size - 120)
            
            # Calculate confidence based on text characteristics
            confidence = 0.95
            
            # Adjust confidence based on context
            if context.accent:
                confidence *= 0.92  # Slight adjustment for accent synthesis
            
            if context.language != "en":
                confidence *= 0.88  # Lower confidence for non-English synthesis
            
            # Check for difficult words or phrases
            difficult_words = ["pronunciation", "onomatopoeia", "worcestershire"]
            if any(word in text.lower() for word in difficult_words):
                confidence *= 0.85
            
            logger.debug(f"TTS processed: {len(audio_data)} bytes (confidence: {confidence:.2f})")
            return audio_data, confidence
            
        except Exception as e:
            logger.error(f"TTS processing failed: {e}")
            if self.enable_graceful_degradation:
                # Return minimal audio data for error case
                return b"ERROR_AUDIO_PLACEHOLDER", 0.0
            raise
    
    async def _update_conversation_history(
        self,
        context: ProcessingContext,
        user_input: str,
        assistant_response: str
    ) -> None:
        """Update conversation history in context."""
        try:
            # Add new exchange to conversation history
            exchange = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "assistant_response": assistant_response,
                "turn_number": len(context.conversation_history) + 1
            }
            
            context.conversation_history.append(exchange)
            
            # Limit conversation history size
            max_history = self.config.get("max_conversation_history", 10)
            if len(context.conversation_history) > max_history:
                context.conversation_history = context.conversation_history[-max_history:]
            
            # Update context timestamp
            context.updated_at = datetime.utcnow()
            
            logger.debug(f"Updated conversation history: {len(context.conversation_history)} exchanges")
            
        except Exception as e:
            logger.error(f"Failed to update conversation history: {e}")
    
    def _update_context_cache(self, context: ProcessingContext) -> None:
        """Update context cache with current context."""
        try:
            self.context_cache[context.session_id] = context
            
            # Clean up expired contexts
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.context_ttl_minutes)
            expired_sessions = [
                session_id for session_id, ctx in self.context_cache.items()
                if ctx.updated_at < cutoff_time
            ]
            
            for session_id in expired_sessions:
                del self.context_cache[session_id]
            
            logger.debug(f"Context cache updated: {len(self.context_cache)} active sessions")
            
        except Exception as e:
            logger.error(f"Failed to update context cache: {e}")
    
    def _update_performance_tracking(self, stage_timings: Dict[str, float]) -> None:
        """Update performance tracking with stage timings."""
        try:
            for stage, timing in stage_timings.items():
                if stage in self.stage_performance:
                    self.stage_performance[stage].append(timing)
                    
                    # Keep only recent performance data
                    max_samples = self.config.get("max_performance_samples", 1000)
                    if len(self.stage_performance[stage]) > max_samples:
                        self.stage_performance[stage] = self.stage_performance[stage][-max_samples:]
            
        except Exception as e:
            logger.error(f"Failed to update performance tracking: {e}")
    
    def get_processing_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status for a request."""
        if request_id in self.processing_results:
            return self.processing_results[request_id].to_dict()
        elif request_id in self.active_requests:
            return {
                "request_id": request_id,
                "status": ProcessingStatus.PROCESSING.value,
                "stage": ProcessingStage.PROCESSING.value
            }
        else:
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the pipeline."""
        metrics = {}
        
        for stage, timings in self.stage_performance.items():
            if timings:
                metrics[stage] = {
                    "count": len(timings),
                    "avg_ms": round(sum(timings) / len(timings), 2),
                    "min_ms": round(min(timings), 2),
                    "max_ms": round(max(timings), 2),
                    "p95_ms": round(sorted(timings)[int(len(timings) * 0.95)], 2) if len(timings) > 20 else None
                }
        
        return {
            "stage_performance": metrics,
            "active_requests": len(self.active_requests),
            "completed_requests": len(self.processing_results),
            "context_cache_size": len(self.context_cache)
        }
    
    def get_context(self, session_id: str) -> Optional[ProcessingContext]:
        """Get processing context for a session."""
        return self.context_cache.get(session_id)
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data and return cleanup statistics."""
        try:
            # Clean up old results
            result_ttl = timedelta(hours=self.config.get("result_ttl_hours", 24))
            cutoff_time = datetime.utcnow() - result_ttl
            
            expired_results = []
            for request_id, result in self.processing_results.items():
                if result.context.updated_at < cutoff_time:
                    expired_results.append(request_id)
            
            for request_id in expired_results:
                del self.processing_results[request_id]
            
            # Clean up expired contexts (already done in _update_context_cache)
            expired_contexts = 0
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.context_ttl_minutes)
            expired_sessions = [
                session_id for session_id, ctx in self.context_cache.items()
                if ctx.updated_at < cutoff_time
            ]
            
            for session_id in expired_sessions:
                del self.context_cache[session_id]
                expired_contexts += 1
            
            cleanup_stats = {
                "expired_results": len(expired_results),
                "expired_contexts": expired_contexts,
                "remaining_results": len(self.processing_results),
                "remaining_contexts": len(self.context_cache)
            }
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"error": str(e)}


# Global pipeline instance
_processing_pipeline: Optional[ProcessingPipeline] = None


def get_processing_pipeline() -> ProcessingPipeline:
    """Get the global processing pipeline instance."""
    global _processing_pipeline
    if _processing_pipeline is None:
        _processing_pipeline = ProcessingPipeline()
    return _processing_pipeline


def set_processing_pipeline(pipeline: ProcessingPipeline) -> None:
    """Set the global processing pipeline instance."""
    global _processing_pipeline
    _processing_pipeline = pipeline


# Convenience functions
async def process_voice(
    audio_data: Optional[bytes] = None,
    text_input: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    language: str = "en",
    **kwargs
) -> ProcessingResult:
    """
    Convenience function to process voice input.
    
    Args:
        audio_data: Audio data to process
        text_input: Text input (alternative to audio)
        session_id: Session identifier
        user_id: User identifier
        language: Language code
        **kwargs: Additional processing options
        
    Returns:
        Processing result
    """
    pipeline = get_processing_pipeline()
    
    # Create context
    if not session_id:
        session_id = str(uuid.uuid4())
    
    context = ProcessingContext(
        session_id=session_id,
        user_id=user_id,
        conversation_id=kwargs.get("conversation_id"),
        language=language,
        accent=kwargs.get("accent"),
        emotion_context=kwargs.get("emotion_context"),
        conversation_history=kwargs.get("conversation_history", []),
        user_preferences=kwargs.get("user_preferences", {}),
        processing_metadata=kwargs.get("processing_metadata", {}),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create request
    request = ProcessingRequest(
        request_id=str(uuid.uuid4()),
        audio_data=audio_data,
        text_input=text_input,
        context=context,
        processing_options=kwargs.get("processing_options", {}),
        priority=kwargs.get("priority", 5),
        timeout_seconds=kwargs.get("timeout_seconds", 30)
    )
    
    return await pipeline.process_voice_request(request)
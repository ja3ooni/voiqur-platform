"""
Real-time Audio Streaming Components
WebSocket audio streaming handler with buffering, incremental transcription, and voice activity detection
"""

import asyncio
import logging
import numpy as np
import json
import time
from typing import Dict, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
import threading
from collections import deque
import wave
import io

from .stt_agent import STTAgent, TranscriptionResult, AudioChunk
from .language_detection import AdvancedLanguageDetector


class StreamingState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class VoiceActivityResult:
    """Voice activity detection result"""
    is_speech: bool
    confidence: float
    energy_level: float
    timestamp: float


@dataclass
class StreamingSession:
    """WebSocket streaming session"""
    session_id: str
    websocket: WebSocketServerProtocol
    state: StreamingState
    buffer: deque
    last_activity: float
    total_processed: int
    language: Optional[str] = None
    accent: Optional[str] = None


class VoiceActivityDetector:
    """Voice Activity Detection (VAD) for silence handling"""
    
    def __init__(self, 
                 energy_threshold: float = 0.01,
                 silence_duration: float = 1.0,
                 speech_duration: float = 0.3):
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.speech_duration = speech_duration
        self.logger = logging.getLogger(__name__)
        
        # State tracking
        self.is_speech_active = False
        self.speech_start_time = None
        self.silence_start_time = None
        self.energy_history = deque(maxlen=10)
        
    def detect_voice_activity(self, audio_chunk: AudioChunk) -> VoiceActivityResult:
        """Detect voice activity in audio chunk"""
        try:
            # Calculate energy level
            energy = np.mean(np.square(audio_chunk.data))
            self.energy_history.append(energy)
            
            # Adaptive threshold based on recent history
            if len(self.energy_history) > 5:
                avg_energy = np.mean(list(self.energy_history))
                adaptive_threshold = max(self.energy_threshold, avg_energy * 0.1)
            else:
                adaptive_threshold = self.energy_threshold
            
            # Determine if current chunk contains speech
            is_speech = energy > adaptive_threshold
            confidence = min(1.0, energy / adaptive_threshold) if is_speech else 0.0
            
            # Update state tracking
            current_time = audio_chunk.timestamp
            
            if is_speech and not self.is_speech_active:
                # Speech started
                self.speech_start_time = current_time
                self.is_speech_active = True
                self.silence_start_time = None
                
            elif not is_speech and self.is_speech_active:
                # Potential speech end
                if self.silence_start_time is None:
                    self.silence_start_time = current_time
                elif current_time - self.silence_start_time > self.silence_duration:
                    # Confirmed speech end
                    self.is_speech_active = False
                    self.speech_start_time = None
                    
            elif is_speech and self.is_speech_active:
                # Continue speech
                self.silence_start_time = None
            
            return VoiceActivityResult(
                is_speech=self.is_speech_active,
                confidence=confidence,
                energy_level=energy,
                timestamp=current_time
            )
            
        except Exception as e:
            self.logger.error(f"Voice activity detection failed: {e}")
            return VoiceActivityResult(
                is_speech=False,
                confidence=0.0,
                energy_level=0.0,
                timestamp=audio_chunk.timestamp
            )


class AudioBuffer:
    """Circular buffer for audio streaming with overflow protection"""
    
    def __init__(self, max_duration: float = 30.0, sample_rate: int = 16000):
        self.max_duration = max_duration
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration * sample_rate)
        self.buffer = deque(maxlen=self.max_samples)
        self.timestamps = deque(maxlen=self.max_samples)
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def add_audio(self, audio_data: np.ndarray, timestamp: float):
        """Add audio data to buffer"""
        with self.lock:
            for i, sample in enumerate(audio_data):
                self.buffer.append(sample)
                self.timestamps.append(timestamp + i / self.sample_rate)
    
    def get_audio_chunk(self, duration: float) -> Optional[AudioChunk]:
        """Get audio chunk of specified duration"""
        with self.lock:
            chunk_samples = int(duration * self.sample_rate)
            
            if len(self.buffer) < chunk_samples:
                return None
            
            # Extract chunk
            chunk_data = np.array([self.buffer.popleft() for _ in range(chunk_samples)])
            start_timestamp = self.timestamps[0] if self.timestamps else time.time()
            
            # Remove corresponding timestamps
            for _ in range(chunk_samples):
                if self.timestamps:
                    self.timestamps.popleft()
            
            return AudioChunk(
                data=chunk_data,
                sample_rate=self.sample_rate,
                timestamp=start_timestamp,
                chunk_id=int(start_timestamp * 1000)  # Use timestamp as ID
            )
    
    def get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds"""
        with self.lock:
            return len(self.buffer) / self.sample_rate
    
    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()
            self.timestamps.clear()


class IncrementalTranscriber:
    """Handles incremental transcription with partial results"""
    
    def __init__(self, stt_agent: STTAgent):
        self.stt_agent = stt_agent
        self.logger = logging.getLogger(__name__)
        
        # Transcription state
        self.partial_results = {}
        self.final_results = []
        self.context_window = deque(maxlen=5)  # Keep last 5 results for context
        
    async def process_incremental(self, audio_chunk: AudioChunk) -> Dict:
        """Process audio chunk and return incremental results"""
        try:
            # Get transcription from STT agent
            transcription = await self.stt_agent.model_manager.transcribe(audio_chunk)
            
            # Update partial results
            chunk_id = audio_chunk.chunk_id
            self.partial_results[chunk_id] = transcription
            
            # Determine if this is a final result (based on silence or completion)
            is_final = self._should_finalize_result(transcription)
            
            if is_final:
                # Move to final results and clean up partials
                self.final_results.append(transcription)
                self.context_window.append(transcription.text)
                
                # Clean up old partial results
                self._cleanup_partial_results(chunk_id)
            
            # Prepare response
            response = {
                "type": "transcription_update",
                "chunk_id": chunk_id,
                "partial_text": transcription.text,
                "confidence": transcription.confidence,
                "is_final": is_final,
                "language": transcription.language,
                "timestamp": transcription.timestamps[0] if transcription.timestamps else time.time(),
                "context": list(self.context_window)[-3:] if self.context_window else []
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Incremental transcription failed: {e}")
            return {
                "type": "error",
                "message": str(e),
                "chunk_id": audio_chunk.chunk_id
            }
    
    def _should_finalize_result(self, transcription: TranscriptionResult) -> bool:
        """Determine if transcription result should be finalized"""
        # Simple heuristic: finalize if confidence is high and text ends with punctuation
        if transcription.confidence > 0.9:
            text = transcription.text.strip()
            if text.endswith(('.', '!', '?', ';')):
                return True
        
        # Or if we have accumulated enough partial results
        return len(self.partial_results) > 10
    
    def _cleanup_partial_results(self, current_chunk_id: int):
        """Clean up old partial results"""
        # Keep only recent partial results
        cutoff_id = current_chunk_id - 5
        self.partial_results = {
            k: v for k, v in self.partial_results.items() 
            if k > cutoff_id
        }
    
    def get_full_transcription(self) -> str:
        """Get complete transcription from all final results"""
        return " ".join([result.text for result in self.final_results])
    
    def reset(self):
        """Reset transcription state"""
        self.partial_results.clear()
        self.final_results.clear()
        self.context_window.clear()


class WebSocketAudioStreamer:
    """WebSocket server for real-time audio streaming"""
    
    def __init__(self, stt_agent: STTAgent, host: str = "localhost", port: int = 8765):
        self.stt_agent = stt_agent
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.vad = VoiceActivityDetector()
        
        # Active sessions
        self.sessions: Dict[str, StreamingSession] = {}
        self.session_counter = 0
        
        # Server state
        self.server = None
        self.is_running = False
        
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            self.logger.info(f"Starting WebSocket audio streaming server on {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                max_size=10 * 1024 * 1024  # 10MB max message size
            )
            
            self.is_running = True
            self.logger.info("WebSocket server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.logger.info("Stopping WebSocket server")
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            
            # Clean up sessions
            for session in self.sessions.values():
                await session.websocket.close()
            self.sessions.clear()
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket client connection"""
        session_id = f"session_{self.session_counter}"
        self.session_counter += 1
        
        self.logger.info(f"New client connected: {session_id}")
        
        # Create session
        session = StreamingSession(
            session_id=session_id,
            websocket=websocket,
            state=StreamingState.IDLE,
            buffer=AudioBuffer(),
            last_activity=time.time(),
            total_processed=0
        )
        
        self.sessions[session_id] = session
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connection_established",
                "session_id": session_id,
                "supported_languages": self.stt_agent.get_supported_languages(),
                "sample_rate": 16000,
                "chunk_duration": 0.5
            }))
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            self.logger.error(f"Error handling client {session_id}: {e}")
        finally:
            # Clean up session
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    async def handle_message(self, session: StreamingSession, message):
        """Handle incoming WebSocket message"""
        try:
            if isinstance(message, bytes):
                # Binary audio data
                await self.handle_audio_data(session, message)
            else:
                # JSON control message
                data = json.loads(message)
                await self.handle_control_message(session, data)
                
        except Exception as e:
            self.logger.error(f"Message handling error for {session.session_id}: {e}")
            await session.websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def handle_audio_data(self, session: StreamingSession, audio_bytes: bytes):
        """Handle incoming audio data"""
        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Add to buffer
            session.buffer.add_audio(audio_data, time.time())
            session.last_activity = time.time()
            
            # Process if we have enough data
            if session.buffer.get_buffer_duration() >= 0.5:  # 500ms chunks
                await self.process_audio_chunk(session)
                
        except Exception as e:
            self.logger.error(f"Audio data processing error: {e}")
    
    async def handle_control_message(self, session: StreamingSession, data: Dict):
        """Handle control messages"""
        message_type = data.get("type")
        
        if message_type == "start_streaming":
            session.state = StreamingState.LISTENING
            session.language = data.get("language")
            session.accent = data.get("accent")
            
            await session.websocket.send(json.dumps({
                "type": "streaming_started",
                "session_id": session.session_id
            }))
            
        elif message_type == "stop_streaming":
            session.state = StreamingState.IDLE
            session.buffer.clear()
            
            await session.websocket.send(json.dumps({
                "type": "streaming_stopped",
                "session_id": session.session_id,
                "total_processed": session.total_processed
            }))
            
        elif message_type == "pause_streaming":
            session.state = StreamingState.PAUSED
            
        elif message_type == "resume_streaming":
            session.state = StreamingState.LISTENING
            
        elif message_type == "get_status":
            await session.websocket.send(json.dumps({
                "type": "status",
                "session_id": session.session_id,
                "state": session.state.value,
                "buffer_duration": session.buffer.get_buffer_duration(),
                "total_processed": session.total_processed,
                "last_activity": session.last_activity
            }))
    
    async def process_audio_chunk(self, session: StreamingSession):
        """Process audio chunk from session buffer"""
        if session.state != StreamingState.LISTENING:
            return
        
        try:
            session.state = StreamingState.PROCESSING
            
            # Get audio chunk from buffer
            audio_chunk = session.buffer.get_audio_chunk(0.5)  # 500ms
            if not audio_chunk:
                session.state = StreamingState.LISTENING
                return
            
            # Voice activity detection
            vad_result = self.vad.detect_voice_activity(audio_chunk)
            
            # Send VAD result
            await session.websocket.send(json.dumps({
                "type": "voice_activity",
                "is_speech": vad_result.is_speech,
                "confidence": vad_result.confidence,
                "energy_level": vad_result.energy_level,
                "timestamp": vad_result.timestamp
            }))
            
            # Process transcription if speech is detected
            if vad_result.is_speech:
                # Create incremental transcriber for this session if needed
                if not hasattr(session, 'transcriber'):
                    session.transcriber = IncrementalTranscriber(self.stt_agent)
                
                # Get incremental transcription
                transcription_result = await session.transcriber.process_incremental(audio_chunk)
                
                # Send transcription result
                await session.websocket.send(json.dumps(transcription_result))
                
                session.total_processed += 1
            
            session.state = StreamingState.LISTENING
            
        except Exception as e:
            self.logger.error(f"Audio chunk processing error: {e}")
            session.state = StreamingState.ERROR
            
            await session.websocket.send(json.dumps({
                "type": "processing_error",
                "message": str(e)
            }))
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about active sessions"""
        return {
            session_id: {
                "state": session.state.value,
                "buffer_duration": session.buffer.get_buffer_duration(),
                "total_processed": session.total_processed,
                "last_activity": session.last_activity,
                "language": session.language,
                "accent": session.accent
            }
            for session_id, session in self.sessions.items()
        }


class AudioStreamingManager:
    """Manager for audio streaming operations"""
    
    def __init__(self, stt_agent: STTAgent):
        self.stt_agent = stt_agent
        self.logger = logging.getLogger(__name__)
        
        # Streaming components
        self.websocket_streamer = None
        self.is_initialized = False
        
    async def initialize(self, host: str = "localhost", port: int = 8765) -> bool:
        """Initialize audio streaming manager"""
        try:
            self.logger.info("Initializing Audio Streaming Manager")
            
            # Create WebSocket streamer
            self.websocket_streamer = WebSocketAudioStreamer(
                self.stt_agent, host, port
            )
            
            self.is_initialized = True
            self.logger.info("Audio Streaming Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Audio Streaming Manager initialization failed: {e}")
            return False
    
    async def start_streaming(self) -> bool:
        """Start audio streaming services"""
        if not self.is_initialized:
            self.logger.error("Audio Streaming Manager not initialized")
            return False
        
        try:
            await self.websocket_streamer.start_server()
            self.logger.info("Audio streaming services started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start audio streaming: {e}")
            return False
    
    async def stop_streaming(self):
        """Stop audio streaming services"""
        if self.websocket_streamer:
            await self.websocket_streamer.stop_server()
            self.logger.info("Audio streaming services stopped")
    
    def get_streaming_status(self) -> Dict:
        """Get current streaming status"""
        if not self.websocket_streamer:
            return {"status": "not_initialized"}
        
        return {
            "status": "running" if self.websocket_streamer.is_running else "stopped",
            "active_sessions": self.websocket_streamer.get_active_sessions(),
            "server_info": {
                "host": self.websocket_streamer.host,
                "port": self.websocket_streamer.port
            }
        }
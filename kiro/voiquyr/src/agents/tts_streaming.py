"""
Real-time TTS Audio Streaming Components
WebSocket audio streaming for TTS output with <100ms latency, format conversion, and compression
"""

import asyncio
import logging
import numpy as np
import json
import time
import base64
import io
import wave
import struct
from typing import Dict, List, Optional, AsyncGenerator, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
import threading
from collections import deque
import uuid
from datetime import datetime

from .tts_agent import TTSAgent, SynthesisResult, SynthesisRequest, VoiceQuality, EmotionType
from ..core.models import AgentMessage, Priority

class 
AudioFormat(Enum):
    """Supported audio formats for streaming"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    WEBM = "webm"
    PCM = "pcm"


class CompressionLevel(Enum):
    """Audio compression levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class StreamingConfig:
    """Configuration for audio streaming"""
    chunk_duration: float = 0.1  # 100ms chunks for <100ms latency
    sample_rate: int = 22050
    format: AudioFormat = AudioFormat.WAV
    compression: CompressionLevel = CompressionLevel.LOW
    buffer_size: int = 8192
    max_latency: float = 0.1  # Maximum acceptable latency in seconds
    quality: VoiceQuality = VoiceQuality.MEDIUM


@dataclass
class AudioChunk:
    """Audio chunk for streaming"""
    chunk_id: str
    data: bytes
    format: AudioFormat
    sample_rate: int
    duration: float
    timestamp: float
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamingSession:
    """TTS streaming session"""
    session_id: str
    websocket: WebSocketServerProtocol
    config: StreamingConfig
    created_at: float
    last_activity: float
    total_chunks_sent: int = 0
    total_bytes_sent: int = 0
    current_synthesis: Optional[str] = None
    queue: deque = field(default_factory=deque)
    is_active: bool = True


class AudioFormatConverter:
    """Handles audio format conversion and compression"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def convert_to_format(self, audio_data: np.ndarray, sample_rate: int, 
                         target_format: AudioFormat, compression: CompressionLevel) -> bytes:
        """Convert audio data to target format with compression"""
        try:
            if target_format == AudioFormat.PCM:
                return self._to_pcm(audio_data)
            elif target_format == AudioFormat.WAV:
                return self._to_wav(audio_data, sample_rate, compression)
            elif target_format == AudioFormat.MP3:
                return self._to_mp3(audio_data, sample_rate, compression)
            elif target_format == AudioFormat.OGG:
                return self._to_ogg(audio_data, sample_rate, compression)
            elif target_format == AudioFormat.WEBM:
                return self._to_webm(audio_data, sample_rate, compression)
            else:
                # Default to WAV
                return self._to_wav(audio_data, sample_rate, compression)
                
        except Exception as e:
            self.logger.error(f"Audio format conversion failed: {e}")
            # Fallback to PCM
            return self._to_pcm(audio_data)
    
    def _to_pcm(self, audio_data: np.ndarray) -> bytes:
        """Convert to raw PCM format"""
        # Convert to 16-bit PCM
        audio_int16 = (audio_data * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    def _to_wav(self, audio_data: np.ndarray, sample_rate: int, 
               compression: CompressionLevel) -> bytes:
        """Convert to WAV format with optional compression"""
        try:
            # Apply compression by reducing bit depth if needed
            if compression == CompressionLevel.HIGH:
                # 8-bit PCM for high compression
                audio_int8 = (audio_data * 127).astype(np.int8)
                sample_width = 1
                audio_bytes = audio_int8.tobytes()
            elif compression == CompressionLevel.MEDIUM:
                # 12-bit PCM (stored as 16-bit)
                audio_int16 = (audio_data * 2047).astype(np.int16)
                sample_width = 2
                audio_bytes = audio_int16.tobytes()
            else:
                # 16-bit PCM (low/no compression)
                audio_int16 = (audio_data * 32767).astype(np.int16)
                sample_width = 2
                audio_bytes = audio_int16.tobytes()
            
            # Create WAV file in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            self.logger.error(f"WAV conversion failed: {e}")
            return self._to_pcm(audio_data)
    
    def _to_mp3(self, audio_data: np.ndarray, sample_rate: int, 
               compression: CompressionLevel) -> bytes:
        """Convert to MP3 format (simplified implementation)"""
        # Note: Real implementation would use libraries like pydub or ffmpeg
        # For now, return WAV as fallback
        self.logger.warning("MP3 encoding not implemented, falling back to WAV")
        return self._to_wav(audio_data, sample_rate, compression)
    
    def _to_ogg(self, audio_data: np.ndarray, sample_rate: int, 
               compression: CompressionLevel) -> bytes:
        """Convert to OGG format (simplified implementation)"""
        # Note: Real implementation would use libraries like soundfile or ffmpeg
        # For now, return WAV as fallback
        self.logger.warning("OGG encoding not implemented, falling back to WAV")
        return self._to_wav(audio_data, sample_rate, compression)
    
    def _to_webm(self, audio_data: np.ndarray, sample_rate: int, 
                compression: CompressionLevel) -> bytes:
        """Convert to WebM format (simplified implementation)"""
        # Note: Real implementation would use ffmpeg
        # For now, return WAV as fallback
        self.logger.warning("WebM encoding not implemented, falling back to WAV")
        return self._to_wav(audio_data, sample_rate, compression)
    
    def get_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """Calculate compression ratio"""
        if original_size == 0:
            return 1.0
        return compressed_size / original_size


class AudioChunker:
    """Handles audio chunking for streaming with latency optimization"""
    
    def __init__(self, chunk_duration: float = 0.1, overlap: float = 0.01):
        self.chunk_duration = chunk_duration
        self.overlap = overlap  # Small overlap to prevent audio artifacts
        self.logger = logging.getLogger(__name__)
    
    def chunk_audio(self, audio_data: np.ndarray, sample_rate: int, 
                   session_id: str) -> List[AudioChunk]:
        """Split audio into chunks optimized for streaming"""
        try:
            chunks = []
            chunk_samples = int(self.chunk_duration * sample_rate)
            overlap_samples = int(self.overlap * sample_rate)
            
            # Calculate step size (chunk size minus overlap)
            step_size = chunk_samples - overlap_samples
            
            start_time = time.time()
            
            for i in range(0, len(audio_data), step_size):
                # Extract chunk with overlap
                end_idx = min(i + chunk_samples, len(audio_data))
                chunk_data = audio_data[i:end_idx]
                
                # Skip very small chunks at the end
                if len(chunk_data) < chunk_samples // 4:
                    break
                
                # Pad if necessary to maintain consistent chunk size
                if len(chunk_data) < chunk_samples:
                    padding = np.zeros(chunk_samples - len(chunk_data))
                    chunk_data = np.concatenate([chunk_data, padding])
                
                # Apply fade in/out to prevent clicks
                chunk_data = self._apply_fade(chunk_data, fade_samples=overlap_samples//2)
                
                # Create chunk
                chunk_id = f"{session_id}_{len(chunks):04d}"
                timestamp = start_time + (i / sample_rate)
                duration = len(chunk_data) / sample_rate
                is_final = (end_idx >= len(audio_data))
                
                # Convert to bytes (will be converted to target format later)
                chunk_bytes = (chunk_data * 32767).astype(np.int16).tobytes()
                
                chunk = AudioChunk(
                    chunk_id=chunk_id,
                    data=chunk_bytes,
                    format=AudioFormat.PCM,  # Raw format, will be converted later
                    sample_rate=sample_rate,
                    duration=duration,
                    timestamp=timestamp,
                    is_final=is_final,
                    metadata={
                        "chunk_index": len(chunks),
                        "original_samples": len(chunk_data),
                        "has_overlap": i > 0
                    }
                )
                
                chunks.append(chunk)
            
            self.logger.debug(f"Created {len(chunks)} audio chunks for streaming")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Audio chunking failed: {e}")
            return []
    
    def _apply_fade(self, audio_data: np.ndarray, fade_samples: int) -> np.ndarray:
        """Apply fade in/out to prevent audio artifacts"""
        if fade_samples <= 0 or len(audio_data) <= fade_samples * 2:
            return audio_data
        
        result = audio_data.copy()
        
        # Fade in
        fade_in = np.linspace(0, 1, fade_samples)
        result[:fade_samples] *= fade_in
        
        # Fade out
        fade_out = np.linspace(1, 0, fade_samples)
        result[-fade_samples:] *= fade_out
        
        return result


class LatencyOptimizer:
    """Optimizes streaming latency through various techniques"""
    
    def __init__(self, target_latency: float = 0.1):
        self.target_latency = target_latency
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.latency_history = deque(maxlen=100)
        self.chunk_times = deque(maxlen=50)
        
    def optimize_chunk_size(self, current_latency: float, chunk_duration: float) -> float:
        """Dynamically adjust chunk size based on latency"""
        try:
            self.latency_history.append(current_latency)
            
            if len(self.latency_history) < 10:
                return chunk_duration
            
            avg_latency = np.mean(list(self.latency_history)[-10:])
            
            # Adjust chunk size to meet target latency
            if avg_latency > self.target_latency * 1.2:
                # Latency too high, reduce chunk size
                new_duration = max(0.05, chunk_duration * 0.9)
                self.logger.debug(f"Reducing chunk size: {chunk_duration:.3f} -> {new_duration:.3f}")
                return new_duration
            elif avg_latency < self.target_latency * 0.8:
                # Latency acceptable, can increase chunk size for efficiency
                new_duration = min(0.2, chunk_duration * 1.05)
                self.logger.debug(f"Increasing chunk size: {chunk_duration:.3f} -> {new_duration:.3f}")
                return new_duration
            
            return chunk_duration
            
        except Exception as e:
            self.logger.error(f"Chunk size optimization failed: {e}")
            return chunk_duration
    
    def should_skip_chunk(self, queue_size: int, max_queue_size: int = 5) -> bool:
        """Determine if chunk should be skipped to reduce latency"""
        # Skip chunks if queue is getting too large
        return queue_size > max_queue_size
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.latency_history:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "current": 0.0}
        
        history = list(self.latency_history)
        return {
            "avg": np.mean(history),
            "min": np.min(history),
            "max": np.max(history),
            "current": history[-1] if history else 0.0,
            "target": self.target_latency
        }


class TTSWebSocketStreamer:
    """WebSocket server for real-time TTS audio streaming"""
    
    def __init__(self, tts_agent: TTSAgent, host: str = "localhost", port: int = 8767):
        self.tts_agent = tts_agent
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.format_converter = AudioFormatConverter()
        self.chunker = AudioChunker()
        self.latency_optimizer = LatencyOptimizer()
        
        # Active sessions
        self.sessions: Dict[str, StreamingSession] = {}
        self.session_counter = 0
        
        # Server state
        self.server = None
        self.is_running = False
        
        # Performance metrics
        self.total_sessions = 0
        self.total_chunks_sent = 0
        self.total_bytes_sent = 0
        
    async def start_server(self):
        """Start the WebSocket server for TTS streaming"""
        try:
            self.logger.info(f"Starting TTS WebSocket streaming server on {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                max_size=50 * 1024 * 1024,  # 50MB max message size for large audio
                compression=None  # Disable compression for lower latency
            )
            
            self.is_running = True
            self.logger.info("TTS WebSocket server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start TTS WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.logger.info("Stopping TTS WebSocket server")
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            
            # Clean up sessions
            for session in self.sessions.values():
                await session.websocket.close()
            self.sessions.clear()
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket client connection"""
        session_id = f"tts_session_{self.session_counter}"
        self.session_counter += 1
        self.total_sessions += 1
        
        self.logger.info(f"New TTS client connected: {session_id}")
        
        # Create session with default config
        session = StreamingSession(
            session_id=session_id,
            websocket=websocket,
            config=StreamingConfig(),
            created_at=time.time(),
            last_activity=time.time()
        )
        
        self.sessions[session_id] = session
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connection_established",
                "session_id": session_id,
                "supported_formats": [fmt.value for fmt in AudioFormat],
                "supported_voices": [vm.voice_id for vm in self.tts_agent.voice_manager.get_voice_models()],
                "supported_languages": self.tts_agent.voice_manager.get_supported_languages(),
                "default_config": {
                    "chunk_duration": session.config.chunk_duration,
                    "sample_rate": session.config.sample_rate,
                    "format": session.config.format.value,
                    "compression": session.config.compression.value
                }
            }))
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"TTS client disconnected: {session_id}")
        except Exception as e:
            self.logger.error(f"Error handling TTS client {session_id}: {e}")
        finally:
            # Clean up session
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    async def handle_message(self, session: StreamingSession, message):
        """Handle incoming WebSocket message"""
        try:
            # All TTS messages should be JSON (no binary audio input)
            data = json.loads(message)
            await self.handle_control_message(session, data)
                
        except Exception as e:
            self.logger.error(f"Message handling error for {session.session_id}: {e}")
            await session.websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def handle_control_message(self, session: StreamingSession, data: Dict):
        """Handle control messages"""
        message_type = data.get("type")
        session.last_activity = time.time()
        
        if message_type == "synthesize_text":
            await self.handle_synthesis_request(session, data)
            
        elif message_type == "configure_streaming":
            await self.handle_config_update(session, data)
            
        elif message_type == "get_status":
            await self.send_status(session)
            
        elif message_type == "stop_synthesis":
            await self.stop_synthesis(session)
            
        elif message_type == "get_latency_stats":
            await self.send_latency_stats(session)
            
        else:
            await session.websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }))
    
    async def handle_synthesis_request(self, session: StreamingSession, data: Dict):
        """Handle text synthesis request"""
        try:
            text = data.get("text")
            if not text:
                raise ValueError("Text is required for synthesis")
            
            voice_id = data.get("voice_id")
            language = data.get("language")
            emotion = data.get("emotion", "neutral")
            streaming = data.get("streaming", True)
            
            # Update session config if provided
            if "config" in data:
                await self.update_session_config(session, data["config"])
            
            self.logger.info(f"Starting synthesis for session {session.session_id}: '{text[:50]}...'")
            
            # Start synthesis
            synthesis_id = str(uuid.uuid4())
            session.current_synthesis = synthesis_id
            
            # Send synthesis started message
            await session.websocket.send(json.dumps({
                "type": "synthesis_started",
                "synthesis_id": synthesis_id,
                "text": text,
                "estimated_duration": len(text) * 0.1,  # Rough estimate
                "config": {
                    "chunk_duration": session.config.chunk_duration,
                    "format": session.config.format.value,
                    "compression": session.config.compression.value
                }
            }))
            
            if streaming:
                # Stream synthesis
                await self.stream_synthesis(session, synthesis_id, text, voice_id, language, emotion)
            else:
                # Complete synthesis
                await self.complete_synthesis(session, synthesis_id, text, voice_id, language, emotion)
                
        except Exception as e:
            self.logger.error(f"Synthesis request failed: {e}")
            await session.websocket.send(json.dumps({
                "type": "synthesis_error",
                "message": str(e)
            }))
    
    async def stream_synthesis(self, session: StreamingSession, synthesis_id: str,
                             text: str, voice_id: Optional[str], language: Optional[str], 
                             emotion: str):
        """Stream synthesis results in real-time"""
        try:
            start_time = time.time()
            
            # Map emotion string to enum
            emotion_type = EmotionType.NEUTRAL
            try:
                emotion_type = EmotionType(emotion.lower())
            except ValueError:
                self.logger.warning(f"Unknown emotion: {emotion}, using neutral")
            
            # Synthesize audio
            result = await self.tts_agent.synthesize_text(
                text=text,
                voice_id=voice_id,
                language=language,
                emotion=emotion_type,
                quality=session.config.quality
            )
            
            synthesis_time = time.time() - start_time
            
            # Create audio chunks
            chunks = self.chunker.chunk_audio(
                result.audio_data, 
                result.sample_rate, 
                session.session_id
            )
            
            chunk_start_time = time.time()
            
            # Stream chunks
            for i, chunk in enumerate(chunks):
                # Check if synthesis was stopped
                if session.current_synthesis != synthesis_id:
                    break
                
                # Optimize latency
                if self.latency_optimizer.should_skip_chunk(len(session.queue)):
                    self.logger.debug(f"Skipping chunk {i} to reduce latency")
                    continue
                
                # Convert to target format
                converted_data = self.format_converter.convert_to_format(
                    np.frombuffer(chunk.data, dtype=np.int16).astype(np.float32) / 32767.0,
                    chunk.sample_rate,
                    session.config.format,
                    session.config.compression
                )
                
                # Update chunk with converted data
                chunk.data = converted_data
                chunk.format = session.config.format
                
                # Calculate current latency
                current_latency = time.time() - chunk_start_time
                
                # Send chunk
                await self.send_audio_chunk(session, chunk, synthesis_id)
                
                # Update latency optimizer
                session.config.chunk_duration = self.latency_optimizer.optimize_chunk_size(
                    current_latency, session.config.chunk_duration
                )
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send synthesis completed message
            total_time = time.time() - start_time
            await session.websocket.send(json.dumps({
                "type": "synthesis_completed",
                "synthesis_id": synthesis_id,
                "total_chunks": len(chunks),
                "total_duration": result.duration,
                "synthesis_time": synthesis_time,
                "streaming_time": total_time,
                "latency_stats": self.latency_optimizer.get_latency_stats()
            }))
            
            session.current_synthesis = None
            
        except Exception as e:
            self.logger.error(f"Streaming synthesis failed: {e}")
            await session.websocket.send(json.dumps({
                "type": "synthesis_error",
                "synthesis_id": synthesis_id,
                "message": str(e)
            }))
            session.current_synthesis = None
    
    async def complete_synthesis(self, session: StreamingSession, synthesis_id: str,
                               text: str, voice_id: Optional[str], language: Optional[str], 
                               emotion: str):
        """Complete synthesis and send as single audio file"""
        try:
            start_time = time.time()
            
            # Map emotion string to enum
            emotion_type = EmotionType.NEUTRAL
            try:
                emotion_type = EmotionType(emotion.lower())
            except ValueError:
                self.logger.warning(f"Unknown emotion: {emotion}, using neutral")
            
            # Synthesize audio
            result = await self.tts_agent.synthesize_text(
                text=text,
                voice_id=voice_id,
                language=language,
                emotion=emotion_type,
                quality=VoiceQuality.HIGH  # Use high quality for complete synthesis
            )
            
            # Convert to target format
            converted_data = self.format_converter.convert_to_format(
                result.audio_data,
                result.sample_rate,
                session.config.format,
                session.config.compression
            )
            
            # Encode as base64 for JSON transmission
            audio_b64 = base64.b64encode(converted_data).decode('utf-8')
            
            synthesis_time = time.time() - start_time
            
            # Send complete audio
            await session.websocket.send(json.dumps({
                "type": "synthesis_completed",
                "synthesis_id": synthesis_id,
                "audio_data": audio_b64,
                "format": session.config.format.value,
                "sample_rate": result.sample_rate,
                "duration": result.duration,
                "synthesis_time": synthesis_time,
                "quality_score": result.quality_score,
                "metadata": result.metadata
            }))
            
            session.current_synthesis = None
            
        except Exception as e:
            self.logger.error(f"Complete synthesis failed: {e}")
            await session.websocket.send(json.dumps({
                "type": "synthesis_error",
                "synthesis_id": synthesis_id,
                "message": str(e)
            }))
            session.current_synthesis = None
    
    async def send_audio_chunk(self, session: StreamingSession, chunk: AudioChunk, 
                             synthesis_id: str):
        """Send audio chunk to client"""
        try:
            # Encode chunk data as base64
            chunk_b64 = base64.b64encode(chunk.data).decode('utf-8')
            
            # Send chunk
            await session.websocket.send(json.dumps({
                "type": "audio_chunk",
                "synthesis_id": synthesis_id,
                "chunk_id": chunk.chunk_id,
                "data": chunk_b64,
                "format": chunk.format.value,
                "sample_rate": chunk.sample_rate,
                "duration": chunk.duration,
                "timestamp": chunk.timestamp,
                "is_final": chunk.is_final,
                "metadata": chunk.metadata
            }))
            
            # Update session stats
            session.total_chunks_sent += 1
            session.total_bytes_sent += len(chunk.data)
            self.total_chunks_sent += 1
            self.total_bytes_sent += len(chunk.data)
            
        except Exception as e:
            self.logger.error(f"Failed to send audio chunk: {e}")
            raise
    
    async def update_session_config(self, session: StreamingSession, config_data: Dict):
        """Update session configuration"""
        try:
            if "chunk_duration" in config_data:
                session.config.chunk_duration = max(0.05, min(0.5, config_data["chunk_duration"]))
            
            if "format" in config_data:
                try:
                    session.config.format = AudioFormat(config_data["format"])
                except ValueError:
                    self.logger.warning(f"Invalid format: {config_data['format']}")
            
            if "compression" in config_data:
                try:
                    session.config.compression = CompressionLevel(config_data["compression"])
                except ValueError:
                    self.logger.warning(f"Invalid compression: {config_data['compression']}")
            
            if "quality" in config_data:
                try:
                    session.config.quality = VoiceQuality(config_data["quality"])
                except ValueError:
                    self.logger.warning(f"Invalid quality: {config_data['quality']}")
            
            # Update chunker with new config
            self.chunker.chunk_duration = session.config.chunk_duration
            
            self.logger.info(f"Updated config for session {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Config update failed: {e}")
    
    async def send_status(self, session: StreamingSession):
        """Send session status"""
        await session.websocket.send(json.dumps({
            "type": "status",
            "session_id": session.session_id,
            "is_active": session.is_active,
            "current_synthesis": session.current_synthesis,
            "total_chunks_sent": session.total_chunks_sent,
            "total_bytes_sent": session.total_bytes_sent,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "config": {
                "chunk_duration": session.config.chunk_duration,
                "format": session.config.format.value,
                "compression": session.config.compression.value,
                "quality": session.config.quality.value
            }
        }))
    
    async def send_latency_stats(self, session: StreamingSession):
        """Send latency statistics"""
        stats = self.latency_optimizer.get_latency_stats()
        await session.websocket.send(json.dumps({
            "type": "latency_stats",
            "stats": stats
        }))
    
    async def stop_synthesis(self, session: StreamingSession):
        """Stop current synthesis"""
        if session.current_synthesis:
            synthesis_id = session.current_synthesis
            session.current_synthesis = None
            
            await session.websocket.send(json.dumps({
                "type": "synthesis_stopped",
                "synthesis_id": synthesis_id
            }))
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        active_sessions = len(self.sessions)
        
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "active_sessions": active_sessions,
            "total_sessions": self.total_sessions,
            "total_chunks_sent": self.total_chunks_sent,
            "total_bytes_sent": self.total_bytes_sent,
            "sessions": {
                session_id: {
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "total_chunks_sent": session.total_chunks_sent,
                    "total_bytes_sent": session.total_bytes_sent,
                    "current_synthesis": session.current_synthesis,
                    "config": {
                        "chunk_duration": session.config.chunk_duration,
                        "format": session.config.format.value,
                        "compression": session.config.compression.value
                    }
                }
                for session_id, session in self.sessions.items()
            }
        }


class TTSStreamingManager:
    """Manager for TTS streaming operations"""
    
    def __init__(self, tts_agent: TTSAgent):
        self.tts_agent = tts_agent
        self.logger = logging.getLogger(__name__)
        
        # Streaming components
        self.websocket_streamer = None
        self.is_initialized = False
        
        # Performance tracking
        self.start_time = None
        
    async def initialize(self, host: str = "localhost", port: int = 8767) -> bool:
        """Initialize TTS streaming manager"""
        try:
            self.logger.info("Initializing TTS Streaming Manager")
            
            # Create WebSocket streamer
            self.websocket_streamer = TTSWebSocketStreamer(
                self.tts_agent, host, port
            )
            
            self.is_initialized = True
            self.start_time = time.time()
            self.logger.info("TTS Streaming Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"TTS Streaming Manager initialization failed: {e}")
            return False
    
    async def start_streaming(self) -> bool:
        """Start TTS streaming services"""
        if not self.is_initialized:
            self.logger.error("TTS Streaming Manager not initialized")
            return False
        
        try:
            await self.websocket_streamer.start_server()
            self.logger.info("TTS streaming services started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start TTS streaming: {e}")
            return False
    
    async def stop_streaming(self):
        """Stop TTS streaming services"""
        if self.websocket_streamer:
            await self.websocket_streamer.stop_server()
            self.logger.info("TTS streaming services stopped")
    
    def get_streaming_status(self) -> Dict:
        """Get current streaming status"""
        if not self.websocket_streamer:
            return {"status": "not_initialized"}
        
        base_status = {
            "status": "running" if self.websocket_streamer.is_running else "stopped",
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "server_stats": self.websocket_streamer.get_server_stats()
        }
        
        return base_status
    
    async def synthesize_and_stream(self, text: str, voice_id: Optional[str] = None,
                                  language: Optional[str] = None, 
                                  emotion: str = "neutral") -> AsyncGenerator[bytes, None]:
        """Synthesize text and return streaming generator"""
        try:
            # Map emotion string to enum
            emotion_type = EmotionType.NEUTRAL
            try:
                emotion_type = EmotionType(emotion.lower())
            except ValueError:
                self.logger.warning(f"Unknown emotion: {emotion}, using neutral")
            
            # Synthesize audio
            result = await self.tts_agent.synthesize_text(
                text=text,
                voice_id=voice_id,
                language=language,
                emotion=emotion_type,
                streaming=True
            )
            
            # Create chunker for streaming
            chunker = AudioChunker(chunk_duration=0.1)  # 100ms chunks
            chunks = chunker.chunk_audio(result.audio_data, result.sample_rate, "direct_stream")
            
            # Stream chunks
            for chunk in chunks:
                yield chunk.data
                await asyncio.sleep(0.05)  # Small delay for real-time feel
                
        except Exception as e:
            self.logger.error(f"Direct streaming synthesis failed: {e}")
            raise
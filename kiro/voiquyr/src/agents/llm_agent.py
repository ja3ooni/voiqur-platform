"""
LLM Agent - Dialog management and reasoning using Mistral Small 3.1
Implements context management, conversation state tracking, and tool calling capabilities
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime, timedelta

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import numpy as np

from ..core.models import AgentMessage, AgentState, Task, AgentCapability
from ..core.messaging import MessageBus
from .dialog_manager import DialogManager, ConversationSession, DialogTurn, TurnType
from .tool_integration import (
    ToolRegistry, ToolExecutor, PluginSystem, ToolCall, ToolDefinition, 
    ToolParameter, ToolType, FunctionTool
)


class ModelType(Enum):
    MISTRAL_SMALL_31 = "mistral-small-3.1"
    TILDEOPEN_LLM = "tildeopen-llm-30b"


class ConversationState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    WAITING_FOR_TOOL = "waiting_for_tool"
    ERROR = "error"


@dataclass
class ConversationContext:
    """Conversation context with 32k token support"""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context_window: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0
    max_tokens: int = 32000
    language: str = "en"
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        self.context_window.append(message)
        self.last_updated = datetime.utcnow()
        
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        self.token_count += len(content) // 4
        
        # Trim context window if exceeding token limit
        self._trim_context_window()
    
    def _trim_context_window(self):
        """Trim context window to stay within token limits"""
        while self.token_count > self.max_tokens and len(self.context_window) > 1:
            removed_message = self.context_window.pop(0)
            self.token_count -= len(removed_message["content"]) // 4
    
    def get_context_for_model(self) -> List[Dict[str, str]]:
        """Get formatted context for model input"""
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in self.context_window]
    
    def update_intent(self, intent: str, confidence: float = 1.0):
        """Update current intent"""
        self.current_intent = intent
        self.metadata["intent_confidence"] = confidence
        self.last_updated = datetime.utcnow()
    
    def update_entities(self, entities: Dict[str, Any]):
        """Update extracted entities"""
        self.entities.update(entities)
        self.last_updated = datetime.utcnow()


@dataclass
class IntentRecognitionResult:
    """Result from intent recognition"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    context_needed: List[str]


@dataclass
class ToolCall:
    """Tool call request"""
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ToolResult:
    """Tool execution result"""
    call_id: str
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0


class MistralModelManager:
    """Manager for Mistral Small 3.1 and TildeOpen LLM models"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_model = None
        self.tokenizer = None
        self.model_type = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models_cache = {}
        
        # Model configurations
        self.model_configs = {
            ModelType.MISTRAL_SMALL_31: {
                "model_name": "mistralai/Mistral-Small-Instruct-2409",
                "max_tokens": 32768,
                "temperature": 0.7,
                "top_p": 0.9,
                "supports_tools": True
            },
            ModelType.TILDEOPEN_LLM: {
                "model_name": "tildeopen/tildeopen-llm-30b",
                "max_tokens": 32768,
                "temperature": 0.7,
                "top_p": 0.9,
                "supports_tools": False,
                "eu_languages": True
            }
        }
    
    async def load_model(self, model_type: ModelType, model_path: Optional[str] = None) -> bool:
        """Load and initialize model"""
        try:
            self.logger.info(f"Loading {model_type.value} model...")
            
            # Check if model is already cached
            if model_type in self.models_cache:
                self.current_model = self.models_cache[model_type]["model"]
                self.tokenizer = self.models_cache[model_type]["tokenizer"]
                self.model_type = model_type
                self.logger.info(f"Using cached {model_type.value} model")
                return True
            
            config = self.model_configs[model_type]
            model_name = model_path or config["model_name"]
            
            # Load tokenizer
            self.logger.info(f"Loading tokenizer for {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load model
            self.logger.info(f"Loading model {model_name}")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                device_map="auto" if self.device.type == "cuda" else None,
                trust_remote_code=True
            )
            
            # Cache the model and tokenizer
            self.models_cache[model_type] = {
                "model": model,
                "tokenizer": tokenizer
            }
            
            self.current_model = model
            self.tokenizer = tokenizer
            self.model_type = model_type
            
            self.logger.info(f"Successfully loaded {model_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load {model_type.value}: {e}")
            # Fallback to mock model for development
            return await self._load_mock_model(model_type)
    
    async def _load_mock_model(self, model_type: ModelType) -> bool:
        """Load mock model for development/testing"""
        self.logger.warning(f"Loading mock model for {model_type.value}")
        
        self.current_model = {
            "name": model_type.value,
            "type": "mock",
            "config": self.model_configs[model_type]
        }
        self.tokenizer = None
        self.model_type = model_type
        
        return True
    
    async def generate_response(self, context: ConversationContext, 
                              system_prompt: Optional[str] = None,
                              tools: Optional[List[Dict]] = None) -> str:
        """Generate response using current model"""
        if not self.current_model:
            raise RuntimeError("No model loaded")
        
        try:
            # Prepare messages for model
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.extend(context.get_context_for_model())
            
            # Handle mock model
            if isinstance(self.current_model, dict) and self.current_model.get("type") == "mock":
                return await self._generate_mock_response(messages, tools)
            
            # Real model inference
            if self.tokenizer:
                # Format messages for the model
                formatted_prompt = self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
                
                # Tokenize input
                inputs = self.tokenizer(
                    formatted_prompt, 
                    return_tensors="pt", 
                    truncation=True,
                    max_length=self.model_configs[self.model_type]["max_tokens"]
                ).to(self.device)
                
                # Generate response
                with torch.no_grad():
                    outputs = self.current_model.generate(
                        **inputs,
                        max_new_tokens=1024,
                        temperature=self.model_configs[self.model_type]["temperature"],
                        top_p=self.model_configs[self.model_type]["top_p"],
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # Decode response
                response = self.tokenizer.decode(
                    outputs[0][inputs.input_ids.shape[1]:], 
                    skip_special_tokens=True
                )
                
                return response.strip()
            
            return "Model inference not available"
            
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    async def _generate_mock_response(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> str:
        """Generate mock response for development"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        last_message = messages[-1]["content"] if messages else ""
        
        # Simple mock responses based on content
        if "hello" in last_message.lower():
            return "Hello! How can I assist you today?"
        elif "weather" in last_message.lower():
            if tools and any("weather" in tool.get("name", "") for tool in tools):
                return "I'll check the weather for you. Let me use the weather tool."
            return "I'd be happy to help with weather information, but I don't have access to current weather data."
        elif "time" in last_message.lower():
            return f"The current time is {datetime.now().strftime('%H:%M:%S')}."
        elif "?" in last_message:
            return "That's an interesting question. Let me think about that and provide you with a helpful response."
        else:
            return "I understand. How can I help you further?"
    
    def supports_tools(self) -> bool:
        """Check if current model supports tool calling"""
        if not self.model_type:
            return False
        return self.model_configs[self.model_type].get("supports_tools", False)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        if not self.model_type:
            return {}
        
        config = self.model_configs[self.model_type]
        return {
            "model_type": self.model_type.value,
            "max_tokens": config["max_tokens"],
            "supports_tools": config.get("supports_tools", False),
            "eu_languages": config.get("eu_languages", False),
            "device": str(self.device)
        }


class IntentRecognizer:
    """Intent recognition and entity extraction"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Predefined intents with patterns
        self.intent_patterns = {
            "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
            "question": ["what", "how", "when", "where", "why", "who", "which"],
            "request": ["please", "can you", "could you", "would you", "help me"],
            "weather": ["weather", "temperature", "rain", "sunny", "cloudy", "forecast"],
            "time": ["time", "clock", "hour", "minute", "date", "today", "now"],
            "goodbye": ["bye", "goodbye", "see you", "farewell", "exit", "quit"],
            "information": ["tell me", "explain", "describe", "information about"],
            "booking": ["book", "reserve", "schedule", "appointment", "meeting"],
            "support": ["help", "support", "problem", "issue", "error", "trouble"]
        }
        
        # Entity patterns
        self.entity_patterns = {
            "location": r"\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
            "date": r"\b(?:today|tomorrow|yesterday|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            "time": r"\b(?:\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?|\d{1,2}\s*[AaPp][Mm])\b",
            "number": r"\b\d+\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
        }
    
    async def recognize_intent(self, text: str, context: ConversationContext) -> IntentRecognitionResult:
        """Recognize intent from text"""
        try:
            text_lower = text.lower()
            
            # Score each intent
            intent_scores = {}
            for intent, patterns in self.intent_patterns.items():
                score = sum(1 for pattern in patterns if pattern in text_lower)
                if score > 0:
                    intent_scores[intent] = score / len(patterns)
            
            # Get best intent
            if intent_scores:
                best_intent = max(intent_scores, key=intent_scores.get)
                confidence = intent_scores[best_intent]
            else:
                best_intent = "general"
                confidence = 0.5
            
            # Extract entities
            entities = await self._extract_entities(text)
            
            # Determine context needed
            context_needed = self._determine_context_needed(best_intent, entities)
            
            return IntentRecognitionResult(
                intent=best_intent,
                confidence=confidence,
                entities=entities,
                context_needed=context_needed
            )
            
        except Exception as e:
            self.logger.error(f"Intent recognition failed: {e}")
            return IntentRecognitionResult(
                intent="general",
                confidence=0.0,
                entities={},
                context_needed=[]
            )
    
    async def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text"""
        import re
        
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def _determine_context_needed(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Determine what additional context is needed"""
        context_needed = []
        
        if intent == "weather" and "location" not in entities:
            context_needed.append("location")
        
        if intent == "booking" and "date" not in entities:
            context_needed.append("date")
        
        if intent == "booking" and "time" not in entities:
            context_needed.append("time")
        
        return context_needed


class SessionManager:
    """Manages conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationContext] = {}
        self.session_timeout = timedelta(hours=1)
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: Optional[str] = None, language: str = "en") -> ConversationContext:
        """Create new conversation session"""
        session_id = str(uuid.uuid4())
        
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            language=language
        )
        
        self.sessions[session_id] = context
        self.logger.info(f"Created new session {session_id} for user {user_id}")
        
        return context
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get existing session"""
        session = self.sessions.get(session_id)
        
        if session:
            # Check if session has expired
            if datetime.utcnow() - session.last_updated > self.session_timeout:
                self.logger.info(f"Session {session_id} expired, removing")
                del self.sessions[session_id]
                return None
        
        return session
    
    def update_session(self, session_id: str, context: ConversationContext):
        """Update session"""
        self.sessions[session_id] = context
    
    def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Deleted session {session_id}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, context in self.sessions.items()
            if current_time - context.last_updated > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len([
                s for s in self.sessions.values()
                if datetime.utcnow() - s.last_updated < timedelta(minutes=30)
            ])
        }


class LLMAgent:
    """
    LLM Agent for dialog management and reasoning using Mistral Small 3.1
    Implements context management, conversation state tracking, and tool calling
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.model_manager = MistralModelManager()
        self.intent_recognizer = IntentRecognizer()
        self.session_manager = SessionManager()
        self.dialog_manager = DialogManager()
        
        # Tool system components
        self.tool_registry = ToolRegistry()
        self.tool_executor = ToolExecutor(self.tool_registry, message_bus)
        self.plugin_system = PluginSystem(self.tool_registry)
        
        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type="llm",
            status="idle",
            current_task=None,
            capabilities=[
                AgentCapability(
                    name="dialog_management",
                    description="Manage multi-turn conversations with context",
                    input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"response": {"type": "string"}}}
                ),
                AgentCapability(
                    name="intent_recognition",
                    description="Recognize user intents and extract entities",
                    input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"intent": {"type": "string"}}}
                ),
                AgentCapability(
                    name="context_management",
                    description="Maintain conversation context with 32k token support",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"}
                ),
                AgentCapability(
                    name="tool_calling",
                    description="Call external tools and integrate responses",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"}
                )
            ],
            dependencies=["stt_agent", "tts_agent"],
            performance_metrics={
                "response_latency": 0.0,
                "context_retention": 0.0,
                "intent_accuracy": 0.0,
                "tool_success_rate": 0.0
            }
        )
        
        # Performance tracking
        self.performance_metrics = {
            "total_conversations": 0,
            "total_messages_processed": 0,
            "average_response_time": 0.0,
            "intent_recognition_accuracy": 0.0,
            "tool_calls_made": 0,
            "tool_calls_successful": 0
        }
        

        
        # System prompts
        self.system_prompts = {
            "default": """You are EUVoice AI, a helpful and knowledgeable voice assistant designed for European users. 
You support multiple European languages and are culturally aware. 
Provide helpful, accurate, and contextually appropriate responses.
If you need to use tools, explain what you're doing and why.""",
            
            "multilingual": """You are EUVoice AI, supporting 24+ European languages. 
Respond in the same language as the user's input. 
Be culturally sensitive and adapt your responses to regional contexts."""
        }
    
    async def initialize(self) -> bool:
        """Initialize the LLM agent"""
        try:
            self.logger.info(f"Initializing LLM Agent {self.agent_id}")
            
            # Try to load Mistral Small 3.1 first, then TildeOpen as fallback
            if await self.model_manager.load_model(ModelType.MISTRAL_SMALL_31):
                self.logger.info("Successfully loaded Mistral Small 3.1")
            elif await self.model_manager.load_model(ModelType.TILDEOPEN_LLM):
                self.logger.info("Successfully loaded TildeOpen LLM as fallback")
            else:
                self.logger.error("Failed to load any LLM model")
                return False
            
            # Register default tools
            await self._register_default_tools()
            
            self.state.status = "ready"
            self.logger.info(f"LLM Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"LLM Agent initialization failed: {e}")
            self.state.status = "error"
            return False
    
    async def _register_default_tools(self):
        """Register default tools using the new tool system"""
        # Time tool
        self.tool_registry.register_function(
            name="get_current_time",
            description="Get the current date and time",
            function=self._get_current_time,
            parameters=[
                ToolParameter(
                    name="timezone",
                    type="string",
                    description="Timezone (optional)",
                    required=False
                )
            ]
        )
        
        # Weather tool (placeholder)
        self.tool_registry.register_function(
            name="get_weather",
            description="Get weather information for a location",
            function=self._get_weather,
            parameters=[
                ToolParameter(
                    name="location",
                    type="string",
                    description="Location name",
                    required=True
                ),
                ToolParameter(
                    name="units",
                    type="string",
                    description="Temperature units",
                    required=False,
                    default="celsius",
                    enum_values=["celsius", "fahrenheit"]
                )
            ]
        )
        
        # STT Agent integration tool
        self.tool_registry.register_agent_integration(
            name="transcribe_audio",
            description="Transcribe audio using STT agent",
            agent_id="stt_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="audio_data",
                    type="string",
                    description="Base64 encoded audio data",
                    required=True
                ),
                ToolParameter(
                    name="sample_rate",
                    type="integer",
                    description="Audio sample rate",
                    required=False,
                    default=16000
                )
            ]
        )
        
        # TTS Agent integration tool
        self.tool_registry.register_agent_integration(
            name="synthesize_speech",
            description="Synthesize speech using TTS agent",
            agent_id="tts_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to synthesize",
                    required=True
                ),
                ToolParameter(
                    name="voice_id",
                    type="string",
                    description="Voice ID to use",
                    required=False
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Language code",
                    required=False,
                    default="en"
                )
            ]
        )
        
        # Emotion Agent integration tool
        self.tool_registry.register_agent_integration(
            name="detect_emotion",
            description="Detect emotion from audio or text using Emotion agent",
            agent_id="emotion_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="input_data",
                    type="string",
                    description="Audio data (base64) or text to analyze",
                    required=True
                ),
                ToolParameter(
                    name="input_type",
                    type="string",
                    description="Type of input: 'audio' or 'text'",
                    required=True,
                    enum_values=["audio", "text"]
                ),
                ToolParameter(
                    name="sample_rate",
                    type="integer",
                    description="Audio sample rate (for audio input)",
                    required=False,
                    default=16000
                )
            ]
        )
        
        # Accent Agent integration tool
        self.tool_registry.register_agent_integration(
            name="detect_accent",
            description="Detect regional accent from audio using Accent agent",
            agent_id="accent_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="audio_data",
                    type="string",
                    description="Base64 encoded audio data",
                    required=True
                ),
                ToolParameter(
                    name="sample_rate",
                    type="integer",
                    description="Audio sample rate",
                    required=False,
                    default=16000
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Expected language for accent detection",
                    required=False
                )
            ]
        )
        
        # Lip Sync Agent integration tool
        self.tool_registry.register_agent_integration(
            name="generate_lip_sync",
            description="Generate lip sync animation using Lip Sync agent",
            agent_id="lip_sync_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="audio_data",
                    type="string",
                    description="Base64 encoded audio data",
                    required=True
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text corresponding to the audio",
                    required=True
                ),
                ToolParameter(
                    name="avatar_style",
                    type="string",
                    description="Avatar style for animation",
                    required=False,
                    default="default"
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Language for phoneme mapping",
                    required=False,
                    default="en"
                )
            ]
        )
        
        # Arabic Agent integration tool
        self.tool_registry.register_agent_integration(
            name="process_arabic",
            description="Process Arabic text/speech using Arabic specialist agent",
            agent_id="arabic_agent",
            message_bus=self.message_bus,
            parameters=[
                ToolParameter(
                    name="input_data",
                    type="string",
                    description="Arabic text or audio data (base64)",
                    required=True
                ),
                ToolParameter(
                    name="input_type",
                    type="string",
                    description="Type of input: 'text' or 'audio'",
                    required=True,
                    enum_values=["text", "audio"]
                ),
                ToolParameter(
                    name="dialect",
                    type="string",
                    description="Arabic dialect preference",
                    required=False,
                    enum_values=["msa", "egyptian", "levantine", "gulf", "maghrebi"]
                ),
                ToolParameter(
                    name="task",
                    type="string",
                    description="Processing task to perform",
                    required=False,
                    default="transcribe",
                    enum_values=["transcribe", "translate", "diacritize", "analyze"]
                )
            ]
        )
        
        # Knowledge Base integration tool
        self.tool_registry.register_function(
            name="query_knowledge_base",
            description="Query the shared knowledge base for information",
            function=self._query_knowledge_base,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query or question",
                    required=True
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Knowledge category to search in",
                    required=False
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return",
                    required=False,
                    default=5
                )
            ]
        )
        
        # Multi-agent coordination tool
        self.tool_registry.register_function(
            name="coordinate_agents",
            description="Coordinate multiple agents for complex tasks",
            function=self._coordinate_agents,
            parameters=[
                ToolParameter(
                    name="task_description",
                    type="string",
                    description="Description of the task requiring coordination",
                    required=True
                ),
                ToolParameter(
                    name="required_agents",
                    type="array",
                    description="List of agent types needed for the task",
                    required=True
                ),
                ToolParameter(
                    name="priority",
                    type="string",
                    description="Task priority level",
                    required=False,
                    default="normal",
                    enum_values=["low", "normal", "high", "critical"]
                )
            ]
        )
    
    async def _get_current_time(self, timezone: Optional[str] = None) -> str:
        """Get current time tool"""
        current_time = datetime.now()
        if timezone:
            return f"Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        return f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def _get_weather(self, location: str, units: str = "celsius") -> str:
        """Get weather tool (placeholder)"""
        # This would integrate with a real weather API
        return f"Weather in {location}: 22°C, partly cloudy (mock data)"
    
    async def _query_knowledge_base(self, query: str, category: Optional[str] = None, max_results: int = 5) -> str:
        """Query the shared knowledge base"""
        try:
            # This would integrate with the actual knowledge base system
            # For now, return mock data
            results = [
                f"Knowledge result 1 for '{query}'",
                f"Knowledge result 2 for '{query}'",
                f"Knowledge result 3 for '{query}'"
            ]
            
            if category:
                results = [f"[{category}] {result}" for result in results[:max_results]]
            
            return f"Found {len(results)} results:\n" + "\n".join(results)
            
        except Exception as e:
            self.logger.error(f"Knowledge base query failed: {e}")
            return f"Failed to query knowledge base: {str(e)}"
    
    async def _coordinate_agents(self, task_description: str, required_agents: List[str], priority: str = "normal") -> str:
        """Coordinate multiple agents for complex tasks"""
        try:
            # Create coordination message
            coordination_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=None,  # Broadcast
                message_type="coordination_request",
                payload={
                    "task_description": task_description,
                    "required_agents": required_agents,
                    "priority": priority,
                    "coordinator": self.agent_id
                },
                priority=Priority.HIGH if priority == "critical" else Priority.NORMAL
            )
            
            # Send coordination request
            if self.message_bus:
                await self.message_bus.send_notification(
                    sender_id=self.agent_id,
                    notification_data=coordination_message.payload
                )
                
                return f"Coordination request sent for task: {task_description}. Required agents: {', '.join(required_agents)}"
            else:
                return f"Mock coordination: Task '{task_description}' would require agents: {', '.join(required_agents)}"
                
        except Exception as e:
            self.logger.error(f"Agent coordination failed: {e}")
            return f"Failed to coordinate agents: {str(e)}"   
 async def process_message(self, text: str, session_id: Optional[str] = None, 
                            user_id: Optional[str] = None, language: str = "en") -> Dict[str, Any]:
        """Process incoming message and generate response"""
        try:
            start_time = time.time()
            self.state.status = "processing"
            
            # Get or create session
            if session_id:
                context = self.session_manager.get_session(session_id)
                if not context:
                    context = self.session_manager.create_session(user_id, language)
                    session_id = context.session_id
            else:
                context = self.session_manager.create_session(user_id, language)
                session_id = context.session_id
            
            # Add user message to context
            context.add_message("user", text)
            
            # Recognize intent
            intent_result = await self.intent_recognizer.recognize_intent(text, context)
            context.update_intent(intent_result.intent, intent_result.confidence)
            context.update_entities(intent_result.entities)
            
            # Check if tool calling is needed
            tool_calls = await self._determine_tool_calls(intent_result, context)
            
            # Execute tool calls if needed
            tool_results = []
            if tool_calls:
                self.state.status = "waiting_for_tool"
                for tool_call in tool_calls:
                    result = await self._execute_tool_call(tool_call)
                    tool_results.append(result)
                    
                    # Add tool result to context
                    if result.status.value == "completed":
                        context.add_message("tool", f"Tool {tool_call.tool_name} result: {result.result}")
                    else:
                        context.add_message("tool", f"Tool {tool_call.tool_name} failed: {result.error_message}")
            
            # Generate response
            self.state.status = "responding"
            system_prompt = self._get_system_prompt(context)
            response = await self.model_manager.generate_response(
                context, 
                system_prompt, 
                self.tool_registry.get_openai_functions() if self.model_manager.supports_tools() else None
            )
            
            # Add assistant response to context
            context.add_message("assistant", response)
            
            # Update session
            self.session_manager.update_session(session_id, context)
            
            # Update performance metrics
            processing_time = time.time() - start_time
            self._update_performance_metrics(processing_time, intent_result.confidence, tool_results)
            
            self.state.status = "ready"
            
            return {
                "response": response,
                "session_id": session_id,
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "entities": intent_result.entities,
                "tool_calls": [tc.__dict__ for tc in tool_calls],
                "tool_results": [tr.__dict__ for tr in tool_results],
                "processing_time": processing_time,
                "context_tokens": context.token_count
            }
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")
            self.state.status = "error"
            return {
                "response": "I apologize, but I encountered an error while processing your message.",
                "error": str(e),
                "session_id": session_id
            }
    
    async def _determine_tool_calls(self, intent_result: IntentRecognitionResult, 
                                  context: ConversationContext) -> List[ToolCall]:
        """Determine if tool calls are needed based on intent and context"""
        tool_calls = []
        
        # Time-related intents
        if intent_result.intent == "time" or "time" in intent_result.entities:
            tool_calls.append(ToolCall(
                tool_name="get_current_time",
                parameters={},
                caller_agent_id=self.agent_id
            ))
        
        # Weather-related intents
        if intent_result.intent == "weather":
            location = None
            if "location" in intent_result.entities:
                location = intent_result.entities["location"][0]
            elif "location" in context.entities:
                location = context.entities["location"]
            
            if location:
                tool_calls.append(ToolCall(
                    tool_name="get_weather",
                    parameters={"location": location},
                    caller_agent_id=self.agent_id
                ))
        
        # Information/knowledge requests
        if intent_result.intent in ["question", "information"] or any(word in context.conversation_history[-1]["content"].lower() 
                                                                     for word in ["what is", "tell me about", "explain", "define"]):
            last_message = context.conversation_history[-1]["content"] if context.conversation_history else ""
            tool_calls.append(ToolCall(
                tool_name="query_knowledge_base",
                parameters={"query": last_message},
                caller_agent_id=self.agent_id
            ))
        
        # Emotion detection for customer service or support intents
        if intent_result.intent in ["support", "complaint"] or any(word in context.conversation_history[-1]["content"].lower() 
                                                                  for word in ["angry", "frustrated", "upset", "happy", "sad"]):
            last_message = context.conversation_history[-1]["content"] if context.conversation_history else ""
            tool_calls.append(ToolCall(
                tool_name="detect_emotion",
                parameters={
                    "input_data": last_message,
                    "input_type": "text"
                },
                caller_agent_id=self.agent_id
            ))
        
        # Arabic language processing
        if context.language in ["ar", "arabic"] or self._contains_arabic_text(context.conversation_history[-1]["content"] if context.conversation_history else ""):
            last_message = context.conversation_history[-1]["content"] if context.conversation_history else ""
            tool_calls.append(ToolCall(
                tool_name="process_arabic",
                parameters={
                    "input_data": last_message,
                    "input_type": "text",
                    "task": "analyze"
                },
                caller_agent_id=self.agent_id
            ))
        
        # Complex multi-agent tasks
        if intent_result.intent == "booking" and len(intent_result.context_needed) > 2:
            # Complex booking might need coordination between multiple agents
            tool_calls.append(ToolCall(
                tool_name="coordinate_agents",
                parameters={
                    "task_description": f"Handle complex booking request: {context.conversation_history[-1]['content'] if context.conversation_history else ''}",
                    "required_agents": ["llm_agent", "booking_agent", "calendar_agent"],
                    "priority": "normal"
                },
                caller_agent_id=self.agent_id
            ))
        
        # Voice/audio processing requests
        last_message_lower = context.conversation_history[-1]["content"].lower() if context.conversation_history else ""
        if any(word in last_message_lower for word in ["voice", "accent", "pronunciation", "speak", "audio"]):
            # Might need accent detection or TTS
            if "accent" in last_message_lower or "pronunciation" in last_message_lower:
                # This would typically be called with actual audio data
                tool_calls.append(ToolCall(
                    tool_name="detect_accent",
                    parameters={
                        "audio_data": "mock_audio_data",  # In real scenario, this would be actual audio
                        "language": context.language
                    },
                    caller_agent_id=self.agent_id
                ))
        
        return tool_calls
    
    def _contains_arabic_text(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        try:
            # Check for Arabic Unicode range
            arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
            import re
            return bool(re.search(arabic_pattern, text))
        except:
            return False
    
    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Execute a tool call using the tool executor"""
        try:
            # Execute using the tool executor
            executed_call = await self.tool_executor.execute_tool_call(tool_call)
            
            # Update performance metrics
            self.performance_metrics["tool_calls_made"] += 1
            if executed_call.status.value == "completed":
                self.performance_metrics["tool_calls_successful"] += 1
            
            return executed_call
            
        except Exception as e:
            self.performance_metrics["tool_calls_made"] += 1
            self.logger.error(f"Tool call {tool_call.tool_name} failed: {e}")
            tool_call.fail_execution(str(e))
            return tool_call
    
    def _get_system_prompt(self, context: ConversationContext) -> str:
        """Get appropriate system prompt based on context"""
        if context.language != "en":
            return self.system_prompts["multilingual"]
        return self.system_prompts["default"]
    
    def _update_performance_metrics(self, processing_time: float, intent_confidence: float, 
                                  tool_results: List[ToolResult]):
        """Update agent performance metrics"""
        self.performance_metrics["total_messages_processed"] += 1
        
        # Update average response time
        total_messages = self.performance_metrics["total_messages_processed"]
        current_avg = self.performance_metrics["average_response_time"]
        self.performance_metrics["average_response_time"] = (
            (current_avg * (total_messages - 1) + processing_time) / total_messages
        )
        
        # Update intent recognition accuracy
        current_intent_avg = self.performance_metrics["intent_recognition_accuracy"]
        self.performance_metrics["intent_recognition_accuracy"] = (
            (current_intent_avg * (total_messages - 1) + intent_confidence) / total_messages
        )
        
        # Calculate tool success rate
        if self.performance_metrics["tool_calls_made"] > 0:
            self.performance_metrics["tool_success_rate"] = (
                self.performance_metrics["tool_calls_successful"] / 
                self.performance_metrics["tool_calls_made"]
            )
        
        # Update agent state metrics
        self.state.performance_metrics.update({
            "response_latency": self.performance_metrics["average_response_time"],
            "intent_accuracy": self.performance_metrics["intent_recognition_accuracy"],
            "tool_success_rate": self.performance_metrics.get("tool_success_rate", 0.0),
            "total_processed": self.performance_metrics["total_messages_processed"]
        })
        
        self.state.last_updated = datetime.utcnow()
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents"""
        try:
            if message.message_type == "dialog_request":
                # Handle dialog processing request
                text = message.payload.get("text", "")
                session_id = message.payload.get("session_id")
                user_id = message.payload.get("user_id")
                language = message.payload.get("language", "en")
                
                result = await self.process_message(text, session_id, user_id, language)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="dialog_response",
                    payload=result,
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "intent_recognition_request":
                # Handle intent recognition request
                text = message.payload.get("text", "")
                session_id = message.payload.get("session_id")
                
                context = self.session_manager.get_session(session_id) if session_id else ConversationContext(session_id="temp")
                intent_result = await self.intent_recognizer.recognize_intent(text, context)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="intent_recognition_response",
                    payload={
                        "intent": intent_result.intent,
                        "confidence": intent_result.confidence,
                        "entities": intent_result.entities,
                        "context_needed": intent_result.context_needed
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "context_request":
                # Handle context information request
                session_id = message.payload.get("session_id")
                context = self.session_manager.get_session(session_id)
                
                if context:
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="context_response",
                        payload={
                            "session_id": session_id,
                            "context": {
                                "current_intent": context.current_intent,
                                "entities": context.entities,
                                "language": context.language,
                                "token_count": context.token_count,
                                "conversation_length": len(context.conversation_history)
                            }
                        },
                        correlation_id=message.message_id,
                        priority=message.priority
                    )
            
            elif message.message_type == "tool_registration":
                # Handle tool registration from other agents
                tool_info = message.payload.get("tool_info")
                if tool_info:
                    success = await self.register_external_tool(tool_info)
                    
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="tool_registration_response",
                        payload={"status": "registered" if success else "failed", "tool_name": tool_info.get("name")},
                        correlation_id=message.message_id,
                        priority=message.priority
                    )
            
            elif message.message_type == "tool_request":
                # Handle tool execution request from other agents
                tool_name = message.payload.get("tool_name")
                parameters = message.payload.get("parameters", {})
                
                if tool_name in self.tool_registry.list_tools():
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        parameters=parameters,
                        caller_agent_id=message.sender_id
                    )
                    
                    result = await self._execute_tool_call(tool_call)
                    
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="tool_response",
                        payload={
                            "result": result.result,
                            "status": result.status.value,
                            "error_message": result.error_message,
                            "execution_time": result.execution_time
                        },
                        correlation_id=message.message_id,
                        priority=message.priority
                    )
                else:
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="error",
                        payload={"error": f"Tool {tool_name} not found"},
                        correlation_id=message.message_id,
                        priority=message.priority
                    )
            
            elif message.message_type == "coordination_request":
                # Handle coordination requests from other agents
                task_description = message.payload.get("task_description")
                required_agents = message.payload.get("required_agents", [])
                
                # Check if this agent is needed for the coordination
                if "llm_agent" in required_agents or self.agent_id in required_agents:
                    # Acknowledge participation in coordination
                    return AgentMessage(
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        message_type="coordination_response",
                        payload={
                            "status": "accepted",
                            "capabilities": [cap.dict() for cap in self.state.capabilities],
                            "estimated_time": "30s",  # Mock estimation
                            "agent_id": self.agent_id
                        },
                        correlation_id=message.message_id,
                        priority=message.priority
                    )
            
            elif message.message_type == "plugin_load_request":
                # Handle plugin loading requests
                plugin_name = message.payload.get("plugin_name")
                plugin_config = message.payload.get("plugin_config", {})
                
                # This would load a plugin module in a real implementation
                success = True  # Mock success
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="plugin_load_response",
                    payload={
                        "status": "loaded" if success else "failed",
                        "plugin_name": plugin_name,
                        "available_tools": self.tool_registry.list_tools()
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "status_request":
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="status_response",
                    payload={
                        "state": self.state.dict(),
                        "performance_metrics": self.performance_metrics,
                        "session_stats": self.session_manager.get_session_stats(),
                        "model_info": self.model_manager.get_model_info(),
                        "available_tools": self.tool_registry.list_tools(),
                        "tool_metrics": self.tool_executor.get_metrics()
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
            return AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type="error",
                payload={"error": str(e)},
                correlation_id=message.message_id,
                priority=message.priority
            )
    
    async def register_external_tool(self, tool_info: Dict[str, Any]) -> bool:
        """Register a new external tool for use by the LLM"""
        try:
            # Convert tool_info to ToolDefinition format
            parameters = []
            if "parameters" in tool_info:
                param_props = tool_info["parameters"].get("properties", {})
                required_params = tool_info["parameters"].get("required", [])
                
                for param_name, param_schema in param_props.items():
                    parameters.append(ToolParameter(
                        name=param_name,
                        type=param_schema.get("type", "string"),
                        description=param_schema.get("description", ""),
                        required=param_name in required_params,
                        default=param_schema.get("default"),
                        enum_values=param_schema.get("enum")
                    ))
            
            # Register as agent integration tool
            return self.tool_registry.register_agent_integration(
                name=tool_info["name"],
                description=tool_info.get("description", ""),
                agent_id=tool_info.get("agent_id", "unknown"),
                parameters=parameters
            )
            
        except Exception as e:
            self.logger.error(f"External tool registration failed: {e}")
            return False
    
    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        return self.tool_registry.unregister_tool(tool_name)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools"""
        return self.tool_registry.list_tools()
    
    async def load_plugin(self, plugin_name: str, plugin_module: Any) -> bool:
        """Load a plugin with additional tools"""
        return self.plugin_system.load_plugin(plugin_name, plugin_module)
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        return self.plugin_system.unload_plugin(plugin_name)
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugins"""
        return self.plugin_system.list_plugins()
    
    async def register_agent_tool(self, agent_id: str, tool_definition: Dict[str, Any]) -> bool:
        """Register a tool provided by another agent"""
        try:
            # Convert tool definition to our format
            parameters = []
            if "parameters" in tool_definition:
                param_props = tool_definition["parameters"].get("properties", {})
                required_params = tool_definition["parameters"].get("required", [])
                
                for param_name, param_schema in param_props.items():
                    parameters.append(ToolParameter(
                        name=param_name,
                        type=param_schema.get("type", "string"),
                        description=param_schema.get("description", ""),
                        required=param_name in required_params,
                        default=param_schema.get("default"),
                        enum_values=param_schema.get("enum")
                    ))
            
            # Register as agent integration tool
            success = self.tool_registry.register_agent_integration(
                name=tool_definition["name"],
                description=tool_definition.get("description", ""),
                agent_id=agent_id,
                parameters=parameters,
                timeout_seconds=tool_definition.get("timeout", 30)
            )
            
            if success:
                self.logger.info(f"Registered tool {tool_definition['name']} from agent {agent_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to register agent tool: {e}")
            return False
    
    async def discover_agent_tools(self, agent_id: str) -> List[Dict[str, Any]]:
        """Discover available tools from another agent"""
        try:
            # Send tool discovery request
            discovery_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=agent_id,
                message_type="tool_discovery_request",
                payload={}
            )
            
            if self.message_bus:
                # In a real implementation, this would wait for response
                # For now, return mock tools
                return [
                    {
                        "name": f"{agent_id}_primary_function",
                        "description": f"Primary function of {agent_id}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string", "description": "Input data"}
                            },
                            "required": ["input"]
                        }
                    }
                ]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Tool discovery failed for agent {agent_id}: {e}")
            return []
    
    async def broadcast_tool_availability(self) -> bool:
        """Broadcast available tools to other agents"""
        try:
            available_tools = []
            for tool_name in self.tool_registry.list_tools():
                tool_def = self.tool_registry.get_tool_definition(tool_name)
                if tool_def and tool_def.tool_type == ToolType.FUNCTION:
                    available_tools.append({
                        "name": tool_name,
                        "description": tool_def.description,
                        "parameters": tool_def.to_openai_function()["parameters"],
                        "agent_id": self.agent_id
                    })
            
            # Broadcast tool availability
            if self.message_bus and available_tools:
                await self.message_bus.send_notification(
                    sender_id=self.agent_id,
                    notification_data={
                        "event": "tools_available",
                        "agent_id": self.agent_id,
                        "tools": available_tools
                    }
                )
                
                self.logger.info(f"Broadcasted {len(available_tools)} available tools")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast tool availability: {e}")
            return False
    
    async def create_tool_chain(self, tools: List[str], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and execute a chain of tool calls"""
        try:
            results = []
            current_data = input_data
            
            for tool_name in tools:
                # Create tool call
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=current_data,
                    caller_agent_id=self.agent_id
                )
                
                # Execute tool
                result = await self._execute_tool_call(tool_call)
                results.append({
                    "tool": tool_name,
                    "status": result.status.value,
                    "result": result.result,
                    "execution_time": result.execution_time
                })
                
                # Use result as input for next tool (if successful)
                if result.status.value == "completed" and isinstance(result.result, dict):
                    current_data.update(result.result)
                elif result.status.value != "completed":
                    # Chain broken, return partial results
                    break
            
            return {
                "chain_status": "completed" if all(r["status"] == "completed" for r in results) else "partial",
                "results": results,
                "final_data": current_data
            }
            
        except Exception as e:
            self.logger.error(f"Tool chain execution failed: {e}")
            return {
                "chain_status": "failed",
                "error": str(e),
                "results": results if 'results' in locals() else []
            }
    
    def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        executor_metrics = self.tool_executor.get_metrics()
        
        return {
            "total_tools_registered": len(self.tool_registry.list_tools()),
            "tools_by_type": {
                tool_type.value: len(self.tool_registry.get_tools_by_type(tool_type))
                for tool_type in ToolType
            },
            "execution_metrics": executor_metrics,
            "plugins_loaded": len(self.plugin_system.list_plugins()),
            "agent_integrations": len([
                tool for tool in self.tool_registry.list_tools()
                if self.tool_registry.get_tool_definition(tool).tool_type == ToolType.AGENT_INTEGRATION
            ])
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        context = self.session_manager.get_session(session_id)
        if context:
            return {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "language": context.language,
                "current_intent": context.current_intent,
                "entities": context.entities,
                "conversation_length": len(context.conversation_history),
                "token_count": context.token_count,
                "created_at": context.created_at.isoformat(),
                "last_updated": context.last_updated.isoformat()
            }
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "state": self.state.dict(),
            "session_stats": self.session_manager.get_session_stats(),
            "model_info": self.model_manager.get_model_info(),
            "tool_metrics": self.tool_executor.get_metrics(),
            "dialog_stats": self.dialog_manager.get_dialog_stats()
        }
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        self.session_manager.cleanup_expired_sessions()
    
    async def handle_interruption(self, session_id: str, new_input: str) -> Dict[str, Any]:
        """Handle conversation interruption and context switching"""
        try:
            context = self.session_manager.get_session(session_id)
            if not context:
                return {"error": "Session not found"}
            
            # Save current state
            previous_intent = context.current_intent
            previous_entities = context.entities.copy()
            
            # Process interruption
            context.add_message("user", f"[INTERRUPTION] {new_input}")
            
            # Recognize new intent
            intent_result = await self.intent_recognizer.recognize_intent(new_input, context)
            
            # Update context with new intent
            context.update_intent(intent_result.intent, intent_result.confidence)
            context.update_entities(intent_result.entities)
            
            # Generate response for interruption
            system_prompt = f"{self._get_system_prompt(context)}\n\nThe user has interrupted the conversation. Handle this gracefully and address their new request."
            response = await self.model_manager.generate_response(context, system_prompt)
            
            context.add_message("assistant", response)
            self.session_manager.update_session(session_id, context)
            
            return {
                "response": response,
                "previous_intent": previous_intent,
                "new_intent": intent_result.intent,
                "context_switched": True,
                "session_id": session_id
            }
            
        except Exception as e:
            self.logger.error(f"Interruption handling failed: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown the LLM agent"""
        self.logger.info(f"Shutting down LLM Agent {self.agent_id}")
        
        # Clean up sessions
        self.session_manager.sessions.clear()
        
        # Clear model cache
        self.model_manager.models_cache.clear()
        
        self.state.status = "offline"
        self.logger.info(f"LLM Agent {self.agent_id} shutdown complete")
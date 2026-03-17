# Agent Interface Documentation

## Overview

The EUVoice AI Platform uses a multi-agent architecture where specialized agents handle different aspects of voice processing. This document describes the standardized interfaces and protocols that all agents must implement.

## Agent Interface Specification

### Base Agent Interface

All agents must implement the following interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.core.models import AgentMessage, AgentCapability, AgentState

class BaseAgent(ABC):
    """Base interface that all agents must implement"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration"""
        pass
    
    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return response"""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[AgentCapability]:
        """Return list of agent capabilities"""
        pass
    
    @abstractmethod
    async def get_state(self) -> AgentState:
        """Return current agent state and health"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent"""
        pass
```

### Agent Registration

Agents register themselves with the framework using:

```python
from src.core.models import AgentRegistration, AgentCapability

registration = AgentRegistration(
    agent_id="unique_agent_id",
    agent_type="STT|LLM|TTS|EMOTION|ACCENT|LIPSYNC|ARABIC|CUSTOM",
    capabilities=[
        AgentCapability(
            name="capability_name",
            description="Human readable description",
            input_schema={"field": "type"},
            output_schema={"field": "type"},
            performance_metrics={
                "latency_ms": 50,
                "accuracy": 0.95,
                "throughput_rps": 100
            }
        )
    ],
    endpoint="http://agent-service:8080",
    health_check_endpoint="http://agent-service:8080/health",
    metadata={
        "version": "1.0.0",
        "model": "mistral-voxtral-small",
        "languages": ["en", "fr", "de", "es"]
    }
)
```

## Core Agent Types

### STT (Speech-to-Text) Agent

**Purpose**: Convert audio input to text with language detection and accent recognition.

**Capabilities**:
- `speech_to_text`: Primary transcription capability
- `language_detection`: Automatic language identification
- `accent_detection`: Regional accent recognition
- `real_time_streaming`: Incremental transcription

**Input Schema**:
```json
{
  "audio": "bytes|base64",
  "format": "wav|mp3|flac|opus",
  "sample_rate": "integer",
  "language": "string|auto",
  "enable_accent_detection": "boolean",
  "enable_emotion_analysis": "boolean",
  "streaming": "boolean"
}
```

**Output Schema**:
```json
{
  "text": "string",
  "confidence": "float",
  "language": "string",
  "accent": "string",
  "emotion": {
    "primary": "string",
    "confidence": "float",
    "sentiment": "float"
  },
  "timestamps": [
    {"start": "float", "end": "float", "word": "string"}
  ],
  "is_partial": "boolean"
}
```

**Example Implementation**:
```python
class STTAgent(BaseAgent):
    async def process(self, message: AgentMessage) -> AgentMessage:
        audio_data = message.payload.get("audio")
        language = message.payload.get("language", "auto")
        
        # Process audio through Mistral Voxtral
        result = await self.transcribe_audio(audio_data, language)
        
        return AgentMessage(
            agent_id=self.agent_id,
            task_id=message.task_id,
            message_type="response",
            payload=result
        )
```

### LLM (Large Language Model) Agent

**Purpose**: Handle dialog management, reasoning, and tool calling.

**Capabilities**:
- `dialog_management`: Conversation state tracking
- `intent_recognition`: Intent and entity extraction
- `tool_calling`: External tool integration
- `context_management`: Long-term context handling

**Input Schema**:
```json
{
  "text": "string",
  "context": {
    "session_id": "string",
    "user_id": "string",
    "conversation_history": "array",
    "user_preferences": "object"
  },
  "available_tools": "array",
  "max_tokens": "integer",
  "temperature": "float"
}
```

**Output Schema**:
```json
{
  "response": "string",
  "intent": "string",
  "entities": "array",
  "tool_calls": "array",
  "context_updated": "boolean",
  "confidence": "float",
  "reasoning": "string"
}
```

### TTS (Text-to-Speech) Agent

**Purpose**: Convert text to natural speech with voice cloning and emotion.

**Capabilities**:
- `text_to_speech`: Primary synthesis capability
- `voice_cloning`: Custom voice generation
- `emotion_synthesis`: Emotion-aware speech
- `multilingual_synthesis`: Multiple language support

**Input Schema**:
```json
{
  "text": "string",
  "voice": "string|voice_id",
  "language": "string",
  "emotion": "string",
  "speed": "float",
  "pitch": "float",
  "volume": "float",
  "output_format": "wav|mp3|opus"
}
```

**Output Schema**:
```json
{
  "audio_data": "bytes|base64",
  "audio_url": "string",
  "duration": "float",
  "format": "string",
  "sample_rate": "integer",
  "lip_sync_data": {
    "phonemes": "array",
    "timestamps": "array"
  }
}
```

### Specialized Feature Agents

#### Emotion Agent
Detects emotions from audio and provides emotional context.

**Capabilities**: `emotion_detection`, `sentiment_analysis`

#### Accent Agent  
Recognizes regional accents and adapts processing accordingly.

**Capabilities**: `accent_detection`, `regional_adaptation`

#### Lip Sync Agent
Generates facial animation data synchronized with speech.

**Capabilities**: `lip_sync_generation`, `phoneme_mapping`

#### Arabic Agent
Specialized processing for Arabic language and dialects.

**Capabilities**: `arabic_processing`, `dialect_recognition`, `diacritization`

## Communication Protocols

### Message Format

All inter-agent communication uses the standardized `AgentMessage` format:

```python
@dataclass
class AgentMessage:
    agent_id: str
    task_id: str
    message_type: str  # "request", "response", "notification", "error"
    payload: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    retry_count: int = 0
    expires_at: Optional[datetime] = None
```

### Message Types

1. **Request**: Agent requesting processing from another agent
2. **Response**: Response to a previous request
3. **Notification**: Broadcast information to interested agents
4. **Error**: Error information and recovery instructions

### Message Routing

Messages are routed through the central `MessageRouter`:

```python
# Send message to specific agent
await message_router.send_to_agent("target_agent_id", message)

# Broadcast to all agents of a type
await message_router.broadcast_to_type("STT", message)

# Send to best available agent with capability
await message_router.send_to_capability("speech_to_text", message)
```

## Agent Lifecycle

### 1. Registration Phase
```python
# Agent registers with the framework
await framework.register_agent(registration)
```

### 2. Active Phase
```python
# Agent processes messages
while active:
    message = await message_queue.get()
    response = await agent.process(message)
    await message_router.send_response(response)
```

### 3. Health Monitoring
```python
# Framework monitors agent health
health = await agent.get_state()
if health.status == AgentStatus.UNHEALTHY:
    await framework.handle_unhealthy_agent(agent_id)
```

### 4. Shutdown Phase
```python
# Graceful shutdown
await agent.shutdown()
await framework.unregister_agent(agent_id)
```

## Performance Requirements

### Latency Targets
- **STT Agent**: < 100ms for real-time streaming
- **LLM Agent**: < 200ms for simple queries
- **TTS Agent**: < 150ms for short text synthesis
- **Feature Agents**: < 50ms for analysis tasks

### Accuracy Targets
- **STT**: > 95% for major EU languages
- **LLM**: > 90% intent recognition accuracy
- **TTS**: > 4.0 MOS (Mean Opinion Score)
- **Emotion**: > 85% emotion detection accuracy

### Throughput Requirements
- **Concurrent Sessions**: 1000+ per agent instance
- **Requests per Second**: 100+ per agent
- **Scalability**: Horizontal scaling support

## Error Handling

### Error Types
```python
class AgentError(Exception):
    def __init__(self, code: str, message: str, recoverable: bool = True):
        self.code = code
        self.message = message
        self.recoverable = recoverable
```

### Common Error Codes
- `AGENT_UNAVAILABLE`: Agent is not responding
- `CAPABILITY_NOT_SUPPORTED`: Requested capability not available
- `PROCESSING_FAILED`: Error during message processing
- `TIMEOUT_EXCEEDED`: Processing took too long
- `RESOURCE_EXHAUSTED`: Agent at capacity

### Recovery Strategies
1. **Retry**: Automatic retry with exponential backoff
2. **Failover**: Route to backup agent instance
3. **Degradation**: Use simpler processing method
4. **Circuit Breaker**: Temporarily disable failing agent

## Security and Compliance

### Authentication
Agents authenticate using mutual TLS certificates:

```python
# Agent certificate configuration
agent_config = {
    "cert_file": "/etc/certs/agent.crt",
    "key_file": "/etc/certs/agent.key",
    "ca_file": "/etc/certs/ca.crt"
}
```

### Data Protection
- All inter-agent communication is encrypted
- Sensitive data is automatically anonymized
- Audit logs track all agent interactions
- GDPR compliance built into message handling

### Access Control
Agents have role-based access to capabilities:

```python
class AgentRole:
    CORE_PROCESSOR = "core_processor"      # STT, LLM, TTS
    FEATURE_ANALYZER = "feature_analyzer"  # Emotion, Accent
    SYSTEM_MONITOR = "system_monitor"      # Health, Performance
    DATA_PROCESSOR = "data_processor"      # Dataset, Training
```

## Development Guidelines

### Creating a New Agent

1. **Inherit from BaseAgent**:
```python
class MyCustomAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = config["agent_id"]
```

2. **Implement Required Methods**:
```python
async def initialize(self, config: Dict[str, Any]) -> None:
    # Initialize models, connections, etc.
    pass

async def process(self, message: AgentMessage) -> AgentMessage:
    # Main processing logic
    pass
```

3. **Define Capabilities**:
```python
async def get_capabilities(self) -> List[AgentCapability]:
    return [
        AgentCapability(
            name="my_capability",
            description="Custom processing capability",
            input_schema={"input": "string"},
            output_schema={"output": "string"}
        )
    ]
```

4. **Register with Framework**:
```python
registration = AgentRegistration(
    agent_id="my_custom_agent",
    agent_type="CUSTOM",
    capabilities=await agent.get_capabilities(),
    endpoint="http://localhost:8080"
)
await framework.register_agent(registration)
```

### Testing Agents

Use the provided test utilities:

```python
from src.core.testing import AgentTestSuite

class TestMyAgent(AgentTestSuite):
    async def test_basic_processing(self):
        message = self.create_test_message({
            "input": "test data"
        })
        
        response = await self.agent.process(message)
        
        assert response.message_type == "response"
        assert "output" in response.payload
```

### Deployment

Agents can be deployed as:
1. **Standalone Services**: Independent microservices
2. **Embedded Agents**: Within the main framework process
3. **Serverless Functions**: For lightweight processing
4. **Container Instances**: Kubernetes pods with auto-scaling

## Monitoring and Observability

### Metrics Collection
Agents automatically report metrics:

```python
# Performance metrics
await self.report_metric("processing_latency", latency_ms)
await self.report_metric("accuracy_score", accuracy)
await self.report_metric("throughput_rps", requests_per_second)

# Custom metrics
await self.report_custom_metric("model_confidence", confidence)
```

### Health Checks
Implement health check endpoints:

```python
async def health_check(self) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "uptime": self.get_uptime(),
        "memory_usage": self.get_memory_usage(),
        "model_loaded": self.model is not None
    }
```

### Logging
Use structured logging for observability:

```python
import structlog

logger = structlog.get_logger()

await logger.info(
    "message_processed",
    agent_id=self.agent_id,
    task_id=message.task_id,
    latency_ms=processing_time,
    success=True
)
```

## Best Practices

1. **Stateless Design**: Agents should be stateless for easy scaling
2. **Graceful Degradation**: Handle failures gracefully
3. **Resource Management**: Properly manage memory and GPU resources
4. **Configuration**: Use environment variables for configuration
5. **Monitoring**: Implement comprehensive health checks and metrics
6. **Testing**: Write thorough unit and integration tests
7. **Documentation**: Document all capabilities and interfaces
8. **Security**: Follow security best practices for data handling

## Community Contributions

To contribute a new agent:

1. Fork the repository
2. Create agent following the interface specification
3. Add comprehensive tests
4. Update documentation
5. Submit pull request with agent description

See `CONTRIBUTING.md` for detailed guidelines.
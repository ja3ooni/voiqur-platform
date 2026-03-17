# EUVoice AI Platform Developer Guide

## Introduction

This guide provides comprehensive information for developers who want to extend, customize, or contribute to the EUVoice AI Platform.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Environment](#development-environment)
- [Core Concepts](#core-concepts)
- [Creating Custom Agents](#creating-custom-agents)
- [API Development](#api-development)
- [Testing](#testing)
- [Performance Optimization](#performance-optimization)
- [Deployment](#deployment)

## Architecture Overview

### Multi-Agent System

The platform uses a multi-agent architecture where specialized agents coordinate to provide voice processing capabilities:

```
┌─────────────────────────────────────────────────┐
│         Agent Orchestration Layer               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Registry │  │ Message  │  │ Quality  │     │
│  │          │  │ Router   │  │ Monitor  │     │
│  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼───┐   ┌────▼───┐   ┌────▼───┐
   │  STT   │   │  LLM   │   │  TTS   │
   │ Agent  │   │ Agent  │   │ Agent  │
   └────────┘   └────────┘   └────────┘
```

### Key Components

1. **Agent Orchestrator**: Coordinates agent activities
2. **Message Router**: Routes messages between agents
3. **Service Registry**: Tracks available agents
4. **Knowledge Base**: Shared knowledge storage
5. **Quality Monitor**: Monitors system health

## Development Environment

### Setup

```bash
# Clone repository
git clone https://github.com/euvoice/euvoice-ai-platform.git
cd euvoice-ai-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start services
docker-compose up -d

# Run tests
pytest
```

### Project Structure

```
euvoice-ai-platform/
├── src/
│   ├── agents/          # Agent implementations
│   ├── api/             # REST API
│   ├── core/            # Core framework
│   ├── compliance/      # GDPR/AI Act compliance
│   ├── monitoring/      # Monitoring and metrics
│   └── security/        # Security features
├── tests/               # Test suite
├── docs/                # Documentation
├── k8s/                 # Kubernetes configs
├── examples/            # Example code
└── requirements.txt     # Dependencies
```

## Core Concepts

### Agent Interface

All agents implement the `BaseAgent` interface:

```python
from abc import ABC, abstractmethod
from src.core.models import AgentMessage, AgentCapability

class BaseAgent(ABC):
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with configuration"""
        pass
    
    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process incoming message"""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[AgentCapability]:
        """Return agent capabilities"""
        pass
    
    @abstractmethod
    async def get_state(self) -> AgentState:
        """Return current state"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass
```

### Message Protocol

Agents communicate using standardized messages:

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
```

### Agent Registration

Agents register their capabilities:

```python
registration = AgentRegistration(
    agent_id="my_agent",
    agent_type="CUSTOM",
    capabilities=[
        AgentCapability(
            name="custom_processing",
            description="Custom processing",
            input_schema={"input": "string"},
            output_schema={"output": "string"}
        )
    ],
    endpoint="http://localhost:8080"
)

await framework.register_agent(registration)
```

## Creating Custom Agents

### Step 1: Define Agent Class

```python
from src.agents.base import BaseAgent
from src.core.models import AgentMessage, AgentCapability

class MyCustomAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agent_id = config["agent_id"]
        self.model = self._load_model(config["model_path"])
    
    def _load_model(self, path: str):
        # Load your model
        pass
```

### Step 2: Implement Processing Logic

```python
async def process(self, message: AgentMessage) -> AgentMessage:
    try:
        # Extract input
        input_data = message.payload.get("input")
        
        # Process
        result = await self._process_data(input_data)
        
        # Return response
        return AgentMessage(
            agent_id=self.agent_id,
            task_id=message.task_id,
            message_type="response",
            payload={"result": result}
        )
    except Exception as e:
        return AgentMessage(
            agent_id=self.agent_id,
            task_id=message.task_id,
            message_type="error",
            payload={"error": str(e)}
        )
```

### Step 3: Define Capabilities

```python
async def get_capabilities(self) -> List[AgentCapability]:
    return [
        AgentCapability(
            name="custom_processing",
            description="Process custom data",
            input_schema={
                "input": "string",
                "options": "object"
            },
            output_schema={
                "result": "object",
                "confidence": "float"
            },
            performance_metrics={
                "latency_ms": 50,
                "accuracy": 0.95
            }
        )
    ]
```

### Step 4: Add Tests

```python
import pytest
from src.agents.my_custom_agent import MyCustomAgent

@pytest.fixture
async def agent():
    config = {"agent_id": "test_agent", "model_path": "/models/test"}
    agent = MyCustomAgent(config)
    await agent.initialize(config)
    yield agent
    await agent.shutdown()

@pytest.mark.asyncio
async def test_processing(agent):
    message = AgentMessage(
        agent_id="test",
        task_id="task_1",
        message_type="request",
        payload={"input": "test data"}
    )
    
    response = await agent.process(message)
    
    assert response.message_type == "response"
    assert "result" in response.payload
```

## API Development

### Adding New Endpoints

```python
from fastapi import APIRouter, Depends
from src.api.auth import get_current_user

router = APIRouter()

@router.post("/custom/process")
async def process_custom(
    data: CustomRequest,
    user = Depends(get_current_user)
):
    """Process custom data."""
    # Implementation
    return {"result": "processed"}
```

### Request/Response Models

```python
from pydantic import BaseModel, Field

class CustomRequest(BaseModel):
    input: str = Field(..., description="Input data")
    options: Dict[str, Any] = Field(default_factory=dict)

class CustomResponse(BaseModel):
    result: Any
    confidence: float
    processing_time: float
```

### Error Handling

```python
from fastapi import HTTPException

@router.post("/process")
async def process(data: CustomRequest):
    try:
        result = await process_data(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")
```

## Testing

### Unit Tests

```python
import pytest
from src.core.messaging import MessageRouter

@pytest.mark.asyncio
async def test_message_routing():
    router = MessageRouter()
    
    # Test message delivery
    message = AgentMessage(...)
    await router.send_to_agent("target_agent", message)
    
    # Verify delivery
    assert message.delivered
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_agent_integration():
    # Start framework
    framework = MultiAgentFramework()
    await framework.start()
    
    # Register agents
    await framework.register_agent(stt_registration)
    await framework.register_agent(llm_registration)
    
    # Test interaction
    result = await framework.process_audio(audio_data)
    
    assert result.text is not None
    
    await framework.stop()
```

### Performance Tests

```python
import time

@pytest.mark.performance
async def test_latency():
    start = time.time()
    result = await agent.process(message)
    latency = (time.time() - start) * 1000
    
    assert latency < 100  # < 100ms
```

## Performance Optimization

### Async Processing

```python
import asyncio

async def process_batch(items: List[Any]):
    # Process items concurrently
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results
```

### Caching

```python
from functools import lru_cache
import redis

# In-memory cache
@lru_cache(maxsize=1000)
def get_model_config(model_id: str):
    return load_config(model_id)

# Redis cache
redis_client = redis.Redis()

async def get_cached_result(key: str):
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    result = await compute_result()
    redis_client.setex(key, 3600, json.dumps(result))
    return result
```

### GPU Optimization

```python
import torch

# Use mixed precision
with torch.cuda.amp.autocast():
    output = model(input_tensor)

# Batch processing
def process_batch(inputs: List[torch.Tensor]):
    batch = torch.stack(inputs)
    with torch.no_grad():
        outputs = model(batch)
    return outputs.split(1)
```

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30
)
```

## Deployment

### Docker Build

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY models/ ./models/

CMD ["python", "-m", "src.api.main"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: custom-agent
  template:
    metadata:
      labels:
        app: custom-agent
    spec:
      containers:
      - name: agent
        image: euvoice/custom-agent:latest
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
```

### Monitoring

```python
from prometheus_client import Counter, Histogram

# Define metrics
requests_total = Counter(
    'agent_requests_total',
    'Total requests processed'
)

processing_time = Histogram(
    'agent_processing_seconds',
    'Time spent processing requests'
)

# Use metrics
@processing_time.time()
async def process(message):
    requests_total.inc()
    # Process message
```

## Best Practices

1. **Use Type Hints**: Add type hints to all functions
2. **Write Tests**: Aim for 80%+ code coverage
3. **Document Code**: Add docstrings and comments
4. **Handle Errors**: Implement proper error handling
5. **Log Appropriately**: Use structured logging
6. **Optimize Performance**: Profile and optimize hot paths
7. **Follow Standards**: Adhere to PEP 8 and project conventions
8. **Security First**: Validate inputs, sanitize outputs
9. **EU Compliance**: Ensure GDPR compliance
10. **Monitor Everything**: Add metrics and logging

## Resources

- [API Documentation](api/README.md)
- [Agent Documentation](agents/README.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Community Forum](https://community.euvoice.ai)
- [GitHub Repository](https://github.com/euvoice/euvoice-ai-platform)

## Support

- **Technical Questions**: developers@euvoice.ai
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions
- **Security Issues**: security@euvoice.ai

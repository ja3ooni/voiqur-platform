# EUVoice AI Multi-Agent Framework

A comprehensive multi-agent framework for building, deploying, and managing voice assistants tailored for European, Asian, African, and Middle Eastern languages. This framework implements the foundational components for coordinated multi-agent development and operation.

## Overview

The EUVoice AI Multi-Agent Framework provides the core infrastructure for managing multiple specialized AI agents that work together to build and operate voice assistant systems. The framework emphasizes EU compliance, data sovereignty, and support for low-resource languages.

## Documentation

📚 **[Complete Documentation](docs/README.md)**

### Quick Links
- **[User Guide](docs/USER_GUIDE.md)** - Get started with using the platform
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Extend and customize the platform
- **[API Documentation](docs/api/README.md)** - REST/WebSocket API reference
- **[Deployment Guide](docs/deployment/README.md)** - Production deployment
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[FAQ](docs/FAQ.md)** - Frequently asked questions

## Architecture

The framework consists of several core components:

### 1. Agent Communication Protocol (`src/core/models.py`, `src/core/messaging.py`)
- **AgentMessage**: Standardized message format based on OpenAI function calling patterns
- **MessageRouter**: Central message routing with priority queuing
- **MessageBus**: High-level messaging interface for common patterns
- **Priority queuing** with automatic message expiration and retry mechanisms

### 2. Agent Discovery and Registration (`src/core/discovery.py`)
- **ServiceRegistry**: Central registry for agent discovery and health monitoring
- **AgentDiscoveryClient**: Client-side discovery functionality
- **Health monitoring** with automatic failover and recovery
- **Capability-based agent selection** with performance metrics

### 3. Agent Orchestration (`src/core/orchestration.py`)
- **AgentOrchestrator**: Task distribution and load balancing
- **Multiple load balancing strategies**: Round-robin, least-loaded, performance-based, capability-based
- **Dependency management** with automatic task scheduling
- **Timeout handling** and task recovery mechanisms

### 4. Coordination Controller (`src/core/coordination.py`)
- **Multi-agent workflow management** with dependencies and synchronization
- **SynchronizationPoint**: Coordinate multiple agents at specific points
- **ConflictResolution**: Handle conflicts between concurrent operations
- **Workflow execution** with step-by-step coordination

### 5. Quality Monitor (`src/core/quality_monitor.py`)
- **Real-time performance monitoring** for all agents
- **Health status tracking** with configurable thresholds
- **Alert system** with automatic resolution
- **Comprehensive metrics**: Latency, throughput, error rates, resource usage

### 6. Shared Knowledge Base (`src/core/knowledge_base.py`)
- **Distributed storage** with Redis/PostgreSQL backend
- **Knowledge sharing protocols** between agents
- **Conflict resolution** for concurrent knowledge updates
- **Access control** with different permission levels
- **Knowledge validation** and confidence scoring

## Key Features

### Multi-Agent Coordination
- **Standardized communication** using OpenAI function calling patterns
- **Automatic agent discovery** and registration
- **Load balancing** across multiple agent instances
- **Dependency management** for complex workflows
- **Real-time synchronization** points for coordinated operations

### EU Compliance & Data Sovereignty
- **GDPR-compliant** data handling and anonymization
- **EU-only hosting** requirements enforcement
- **Audit logging** for compliance reporting
- **Data encryption** at rest and in transit

### Performance & Reliability
- **Sub-100ms latency** requirements monitoring
- **Automatic failover** and recovery mechanisms
- **Health monitoring** with configurable thresholds
- **Performance optimization** based on real-time metrics
- **Circuit breaker patterns** for fault tolerance

### Knowledge Management
- **Distributed knowledge storage** with conflict resolution
- **Version control** and validation mechanisms
- **Access control** with different permission levels
- **Real-time knowledge sharing** between agents
- **Automatic cleanup** of expired knowledge

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up databases:
   - Redis server for caching and real-time data
   - PostgreSQL for persistent storage

3. Configure connection URLs in your application or use defaults:
   - Redis: `redis://localhost:6379`
   - PostgreSQL: `postgresql://localhost:5432/euvoice`

## Quick Start

```python
import asyncio
from src.multi_agent_framework import MultiAgentFramework
from src.core import AgentRegistration, AgentCapability, Task

async def main():
    # Create and start the framework
    framework = MultiAgentFramework()
    await framework.start()
    
    try:
        # Register an agent
        capabilities = [
            AgentCapability(
                name="speech_to_text",
                description="Convert speech to text",
                input_schema={"audio": "bytes"},
                output_schema={"text": "string"}
            )
        ]
        
        registration = AgentRegistration(
            agent_id="stt_agent_001",
            agent_type="STT",
            capabilities=capabilities,
            endpoint="http://localhost:8001/stt"
        )
        
        await framework.register_agent(registration)
        
        # Submit a task
        task = Task(
            description="Transcribe audio file",
            context={
                "required_capabilities": ["speech_to_text"],
                "input_data": {"audio_file": "example.wav"}
            }
        )
        
        await framework.submit_task(task)
        
        # Monitor system health
        health = framework.get_system_health()
        print(f"System health: {health['health_percentage']:.2%}")
        
    finally:
        await framework.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Examples

See the `examples/` directory for comprehensive usage examples:

- `basic_usage.py`: Complete example showing agent registration, task submission, knowledge sharing, and monitoring

## Framework Components

### Core Models
- **AgentMessage**: Standardized inter-agent communication
- **AgentState**: Agent status and performance tracking
- **Task**: Work units with dependencies and requirements
- **KnowledgeItem**: Shared knowledge with access control

### Message Routing
- **Priority-based queuing** with automatic expiration
- **Broadcast and unicast** messaging patterns
- **Retry mechanisms** with exponential backoff
- **Message correlation** for request-response tracking

### Agent Management
- **Automatic discovery** and registration
- **Health monitoring** with configurable intervals
- **Performance tracking** and optimization
- **Capability-based selection** for task assignment

### Quality Assurance
- **Real-time monitoring** of all system components
- **Configurable alerts** with automatic resolution
- **Performance metrics** collection and analysis
- **System health** reporting and dashboards

## Configuration

The framework supports various configuration options:

```python
framework = MultiAgentFramework(
    redis_url="redis://localhost:6379",
    postgres_url="postgresql://localhost:5432/euvoice"
)

# Configure component-specific settings
framework.orchestrator.max_concurrent_tasks_per_agent = 5
framework.quality_monitor.monitoring_interval = 10.0
framework.knowledge_base.cache_ttl = 600
```

## Monitoring and Observability

The framework provides comprehensive monitoring capabilities:

- **System-wide metrics**: Total throughput, average latency, error rates
- **Agent-specific metrics**: Individual performance, health status, resource usage
- **Real-time alerts**: Configurable thresholds with automatic notifications
- **Historical data**: Performance trends and capacity planning

## Requirements Addressed

This implementation addresses the following requirements from the specification:

- **REQ-1.1**: Multi-agent system with specialized agents for different components
- **REQ-1.2**: Conflict-free coordination between agents working on different components
- **REQ-1.3**: Automatic notification and knowledge base updates
- **REQ-1.4**: Coordinated changes through designated architecture patterns

## Next Steps

This foundation enables the development of specialized agents for:

1. **STT Agent**: Speech-to-text using Mistral Voxtral models
2. **LLM Agent**: Dialog management using Mistral Small 3.1
3. **TTS Agent**: Text-to-speech using XTTS-v2
4. **Specialized Feature Agents**: Emotion detection, accent recognition, lip sync
5. **Infrastructure Agents**: Frontend, deployment, integration

## Community and Support

### Getting Help
- **Documentation**: [docs/](docs/README.md)
- **Community Forum**: https://community.euvoice.ai
- **Discord**: https://discord.gg/euvoice
- **GitHub Issues**: [Report bugs or request features](https://github.com/euvoice/euvoice-ai-platform/issues)

### Contact
- **General Support**: support@euvoice.ai
- **Technical Questions**: developers@euvoice.ai
- **Security Issues**: security@euvoice.ai
- **Commercial Inquiries**: sales@euvoice.ai

### Contributing

We welcome contributions! The framework is designed to be extensible. New agents can be easily integrated by:

1. Implementing the standard agent interface
2. Registering capabilities with the service registry
3. Following the communication protocols
4. Participating in the health monitoring system

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Code of conduct
- Development setup
- Creating custom agents
- Testing requirements
- Pull request process

## License

Apache 2.0 - This project is designed for EU compliance and uses Apache 2.0 compatible licensing for all dependencies. See [LICENSE](LICENSE) file for details.
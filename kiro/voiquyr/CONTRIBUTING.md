# Contributing to EUVoice AI Platform

Thank you for your interest in contributing to the EUVoice AI Platform! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Agent Development](#agent-development)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background, identity, or experience level.

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors include:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of unacceptable behavior may be reported to the project team at conduct@euvoice.ai. All complaints will be reviewed and investigated promptly and fairly.

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Git
- Basic understanding of multi-agent systems
- Familiarity with FastAPI, asyncio, and modern Python

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/euvoice-ai-platform.git
cd euvoice-ai-platform

# Add upstream remote
git remote add upstream https://github.com/euvoice/euvoice-ai-platform.git
```

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Start Development Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run database migrations
python -m alembic upgrade head
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agents.py
```

### 5. Start Development Server

```bash
# Start API server
python -m src.api.main

# Or use uvicorn with auto-reload
uvicorn src.api.app:app --reload
```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

1. **Bug Reports**: Report issues you encounter
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Fix bugs or implement features
4. **Documentation**: Improve or add documentation
5. **Agent Development**: Create new specialized agents
6. **Testing**: Add or improve tests
7. **Translations**: Add support for new languages

### Reporting Bugs

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Detailed steps to reproduce the bug
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python version, relevant dependencies
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable

Use the bug report template:

```markdown
**Bug Description**
A clear and concise description of the bug.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What you expected to happen.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.10.5]
- EUVoice Version: [e.g., 1.0.0]

**Additional Context**
Add any other context about the problem here.
```

### Suggesting Features

When suggesting features, please include:

- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: Other solutions you've considered
- **Additional Context**: Any other relevant information

## Agent Development

### Creating a New Agent

1. **Define Agent Purpose**: Clearly define what your agent will do
2. **Implement Base Interface**: Inherit from `BaseAgent`
3. **Define Capabilities**: Specify agent capabilities
4. **Implement Processing Logic**: Core agent functionality
5. **Add Tests**: Comprehensive unit and integration tests
6. **Document**: Add documentation for your agent

### Agent Template

```python
"""
Custom Agent Implementation

Description of what this agent does.
"""

from typing import Dict, Any, List
from src.core.models import AgentMessage, AgentCapability, AgentState, AgentStatus
from src.agents.base import BaseAgent


class CustomAgent(BaseAgent):
    """
    Custom agent for [specific purpose].
    
    This agent handles [description of functionality].
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the custom agent.
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__(config)
        self.agent_id = config.get("agent_id", "custom_agent")
        self.agent_type = "CUSTOM"
        
        # Initialize your models, connections, etc.
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize models and resources."""
        # Load models, establish connections, etc.
        pass
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the agent with configuration.
        
        Args:
            config: Configuration dictionary
        """
        # Perform async initialization
        pass
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process an incoming message.
        
        Args:
            message: Incoming agent message
            
        Returns:
            Response message
        """
        try:
            # Extract input from message
            input_data = message.payload.get("input")
            
            # Process the input
            result = await self._process_input(input_data)
            
            # Return response
            return AgentMessage(
                agent_id=self.agent_id,
                task_id=message.task_id,
                message_type="response",
                payload={"result": result},
                correlation_id=message.correlation_id
            )
        except Exception as e:
            return AgentMessage(
                agent_id=self.agent_id,
                task_id=message.task_id,
                message_type="error",
                payload={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def _process_input(self, input_data: Any) -> Any:
        """
        Core processing logic.
        
        Args:
            input_data: Input to process
            
        Returns:
            Processing result
        """
        # Implement your processing logic here
        pass
    
    async def get_capabilities(self) -> List[AgentCapability]:
        """
        Return agent capabilities.
        
        Returns:
            List of agent capabilities
        """
        return [
            AgentCapability(
                name="custom_processing",
                description="Custom processing capability",
                input_schema={
                    "input": "string"
                },
                output_schema={
                    "result": "object"
                },
                performance_metrics={
                    "latency_ms": 50,
                    "accuracy": 0.95,
                    "throughput_rps": 100
                }
            )
        ]
    
    async def get_state(self) -> AgentState:
        """
        Return current agent state.
        
        Returns:
            Current agent state
        """
        return AgentState(
            agent_id=self.agent_id,
            status=AgentStatus.ACTIVE,
            current_task=None,
            performance_metrics={
                "requests_processed": self._requests_processed,
                "average_latency": self._average_latency,
                "error_rate": self._error_rate
            }
        )
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        # Cleanup resources
        pass
```

### Agent Testing Template

```python
"""
Tests for Custom Agent
"""

import pytest
from src.agents.custom_agent import CustomAgent
from src.core.models import AgentMessage


@pytest.fixture
async def custom_agent():
    """Create a custom agent for testing."""
    config = {
        "agent_id": "test_custom_agent",
        # Add other config parameters
    }
    agent = CustomAgent(config)
    await agent.initialize(config)
    yield agent
    await agent.shutdown()


@pytest.mark.asyncio
async def test_agent_initialization(custom_agent):
    """Test agent initializes correctly."""
    assert custom_agent.agent_id == "test_custom_agent"
    assert custom_agent.agent_type == "CUSTOM"


@pytest.mark.asyncio
async def test_agent_capabilities(custom_agent):
    """Test agent returns correct capabilities."""
    capabilities = await custom_agent.get_capabilities()
    assert len(capabilities) > 0
    assert capabilities[0].name == "custom_processing"


@pytest.mark.asyncio
async def test_agent_processing(custom_agent):
    """Test agent processes messages correctly."""
    message = AgentMessage(
        agent_id="test_sender",
        task_id="test_task",
        message_type="request",
        payload={"input": "test data"}
    )
    
    response = await custom_agent.process(message)
    
    assert response.message_type == "response"
    assert "result" in response.payload


@pytest.mark.asyncio
async def test_agent_error_handling(custom_agent):
    """Test agent handles errors gracefully."""
    message = AgentMessage(
        agent_id="test_sender",
        task_id="test_task",
        message_type="request",
        payload={"input": None}  # Invalid input
    )
    
    response = await custom_agent.process(message)
    
    assert response.message_type == "error"
    assert "error" in response.payload
```

## Testing Requirements

### Test Coverage

- **Minimum Coverage**: 80% for new code
- **Critical Paths**: 100% coverage for critical functionality
- **Integration Tests**: Test agent interactions
- **Performance Tests**: Verify latency requirements

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance

# Run tests in parallel
pytest -n auto
```

### Writing Tests

- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Use fixtures for common setup
- Add docstrings to test functions

## Documentation

### Documentation Standards

- **Code Comments**: Explain complex logic
- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Add type hints to all functions
- **README Updates**: Update README for new features
- **API Documentation**: Document all API endpoints

### Docstring Example

```python
def process_audio(
    audio_data: bytes,
    sample_rate: int = 16000,
    language: str = "auto"
) -> Dict[str, Any]:
    """
    Process audio data and return transcription.
    
    Args:
        audio_data: Raw audio bytes
        sample_rate: Audio sample rate in Hz
        language: Target language code or "auto" for detection
        
    Returns:
        Dictionary containing:
            - text: Transcribed text
            - confidence: Confidence score (0-1)
            - language: Detected language code
            
    Raises:
        ValueError: If audio_data is empty or invalid
        RuntimeError: If processing fails
        
    Example:
        >>> audio = load_audio_file("sample.wav")
        >>> result = process_audio(audio, sample_rate=16000)
        >>> print(result["text"])
        "Hello world"
    """
    pass
```

## Pull Request Process

### Before Submitting

1. **Update from Upstream**: Sync with latest changes
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run Tests**: Ensure all tests pass
   ```bash
   pytest
   ```

3. **Check Code Style**: Run linters
   ```bash
   black src/
   flake8 src/
   mypy src/
   ```

4. **Update Documentation**: Add/update relevant docs

### Submitting a Pull Request

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Implement your feature/fix

3. **Commit Changes**: Use conventional commits
   ```bash
   git commit -m "feat: add custom agent for X"
   git commit -m "fix: resolve issue with Y"
   git commit -m "docs: update agent documentation"
   ```

4. **Push to Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open Pull Request**: On GitHub, open a PR to `main` branch

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added that prove fix/feature works
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainers review your code
3. **Address Feedback**: Make requested changes
4. **Approval**: Once approved, PR will be merged

## Community

### Communication Channels

- **GitHub Discussions**: General discussions and Q&A
- **Discord**: Real-time chat and support
- **Mailing List**: Announcements and updates
- **Monthly Meetings**: Community video calls

### Getting Help

- **Documentation**: Check docs first
- **GitHub Issues**: Search existing issues
- **Discord**: Ask in #help channel
- **Stack Overflow**: Tag with `euvoice-ai`

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project website
- Annual contributor awards

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

## Questions?

If you have questions about contributing, please:
- Open a GitHub Discussion
- Join our Discord server
- Email: contributors@euvoice.ai

Thank you for contributing to EUVoice AI Platform! 🎉

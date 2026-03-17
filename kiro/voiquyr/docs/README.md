# EUVoice AI Platform Documentation

Welcome to the EUVoice AI Platform documentation! This directory contains comprehensive guides, references, and resources for users, developers, and contributors.

## Documentation Structure

### For Users

- **[User Guide](USER_GUIDE.md)** - Complete guide for using the platform
  - Quick start and installation
  - Voice processing (STT, LLM, TTS)
  - Configuration and customization
  - Advanced features
  - Troubleshooting

- **[FAQ](FAQ.md)** - Frequently asked questions
  - General questions
  - Technical questions
  - Feature questions
  - Compliance questions
  - Troubleshooting

### For Developers

- **[Developer Guide](DEVELOPER_GUIDE.md)** - Comprehensive development guide
  - Architecture overview
  - Development environment setup
  - Creating custom agents
  - API development
  - Testing and optimization
  - Deployment

- **[API Documentation](api/README.md)** - REST/WebSocket API reference
  - Authentication
  - Endpoints
  - Request/response formats
  - SDKs and examples
  - Error handling

- **[Agent Documentation](agents/README.md)** - Agent interface specification
  - Base agent interface
  - Core agent types (STT, LLM, TTS)
  - Specialized agents
  - Communication protocols
  - Development guidelines

### For DevOps

- **[Deployment Guide](deployment/README.md)** - Production deployment guide
  - Infrastructure requirements
  - Kubernetes deployment
  - Configuration
  - Monitoring and observability
  - Security
  - Backup and disaster recovery
  - Troubleshooting

- **[Configuration Guide](deployment/CONFIGURATION.md)** - Detailed configuration reference
  - Environment variables
  - Agent configuration
  - Database setup
  - Monitoring setup
  - Security configuration
  - Performance tuning

### For Contributors

- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
  - Code of conduct
  - Development setup
  - Contributing guidelines
  - Agent development
  - Testing requirements
  - Pull request process

## Quick Links

### Getting Started
- [Installation](USER_GUIDE.md#installation)
- [Quick Start](USER_GUIDE.md#quick-start)
- [Basic Usage](USER_GUIDE.md#basic-usage)

### Core Features
- [Speech-to-Text](USER_GUIDE.md#speech-to-text-stt)
- [Dialog Management](USER_GUIDE.md#dialog-management-llm)
- [Text-to-Speech](USER_GUIDE.md#text-to-speech-tts)
- [Emotion Detection](USER_GUIDE.md#emotion-detection)
- [Voice Cloning](USER_GUIDE.md#voice-cloning)
- [Arabic Support](USER_GUIDE.md#arabic-language-support)

### Development
- [Creating Custom Agents](DEVELOPER_GUIDE.md#creating-custom-agents)
- [API Development](DEVELOPER_GUIDE.md#api-development)
- [Testing](DEVELOPER_GUIDE.md#testing)
- [Performance Optimization](DEVELOPER_GUIDE.md#performance-optimization)

### Deployment
- [Quick Deployment](deployment/README.md#quick-start)
- [Kubernetes Setup](deployment/README.md#detailed-configuration)
- [Monitoring](deployment/README.md#monitoring-and-observability)
- [Security](deployment/README.md#security-configuration)

## Language Support

The platform supports 24+ languages with emphasis on EU languages and Arabic:

### Western European
- English (en)
- French (fr)
- German (de)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Dutch (nl)

### Nordic
- Swedish (sv)
- Danish (da)
- Finnish (fi)

### Eastern European
- Polish (pl)
- Czech (cs)
- Romanian (ro)
- Hungarian (hu)
- Bulgarian (bg)
- Croatian (hr)
- Slovak (sk)
- Slovenian (sl)

### Baltic
- Estonian (et)
- Latvian (lv)
- Lithuanian (lt)

### Other
- Greek (el)
- Maltese (mt)
- Irish (ga)

### Middle Eastern
- Arabic (ar)
  - Modern Standard Arabic (MSA)
  - Egyptian dialect
  - Levantine dialect
  - Gulf dialect
  - Maghrebi dialect

## Architecture

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
   └────┬───┘   └────┬───┘   └────┬───┘
        │            │            │
   ┌────▼────────────▼────────────▼───┐
   │    Specialized Feature Agents    │
   │  Emotion │ Accent │ Lip Sync │   │
   └──────────────────────────────────┘
```

## Key Features

### Multi-Agent Architecture
- Specialized agents for different tasks
- Coordinated parallel processing
- Automatic failover and recovery
- Horizontal scaling

### EU Compliance
- GDPR compliant by design
- EU AI Act compliance checking
- Data residency in EU/EEA
- Audit logging and reporting

### Performance
- <100ms latency for real-time processing
- >95% transcription accuracy
- >4.0 MOS for speech synthesis
- Horizontal scaling support

### Advanced Features
- Emotion detection (>85% accuracy)
- Accent recognition (>90% accuracy)
- Voice cloning (6-second samples)
- Lip synchronization (<50ms latency)
- Arabic dialect support

## System Requirements

### Minimum (Development)
- CPU: 8 cores
- RAM: 32GB
- GPU: NVIDIA RTX 3090
- Storage: 500GB SSD

### Recommended (Production)
- CPU: 32+ cores
- RAM: 128GB+
- GPU: NVIDIA A100/H100
- Storage: 10TB+ NVMe SSD

## Support and Community

### Getting Help
- **Documentation**: https://docs.euvoice.ai
- **Community Forum**: https://community.euvoice.ai
- **Discord**: https://discord.gg/euvoice
- **GitHub Issues**: https://github.com/euvoice/euvoice-ai-platform/issues

### Contact
- **General Support**: support@euvoice.ai
- **Technical Questions**: developers@euvoice.ai
- **Security Issues**: security@euvoice.ai
- **Commercial Inquiries**: sales@euvoice.ai

### Contributing
We welcome contributions! See the [Contributing Guide](../CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Contribution guidelines
- Pull request process

### Community Calls
Join our monthly community calls:
- **When**: First Tuesday of each month, 15:00 CET
- **Where**: Zoom (link in Discord)
- **Topics**: Updates, demos, Q&A

## License

Apache 2.0 - See [LICENSE](../LICENSE) file for details.

## Acknowledgments

This project uses open-source models and datasets:
- Mistral AI models (Voxtral, Small 3.1)
- XTTS-v2 for speech synthesis
- Mozilla Common Voice dataset
- VoxPopuli dataset
- And many more...

See [ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md) for complete list.

## Roadmap

See [ROADMAP.md](../ROADMAP.md) for planned features and improvements.

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for version history and changes.

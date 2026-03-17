# Frequently Asked Questions (FAQ)

## General Questions

### What is EUVoice AI Platform?

EUVoice AI Platform is an open-source SaaS platform for building, deploying, and managing voice assistants tailored for European, Asian, African, and Middle Eastern languages. It emphasizes EU compliance, data sovereignty, and support for low-resource languages.

### What makes EUVoice different from other voice platforms?

- **EU-First**: Hosted exclusively in EU with GDPR and AI Act compliance
- **Multilingual**: Native support for 24+ EU languages plus Arabic
- **Low-Resource Languages**: Optimized for Croatian, Estonian, Maltese, etc.
- **Open Source**: Apache 2.0 licensed, community-driven
- **Multi-Agent Architecture**: Extensible and scalable design
- **Advanced Features**: Emotion detection, accent recognition, lip sync

### Is EUVoice AI Platform free to use?

Yes, the platform is open-source under Apache 2.0 license. You can self-host it for free. We also offer managed cloud services with different pricing tiers.

### What languages are supported?

All 24 official EU languages plus Arabic with dialect support:
- Western European: English, French, German, Spanish, Italian, Portuguese, Dutch
- Nordic: Swedish, Danish, Finnish
- Eastern European: Polish, Czech, Romanian, Hungarian, Bulgarian, Croatian, Slovak, Slovenian
- Baltic: Estonian, Latvian, Lithuanian
- Other: Greek, Maltese, Irish
- Middle Eastern: Arabic (MSA, Egyptian, Levantine, Gulf, Maghrebi)

## Technical Questions

### What are the system requirements?

**Minimum (Development)**:
- CPU: 8 cores
- RAM: 32GB
- GPU: NVIDIA RTX 3090 or better
- Storage: 500GB SSD

**Recommended (Production)**:
- CPU: 32+ cores
- RAM: 128GB+
- GPU: NVIDIA A100 or H100
- Storage: 10TB+ NVMe SSD

### Can I run this without a GPU?

Yes, but performance will be significantly slower. GPU is highly recommended for production use, especially for real-time processing.

### What cloud providers are supported?

Any EU-based cloud provider:
- OVHcloud (France)
- Scaleway (France)
- Hetzner (Germany)
- DigitalOcean (EU regions)
- AWS (EU regions)
- Google Cloud (EU regions)
- Azure (EU regions)

### How do I deploy to Kubernetes?

```bash
helm install euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-production.yaml
```

See the [Deployment Guide](deployment/README.md) for details.

### What databases are required?

- **PostgreSQL**: Primary data storage
- **Redis**: Caching and real-time data
- **MinIO** (optional): Object storage for audio files

## Feature Questions

### Does it support real-time streaming?

Yes, the platform supports real-time audio streaming with WebSocket connections for both input (STT) and output (TTS).

### Can I clone voices?

Yes, the TTS agent supports voice cloning from 6-second audio samples using XTTS-v2.

### Does it detect emotions?

Yes, the Emotion Agent provides real-time emotion detection with >85% accuracy and sentiment scoring.

### Can it recognize accents?

Yes, the Accent Agent identifies regional accents with >90% accuracy and adapts processing accordingly.

### Does it support lip synchronization?

Yes, the Lip Sync Agent generates facial animation data synchronized with synthesized speech with <50ms latency.

### What about Arabic language support?

Comprehensive Arabic support including:
- Modern Standard Arabic (MSA)
- Regional dialects (Egyptian, Levantine, Gulf, Maghrebi)
- Diacritization
- Code-switching between Arabic and other languages

## Compliance Questions

### Is it GDPR compliant?

Yes, the platform is designed with GDPR compliance built-in:
- Data minimization
- Right to deletion
- Data portability
- Consent management
- Audit logging
- EU-only data residency

### What about the EU AI Act?

The platform includes automated AI Act compliance checking:
- Risk classification
- Transparency requirements
- Documentation generation
- Compliance reporting

### Where is data stored?

All data is stored exclusively within EU/EEA boundaries. You can configure specific regions based on your requirements.

### How long is data retained?

Default retention is 30 days, configurable based on your needs. Audio data can be automatically deleted after processing.

## Development Questions

### How do I create a custom agent?

See the [Developer Guide](DEVELOPER_GUIDE.md) for detailed instructions. Basic steps:

1. Inherit from `BaseAgent`
2. Implement required methods
3. Define capabilities
4. Add tests
5. Register with framework

### Can I use my own models?

Yes, the platform is designed to be model-agnostic. You can integrate custom models by creating appropriate agent implementations.

### How do I contribute?

See the [Contributing Guide](../CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting features
- Submitting pull requests
- Creating agents
- Writing documentation

### What programming languages are supported?

The core platform is Python-based. SDKs are available for:
- Python
- JavaScript/TypeScript
- More coming soon

## Performance Questions

### What latency can I expect?

Target latencies:
- STT: <100ms for real-time streaming
- LLM: <200ms for simple queries
- TTS: <150ms for short text
- End-to-end: <500ms

### How many concurrent users can it handle?

Depends on your infrastructure. With recommended setup:
- Small: 1,000-5,000 users
- Medium: 10,000-50,000 users
- Large: 100,000+ users

### How do I optimize performance?

- Use GPU acceleration
- Enable caching
- Configure autoscaling
- Optimize batch sizes
- Use connection pooling
- Monitor and tune based on metrics

## Pricing Questions

### Is there a free tier?

Yes, self-hosted deployment is completely free. Managed cloud services offer a free tier with limitations.

### What are the managed service pricing tiers?

- **Free**: 100 requests/month
- **Starter**: €49/month - 10,000 requests
- **Pro**: €199/month - 100,000 requests
- **Enterprise**: Custom pricing

### Can I get academic/research discounts?

Yes, we offer free access for academic research and non-profit organizations. Contact us at academic@euvoice.ai

## Troubleshooting

### Audio transcription is inaccurate

- Ensure audio quality is good (16kHz+, mono, minimal noise)
- Specify language explicitly instead of auto-detection
- Enable accent detection
- Check that the correct model is loaded

### High latency issues

- Check GPU utilization
- Verify network connectivity
- Review database performance
- Check for resource constraints
- Enable caching

### Agent not responding

- Check agent health status
- Review logs for errors
- Verify agent registration
- Check network connectivity
- Restart agent if needed

### Out of memory errors

- Reduce batch size
- Enable model quantization
- Increase available RAM
- Use smaller models
- Implement request queuing

## Community Questions

### How do I get help?

- **Documentation**: https://docs.euvoice.ai
- **Community Forum**: https://community.euvoice.ai
- **Discord**: https://discord.gg/euvoice
- **GitHub Issues**: For bug reports
- **Email**: support@euvoice.ai

### How can I stay updated?

- Follow us on Twitter: @euvoiceai
- Join our Discord server
- Subscribe to our newsletter
- Watch the GitHub repository
- Attend monthly community calls

### Can I use this commercially?

Yes, the Apache 2.0 license allows commercial use. For managed services, see our pricing tiers.

### How do I report security issues?

Email security@euvoice.ai with details. Do not open public GitHub issues for security vulnerabilities.

## Still Have Questions?

- Check the [User Guide](USER_GUIDE.md)
- Read the [Developer Guide](DEVELOPER_GUIDE.md)
- Visit the [Community Forum](https://community.euvoice.ai)
- Contact us at support@euvoice.ai

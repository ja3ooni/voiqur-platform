# EUVoice AI Kubernetes Infrastructure

This directory contains Kubernetes deployment manifests and Helm charts for the EUVoice AI platform.

## Structure

- `helm/` - Helm charts for all microservices
- `manifests/` - Raw Kubernetes manifests
- `istio/` - Istio service mesh configuration
- `monitoring/` - Prometheus, Grafana, and Jaeger configurations
- `security/` - Security policies and RBAC configurations

## Deployment

### Prerequisites

1. Kubernetes cluster (1.25+) in EU region
2. Helm 3.x installed
3. Istio service mesh installed
4. Prometheus Operator installed

### Quick Start

```bash
# Install the complete EUVoice AI platform
helm install euvoice ./helm/euvoice-platform --namespace euvoice --create-namespace

# Install individual services
helm install stt-agent ./helm/stt-agent --namespace euvoice
helm install llm-agent ./helm/llm-agent --namespace euvoice
helm install tts-agent ./helm/tts-agent --namespace euvoice
```

## EU Compliance

All deployments are configured for:
- GDPR compliance with data encryption and audit logging
- EU-only data residency
- AI Act compliance monitoring
- Automated compliance reporting
# EUVoice AI Platform Deployment Guide

This guide provides step-by-step instructions for deploying the EUVoice AI Platform on Kubernetes with full EU compliance.

## Prerequisites

### Infrastructure Requirements

- **Kubernetes Cluster**: Version 1.25+ running in EU region (eu-central-1 recommended)
- **Node Requirements**:
  - GPU nodes with NVIDIA GPUs (A100/H100 recommended for production)
  - CPU nodes with minimum 32 cores and 128GB RAM
  - Storage: 1TB+ NVMe SSD per node
- **Network**: 10Gbps+ connectivity between nodes
- **EU Compliance**: All infrastructure must be located within EU/EEA boundaries

### Software Dependencies

- Helm 3.x
- kubectl configured for your cluster
- Istio service mesh
- cert-manager for TLS certificates
- Prometheus Operator
- NVIDIA GPU Operator (for GPU nodes)

## Deployment Steps

### 1. Prepare the Cluster

```bash
# Create namespace
kubectl create namespace euvoice

# Label namespace for compliance
kubectl label namespace euvoice compliance.euvoice.ai/gdpr=enabled
kubectl label namespace euvoice compliance.euvoice.ai/ai-act=enabled
kubectl label namespace euvoice region=eu-central-1

# Install GPU Operator (if using GPU nodes)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator-resources \
  --create-namespace \
  --set driver.enabled=true
```

### 2. Install Dependencies

```bash
# Install Istio
curl -L https://istio.io/downloadIstio | sh -
istioctl install --set values.global.meshID=euvoice --set values.global.network=euvoice-network

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus-operator prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### 3. Configure Security and Compliance

```bash
# Apply RBAC configurations
kubectl apply -f k8s/security/rbac.yaml

# Apply Pod Security Policies
kubectl apply -f k8s/security/pod-security-policies.yaml

# Apply Network Policies
kubectl apply -f k8s/security/network-policies.yaml

# Configure encryption
kubectl apply -f k8s/security/encryption.yaml

# Set up audit logging
kubectl apply -f k8s/security/audit-logging.yaml

# Configure GDPR compliance
kubectl apply -f k8s/security/gdpr-compliance.yaml
```

### 4. Deploy Istio Service Mesh

```bash
# Enable Istio injection for euvoice namespace
kubectl label namespace euvoice istio-injection=enabled

# Apply Istio configurations
kubectl apply -f k8s/istio/gateway.yaml
kubectl apply -f k8s/istio/security-policies.yaml
```

### 5. Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f k8s/monitoring/prometheus.yaml

# Deploy Grafana
kubectl apply -f k8s/monitoring/grafana.yaml

# Deploy Jaeger
kubectl apply -f k8s/monitoring/jaeger.yaml

# Deploy Alertmanager
kubectl apply -f k8s/monitoring/alertmanager.yaml
```

### 6. Configure Auto-scaling and Load Balancing

```bash
# Install Cluster Autoscaler
kubectl apply -f k8s/autoscaling/cluster-autoscaler.yaml

# Configure HPA
kubectl apply -f k8s/autoscaling/hpa-configs.yaml

# Configure VPA (optional)
kubectl apply -f k8s/autoscaling/vpa-configs.yaml

# Deploy NGINX Ingress
kubectl apply -f k8s/load-balancing/nginx-ingress.yaml

# Configure Circuit Breakers
kubectl apply -f k8s/load-balancing/circuit-breaker.yaml
```

### 7. Deploy EUVoice Platform

```bash
# Update Helm values for your environment
cp k8s/helm/euvoice-platform/values.yaml values-production.yaml

# Edit values-production.yaml with your specific configuration:
# - Image registry URLs
# - Domain names
# - Resource limits
# - Storage classes
# - Secrets

# Install the platform
helm install euvoice-platform ./k8s/helm/euvoice-platform \
  --namespace euvoice \
  --values values-production.yaml \
  --timeout 20m
```

### 8. Verify Deployment

```bash
# Check pod status
kubectl get pods -n euvoice

# Check services
kubectl get services -n euvoice

# Check ingress
kubectl get ingress -n euvoice

# Verify Istio configuration
istioctl analyze -n euvoice

# Check monitoring
kubectl port-forward -n euvoice svc/grafana 3000:3000
# Access Grafana at http://localhost:3000

# Check compliance status
kubectl get events -n euvoice --field-selector reason=GDPRCompliance
```

## Configuration

### Environment-Specific Settings

#### Development Environment

```yaml
# values-dev.yaml
global:
  region: "eu-central-1"
  imageRegistry: "your-dev-registry"

multiAgentFramework:
  replicaCount: 1
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"

sttAgent:
  replicaCount: 1
  autoscaling:
    enabled: false

llmAgent:
  replicaCount: 1
  autoscaling:
    enabled: false

ttsAgent:
  replicaCount: 1
  autoscaling:
    enabled: false
```

#### Production Environment

```yaml
# values-prod.yaml
global:
  region: "eu-central-1"
  imageRegistry: "your-prod-registry"
  gdprCompliance: true
  aiActCompliance: true

multiAgentFramework:
  replicaCount: 3
  resources:
    requests:
      cpu: "2"
      memory: "4Gi"
    limits:
      cpu: "4"
      memory: "8Gi"

sttAgent:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10

llmAgent:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 8

ttsAgent:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 6
```

### Secrets Configuration

```bash
# Create required secrets
kubectl create secret generic euvoice-platform-secrets \
  --from-literal=jwt-secret="your-jwt-secret" \
  --from-literal=data-encryption-key="your-encryption-key" \
  --from-literal=webhook-secret="your-webhook-secret" \
  -n euvoice

# Create database secrets
kubectl create secret generic euvoice-platform-postgres \
  --from-literal=password="your-postgres-password" \
  --from-literal=username="postgres" \
  --from-literal=database="euvoice" \
  -n euvoice

# Create Redis secrets
kubectl create secret generic euvoice-platform-redis \
  --from-literal=password="your-redis-password" \
  -n euvoice

# Create TLS certificates (using cert-manager)
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: euvoice-tls
  namespace: euvoice
spec:
  secretName: euvoice-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  commonName: api.euvoice.ai
  dnsNames:
  - api.euvoice.ai
  - dashboard.euvoice.ai
EOF
```

## Monitoring and Observability

### Accessing Dashboards

```bash
# Grafana (monitoring)
kubectl port-forward -n euvoice svc/grafana 3000:3000
# Access: http://localhost:3000 (admin/admin)

# Prometheus (metrics)
kubectl port-forward -n euvoice svc/prometheus 9090:9090
# Access: http://localhost:9090

# Jaeger (tracing)
kubectl port-forward -n euvoice svc/jaeger 16686:16686
# Access: http://localhost:16686

# Alertmanager (alerts)
kubectl port-forward -n euvoice svc/alertmanager 9093:9093
# Access: http://localhost:9093
```

### Key Metrics to Monitor

- **Voice Processing Latency**: <100ms end-to-end
- **Transcription Accuracy**: >95% for EU languages
- **TTS Quality**: MOS >4.0
- **System Availability**: >99.9%
- **GDPR Compliance**: 100% data residency in EU
- **Resource Utilization**: CPU <80%, Memory <85%, GPU <90%

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status and events
kubectl describe pod <pod-name> -n euvoice

# Check logs
kubectl logs <pod-name> -n euvoice

# Check resource constraints
kubectl top pods -n euvoice
kubectl describe nodes
```

#### GPU Not Available

```bash
# Check GPU operator status
kubectl get pods -n gpu-operator-resources

# Verify GPU nodes
kubectl get nodes -l accelerator=nvidia-gpu

# Check GPU resources
kubectl describe node <gpu-node-name>
```

#### Network Connectivity Issues

```bash
# Check network policies
kubectl get networkpolicies -n euvoice

# Test service connectivity
kubectl run test-pod --image=busybox -it --rm -- /bin/sh
# Inside pod: nslookup euvoice-platform-stt-agent.euvoice.svc.cluster.local

# Check Istio configuration
istioctl proxy-config cluster <pod-name> -n euvoice
```

#### Performance Issues

```bash
# Check HPA status
kubectl get hpa -n euvoice

# Check resource usage
kubectl top pods -n euvoice
kubectl top nodes

# Check metrics
kubectl port-forward -n euvoice svc/prometheus 9090:9090
# Query: rate(http_requests_total[5m])
```

### Compliance Verification

```bash
# Check GDPR compliance status
kubectl get events -n euvoice --field-selector reason=GDPRCompliance

# Verify data residency
kubectl get pods -n euvoice -o wide
# Ensure all pods are running on EU nodes

# Check audit logs
kubectl logs -n kube-system -l app=fluent-bit-audit

# Verify encryption
kubectl get secrets -n euvoice
kubectl describe storageclass gp3-encrypted
```

## Scaling Guidelines

### Horizontal Scaling

- **STT Agent**: Scale based on audio processing queue length
- **LLM Agent**: Scale based on context memory usage and response time
- **TTS Agent**: Scale based on synthesis queue length
- **API Gateway**: Scale based on request rate and WebSocket connections

### Vertical Scaling

- **GPU Memory**: Monitor GPU memory usage, scale up if >90%
- **CPU**: Scale up if sustained >80% usage
- **Memory**: Scale up if sustained >85% usage

### Cluster Scaling

- **Node Autoscaling**: Configured to scale 1-100 nodes per group
- **GPU Nodes**: Scale based on GPU resource requests
- **CPU Nodes**: Scale based on CPU/memory resource requests

## Security Best Practices

1. **Network Segmentation**: Use NetworkPolicies for micro-segmentation
2. **RBAC**: Follow principle of least privilege
3. **Pod Security**: Use Pod Security Policies/Standards
4. **Secrets Management**: Use external secret management (Vault)
5. **Image Security**: Scan images for vulnerabilities
6. **Audit Logging**: Enable comprehensive audit logging
7. **Encryption**: Encrypt data at rest and in transit
8. **Compliance**: Regular GDPR and AI Act compliance checks

## Backup and Disaster Recovery

### Database Backup

```bash
# PostgreSQL backup
kubectl exec -n euvoice deployment/postgresql -- pg_dump -U postgres euvoice > backup.sql

# Restore
kubectl exec -i -n euvoice deployment/postgresql -- psql -U postgres euvoice < backup.sql
```

### Configuration Backup

```bash
# Backup all configurations
kubectl get all,secrets,configmaps,pvc -n euvoice -o yaml > euvoice-backup.yaml

# Backup Helm values
helm get values euvoice-platform -n euvoice > values-backup.yaml
```

### Disaster Recovery Plan

1. **RTO**: 4 hours (Recovery Time Objective)
2. **RPO**: 1 hour (Recovery Point Objective)
3. **Multi-AZ**: Deploy across multiple availability zones
4. **Cross-Region**: Maintain standby cluster in secondary EU region
5. **Data Replication**: Real-time replication of critical data

## Maintenance

### Regular Tasks

- **Weekly**: Review monitoring dashboards and alerts
- **Monthly**: Update container images and security patches
- **Quarterly**: Review and update resource allocations
- **Annually**: Compliance audit and security assessment

### Update Procedure

```bash
# Update platform
helm upgrade euvoice-platform ./k8s/helm/euvoice-platform \
  --namespace euvoice \
  --values values-production.yaml

# Rolling update strategy ensures zero downtime
kubectl rollout status deployment/euvoice-platform-stt-agent -n euvoice
```

## Support and Documentation

- **Technical Documentation**: https://docs.euvoice.ai
- **API Documentation**: https://api.euvoice.ai/docs
- **Compliance Documentation**: https://compliance.euvoice.ai
- **Support**: support@euvoice.ai
- **Security Issues**: security@euvoice.ai
- **Privacy/GDPR**: privacy@euvoice.ai
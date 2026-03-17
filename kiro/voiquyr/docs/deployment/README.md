# EUVoice AI Platform Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the EUVoice AI Platform in production environments with EU compliance, GDPR requirements, and high availability.

## Prerequisites

### Infrastructure Requirements

#### Minimum Production Setup
- **Kubernetes Cluster**: v1.24+ with 10+ nodes
- **CPU**: 32 cores per node (AMD EPYC or Intel Xeon)
- **RAM**: 128GB per node
- **GPU**: NVIDIA A100 or H100 (2-4 per node)
- **Storage**: 10TB NVMe SSD + 100TB distributed storage
- **Network**: 10Gbps+ connectivity

#### EU Compliance Requirements
- **Data Residency**: All infrastructure within EU/EEA boundaries
- **Hosting Providers**: OVHcloud, Scaleway, Hetzner, or equivalent EU providers
- **Certifications**: ISO 27001, SOC 2, GDPR-compliant data centers

### Software Requirements

- **Kubernetes**: v1.24+
- **Helm**: v3.10+
- **kubectl**: v1.24+
- **Docker**: v20.10+
- **PostgreSQL**: v14+
- **Redis**: v7.0+
- **MinIO**: Latest stable (for object storage)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/euvoice/euvoice-ai-platform.git
cd euvoice-ai-platform
```

### 2. Configure Environment

```bash
# Copy example configuration
cp k8s/helm/euvoice-platform/values.yaml values-production.yaml

# Edit configuration for your environment
vim values-production.yaml
```

### 3. Deploy with Helm

```bash
# Add required Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace euvoice-production

# Deploy the platform
helm install euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-production.yaml \
  --wait --timeout 15m
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n euvoice-production

# Check services
kubectl get svc -n euvoice-production

# View logs
kubectl logs -n euvoice-production -l app=api-gateway --tail=100
```

## Detailed Configuration

### Helm Values Configuration

The `values.yaml` file controls all deployment parameters. Key sections:

#### Global Settings

```yaml
global:
  environment: production
  region: eu-west-1
  dataResidency: EU
  gdprMode: true
  
  # Image registry
  imageRegistry: registry.euvoice.ai
  imagePullSecrets:
    - name: registry-credentials
```

#### API Gateway Configuration

```yaml
apiGateway:
  enabled: true
  replicaCount: 3
  
  image:
    repository: euvoice/api-gateway
    tag: "1.0.0"
    pullPolicy: IfNotPresent
  
  resources:
    requests:
      cpu: "2000m"
      memory: "4Gi"
    limits:
      cpu: "4000m"
      memory: "8Gi"
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  
  service:
    type: LoadBalancer
    port: 443
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
```

#### STT Agent Configuration

```yaml
sttAgent:
  enabled: true
  replicaCount: 5
  
  model:
    name: "mistral-voxtral-small"
    version: "24B"
    
  resources:
    requests:
      cpu: "4000m"
      memory: "16Gi"
      nvidia.com/gpu: "1"
    limits:
      cpu: "8000m"
      memory: "32Gi"
      nvidia.com/gpu: "1"
  
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 50
    targetCPUUtilizationPercentage: 60
```

#### Database Configuration

```yaml
postgresql:
  enabled: true
  auth:
    username: euvoice
    password: <secure-password>
    database: euvoice_production
  
  primary:
    persistence:
      enabled: true
      size: 500Gi
      storageClass: fast-ssd
    
    resources:
      requests:
        cpu: "4000m"
        memory: "16Gi"
      limits:
        cpu: "8000m"
        memory: "32Gi"
  
  replication:
    enabled: true
    replicaCount: 2
```

### Environment Variables

Create a `.env` file or Kubernetes secrets:

```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/euvoice
REDIS_URL=redis://redis:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Authentication
JWT_SECRET_KEY=<generate-secure-key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# EU Compliance
EU_DATA_RESIDENCY=true
GDPR_MODE=true
DATA_RETENTION_DAYS=30

# Model Configuration
STT_MODEL=mistral-voxtral-small
LLM_MODEL=mistral-small-3.1
TTS_MODEL=xtts-v2

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
JAEGER_ENABLED=true
```

## Deployment Strategies

### Blue-Green Deployment

```bash
# Deploy new version (green)
helm upgrade euvoice-green k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-production.yaml \
  --set global.version=2.0.0 \
  --install

# Test green deployment
kubectl port-forward -n euvoice-production svc/euvoice-green-api 8080:80

# Switch traffic to green
kubectl patch svc euvoice-api -n euvoice-production \
  -p '{"spec":{"selector":{"version":"2.0.0"}}}'

# Remove blue deployment after verification
helm uninstall euvoice-blue -n euvoice-production
```

### Canary Deployment

```yaml
# values-canary.yaml
apiGateway:
  canary:
    enabled: true
    weight: 10  # 10% of traffic to canary
    
  version: "2.0.0"
```

```bash
# Deploy canary
helm upgrade euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-canary.yaml

# Gradually increase canary weight
# Monitor metrics and errors
# Promote or rollback based on results
```

### Rolling Update

```bash
# Update with rolling strategy (default)
helm upgrade euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-production.yaml \
  --set global.version=2.0.0

# Monitor rollout
kubectl rollout status deployment/api-gateway -n euvoice-production

# Rollback if needed
helm rollback euvoice -n euvoice-production
```

## Monitoring and Observability

### Prometheus Metrics

Access Prometheus at `http://prometheus.euvoice.ai`

Key metrics to monitor:
- `euvoice_request_duration_seconds`: Request latency
- `euvoice_requests_total`: Total requests
- `euvoice_errors_total`: Error count
- `euvoice_agent_health`: Agent health status
- `euvoice_gpu_utilization`: GPU usage

### Grafana Dashboards

Access Grafana at `http://grafana.euvoice.ai`

Pre-configured dashboards:
- **System Overview**: Overall system health and performance
- **Agent Performance**: Individual agent metrics
- **API Gateway**: Request rates, latency, errors
- **GPU Utilization**: GPU memory and compute usage
- **Database Performance**: Query performance, connections

### Distributed Tracing

Access Jaeger at `http://jaeger.euvoice.ai`

Trace complete request flows:
- Audio input → STT → LLM → TTS → Output
- Agent communication and coordination
- Database queries and external API calls

### Log Aggregation

```bash
# View logs from all components
kubectl logs -n euvoice-production -l app=euvoice --tail=1000

# Stream logs in real-time
kubectl logs -n euvoice-production -l app=api-gateway -f

# Export logs for analysis
kubectl logs -n euvoice-production --all-containers=true > logs.txt
```

## Security Configuration

### TLS/SSL Certificates

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create certificate issuer
kubectl apply -f k8s/security/cert-issuer.yaml

# Certificates are automatically provisioned for ingress
```

### Network Policies

```bash
# Apply network policies for isolation
kubectl apply -f k8s/security/network-policies.yaml

# Verify policies
kubectl get networkpolicies -n euvoice-production
```

### RBAC Configuration

```bash
# Apply role-based access control
kubectl apply -f k8s/security/rbac.yaml

# Create service accounts
kubectl apply -f k8s/security/service-accounts.yaml
```

### Secrets Management

```bash
# Create secrets from files
kubectl create secret generic api-secrets \
  --from-file=jwt-key=./secrets/jwt.key \
  --from-file=db-password=./secrets/db-pass.txt \
  -n euvoice-production

# Or use sealed secrets for GitOps
kubeseal --format yaml < secrets.yaml > sealed-secrets.yaml
kubectl apply -f sealed-secrets.yaml
```

## Backup and Disaster Recovery

### Database Backups

```bash
# Automated daily backups
kubectl apply -f k8s/backup/postgres-backup-cronjob.yaml

# Manual backup
kubectl exec -n euvoice-production postgres-0 -- \
  pg_dump -U euvoice euvoice_production > backup.sql

# Restore from backup
kubectl exec -i -n euvoice-production postgres-0 -- \
  psql -U euvoice euvoice_production < backup.sql
```

### Model and Configuration Backups

```bash
# Backup models to S3-compatible storage
kubectl apply -f k8s/backup/model-backup-cronjob.yaml

# Backup configurations
kubectl get configmap -n euvoice-production -o yaml > configs-backup.yaml
kubectl get secret -n euvoice-production -o yaml > secrets-backup.yaml
```

### Disaster Recovery Plan

1. **Regular Backups**: Automated daily backups of databases and models
2. **Multi-Region**: Deploy in multiple EU regions for redundancy
3. **Recovery Time Objective (RTO)**: < 1 hour
4. **Recovery Point Objective (RPO)**: < 15 minutes
5. **Failover**: Automatic failover to secondary region

## Scaling Guidelines

### Horizontal Pod Autoscaling

```yaml
# HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stt-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stt-agent
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### Vertical Pod Autoscaling

```bash
# Install VPA
kubectl apply -f k8s/autoscaling/vpa-configs.yaml

# VPA will automatically adjust resource requests/limits
```

### Cluster Autoscaling

```bash
# Configure cluster autoscaler
kubectl apply -f k8s/autoscaling/cluster-autoscaler.yaml

# Autoscaler will add/remove nodes based on demand
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n euvoice-production

# Check events
kubectl get events -n euvoice-production --sort-by='.lastTimestamp'

# Check resource availability
kubectl top nodes
kubectl top pods -n euvoice-production
```

#### High Latency

```bash
# Check agent performance
kubectl logs -n euvoice-production -l app=stt-agent --tail=100

# Check database performance
kubectl exec -n euvoice-production postgres-0 -- \
  psql -U euvoice -c "SELECT * FROM pg_stat_activity;"

# Check network latency
kubectl exec -n euvoice-production api-gateway-0 -- \
  ping stt-agent-service
```

#### GPU Issues

```bash
# Check GPU availability
kubectl describe node <node-name> | grep nvidia.com/gpu

# Check GPU utilization
kubectl exec -n euvoice-production stt-agent-0 -- nvidia-smi

# Restart GPU pods if needed
kubectl delete pod -n euvoice-production -l gpu=true
```

### Debug Mode

```bash
# Enable debug logging
kubectl set env deployment/api-gateway -n euvoice-production LOG_LEVEL=DEBUG

# Access pod shell for debugging
kubectl exec -it -n euvoice-production api-gateway-0 -- /bin/bash
```

## Performance Tuning

### Database Optimization

```sql
-- Optimize PostgreSQL for production
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
```

### Redis Optimization

```bash
# Configure Redis for production
kubectl exec -n euvoice-production redis-0 -- redis-cli CONFIG SET maxmemory 8gb
kubectl exec -n euvoice-production redis-0 -- redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### GPU Optimization

```yaml
# Enable GPU sharing for better utilization
resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    nvidia.com/gpu: 1

# Use MIG (Multi-Instance GPU) for A100
nvidia.com/mig-1g.5gb: 1
```

## Compliance and Auditing

### GDPR Compliance

```bash
# Enable audit logging
kubectl apply -f k8s/security/audit-logging.yaml

# Configure data retention
kubectl apply -f k8s/security/gdpr-compliance.yaml

# Generate compliance report
kubectl exec -n euvoice-production api-gateway-0 -- \
  python -m src.compliance.compliance_system generate-report
```

### EU AI Act Compliance

```bash
# Run AI Act validation
kubectl exec -n euvoice-production api-gateway-0 -- \
  python -m src.compliance.ai_act_validator validate

# Generate risk assessment
kubectl exec -n euvoice-production api-gateway-0 -- \
  python -m src.compliance.ai_act_validator assess-risk
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly: Update security patches
helm upgrade euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --reuse-values

# Monthly: Database vacuum and analyze
kubectl exec -n euvoice-production postgres-0 -- \
  vacuumdb -U euvoice --all --analyze

# Quarterly: Review and optimize resource allocation
kubectl top pods -n euvoice-production
kubectl top nodes
```

### Upgrade Procedure

```bash
# 1. Backup current state
kubectl get all -n euvoice-production -o yaml > backup-pre-upgrade.yaml

# 2. Test upgrade in staging
helm upgrade euvoice-staging k8s/helm/euvoice-platform \
  --namespace euvoice-staging \
  --values values-staging.yaml

# 3. Upgrade production
helm upgrade euvoice k8s/helm/euvoice-platform \
  --namespace euvoice-production \
  --values values-production.yaml

# 4. Verify upgrade
kubectl rollout status deployment -n euvoice-production

# 5. Rollback if needed
helm rollback euvoice -n euvoice-production
```

## Support and Resources

- **Documentation**: https://docs.euvoice.ai
- **Community Forum**: https://community.euvoice.ai
- **Issue Tracker**: https://github.com/euvoice/euvoice-ai-platform/issues
- **Security Issues**: security@euvoice.ai
- **Commercial Support**: support@euvoice.ai

## License

Apache 2.0 - See LICENSE file for details

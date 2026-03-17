# Configuration Guide

## Overview

This guide provides detailed information about configuring the EUVoice AI Platform for different environments and use cases.

## Configuration Files

### Environment Variables

The platform uses environment variables for configuration. Create a `.env` file or set them in your deployment environment:

```bash
# Core Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_TIMEOUT=300

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/euvoice
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5

# Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
OAUTH2_ENABLED=true

# EU Compliance
EU_DATA_RESIDENCY=true
GDPR_MODE=true
DATA_RETENTION_DAYS=30
AUDIT_LOGGING_ENABLED=true

# Model Configuration
STT_MODEL=mistral-voxtral-small
STT_MODEL_PATH=/models/stt
LLM_MODEL=mistral-small-3.1
LLM_MODEL_PATH=/models/llm
TTS_MODEL=xtts-v2
TTS_MODEL_PATH=/models/tts

# Performance
MAX_CONCURRENT_REQUESTS=1000
REQUEST_TIMEOUT=60
STREAMING_CHUNK_SIZE=4096

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true
JAEGER_ENABLED=true
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=euvoice-data
MINIO_SECURE=false

# Webhooks
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_DELAY=5
WEBHOOK_TIMEOUT=30
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: euvoice-config
  namespace: euvoice-production
data:
  # Application Configuration
  environment: "production"
  log_level: "INFO"
  
  # Feature Flags
  emotion_detection_enabled: "true"
  accent_recognition_enabled: "true"
  lip_sync_enabled: "true"
  arabic_specialist_enabled: "true"
  
  # Performance Tuning
  max_concurrent_requests: "1000"
  request_timeout: "60"
  streaming_chunk_size: "4096"
  
  # Model Configuration
  stt_model: "mistral-voxtral-small"
  llm_model: "mistral-small-3.1"
  tts_model: "xtts-v2"
  
  # EU Compliance
  eu_data_residency: "true"
  gdpr_mode: "true"
  data_retention_days: "30"
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: euvoice-secrets
  namespace: euvoice-production
type: Opaque
stringData:
  # Database
  database-url: "postgresql://user:password@postgres:5432/euvoice"
  
  # Redis
  redis-url: "redis://redis:6379/0"
  
  # JWT
  jwt-secret-key: "your-secret-key-here"
  
  # MinIO
  minio-access-key: "your-access-key"
  minio-secret-key: "your-secret-key"
  
  # API Keys
  openai-api-key: "sk-..."
  mistral-api-key: "..."
```

## Agent Configuration

### STT Agent

```yaml
stt_agent:
  model:
    name: "mistral-voxtral-small"
    version: "24B"
    device: "cuda"
    precision: "float16"
  
  processing:
    sample_rate: 16000
    chunk_duration: 0.5
    buffer_size: 4096
    vad_enabled: true
    vad_threshold: 0.5
  
  languages:
    - en
    - fr
    - de
    - es
    - it
    - pt
    - nl
    - pl
    - cs
    - ro
    - hu
    - sv
    - da
    - fi
    - el
    - bg
    - hr
    - sk
    - sl
    - et
    - lv
    - lt
    - mt
    - ga
    - ar
  
  performance:
    max_concurrent_requests: 100
    timeout: 30
    batch_size: 8
```

### LLM Agent

```yaml
llm_agent:
  model:
    name: "mistral-small-3.1"
    version: "22B"
    device: "cuda"
    precision: "float16"
  
  generation:
    max_tokens: 2048
    temperature: 0.7
    top_p: 0.9
    top_k: 50
    repetition_penalty: 1.1
  
  context:
    max_context_length: 32768
    context_window: 8192
    sliding_window: true
  
  tools:
    enabled: true
    max_tool_calls: 5
    timeout: 30
  
  performance:
    max_concurrent_requests: 50
    timeout: 60
    batch_size: 4
```

### TTS Agent

```yaml
tts_agent:
  model:
    name: "xtts-v2"
    device: "cuda"
    precision: "float16"
  
  synthesis:
    sample_rate: 22050
    format: "wav"
    quality: "high"
    streaming: true
  
  voice_cloning:
    enabled: true
    min_audio_length: 6
    max_audio_length: 30
  
  emotion:
    enabled: true
    emotions:
      - neutral
      - happy
      - sad
      - angry
      - excited
      - calm
  
  performance:
    max_concurrent_requests: 100
    timeout: 30
    batch_size: 8
```

### Specialized Agents

```yaml
emotion_agent:
  enabled: true
  model: "emotion-recognition-v1"
  accuracy_threshold: 0.85
  real_time: true

accent_agent:
  enabled: true
  model: "accent-detection-v1"
  accuracy_threshold: 0.90
  supported_accents:
    - american
    - british
    - australian
    - irish
    - scottish
    - french
    - german
    - spanish
    - italian

lip_sync_agent:
  enabled: true
  model: "lip-sync-v1"
  latency_target: 50
  avatar_styles:
    - realistic
    - cartoon
    - anime

arabic_agent:
  enabled: true
  dialects:
    - msa
    - egyptian
    - levantine
    - gulf
    - maghrebi
  diacritization: true
  code_switching: true
```

## Database Configuration

### PostgreSQL

```sql
-- Create database
CREATE DATABASE euvoice_production;

-- Create user
CREATE USER euvoice WITH ENCRYPTED PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE euvoice_production TO euvoice;

-- Performance tuning
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
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET max_parallel_maintenance_workers = 4;

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis

```bash
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

## Monitoring Configuration

### Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'euvoice-api'
    static_configs:
      - targets: ['api-gateway:9090']
  
  - job_name: 'euvoice-stt'
    static_configs:
      - targets: ['stt-agent:9090']
  
  - job_name: 'euvoice-llm'
    static_configs:
      - targets: ['llm-agent:9090']
  
  - job_name: 'euvoice-tts'
    static_configs:
      - targets: ['tts-agent:9090']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana

```yaml
# datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
```

## Security Configuration

### TLS/SSL

```yaml
# tls-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: tls-certificate
  namespace: euvoice-production
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
```

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: euvoice-network-policy
  namespace: euvoice-production
spec:
  podSelector:
    matchLabels:
      app: euvoice
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: euvoice
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
      - podSelector:
          matchLabels:
            app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
      - podSelector:
          matchLabels:
            app: redis
      ports:
        - protocol: TCP
          port: 6379
```

## Performance Tuning

### Resource Limits

```yaml
# resource-limits.yaml
resources:
  requests:
    cpu: "2000m"
    memory: "4Gi"
    nvidia.com/gpu: "1"
  limits:
    cpu: "4000m"
    memory: "8Gi"
    nvidia.com/gpu: "1"
```

### Autoscaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: euvoice-hpa
  namespace: euvoice-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Backup Configuration

### Database Backup

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: euvoice-production
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres -U euvoice euvoice_production | \
              gzip > /backup/euvoice-$(date +%Y%m%d-%H%M%S).sql.gz
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Troubleshooting

### Enable Debug Logging

```bash
# Set log level to DEBUG
kubectl set env deployment/api-gateway -n euvoice-production LOG_LEVEL=DEBUG

# View logs
kubectl logs -n euvoice-production -l app=api-gateway --tail=100 -f
```

### Performance Profiling

```bash
# Enable profiling
kubectl set env deployment/api-gateway -n euvoice-production PROFILING_ENABLED=true

# Access profiling endpoint
kubectl port-forward -n euvoice-production svc/api-gateway 8000:8000
curl http://localhost:8000/debug/pprof/
```

## Best Practices

1. **Use Secrets for Sensitive Data**: Never commit secrets to version control
2. **Enable Resource Limits**: Prevent resource exhaustion
3. **Configure Autoscaling**: Handle variable load automatically
4. **Enable Monitoring**: Track performance and errors
5. **Regular Backups**: Automate database and configuration backups
6. **Security Hardening**: Use network policies, RBAC, and encryption
7. **EU Compliance**: Ensure all data stays within EU boundaries
8. **Performance Testing**: Load test before production deployment
9. **Disaster Recovery**: Have a tested recovery plan
10. **Documentation**: Keep configuration documentation up to date

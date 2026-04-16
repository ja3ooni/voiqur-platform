# Voiquyr Platform — Kubernetes

## Structure

```
k8s/
├── manifests/          # Plain YAML — apply directly with kubectl
│   ├── namespace.yaml
│   ├── secrets.yaml    # Template only — populate with kubectl create secret
│   ├── postgres.yaml
│   ├── redis.yaml
│   ├── api.yaml        # Main platform API (port 8000)
│   ├── dashboard.yaml  # React dashboard (port 80)
│   ├── command-center.yaml  # CC backend (8001) + CC frontend (80)
│   └── ingress.yaml    # nginx-ingress + cert-manager
├── helm/
│   └── euvoice-platform/   # Helm chart wrapping all of the above
├── autoscaling/        # HPA / VPA / cluster-autoscaler configs
├── istio/              # Service mesh (optional)
├── load-balancing/     # nginx-ingress, circuit-breaker
├── monitoring/         # Prometheus, Grafana, Jaeger, Alertmanager
└── security/           # RBAC, NetworkPolicies, encryption, GDPR
```

## Images

| Image | Dockerfile |
|---|---|
| `voiquyr/api` | `Dockerfile` (repo root) |
| `voiquyr/command-center-api` | `voiquyr-command-center/backend/Dockerfile` |
| `voiquyr/dashboard` | `frontend/Dockerfile` |
| `voiquyr/command-center-ui` | `voiquyr-command-center/frontend/Dockerfile` |

Build all images:

```bash
docker build -t voiquyr/api:latest .
docker build -t voiquyr/command-center-api:latest voiquyr-command-center/backend
docker build -t voiquyr/dashboard:latest frontend
docker build -t voiquyr/command-center-ui:latest --build-arg GEMINI_API_KEY=$GEMINI_API_KEY voiquyr-command-center/frontend
```

## Option A — Plain kubectl

```bash
# 1. Create namespace
kubectl apply -f k8s/manifests/namespace.yaml

# 2. Create secrets (fill in real values)
kubectl create secret generic voiquyr-secrets \
  --from-literal=jwt-secret-key="$(openssl rand -hex 32)" \
  --from-literal=database-url="postgresql://postgres:PASSWORD@postgres:5432/euvoice" \
  --from-literal=redis-url="redis://redis:6379" \
  --from-literal=mistral-api-key="..." \
  --from-literal=deepgram-api-key="..." \
  --from-literal=elevenlabs-api-key="..." \
  --from-literal=stripe-api-key="..." \
  --from-literal=gemini-api-key="..." \
  -n voiquyr

kubectl create secret generic voiquyr-postgres \
  --from-literal=password="YOUR_PG_PASSWORD" \
  -n voiquyr

# 3. Deploy infrastructure
kubectl apply -f k8s/manifests/postgres.yaml
kubectl apply -f k8s/manifests/redis.yaml

# 4. Deploy services
kubectl apply -f k8s/manifests/api.yaml
kubectl apply -f k8s/manifests/dashboard.yaml
kubectl apply -f k8s/manifests/command-center.yaml

# 5. Deploy ingress (requires nginx-ingress + cert-manager)
kubectl apply -f k8s/manifests/ingress.yaml
```

## Option B — Helm

```bash
# Add Bitnami repo for postgresql/redis sub-charts
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update k8s/helm/euvoice-platform

# Install (pass real secrets via --set)
helm install voiquyr k8s/helm/euvoice-platform \
  --namespace voiquyr \
  --create-namespace \
  --set secrets.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secrets.mistralApiKey="$MISTRAL_API_KEY" \
  --set secrets.deepgramApiKey="$DEEPGRAM_API_KEY" \
  --set secrets.elevenlabsApiKey="$ELEVENLABS_API_KEY" \
  --set secrets.stripeApiKey="$STRIPE_API_KEY" \
  --set secrets.geminiApiKey="$GEMINI_API_KEY" \
  --set postgresql.auth.postgresPassword="$PG_PASSWORD" \
  --set redis.auth.password="$REDIS_PASSWORD" \
  --set global.imageRegistry="your-registry.example.com"

# Upgrade
helm upgrade voiquyr k8s/helm/euvoice-platform --namespace voiquyr --reuse-values

# Uninstall
helm uninstall voiquyr --namespace voiquyr
```

## Verify

```bash
kubectl get pods -n voiquyr
kubectl get svc -n voiquyr
kubectl get ingress -n voiquyr

# Check API health
kubectl port-forward svc/api 8000:8000 -n voiquyr
curl http://localhost:8000/api/v1/health/
```

## EU Compliance

All manifests enforce:
- Node affinity to EU regions (`topology.kubernetes.io/region`)
- Non-root containers (`runAsNonRoot: true`)
- Read-only root filesystem where possible
- Network policies restricting cross-namespace traffic
- Audit logging retention ≥ 7 years (GDPR Art. 30)

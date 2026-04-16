# Local Run Guide — Voiquyr Platform

All shell commands are single-line. Never use `\` continuations.

---

## Option A — Docker (recommended)

Runs everything in containers. No local Python or Node required.

```bash
cp .env.example .env   # fill in real API keys
docker compose up --build
```

| Service | URL |
|---|---|
| Main API + docs | http://localhost:8000/docs |
| Command Center API | http://localhost:8001 |
| Dashboard (React) | http://localhost:3000 |
| Command Center UI | http://localhost:5173 |

Stop and clean up:

```bash
docker compose down -v
```

---

## Option B — Kubernetes

See [`k8s/README.md`](../k8s/README.md) for full instructions. Quick summary:

```bash
# Build images
docker build -t voiquyr/api:latest .
docker build -t voiquyr/command-center-api:latest voiquyr-command-center/backend
docker build -t voiquyr/dashboard:latest frontend
docker build -t voiquyr/command-center-ui:latest --build-arg GEMINI_API_KEY=$GEMINI_API_KEY voiquyr-command-center/frontend

# Push to your registry, then deploy with Helm:
helm install voiquyr k8s/helm/euvoice-platform --namespace voiquyr --create-namespace \
  --set secrets.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secrets.mistralApiKey="$MISTRAL_API_KEY" \
  --set global.imageRegistry="your-registry.example.com"
```

Or use plain kubectl with `k8s/manifests/`.

---

## Option C — Local (manual)

### Prerequisites

- Docker Desktop running (for Postgres + Redis)
- Node.js 18+
- Python 3.14 (already in `.venv`)

---

## Step 1 — Start infrastructure

```bash
docker run -d --name voiquyr-redis -p 6379:6379 redis:alpine
docker run -d --name voiquyr-pg -e POSTGRES_DB=euvoice -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15
```

Verify they're up:

```bash
docker ps
```

---

## Step 2 — Set environment variables

Copy `.env.example` to `.env` and fill in real values (never commit `.env`):

```bash
cp .env.example .env
```

Minimum required values for local dev:

```
JWT_SECRET_KEY=local-dev-secret-change-me
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/euvoice
REDIS_URL=redis://localhost:6379
MISTRAL_API_KEY=your-mistral-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
STRIPE_API_KEY=sk_test_your-stripe-key
```

Export for the current shell session:

```bash
export JWT_SECRET_KEY=local-dev-secret DATABASE_URL=postgresql://postgres:postgres@localhost:5432/euvoice REDIS_URL=redis://localhost:6379
```

---

## Step 3 — Install dependencies

The `.venv` is already set up. If you need to reinstall:

```bash
.venv/bin/pip install -r requirements.txt
```

---

## Step 4 — Run core platform tests

From the workspace root:

```bash
.venv/bin/python -m pytest tests/test_billing_stripe.py tests/test_billing_ucpm.py tests/test_billing_currency.py tests/test_billing_refund.py tests/test_billing_integration.py tests/test_api_simple.py tests/test_foundation.py tests/test_compliance_simple.py tests/test_omnichannel.py tests/test_workflow_automation.py tests/test_support_system.py tests/test_open_telephony.py tests/test_enterprise_telephony.py tests/test_analytics.py -v
```

---

## Step 5 — Run differentiator tests

From the workspace root:

```bash
.venv/bin/python -m pytest tests/test_edge_orchestrator.py tests/test_byoc_adapter.py tests/test_semantic_vad.py tests/test_flash_mode.py tests/test_code_switch_handler.py tests/test_compliance_layer.py tests/test_latency_validator.py tests/test_byoc_feasibility_spike.py -v
```

These test: Edge_Orchestrator, BYOC_Adapter, Semantic_VAD, Flash_Mode, Code_Switch_Handler, Compliance_Layer, Latency_Validator.

---

## Step 6 — Run full test suite

From the workspace root:

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: **766 passed, 14 skipped** (torch/GPU-dependent tests skip automatically), 0 failed.

The previously broken files (`test_compliance_system.py`, `test_tts_agent.py`, `test_voice_cloning.py`, `test_tool_integration.py`, `test_qa_comprehensive.py`, `test_llm_agent.py`) no longer need to be ignored — they either pass or skip gracefully.

---

## Step 7 — Start the main API server

From the workspace root:

```bash
.venv/bin/python -m uvicorn src.api.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

---

## Step 8 — Start the Command Center backend

From `voiquyr-command-center/backend/`:

```bash
.venv/bin/python -m uvicorn main:app --reload --port 8001
```

Note: the command center backend has its own `.venv` at `voiquyr-command-center/backend/.venv/`.

---

## Step 9 — Start the Command Center frontend

From `voiquyr-command-center/frontend/`:

```bash
npm install
npm run dev
```

Opens at http://localhost:5173. The `GEMINI_API_KEY` is already set in `voiquyr-command-center/frontend/env.local`.

---

## Step 10 — Start the main frontend dashboard

From `frontend/`:

```bash
npm install
npm start
```

Opens at http://localhost:3000.

---

## Known Issues

| Issue | Cause | Status |
|---|---|---|
| `test_tts_agent.py`, `test_voice_cloning.py`, `test_tool_integration.py`, `test_llm_agent.py`, `test_specialized_agents.py`, `test_emotion_integration.py`, `test_dataset_training_pipeline.py` | `torch`/`torchaudio` not installed (GPU env required) | Skip automatically via `pytest.importorskip` |
| STT/TTS/LLM endpoints return placeholder responses | Agents not connected to real models in dev | Expected in local dev |

---

## Stopping infrastructure

```bash
docker stop voiquyr-redis voiquyr-pg && docker rm voiquyr-redis voiquyr-pg
```

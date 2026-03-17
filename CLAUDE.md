# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This repo contains two distinct layers:

- **`voiquyr/`** — Business/strategy layer: landing page, client deployments (medgulf, oman, aqaba), strategy docs. Client projects have their own `CLAUDE.md` files.
- **`kiro/voiquyr/`** — Main technical platform (EUVoice AI multi-agent voice AI system).

Most active development happens in `kiro/voiquyr/`.

---

## kiro/voiquyr — Technical Platform

### Commands

**Backend (from `kiro/voiquyr/`):**
```bash
# Activate venv
source .venv/Scripts/activate   # Windows bash
# or: .venv\Scripts\activate.bat

# Run API server
python -m uvicorn src.api.main:app --reload

# Run tests
pytest

# Run a single test file
pytest tests/test_billing_stripe.py -v

# Run tests matching a pattern
pytest -k "test_stt" -v
```

**Main frontend dashboard (from `kiro/voiquyr/frontend/`):**
```bash
npm start          # dev server
npm run build      # production build
npm test           # run tests (no watch)
```

**Command center app (from `kiro/voiquyr/voiquyr-command-center/frontend/`):**
```bash
npm run dev        # Vite dev server (requires GEMINI_API_KEY in .env.local)
```

**Command center backend (from `kiro/voiquyr/voiquyr-command-center/backend/`):**
```bash
uvicorn main:app --reload
```

### Architecture

#### Core voice pipeline
```
Audio Input → STT Agent → LLM Agent → TTS Agent → Audio Output
```
The pipeline is orchestrated by `src/multi_agent_framework.py` (`MultiAgentFramework`), which wires together six core components:

| Component | File | Role |
|---|---|---|
| `MessageRouter` | `src/core/messaging.py` | Priority-queued inter-agent messaging |
| `ServiceRegistry` | `src/core/discovery.py` | Agent registration and health monitoring |
| `AgentOrchestrator` | `src/core/orchestration.py` | Task distribution and load balancing |
| `CoordinationController` | `src/core/coordination.py` | Multi-agent workflow synchronization |
| `QualityMonitor` | `src/core/quality_monitor.py` | Real-time performance and alerting |
| `SharedKnowledgeBase` | `src/core/knowledge_base.py` | Distributed knowledge (Redis + PostgreSQL) |

#### Agents (`src/agents/`)
- **Core pipeline**: `stt_agent.py`, `llm_agent.py`, `tts_agent.py`, `dialog_manager.py`
- **Specialized features**: `emotion_agent.py`, `accent_agent.py`, `arabic_agent.py`, `lip_sync_agent.py`, `language_detection.py`
- **Streaming**: `audio_streaming.py`, `tts_streaming.py`
- **Support**: `tool_integration.py`, `dataset_agent.py`, `model_training.py`, `data_preparation.py`
- **Plugin system**: `agents/plugins/` — extend via `example_plugin.py`

#### REST API (`src/api/`)
- App factory: `app.py` (`create_app()`) — configures middleware, routers, auth, rate limiting
- Configuration: `config.py` (`APIConfig`) — reads env vars; has `eu_data_residency` and `gdpr_mode` flags
- Routers: `routers/voice_processing.py`, `routers/webhooks.py`, `routers/health.py`, `routers/integrations.py`
- Auth: JWT + OAuth2 via `python-jose` (`auth.py`)
- Rate limiting: Redis-backed (`rate_limiter.py`)
- Third-party integrations: `integrations/` (telephony, CRM, messaging)

#### Frontend dashboard (`frontend/`)
React 18 + MUI 5 + Redux Toolkit + react-router-dom. State slices in `store/slices/`. Components grouped by feature: `Audio/`, `Analytics/`, `VoiceConfig/`.

#### Command center (`voiquyr-command-center/`)
A separate, simpler monitoring app. Vite + React 19 frontend (recharts, lucide-react). FastAPI backend with Deepgram + ElevenLabs + Twilio WebSocket handler.

#### Infrastructure (`k8s/`)
Helm chart at `k8s/helm/euvoice-platform/`. Covers autoscaling (HPA/VPA), Istio service mesh, Prometheus/Grafana/Jaeger monitoring, and GDPR/security policies.

### Infrastructure Dependencies

The backend requires running services:
- **Redis** at `redis://localhost:6379` — messaging bus, rate limiting, knowledge cache
- **PostgreSQL** at `postgresql://localhost:5432/euvoice` — persistent storage for knowledge base, webhooks

### Compliance

GDPR/EU AI Act compliance is a first-class concern baked into the codebase:
- `src/compliance/` — `gdpr_validator.py`, `ai_act_validator.py`, `license_validator.py`
- `src/security/` — `audit_system.py`, `data_protection.py`
- `audit_logs/` — runtime audit trail (JSONL + compliance reports)
- All data must remain EU-resident; `APIConfig.eu_data_residency = True` enforces this
- k8s security configs enforce RBAC, network policies, and encryption at rest

---

## voiquyr/ — Client Projects

- **`medgulf/`** — MedGulf Insurance (Jordan pilot). See `medgulf/CLAUDE.md`.
- **`oman/`** — Shape Digital / Oman LNG. See `oman/CLAUDE.md`.
- **`aqaba/`** — InfraTechton consulting knowledge base.
- **`voiquyr-landing/`** — Landing page (Cloudflare Workers), `index.html`.

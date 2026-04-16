# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This repo contains two distinct layers:

- **`voiquyr/`** — Business/strategy layer: landing page, client deployments (medgulf, oman, aqaba), strategy docs. Client projects have their own `CLAUDE.md` files.
- **`kiro/voiquyr/`** — Main technical platform (EUVoice AI multi-agent voice AI system).

Most active development happens in `kiro/voiquyr/`.

---

## kiro/voiquyr — Technical Platform

### Kiro Specs (`.kiro/specs/`)

Two specification sets govern the platform:

| Spec | Path | Scope |
|---|---|---|
| `euvoice-ai-platform` | `.kiro/specs/euvoice-ai-platform/` | Core platform: 22 requirements, 23 tasks (Phase 1 complete, Phase 2 in progress) |
| `voiquyr-differentiators` | `.kiro/specs/voiquyr-differentiators/` | 8 competitive moat features built on top of the core platform |

Each spec contains `requirements.md`, `design.md`, and `tasks.md`.

---

### Commands

> **IMPORTANT — shell commands must always be single-line.** Never use `\` line continuations or multi-line shell commands. zsh will split them and try to execute filenames as scripts. If a pytest invocation lists many files, put them all on one line separated by spaces.

**Backend (from `kiro/voiquyr/`):**
```bash
# Run API server
.venv/bin/python -m uvicorn src.api.main:app --reload

# Run tests (always use .venv/bin/python -m pytest, never bare pytest)
.venv/bin/python -m pytest tests/test_billing_stripe.py -v

# Run tests matching a pattern
.venv/bin/python -m pytest -k "test_stt" -v

# Run multiple test files (one line, space-separated)
.venv/bin/python -m pytest tests/test_billing_stripe.py tests/test_billing_ucpm.py tests/test_api_simple.py -v
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

#### Voiquyr Differentiators (competitive moat layer)

Eight additional components defined in `.kiro/specs/voiquyr-differentiators/` that sit on top of the core platform:

| Component | Tech | Role |
|---|---|---|
| `Edge_Orchestrator` | Go + gRPC + etcd | Jurisdiction-aware call routing to 4 regional edge nodes (Frankfurt, Bahrain, Mumbai, Singapore) |
| `BYOC_Adapter` | Kamailio + RTPEngine | Generic SIP adapter — any RFC 3261 carrier without per-carrier code (G.711/G.722/Opus, SRTP) |
| `Semantic_VAD` | pyannote.audio + distilBERT | End-of-turn detection via prosody + intent scoring, not just silence |
| `Flash_Mode` | Middleware layer on LLM agent | Speculative LLM inference at 85% STT confidence — reduces TTFT by ≥80ms |
| `Code_Switch_Handler` | MMS (Meta multilingual STT) | Arabic↔English and Hindi↔English mid-sentence code-switching, WER <15% |
| `Compliance_Layer` | Python rule engine + PostgreSQL | Per-jurisdiction enforcement: GDPR, UAE PDPL, India DPDP Act, Singapore PDPA |
| `Latency_Validator` | Prometheus + OTel spans | Continuous p95 <500ms validation per region; deployment gate blocker |
| BYOC Feasibility Spike | Kamailio test env | Engineering spike: Tata Communications + Jio SIP trunk validation |

**Pricing context:** €0.09–0.15/min (EU) · $0.09–0.14/min (ME) · ₹6–9/min (India) — all-inclusive UCPM.

**Key SLA targets:** p95 conversational latency <500ms per region, VAD false interruption rate <5%, code-switch WER <15%.

### Infrastructure Dependencies

The backend requires running services:
- **Redis** at `redis://localhost:6379` — messaging bus, rate limiting, knowledge cache
- **PostgreSQL** at `postgresql://localhost:5432/euvoice` — persistent storage for knowledge base, webhooks, compliance records
- **etcd** (or Consul) — tenant jurisdiction config store for `Edge_Orchestrator` (60s TTL cache)
- **Prometheus + Grafana** — latency metrics (`voiquyr_call_latency_ms`, `voiquyr_flash_mode_hit_rate`, etc.)
- **Kamailio + RTPEngine** — SIP proxy and media relay for BYOC_Adapter (per edge node)

### Compliance

Multi-jurisdiction compliance is a first-class concern baked into the codebase:
- `src/compliance/` — `gdpr_validator.py`, `ai_act_validator.py`, `license_validator.py`
- `src/security/` — `audit_system.py`, `data_protection.py`
- `audit_logs/` — runtime audit trail (JSONL + compliance reports)
- `APIConfig.eu_data_residency = True` enforces EU data residency
- k8s security configs enforce RBAC, network policies, and encryption at rest

**Jurisdiction rule sets (voiquyr-differentiators `Compliance_Layer`):**

| Edge Node | Jurisdiction | Rule Set | Erasure SLA |
|---|---|---|---|
| Frankfurt | EU | GDPR 2018 | 30 days |
| Bahrain | Gulf | UAE PDPL 2021 | 30 days |
| Mumbai | India | India DPDP Act 2023 | 7 days |
| Singapore | SEA | Singapore PDPA 2012 | — |

**Data sovereignty guarantee:** `Edge_Orchestrator` rejects calls rather than rerouting to a different jurisdiction if the designated edge node is unavailable.

---

## voiquyr/ — Client Projects

- **`medgulf/`** — MedGulf Insurance (Jordan pilot). See `medgulf/CLAUDE.md`.
- **`oman/`** — Shape Digital / Oman LNG. See `oman/CLAUDE.md`.
- **`aqaba/`** — InfraTechton consulting knowledge base.
- **`voiquyr-landing/`** — Landing page (Cloudflare Workers), `index.html`.

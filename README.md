# EUVoice AI — Voiquyr Platform

> Multi-agent voice AI platform with EU data residency, GDPR compliance, and enterprise integrations.

**Core pipeline:** Phone call / WebSocket → STT → LLM → TTS → Audio response

---

## Repository Structure

```
voiqur-platform/
├── kiro/voiquyr/          # Main technical platform (EUVoice AI engine)
│   ├── src/
│   │   ├── agents/        # STT, LLM, TTS, emotion, accent, Arabic, language detection
│   │   ├── api/           # FastAPI app, routers, auth, rate limiting, integrations
│   │   ├── billing/       # Stripe UCPM billing, currency, refunds
│   │   ├── compliance/    # GDPR validator, EU AI Act validator
│   │   ├── core/          # Multi-agent framework, messaging, orchestration, knowledge base
│   │   ├── security/      # Audit system, data protection
│   │   └── telephony/     # Call controller, SIP trunk registry
│   ├── frontend/          # React 18 + MUI 5 dashboard
│   └── voiquyr-command-center/  # Monitoring + flash simulator app
├── voiquyr/               # Business layer: client deployments, landing page
│   ├── medgulf/           # MedGulf Insurance (Jordan) deployment
│   ├── oman/              # Shape Digital / Oman LNG deployment
│   ├── aqaba/             # InfraTechton consulting knowledge base
│   └── voiquyr-landing/   # Cloudflare Workers landing page
└── .planning/             # GSD project planning (roadmap, phases, research)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Database | PostgreSQL (asyncpg), Redis (aioredis 2.x) |
| Auth | JWT (PyJWT), bcrypt |
| STT | Deepgram SDK (streaming), Mistral Voxtral (fallback) |
| LLM | Mistral API (`mistralai` SDK) |
| TTS | ElevenLabs SDK, XTTS-v2 (self-hosted path) |
| Telephony | Twilio (calls, SMS, media streams) |
| CRM | Salesforce REST API (OAuth2) |
| Messaging | WhatsApp (Twilio), Slack (Bolt), Telegram |
| Billing | Stripe (UCPM, webhooks) |
| Frontend | React 18, MUI 5, Redux Toolkit, react-router-dom |
| Infrastructure | Kubernetes, Helm, Istio, Prometheus/Grafana |
| Compliance | GDPR, EU AI Act — EU data residency enforced |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis running on `localhost:6379`
- PostgreSQL running on `localhost:5432` with database `euvoice`

### Backend

```bash
cd kiro/voiquyr

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# or: .venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# Start API server
python -m uvicorn src.api.main:app --reload
```

### Frontend Dashboard

```bash
cd kiro/voiquyr/frontend
npm install
npm start
```

### Command Center

```bash
# Frontend
cd kiro/voiquyr/voiquyr-command-center/frontend
npm install
npm run dev   # requires GEMINI_API_KEY in .env.local

# Backend
cd kiro/voiquyr/voiquyr-command-center/backend
uvicorn main:app --reload
```

---

## Environment Variables

Copy `kiro/voiquyr/.env.example` to `.env` and fill in:

```env
# AI Services
MISTRAL_API_KEY=
DEEPGRAM_API_KEY=
ELEVENLABS_API_KEY=

# Database
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:password@localhost:5432/euvoice

# Auth
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256

# Telephony & Billing
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
STRIPE_API_KEY=

# Compliance
EU_DATA_RESIDENCY=true
GDPR_MODE=true
```

---

## Architecture

```
Audio Input
    │
    ▼
STT Agent (Deepgram / Voxtral)
    │  transcript
    ▼
LLM Agent (Mistral API)
    │  response + tool calls
    ▼
TTS Agent (ElevenLabs / XTTS-v2)
    │  audio bytes
    ▼
Audio Output (WebSocket / Twilio Media Stream)
```

The pipeline is orchestrated by `MultiAgentFramework` (`src/multi_agent_framework.py`) which wires together six core components: `MessageRouter`, `ServiceRegistry`, `AgentOrchestrator`, `CoordinationController`, `QualityMonitor`, and `SharedKnowledgeBase`.

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Billing (Stripe UCPM) | ✅ 95% | Production key needed |
| Emotion / Accent / Arabic detection | ✅ 100% | — |
| Frontend dashboard | ✅ 95% | Login page stub |
| API framework | ✅ 80% | Auth uses mock users |
| STT agent | 🔧 In progress | Deepgram integration (Sprint 2) |
| LLM agent | ⏳ Pending | Mistral API (Sprint 3) |
| TTS agent | ⏳ Pending | ElevenLabs (Sprint 4) |
| Telephony (Twilio) | ⏳ Pending | Sprint 5 |
| CRM / Messaging | ⏳ Pending | Sprint 6 |
| Command center | ⏳ Pending | Sprint 7 |
| K8s / Helm | ⚠️ 70% | Secrets = changeme |

---

## Running Tests

```bash
cd kiro/voiquyr
source .venv/bin/activate

pytest                          # full suite
pytest tests/test_billing_stripe.py -v
pytest -k "test_stt" -v
pytest --cov=src --cov-report=term-missing
```

---

## Client Deployments

| Client | Directory | Description |
|--------|-----------|-------------|
| MedGulf Insurance | `voiquyr/medgulf/` | Jordan pilot — see `medgulf/CLAUDE.md` |
| Oman LNG | `voiquyr/oman/` | Shape Digital — see `oman/CLAUDE.md` |
| Aqaba | `voiquyr/aqaba/` | InfraTechton consulting knowledge base |

---

## Compliance

GDPR and EU AI Act compliance is first-class:

- All data remains EU-resident (`APIConfig.eu_data_residency = True`)
- GDPR validator: `src/compliance/gdpr_validator.py`
- EU AI Act validator: `src/compliance/ai_act_validator.py`
- Audit trail: `audit_logs/` (JSONL + compliance reports)
- K8s security: RBAC, network policies, encryption at rest

---

## Infrastructure

```bash
# Helm dry-run
helm install euvoice k8s/helm/euvoice-platform --dry-run

# Components: HPA/VPA autoscaling, Istio service mesh,
# Prometheus/Grafana/Jaeger monitoring, GDPR security policies
```

---

## License

Private — all rights reserved.

# EUVoice AI / Voiquyr Platform

## What This Is

EUVoice AI (Voiquyr) is a multi-agent voice AI platform built for EU data residency and GDPR compliance. It orchestrates STT → LLM → TTS pipeline agents to power real-time voice conversations, with integrations for telephony (Twilio), CRM, messaging (WhatsApp/Slack/Telegram), and billing (Stripe). The platform serves as a white-label foundation for enterprise voice AI deployments (e.g. MedGulf, Oman LNG, Aqaba).

## Core Value

Real-time, EU-resident voice AI that connects a phone call or WebSocket stream to intelligent LLM-driven conversation — from audio in to audio out — with full GDPR compliance and enterprise integrations.

## Requirements

### Validated (Shipped in v1.0)

- ✓ Foundation: PostgreSQL + Redis connections, JWT auth with bcrypt password hashing
- ✓ STT Pipeline: Deepgram primary + Voxtral fallback, language detection
- ✓ LLM Pipeline: Real Mistral API inference with tool calling and multi-turn conversations
- ✓ TTS Pipeline: ElevenLabs synthesis + XTTS-v2 self-hosted path, voice cloning
- ✓ Telephony: Twilio HTTP calls, SMS, call controller media stream bridging
- ✓ Billing: Stripe webhook verification + production payment path
- ✓ CRM: Salesforce OAuth2 + contact/case creation
- ✓ Messaging: WhatsApp/Slack/Telegram integrations
- ✓ Frontend: React dashboard with WebSocket audio streaming, command center
- ✓ Testing: 768 tests passing, integration tests with real DB fixtures, compliance E2E
- ✓ Production: Kubernetes manifests, Helm charts, Prometheus metrics, deployment guide
- ✓ Compliance: GDPR/AI Act validators, EU data residency enforcement

### Active (Next Milestone)

- [ ] Performance optimization and caching improvements
- [ ] Self-hosted STT options (Voxtral when released)
- [ ] Self-hosted LLM via vLLM for cost control
- [ ] Enhanced monitoring and alerting
- [ ] Multi-region EU deployment architecture

### Out of Scope

- Mobile apps — web + telephony first; mobile deferred
- Self-hosted LLM at launch — Mistral API sufficient; self-hosted = v2
- Video/visual modalities — voice pipeline only in v1
- Non-EU data residency configurations — EU-first by design

## Context

- **Stack**: Python FastAPI backend, React 18 + MUI 5 frontend, Redis + PostgreSQL, Kubernetes/Helm
- **Repo layout**: `kiro/voiquyr/` is the main technical platform; `voiquyr/` is business/client layer
- **Current state**: v1.0 MVP shipped (2026-04-23). 644 files, ~179K LOC, 768 tests passing.
- **Client deployments**: MedGulf (Jordan), Oman LNG, Aqaba — core platform production-ready
- **GDPR constraint**: All data must remain EU-resident; `APIConfig.eu_data_residency = True` enforced

## Constraints

- **Compliance**: EU AI Act + GDPR compliance is non-negotiable — every integration must preserve data residency
- **Dependencies**: Requires running Redis (localhost:6379) and PostgreSQL (localhost:5432/euvoice) for backend
- **API Keys**: MISTRAL_API_KEY, DEEPGRAM_API_KEY, STRIPE_API_KEY, TWILIO_ACCOUNT_SID/AUTH_TOKEN, ELEVENLABS_API_KEY required
- **K8s**: Requires sealed-secrets operator for production deployment

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deepgram as primary STT | SDK available, streaming support, lower latency than Voxtral | ✅ Implemented |
| Mistral API for LLM | Existing mock structure, EU-based provider | ✅ Implemented |
| ElevenLabs for TTS (with XTTS-v2 self-hosted path) | Immediate results via SDK; self-hosted for cost control | ✅ Implemented |
| asyncpg + aioredis for DB | Async-native, matches FastAPI event loop | ✅ Implemented |
| 10-phase fine-grained plan | Keeps per-phase context small, avoids token blowout | ✅ Validated |

---
*Last updated: 2026-04-23 after v1.0 milestone*
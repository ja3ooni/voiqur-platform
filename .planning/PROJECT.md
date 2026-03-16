# EUVoice AI / Voiquyr Platform

## What This Is

EUVoice AI (Voiquyr) is a multi-agent voice AI platform built for EU data residency and GDPR compliance. It orchestrates STT → LLM → TTS pipeline agents to power real-time voice conversations, with integrations for telephony (Twilio), CRM, messaging (WhatsApp/Slack/Telegram), and billing (Stripe). The platform serves as a white-label foundation for enterprise voice AI deployments (e.g. MedGulf, Oman LNG).

## Core Value

Real-time, EU-resident voice AI that connects a phone call or WebSocket stream to intelligent LLM-driven conversation — from audio in to audio out — with full GDPR compliance and enterprise integrations.

## Requirements

### Validated

- ✓ Billing system (UCPM, currency, refunds) — Phase 1 skeleton
- ✓ Emotion/accent/Arabic/language detection agents — 100%
- ✓ Frontend dashboard (React 18 + MUI 5) — 95%
- ✓ API framework (routes, middleware, rate limiting) — 80%
- ✓ Compliance structure (GDPR/AI Act validators) — skeleton
- ✓ K8s/Helm chart — 70% (secrets = changeme, no images)

### Active

- [ ] Real STT transcription via Deepgram/Voxtral (replaces mock)
- [ ] Real LLM inference via Mistral API (replaces mock responses)
- [ ] Real TTS synthesis via ElevenLabs/XTTS-v2 (replaces sine-wave)
- [ ] Real database connections (Redis + PostgreSQL via asyncpg/aioredis)
- [ ] Real auth with JWT + DB user store (replaces mock user lookup)
- [ ] Twilio telephony HTTP calls (replaces structure-only)
- [ ] Stripe webhook signature verification + production path
- [ ] Salesforce CRM OAuth2 + contact creation
- [ ] WhatsApp/Slack/Telegram messaging integrations
- [ ] Login page (currently 14-line stub)
- [ ] Real WebSocket connections in frontend (env-var URL)
- [ ] Command center frontend (currently empty)
- [ ] Command center backend routers (directory missing)
- [ ] Unit tests for 42 zero-coverage modules
- [ ] Integration + E2E tests
- [ ] K8s secrets via sealed-secrets (replace all `changeme`)
- [ ] DB init job / Alembic migrations
- [ ] CI/CD pipeline (GitHub Actions) + image registry
- [ ] Prometheus metrics in agents and API

### Out of Scope

- Mobile apps — web + telephony only
- Self-hosted LLM serving at runtime — Mistral API only for now
- Video/visual modalities — voice pipeline only
- Non-EU data residency configurations — EU-first by design

## Context

- **Stack**: Python FastAPI backend, React 18 + MUI 5 frontend, Redis + PostgreSQL, Kubernetes/Helm
- **Repo layout**: `kiro/voiquyr/` is the main technical platform; `voiquyr/` is business/client layer
- **Current state**: ~55% implemented. Phase 1 skeleton complete (billing, analytics, compliance structure, frontend shell). All core voice AI is mock data.
- **Client deployments**: MedGulf (Jordan), Oman LNG, Aqaba — these depend on the core platform being production-ready
- **GDPR constraint**: All data must remain EU-resident; `APIConfig.eu_data_residency = True` enforced at config level

## Constraints

- **Compliance**: EU AI Act + GDPR compliance is non-negotiable — every integration must preserve data residency
- **Dependencies**: Requires running Redis (localhost:6379) and PostgreSQL (localhost:5432/euvoice) for backend
- **API Keys**: MISTRAL_API_KEY, DEEPGRAM_API_KEY, STRIPE_API_KEY, TWILIO_ACCOUNT_SID/AUTH_TOKEN, ELEVENLABS_API_KEY required
- **K8s**: Cannot deploy until secrets are replaced and images are defined

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deepgram as primary STT | SDK available, streaming support, lower latency than Voxtral | — Pending |
| Mistral API for LLM | Existing mock structure, EU-based provider | — Pending |
| ElevenLabs for TTS (with XTTS-v2 self-hosted path) | Immediate results via SDK; self-hosted for cost control | — Pending |
| asyncpg + aioredis for DB | Async-native, matches FastAPI event loop | — Pending |
| 10-sprint fine-grained phases | Keeps per-sprint context small, avoids token blowout | — Pending |

---
*Last updated: 2026-03-16 after initialization*

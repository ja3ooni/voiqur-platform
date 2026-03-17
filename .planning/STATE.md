# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Real-time, EU-resident voice AI — audio in to audio out — with GDPR compliance and enterprise integrations
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 10 (Foundation)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-03-17 — Completed 01-01 (dotenv wiring, .env.example)

Progress: [██░░░░░░░░] 7%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 10min
- Total execution time: 0.33 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2/3 | 20min | 10min |

**Recent Trend:**
- Last 5 plans: 01-00 (15min), 01-01 (5min)
- Trend: accelerating

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Setup]: Deepgram as primary STT, Voxtral as fallback
- [Setup]: Mistral API for LLM (EU-based provider)
- [Setup]: ElevenLabs SDK for TTS with XTTS-v2 self-hosted path
- [Setup]: asyncpg + aioredis for async-native DB connections
- [Setup]: 10-sprint fine-grained phases to keep per-sprint context small
- [01-00]: asyncio_mode=auto in pytest.ini — no per-test @pytest.mark.asyncio needed
- [01-00]: aioredis 2.x incompatible with Python 3.14 — guarded with try/except in conftest.py
- [01-00]: Fixtures skip gracefully (not fail) when PostgreSQL/Redis unavailable
- [01-01]: load_dotenv() must be at module level in main.py — uvicorn src.api.main:app bypasses main() entirely
- [01-01]: Root .gitignore covers .env — no per-directory .gitignore needed
- [01-01]: Pydantic v2 removed regex= kwarg in Field(), use pattern= instead

### Pending Todos

None yet.

### Blockers/Concerns

- API keys required before Phase 2+ can be tested: MISTRAL_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, TWILIO_ACCOUNT_SID/AUTH_TOKEN, STRIPE_API_KEY
- Phase 1 prerequisite: Redis (localhost:6379) and PostgreSQL (localhost:5432/euvoice) must be running locally
- K8s cannot be deployed until Phase 10 replaces all `changeme` secrets

## Session Continuity

Last session: 2026-03-17
Stopped at: Completed 01-01-PLAN.md — dotenv wiring (main.py load_dotenv(), .env.example, .env)
Resume file: None

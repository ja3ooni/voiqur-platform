# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-23
**Phases:** 10 | **Plans:** 27 | **Sessions:** ~50+

### What Was Built
- Foundation: PostgreSQL + Redis connections, JWT auth with bcrypt password hashing
- STT Pipeline: Deepgram primary + Voxtral fallback, language detection via langdetect
- LLM Pipeline: Real Mistral API inference with tool calling and multi-turn conversations
- TTS Pipeline: ElevenLabs synthesis + XTTS-v2 self-hosted path with voice cloning
- Telephony: Twilio HTTP calls, SMS, call controller media stream bridging
- Billing: Stripe webhook signature verification and production payment path
- CRM: Salesforce OAuth2 integration with contact/case creation
- Messaging: WhatsApp/Slack/Telegram integrations
- Frontend: React dashboard with WebSocket audio streaming, command center
- Testing: 768 tests passing with integration tests and compliance E2E
- Production: Kubernetes manifests, Helm charts, Prometheus metrics, deployment guide

### What Worked
- 10-phase fine-grained planning kept per-phase context manageable
- Phase structure with PLAN → SUMMARY workflow provided clear deliverables
- GSD workflow automation maintained consistent execution patterns
- Requirement traceability from PROJECT.md → ROADMAP.md → REQUIREMENTS.md
- Test-first approach with xfail stubs before implementation

### What Was Inefficient
- Some phases had stub implementations waiting on API keys (TTS, LLM, STT)
- Requirements tracking in traceability table was not updated consistently with checkboxes
- Phase 10 production readiness items (Alembic, CI/CD) need setup before deployment
- Some test infrastructure (Twilio credentials) not available for full validation

### Patterns Established
- Parallel phase execution for independent tracks (Phases 6 and 7 after Phase 1)
- API key availability gating for cloud service tests
- Environment variable-based configuration for all external services
- EU data residency enforcement at config level

### Key Lessons
1. Plan stub implementations that gracefully degrade when API keys are absent
2. Keep requirements checkboxes and traceability tables in sync throughout phases
3. Set up CI/CD and Alembic migrations early in production readiness phase
4. Document test credential requirements upfront to avoid late-stage blockers

### Cost Observations
- Model mix: Predominantly opus for complex reasoning, haiku for verification
- Sessions: ~50+ across 10 phases
- Notable: GSD workflow reduced context overhead by maintaining state across phases

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~50+ | 10 | Initial build — all phases from scratch |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 768 | ~80% | 644 files |

### Top Lessons (Verified Across Milestones)

1. Fine-grained phases (10 vs 4) reduce context load per session
2. Phase dependencies should be minimized for parallel execution
3. API key availability should be verified before phase execution
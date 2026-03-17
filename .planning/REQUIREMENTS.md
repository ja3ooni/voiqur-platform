# Requirements: EUVoice AI / Voiquyr Platform

**Defined:** 2026-03-16
**Core Value:** Real-time, EU-resident voice AI — audio in to audio out — with GDPR compliance and enterprise integrations

## v1 Requirements

### Foundation

- [x] **FOUND-01**: System loads all secrets from environment variables (`.env` + `APIConfig`)
- [x] **FOUND-02**: `.env.example` documents all required vars (MISTRAL, DEEPGRAM, STRIPE, REDIS, POSTGRES, JWT, TWILIO)
- [x] **FOUND-03**: Redis connects via real `aioredis` connection pool (health check passes)
- [x] **FOUND-04**: PostgreSQL connects via real `asyncpg` connection pool (health check passes)
- [x] **FOUND-05**: DB migration creates tables: users, sessions, knowledge_items, webhook_registrations, audit_logs
- [x] **FOUND-06**: `verify_token()` decodes real JWT and looks up user in PostgreSQL
- [x] **FOUND-07**: User registration endpoint stores bcrypt-hashed passwords in DB
- [x] **FOUND-08**: User login endpoint returns real JWT token
- [x] **FOUND-09**: `/health` endpoint reports real Redis + PostgreSQL connection status

### STT Pipeline

- [ ] **STT-01**: `VoxtralModelManager.transcribe()` calls Deepgram SDK (asynclive streaming)
- [ ] **STT-02**: Fallback to Mistral Voxtral SDK when Deepgram unavailable
- [ ] **STT-03**: `LanguageDetector.detect_language()` uses `langdetect` (not random)
- [ ] **STT-04**: Real transcription results wired into `processing_pipeline.py`
- [ ] **STT-05**: `pytest tests/test_stt_agent.py` passes with DEEPGRAM_API_KEY set

### LLM Pipeline

- [ ] **LLM-01**: `_load_mistral_small_31()` uses real `mistralai` SDK (`MistralClient.chat()`)
- [ ] **LLM-02**: `_generate_mock_response()` removed — all generation through real API
- [ ] **LLM-03**: Tool calling uses Mistral function calling format via existing `ToolCaller`
- [ ] **LLM-04**: `ConversationManager` history passed as `messages` list to Mistral
- [ ] **LLM-05**: Multi-turn conversation with tool call execution verified by tests

### TTS Pipeline

- [ ] **TTS-01**: `XTTSv2ModelManager.synthesize()` calls ElevenLabs SDK (not sine-wave)
- [ ] **TTS-02**: XTTS-v2 via `TTS` library available as self-hosted path
- [ ] **TTS-03**: `VoiceCloningEngine.clone_voice()` uses real speaker embedding (XTTS-v2 `get_conditioning_latents()`)
- [ ] **TTS-04**: Streaming chunks wired into `tts_streaming.py` for WebSocket delivery
- [ ] **TTS-05**: End-to-end pipeline test passes: audio in → STT → LLM → TTS → audio out

### Telephony

- [ ] **TEL-01**: `TwilioIntegration.make_call()` makes real HTTP POST to Twilio Calls API
- [ ] **TEL-02**: `TwilioIntegration.send_sms()` makes real HTTP POST to Twilio Messages API
- [ ] **TEL-03**: `TwilioIntegration.authenticate()` uses Basic Auth (base64 SID:TOKEN)
- [ ] **TEL-04**: `call_controller.py` handles real-time audio bridging via media streams
- [ ] **TEL-05**: SIP trunk provider registry populated with real provider configs
- [ ] **TEL-06**: `pytest tests/test_telephony_abstraction.py` passes with Twilio test credentials

### Billing & Integrations

- [ ] **BILL-01**: Stripe `stripe_service.py` mock fallback removed for production path
- [ ] **BILL-02**: Stripe webhook signature verification implemented
- [ ] **CRM-01**: `SalesforceIntegration` OAuth2 token flow implemented
- [ ] **CRM-02**: Salesforce contact and case creation via REST API
- [ ] **MSG-01**: WhatsApp integration via Twilio Conversations API
- [ ] **MSG-02**: Slack integration via Bolt SDK
- [ ] **MSG-03**: Telegram integration via `python-telegram-bot`

### Frontend & Command Center

- [ ] **FE-01**: Login page (`Login.tsx`) implements full MUI form + Redux auth dispatch
- [ ] **FE-02**: `audioStreamService.ts` WebSocket URL reads from `REACT_APP_API_URL` env var
- [ ] **FE-03**: Command center frontend has Dashboard, Config, FlashSimulator pages
- [ ] **FE-04**: Command center backend has `auth.py`, `sip_trunks.py`, `calls.py`, `health.py` routers

### Test Coverage

- [ ] **TEST-01**: `tests/test_auth.py` covers `src/api/auth.py`
- [ ] **TEST-02**: `tests/test_gdpr_validator.py` covers `src/compliance/gdpr_validator.py`
- [ ] **TEST-03**: `tests/test_ai_act_validator.py` covers `src/compliance/ai_act_validator.py`
- [ ] **TEST-04**: `tests/test_audit_system.py` covers `src/security/audit_system.py`
- [ ] **TEST-05**: `tests/test_call_controller.py` covers `src/telephony/call_controller.py`
- [ ] **TEST-06**: `tests/test_dialog_manager.py` covers `src/agents/dialog_manager.py`
- [ ] **TEST-07**: `tests/test_messaging.py` covers `src/core/messaging.py`
- [ ] **TEST-08**: `tests/test_orchestration.py` covers `src/core/orchestration.py`
- [ ] **TEST-09**: Integration tests use real test DB fixtures (pytest-asyncio + asyncpg pool)
- [ ] **TEST-10**: E2E test: full call flow audio → STT → LLM → TTS → response
- [ ] **TEST-11**: Compliance E2E: EU data residency enforcement test

### Production Readiness

- [ ] **PROD-01**: K8s secrets replaced with sealed-secrets or external-secrets references
- [ ] **PROD-02**: DB init job or Alembic migrations for PostgreSQL schema
- [ ] **PROD-03**: GitHub Actions CI/CD pipeline builds and pushes 4 service images
- [ ] **PROD-04**: PVCs defined for PostgreSQL and Redis using `gp3-encrypted` storage class
- [ ] **PROD-05**: Prometheus metrics wired in agents and API via `prometheus-client`
- [ ] **PROD-06**: `helm install --dry-run` passes
- [ ] **PROD-07**: `k8s/DEPLOYMENT_GUIDE.md` documents secrets management

## v2 Requirements

### Advanced Features

- **ADV-01**: Voxtral self-hosted STT (when model released)
- **ADV-02**: Self-hosted LLM via vLLM for cost control
- **ADV-03**: Multi-region EU deployment (beyond single-cluster)
- **ADV-04**: Visual/video modality pipeline

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile apps | Web + telephony first; mobile deferred |
| Non-EU data residency | Compliance requirement, by design |
| Real-time video | Voice pipeline only in v1 |
| Self-hosted LLM at launch | Mistral API sufficient; self-hosted = v2 |
| OAuth login for end-users | JWT/password sufficient for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| FOUND-06 | Phase 1 | Complete |
| FOUND-07 | Phase 1 | Complete |
| FOUND-08 | Phase 1 | Complete |
| FOUND-09 | Phase 1 | Complete |
| STT-01 | Phase 2 | Pending |
| STT-02 | Phase 2 | Pending |
| STT-03 | Phase 2 | Pending |
| STT-04 | Phase 2 | Pending |
| STT-05 | Phase 2 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| LLM-03 | Phase 3 | Pending |
| LLM-04 | Phase 3 | Pending |
| LLM-05 | Phase 3 | Pending |
| TTS-01 | Phase 4 | Pending |
| TTS-02 | Phase 4 | Pending |
| TTS-03 | Phase 4 | Pending |
| TTS-04 | Phase 4 | Pending |
| TTS-05 | Phase 4 | Pending |
| TEL-01 | Phase 5 | Pending |
| TEL-02 | Phase 5 | Pending |
| TEL-03 | Phase 5 | Pending |
| TEL-04 | Phase 5 | Pending |
| TEL-05 | Phase 5 | Pending |
| TEL-06 | Phase 5 | Pending |
| BILL-01 | Phase 6 | Pending |
| BILL-02 | Phase 6 | Pending |
| CRM-01 | Phase 6 | Pending |
| CRM-02 | Phase 6 | Pending |
| MSG-01 | Phase 6 | Pending |
| MSG-02 | Phase 6 | Pending |
| MSG-03 | Phase 6 | Pending |
| FE-01 | Phase 7 | Pending |
| FE-02 | Phase 7 | Pending |
| FE-03 | Phase 7 | Pending |
| FE-04 | Phase 7 | Pending |
| TEST-01 | Phase 8 | Pending |
| TEST-02 | Phase 8 | Pending |
| TEST-03 | Phase 8 | Pending |
| TEST-04 | Phase 8 | Pending |
| TEST-05 | Phase 8 | Pending |
| TEST-06 | Phase 8 | Pending |
| TEST-07 | Phase 8 | Pending |
| TEST-08 | Phase 8 | Pending |
| TEST-09 | Phase 9 | Pending |
| TEST-10 | Phase 9 | Pending |
| TEST-11 | Phase 9 | Pending |
| PROD-01 | Phase 10 | Pending |
| PROD-02 | Phase 10 | Pending |
| PROD-03 | Phase 10 | Pending |
| PROD-04 | Phase 10 | Pending |
| PROD-05 | Phase 10 | Pending |
| PROD-06 | Phase 10 | Pending |
| PROD-07 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 — traceability expanded to individual requirement rows*

# Product Requirements Document: Voiquyr Platform (EUVoice AI)

**Version:** 1.0
**Date:** 2026-04-17
**Author:** Product Team
**Status:** Draft

---

## 1. Problem Statement

Enterprise and SMB customers in the EU, Middle East, and Asia need conversational voice AI for customer-facing use cases — inbound call centers, outbound campaigns, appointment scheduling, and multi-channel support. Today, they face three compounding problems:

1. **No EU-compliant option exists.** The dominant player (Vapi) is US-based with limited GDPR guarantees and zero EU AI Act compliance. Government, healthcare, and financial services customers in the EU cannot adopt it without legal risk. Data residency is not configurable — it's US-first by design.

2. **Vendor lock-in on telephony.** Existing voice AI platforms hardcode a single telephony provider (Twilio). Enterprises with existing PBX infrastructure (Asterisk, FreeSWITCH, Kamailio) or regional SIP carriers cannot bring their own carrier, forcing expensive migrations and dual billing.

3. **Developer-only UX blocks adoption.** Current platforms require JSON configuration and backend coding for every conversation flow. Non-technical users (operations managers, marketing teams, small business owners) are locked out, creating a dependency bottleneck on engineering resources.

**Who is affected:** Contact center operators, enterprise IT teams, government agencies, SMBs, and system integrators across EU/MEA/Asia markets — estimated TAM of 50,000+ organizations in the EU alone that need GDPR-compliant voice AI.

**Cost of not solving:** Organizations either operate without voice AI automation (leaving 60-70% of call volume unautomated) or use non-compliant US platforms and accept regulatory risk (GDPR fines up to 4% of global revenue).

---

## 2. Goals

### User Goals

| # | Goal | Metric |
|---|------|--------|
| U1 | Deploy a production voice AI agent from zero to live call in under 1 hour | Time-to-first-call < 60 min for template-based deployments |
| U2 | Build conversation flows without writing code | 80%+ of standard flows configurable via visual builder alone |
| U3 | Use existing telephony infrastructure without migration | BYOC adapter supports Asterisk, FreeSWITCH, Kamailio, and direct SIP trunking |

### Business Goals

| # | Goal | Metric |
|---|------|--------|
| B1 | Become the default EU-compliant voice AI platform | 3 paying enterprise deployments within 6 months of GA (MedGulf, Oman LNG, Aqaba pipeline active) |
| B2 | Achieve predictable unit economics via UCPM billing | UCPM margin > 40% at €0.04/min blended rate |
| B3 | Build defensible competitive moats through open-source community and EU compliance | 500+ GitHub stars, 10+ community contributors within 12 months of open-source release |

---

## 3. Non-Goals

| # | Non-Goal | Rationale |
|---|----------|-----------|
| NG1 | Mobile native apps (iOS/Android) | Web + telephony covers 95% of use cases; mobile deferred to v2+ |
| NG2 | Self-hosted LLM inference at launch | Mistral API provides sufficient quality/latency; self-hosted via vLLM is a v2 cost-optimization play |
| NG3 | Video or visual modalities | Voice pipeline is the core product; video (lip sync agent exists as skeleton) deferred to v2 |
| NG4 | Non-EU data residency configurations | EU-first is the core differentiator; multi-region is a v2 feature (ADV-03) |
| NG5 | OAuth/SSO login for end-users at launch | JWT/password auth sufficient for v1; enterprise SSO (SAML, OIDC) deferred |

---

## 4. User Stories

### Persona: Contact Center Manager (non-technical)

- **US-01:** As a contact center manager, I want to deploy a pre-built appointment scheduling voice agent using a template, so that I can automate 40% of inbound calls without involving engineering.
- **US-02:** As a contact center manager, I want to see real-time call analytics (volume, duration, sentiment, resolution rate) in a dashboard, so that I can make staffing decisions based on data.
- **US-03:** As a contact center manager, I want the AI agent to hand off to a human operator when it detects frustration or an unresolvable query, so that customer satisfaction stays above target.

### Persona: Enterprise IT / DevOps Engineer

- **US-04:** As a DevOps engineer, I want to deploy the platform on our existing Kubernetes cluster using Helm charts with sealed secrets, so that it integrates with our infrastructure-as-code workflow.
- **US-05:** As a DevOps engineer, I want to connect our existing Asterisk PBX to the platform via the BYOC adapter, so that we don't need to migrate to Twilio or pay double for telephony.
- **US-06:** As a DevOps engineer, I want the platform to enforce EU data residency at the infrastructure level (not just configuration), so that we pass our annual GDPR audit without exceptions.

### Persona: Voice AI Developer / Integrator

- **US-07:** As a developer, I want a WebSocket API that streams audio in and receives synthesized audio out in real-time, so that I can integrate voice AI into our custom web application.
- **US-08:** As a developer, I want to register custom tools (API calls, DB lookups) that the LLM agent can invoke during conversation, so that the voice agent can take actions on behalf of the caller.
- **US-09:** As a developer, I want to clone a customer's brand voice using a 30-second audio sample, so that the TTS output matches their brand identity.

### Persona: Compliance Officer

- **US-10:** As a compliance officer, I want to generate monthly compliance reports that prove all voice data was processed within EU boundaries, so that I can submit evidence to our Data Protection Officer.
- **US-11:** As a compliance officer, I want the platform to automatically enforce data retention policies per jurisdiction (EU: 365 days, India DPDP: 180 days, UAE PDPL: configurable), so that we don't manually track deletion schedules.

### Edge Cases

- **US-12:** As a caller who code-switches between Arabic and English mid-sentence, I want the STT agent to correctly transcribe both languages at word-level granularity, so that the LLM understands my full intent.
- **US-13:** As an operator during a regional telephony outage, I want the platform to failover to an alternate SIP trunk within 5 seconds, so that active calls are not dropped.

---

## 5. Requirements

### P0 — Must Have (Cannot Ship Without)

| ID | Requirement | Acceptance Criteria | Dependencies |
|----|-------------|---------------------|--------------|
| P0-01 | **Real-time STT via Deepgram** | Given a WAV audio stream, when sent to the STT agent, then a real transcript string is returned within 500ms (not a mock). Deepgram SDK (asynclive streaming) is the primary path. | DEEPGRAM_API_KEY |
| P0-02 | **STT Fallback to Voxtral** | Given DEEPGRAM_API_KEY is absent, when the STT agent receives audio, then it falls back to Mistral Voxtral SDK without crashing and returns a transcript. | MISTRAL_API_KEY |
| P0-03 | **Real LLM inference via Mistral API** | Given a user message, when sent to the LLM agent, then `MistralClient.chat()` generates the response. `_generate_mock_response()` no longer exists in the codebase. | MISTRAL_API_KEY |
| P0-04 | **Multi-turn conversation with tool calling** | Given a 3+ turn conversation with tool calls, when each turn is processed, then the full `messages` history is passed to Mistral, tool calls execute via `ToolCaller`, and results flow back into the next LLM call. | P0-03 |
| P0-05 | **Real TTS via ElevenLabs** | Given an LLM response text, when sent to the TTS agent, then `XTTSv2ModelManager.synthesize()` returns real audio bytes via ElevenLabs SDK (not a sine-wave buffer). | ELEVENLABS_API_KEY |
| P0-06 | **End-to-end voice pipeline** | Given an audio input file, when processed through the full pipeline (STT → LLM → TTS), then non-empty audio bytes are returned as output. | P0-01, P0-03, P0-05 |
| P0-07 | **Twilio telephony integration** | Given valid Twilio credentials, when `make_call()` is invoked, then a real HTTP POST to `api.twilio.com/Calls` succeeds and returns a call SID. `send_sms()` works equivalently. | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN |
| P0-08 | **Call controller audio bridging** | Given an active Twilio Media Stream WebSocket, when audio frames arrive, then `call_controller.py` routes them to the STT agent and returns TTS audio back to the stream. | P0-06, P0-07 |
| P0-09 | **GDPR data residency enforcement** | Given `EU_DATA_RESIDENCY=true`, when any data processing request is made, then no data leaves the EU-resident endpoint. Verified by compliance E2E test. | — |
| P0-10 | **EU AI Act compliance validation** | Given a voice AI deployment, when the AI Act validator runs, then it classifies the system's risk level and produces an audit-ready report. | — |
| P0-11 | **JWT authentication with real DB** | Given a registered user, when they POST to `/auth/login`, then a signed JWT is returned and accepted by all protected routes. Users stored in PostgreSQL with bcrypt-hashed passwords. | PostgreSQL |
| P0-12 | **Health endpoint with real infrastructure** | Given running Redis and PostgreSQL, when GET `/health` is called, then it returns `{"redis": "ok", "postgres": "ok"}`. | Redis, PostgreSQL |

### P1 — Should Have (Core UX works without, fast follow-up)

| ID | Requirement | Acceptance Criteria | Dependencies |
|----|-------------|---------------------|--------------|
| P1-01 | **BYOC SIP adapter** | Given an Asterisk/FreeSWITCH trunk configuration, when registered with the BYOC adapter, then calls route through the customer's carrier with codec transcoding (G.711, G.722, Opus). | Kamailio, RTPEngine |
| P1-02 | **Semantic VAD (intelligent turn detection)** | Given streaming audio with pauses, when prosody + intent analysis runs, then end-of-turn is detected with <50ms latency and <5% false interruption rate. | — |
| P1-03 | **Flash Mode (speculative LLM inference)** | Given a partial transcript with >85% confidence, when Flash Mode is enabled, then speculative inference begins, reducing TTFT by ~80ms. Reconciliation handles misses. | P0-03 |
| P1-04 | **Code-switching STT** | Given Arabic/English code-switched speech, when processed by Code_Switch_Handler, then word-level language identification achieves <15% WER. | P0-01 |
| P1-05 | **Voice cloning** | Given a 30-second audio sample, when `VoiceCloningEngine.clone_voice()` is called, then a usable voice embedding is returned via XTTS-v2 `get_conditioning_latents()`. | XTTS-v2 model |
| P1-06 | **TTS streaming over WebSocket** | Given an LLM response, when TTS generates audio, then chunks stream to the client via WebSocket in real-time (not batch). | P0-05 |
| P1-07 | **Stripe UCPM billing (production path)** | Given a call session, when billing is triggered, then Stripe charges the customer per UCPM rate with webhook signature verification. Mock fallback removed. | STRIPE_API_KEY |
| P1-08 | **Stripe auto-refunds for failures** | Given a call that fails mid-session due to platform error, when the failure is detected, then the refund engine automatically issues a prorated Stripe refund. | P1-07 |
| P1-09 | **Multi-currency billing** | Given a customer in a non-EUR currency, when they view their bill, then amounts are displayed in their local currency using real-time exchange rates. | P1-07 |
| P1-10 | **Login page (full MUI form)** | Given a user navigating to `/login`, when they submit valid credentials, then Redux auth dispatch occurs and redirects to the dashboard. | P0-11 |
| P1-11 | **Frontend WebSocket configuration** | Given `REACT_APP_API_URL` environment variable, when `audioStreamService.ts` initializes, then the WebSocket URL is read from env (not hardcoded). | — |

### P2 — Could Have (Desirable, will not delay delivery)

| ID | Requirement | Acceptance Criteria | Dependencies |
|----|-------------|---------------------|--------------|
| P2-01 | **Salesforce CRM integration** | Given valid Salesforce OAuth2 credentials, when a call completes, then a contact record and case are created in Salesforce automatically. | Salesforce sandbox |
| P2-02 | **WhatsApp messaging integration** | Given a Twilio Conversations API key, when a customer messages via WhatsApp, then the LLM agent responds through the WhatsApp channel. | Twilio |
| P2-03 | **Slack integration** | Given a Slack Bolt SDK token, when a trigger event occurs, then a notification or response is sent to the configured Slack channel. | Slack app |
| P2-04 | **Telegram integration** | Given a Telegram bot token, when a user messages the bot, then the LLM agent processes and responds. | Telegram bot |
| P2-05 | **Visual conversation flow builder** | Given the no-code dashboard, when a user opens the flow builder, then they can drag-and-drop conversation nodes, set branching conditions, and publish flows without code. | P1-10 |
| P2-06 | **Command center (monitoring app)** | Given the command center app, when an operator accesses it, then Dashboard, Config, and FlashSimulator pages render with real-time data. Backend routers (auth, sip_trunks, calls, health) all respond. | P0-12 |
| P2-07 | **Emotion detection in calls** | Given a live call audio stream, when emotion analysis runs, then caller sentiment (positive, negative, neutral, frustrated) is classified and surfaced in analytics. | P0-01 |
| P2-08 | **A/B testing for conversation flows** | Given two flow variants, when calls are routed, then traffic splits according to configured percentages and conversion metrics are tracked per variant. | P2-05 |

### Won't Have (v1)

| Feature | Rationale |
|---------|-----------|
| Mobile native apps | Web + telephony first |
| Self-hosted LLM (vLLM) | Mistral API sufficient for v1; cost optimization in v2 |
| Video/lip-sync modalities | Voice-only scope |
| Multi-region EU deployment | Single EU cluster for v1; multi-region in v2 (ADV-03) |
| OAuth/SSO (SAML, OIDC) | JWT/password auth covers v1 needs |
| Voxtral self-hosted STT | Pending model release; Deepgram primary for now |

---

## 6. Success Metrics

### Leading Indicators (measure within 30 days of GA)

| Metric | Target | Measurement Method | Evaluation Timeline |
|--------|--------|--------------------|---------------------|
| Time-to-first-call | < 60 min (template) / < 4 hrs (custom) | Onboarding funnel tracking | First 30 days |
| End-to-end pipeline latency (p95) | < 500ms | Latency Validator synthetic tests (every 5 min) | Continuous |
| STT transcription accuracy (WER) | < 10% (English), < 15% (code-switched) | Benchmark test suite against reference transcripts | Monthly |
| API uptime | > 99.5% | Prometheus + health endpoint monitoring | Continuous |
| False interruption rate (Semantic VAD) | < 5% | VAD accuracy benchmarks | Monthly |

### Lagging Indicators (measure 90+ days post-GA)

| Metric | Target | Measurement Method | Evaluation Timeline |
|--------|--------|--------------------|---------------------|
| Paying enterprise deployments | 3+ within 6 months | CRM pipeline tracking | Quarterly |
| UCPM gross margin | > 40% | Stripe billing vs. provider costs | Monthly |
| Customer retention (monthly) | > 90% | Billing churn analysis | Quarterly |
| GDPR compliance audit pass rate | 100% | Compliance report generation | Per audit |
| Support ticket resolution time | < 4 hrs (P1), < 24 hrs (P2) | Ticketing system SLA tracking | Monthly |

### Baseline Measurements Needed Before Launch

- Current call automation rate for pilot customers (MedGulf, Oman LNG) — need baseline to measure improvement
- Provider cost breakdown per minute (Deepgram + Mistral + ElevenLabs + Twilio) — validates UCPM margin target

---

## 7. Open Questions

| # | Question | Owner | Blocking? |
|---|----------|-------|-----------|
| OQ-1 | What is the actual per-minute cost breakdown for Deepgram + Mistral + ElevenLabs + Twilio at projected volume? Validates the €0.04 UCPM target. | Finance / Product | Yes — blocks pricing finalization |
| OQ-2 | Should XTTS-v2 self-hosted TTS be offered as a toggle at launch, or deferred until cost pressure justifies it? | Engineering | No — ElevenLabs SDK covers launch |
| OQ-3 | MedGulf pilot requires Arabic dialect support (Jordanian Arabic). Is the current Arabic agent + code-switch handler sufficient, or do we need dialect-specific fine-tuning? | ML / Product | Yes — blocks MedGulf deployment sign-off |
| OQ-4 | K8s secrets are all `changeme`. What secrets management solution (sealed-secrets vs. external-secrets-operator vs. Vault) aligns with target customer infrastructure? | DevOps | No — must decide before Phase 10, not blocking current sprints |
| OQ-5 | Licensing: README says Apache 2.0, but the root LICENSE says "Private — all rights reserved." Which is the intended license for GA? | Legal / Founder | Yes — blocks open-source community strategy (B3) |
| OQ-6 | The Oman LNG deployment references "Shape Digital" as a partner. Is this a reseller, SI, or direct customer? Affects pricing model. | Sales | No — but informs go-to-market strategy |

---

## 8. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│  Phone Call │ WebSocket │ WhatsApp │ Slack │ Telegram │ WebChat │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Edge Orchestrator                              │
│  Jurisdiction routing │ BYOC SIP Adapter │ Compliance admission  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Voice Processing Pipeline                       │
│                                                                   │
│  ┌─────────────┐   ┌───────────┐   ┌─────────────┐              │
│  │ STT Agent   │──▶│ LLM Agent │──▶│ TTS Agent   │              │
│  │ (Deepgram/  │   │ (Mistral  │   │ (ElevenLabs │              │
│  │  Voxtral)   │   │  API)     │   │  / XTTS-v2) │              │
│  └─────────────┘   └───────────┘   └─────────────┘              │
│         │                │                │                       │
│  Semantic VAD    Tool Calling      TTS Streaming                 │
│  Code-Switch     Flash Mode        Voice Cloning                 │
│  Language Det.   Dialog Mgr        Emotion Agent                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Platform Services                              │
│                                                                   │
│  Billing (Stripe UCPM) │ Auth (JWT/bcrypt) │ Analytics Engine    │
│  Compliance (GDPR/AI Act) │ Audit System │ Knowledge Base        │
│  Webhook Service │ Rate Limiter │ Monitoring (Prometheus)        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Infrastructure                                 │
│  PostgreSQL │ Redis │ Kubernetes (Helm) │ Istio │ Grafana/Jaeger │
└──────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Database | PostgreSQL (asyncpg), Redis (aioredis 2.x) |
| Auth | JWT (PyJWT), bcrypt |
| STT | Deepgram SDK (streaming), Mistral Voxtral (fallback) |
| LLM | Mistral API (mistralai SDK) |
| TTS | ElevenLabs SDK, XTTS-v2 (self-hosted path) |
| Telephony | Twilio (calls, SMS, media streams); BYOC via Kamailio/RTPEngine |
| CRM | Salesforce REST API (OAuth2) |
| Messaging | WhatsApp (Twilio), Slack (Bolt), Telegram |
| Billing | Stripe (UCPM, webhooks) |
| Frontend | React 18, MUI 5, Redux Toolkit |
| Infrastructure | Kubernetes, Helm, Istio, Prometheus/Grafana/Jaeger |
| Compliance | GDPR, EU AI Act — EU data residency enforced |

---

## 9. Implementation Phases

The platform is ~55% complete. Phase 1 (Foundation) is done. Remaining phases:

| Phase | Scope | Status | Requirements |
|-------|-------|--------|-------------|
| Phase 1: Foundation | Config, DB connections, JWT auth | Complete (2026-03-17) | FOUND-01 through FOUND-09 |
| Phase 2: STT | Deepgram/Voxtral real transcription | Not started | STT-01 through STT-05 |
| Phase 3: LLM | Mistral API real inference | Not started | LLM-01 through LLM-05 |
| Phase 4: TTS | ElevenLabs/XTTS-v2 real synthesis | Not started | TTS-01 through TTS-05 |
| Phase 5: Telephony | Twilio HTTP calls, call controller | Not started | TEL-01 through TEL-06 |
| Phase 6: Billing & Integrations | Stripe production, CRM, messaging | Not started | BILL-01/02, CRM-01/02, MSG-01/02/03 |
| Phase 7: Frontend & Command Center | Login, WebSocket config, monitoring app | Not started | FE-01 through FE-04 |
| Phase 8: Unit Tests | 42 zero-coverage modules | Not started | TEST-01 through TEST-08 |
| Phase 9: Integration & E2E Tests | DB fixtures, full call flow, compliance | Not started | TEST-09 through TEST-11 |
| Phase 10: Production Readiness | K8s secrets, migrations, CI/CD, metrics | Not started | PROD-01 through PROD-07 |

**Parallelization note:** Phases 6 and 7 depend only on Phase 1 and can run in parallel with Phases 2-5.

---

## 10. Client Deployments (Dependent on v1 GA)

| Client | Region | Use Case | Status |
|--------|--------|----------|--------|
| MedGulf Insurance | Jordan | Inbound claims / appointment scheduling (Arabic + English) | Pilot — awaiting core pipeline |
| Oman LNG (via Shape Digital) | Oman | Enterprise voice automation | Pilot — awaiting core pipeline |
| InfraTechton (Aqaba) | Jordan | Consulting knowledge base voice interface | Pilot — awaiting core pipeline |

---

*Document generated from repository analysis of [ja3ooni/voiqur-platform](https://github.com/ja3ooni/voiqur-platform).*

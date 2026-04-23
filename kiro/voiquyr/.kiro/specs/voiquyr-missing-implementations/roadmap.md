# Roadmap - Voiquyr Missing Implementations

## Timeline Overview

| Phase | Duration | Focus | Key Deliverables |
|-------|----------|-------|-----------------|
| **Phase 1: Core Pipeline** | Weeks 1-4 | Real voice pipeline | STT → LLM → TTS working |
| **Phase 2: Telephony** | Weeks 5-8 | Call handling | Twilio + Asterisk + Billing |
| **Phase 3: Developer Platform** | Weeks 9-12 | SDKs + API | Python/TS SDKs, Command Center |
| **Phase 4: Production** | Weeks 13-16 | Infrastructure | CI/CD, Metrics, Tests |

**Total Duration**: 16 weeks (4 months)

---

## Phase 1: Core Voice Pipeline (Weeks 1-4)

### Goals
- Replace all mock implementations with real API integrations
- Establish working STT → LLM → TTS chain
- Remove all hardcoded responses, sine waves, and stubs

###Sprint Breakdown

#### Sprint 1.1: STT Integration (Week 1-2)
- Connect Deepgram Nova-3 streaming
- Implement Voxtral fallback when Deepgram unavailable
- Add proper error handling and timeouts
- Unit tests for STT agent

#### Sprint 1.2: LLM Integration (Week 2-3)
- Connect Mistral Small API
- Implement Ollama fallback
- Add streaming token response
- Remove `_generate_mock_response()` entirely

#### Sprint 1.3: TTS Integration (Week 3-4)
- Connect ElevenLabs Flash
- Implement Piper fallback
- Audio streaming support
- Replace sine wave generation

#### Sprint 1.4: Pipeline Integration (Week 4)
- Connect STT → LLM → TTS chain
- End-to-end testing with real audio
- Latency optimization
- Property-based tests

**Phase 1 Deliverables**:
- `src/agents/stt_agent.py` - Real Deepgram/Voxtral
- `src/agents/llm_agent.py` - Real Mistral/Ollama
- `src/agents/tts_agent.py` - Real ElevenLabs/Piper
- E2E voice pipeline working
- 70% test coverage on voice pipeline modules

---

## Phase 2: Telephony & Billing (Weeks 5-8)

### Goals
- Full Twilio integration for inbound/outbound calls
- Asterisk AudioSocket support
- Production Stripe billing
- Live exchange rate fetching

### Sprint Breakdown

#### Sprint 2.1: Twilio Integration (Week 5)
- Inbound call webhook with signature validation
- Media stream handling
- Outbound call initiation
- Call status callbacks

#### Sprint 2.2: Asterisk Integration (Week 6)
- AudioSocket TCP connection handler
- Audio frame processing
- Session management
- Clean disconnection handling

#### Sprint 2.3: Stripe Billing (Week 7)
- Real Stripe API integration
- Usage record creation
- Webhook processing with idempotency
- Refund handling

#### Sprint 2.4: Currency & UCPM (Week 8)
- Live exchange rate API
- UCPM calculation
- Multi-currency support
- Invoice generation

**Phase 2 Deliverables**:
- `src/telephony/twilio_bridge.py` - Twilio integration
- `src/telephony/asterisk_bridge.py` - Asterisk integration
- `src/billing/stripe_service.py` - Real Stripe
- `src/billing/currency_manager.py` - Exchange rates
- Full call flow with billing

---

## Phase 3: Developer Platform (Weeks 9-12)

### Goals
- Python SDK (PyPI)
- TypeScript SDK (npm)
- Command Center improvements
- WebRTC demo page
- Quickstart documentation

### Sprint Breakdown

#### Sprint 3.1: Python SDK (Week 9)
- VoiquyrClient class
- `make_call()`, `list_agents()`, `stream_audio()`
- PyPI package setup
- README with examples

#### Sprint 3.2: TypeScript SDK (Week 10)
- VoiquyrClient class
- TypeScript definitions
- npm package publishing
- README with examples

#### Sprint 3.3: Command Center (Week 11)
- Login flow completion
- Real-time dashboard with WebSocket
- Agent configuration UI
- Environment variable config

#### Sprint 3.4: WebRTC Demo + Docs (Week 12)
- Landing page demo
- Public demo phone number
- Quickstart guide
- API documentation

**Phase 3 Deliverables**:
- `voiquyr/` - Python SDK on PyPI
- `@voiquyr/sdk` - TypeScript SDK on npm
- `voiquyr-command-center/` - Complete frontend
- WebRTC demo page
- Documentation

---

## Phase 4: Production Readiness (Weeks 13-16)

### Goals
- Database migrations (Alembic)
- CI/CD pipeline
- Prometheus metrics
- Test coverage to 70%+
- Kubernetes secrets remediation

### Sprint Breakdown

#### Sprint 4.1: Database Migrations (Week 13)
- Alembic setup
- Initial migration
- Migration testing in CI

#### Sprint 4.2: CI/CD Pipeline (Week 14)
- GitHub Actions workflow
- Test execution
- Docker build
- Image push

#### Sprint 4.3: Monitoring & Observability (Week 15)
- Prometheus `/metrics` endpoint
- Key metrics implementation
- ServiceMonitor for K8s
- SLO definitions

#### Sprint 4.4: Security & Cleanup (Week 16)
- Remove `changeme` secrets
- Sealed Secrets setup
- Test coverage to 70%+
- Final integration tests

**Phase 4 Deliverables**:
- `alembic/` - Database migrations
- `.github/workflows/ci.yml` - CI/CD pipeline
- `src/monitoring/metrics.py` - Prometheus metrics
- Kubernetes secrets remediation
- 70% test coverage

---

## Resource Allocation

### Team Structure
| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|----------|
| Backend Engineer | 2 | 2 | 1 | 1 |
| Frontend Engineer | 0 | 0 | 2 | 1 |
| DevOps Engineer | 0 | 0 | 1 | 2 |
| QA Engineer | 1 | 1 | 1 | 1 |

### External Dependencies
| Dependency | Required By | Notes |
|-----------|------------|-------|
| Deepgram API Key | Sprint 1.1 | Get from deepgram.com |
| Mistral API Key | Sprint 1.2 | Get from mistral.ai |
| ElevenLabs API Key | Sprint 1.3 | Get from elevenlabs.io |
| Stripe Account | Sprint 2.3 | Production account |
| Twilio Account | Sprint 2.1 | Phone number + credentials |
| PyPI Account | Sprint 3.1 | For package publishing |
| npm Account | Sprint 3.2 | For package publishing |

---

## Milestones

### Milestone 1: First Real Call (End of Week 4)
- Audio in → Transcript → LLM Response → Audio out
- All real providers, no mocks
- Demo with test credentials

### Milestone 2: Production Billing (End of Week 8)
- Real Stripe charges
- Live exchange rates
- Working Twilio/Asterisk

### Milestone 3: Developer GA (End of Week 12)
- Python SDK on PyPI
- TypeScript SDK on npm
- Complete documentation

### Milestone 4: Production Ready (End of Week 16)
- CI/CD pipeline passing
- 70%+ test coverage
- Prometheus metrics
- Kubernetes secrets fixed

---

## Go-to-Market Plan

### Pre-Launch (Weeks 1-12)
| Week | Activity | Target |
|------|---------|--------|
| 4 | Private beta | Selected developers |
| 8 | Integration partners | 3 beta customers |
| 12 | Public beta | Open registration |

### Launch (Week 13-16)
| Week | Activity | Target |
|------|---------|--------|
| 13 | Soft launch | Early adopters |
| 14 | SDKs public | Developer community |
| 15 | Press release | Tech media |
| 16 | General availability | Public launch |

### Pricing (UCPM Model)
| Tier | Rate | Includes |
|------|------|---------|
| Developer | $0.05/min | Basic agents |
| Pro | $0.08/min | Custom voices |
| Enterprise | Custom | Dedicated infrastructure |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| API provider downtime | Medium | High | Multiple fallbacks |
| SDK adoption low | Medium | Medium | Developer relations |
| Test coverage targets missed | High | Medium | Extended sprint |
| Kubernetes secrets issues | Low | High | Early remediation |

---

## Success Metrics

### Technical Metrics
| Metric | Target | Measurement |
|--------|--------|------------|
| Voice pipeline latency | <1,500ms | 95th percentile |
| API availability | 99.5% | 30-day SLA |
| Test coverage | 70%+ | pytest --cov |
| Build success rate | 100% | CI pipeline |

### Business Metrics
| Metric | Target | Measurement |
|--------|--------|------------|
| Beta signups | 100 | Week 12 |
| Active developers | 50 | Week 16 |
| First paying customers | 10 | Week 16 |
| NPS score | 40+ | Survey |

---

Last Updated: April 2026
# Roadmap: Voiquyr Platform

## Milestones

- ✅ **v1.0 MVP** — Phases 1-10 (shipped 2026-04-23)
- 📋 **v1.1 Optimization** — Phases 11-15 (active)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-10) — SHIPPED 2026-04-23</summary>

- [x] Phase 1: Foundation (4/4 plans) — completed 2026-03-17
- [x] Phase 2: STT (4/4 plans) — completed 2026-04-22
- [x] Phase 3: LLM (3/3 plans) — completed 2026-04-22
- [x] Phase 4: TTS (3/3 plans) — completed 2026-04-22
- [x] Phase 5: Telephony (3/3 plans) — completed 2026-04-22
- [x] Phase 6: Billing & Integrations (3/3 plans) — completed 2026-04-23
- [x] Phase 7: Frontend & Command Center (3/3 plans) — completed 2026-04-23
- [x] Phase 8: Unit Tests (3/3 plans) — completed 2026-04-19
- [x] Phase 9: Integration & E2E Tests (3/3 plans) — completed 2026-04-23
- [x] Phase 10: Production Readiness (4/4 plans) — completed 2026-04-23

</details>

### 📋 v1.1 Optimization (Active)

**Goal:** Performance optimization, self-hosted model options, enhanced compliance features

**Phase 11: Performance Caching**

- Goal: Response caching, query memoization, connection pooling
- Requirements: PERF-01, PERF-02, PERF-03
- Success criteria: 50% cache hit rate, <5ms cache lookup

**[x] Phase 12: Self-Hosted Models** — completed 2026-05-10

- Goal: vLLM deployment, OpenAI-compatible API, model fallback
- Requirements: SELF-01, SELF-02, SELF-03, SELF-04
- Success criteria: vLLM serving, fallback chain works ✓

**[x] Phase 13: Enhanced Monitoring** — completed 2026-05-28

- Goal: Prometheus metrics, Grafana dashboards, alerting
- Requirements: MON-01, MON-02, MON-03, MON-04
- Success criteria: All components instrumented, alerts trigger

**Phase 14: Multi-Region Deployment**

- Goal: Frankfurt + UAE edge manifests, DNS routing
- Requirements: MULTI-01, MULTI-02, MULTI-03, MULTI-04
- Success criteria: Both regions deployable, routing configured

**Phase 15: v1.1 Polish & Verification**

- Goal: Integration testing, full pipeline verification
- Requirements: All v1.1 requirements
- Success criteria: E2E tests pass, all features functional

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | Complete | 2026-03-17 |
| 2. STT | v1.0 | 4/4 | Complete | 2026-04-22 |
| 3. LLM | v1.0 | 3/3 | Complete | 2026-04-22 |
| 4. TTS | v1.0 | 3/3 | Complete | 2026-04-22 |
| 5. Telephony | v1.0 | 3/3 | Complete | 2026-04-22 |
| 6. Billing & Integrations | v1.0 | 3/3 | Complete | 2026-04-23 |
| 7. Frontend & Command Center | v1.0 | 3/3 | Complete | 2026-04-23 |
| 8. Unit Tests | v1.0 | 3/3 | Complete | 2026-04-19 |
| 9. Integration & E2E Tests | v1.0 | 3/3 | Complete | 2026-04-23 |
| 10. Production Readiness | v1.0 | 4/4 | Complete | 2026-04-23 |
| 11. Performance Caching | v1.1 | 3/3 | Complete | 2026-04-25 |
| 12. Self-Hosted Models | v1.1 | 4/4 | Complete | 2026-05-10 |
| 13. Enhanced Monitoring | v1.1 | 4/4 | Complete    | 2026-05-28 |
| 14. Multi-Region Deployment | v1.1 | 0/4 | Pending | — |
| 15. v1.1 Polish & Verification | v1.1 | 0/3 | Pending | — |

---

*Roadmap created: 2026-03-16*
*Milestone v1.0 completed: 2026-04-23*
*Milestone v1.1 started: 2026-04-25*
*Granularity: fine (15 phases total)*
*Coverage: 15+15 v1.1 requirements mapped*

---

## Backlog

### v2 Requirements

**Advanced Features:**

- [ ] **ADV-01**: Voxtral self-hosted STT (when model released)
- [ ] **ADV-02**: Self-hosted LLM via vLLM for cost control
- [ ] **ADV-03**: Multi-region EU deployment (beyond single-cluster)
- [ ] **ADV-04**: Visual/video modality pipeline

### Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile apps | Web + telephony first; mobile deferred |
| Non-EU data residency | Compliance requirement, by design |
| Real-time video | Voice pipeline only in v1 |
| Self-hosted LLM at launch | Mistral API sufficient; self-hosted = v2 |
| OAuth login for end-users | JWT/password sufficient for v1 |

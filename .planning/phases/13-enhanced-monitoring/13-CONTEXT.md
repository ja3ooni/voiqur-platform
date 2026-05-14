# Phase 13: Enhanced Monitoring - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Instrument the Voiquyr platform pipeline with Prometheus metrics, build two
pre-provisioned Grafana dashboards, define Prometheus alert rules, and wire
Alertmanager to a Slack webhook. All monitoring infrastructure delivered as
Helm chart additions — no manual post-deploy steps.

</domain>

<decisions>
## Implementation Decisions

### Metrics Scope
- **D-01:** Instrument **pipeline only** — STT, LLM, TTS stages, end-to-end call, flash mode, and fallback chain. No Redis/Postgres infra metrics in this phase.
- **D-02:** Per-stage Histograms: `voiquyr_stt_latency_ms`, `voiquyr_llm_latency_ms`, `voiquyr_tts_latency_ms`. End-to-end: `voiquyr_call_latency_ms`. Flash mode: `voiquyr_flash_mode_hit_rate` (Gauge or Counter).
- **D-03:** Fallback chain circuit breaker metrics: `voiquyr_fallback_activations_total` (Counter) + `voiquyr_circuit_breaker_state` (Gauge: 0=CLOSED, 1=OPEN, 2=HALF_OPEN).
- **D-04:** No per-tenant label cardinality — keep labels simple (stage, status). High-cardinality labels (tenant_id, call_id) are NOT added to Prometheus metrics.

### Grafana Dashboards
- **D-05:** Two dashboards, pre-provisioned via Helm ConfigMaps with `grafana.sidecar.dashboards.enabled=true`. Auto-available on every deploy, no manual import.
- **D-06:** Dashboard 1 — **Pipeline SLA**: call latency p50/p95/p99, per-stage latency breakdown, flash mode hit rate, error rates.
- **D-07:** Dashboard 2 — **Fallback & Health**: circuit breaker state, vLLM vs Mistral API usage ratio, per-stage error rates over time.

### Alerting
- **D-08:** Alertmanager routes to **Slack webhook**. Webhook URL configured via Helm values / sealed secret (never hardcoded).
- **D-09:** Four alert rules:
  1. `VoiquyrLatencyWarning` — p95 call latency >500ms for 2min → WARNING (SLA breach)
  2. `VoiquyrLatencyCritical` — p95 call latency >800ms for 1min → CRITICAL
  3. `VoiquyrCircuitBreakerOpen` — circuit breaker OPEN state → CRITICAL
  4. `VoiquyrHighErrorRate` — error rate >5% over 5min → WARNING

### Metrics Endpoint & Scrape
- **D-10:** Use `prometheus-fastapi-instrumentator` for automatic route instrumentation + `prometheus_client` for custom metrics. Expose `GET /metrics` on the existing FastAPI app (same port).
- **D-11:** `/metrics` endpoint is **not** exposed via Ingress — cluster-internal only, no app-level auth required.
- **D-12:** Prometheus discovers the app via **ServiceMonitor CRD** (kube-prometheus-stack). Add ServiceMonitor manifest to Helm chart.

### Claude's Discretion
- Histogram bucket boundaries for latency metrics (planner should use standard `[10, 25, 50, 100, 250, 500, 1000, 2500]` ms buckets)
- Alertmanager grouping and repeat intervals
- Dashboard time range defaults and auto-refresh interval

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Platform Architecture
- `.planning/ROADMAP.md` — Phase 13 goals (MON-01 through MON-04) and success criteria
- `.planning/PROJECT.md` — Named metric constants (`voiquyr_call_latency_ms`, `voiquyr_flash_mode_hit_rate`) and SLA targets (p95 <500ms per region)
- `CLAUDE.md` — Architecture overview, named metrics list, k8s Helm chart location

### Existing Code to Instrument
- `kiro/voiquyr/src/core/quality_monitor.py` — Existing internal health/alert model; metric recording hooks should call into this OR supplement it with Prometheus counters
- `kiro/voiquyr/src/core/flash_mode.py` — Flash mode activation site; instrument `voiquyr_flash_mode_hit_rate` here
- `kiro/voiquyr/src/agents/fallback_chain.py` — Circuit breaker state transitions; instrument `voiquyr_circuit_breaker_state` and `voiquyr_fallback_activations_total` here
- `kiro/voiquyr/src/agents/stt_agent.py` — Instrument `voiquyr_stt_latency_ms`
- `kiro/voiquyr/src/agents/llm_agent.py` — Instrument `voiquyr_llm_latency_ms`
- `kiro/voiquyr/src/agents/tts_agent.py` — Instrument `voiquyr_tts_latency_ms`
- `kiro/voiquyr/src/api/app.py` — Register `prometheus-fastapi-instrumentator` middleware here; expose `/metrics` route

### Infrastructure
- `kiro/voiquyr/k8s/helm/euvoice-platform/` — Helm chart root; add ServiceMonitor, Alertmanager config, and Grafana dashboard ConfigMaps here
- `.planning/phases/12-self-hosted-models/12-CONTEXT.md` — vLLM deployment context; fallback chain is the circuit breaker in `fallback_chain.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/quality_monitor.py`: Has `Alert`, `HealthStatus`, `MetricType` — planner can decide whether to keep it as-is and layer Prometheus on top, or consolidate. Either is acceptable.
- `src/api/routers/health.py`: Existing health endpoint — `/metrics` should be a separate route, not merged here.
- `src/agents/fallback_chain.py` (Phase 12): `FallbackOrchestrator` with `CircuitBreakerState` enum (CLOSED/OPEN/HALF_OPEN) — instrument state transitions directly.

### Established Patterns
- FastAPI app factory in `src/api/app.py` (`create_app()`) — register instrumentator and `/metrics` route in `create_app()`, consistent with how other middleware and routers are registered.
- Helm chart structure at `k8s/helm/euvoice-platform/` — add monitoring templates alongside existing manifests.

### Integration Points
- `create_app()` in `src/api/app.py` — instrumentator registration point
- `FallbackOrchestrator._transition_state()` in `src/agents/fallback_chain.py` — circuit breaker metric update point
- `k8s/helm/euvoice-platform/templates/` — ServiceMonitor + Alertmanager + Grafana ConfigMap destination

</code_context>

<specifics>
## Specific Ideas

- Metric names from CLAUDE.md are canonical: `voiquyr_call_latency_ms`, `voiquyr_flash_mode_hit_rate` — use exactly these names.
- SLA threshold of p95 <500ms is the hard line for `VoiquyrLatencyWarning` alert.
- Circuit breaker Gauge encoding: 0=CLOSED (healthy), 1=OPEN (failing), 2=HALF_OPEN (recovering) — matches `CircuitBreakerState` enum order in `fallback_chain.py`.

</specifics>

<deferred>
## Deferred Ideas

- Redis/Postgres infra metrics (connection pool stats, query times) — out of scope for this phase, consider Phase 15 or v2
- Per-tenant metrics / multi-tenant dashboards — high-cardinality; deferred to v2
- Mobile/PagerDuty alerting integration — Slack is sufficient for now

</deferred>

---

*Phase: 13-Enhanced Monitoring*
*Context gathered: 2026-05-14*

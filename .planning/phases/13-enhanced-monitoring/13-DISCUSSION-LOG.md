# Phase 13: Enhanced Monitoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 13-Enhanced Monitoring
**Areas discussed:** Metrics scope & naming, Grafana dashboards, Alerting targets & thresholds, Metrics endpoint & scrape config

---

## Metrics Scope & Naming

### Component coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline only | STT, LLM, TTS, fallback chain — named metrics from CLAUDE.md | ✓ |
| Pipeline + infra | Add Redis pool stats, Postgres query times, vLLM GPU memory | |
| Everything | Full coverage including per-agent task queues, knowledge base, compliance layer | |

**User's choice:** Pipeline only
**Notes:** Canonical metric names from CLAUDE.md are the anchor; scope is the pipeline components only.

### Per-stage breakdown

| Option | Description | Selected |
|--------|-------------|----------|
| Per-stage Histograms | voiquyr_stt_latency_ms, voiquyr_llm_latency_ms, voiquyr_tts_latency_ms | ✓ |
| End-to-end only | Only voiquyr_call_latency_ms (e2e) and voiquyr_flash_mode_hit_rate | |
| Per-stage + error counters | Per-stage Histograms + per-stage error Counters | |

**User's choice:** Per-stage Histograms (recommended)

### Fallback chain metrics

| Option | Description | Selected |
|--------|-------------|----------|
| Circuit breaker state + hit rate | voiquyr_fallback_activations_total + voiquyr_circuit_breaker_state Gauge | ✓ |
| No dedicated metric | LLM latency Histogram will indirectly show fallback degradation | |

**User's choice:** Circuit breaker state + hit rate (recommended)

---

## Grafana Dashboards

### Delivery mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-provisioned via Helm ConfigMaps | grafana.sidecar.dashboards.enabled=true, auto-available on deploy | ✓ |
| JSON files committed to repo | Operators import manually | |
| You decide | Leave to planner | |

**User's choice:** Pre-provisioned Helm ConfigMaps (recommended)

### Number of dashboards

| Option | Description | Selected |
|--------|-------------|----------|
| Two dashboards | Pipeline SLA + Fallback & Health | ✓ |
| One combined dashboard | All metrics in a single dashboard | |
| Three dashboards | Add Operations dashboard for Redis/Postgres | |

**User's choice:** Two dashboards (recommended)

---

## Alerting Targets & Thresholds

### Alert destination

| Option | Description | Selected |
|--------|-------------|----------|
| Slack webhook | Alertmanager → Slack incoming webhook | ✓ |
| Email only | Alertmanager SMTP | |
| Slack + email | Critical to Slack, all to email | |

**User's choice:** Slack webhook (recommended)

### Alert rules

| Option | Description | Selected |
|--------|-------------|----------|
| SLA + circuit breaker (4 rules) | Latency WARNING + CRITICAL, circuit breaker OPEN, error rate >5% | ✓ |
| Latency only | Only p95 >500ms SLA breach | |
| You decide | Leave thresholds to planner | |

**User's choice:** 4-rule set (recommended)
**Notes:** p95 <500ms comes directly from CLAUDE.md SLA targets; 800ms is the CRITICAL escalation threshold.

---

## Metrics Endpoint & Scrape Config

### Exposure mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| prometheus_client /metrics on FastAPI app | prometheus-fastapi-instrumentator + custom metrics on same port | ✓ |
| Separate metrics port | Run prometheus_client on a dedicated port (e.g. 9090) | |
| Pushgateway | Push model — overkill for long-running service | |

**User's choice:** /metrics on existing FastAPI app (recommended)

### Kubernetes discovery

| Option | Description | Selected |
|--------|-------------|----------|
| ServiceMonitor CRD | Works with kube-prometheus-stack operator | ✓ |
| Static scrape config | Manual prometheus.yml job config | |
| You decide | Leave to planner | |

**User's choice:** ServiceMonitor CRD (recommended)

### Authentication

| Option | Description | Selected |
|--------|-------------|----------|
| No auth — network-level restriction | /metrics not exposed via Ingress; cluster-internal only | ✓ |
| Bearer token auth | Static token checked on /metrics | |

**User's choice:** No auth — network-level restriction (recommended)

---

## Claude's Discretion

- Histogram bucket boundaries (standard `[10, 25, 50, 100, 250, 500, 1000, 2500]` ms recommended)
- Alertmanager grouping keys, repeat intervals, and inhibition rules
- Dashboard time range defaults and auto-refresh interval

## Deferred Ideas

- Redis/Postgres infra metrics — out of scope, consider Phase 15 or v2
- Per-tenant metrics / multi-tenant Grafana dashboards — high-cardinality, deferred to v2
- PagerDuty integration — Slack is sufficient for v1.1

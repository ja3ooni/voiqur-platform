---
phase: 12
plan: 12-03
plan_name: "Model Fallback Chain"
status: complete
requirements: [SELF-04]
completed: "2026-05-10"
---

# Plan 12-03 Summary: Model Fallback Chain

## What Was Built

Circuit breaker fallback orchestrator: Mistral API → self-hosted vLLM → error.

## Files Created

- `kiro/voiquyr/src/agents/fallback_chain.py` — `FallbackOrchestrator`:
  - Three-state circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED
  - Provider order: `[MISTRAL_API, VLLM]` by default
  - Exponential moving average latency tracking per provider
  - `health_report` property for monitoring
  - `get_fallback_orchestrator()` / `set_fallback_orchestrator()` singletons

## WIP Bugs Fixed

Two bugs in the original WIP file were corrected:
1. `Model-health` (hyphen = invalid Python identifier) → renamed to `ModelHealth`
2. `time.monostics()` (typo) → corrected to `time.monotonic()`

## Tests

25 tests in `tests/test_fallback_chain.py` — all passing.
- ModelHealth/FallbackConfig defaults and custom values
- Circuit state transitions: closed, open, half-open recovery
- _can_attempt blocking during OPEN, allowing after timeout
- complete(): primary success, fallback on failure/timeout, all-fail raises FallbackError
- Success/failure count tracking, health report structure
- Global singleton set/get

## Key Decisions

- Circuit opens on `failure_threshold` failures from *any* provider (not per-provider)
- HALF_OPEN allows one probe — success closes, failure re-opens
- `circuit_open_timeout` defaults to 300s (5 min cool-down)
- `timeout_seconds` (30s default) enforced via `asyncio.wait_for`

## Self-Check: PASSED

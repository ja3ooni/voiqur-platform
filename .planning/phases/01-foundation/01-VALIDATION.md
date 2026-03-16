---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (NOT YET INSTALLED — Wave 0 installs) |
| **Config file** | `kiro/voiquyr/pytest.ini` — Wave 0 creates |
| **Quick run command** | `pytest tests/test_foundation.py -x -v` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds (integration tests need live Redis + PG) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_foundation.py -x -v`
- **After every plan wave:** Run `pytest -v` (full suite)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | FOUND-01 | unit | `pytest tests/test_foundation.py::test_env_loading -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | FOUND-02 | smoke | `pytest tests/test_foundation.py::test_env_example_exists -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | FOUND-03 | integration | `pytest tests/test_foundation.py::test_redis_connection -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | FOUND-04 | integration | `pytest tests/test_foundation.py::test_postgres_connection -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | FOUND-05 | integration | `pytest tests/test_foundation.py::test_schema_tables -x` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 1 | FOUND-09 | integration | `pytest tests/test_foundation.py::test_health_real_connections -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | FOUND-06 | unit | `pytest tests/test_foundation.py::test_verify_token_db_lookup -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | FOUND-07 | integration | `pytest tests/test_foundation.py::test_register_endpoint -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | FOUND-08 | integration | `pytest tests/test_foundation.py::test_login_endpoint -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `kiro/voiquyr/tests/conftest.py` — pytest fixtures: test DB URL, asyncpg pool, httpx AsyncClient
- [ ] `kiro/voiquyr/tests/test_foundation.py` — stubs for FOUND-01 through FOUND-09
- [ ] `kiro/voiquyr/pytest.ini` — configure `asyncio_mode = auto` for pytest-asyncio
- [ ] `pip install pytest pytest-asyncio httpx` in active venv — none currently installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Server starts without errors | FOUND-01 | Startup log inspection required | Run `python -m uvicorn src.api.main:app --reload` in kiro/voiquyr/, verify no ImportError or config error in logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

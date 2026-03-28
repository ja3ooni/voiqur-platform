---
phase: 3
slug: llm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | kiro/voiquyr/pytest.ini or pyproject.toml |
| **Quick run command** | `pytest tests/test_llm_agent.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_llm_agent.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | LLM-01 | unit | `pytest tests/test_llm_agent.py::test_real_mistral_chat -v` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | LLM-02 | unit | `pytest tests/test_llm_agent.py::test_mock_removed -v` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | LLM-03 | unit | `pytest tests/test_llm_agent.py::test_history_wiring -v` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | LLM-04 | unit | `pytest tests/test_llm_agent.py::test_function_calling_format -v` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | LLM-05 | integration | `pytest tests/test_llm_integration.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_llm_agent.py` — stubs for LLM-01, LLM-02, LLM-03, LLM-04
- [ ] `tests/test_llm_integration.py` — multi-turn tool call integration stubs for LLM-05
- [ ] `tests/conftest.py` — shared fixtures (mock Mistral client, sample conversation context)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mistral API key valid + live call succeeds | LLM-01 | Requires live API credentials | Set MISTRAL_API_KEY, run agent, verify response not from mock |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

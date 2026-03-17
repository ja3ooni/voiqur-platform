---
phase: 2
slug: stt
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio_mode=auto) |
| **Config file** | `kiro/voiquyr/pytest.ini` |
| **Quick run command** | `cd kiro/voiquyr && pytest tests/test_stt_agent.py -v` |
| **Full suite command** | `cd kiro/voiquyr && pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds (unit/mock); ~30s with live API keys |

---

## Sampling Rate

- **After every task commit:** Run `cd kiro/voiquyr && pytest tests/test_stt_agent.py -v`
- **After every plan wave:** Run `cd kiro/voiquyr && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green with `DEEPGRAM_API_KEY` set
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-00-01 | 00 | 0 | STT-01–05 | scaffold | `pytest tests/test_stt_agent.py -v` (xfail stubs) | ❌ Wave 0 | ⬜ pending |
| 2-01-01 | 01 | 1 | STT-01 | integration | `pytest tests/test_stt_agent.py::test_transcribe_returns_real_string -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-02 | 01 | 1 | STT-02 | integration | `pytest tests/test_stt_agent.py::test_voxtral_fallback -x` | ❌ Wave 0 | ⬜ pending |
| 2-02-01 | 02 | 1 | STT-03 | unit | `pytest tests/test_stt_agent.py::test_language_detection_returns_code -x` | ❌ Wave 0 | ⬜ pending |
| 2-03-01 | 03 | 2 | STT-04 | unit | `pytest tests/test_stt_agent.py::test_pipeline_stt_integration -x` | ❌ Wave 0 | ⬜ pending |
| 2-03-02 | 03 | 2 | STT-05 | integration | `pytest tests/test_stt_agent.py -v` (full suite) | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `kiro/voiquyr/tests/test_stt_agent.py` — rewritten from asyncio script to pytest async tests with `xfail` stubs for STT-01 through STT-05
- [ ] `kiro/voiquyr/requirements.txt` — add `deepgram-sdk>=3.1.0,<4.0`, `mistralai>=2.0.0`, `langdetect>=1.0.9`

*Existing pytest infrastructure from Phase 1 (pytest.ini, conftest.py, asyncio_mode=auto) covers all other needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Deepgram API call returns non-empty transcript | STT-01 | Requires live `DEEPGRAM_API_KEY` and network access | Set `DEEPGRAM_API_KEY` in `.env`, run `pytest tests/test_stt_agent.py::test_transcribe_returns_real_string -v -s` with a real WAV file |
| Voxtral fallback produces transcript | STT-02 | Requires `MISTRAL_API_KEY` and network access | Unset `DEEPGRAM_API_KEY`, set `MISTRAL_API_KEY`, run `pytest tests/test_stt_agent.py::test_voxtral_fallback -v -s` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

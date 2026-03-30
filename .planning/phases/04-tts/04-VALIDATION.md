---
phase: 4
slug: tts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | kiro/voiquyr/pytest.ini or pyproject.toml |
| **Quick run command** | `pytest tests/test_tts_agent.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_tts_agent.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | TTS-01 | unit | `pytest tests/test_tts_agent.py --co -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | TTS-01 | unit | `pytest tests/test_tts_agent.py::test_elevenlabs_convert -v` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | TTS-02 | unit | `pytest tests/test_tts_agent.py::test_xtts_import -v` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | TTS-03 | unit | `pytest tests/test_tts_agent.py::test_voice_cloning -v` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | TTS-04 | unit | `pytest tests/test_tts_streaming.py -v` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | TTS-05 | integration | `pytest tests/test_pipeline_e2e.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tts_agent.py` — stubs for TTS-01, TTS-02, TTS-03 (xfail for model-download tests)
- [ ] `tests/test_tts_streaming.py` — stubs for TTS-04 (streaming chunks)
- [ ] `tests/test_pipeline_e2e.py` — stub for TTS-05 (audio in → STT → LLM → TTS → audio out)
- [ ] Fix syntax error in `kiro/voiquyr/src/agents/tts_streaming.py` line 28-29 (`class \nAudioFormat`)
- [ ] `tests/conftest.py` — shared fixtures (mock ElevenLabs client, sample WAV bytes)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ElevenLabs live API call returns real audio | TTS-01 | Requires live API key + network | Set ELEVENLABS_API_KEY, call synthesize("Hello world"), verify bytes > 1000 |
| XTTS-v2 model download succeeds | TTS-02 | ~2 GB download, not suitable for CI | Run `tts --model_name tts_models/multilingual/multi-dataset/xtts_v2` on target machine |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

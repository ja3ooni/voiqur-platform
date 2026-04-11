---
phase: 5
slug: telephony
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `kiro/voiquyr/pytest.ini` or `kiro/voiquyr/pyproject.toml` |
| **Quick run command** | `cd kiro/voiquyr && pytest tests/test_twilio_integration.py -v` |
| **Full suite command** | `cd kiro/voiquyr && pytest tests/test_telephony_abstraction.py tests/test_twilio_integration.py -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd kiro/voiquyr && pytest tests/test_twilio_integration.py -v`
- **After every plan wave:** Run `cd kiro/voiquyr && pytest tests/test_telephony_abstraction.py tests/test_twilio_integration.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | TEL-01 | unit | `pytest tests/test_twilio_integration.py::test_make_call_posts_to_twilio -v` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | TEL-02 | unit | `pytest tests/test_twilio_integration.py::test_send_sms_posts_to_twilio -v` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | TEL-03 | unit | `pytest tests/test_twilio_integration.py::test_authenticate_basic_auth -v` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | TEL-04 | unit | `pytest tests/test_twilio_integration.py::test_media_stream_audio_bridge -v` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | TEL-05 | unit | `pytest tests/test_twilio_integration.py::test_sip_trunk_registry -v` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | TEL-06 | integration | `cd kiro/voiquyr && pytest tests/test_telephony_abstraction.py -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `kiro/voiquyr/tests/test_twilio_integration.py` — xfail stubs for TEL-01, TEL-02, TEL-03, TEL-04, TEL-05
- [ ] `kiro/voiquyr/requirements.txt` — add `audioop-lts` (audioop removed in Python 3.13+) and `aioresponses==0.7.8`

*Existing infrastructure covers the abstraction layer (test_telephony_abstraction.py already passes).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Twilio call completes with audio | TEL-04 | Requires live Twilio account + phone | Set real TWILIO_ACCOUNT_SID/TOKEN, call a Twilio test number (+15005550006), verify STT receives audio |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

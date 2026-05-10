---
phase: 12
plan: 12-04
plan_name: "Voxtral STT Integration (Deferred)"
status: complete
requirements: [SELF-03]
completed: "2026-05-10"
---

# Plan 12-04 Summary: Voxtral STT Integration Stub

## What Was Built

Deferred integration stub for Voxtral STT (Mistral's upcoming speech-to-text model).

## Files Created

- `kiro/voiquyr/src/stt/voxtral.py` — `VoxtralSTT` stub:
  - `transcribe(audio, language, prompt)` — raises `VoxtralNotAvailable` until activated
  - `health_check()` — returns `False` until Voxtral is available
  - `VOXTRAL_AVAILABLE` flag — set to `True` when model is released
  - `is_voxtral_available()` helper
  - Same interface as existing STT providers — drop-in replacement

## Status

Deferred: Mistral has not yet released Voxtral as of 2026-05-10.
Monitor: https://mistral.ai for release announcements.
Activation path: Set `VOXTRAL_AVAILABLE = True` and implement the
  `POST {vllm_url}/v1/audio/transcriptions` call.

## Tests

13 tests in `tests/test_voxtral_stub.py` — all passing.
- Constants (VOXTRAL_AVAILABLE=False, model ID)
- Init defaults, trailing slash stripping
- Transcribe raises VoxtralNotAvailable, health_check returns False
- Interface contract: transcribe/health_check present, correct parameters

## Self-Check: PASSED

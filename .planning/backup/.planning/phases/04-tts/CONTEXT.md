# Phase 4: TTS - Context

**Goal:** Implement real Text-to-Speech synthesis using ElevenLabs (primary cloud) and XTTS-v2 (self-hosted fallback/cloning) to replace mocks in the voice processing pipeline.

## Requirements

- **TTS-01:** `XTTSv2ModelManager.synthesize()` calls real ElevenLabs SDK (replaces sine-wave mock)
- **TTS-02:** XTTS-v2 self-hosted path available via the `TTS` (Coqui) library
- **TTS-03:** `VoiceCloningEngine.clone_voice()` uses real `get_conditioning_latents()`
- **TTS-04:** Real audio chunks wired to WebSocket streaming via ElevenLabs `.stream()`
- **TTS-05:** End-to-end pipeline test passes: audio in → STT → LLM → TTS → audio out

## Established Decisions

- **SDK:** ElevenLabs SDK (v2+) is the primary synthesis path
- **Self-hosted:** XTTS-v2 via Coqui `TTS` library (v0.22.0) is the secondary path
- **Import Guard:** Heavy libraries (`torch`, `torchaudio`, `TTS`) must be guarded with try/except in `tts_agent.py` to allow test collection in lean environments
- **Model Loading:** `XTTSv2ModelManager` name is fixed; ElevenLabs client is added within this class
- **Audio Format:** ElevenLabs output must be `pcm_22050` to match existing 22050Hz float32 pipeline

## Technical Gaps

- **ElevenLabs SDK:** Not yet installed in venv
- **XTTS-v2 Library:** Not yet installed in venv
- **VoiceCloningEngine:** Class does not exist yet; must be created in `tts_agent.py`
- **Processing Pipeline:** `_process_tts()` is a mock returning `b"MOCK_AUDIO_DATA_..."`

## Plan Structure

1. **04-00:** Wave 0 setup (test stubs + import guards)
2. **04-01:** ElevenLabs integration (cloud synthesis)
3. **04-02:** XTTS-v2 & VoiceCloningEngine (self-hosted/cloning)
4. **04-03:** Pipeline wiring & E2E verification

# Research: Phase 4 - TTS

**Phase:** 04 - TTS
**Researcher:** gsd-phase-researcher
**Date:** 2026-04-19

## Phase Goal

**From ROADMAP.md:**
- "LLM responses are synthesized to real audio via ElevenLabs (with XTTS-v2 self-hosted path) and streamed to WebSocket clients"

## Key Requirements

| ID | Requirement | Current State |
|----|--------------|---------------|
| TTS-01 | `XTTSv2ModelManager.synthesize()` calls ElevenLabs SDK | Mock sine-wave generation |
| TTS-02 | XTTS-v2 via `TTS` library available as self-hosted path | Not implemented (mock only) |
| TTS-03 | `VoiceCloningEngine.clone_voice()` uses real speaker embedding | Stub implementation |
| TTS-04 | Streaming chunks wired into `tts_streaming.py` | Sine wave streaming |
| TTS-05 | E2E pipeline test: audio → STT → LLM → TTS → audio out | Mock E2E |

## Current Implementation Analysis

### File: `kiro/voiquyr/src/agents/tts_agent.py`

**XTTSv2ModelManager (line 432):**
- `synthesize()` method generates numpy sine waves (lines 604-648)
- Sample rate: 22050 Hz
- No actual API calls to ElevenLabs or XTTS library
- Language support is mocked

**VoiceCloningEngine:**
- Not found in codebase - needs to be created

**Streaming:**
- `tts_streaming.py` exists but uses the mock sine-wave generator

### Missing Components

1. **ElevenLabs SDK integration** - Package: `elevenlabs`
2. **XTTS-v2 local inference** - Package: `TTS` (Coqui TTS)
3. **Voice cloning with conditioning latents** - Not in requirements.txt

## Technical Approaches

### Approach A: ElevenLabs Cloud (Primary)

**Pros:**
- High quality output
- Managed infrastructure
- Built-in voice cloning API
- Low latency

**Cons:**
- Cost per character
- External dependency
- Data leaves EU concern

**Implementation:**
```python
# elevenlabs SDK
from elevenlabs import generate, play, save
audio = generate(text="Hello", voice="Rachel", model="eleven_multilingual_v2")
```

### Approach B: XTTS-v2 Self-Hosted

**Pros:**
- No per-character cost
- Full control
- Works offline

**Cons:**
- GPU required
- More complex setup
- Potentially lower quality than ElevenLabs

**Implementation:**
```python
# TTS library (Coqui)
from TTS.api import TTS
tts = TTS(model_name="tts_models/multilingual/mxtts/multilingual_fastscan")
tts.tts(text, speaker_wav="reference.wav", language="en")
```

### Approach C: Hybrid

**Pros:**
- Best of both worlds
- Fallback capability
- Cost optimization

**Cons:**
- Most complex
- More integration code

## Recommendation

**Approach A (ElevenLabs)** for Phase 4 due to:
1. Production-ready quality
2. Clear API contract
3. Built-in voice cloning
4. Multilingual support (critical for MENA region)

**XTTS-v2** can be added in a future phase for cost optimization.

## Validation Architecture

**Tests needed:**
1. Unit test: `synthesize()` returns real audio bytes (not sine wave)
2. Unit test: `clone_voice()` returns voice embedding
3. Integration test: Full pipeline (audio in → audio out)
4. Streaming test: Chunk delivery to WebSocket

## Open Questions

1. **ElevenLabs API key** - Will be provided in environment
2. **Voice selection** - Default voices to use per language
3. **Streaming vs batch** - Both need implementation
4. **Fallback behavior** - If ElevenLabs unavailable

---

*Research complete: 2026-04-19*
# Phase 2: STT - Research

**Researched:** 2026-03-17
**Domain:** Speech-to-Text pipeline — Deepgram SDK, Mistral Voxtral API, langdetect, pytest async patterns
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STT-01 | `VoxtralModelManager.transcribe()` calls Deepgram SDK (asynclive streaming) | Deepgram SDK v3+ `AsyncDeepgramClient` + `PrerecordedOptions` confirmed; live streaming path via `asynclive.v("1").transcribe()` |
| STT-02 | Fallback to Mistral Voxtral SDK when Deepgram unavailable | `mistralai` SDK v2+ `client.audio.transcriptions.complete()` with `"voxtral-mini-latest"` model confirmed |
| STT-03 | `LanguageDetector.detect_language()` uses `langdetect` (not random) | `langdetect 1.0.9` `detect()` returns ISO 639-1 codes; `DetectorFactory.seed=0` for determinism |
| STT-04 | Real transcription results wired into `processing_pipeline.py` | `_process_stt()` in `processing_pipeline.py` must call `VoxtralModelManager.transcribe()` instead of inline mock |
| STT-05 | `pytest tests/test_stt_agent.py` passes with `DEEPGRAM_API_KEY` set | Existing `test_stt_agent.py` is a script (not pytest); must be rewritten as proper pytest async tests |
</phase_requirements>

---

## Summary

Phase 2 replaces every mock/stub in the STT layer with real API calls. Three distinct components need work: (1) `VoxtralModelManager.transcribe()` in `stt_agent.py` must call Deepgram's async pre-recorded SDK instead of returning `"Transcribed audio chunk N"`; (2) `LanguageDetector.detect_language()` in `stt_agent.py` must call `langdetect.detect()` on transcribed text instead of `np.random.choice()`; (3) `_process_stt()` in `processing_pipeline.py` must delegate to the real STT agent instead of its inline mock.

The fallback chain is Deepgram (primary) → Mistral Voxtral API (fallback when `DEEPGRAM_API_KEY` absent). `langdetect` 1.0.9 operates on text — meaning language detection should run post-transcription, not on audio. This is a key architectural insight: the existing `LanguageDetector` takes an `AudioChunk`, but language detection from text (via `langdetect`) is simpler, more accurate, and avoids heavy audio-feature ML models. The `detect_language()` method on `LanguageDetector` should be changed to accept text input.

The existing `tests/test_stt_agent.py` is an asyncio script (`asyncio.run(main())`), not a pytest file. It must be replaced with proper `async def test_*` functions that pytest can discover. The `pytest.ini` has `asyncio_mode = auto`, so no decorators are needed.

**Primary recommendation:** Use `deepgram-sdk` 3.x `AsyncDeepgramClient` + `PrerecordedOptions` for `VoxtralModelManager.transcribe()`, with `DEEPGRAM_API_KEY` env-guard controlling fallback to `mistralai` SDK `client.audio.transcriptions.complete()`. Replace `LanguageDetector.detect_language(AudioChunk)` with `detect_language(text: str)` calling `langdetect.detect()`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `deepgram-sdk` | 3.x (latest PyPI: 3.3.0) | Async STT via Deepgram API | Primary STT provider per architecture decision; command-center already pins `3.1.0` |
| `mistralai` | 2.0.4 | Voxtral STT fallback via `client.audio.transcriptions.complete()` | EU-based provider per project decision; already required for LLM phase |
| `langdetect` | 1.0.9 | Text language detection returning ISO 639-1 codes | Lightweight, well-known Python port of Google langdetect; no GPU needed |
| `python-dotenv` | already installed | Load `DEEPGRAM_API_KEY` in tests | Already wired in Phase 1 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | already installed (asyncio_mode=auto) | Async test support | All STT tests are async |
| `numpy` | already installed | Test audio generation (sine wave) | Creating WAV bytes for test fixtures |
| `scipy.io.wavfile` | already installed (scipy>=1.10.0) | WAV encoding for Deepgram API | Converting numpy float32 arrays to WAV bytes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langdetect` | `lingua-language-detector` | lingua is more accurate but heavier; langdetect is the requirement per STT-03 |
| `langdetect` on text | `langdetect` on audio features | Audio-based detection requires ML models; text-based is simpler, works post-transcription |
| `deepgram-sdk` pre-recorded | Deepgram live streaming WebSocket | Pre-recorded is simpler for WAV file input; live streaming needed for real-time phone calls (future phase) |

**Installation (additions to `requirements.txt`):**
```bash
# In kiro/voiquyr/
pip install deepgram-sdk mistralai langdetect
```

**Version verification:**
- `deepgram-sdk`: PyPI latest is **3.x** (command-center pins `3.1.0`, use `>=3.1.0,<4.0`)
- `mistralai`: PyPI latest is **2.0.4**
- `langdetect`: PyPI latest is **1.0.9** (stable since 2021, no breaking changes)

**Note on deepgram-sdk major version:** PyPI reports `6.0.1` as absolute latest, but the command-center uses `3.1.0`. The v3→v4+ SDK introduced breaking API changes. The code examples in this document use the **v3.x API** (`asyncprerecorded.v("1").transcribe_url()`), which matches the command-center pinning. Use `deepgram-sdk>=3.1.0,<4.0` to stay on the v3 API surface.

---

## Architecture Patterns

### What Needs to Change (Gap Analysis)

| File | Current State | Target State |
|------|--------------|--------------|
| `src/agents/stt_agent.py` — `VoxtralModelManager.transcribe()` | Returns mock string `"Transcribed audio chunk N"` | Calls Deepgram `AsyncDeepgramClient` pre-recorded API |
| `src/agents/stt_agent.py` — `VoxtralModelManager` (new init) | No API key / SDK usage | Accepts `deepgram_api_key` optional; falls back to Voxtral when absent |
| `src/agents/stt_agent.py` — `LanguageDetector.detect_language()` | `np.random.choice(supported_languages)` | Calls `langdetect.detect(text)` on transcribed text |
| `src/agents/stt_agent.py` — `LanguageDetector.detect_language()` signature | Takes `AudioChunk` | Should also accept `text: str` (post-transcription detection) |
| `src/core/processing_pipeline.py` — `_process_stt()` | Inline mock returning hardcoded strings | Delegates to `VoxtralModelManager` |
| `tests/test_stt_agent.py` | `asyncio.run(main())` script, not pytest | `async def test_*` functions with `pytest.ini asyncio_mode=auto` |

### Recommended Project Structure (additions)

```
kiro/voiquyr/
├── src/agents/
│   └── stt_agent.py          # VoxtralModelManager + LanguageDetector (modified)
├── src/core/
│   └── processing_pipeline.py # _process_stt() wired to real STT (modified)
└── tests/
    └── test_stt_agent.py      # Rewritten as proper pytest async tests
```

### Pattern 1: Deepgram Async Pre-Recorded Transcription

**What:** Call Deepgram REST API with audio bytes; await response; extract transcript string.
**When to use:** STT-01 — any WAV/MP3 bytes passed to `VoxtralModelManager.transcribe()`.

```python
# Source: https://developers.deepgram.com/docs/pre-recorded-audio
# deepgram-sdk v3.x API
import os
from deepgram import DeepgramClient, PrerecordedOptions

async def transcribe_with_deepgram(audio_bytes: bytes) -> str:
    api_key = os.getenv("DEEPGRAM_API_KEY")
    client = DeepgramClient(api_key)

    payload = {"buffer": audio_bytes}
    options = PrerecordedOptions(model="nova-2", language="en", punctuate=True)

    # asyncprerecorded for async call
    response = await client.listen.asyncprerecorded.v("1").transcribe_file(payload, options)
    return response.results.channels[0].alternatives[0].transcript
```

### Pattern 2: Mistral Voxtral Fallback Transcription

**What:** Call Mistral audio transcription API; extract `.text` from response.
**When to use:** STT-02 — `DEEPGRAM_API_KEY` absent or `DeepgramError` raised.

```python
# Source: https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
import os
from mistralai import Mistral

async def transcribe_with_voxtral(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key)

    # Mistral SDK is synchronous; wrap in executor for async contexts
    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.audio.transcriptions.complete(
            model="voxtral-mini-latest",
            file={"content": audio_bytes, "file_name": filename},
        )
    )
    return response.text
```

### Pattern 3: langdetect Language Detection (Post-Transcription)

**What:** Detect ISO 639-1 language code from transcribed text string.
**When to use:** STT-03 — after transcript string is obtained, detect language for pipeline context.

```python
# Source: https://github.com/Mimino666/langdetect
from langdetect import detect, DetectorFactory

# Set seed ONCE at module level for determinism
DetectorFactory.seed = 0

def detect_language(text: str) -> str:
    """Returns ISO 639-1 language code, e.g. 'en', 'ar', 'fr'."""
    try:
        return detect(text)
    except Exception:
        return "en"  # fallback
```

### Pattern 4: VoxtralModelManager — Deepgram Primary, Voxtral Fallback

**What:** Check `DEEPGRAM_API_KEY` at transcription time; fall back cleanly if absent.
**When to use:** STT-01 + STT-02 combined in `transcribe()` method.

```python
import os

class VoxtralModelManager:
    def __init__(self):
        self._deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        self._mistral_api_key = os.getenv("MISTRAL_API_KEY")

    async def transcribe(self, audio_chunk: AudioChunk) -> TranscriptionResult:
        audio_bytes = self._chunk_to_wav_bytes(audio_chunk)

        if self._deepgram_api_key:
            try:
                text = await self._transcribe_deepgram(audio_bytes)
            except Exception as e:
                self.logger.warning(f"Deepgram failed ({e}), falling back to Voxtral")
                text = await self._transcribe_voxtral(audio_bytes)
        else:
            text = await self._transcribe_voxtral(audio_bytes)

        return TranscriptionResult(
            text=text,
            confidence=0.95,
            language="",   # LanguageDetector fills this after
            ...
        )
```

### Pattern 5: WAV Bytes from numpy float32

**What:** Convert `AudioChunk.data` (numpy float32) to WAV bytes for Deepgram/Voxtral file upload.
**When to use:** Before calling either API; they accept file bytes, not numpy arrays.

```python
import io
import numpy as np
import scipy.io.wavfile

def _chunk_to_wav_bytes(chunk: AudioChunk) -> bytes:
    """Encode numpy float32 audio as WAV bytes."""
    buf = io.BytesIO()
    # scipy expects int16 or float32; normalize to int16 for broadest compat
    audio_int16 = (chunk.data * 32767).astype(np.int16)
    scipy.io.wavfile.write(buf, chunk.sample_rate, audio_int16)
    return buf.getvalue()
```

### Pattern 6: pytest async test with API key skip guard

**What:** Skip test when `DEEPGRAM_API_KEY` not set; run real transcription when set.
**When to use:** STT-05 — `pytest tests/test_stt_agent.py` pattern.

```python
# pytest.ini has asyncio_mode=auto — no @pytest.mark.asyncio needed
import os
import pytest
import numpy as np

pytestmark = pytest.mark.skipif(
    not os.getenv("DEEPGRAM_API_KEY"),
    reason="DEEPGRAM_API_KEY not set"
)

async def test_transcribe_returns_real_string():
    from src.agents.stt_agent import VoxtralModelManager, AudioChunk
    mgr = VoxtralModelManager()
    # 1 second 440 Hz sine wave
    sr = 16000
    t = np.linspace(0, 1.0, sr)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    chunk = AudioChunk(data=audio, sample_rate=sr, timestamp=0.0, chunk_id=0)
    result = await mgr.transcribe(chunk)
    assert isinstance(result.text, str)
    assert len(result.text) > 0
    assert result.text != f"Transcribed audio chunk {chunk.chunk_id}"
```

### Anti-Patterns to Avoid

- **Running `asyncio.run()` inside pytest:** `asyncio_mode=auto` in `pytest.ini` already handles the event loop. Wrapping test functions in `asyncio.run()` will cause "This event loop is already running" errors.
- **Calling `langdetect.detect()` directly on audio bytes:** `langdetect` operates on text strings only. Language detection must happen after transcription.
- **Module-level `DeepgramClient()` without API key:** Instantiation without a key raises at import time in some SDK versions. Guard with `os.getenv("DEEPGRAM_API_KEY")` check before instantiation.
- **Using `deepgram-sdk` v4+ API on a v3 install:** The `.listen.v1.media.transcribe_file()` path is v4+; the v3 path is `.listen.asyncprerecorded.v("1").transcribe_file()`. Check installed version.
- **Blocking Mistral SDK calls in async context:** `mistralai` 2.x client methods are synchronous. Must wrap in `loop.run_in_executor()` or use a thread pool.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio → text transcription | Custom WebSocket client to Deepgram REST | `deepgram-sdk` `AsyncDeepgramClient` | SDK handles auth headers, retry, response parsing, JSON unmarshalling |
| Language detection | Feature-based acoustic classifier | `langdetect.detect(text)` | The acoustic classifier in `language_detection.py` is fully mocked; `langdetect` gives real ISO codes from text in <1ms |
| WAV encoding | Manual PCM byte assembly | `scipy.io.wavfile.write()` to `BytesIO` | Correct RIFF headers, sample width negotiation, endianness handled |
| Async event loop management | Manual `asyncio.run()` in tests | `pytest.ini asyncio_mode=auto` | Already configured in Phase 1 |

**Key insight:** Language detection from audio requires trained ML models (Whisper-style) — that's a v2 feature. For v1, detect language from the transcribed text string using `langdetect`. This satisfies STT-03 without model training.

---

## Common Pitfalls

### Pitfall 1: `test_stt_agent.py` is a Script, Not Pytest

**What goes wrong:** Running `pytest tests/test_stt_agent.py` collects 0 tests and reports success with no assertions verified, or fails because the file calls `asyncio.run()` at module level.

**Why it happens:** The file ends with `if __name__ == "__main__": asyncio.run(main())`. Pytest does not run `main()`.

**How to avoid:** Rewrite the file as standard pytest with `async def test_*()` functions. Do NOT keep the old `asyncio.run(main())` structure.

**Warning signs:** `pytest tests/test_stt_agent.py` output shows `0 tests collected` or `passed` with no test names printed.

### Pitfall 2: Deepgram SDK v3 vs v4 API Surface

**What goes wrong:** Using `client.listen.v1.media.transcribe_file()` (v4 API) on a v3.x install raises `AttributeError: 'Listen' object has no attribute 'v1'`.

**Why it happens:** Deepgram made breaking API changes between v3 and v4.

**How to avoid:** Pin `deepgram-sdk>=3.1.0,<4.0` in `requirements.txt`. Use v3 API: `client.listen.asyncprerecorded.v("1").transcribe_file(payload, options)`.

**Warning signs:** `AttributeError` on `listen.v1` or `listen.prerecorded`.

### Pitfall 3: `langdetect` Non-Determinism Without Seed

**What goes wrong:** `langdetect.detect()` returns different language codes for the same short text on repeated runs — tests are flaky.

**Why it happens:** Internal algorithm uses random initialization by default.

**How to avoid:** Add `from langdetect import DetectorFactory; DetectorFactory.seed = 0` at module level in `language_detection.py` or wherever `detect()` is first called. Must happen before the first call.

**Warning signs:** Test for language detection passes sometimes, fails other times on the same input.

### Pitfall 4: `np.random.choice()` Still in `LanguageDetector`

**What goes wrong:** STT-03 fails — `detect_language()` returns unpredictable language codes despite `langdetect` being installed, because the old random path was not removed.

**Why it happens:** The existing `LanguageDetector.detect_language()` in `stt_agent.py` calls `np.random.choice(self.supported_languages)` — it operates on `AudioChunk`, not text. The langdetect integration must replace this entire code path.

**How to avoid:** Change `detect_language(audio_chunk: AudioChunk)` signature to also accept `text: str`. Remove the `np.random.choice()` call entirely.

### Pitfall 5: Mistral SDK Blocking Call in Async Context

**What goes wrong:** `client.audio.transcriptions.complete()` blocks the event loop for seconds, causing timeouts in the async pipeline.

**Why it happens:** `mistralai` v2 SDK is synchronous; no `await` support for transcriptions.

**How to avoid:** Wrap in `asyncio.get_event_loop().run_in_executor(None, lambda: ...)` to offload to threadpool. Alternatively use `asyncio.to_thread()` (Python 3.9+).

### Pitfall 6: Sending numpy float32 Array Directly to Deepgram

**What goes wrong:** Deepgram API returns 400/422 because the payload is not valid WAV bytes.

**Why it happens:** `AudioChunk.data` is a numpy float32 array. Deepgram expects file bytes (WAV, MP3, etc.).

**How to avoid:** Convert using `scipy.io.wavfile.write()` to a `BytesIO` buffer first. Normalize float32 to int16 before encoding.

---

## Code Examples

Verified patterns from official sources:

### Deepgram v3 Async Pre-Recorded (URL)

```python
# Source: https://developers.deepgram.com/docs/pre-recorded-audio (v3 pattern)
import os
import asyncio
from deepgram import DeepgramClient, PrerecordedOptions

AUDIO_URL = {"url": "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"}

async def main():
    deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
    options = PrerecordedOptions(model="nova-2", smart_format=True)
    response = await deepgram.listen.asyncprerecorded.v("1").transcribe_url(AUDIO_URL, options)
    transcript = response.results.channels[0].alternatives[0].transcript
    print(transcript)

asyncio.run(main())
```

### Mistral Voxtral Offline Transcription

```python
# Source: https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
import os
from mistralai import Mistral

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

with open("audio.mp3", "rb") as f:
    response = client.audio.transcriptions.complete(
        model="voxtral-mini-latest",
        file={"content": f, "file_name": "audio.mp3"},
    )
print(response.text)
```

### langdetect Basic Usage

```python
# Source: https://github.com/Mimino666/langdetect
from langdetect import detect, detect_langs, DetectorFactory

DetectorFactory.seed = 0  # determinism

detect("This is English text")   # returns 'en'
detect("Bonjour le monde")       # returns 'fr'
detect_langs("I love this")      # returns [en:0.9999...]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mock string `"Transcribed audio chunk N"` | Real Deepgram API call | Phase 2 | STT-01 satisfied |
| `np.random.choice(languages)` for language detection | `langdetect.detect(text)` | Phase 2 | STT-03 satisfied |
| Deepgram SDK v2 (`deepgram.transcription.prerecorded()`) | SDK v3 (`listen.asyncprerecorded.v("1")`) | SDK v3 release 2023 | Breaking API change — v3 is the current interface |
| asyncio.run() test scripts | `pytest asyncio_mode=auto` | Phase 1 established | No @pytest.mark.asyncio needed |
| `aioredis` | `redis.asyncio` | Phase 1 (Python 3.14 compat) | Already resolved |

**Deprecated/outdated:**
- `asyncio.sleep(0.05)` simulation in `transcribe()`: must be fully removed — this is the mock, not a helper
- `_load_voxtral_small()`, `_load_voxtral_mini()`, `_load_nvidia_canary()` returning mock dict objects: these placeholder loaders are not needed for API-based transcription (no local model loading)
- `VoxtralModelManager.load_model()` model-loading flow: the fallback chain in `STTAgent.initialize()` loads local models; for API-based calls, no local model load is needed — the manager just needs the API key

---

## Open Questions

1. **Deepgram SDK v3 vs v4 installed version**
   - What we know: Command-center pins `3.1.0`; PyPI absolute latest is `6.0.1`; v3 and v4+ have incompatible APIs
   - What's unclear: Which version will be installed in the main `kiro/voiquyr/` venv
   - Recommendation: Explicitly pin `deepgram-sdk>=3.1.0,<4.0` in `requirements.txt` and use v3 API. Document this in Wave 0 of plan.

2. **Voxtral model availability at `voxtral-mini-latest`**
   - What we know: Mistral docs show `"voxtral-mini-latest"` as the model name for offline transcription
   - What's unclear: Whether this model name resolves correctly with `mistralai` SDK v2.0.4 as of March 2026
   - Recommendation: Also test `"voxtral-mini-2407"` as fallback model name. Treat STT-02 test as requiring `MISTRAL_API_KEY` guard.

3. **`LanguageDetector` signature — AudioChunk vs text**
   - What we know: Existing `detect_language(self, audio_chunk: AudioChunk)` signature is called from `STTAgent.process_audio_stream()`; langdetect works on text strings
   - What's unclear: Whether the planner should change the method signature or add a new `detect_language_from_text(text: str)` method
   - Recommendation: Change the `LanguageDetector.detect_language()` method to accept `text: str`; update the `STTAgent` caller to pass the transcribed text.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (asyncio_mode=auto) |
| Config file | `kiro/voiquyr/pytest.ini` |
| Quick run command | `pytest tests/test_stt_agent.py -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STT-01 | `VoxtralModelManager.transcribe()` returns real transcript (not mock) | integration | `pytest tests/test_stt_agent.py::test_transcribe_returns_real_string -x` | ❌ Wave 0 |
| STT-02 | Falls back to Voxtral when `DEEPGRAM_API_KEY` absent | integration | `pytest tests/test_stt_agent.py::test_voxtral_fallback -x` | ❌ Wave 0 |
| STT-03 | `LanguageDetector.detect_language()` returns real language code | unit | `pytest tests/test_stt_agent.py::test_language_detection_returns_code -x` | ❌ Wave 0 |
| STT-04 | `processing_pipeline._process_stt()` calls real STT, not mock | unit | `pytest tests/test_stt_agent.py::test_pipeline_stt_integration -x` | ❌ Wave 0 |
| STT-05 | Full `pytest tests/test_stt_agent.py` passes | integration | `pytest tests/test_stt_agent.py -v` | ❌ Wave 0 (rewrite) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_stt_agent.py -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green (with API keys set) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_stt_agent.py` — must be **rewritten** from asyncio script to pytest async tests; covers STT-01 through STT-05
- [ ] `requirements.txt` additions: `deepgram-sdk>=3.1.0,<4.0`, `mistralai>=2.0.0`, `langdetect>=1.0.9`

*(Existing pytest infrastructure from Phase 1 covers fixtures and asyncio_mode=auto — no new conftest needed)*

---

## Sources

### Primary (HIGH confidence)

- `kiro/voiquyr/src/agents/stt_agent.py` — Full source audit; mock code confirmed at lines 219-235 (transcribe), 269 (random language choice)
- `kiro/voiquyr/src/agents/language_detection.py` — Source audit; all detection is simulated (`_simulate_*` methods)
- `kiro/voiquyr/src/core/processing_pipeline.py` — Source audit; `_process_stt()` mock confirmed at lines 311-335
- `kiro/voiquyr/tests/test_stt_agent.py` — Source audit; confirmed as `asyncio.run(main())` script, not pytest
- `kiro/voiquyr/pytest.ini` — Confirmed `asyncio_mode = auto`
- `kiro/voiquyr/voiquyr-command-center/backend/requirements.txt` — Confirmed `deepgram-sdk==3.1.0` already in use
- https://pypi.org/pypi/deepgram-sdk/json — Version 6.0.1 latest absolute; v3.x in use here
- https://pypi.org/pypi/langdetect/json — Version 1.0.9, stable
- https://pypi.org/pypi/mistralai/json — Version 2.0.4 latest

### Secondary (MEDIUM confidence)

- https://developers.deepgram.com/docs/pre-recorded-audio — v3 `asyncprerecorded.v("1").transcribe_url()` API confirmed
- https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription — `client.audio.transcriptions.complete()` with `voxtral-mini-latest` confirmed
- https://github.com/Mimino666/langdetect — `detect()`, `DetectorFactory.seed = 0` confirmed

### Tertiary (LOW confidence)

- WebSearch results for Deepgram SDK v3 async examples — cross-verified with PyPI and command-center code
- WebSearch results for Mistral Voxtral 2025 — model name `voxtral-mini-latest` from official docs; untested against API

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyPI versions verified, command-center deepgram-sdk version confirmed
- Architecture: HIGH — source code fully read; all mock locations identified exactly
- Pitfalls: HIGH — directly derived from reading source code and known SDK version issues
- Voxtral model name: MEDIUM — docs show `voxtral-mini-latest` but untested against live API

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (deepgram-sdk major version stable; langdetect frozen)

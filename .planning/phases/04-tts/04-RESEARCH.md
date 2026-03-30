# Phase 4: TTS - Research

**Researched:** 2026-03-28
**Domain:** Text-to-Speech synthesis — ElevenLabs SDK v2, Coqui TTS XTTS-v2 self-hosted, WebSocket streaming
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TTS-01 | `XTTSv2ModelManager.synthesize()` calls ElevenLabs SDK (not sine-wave) | ElevenLabs SDK v2 `text_to_speech.convert()` is the correct method; `AsyncElevenLabs` for async path |
| TTS-02 | XTTS-v2 via `TTS` library available as self-hosted path | Coqui TTS 0.22.0 `TTS("tts_models/multilingual/multi-dataset/xtts_v2")` is confirmed importable; needs to be added to requirements.txt |
| TTS-03 | `VoiceCloningEngine.clone_voice()` uses real `get_conditioning_latents()` | `model.get_conditioning_latents(audio_path=["ref.wav"])` returns `(gpt_cond_latent, speaker_embedding)` tuple — confirmed in Coqui docs |
| TTS-04 | Streaming chunks wired into `tts_streaming.py` for WebSocket delivery | `TTSStreamingManager` and `TTSWebSocketStreamer` exist; they call `tts_agent.synthesize_text()` — the fix is in `synthesize_text()` backing implementation, not the streaming layer |
| TTS-05 | End-to-end pipeline test passes: audio in → STT → LLM → TTS → audio out | `processing_pipeline._process_tts()` returns `b"MOCK_AUDIO_DATA_..."` — needs wiring to real `TTSAgent.synthesize_text()` |
</phase_requirements>

---

## Summary

Phase 4 replaces all TTS mock implementations with real synthesis calls. There are two parallel paths:

**Path A — ElevenLabs (primary, API-backed):** `XTTSv2ModelManager.synthesize()` currently generates a sine-wave. The fix is to call `AsyncElevenLabs.text_to_speech.convert()` (SDK v2 method — `generate()` was removed in v2). The `ELEVENLABS_API_KEY` is already present in `.env` and `.env.example`. The ElevenLabs SDK 2.40.0 is the current PyPI version (not yet installed in the project venv).

**Path B — XTTS-v2 self-hosted (fallback):** The `TTS` library (Coqui, 0.22.0) must be importable and callable. `XTTSv2ModelManager.initialize()` currently creates a mock dict; the real path loads `TTS("tts_models/multilingual/multi-dataset/xtts_v2")`. `VoiceCloningEngine.clone_voice()` must call `model.get_conditioning_latents(audio_path=[...])` which returns `(gpt_cond_latent, speaker_embedding)` — not a dict/mock as now. XTTS-v2 outputs audio at 24 kHz.

**Streaming (TTS-04):** The `TTSWebSocketStreamer` and `TTSStreamingManager` in `tts_streaming.py` already have the correct structure — they call `tts_agent.synthesize_text()`. Fixing the backing `synthesize_text()` (TTS-01/TTS-02) unblocks streaming automatically. The chunk delivery loop is already wired. Minor fix needed: the class definition on line 28 has a stray newline (`class \nAudioFormat`) — a syntax error to fix in Wave 0.

**Pipeline (TTS-05):** `processing_pipeline._process_tts()` is a pure mock. It must be wired to `TTSAgent.synthesize_text()` and convert `SynthesisResult.audio_data` (numpy array) to WAV bytes.

**Primary recommendation:** Install `elevenlabs>=2.0.0` and `TTS==0.22.0` into requirements.txt and venv. Replace `XTTSv2ModelManager.synthesize()` with ElevenLabs SDK call. Make XTTS-v2 importable and callable via `TTS` API. Wire `_process_tts()` in pipeline to real `TTSAgent`.

---

## Project Constraints (from CLAUDE.md)

- Primary development is in `kiro/voiquyr/`
- Backend runs: `python -m uvicorn src.api.main:app --reload` from `kiro/voiquyr/`
- Tests run: `pytest` from `kiro/voiquyr/`; single file: `pytest tests/test_tts_agent.py -v`
- `ELEVENLABS_API_KEY` is documented in `.env.example` and already present in `.env`
- Immutability rule: create new `SynthesisResult` objects, never mutate in place
- File size: 200-400 lines typical, 800 max (`tts_agent.py` is ~1750 lines — the planner should be aware of this; refactoring is out of scope but new code blocks must stay under 800 lines each)
- TDD: write tests first (RED), then implement (GREEN)
- 80% minimum test coverage

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| elevenlabs | 2.40.0 | ElevenLabs TTS API — `text_to_speech.convert()` and `.stream()` | Official SDK; `generate()` was removed in v2 — must use v2 API |
| TTS | 0.22.0 | Coqui XTTS-v2 self-hosted path — `TTS("tts_models/multilingual/multi-dataset/xtts_v2")` | Latest stable; includes XTTS-v2 model download + inference |
| torch | >=2.0.0 | Required by TTS library and existing tts_agent.py | Already in requirements.txt |
| torchaudio | >=2.0.0 | Audio resampling utilities | Already in requirements.txt |
| numpy | >=1.24.0 | Audio array manipulation | Already in requirements.txt |
| soundfile | >=0.12.0 | WAV bytes conversion from numpy (scipy.io.wavfile alternative) | Clean API for float32→WAV bytes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | >=1.10.0 | `scipy.io.wavfile.write()` for numpy→WAV bytes | Already in requirements.txt; use for pipeline WAV output |
| pytest-asyncio | >=0.23.0 | Async TTS tests | Already configured in pytest.ini (`asyncio_mode = auto`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ElevenLabs SDK | Direct HTTP to `api.elevenlabs.io` | SDK handles auth, retry, streaming iterators — no reason to hand-roll |
| `TTS` library | `transformers` + XTTS-v2 weights | `TTS` library is the official Coqui wrapper with model management built in |
| `soundfile` for WAV bytes | `scipy.io.wavfile` | `scipy` already in requirements; either works; scipy avoids an extra install |

**Installation (add to `kiro/voiquyr/requirements.txt`):**
```bash
pip install "elevenlabs>=2.0.0" "TTS==0.22.0"
```

**Version verification (confirmed 2026-03-28):**
- `elevenlabs`: PyPI latest = 2.40.0
- `TTS` (Coqui): PyPI latest = 0.22.0
- Both are NOT currently installed in the project venv

---

## Architecture Patterns

### TTS-01: ElevenLabs SDK Path in `XTTSv2ModelManager.synthesize()`

The class name `XTTSv2ModelManager` is misleading — per the requirements, `TTS-01` says this class calls ElevenLabs (not XTTS-v2). XTTS-v2 is the fallback (TTS-02). The planner must treat `XTTSv2ModelManager` as the **primary/ElevenLabs** manager, and `VoiceCloningEngine` + XTTS-v2 model loading as the **self-hosted** path.

**Pattern: Replace mock dict with `AsyncElevenLabs` client**

```python
# Source: https://github.com/elevenlabs/elevenlabs-python/blob/main/README.md
from elevenlabs.client import AsyncElevenLabs
import os, io
import numpy as np
import soundfile as sf

class XTTSv2ModelManager:
    async def initialize(self) -> bool:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        self.client = AsyncElevenLabs(api_key=api_key)
        self.model_loaded = True
        return True

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        # ElevenLabs SDK v2: use text_to_speech.convert() — NOT generate()
        audio_bytes_iter = await self.client.text_to_speech.convert(
            text=request.text,
            voice_id=request.voice_id,   # ElevenLabs voice ID string
            model_id="eleven_multilingual_v2",
            output_format="pcm_22050",   # raw PCM at 22050 Hz → numpy-friendly
        )
        # collect bytes from iterator
        audio_bytes = b"".join(audio_bytes_iter)
        # convert PCM bytes → numpy float32 array
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        sample_rate = 22050
        return SynthesisResult(
            audio_data=audio,
            sample_rate=sample_rate,
            duration=len(audio) / sample_rate,
            voice_id=request.voice_id,
            text=request.text,
            quality_score=4.5,
            processing_time=0.0,
        )
```

**ElevenLabs voice_id mapping:** ElevenLabs uses string voice IDs like `"JBFqnCBsd6RMkjVDRZzb"` (Rachel). The existing `VoiceModel.voice_id` strings (`"en_us_female_1"`, etc.) are internal — a mapping dict from internal IDs to ElevenLabs voice IDs is needed in `XTTSv2ModelManager` or `VoiceModelManager`.

### TTS-02: XTTS-v2 Self-Hosted Path

The `TTS` library downloads the XTTS-v2 model (~2 GB) from Hugging Face on first call. The plan must NOT block on model download in the test — use `pytest.mark.xfail` or a `@pytest.mark.slow` guard for the download step.

```python
# Source: https://huggingface.co/coqui/XTTS-v2
from TTS.api import TTS
import numpy as np

class XTTSv2SelfHostedManager:
    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
    SAMPLE_RATE = 24000  # XTTS-v2 outputs 24 kHz

    async def initialize(self) -> bool:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # TTS() download triggers on first init — can take minutes
        self.tts = TTS(self.MODEL_NAME).to(device)
        self.model_loaded = True
        return True

    async def synthesize(self, text: str, speaker_wav: str, language: str = "en") -> np.ndarray:
        # tts.tts() returns list of amplitude values (float)
        audio = self.tts.tts(text=text, speaker_wav=speaker_wav, language=language)
        return np.array(audio, dtype=np.float32)
```

**For importability test (TTS-02 success criteria #2):** The test only needs to verify `from TTS.api import TTS` does not raise — it does NOT need to load the full model. The plan should have a separate lightweight import test.

### TTS-03: `VoiceCloningEngine.clone_voice()` with `get_conditioning_latents()`

The low-level XTTS-v2 model (not the `TTS` API wrapper) exposes `get_conditioning_latents()`. This requires loading the model via `XttsConfig` + `Xtts.init_from_config()`, not via the `TTS` API wrapper.

```python
# Source: https://github.com/coqui-ai/TTS/blob/dev/docs/source/models/xtts.md
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

# Load model (low-level path)
config = XttsConfig()
config.load_json("/path/to/xtts/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="/path/to/xtts/", eval=True)

# Voice cloning — returns (gpt_cond_latent, speaker_embedding)
gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
    audio_path=["reference.wav"]
)

# Inference with conditioning latents
out = model.inference(
    "Hello world",
    "en",
    gpt_cond_latent,
    speaker_embedding,
    temperature=0.7,
)
# out["wav"] is a list/array of float samples at 24 kHz
```

**Critical detail:** `get_conditioning_latents()` takes `audio_path` as a **list** of strings (file paths), not a numpy array. The current `VoiceCloneRequest` carries `sample_audio: np.ndarray` — the implementation must write the numpy array to a temp WAV file first before calling `get_conditioning_latents()`.

**Also critical:** The `TTS` API wrapper (`TTS.api.TTS`) does NOT expose `get_conditioning_latents()` directly — the low-level `Xtts` model class must be used for TTS-03.

### TTS-04: Streaming Wiring in `tts_streaming.py`

`TTSWebSocketStreamer.stream_synthesis()` calls `self.tts_agent.synthesize_text()` and then chunks the result. This is already structurally correct — fixing `synthesize_text()` backing implementation (TTS-01) unblocks streaming automatically.

**One bug to fix (Wave 0):** In `tts_streaming.py` line 28-29, there is a syntax error — a newline inside the class definition keyword:
```python
# BROKEN (current):
class
AudioFormat(Enum):

# FIXED:
class AudioFormat(Enum):
```
This must be fixed before any TTS streaming tests can pass.

### TTS-05: E2E Pipeline Wiring

`processing_pipeline._process_tts()` returns mock bytes. It must call `TTSAgent.synthesize_text()` and convert `SynthesisResult.audio_data` (numpy float32 array) to WAV bytes:

```python
# Pattern: numpy array → WAV bytes using scipy (already in requirements)
import io
import scipy.io.wavfile as wav

def audio_array_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio_int16 = (audio * 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, sample_rate, audio_int16)
    return buf.getvalue()
```

### Recommended Project Structure (no changes needed)

The existing structure in `kiro/voiquyr/src/agents/` is already correct:
```
src/agents/
├── tts_agent.py          # XTTSv2ModelManager, VoiceCloningEngine, TTSAgent
├── tts_streaming.py      # TTSWebSocketStreamer, TTSStreamingManager
src/core/
├── processing_pipeline.py   # _process_tts() mock → real TTSAgent call
tests/
├── test_tts_agent.py        # Exists — needs conversion to real pytest format with xfail stubs
```

### Anti-Patterns to Avoid

- **Using the old `elevenlabs.generate()` API:** Was removed in SDK v2. Always use `client.text_to_speech.convert()`.
- **Blocking on XTTS-v2 model download in unit tests:** The `TTS()` constructor downloads ~2 GB. Tests must mock the model or use `@pytest.mark.slow` / `xfail` stubs for CI.
- **Passing numpy array directly to `get_conditioning_latents()`:** The method takes file paths, not arrays. Write to temp file first.
- **Assuming XTTS-v2 outputs 22050 Hz:** XTTS-v2 outputs at 24000 Hz. The pipeline `SynthesisResult` must carry the correct `sample_rate`.
- **Conflating `XTTSv2ModelManager` with XTTS-v2 self-hosted:** Per TTS-01, `XTTSv2ModelManager.synthesize()` calls ElevenLabs, not the TTS library. The name is legacy — do not refactor the class name (out of scope).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TTS synthesis | Custom HTTP calls to ElevenLabs REST API | `elevenlabs` SDK `text_to_speech.convert()` | SDK handles auth, chunked transfer, retries, streaming iterators |
| Streaming audio delivery | Custom chunk scheduler | Existing `TTSWebSocketStreamer` in `tts_streaming.py` | Already implemented with latency optimizer and format conversion |
| Numpy array → WAV bytes | Custom WAV header construction | `scipy.io.wavfile.write()` into `io.BytesIO` | Handles all WAV header edge cases correctly |
| Voice embedding extraction | Custom speaker encoder | `model.get_conditioning_latents()` from Coqui XTTS-v2 | The correct way to extract conditioning latents from XTTS-v2 |
| Model download management | Custom HuggingFace download | `TTS("tts_models/multilingual/multi-dataset/xtts_v2")` | TTS library handles model download, caching, device placement |

**Key insight:** The hard parts of TTS (prosody, voice consistency, streaming buffering) are solved by ElevenLabs and Coqui. The only work in Phase 4 is wiring calls correctly.

---

## Common Pitfalls

### Pitfall 1: ElevenLabs SDK v1 vs v2 API Mismatch
**What goes wrong:** `from elevenlabs import generate` raises `ImportError`. The command-center backend uses `elevenlabs==0.2.27` (v0.x), while the main platform needs v2.x.
**Why it happens:** The old simple `generate()` function was removed in SDK v2. The `voiquyr-command-center/backend/requirements.txt` pins `0.2.27`.
**How to avoid:** Install `elevenlabs>=2.0.0` in `kiro/voiquyr/requirements.txt`. The command-center backend is a separate venv — no conflict.
**Warning signs:** `ImportError: cannot import name 'generate' from 'elevenlabs'`

### Pitfall 2: XTTS-v2 Model Download Blocking Tests
**What goes wrong:** `TTS("tts_models/multilingual/multi-dataset/xtts_v2")` downloads ~2 GB on first run, causing test timeout or CI failure.
**Why it happens:** The `TTS` library calls HuggingFace Hub on construction if the model isn't cached locally.
**How to avoid:** Use `pytest.mark.xfail(reason="requires model download")` for tests requiring the actual XTTS-v2 model. The importability test (TTS-02 success criterion #2) only needs `from TTS.api import TTS` — no model load.
**Warning signs:** Tests hang for minutes; CI shows no output; `OSError: [Errno 28] No space left` in minimal environments.

### Pitfall 3: `get_conditioning_latents()` Requires File Path, Not Array
**What goes wrong:** `model.get_conditioning_latents(audio_path=sample_audio_array)` raises `TypeError` or produces garbage embeddings.
**Why it happens:** The method signature requires a list of file paths: `audio_path: List[str]`. The existing `VoiceCloneRequest.sample_audio` is a numpy array.
**How to avoid:** Write the numpy array to a `tempfile.NamedTemporaryFile(suffix=".wav")` before calling `get_conditioning_latents()`. Clean up after.
**Warning signs:** `AttributeError: 'numpy.ndarray' object has no attribute 'read'`

### Pitfall 4: Wrong Sample Rate in SynthesisResult
**What goes wrong:** Audio sounds sped up or slowed down after TTS pipeline returns bytes.
**Why it happens:** XTTS-v2 outputs 24 kHz audio. If the system assumes 22050 Hz (the `SynthesisRequest.sample_rate` default), the WAV file or streaming chunks carry wrong metadata.
**How to avoid:** Set `SynthesisResult.sample_rate = 24000` for the XTTS-v2 path. For ElevenLabs with `output_format="pcm_22050"`, set `sample_rate = 22050`.
**Warning signs:** Audio duration calculation is wrong; audio plays at wrong speed.

### Pitfall 5: `tts_streaming.py` Syntax Error
**What goes wrong:** `pytest tests/test_tts_streaming.py` fails with `SyntaxError` even before tests run.
**Why it happens:** Line 28-29 of `tts_streaming.py` has a newline between `class` keyword and class name: `class \nAudioFormat(Enum):`.
**How to avoid:** Fix in Wave 0 before implementing anything.
**Warning signs:** `SyntaxError: invalid syntax` pointing to `tts_streaming.py` line 28.

### Pitfall 6: ElevenLabs voice_id Namespace Mismatch
**What goes wrong:** `XTTSv2ModelManager.synthesize()` receives `voice_id="en_us_female_1"` (internal ID) but ElevenLabs API needs `"JBFqnCBsd6RMkjVDRZzb"` (ElevenLabs voice ID).
**Why it happens:** The internal `VoiceModel.voice_id` scheme is project-local. ElevenLabs has its own voice registry.
**How to avoid:** Add a mapping dict in `XTTSv2ModelManager` from internal IDs to ElevenLabs IDs, with a fallback to a default ElevenLabs voice (e.g., "Rachel" = `"21m00Tcm4TlvDq8ikWAM"`).
**Warning signs:** `HTTPError: 404 - voice not found` from ElevenLabs API.

---

## Code Examples

### ElevenLabs SDK v2 - Async synthesis (verified from official SDK repo)

```python
# Source: https://github.com/elevenlabs/elevenlabs-python/blob/main/README.md
from elevenlabs.client import AsyncElevenLabs
import asyncio

async def synthesize_with_elevenlabs(text: str, voice_id: str, api_key: str) -> bytes:
    client = AsyncElevenLabs(api_key=api_key)
    audio_iter = await client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    return b"".join(audio_iter)
```

### ElevenLabs SDK v2 - Streaming (verified)

```python
# Source: https://github.com/elevenlabs/elevenlabs-python/blob/main/README.md
async def stream_with_elevenlabs(text: str, voice_id: str, api_key: str):
    client = AsyncElevenLabs(api_key=api_key)
    audio_stream = await client.text_to_speech.stream(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
    )
    async for chunk in audio_stream:
        if isinstance(chunk, bytes):
            yield chunk
```

### XTTS-v2 Simple API (TTS library wrapper)

```python
# Source: https://huggingface.co/coqui/XTTS-v2
import torch
from TTS.api import TTS

device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# Returns: list of float amplitude values (24 kHz)
audio = tts.tts(
    text="Hello world",
    speaker_wav="reference.wav",
    language="en"
)
# Write to file:
tts.tts_to_file(text="Hello world", speaker_wav="ref.wav", language="en", file_path="out.wav")
```

### XTTS-v2 Low-Level: `get_conditioning_latents()` for `VoiceCloningEngine`

```python
# Source: https://github.com/coqui-ai/TTS/blob/dev/docs/source/models/xtts.md
import tempfile, os
import numpy as np
import scipy.io.wavfile as wav
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

def numpy_to_temp_wav(audio: np.ndarray, sample_rate: int) -> str:
    """Write numpy array to temp WAV file, return path."""
    audio_int16 = (audio * 32767).astype(np.int16)
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.write(tf.name, sample_rate, audio_int16)
    return tf.name

# Load model (requires downloaded checkpoint)
config = XttsConfig()
config.load_json("/path/to/xtts/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="/path/to/xtts/", eval=True)
model.cuda()

# Clone voice from numpy sample
temp_path = numpy_to_temp_wav(sample_audio_np, sample_rate=22050)
try:
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        audio_path=[temp_path]
    )
finally:
    os.unlink(temp_path)  # clean up temp file

# Synthesize with cloned voice
out = model.inference("Hello world", "en", gpt_cond_latent, speaker_embedding, temperature=0.7)
# out["wav"] is a list of floats at 24 kHz
```

### Pipeline: numpy → WAV bytes

```python
import io
import numpy as np
import scipy.io.wavfile as wav

def audio_array_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 audio array to WAV bytes."""
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, sample_rate, audio_int16)
    buf.seek(0)
    return buf.read()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `elevenlabs.generate()` | `client.text_to_speech.convert()` | SDK v2 (2024) | Breaking change — the old method is deleted |
| `elevenlabs.clone()` | `client.voices.ivc.create()` | SDK v2 (2024) | Breaking change — the old method is deleted |
| Coqui TTS `tts_models/tts_models/xtts_v2` | `tts_models/multilingual/multi-dataset/xtts_v2` | TTS 0.17+ | Model path format changed |
| `TTS.tts()` returns list | `TTS.tts()` returns list of floats (numpy-convertible) | stable | `np.array(result)` converts correctly |

**Deprecated/outdated:**
- `elevenlabs.generate()`: Removed in SDK v2. Any usage will raise `ImportError`.
- `elevenlabs.clone()`: Removed in SDK v2. Use `client.voices.ivc.create()` for instant voice clone via ElevenLabs.
- Command-center backend uses `elevenlabs==0.2.27` (v0.x old API) — this is a separate service/venv and does NOT affect the main platform. Do NOT update it in this phase.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 (venv) | All tests | Yes | 3.14 (venv) | — |
| `elevenlabs` SDK | TTS-01 | No (not in venv) | — | Install in Wave 0 |
| `TTS` (Coqui) | TTS-02, TTS-03 | No (not in venv) | — | Install in Wave 0 |
| `torch` | TTS-02, TTS-03 | Yes (requirements.txt) | >=2.0.0 | — |
| ELEVENLABS_API_KEY | TTS-01 | Yes (in .env) | — | — |
| XTTS-v2 model weights | TTS-02, TTS-03 | No (downloaded on first use) | — | xfail test stubs until downloaded |
| `scipy` | numpy→WAV bytes | Yes (requirements.txt) | >=1.10.0 | — |
| `pytest` + `pytest-asyncio` | All tests | Yes (pytest.ini present) | asyncio_mode=auto | — |

**Missing dependencies with no fallback:**
- `elevenlabs` (PyPI 2.40.0) — blocks TTS-01 and all streaming; install in Wave 0
- `TTS` (PyPI 0.22.0) — blocks TTS-02 and TTS-03; install in Wave 0

**Missing dependencies with fallback:**
- XTTS-v2 model weights — tests for TTS-02/TTS-03 can use `pytest.mark.xfail` stubs until model is downloaded in a GPU-enabled environment

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `kiro/voiquyr/pytest.ini` (asyncio_mode = auto) |
| Quick run command | `pytest tests/test_tts_agent.py -v -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TTS-01 | `XTTSv2ModelManager.synthesize("Hello world")` returns real audio bytes (not sine-wave) | unit + integration | `pytest tests/test_tts_agent.py::test_synthesize_real_audio -x` | Needs new test in existing file |
| TTS-02 | `from TTS.api import TTS` is importable without error | unit (import test) | `pytest tests/test_tts_agent.py::test_xtts_importable -x` | Needs new test |
| TTS-03 | `VoiceCloningEngine.clone_voice()` returns real embedding from `get_conditioning_latents()` | unit (slow/xfail) | `pytest tests/test_voice_cloning.py::test_real_conditioning_latents -x` | Existing file |
| TTS-04 | Streaming chunks flow through `tts_streaming.py` to WebSocket | integration | `pytest tests/test_tts_streaming.py::test_stream_synthesis -x` | Existing file |
| TTS-05 | E2E: audio in → STT → LLM → TTS → audio bytes out | E2E (slow) | `pytest tests/test_core_pipeline.py::test_e2e_audio_pipeline -x` | test_core_pipeline.py exists |

### Sampling Rate
- **Per task commit:** `pytest tests/test_tts_agent.py -v -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Fix syntax error in `tts_streaming.py` line 28 (`class \nAudioFormat` → `class AudioFormat`)
- [ ] `pip install "elevenlabs>=2.0.0" "TTS==0.22.0"` — add to `kiro/voiquyr/requirements.txt`
- [ ] Convert existing test functions in `test_tts_agent.py` from bare `async def` to `pytest` format (`async def test_*`) with `xfail` stubs for real API calls
- [ ] Add `test_synthesize_real_audio` stub in `test_tts_agent.py` (xfail until TTS-01 implemented)
- [ ] Add `test_xtts_importable` stub in `test_tts_agent.py` (xfail until TTS-02 implemented)

---

## Open Questions

1. **ElevenLabs voice_id mapping strategy**
   - What we know: Internal voice IDs are `"en_us_female_1"`, etc. ElevenLabs needs IDs like `"21m00Tcm4TlvDq8ikWAM"`.
   - What's unclear: Whether to hardcode a mapping dict or call `client.voices.list()` dynamically.
   - Recommendation: Hardcode a minimal mapping of 2-3 default voices in `XTTSv2ModelManager`. The test only needs `synthesize("Hello world")` to return real bytes — the exact voice is not specified.

2. **XTTS-v2 model download in CI**
   - What we know: The model is ~2 GB. Test TTS-02 success criterion #2 is "importable and callable without error."
   - What's unclear: Whether "callable" means actually running synthesis or just instantiating the `TTS` object.
   - Recommendation: Treat success criterion #2 as "import succeeds + `TTS(model_name)` constructor does not raise" (model downloads lazily). Mark integration synthesis tests as `@pytest.mark.slow`.

3. **`VoiceCloningEngine` class location**
   - What we know: The code inside `XTTSv2ModelManager.clone_voice()` (lines 554+) contains the cloning logic. `VoiceCloningEngine` is mentioned in success criteria but may be a method, not a standalone class.
   - What's unclear: Whether TTS-03 wants a separate `VoiceCloningEngine` class or just `XTTSv2ModelManager.clone_voice()`.
   - Recommendation: Treat `XTTSv2ModelManager.clone_voice()` as the target. No new class needed unless the planner determines a refactor is warranted.

---

## Sources

### Primary (HIGH confidence)
- GitHub: https://github.com/elevenlabs/elevenlabs-python — SDK README, method signatures
- GitHub Wiki: https://github.com/elevenlabs/elevenlabs-python/wiki/v2-upgrade-guide — v2 breaking changes (generate() removed)
- HuggingFace: https://huggingface.co/coqui/XTTS-v2 — model name, usage examples, 24 kHz sample rate
- GitHub: https://github.com/coqui-ai/TTS/blob/dev/docs/source/models/xtts.md — `get_conditioning_latents()` signature, `inference()` parameters
- PyPI: https://pypi.org/project/elevenlabs/ — version 2.40.0 confirmed
- PyPI: https://pypi.org/project/TTS/ — version 0.22.0 confirmed

### Secondary (MEDIUM confidence)
- Search results confirming ElevenLabs v2 API: `text_to_speech.convert()` pattern
- Search results confirming XTTS-v2 `get_conditioning_latents()` return type: `(gpt_cond_latent, speaker_embedding)` tuple

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed from PyPI directly
- Architecture: HIGH — ElevenLabs verified from SDK README + v2 upgrade guide; XTTS-v2 verified from official Coqui docs
- Pitfalls: HIGH — v2 breaking change confirmed; syntax error in tts_streaming.py observed in source code directly
- `get_conditioning_latents()` signature: HIGH — confirmed from both HuggingFace model card and coqui-ai/TTS docs/xtts.md

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (ElevenLabs moves fast; re-verify SDK version in 30 days)

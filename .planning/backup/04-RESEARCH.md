# Phase 4: TTS - Research

**Researched:** 2026-03-28
**Domain:** Text-to-Speech synthesis — ElevenLabs Python SDK (cloud) + XTTS-v2 via Coqui TTS library (self-hosted)
**Confidence:** HIGH (stack decisions are locked; API surfaces verified against PyPI, GitHub, HuggingFace)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase. Constraints are sourced from STATE.md decisions log and ROADMAP.md locked plan structure.

### Locked Decisions (from STATE.md + ROADMAP.md)
- ElevenLabs SDK for TTS primary path (ELEVENLABS_API_KEY already in .env.example)
- XTTS-v2 self-hosted path via the `TTS` (Coqui) library as secondary/fallback
- `XTTSv2ModelManager` class name is fixed (referenced in success criteria and plan names)
- `VoiceCloningEngine.clone_voice()` must call real `get_conditioning_latents()` — not a simulated call
- Streaming must wire into the existing `tts_streaming.py` file (not a replacement file)
- End-to-end test: audio in → STT → LLM → TTS → audio bytes out must pass (TTS-05)
- Plans are fixed: 04-01, 04-02, 04-03 (no restructuring)

### Claude's Discretion
- How to guard heavy XTTS-v2 import (try/except pattern, matching the STT phase precedent)
- Whether `VoiceCloningEngine` is a new class in `tts_agent.py` or a standalone module
- Exact test structure: xfail stubs or direct unit tests for Wave 0
- How to handle `torch`/`TTS` not being installed in venv yet (try/except guard at module level)
- Whether ElevenLabs `convert()` returns raw bytes or an iterator — handle both

### Deferred Ideas (OUT OF SCOPE)
- MeloTTS and NVIDIA Parakeet alternatives (already stubbed in tts_agent.py, not a Phase 4 target)
- Emotion modulation via audio DSP — the existing `AudioProcessor` class handles post-synthesis modulation; Phase 4 does not need to change it
- WebSocket server start/stop lifecycle — TTSWebSocketStreamer exists; Phase 4 only wires synthesis into it
- MP3/OGG/WebM encoding (tts_streaming.py already stubs these as WAV fallbacks)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TTS-01 | `XTTSv2ModelManager.synthesize()` calls ElevenLabs SDK (not sine-wave) | ElevenLabs SDK `text_to_speech.convert()` + `.stream()` API verified — replaces the mock sine-wave generator in `XTTSv2ModelManager.synthesize()` |
| TTS-02 | XTTS-v2 via `TTS` library available as self-hosted path | Coqui `TTS` 0.22.0 is the latest; `TTS.tts.models.xtts.Xtts` is importable; must be guarded with try/except because TTS+torch are heavy deps not yet installed |
| TTS-03 | `VoiceCloningEngine.clone_voice()` uses real speaker embedding (`get_conditioning_latents()`) | `Xtts.get_conditioning_latents(audio_path, ...)` returns `(gpt_cond_latent, speaker_embedding)` — documented in Coqui TTS 0.22.0 source |
| TTS-04 | Streaming chunks wired into `tts_streaming.py` for WebSocket delivery | `TTSStreamingManager.synthesize_and_stream()` already exists; replace the mock `TTSAgent.synthesize_text()` call it depends on with real ElevenLabs output |
| TTS-05 | End-to-end pipeline test passes: audio in → STT → LLM → TTS → audio bytes out | `processing_pipeline.py._process_tts()` is a stub returning `MOCK_AUDIO_DATA_`; must be replaced with real `TTSAgent.synthesize_text()` call |
</phase_requirements>

---

## Summary

Phase 4 replaces two mock implementations with real TTS synthesis:

1. **`XTTSv2ModelManager.synthesize()`** — currently generates a sine-wave; must be replaced with an ElevenLabs SDK call (`client.text_to_speech.convert()`) that returns real audio bytes. The class name is misleading (it says XTTS but the primary path is ElevenLabs); the plan must add an ElevenLabs client inside this class without renaming it (the success criteria references the exact class name).

2. **`VoiceCloningEngine`** — does not exist yet. Must be created (likely inside `tts_agent.py`) with a `clone_voice()` method that calls `model.get_conditioning_latents()` from the Coqui `TTS` library's `Xtts` class.

3. **`processing_pipeline.py._process_tts()`** — stub returning `b"MOCK_AUDIO_DATA_..."` must be replaced with a real call to `TTSAgent.synthesize_text()`.

4. **`tts_streaming.py`** — the streaming infrastructure is complete but depends on `TTSAgent.synthesize_text()` which is backed by the mock. Once the mock is replaced, streaming works without further changes to `tts_streaming.py`.

**Primary recommendation:** Install `elevenlabs>=2.40.0` for TTS-01/TTS-04/TTS-05. Install `TTS>=0.22.0` (with `torch>=2.0.0`) in the venv for TTS-02/TTS-03, guarded with try/except at module level so tests can still import without GPU/model. Gate real XTTS-v2 tests behind `pytest.importorskip("TTS")`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `elevenlabs` | 2.40.0 (latest) | Cloud TTS via ElevenLabs API | Locked decision; ELEVENLABS_API_KEY already in .env.example; 29+ language support |
| `TTS` (Coqui) | 0.22.0 (latest) | Self-hosted XTTS-v2 path | Locked decision; only library that exposes `get_conditioning_latents()` on XTTS-v2 |
| `torch` | >=2.0.0 | Required by both TTS and tts_agent.py | Already in requirements.txt; required by XTTS-v2 |
| `torchaudio` | >=2.0.0 | Audio resampling in `AudioProcessor` | Already in requirements.txt; used by existing code |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | >=1.24.0 (installed: 2.4.3) | Audio array manipulation | Already installed; used in tts_agent.py |
| `scipy` | >=1.10.0 (installed: 1.17.1) | Audio signal processing | Already installed |
| `websockets` | >=11.0.0 (installed: 16.0) | WebSocket streaming transport | Already installed; used in tts_streaming.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ElevenLabs SDK | OpenAI TTS, Google TTS | ElevenLabs locked by user decision |
| Coqui TTS | bark, pyttsx3, edge-tts | Coqui TTS locked; only one with `get_conditioning_latents()` API |

**Version verification (confirmed 2026-03-28):**
```bash
pip index versions elevenlabs  # Latest: 2.40.0
pip index versions TTS          # Latest: 0.22.0
```

**Installation:**
```bash
pip install elevenlabs>=2.40.0
pip install TTS>=0.22.0  # Installs torch if not present; heavy (~2GB)
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 4 changes)

```
src/agents/
├── tts_agent.py          # XTTSv2ModelManager (add ElevenLabs client + VoiceCloningEngine class)
└── tts_streaming.py      # No changes needed — depends on TTSAgent which is being fixed

src/core/
└── processing_pipeline.py  # Replace _process_tts() stub with real TTSAgent call

tests/
├── test_tts_phase4.py    # Wave 0: xfail stubs for TTS-01 through TTS-05
└── test_pipeline_e2e.py  # E2E test: audio → STT → LLM → TTS (TTS-05)
```

### Pattern 1: ElevenLabs SDK synthesis in XTTSv2ModelManager

**What:** Replace the sine-wave generator with ElevenLabs `text_to_speech.convert()`. The client is initialized once at model load time from the `ELEVENLABS_API_KEY` env var.

**When to use:** Primary synthesis path when `ELEVENLABS_API_KEY` is set.

```python
# Source: github.com/elevenlabs/elevenlabs-python README
from elevenlabs.client import ElevenLabs
import os

class XTTSv2ModelManager:
    async def _load_model(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if api_key:
            self._elevenlabs_client = ElevenLabs(api_key=api_key)
            self.model_loaded = True
        else:
            raise RuntimeError("ELEVENLABS_API_KEY not set")

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        # ElevenLabs path — returns Iterator[bytes]
        audio_iter = self._elevenlabs_client.text_to_speech.convert(
            text=request.text,
            voice_id=self._get_elevenlabs_voice_id(request.voice_id),
            model_id="eleven_multilingual_v2",
            output_format="pcm_22050",  # raw PCM at 22050Hz matches existing sample_rate
        )
        audio_bytes = b"".join(chunk for chunk in audio_iter if isinstance(chunk, bytes))
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
        # ... build SynthesisResult
```

### Pattern 2: ElevenLabs streaming (for tts_streaming.py wiring)

**What:** Use `text_to_speech.stream()` to get chunks as they are generated.

```python
# Source: github.com/elevenlabs/elevenlabs-python README
audio_stream = client.text_to_speech.stream(
    text=request.text,
    voice_id=voice_id,
    model_id="eleven_multilingual_v2",
)
for chunk in audio_stream:
    if isinstance(chunk, bytes):
        yield chunk   # async generator yields raw bytes to WebSocket
```

### Pattern 3: XTTS-v2 self-hosted with guarded import

**What:** Lazy-import `TTS` library behind try/except so the module is importable even when TTS/torch is not installed (matching the `stt_agent.py` precedent from Phase 2).

```python
# Matching STT phase pattern from Phase 02 decision log
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
```

### Pattern 4: VoiceCloningEngine using get_conditioning_latents

**What:** New class that wraps Xtts model's `get_conditioning_latents()` to extract speaker embeddings from reference audio.

```python
# Source: github.com/coqui-ai/TTS XTTS-v2 source (verified in xtts.py)
class VoiceCloningEngine:
    def __init__(self, model: "Xtts"):
        self._model = model

    def clone_voice(self, audio_path: str, gpt_cond_len: int = 30) -> dict:
        """Returns voice embedding using real get_conditioning_latents()."""
        gpt_cond_latent, speaker_embedding = self._model.get_conditioning_latents(
            audio_path=[audio_path],
            gpt_cond_len=gpt_cond_len,
            max_ref_length=60,
        )
        return {
            "gpt_cond_latent": gpt_cond_latent,
            "speaker_embedding": speaker_embedding,
        }
```

### Pattern 5: Replace processing_pipeline._process_tts stub

**What:** The `ProcessingPipeline._process_tts()` method returns `b"MOCK_AUDIO_DATA_..."`. Replace with injection of a real `TTSAgent` instance.

```python
class ProcessingPipeline:
    def __init__(self, config=None, tts_agent=None):
        self._tts_agent = tts_agent  # inject at construction

    async def _process_tts(self, text: str, context: ProcessingContext):
        if self._tts_agent is None:
            raise RuntimeError("No TTS agent configured")
        result = await self._tts_agent.synthesize_text(
            text=text, language=context.language or "en"
        )
        # result.audio_data is np.ndarray; convert to bytes for pipeline output
        audio_bytes = (result.audio_data * 32767).astype(np.int16).tobytes()
        return audio_bytes, 0.95
```

### Anti-Patterns to Avoid

- **Hardcoding ElevenLabs voice IDs:** Map project voice model IDs (e.g., `"en_us_female_1"`) to ElevenLabs voice IDs via a config dict, not inline strings
- **Calling TTS.api.TTS.tts() for voice cloning validation:** The `TTS` high-level API is fine for simple synthesis but `get_conditioning_latents()` requires the low-level `Xtts` class directly
- **Not guarding `import torch` / `import TTS`:** The existing `tts_agent.py` has `import torch` at the top level with no guard — this causes the test collection failure seen in `pytest --collect-only`. Phase 4 must add the try/except guard (matching stt_agent.py pattern)
- **Assuming ElevenLabs `convert()` returns `bytes`:** It returns an `Iterator[bytes]`. Must join chunks: `b"".join(chunk for chunk in result if isinstance(chunk, bytes))`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text-to-speech synthesis | Custom HTTP calls to ElevenLabs REST API | `elevenlabs` SDK `text_to_speech.convert()` | SDK handles auth, retries, rate limits, streaming framing |
| Audio streaming chunks | Manual WebSocket framing of numpy arrays | Existing `AudioChunker` in `tts_streaming.py` | Already implemented with fade in/out, latency optimization |
| XTTS-v2 inference | Direct HuggingFace model loading | `TTS.tts.models.xtts.Xtts.init_from_config()` + `load_checkpoint()` | Official loading path; avoids config schema mismatches |
| Speaker embedding extraction | Hand-compute XTTS conditioning vectors | `model.get_conditioning_latents(audio_path=[...])` | This is the exact method name in the success criteria |
| Voice ID mapping | Build a custom voice registry service | Simple dict in `XTTSv2ModelManager.__init__` | Voice models are already defined in `VoiceModel` dataclasses |

**Key insight:** Both ElevenLabs SDK and Coqui TTS abstract away the most complex parts (API auth, model checkpointing, conditioning latent math). Custom implementations would miss edge cases around PCM format, sample rate negotiation, and multi-language tokenization.

---

## Common Pitfalls

### Pitfall 1: torch/TTS import at module top level crashes pytest collection
**What goes wrong:** `tts_agent.py` has `import torch` and `import torchaudio` at the top (lines 9-10). Since neither is installed in the venv, `pytest --collect-only` fails with `ModuleNotFoundError: No module named 'torch'`. This was confirmed by running `pytest tests/test_tts_agent.py --collect-only`.
**Why it happens:** Heavy ML libraries are not installed in the lean CI venv.
**How to avoid:** Add a try/except guard at the top of `tts_agent.py` matching the pattern established in Phase 2 for `stt_agent.py`:
```python
try:
    import torch
    import torchaudio
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
```
Then gate any code using `torch` behind `if _TORCH_AVAILABLE:`.
**Warning signs:** `pytest --collect-only` shows `ImportError` on `tts_agent.py`

### Pitfall 2: ElevenLabs SDK major API break between v1 and v2
**What goes wrong:** The `elevenlabs` package has a hard break at v2.0.0. Pre-v2 used `generate(text=..., voice=...)`. v2+ uses `client.text_to_speech.convert(text=..., voice_id=..., model_id=...)`.
**Why it happens:** SDK was rewritten in v2 to match ElevenLabs' fanned-out API surface.
**How to avoid:** Always use v2.x SDK pattern with `ElevenLabs(api_key=...)` client instantiation.
**Warning signs:** `AttributeError: module 'elevenlabs' has no attribute 'generate'`

### Pitfall 3: ElevenLabs output format mismatch with existing audio pipeline
**What goes wrong:** The existing `SynthesisResult.audio_data` is `np.ndarray` (float32, 22050Hz). ElevenLabs default output is MP3 at 44100Hz. If you convert blindly, the dtype and sample rate assumptions throughout `AudioProcessor` and `TTSStreamingManager` break.
**Why it happens:** Default `output_format="mp3_44100_128"` is convenient but wrong for this pipeline.
**How to avoid:** Use `output_format="pcm_22050"` (22050Hz raw PCM signed 16-bit) which matches `StreamingConfig.sample_rate = 22050`. Then convert: `np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0`.
**Warning signs:** `wave.Error: file does not start with RIFF id` or distorted audio playback

### Pitfall 4: XTTS-v2 model download on first import (500MB+)
**What goes wrong:** Calling `TTS("tts_models/multilingual/multi-dataset/xtts_v2")` triggers a 500MB+ model download to `~/.local/share/tts/` on first run. In CI this fails silently or takes minutes.
**Why it happens:** Coqui TTS auto-downloads models on first use.
**How to avoid:** Gate XTTS-v2 tests behind `pytest.importorskip("TTS")` AND check for `XTTS_MODEL_PATH` env var. The test should be marked `@pytest.mark.skipif(not os.getenv("XTTS_MODEL_PATH"), reason="XTTS model not available")`.
**Warning signs:** Test hangs for minutes, then fails with download/disk space error

### Pitfall 5: VoiceCloningEngine.clone_voice() calling the wrong method
**What goes wrong:** The success criteria says "using real `get_conditioning_latents()`". The Coqui TTS high-level API (`TTS.api.TTS`) does not expose this method directly — it's on the lower-level `Xtts` model object.
**Why it happens:** `from TTS.api import TTS` gives a high-level wrapper; `from TTS.tts.models.xtts import Xtts` gives the class with `get_conditioning_latents()`.
**How to avoid:** `VoiceCloningEngine` must hold a reference to the `Xtts` instance, not the `TTS` wrapper.

### Pitfall 6: processing_pipeline.py has no TTSAgent dependency injection
**What goes wrong:** `ProcessingPipeline.__init__` currently takes only `config=None`. Injecting a real TTS agent requires modifying the constructor signature.
**Why it happens:** Pipeline was designed as a self-contained stub with no external agent references.
**How to avoid:** Add `tts_agent=None` parameter to `__init__`. Existing callers pass no argument — `None` falls back to error or stub behavior.

---

## Code Examples

Verified patterns from official sources:

### ElevenLabs: Non-streaming synthesis (returns bytes)
```python
# Source: github.com/elevenlabs/elevenlabs-python README (verified 2026-03-28)
from elevenlabs.client import ElevenLabs
import os

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

audio_iter = client.text_to_speech.convert(
    text="Hello world",
    voice_id="JBFqnCBsd6RMkjVDRZzb",      # Rachel voice
    model_id="eleven_multilingual_v2",
    output_format="pcm_22050",               # 22050Hz signed 16-bit PCM
)
audio_bytes: bytes = b"".join(
    chunk for chunk in audio_iter if isinstance(chunk, bytes)
)
```

### ElevenLabs: Streaming synthesis (yields bytes chunks)
```python
# Source: github.com/elevenlabs/elevenlabs-python README (verified 2026-03-28)
audio_stream = client.text_to_speech.stream(
    text="Hello world",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
)
for chunk in audio_stream:
    if isinstance(chunk, bytes):
        yield chunk  # real-time WebSocket delivery
```

### XTTS-v2: Low-level model loading and inference
```python
# Source: huggingface.co/coqui/XTTS-v2 model card (verified 2026-03-28)
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

config = XttsConfig()
config.load_json("/path/to/xtts_v2/config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="/path/to/xtts_v2/", eval=True)
model.cuda()  # or model.cpu()

outputs = model.inference(
    text="Hello world",
    language="en",
    gpt_cond_latent=gpt_cond_latent,    # from get_conditioning_latents
    speaker_embedding=speaker_embedding,  # from get_conditioning_latents
)
wav: list = outputs["wav"]
```

### XTTS-v2: get_conditioning_latents (voice cloning entry point)
```python
# Source: github.com/coqui-ai/TTS xtts.py (verified 2026-03-28)
gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
    audio_path=["path/to/speaker.wav"],   # list of paths
    max_ref_length=30,
    gpt_cond_len=6,
    gpt_cond_chunk_len=6,
)
# Returns: gpt_cond_latent shaped [1, 1024, T], speaker_embedding shaped [512]
```

### XTTS-v2: Streaming synthesis
```python
# Source: baseten.co/blog/streaming-real-time-text-to-speech-with-xtts-v2 (verified 2026-03-28)
streamer = model.inference_stream(
    text,
    language,
    gpt_cond_latent,
    speaker_embedding,
    stream_chunk_size=20,
    enable_text_splitting=True,
)
for chunk in streamer:
    audio_bytes = (chunk.cpu().numpy() * 32767).astype(np.int16).tobytes()
    yield audio_bytes
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `elevenlabs.generate(text=..., voice=...)` | `client.text_to_speech.convert(text=..., voice_id=..., model_id=...)` | v2.0.0 (2024) | All pre-v2 examples are broken |
| Coqui TTS 0.x XTTS API | `Xtts.init_from_config()` + `load_checkpoint()` | 0.22.0 (stable) | Low-level API is stable |
| ElevenLabs eleven_monolingual_v1 | `eleven_multilingual_v2` / `eleven_flash_v2_5` | 2024 | multilingual_v2 is recommended default; flash_v2_5 for lowest latency |
| TTS streaming with post-synthesis chunking | `model.inference_stream()` for real-time chunk generation | XTTS-v2 release | Enables <200ms first-chunk latency vs full synthesis |

**Deprecated/outdated:**
- `elevenlabs.generate()` function: removed in v2.0.0; use `client.text_to_speech.convert()`
- XTTS-v1: superseded by XTTS-v2 with 17 language support vs 13

---

## Open Questions

1. **VoiceCloningEngine placement**
   - What we know: The class doesn't exist yet; success criteria requires `VoiceCloningEngine.clone_voice()` returning a voice embedding
   - What's unclear: Whether it should be a new class inside `tts_agent.py` or a separate module
   - Recommendation: Add as a class inside `tts_agent.py` to avoid import cycle complications (it needs `Xtts` which is guarded by `_TTS_AVAILABLE`)

2. **ElevenLabs voice ID mapping**
   - What we know: Existing `VoiceModel` objects use IDs like `"en_us_female_1"`, `"en_gb_male_1"`. ElevenLabs uses UUIDs like `"JBFqnCBsd6RMkjVDRZzb"`.
   - What's unclear: Whether to hardcode a mapping dict or make it configurable per env var.
   - Recommendation: Add a `ELEVENLABS_VOICE_MAP` dict in `XTTSv2ModelManager.__init__`. If a voice_id is not in the map, fall back to a default voice ID from env var `ELEVENLABS_DEFAULT_VOICE_ID`.

3. **XTTS-v2 model location in CI**
   - What we know: Model download is ~500MB; CI likely doesn't have it.
   - What's unclear: Whether the project has any CI infrastructure yet.
   - Recommendation: Mark XTTS-v2 tests with `@pytest.mark.skipif(not os.getenv("XTTS_MODEL_PATH"), reason="XTTS model not available locally")`. Tests pass in CI by skipping; pass locally when model is pre-downloaded.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `elevenlabs` Python SDK | TTS-01, TTS-04 | Not in venv (must install) | 2.40.0 available on PyPI | None — required for primary path |
| `TTS` (Coqui) library | TTS-02, TTS-03 | Not in venv (must install) | 0.22.0 available on PyPI | Skip XTTS tests in CI |
| `torch` | TTS-02, TTS-03, existing tts_agent.py | Not in venv (must install) | 2.x available | try/except guard |
| `torchaudio` | tts_agent.py AudioProcessor | Not in venv (must install) | 2.x available | try/except guard |
| `numpy` | Audio array conversion | Installed (2.4.3) | 2.4.3 | — |
| `scipy` | Signal processing | Installed (1.17.1) | 1.17.1 | — |
| `websockets` | tts_streaming.py | Installed (16.0) | 16.0 | — |
| `ELEVENLABS_API_KEY` | TTS-01 synthesis | In .env.example; runtime only | — | Tests use pytest.mark.skip if absent |
| Python | All | 3.14.3 | 3.14.3 | — |

**Missing dependencies with no fallback:**
- `elevenlabs` — required for TTS-01, TTS-04, TTS-05; plan 04-01 must install it

**Missing dependencies with fallback:**
- `torch`, `torchaudio`, `TTS` — required for TTS-02, TTS-03; plan 04-02 must install them; tests skipped in CI without model files

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `kiro/voiquyr/pytest.ini` (asyncio_mode=auto) |
| Quick run command | `pytest tests/test_tts_phase4.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TTS-01 | `XTTSv2ModelManager.synthesize("Hello world")` returns real audio bytes | unit (mocked ElevenLabs client) | `pytest tests/test_tts_phase4.py::test_elevenlabs_synthesis -x` | No — Wave 0 |
| TTS-02 | `TTS` library importable and XTTS-v2 callable | unit (import check + skip guard) | `pytest tests/test_tts_phase4.py::test_xtts_import -x` | No — Wave 0 |
| TTS-03 | `VoiceCloningEngine.clone_voice()` returns embedding dict | unit (mocked `get_conditioning_latents`) | `pytest tests/test_tts_phase4.py::test_voice_cloning -x` | No — Wave 0 |
| TTS-04 | Streaming chunks delivered via `TTSStreamingManager` | unit (async generator from mock TTS) | `pytest tests/test_tts_phase4.py::test_tts_streaming -x` | No — Wave 0 |
| TTS-05 | E2E: audio in → STT → LLM → TTS → audio bytes out | integration (mock STT+LLM, real TTS call or mock) | `pytest tests/test_tts_phase4.py::test_e2e_pipeline -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_tts_phase4.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tts_phase4.py` — covers TTS-01 through TTS-05 with xfail stubs matching Phase 2 pattern
- [ ] Fix `tts_agent.py` top-level `import torch` — add try/except guard so test collection no longer fails

*(Existing `tests/test_tts_agent.py`, `test_tts_simple.py`, `test_tts_streaming.py`, `test_tts_streaming_simple.py` exist but are ad-hoc script-style tests, not pytest-collected. The new `test_tts_phase4.py` must use proper `def test_*` conventions with xfail stubs.)*

---

## Sources

### Primary (HIGH confidence)
- `github.com/elevenlabs/elevenlabs-python` README — `text_to_speech.convert()` and `.stream()` API, model IDs
- `github.com/coqui-ai/TTS` xtts.py source — `get_conditioning_latents()` and `inference_stream()` signatures
- `huggingface.co/coqui/XTTS-v2` model card — loading pattern, supported languages, 24kHz sample rate
- PyPI: `pip index versions elevenlabs` — confirmed 2.40.0 is latest (2026-03-28)
- PyPI: `pip index versions TTS` — confirmed 0.22.0 is latest (2026-03-28)
- Project venv inspection (`kiro/voiquyr/.venv/bin/pip list`) — confirmed `torch`, `elevenlabs`, `TTS` are NOT installed

### Secondary (MEDIUM confidence)
- `baseten.co/blog/streaming-real-time-text-to-speech-with-xtts-v2` — `inference_stream()` chunking pattern, wav_postprocess
- Multiple WebSearch results corroborating `get_conditioning_latents()` signature

### Tertiary (LOW confidence)
- None

---

## Project Constraints (from CLAUDE.md)

Directives from `kiro/voiquyr/CLAUDE.md` and `.claude/rules/` that constrain Phase 4 implementation:

| Directive | Source | Impact on Phase 4 |
|-----------|--------|-------------------|
| MANY SMALL FILES — 200-400 lines typical, 800 max | coding-style.md | `tts_agent.py` is already >800 lines (24721 tokens). `VoiceCloningEngine` could be extracted to a new file if size grows further. |
| ALWAYS handle errors explicitly at every level | coding-style.md | ElevenLabs API calls must handle `elevenlabs.core.ApiError` (rate limit, auth) and XTTS failures; never silently swallow |
| ALWAYS use immutable patterns | coding-style.md | `SynthesisResult` and `VoiceCloneResult` are dataclasses — create new instances, never mutate |
| No hardcoded secrets | security.md | `ELEVENLABS_API_KEY` must come from env, never hardcoded |
| TDD: write test first (RED) → implement (GREEN) → refactor | testing.md | Wave 0 tests first, then implementation in waves 1/2 |
| Minimum 80% test coverage | testing.md | New code in `XTTSv2ModelManager.synthesize()`, `VoiceCloningEngine.clone_voice()`, and `_process_tts()` needs unit tests |
| `torch`/`torchaudio` guarded with try/except in `stt_agent.py` for lean CI venv importability | STATE.md Phase 02-stt decision | Apply same guard pattern to `tts_agent.py`'s top-level torch imports |
| `pytest.ini`: asyncio_mode=auto — no per-test `@pytest.mark.asyncio` needed | STATE.md Phase 01-00 decision | All async test functions collected automatically |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed against PyPI registry on 2026-03-28
- Architecture: HIGH — confirmed by reading actual source code of tts_agent.py, tts_streaming.py, and processing_pipeline.py
- Pitfalls: HIGH — `import torch` failure confirmed by running `pytest --collect-only` live; ElevenLabs v2 break confirmed by PyPI version history
- XTTS-v2 API: HIGH — method signatures extracted from coqui-ai/TTS GitHub source directly

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (stable APIs; ElevenLabs SDK moves fast so re-verify model IDs if > 30 days)

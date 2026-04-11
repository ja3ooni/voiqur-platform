# Phase 5: Telephony - Research

**Researched:** 2026-04-11
**Domain:** Twilio REST API (aiohttp), Twilio Media Streams WebSocket, aioresponses test mocking
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use existing `TwilioIntegration` class in `src/api/integrations/telephony.py` — do NOT rewrite
- Use existing `aiohttp` via `BaseIntegration._make_request()` — do NOT switch to Twilio Python SDK
- Verify existing methods satisfy TEL-01/TEL-02. If signature mismatch prevents pytest passing, add thin wrapper — do not rewrite
- New file location for Media Streams handler: `src/telephony/twilio_media_stream.py`
- Use Twilio test credentials (`TWILIO_TEST_ACCOUNT_SID` / `TWILIO_TEST_AUTH_TOKEN`) — no charges, no live calls
- STT bridge target: `stt_agent.process_audio_stream()` (accepts `np.ndarray` + `sample_rate`) — μ-law must be decoded before passing

### Claude's Discretion
- Whether TEL-01/TEL-02 need wrapper methods or existing signatures satisfy the requirements
- Exact mocking strategy for TEL-06 (aioresponses vs. Twilio test credentials for live HTTP)
- FastAPI vs. raw `websockets` library for the Media Streams WebSocket endpoint

### Deferred Ideas (OUT OF SCOPE)
- Asterisk/FreeSWITCH/3CX PBX integrations
- VoIP QoS monitoring beyond Twilio
- Human agent handoff (Phase 6+)
- BYOC_Adapter Kamailio production deployment
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEL-01 | `TwilioIntegration.make_call()` makes real HTTP POST to Twilio Calls API | Existing `make_call(to_number, twiml_url)` posts to `{base_url}/Calls.json` — verified. Wrapper or alias needed to satisfy `make_call(to, from_, url)` signature |
| TEL-02 | `TwilioIntegration.send_sms()` makes real HTTP POST to Twilio Messages API | Existing `send_sms(to_number, message)` posts to `{base_url}/Messages.json` — verified. Same signature gap analysis applies |
| TEL-03 | `TwilioIntegration.authenticate()` uses Basic Auth (base64 SID:TOKEN) | `_create_auth_header()` already builds `Basic base64(SID:TOKEN)` — TEL-03 is already implemented |
| TEL-04 | `call_controller.py` handles real-time audio bridging via media streams | Missing: new `src/telephony/twilio_media_stream.py` with FastAPI WebSocket endpoint; see architecture patterns below |
| TEL-05 | SIP trunk provider registry populated with real provider configs | `ProviderRegistry` exists but has no Twilio entry. Need `ProviderType.TWILIO` registration with env-var-backed `ProviderConfig` |
| TEL-06 | `pytest tests/test_telephony_abstraction.py` passes with Twilio test credentials | Currently passes with `MockTelephonyProvider`. Need tests for `TwilioIntegration` with `aioresponses` OR Twilio test credential live calls |
</phase_requirements>

## Summary

Phase 5 is primarily a wiring and gap-filling phase, not a greenfield implementation. The `TwilioIntegration` class already makes real HTTP calls via `aiohttp`. The existing tests (`test_telephony_abstraction.py`) already pass (3/3) using `MockTelephonyProvider`. Three gaps exist:

1. **Signature gap (TEL-01/TEL-02):** The GSD spec requires `make_call(to, from_, url)` and `send_sms(to, from_, body)` where `from_` is passed explicitly. The existing methods take `from_` from `config.phone_number`. Resolution: add thin wrapper methods that accept the GSD signature and call the existing implementation. This is a 5-line change, not a rewrite.

2. **Missing Media Streams WebSocket bridge (TEL-04):** `call_controller.py` is a load-balanced orchestrator — it does not handle WebSocket connections. A new `TwilioMediaStreamHandler` in `src/telephony/twilio_media_stream.py` must accept Twilio's WebSocket connection, decode μ-law audio frames, and pass them to `STTAgent.process_audio_stream()`.

3. **Test gap (TEL-06):** `test_telephony_abstraction.py` uses `MockTelephonyProvider` exclusively. Adding tests for `TwilioIntegration.make_call()` and `send_sms()` using `aioresponses` to intercept the `aiohttp` calls (or using Twilio test credentials for live HTTP) is the correct approach. Both strategies are viable — `aioresponses` is preferred for determinism.

**Primary recommendation:** Add thin wrapper methods for TEL-01/TEL-02, create `twilio_media_stream.py` as a new FastAPI WebSocket endpoint that decodes μ-law and feeds `STTAgent`, register Twilio in `ProviderRegistry` for TEL-05, and add `aioresponses`-based tests for TEL-06.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.8.0 (already in requirements.txt) | HTTP client for Twilio REST API | Already used via `BaseIntegration._make_request()` — do not change |
| fastapi | >=0.104.0 (already in requirements.txt) | WebSocket endpoint for Media Streams | Already used in the project; built-in WebSocket support |
| websockets | >=11.0.0 (already in requirements.txt) | Underlying WebSocket protocol | Transitive dep for FastAPI WebSocket |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aioresponses | 0.7.8 (latest, not yet in requirements.txt) | Mock aiohttp calls in tests | TEL-06: intercept `_make_request()` HTTP calls to Twilio |
| audioop (stdlib) | stdlib (Python ≤3.12) / audioop-lts (3.13+) | μ-law to PCM conversion | TEL-04: decode Twilio's 8kHz μ-law audio before STT |
| numpy | >=1.24.0 (already in requirements.txt) | Convert decoded bytes to float32 array | TEL-04: STTAgent expects `np.ndarray` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aioresponses | Twilio test credentials (live HTTP) | Live credentials hit real Twilio API but are free — deterministic local mocks are faster and don't need network |
| aioresponses | pytest-mock + unittest.mock | Mock at lower level (patch `aiohttp.ClientSession`) — aioresponses is the standard for aiohttp mocking |
| FastAPI WebSocket | raw `websockets` library | FastAPI is already in use; no reason to add another dependency |
| audioop | audioop-lts | audioop removed in Python 3.13. This project runs Python 3.14.3 — MUST use `audioop-lts` |

**Installation (new dependencies only):**
```bash
pip install aioresponses==0.7.8 audioop-lts
```

**Version verification:**
- aioresponses: 0.7.8 (verified on PyPI, released 2025-01-19)
- audioop-lts: provides `audioop` module for Python 3.13+

## Architecture Patterns

### Recommended Project Structure
```
kiro/voiquyr/src/telephony/
├── base.py              # TelephonyProvider interface (existing, do not modify)
├── call_controller.py   # Load-balanced orchestrator (existing, do not modify)
├── provider_registry.py # Registry + global instance (existing, extend)
├── twilio_media_stream.py  # NEW: Twilio Media Streams WebSocket handler
└── ...

kiro/voiquyr/tests/
├── test_telephony_abstraction.py  # Existing (keep, extend with TEL-06 tests)
└── test_twilio_integration.py    # NEW: aioresponses-based tests for make_call/send_sms
```

### Pattern 1: TwilioIntegration Thin Wrapper (TEL-01 / TEL-02)

**What:** Add `make_call(to, from_, url)` and `send_sms(to, from_, body)` as GSD-spec-compatible methods on `TwilioIntegration`. These delegate to the existing private implementation.

**When to use:** When GSD spec signature differs from existing parameter names.

**Example:**
```python
# Source: gap analysis of telephony.py vs CONTEXT.md spec
async def make_call(self, to: str, from_: str, url: str) -> "TwilioCall":
    """GSD-spec-compatible make_call. Delegates to _make_call_impl."""
    # Temporarily set phone_number from from_ if different
    original = self.config.phone_number
    self.config = self.config.model_copy(update={"phone_number": from_})
    try:
        return await self._make_call_internal(to_number=to, twiml_url=url)
    finally:
        self.config = self.config.model_copy(update={"phone_number": original})
```

Note: Since `TwilioConfig` is a Pydantic model, use `model_copy(update=...)` (Pydantic v2) to avoid mutation.

### Pattern 2: Twilio Media Streams WebSocket Handler (TEL-04)

**What:** FastAPI WebSocket endpoint at `/telephony/stream` that accepts Twilio's `wss://` connection, receives JSON messages, decodes base64 μ-law audio, converts to `np.ndarray` at 8kHz, and passes to `STTAgent.process_audio_stream()`.

**When to use:** For the live audio bridge between Twilio calls and the STT pipeline.

**Twilio WebSocket message flow:**
```
1. Twilio connects → sends {"event": "connected", "protocol": "Call", "version": "1.0.0"}
2. Twilio sends   → {"event": "start", "start": {"mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}}
3. Twilio sends   → {"event": "media", "media": {"payload": "<base64-encoded-mulaw-bytes>", "track": "inbound"}}  (repeats)
4. Twilio sends   → {"event": "stop", "stop": {"callSid": "..."}}
```

**Example FastAPI WebSocket endpoint:**
```python
# Source: Twilio Media Streams docs + FastAPI WebSocket pattern
import json, base64, audioop, numpy as np
from fastapi import WebSocket

@router.websocket("/telephony/stream")
async def twilio_media_stream(websocket: WebSocket):
    await websocket.accept()
    stream_sid: str | None = None
    sample_rate = 8000
    audio_buffer: list[bytes] = []

    async for message in websocket.iter_text():
        data = json.loads(message)
        event = data.get("event")

        if event == "connected":
            pass  # protocol handshake, no action needed

        elif event == "start":
            stream_sid = data["start"]["streamSid"]
            sample_rate = data["start"]["mediaFormat"]["sampleRate"]  # always 8000

        elif event == "media":
            if data["media"]["track"] == "inbound":
                mulaw_bytes = base64.b64decode(data["media"]["payload"])
                # Convert μ-law 8kHz → linear PCM 16-bit
                pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)
                # Convert to float32 numpy array
                pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer.append(pcm_array)

        elif event == "stop":
            if audio_buffer:
                full_audio = np.concatenate(audio_buffer)
                # Pass to STT agent
                async for result in stt_agent.process_audio_stream(full_audio, sample_rate):
                    pass  # results handled by downstream pipeline
            break
```

**Important:** `STTAgent.process_audio_stream()` expects `np.ndarray` (float32) + `sample_rate: int`. The STT agent's `AudioPreprocessor` resamples from 8kHz to 16kHz internally — this is handled automatically.

**Alternative (streaming per-chunk):** For lower latency, pass each PCM chunk to the STT pipeline immediately rather than buffering until stop. This requires the STT agent to support incremental input, which the current implementation does via `process_audio_stream()` yielding async results.

### Pattern 3: SIP Trunk Registry with Twilio Provider (TEL-05)

**What:** Register `ProviderType.TWILIO` in the global `ProviderRegistry` with a `ProviderConfig` backed by environment variables.

**When to use:** At application startup, before `CallController` is used.

**Example:**
```python
# Source: provider_registry.py pattern analysis
from src.telephony.provider_registry import get_registry, register_provider
from src.telephony.base import ProviderType, ProviderConfig
import os

def register_twilio_provider() -> None:
    """Register Twilio as a SIP trunk provider in the global registry."""
    config = ProviderConfig(
        provider_id="twilio-primary",
        provider_type=ProviderType.TWILIO,
        name="Twilio (EU Dublin)",
        host="api.twilio.com",
        port=443,
        username=os.environ["TWILIO_ACCOUNT_SID"],
        password=os.environ["TWILIO_AUTH_TOKEN"],
        enabled=True,
        priority=10,
        capabilities=["voice", "sms", "media_streams"],
    )
    # Note: ProviderRegistry.create_provider() requires a registered provider CLASS.
    # Twilio's TelephonyProvider subclass must be created or a stub used for TEL-05.
    registry = get_registry()
    registry.register_provider_class(ProviderType.TWILIO, TwilioTelephonyProvider)
    registry.create_provider(config)
```

**Gap:** `ProviderType.TWILIO` already exists in the `ProviderType` enum in `base.py`. However, there is no `TwilioTelephonyProvider` class implementing `TelephonyProvider` ABC. A minimal implementation (that delegates to `TwilioIntegration`) is needed for TEL-05.

### Pattern 4: aioresponses Test Mocking (TEL-06)

**What:** Use `aioresponses` to intercept `aiohttp.ClientSession.request()` calls within `BaseIntegration._make_request()` and return deterministic Twilio-like responses.

**When to use:** For testing `TwilioIntegration.make_call()`, `send_sms()`, and `authenticate()` without network calls.

**Example:**
```python
# Source: aioresponses 0.7.8 docs (pypi.org/project/aioresponses)
import pytest
from aioresponses import aioresponses as aioresponses_mock

@pytest.fixture
def mock_responses():
    with aioresponses_mock() as m:
        yield m

@pytest.mark.asyncio
async def test_make_call_posts_to_twilio(mock_responses):
    account_sid = "ACtest123"
    auth_token = "test_token"
    mock_responses.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json",
        payload={"sid": "CA123", "status": "queued", "from": "+15005550006", "to": "+15005550009"},
        status=201,
    )
    config = TwilioConfig(
        name="test",
        account_sid=account_sid,
        auth_token=auth_token,
        phone_number="+15005550006",
        eu_region=False,
    )
    integration = TwilioIntegration(config)
    integration._auth_header = integration._create_auth_header()
    result = await integration.make_call(to="+15005550009", from_="+15005550006", url="https://example.com/twiml")
    assert result.sid == "CA123"
```

**Test credentials approach (alternative):** Using real Twilio test credentials (`ACtest...`, `test...`) sends live HTTP to Twilio's sandbox. Test phone number `+15005550006` is Twilio's "valid" magic number for test calls. This requires `TWILIO_TEST_ACCOUNT_SID` and `TWILIO_TEST_AUTH_TOKEN` in the test environment but does NOT incur charges.

### Anti-Patterns to Avoid

- **Switching to Twilio Python SDK:** The codebase uses raw `aiohttp`. The Twilio Python SDK is sync-first and would require `asyncio.to_thread()` wrapping. Do not add it.
- **Patching `aiohttp.ClientSession` with `unittest.mock`:** This is brittle and does not intercept the session correctly. Use `aioresponses` instead.
- **Buffering all audio before STT:** For the WebSocket bridge, buffer-then-process works for TEL-04 correctness but adds latency. Consider per-chunk streaming for production.
- **Mutating `TwilioConfig` in place:** `TwilioConfig` is a Pydantic model. Use `model_copy(update=...)` (Pydantic v2) — not `setattr()` — to avoid shared state bugs.
- **Assuming `audioop` is in stdlib on Python 3.13+:** `audioop` was removed in Python 3.13. This project runs Python 3.14.3. Install `audioop-lts` package.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| μ-law to PCM conversion | Custom bit manipulation | `audioop.ulaw2lin(data, width=2)` (stdlib / audioop-lts) | ITU-T G.711 μ-law is a well-defined standard; audioop handles edge cases correctly |
| aiohttp request mocking | `unittest.mock.patch('aiohttp.ClientSession')` | `aioresponses` library | aioresponses patches at the right level; manual patching often misses the session context manager |
| Base64 decoding | Custom decoder | `base64.b64decode()` (stdlib) | Twilio base64 payload is standard RFC 4648 |
| Twilio Basic Auth | Custom header construction | Already implemented in `_create_auth_header()` | `base64.b64encode(f"{sid}:{token}".encode()).decode()` |

**Key insight:** The entire HTTP and authentication layer is already implemented. The only missing piece at the HTTP level is the method signature alignment.

## Common Pitfalls

### Pitfall 1: audioop Removed in Python 3.13+
**What goes wrong:** `import audioop` raises `ModuleNotFoundError` on Python 3.13+. This project uses Python 3.14.3.
**Why it happens:** audioop was deprecated in Python 3.11 and removed in 3.13 (PEP 594).
**How to avoid:** Add `audioop-lts` to `requirements.txt`. Import with `try: import audioop except ImportError: import audioop_lts as audioop`.
**Warning signs:** `ModuleNotFoundError: No module named 'audioop'` in `twilio_media_stream.py`.

### Pitfall 2: TwilioConfig.eu_region Controls base_url
**What goes wrong:** Tests use `eu_region=True` (the default) which constructs `https://dublin.api.twilio.com/...` instead of `https://api.twilio.com/...`. aioresponses mock URL must match exactly.
**Why it happens:** `TwilioIntegration.__init__` switches base URL based on `eu_region` flag.
**How to avoid:** In tests using aioresponses, set `eu_region=False` to use the standard `api.twilio.com` URL, OR mock the EU URL. In production, keep `eu_region=True`.
**Warning signs:** `ConnectionError` from aioresponses — URL not found in mock registry.

### Pitfall 3: test_telephony_abstraction.py is Not a pytest Module
**What goes wrong:** The existing `test_telephony_abstraction.py` uses `async def test_*()` functions in a non-pytest style (it has an `async def main()` and `if __name__ == "__main__"` pattern). However, when collected by pytest (with `asyncio_mode = auto`), pytest-asyncio treats `async def test_*` as async tests and runs them — they currently pass.
**Why it happens:** The file can be run both standalone (`python test_telephony_abstraction.py`) and as a pytest module.
**How to avoid:** Do NOT add `asyncio.run()` wrappers to existing tests. When adding new TEL-06 tests, add them to a separate file `tests/test_twilio_integration.py` to keep concerns clean.
**Warning signs:** `RuntimeError: This event loop is already running` if asyncio.run() is nested.

### Pitfall 4: STTAgent Requires Initialization Before Processing
**What goes wrong:** Calling `stt_agent.process_audio_stream()` without first calling `await stt_agent.initialize()` raises `RuntimeError: No model loaded` inside `VoxtralModelManager.transcribe()`.
**Why it happens:** `STTAgent.initialize()` loads the model and sets `self.model_manager.current_model`.
**How to avoid:** In `TwilioMediaStreamHandler`, inject a pre-initialized `STTAgent` or call `initialize()` during handler setup. In tests, mock the model manager.
**Warning signs:** `RuntimeError: No model loaded` during WebSocket audio processing.

### Pitfall 5: Twilio Test Credentials Cannot Use Live Phone Numbers as From
**What goes wrong:** Using a real phone number (e.g., from `.env`) as `From` with Twilio test credentials returns `400 Bad Request`.
**Why it happens:** Twilio test credentials require magic phone numbers: `+15005550006` for valid `From`, `+15005550009` for valid `To`.
**How to avoid:** Use `+15005550006` as `From` and `+15005550009` as `To` in all tests using Twilio test credentials. If using aioresponses, this constraint doesn't apply.
**Warning signs:** `HTTP 400: The 'From' number ... is not a valid phone number` in test output.

### Pitfall 6: ProviderRegistry.create_provider() Requires Registered Class
**What goes wrong:** Calling `registry.create_provider(config)` for `ProviderType.TWILIO` without first calling `register_provider_class(ProviderType.TWILIO, SomeClass)` raises `ValueError: Provider type twilio not registered`.
**Why it happens:** The registry pattern requires class registration before instance creation.
**How to avoid:** Create a minimal `TwilioTelephonyProvider(TelephonyProvider)` stub in `twilio_media_stream.py` or a new file. Register it before creating the instance for TEL-05.
**Warning signs:** `ValueError: Provider type twilio not registered`.

## Code Examples

Verified patterns from official sources:

### Twilio Media Streams WebSocket Message Types
```python
# Source: https://www.twilio.com/docs/voice/media-streams/websocket-messages
{
    "event": "connected",
    "protocol": "Call",
    "version": "1.0.0"
}
{
    "event": "start",
    "sequenceNumber": "1",
    "start": {
        "streamSid": "MZ...",
        "accountSid": "AC...",
        "callSid": "CA...",
        "tracks": ["inbound"],
        "customParameters": {},
        "mediaFormat": {
            "encoding": "audio/x-mulaw",
            "sampleRate": 8000,
            "channels": 1
        }
    },
    "streamSid": "MZ..."
}
{
    "event": "media",
    "sequenceNumber": "2",
    "media": {
        "track": "inbound",
        "chunk": "1",
        "timestamp": "5",
        "payload": "<base64-encoded-mulaw-bytes>"
    },
    "streamSid": "MZ..."
}
{
    "event": "stop",
    "sequenceNumber": "100",
    "stop": {
        "accountSid": "AC...",
        "callSid": "CA..."
    },
    "streamSid": "MZ..."
}
```

### μ-law Decoding (Python 3.14+)
```python
# audioop removed in Python 3.13 — use audioop-lts
try:
    import audioop
except ImportError:
    import audioop_lts as audioop  # pip install audioop-lts
import base64, numpy as np

def decode_mulaw_payload(base64_payload: str) -> np.ndarray:
    """Decode Twilio base64 μ-law payload to float32 numpy array at 8kHz."""
    mulaw_bytes = base64.b64decode(base64_payload)
    pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit output
    return np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
```

### TwiML Stream Verb (for initiating Media Streams from a call)
```xml
<!-- Source: https://www.twilio.com/docs/voice/twiml/stream -->
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://your-server.com/telephony/stream" />
    </Connect>
</Response>
```

### aioresponses POST Mock Pattern
```python
# Source: pypi.org/project/aioresponses — version 0.7.8
import pytest
from aioresponses import aioresponses

@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_twilio_make_call(mock_aiohttp):
    mock_aiohttp.post(
        "https://api.twilio.com/2010-04-01/Accounts/ACtest123/Calls.json",
        payload={"sid": "CA456", "status": "queued"},
        status=201,
        content_type="application/json",
    )
    # ... call TwilioIntegration.make_call() and assert result.sid == "CA456"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Twilio Python SDK (sync) | Raw aiohttp (async) | Already in codebase | SDK would block event loop; aiohttp is correct for async FastAPI |
| audioop (stdlib) | audioop-lts (pip package) | Python 3.13 removed audioop | Must add audioop-lts to requirements.txt for Python 3.13+ |
| Flask + gevent for Media Streams | FastAPI + asyncio WebSocket | 2023+ community practice | FastAPI native async is cleaner than gevent-based Flask |

**Deprecated/outdated:**
- `audioop` (stdlib): Removed in Python 3.13. Replace with `audioop-lts` package.
- Twilio Python SDK sync client: Not relevant here — the codebase uses aiohttp directly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.14.3 | — |
| aiohttp | TEL-01/02/03 | ✓ | >=3.8.0 (in requirements.txt) | — |
| fastapi | TEL-04 WebSocket endpoint | ✓ | >=0.104.0 (in requirements.txt) | — |
| pytest / pytest-asyncio | TEL-06 | ✓ | pytest-9.0.2, asyncio-1.3.0 | — |
| aioresponses | TEL-06 mocking | ✗ | — (0.7.8 available on PyPI) | Twilio test credentials (live HTTP) |
| audioop | TEL-04 μ-law decode | ✗ | Removed in Python 3.13 | audioop-lts (pip) |
| audioop-lts | TEL-04 μ-law decode | ✗ | Available on PyPI | — |
| TWILIO_TEST_ACCOUNT_SID | TEL-06 (if using live test creds) | Unknown | — | aioresponses mock (preferred) |
| TWILIO_TEST_AUTH_TOKEN | TEL-06 (if using live test creds) | Unknown | — | aioresponses mock (preferred) |

**Missing dependencies with no fallback:**
- `audioop-lts`: Required for μ-law decoding on Python 3.13+. Must be installed.

**Missing dependencies with fallback:**
- `aioresponses`: Preferred for deterministic testing. Fallback is Twilio test credentials (live HTTP, no charges). Recommendation: use aioresponses.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `kiro/voiquyr/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command | `pytest tests/test_telephony_abstraction.py tests/test_twilio_integration.py -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEL-01 | `make_call(to, from_, url)` POSTs to Calls.json and returns call SID | unit | `pytest tests/test_twilio_integration.py::test_make_call_posts_to_calls_endpoint -x` | ❌ Wave 0 |
| TEL-02 | `send_sms(to, from_, body)` POSTs to Messages.json and returns message SID | unit | `pytest tests/test_twilio_integration.py::test_send_sms_posts_to_messages_endpoint -x` | ❌ Wave 0 |
| TEL-03 | `authenticate()` constructs correct Basic Auth header | unit | `pytest tests/test_twilio_integration.py::test_authenticate_basic_auth_header -x` | ❌ Wave 0 |
| TEL-04 | WebSocket endpoint receives μ-law frames and passes to STT agent | integration | `pytest tests/test_twilio_integration.py::test_media_stream_audio_bridge -x` | ❌ Wave 0 |
| TEL-05 | ProviderRegistry contains Twilio entry after registration | unit | `pytest tests/test_twilio_integration.py::test_twilio_provider_registered -x` | ❌ Wave 0 |
| TEL-06 | `test_telephony_abstraction.py` passes (already passes — keep green) | unit | `pytest tests/test_telephony_abstraction.py -v` | ✅ Exists (passing) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_telephony_abstraction.py -v` (existing, always green)
- **Per wave merge:** `pytest tests/test_telephony_abstraction.py tests/test_twilio_integration.py -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_twilio_integration.py` — covers TEL-01, TEL-02, TEL-03, TEL-04, TEL-05
- [ ] `aioresponses==0.7.8` added to `requirements.txt`
- [ ] `audioop-lts` added to `requirements.txt`
- [ ] `src/telephony/twilio_media_stream.py` — new file for TEL-04

## Open Questions

1. **TEL-04: Streaming vs. buffered STT**
   - What we know: `STTAgent.process_audio_stream()` is an async generator that yields `TranscriptionResult` per chunk
   - What's unclear: Whether the Media Streams handler should buffer all audio until the `stop` event (simpler) or stream chunks incrementally (lower latency but requires the STT agent to be initialized and running concurrently)
   - Recommendation: Buffer approach for TEL-04 correctness; note streaming as a TEL-04 enhancement path

2. **TEL-05: TwilioTelephonyProvider concrete class scope**
   - What we know: `ProviderRegistry.create_provider()` requires a `TelephonyProvider` subclass registered for `ProviderType.TWILIO`
   - What's unclear: How minimal the stub needs to be — TEL-05 only requires "registry populated with real provider configs", not that the provider can actually make calls through the registry (that's via `TwilioIntegration` directly)
   - Recommendation: Create a minimal `TwilioTelephonyProvider` that delegates `make_call()` / `health_check()` to `TwilioIntegration` internally

3. **TEL-06: Whether to add Twilio test credential env vars to pytest env**
   - What we know: Twilio test credentials (`ACtest...`, `test...`) hit real Twilio sandbox without charges
   - What's unclear: Whether CI environment will have these vars set
   - Recommendation: Use `aioresponses` as primary strategy (no env vars needed). If Twilio test credentials are available, they can be used as an additional integration test layer.

## Sources

### Primary (HIGH confidence)
- [Twilio Media Streams WebSocket Messages](https://www.twilio.com/docs/voice/media-streams/websocket-messages) — connected/start/media/stop event schemas, μ-law 8kHz format
- [Twilio TwiML Stream Verb](https://www.twilio.com/docs/voice/twiml/stream) — `<Connect><Stream>` vs `<Start><Stream>` patterns
- [Twilio Test Credentials](https://www.twilio.com/docs/iam/test-credentials) — magic phone numbers, supported operations, no-charge guarantee
- [aioresponses on PyPI](https://pypi.org/project/aioresponses/) — version 0.7.8 (2025-01-19), context manager API, POST mocking pattern
- Source code analysis: `telephony.py`, `base.py`, `call_controller.py`, `provider_registry.py`, `base.py`, `stt_agent.py`, `test_telephony_abstraction.py` — all read and verified

### Secondary (MEDIUM confidence)
- [Twilio FastAPI + OpenAI Realtime Blog Post](https://www.twilio.com/en-us/blog/voice-ai-assistant-openai-realtime-api-python) — FastAPI WebSocket endpoint pattern for Media Streams verified against official Twilio docs
- Python 3.13 changelog (audioop removal) — verified by runtime: `python3 --version` returns 3.14.3 on this machine; `import audioop` fails

### Tertiary (LOW confidence)
- audioop-lts PyPI availability assumed based on known Python 3.13+ migration path (not tested locally)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — aiohttp and FastAPI already in codebase; aioresponses on PyPI confirmed
- Architecture: HIGH — Twilio WebSocket message format verified from official docs; existing code patterns read directly
- Pitfalls: HIGH — audioop removal verified by Python version check; eu_region URL switching verified by reading TwilioIntegration source

**Research date:** 2026-04-11
**Valid until:** 2026-07-11 (Twilio Media Streams protocol is stable; aioresponses minor versions may update)

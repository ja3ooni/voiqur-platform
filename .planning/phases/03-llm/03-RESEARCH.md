# Phase 3: LLM - Research

**Researched:** 2026-03-28
**Domain:** Mistral AI Python SDK v2.x — async chat completion, function/tool calling, multi-turn conversation history
**Confidence:** HIGH

## Summary

Phase 3 replaces the mock LLM pipeline in `src/agents/llm_agent.py` with real Mistral API calls. The current `MistralModelManager` class loads a local HuggingFace model via `transformers` (self-hosted inference path) and falls back to `_generate_mock_response()` when that load fails. Neither path calls the Mistral REST API. The goal is to swap the `MistralModelManager.generate_response()` core with a call to `client.chat.complete_async()` from the `mistralai` v2 SDK, wire in the `ConversationContext.get_context_for_model()` history, translate existing `ToolDefinition` objects into Mistral function-calling format, and execute returned tool calls through the existing `ToolExecutor`.

The `mistralai` SDK is already installed (v2.0.4 in `.venv`) and `MISTRAL_API_KEY` exists in `.env`. The STT phase (Phase 2) already uses `from mistralai import Mistral` and `asyncio.to_thread(client.audio.transcriptions.complete, ...)`, establishing the pattern of wrapping the sync SDK in a thread executor. For Phase 3 the async method `client.chat.complete_async()` is available and preferred.

**Primary recommendation:** Replace `MistralModelManager` internals to use `from mistralai import Mistral; client.chat.complete_async()`. Keep all surrounding session/tool/dialog infrastructure; only swap the inference layer. Remove `_generate_mock_response()` entirely.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | `_load_mistral_small_31()` uses real `mistralai` SDK (`MistralClient.chat()`) | SDK v2.x installed; `client.chat.complete_async()` is the correct method |
| LLM-02 | `_generate_mock_response()` removed — all generation through real API | Mock is a method on `MistralModelManager`; safe to delete after wiring real path |
| LLM-03 | Tool calling uses Mistral function calling format via existing `ToolCaller` | `ToolDefinition.to_openai_function()` already produces compatible JSON schema; wrap in `{"type":"function","function":{...}}` |
| LLM-04 | `ConversationManager` history passed as `messages` list to Mistral | `ConversationContext.get_context_for_model()` returns `[{"role":..,"content":..}]` — pass directly |
| LLM-05 | Multi-turn conversation with tool call execution verified by tests | Integration test: 3-turn conversation with at least one tool call returning a real result |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

**Platform:** `kiro/voiquyr/` is the active directory for this phase.
**Key commands:**
- Run tests: `pytest` (from `kiro/voiquyr/`)
- Single file: `pytest tests/test_llm_agent.py -v`
- Pattern: `pytest -k "test_llm" -v`
- Activate venv: `source .venv/Scripts/activate` (Windows bash) — on macOS activate normally

**Architecture decisions locked from STATE.md:**
- Mistral API for LLM (EU-based provider) — confirmed, do not switch to OpenAI
- `asyncio_mode=auto` in `pytest.ini` — no `@pytest.mark.asyncio` needed per test
- Pydantic v2: use `pattern=` not `regex=` in `Field()`
- JWT library: `import jwt` (PyJWT), not `python-jose`

**Coding constraints (from rules):**
- ALWAYS create new objects, never mutate in-place
- Functions < 50 lines, files < 800 lines
- No hardcoded secrets — `MISTRAL_API_KEY` from env/config only
- Handle all errors explicitly; no silent swallowing
- Validate inputs at system boundaries

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mistralai | 2.0.4 (installed), 2.1.3 (latest on PyPI) | Mistral REST API client | Only official Mistral Python SDK; already in `.venv` and `requirements.txt>=2.0.0` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Async orchestration | All Mistral calls must be async to fit existing `async def` pipeline |
| unittest.mock | stdlib | Patching `Mistral.chat.complete_async` in tests | Avoid real API calls in unit tests; use `AsyncMock` |
| pytest-asyncio | installed | Async test execution | `asyncio_mode=auto` already in `pytest.ini` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mistralai` SDK | `httpx` raw REST | SDK handles auth, retries, response deserialization; no reason to go raw |
| `client.chat.complete_async()` | `asyncio.to_thread(client.chat.complete, ...)` | Native async preferred; `complete_async` exists in v2; sync wrap was only needed in STT because `audio.transcriptions.complete` lacks async variant |

**Installation:** Already installed. To upgrade to latest:
```bash
pip install "mistralai>=2.0.0"
```

**Version verification:**
```
mistralai in venv: 2.0.4 (verified 2026-03-28)
mistralai latest on PyPI: 2.1.3 (published 2026-03-23)
```
The installed 2.0.4 is sufficient; 2.1.3 is available if upgrade needed.

---

## Architecture Patterns

### Current State (what exists)

```
LLMAgent
├── MistralModelManager          ← loads HuggingFace model or falls back to mock
│   ├── load_model()             ← tries AutoModelForCausalLM; falls back to mock dict
│   ├── generate_response()      ← real HF inference OR _generate_mock_response()
│   └── _generate_mock_response()  ← keyword-matching mock (TO DELETE)
├── SessionManager               ← in-memory ConversationContext store (keep)
├── IntentRecognizer             ← keyword-based intent (keep; will be bypassed by real LLM)
├── ToolRegistry + ToolExecutor  ← already wired (keep)
└── process_message()            ← orchestrates all of the above (minimal changes needed)
```

### Target State (after Phase 3)

```
LLMAgent
├── MistralModelManager          ← now calls Mistral REST API
│   ├── _client: Mistral         ← initialized with MISTRAL_API_KEY
│   ├── generate_response()      ← calls client.chat.complete_async(); handles tool_calls in response
│   └── (no _generate_mock_response)
├── SessionManager               ← unchanged
├── IntentRecognizer             ← unchanged (intent detection still used for pre-tool routing)
├── ToolRegistry + ToolExecutor  ← unchanged
└── process_message()            ← adds tool result loop for Mistral tool call flow
```

### Pattern 1: Async Mistral Chat Completion

**What:** Single-turn or multi-turn call using `complete_async`
**When to use:** Every `generate_response()` invocation
**Example:**
```python
# Source: https://deepwiki.com/mistralai/client-python/7.2-asynchronous-operations
from mistralai import Mistral
import os

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

response = await client.chat.complete_async(
    model="mistral-small-latest",
    messages=messages,        # List[{"role": str, "content": str}]
    tools=tools,              # Optional[List[dict]] — Mistral function calling format
    tool_choice="auto",       # "auto" | "any" | "none"
)
content = response.choices[0].message.content
tool_calls = response.choices[0].message.tool_calls  # None or list
```

### Pattern 2: Tool Calling Full Loop

**What:** Detect tool_calls in response, execute, inject results, call again
**When to use:** Any turn where Mistral returns `tool_calls` instead of a text reply

```python
# Source: https://docs.mistral.ai/capabilities/function_calling/
import json

# Step 1: Call Mistral with tools defined
response = await client.chat.complete_async(
    model="mistral-small-latest",
    messages=messages,
    tools=tools,
)

msg = response.choices[0].message

# Step 2: If tool calls present, execute them
if msg.tool_calls:
    # Append the assistant message (with tool_calls) to history
    messages.append({
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": msg.tool_calls,
    })

    for tc in msg.tool_calls:
        fn_name = tc.function.name
        fn_args = json.loads(tc.function.arguments)
        result = await tool_executor.execute_tool_call(fn_name, fn_args)

        # Append tool result
        messages.append({
            "role": "tool",
            "name": fn_name,
            "content": str(result),
            "tool_call_id": tc.id,
        })

    # Step 3: Call Mistral again with tool results in history
    final_response = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=messages,
    )
    return final_response.choices[0].message.content
```

### Pattern 3: Converting ToolDefinition to Mistral Format

**What:** The existing `ToolDefinition.to_openai_function()` returns the `function` inner object. Mistral needs a wrapper with `"type": "function"`.
**When to use:** When building the `tools` list to pass to Mistral

```python
# ToolRegistry already has get_openai_functions() returning List[Dict]
# Each dict is the inner function schema (name, description, parameters)
# Mistral requires wrapping:

def get_mistral_tools(tool_registry: ToolRegistry) -> list:
    return [
        {"type": "function", "function": fn}
        for fn in tool_registry.get_openai_functions()
    ]
```

### Pattern 4: Multi-Turn History — ConversationContext

**What:** `ConversationContext.get_context_for_model()` already returns the right format
**When to use:** Pass as `messages` to every Mistral call

```python
# get_context_for_model() returns:
# [{"role": "user"|"assistant"|"system"|"tool", "content": str}, ...]
messages = context.get_context_for_model()
# Add system prompt as first message if not already present
if system_prompt and (not messages or messages[0]["role"] != "system"):
    messages = [{"role": "system", "content": system_prompt}] + messages
```

### Pattern 5: MistralClient Initialization in MistralModelManager

**What:** Replace the HuggingFace model loading with a lightweight Mistral API client init
**When to use:** In `MistralModelManager.__init__()` or a new `initialize()` method

```python
import os
from mistralai import Mistral

class MistralModelManager:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        self._client = Mistral(api_key=api_key)
        self._model = "mistral-small-latest"
```

### Anti-Patterns to Avoid

- **Keeping `_generate_mock_response`:** LLM-02 requires complete removal. The mock must not remain as a fallback — tests must verify the real API is called.
- **Using `asyncio.to_thread` for chat:** Unlike audio transcriptions, `chat.complete_async()` exists in v2 — use it directly.
- **Mutating the `messages` list from `get_context_for_model()`:** That method returns a new list; appending tool results to `messages` is safe but do not mutate `context.context_window` directly from the tool loop — use `context.add_message()` instead so the session store stays consistent.
- **Not appending the assistant tool_calls message before tool results:** Mistral requires the assistant message with `tool_calls` in history before the `role: "tool"` messages — omitting it causes API errors.
- **Passing `tool_calls` as raw SDK objects:** JSON-serialize or convert to dicts before appending to `messages`; the SDK response objects may not be JSON-serializable directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP calls to Mistral REST | Custom `aiohttp` client | `mistralai` SDK `client.chat.complete_async()` | Auth headers, retry logic, error parsing, response deserialization all handled |
| Tool schema formatting | Custom JSON schema builder | `ToolDefinition.to_openai_function()` already exists | Re-use existing method; just wrap with `{"type": "function"}` |
| Message history management | New conversation store | `ConversationContext.get_context_for_model()` | Already implemented; produces correct `[{role, content}]` format |
| Async test patching | Custom mock | `unittest.mock.AsyncMock` patching `Mistral.chat.complete_async` | Standard Python mock; avoids real API calls in unit tests |

**Key insight:** The surrounding infrastructure (session management, tool registry, dialog turns) is well-built and should not be replaced. Only `MistralModelManager`'s inference backend changes.

---

## Common Pitfalls

### Pitfall 1: SDK Class Name — `Mistral` not `MistralClient`
**What goes wrong:** Requirements say `MistralClient.chat()` but the v2 SDK exports `Mistral`, not `MistralClient`. Using the wrong name causes `ImportError`.
**Why it happens:** The v0.x/v1.x SDK used `MistralClient`; v2 renamed it to `Mistral`.
**How to avoid:** `from mistralai import Mistral` — the stt_agent.py already has this correct.
**Warning signs:** `ImportError: cannot import name 'MistralClient' from 'mistralai'`

### Pitfall 2: Assistant Message Must Include `tool_calls` Before Tool Results
**What goes wrong:** Appending `{"role": "tool", ...}` directly after user message without the intervening assistant message causes a 422 API error.
**Why it happens:** Mistral (and OpenAI-compatible APIs) require the conversation to show: user → assistant (with tool_calls field) → tool (result). Skipping the assistant message breaks the sequence.
**How to avoid:** Always append `messages.append({"role": "assistant", "content": ..., "tool_calls": [...]})` before appending tool result messages.
**Warning signs:** `MistralAPIStatusException: 422 Unprocessable Entity`

### Pitfall 3: `tool_calls` Objects May Not Serialize Directly
**What goes wrong:** SDK returns Pydantic models for `tool_calls`; appending them to a `messages` list then sending back causes type errors or serialization failures.
**Why it happens:** The `complete_async` response contains `ChatCompletionChoice.message.tool_calls` as SDK model objects.
**How to avoid:** Use `response.choices[0].message` directly (the SDK typically accepts its own model objects back as message entries) or convert: `msg.model_dump()` if using Pydantic v2 models.
**Warning signs:** `TypeError: Object of type ToolCall is not JSON serializable` or unexpected API errors.

### Pitfall 4: `MISTRAL_API_KEY` Must Be Loaded Before Client Init
**What goes wrong:** `MistralModelManager.__init__()` may run before `load_dotenv()`, leaving `os.getenv("MISTRAL_API_KEY")` as `None`.
**Why it happens:** `load_dotenv()` is called in `main.py` at module level; test setups may not trigger it.
**How to avoid:** In tests, set `os.environ["MISTRAL_API_KEY"] = "test-key"` before constructing the manager, or read key lazily in `initialize()` rather than `__init__()`. In production, the Phase 1 decision ensures `load_dotenv()` runs at module level in main.py before anything else.
**Warning signs:** `ValueError: MISTRAL_API_KEY environment variable not set`

### Pitfall 5: `torch` Import at Module Top Level Blocks CI
**What goes wrong:** The current `llm_agent.py` has `import torch` at the top. In Phase 3 the self-hosted path is removed, but if torch is not uninstalled, this is fine. If the CI venv is lean (no torch), the import fails before any test runs.
**Why it happens:** The Phase 2 STT agent resolved this with try/except guards. The same pattern is needed if torch stays in llm_agent.py.
**How to avoid:** After replacing the HuggingFace path, remove the top-level `import torch` and `from transformers import ...` lines entirely (they are no longer needed). If any code still references them, wrap with `try/except ImportError`.
**Warning signs:** `ModuleNotFoundError: No module named 'torch'` on collection.

---

## Code Examples

Verified patterns from official sources:

### Basic Async Chat Call
```python
# Source: https://deepwiki.com/mistralai/client-python/7.1-basic-usage-examples
from mistralai import Mistral
import os

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
response = await client.chat.complete_async(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```

### Minimal Unit Test with AsyncMock
```python
# Pattern for tests/test_llm_agent.py — no real API key needed
from unittest.mock import AsyncMock, MagicMock, patch

@patch("src.agents.llm_agent.Mistral")
async def test_real_chat_called(MockMistral):
    mock_client = MagicMock()
    mock_client.chat.complete_async = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mocked reply", tool_calls=None))]
    ))
    MockMistral.return_value = mock_client

    # instantiate MistralModelManager — it will get the mock client
    ...
    assert mock_client.chat.complete_async.called
```

### Multi-Turn Tool Call Integration (3-turn example)
```python
# Source: https://docs.mistral.ai/capabilities/function_calling/
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What time is it?"},
]
response1 = await client.chat.complete_async(
    model="mistral-small-latest", messages=messages, tools=tools
)
# Turn 1: model calls get_current_time tool
messages.append({
    "role": "assistant",
    "content": response1.choices[0].message.content or "",
    "tool_calls": response1.choices[0].message.tool_calls,
})
messages.append({
    "role": "tool", "name": "get_current_time",
    "content": "2026-03-28 14:00:00",
    "tool_call_id": response1.choices[0].message.tool_calls[0].id,
})
response2 = await client.chat.complete_async(
    model="mistral-small-latest", messages=messages
)
# Turn 2: model incorporates tool result
messages.append({"role": "assistant", "content": response2.choices[0].message.content})
messages.append({"role": "user", "content": "And what day is that?"})
response3 = await client.chat.complete_async(
    model="mistral-small-latest", messages=messages
)
assert response3.choices[0].message.content  # non-empty
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `MistralClient` (v0.x class name) | `Mistral` (v1+ class name) | mistralai v1.0.0 | Import path changed |
| `client.chat()` (v0.x) | `client.chat.complete()` / `client.chat.complete_async()` | mistralai v1.0.0 | Method renamed |
| Self-hosted HuggingFace `AutoModelForCausalLM` | Mistral REST API via SDK | Phase 3 (now) | Remove torch/transformers dependency from llm_agent.py |

**Deprecated/outdated:**
- `MistralClient`: removed in v1.0.0; do not use.
- `from transformers import AutoTokenizer, AutoModelForCausalLM` in `llm_agent.py`: will be removed in this phase (no longer needed once API path is live).
- `import torch` at top of `llm_agent.py`: remove after Phase 3 replaces HF path.

---

## Open Questions

1. **Model ID string for `mistral-small-latest`**
   - What we know: Requirements reference "Mistral Small 3.1" and the model config has `"mistralai/Mistral-Small-Instruct-2409"` (HuggingFace path). The API model ID for the Mistral cloud is `"mistral-small-latest"`.
   - What's unclear: Whether `"mistral-small-3.1-latest"` or `"mistral-small-latest"` is the canonical API string — both may work.
   - Recommendation: Use `"mistral-small-latest"` as the default; expose as a configurable constant or env var `MISTRAL_MODEL` with default `"mistral-small-latest"`.

2. **`tool_calls` serialization format when appending back to messages**
   - What we know: The SDK v2 returns Pydantic models; the exact behavior of passing them back as message dict entries is not 100% confirmed from docs.
   - What's unclear: Whether `response.choices[0].message` (as a full object) can be appended directly to the messages list, or whether `.model_dump()` is needed.
   - Recommendation: Use `response.choices[0].message.model_dump(exclude_none=True)` to convert to plain dict before appending; this is safe across SDK versions.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| mistralai SDK | All LLM calls | Yes | 2.0.4 in `.venv` | None — required |
| MISTRAL_API_KEY | API auth | Yes | Present in `.env` | Tests use mock/patch |
| Python 3.14 | Runtime | Yes | 3.14 (venv confirmed) | — |
| pytest-asyncio | Tests | Yes | asyncio_mode=auto in pytest.ini | — |
| torch / transformers | Current llm_agent.py top-level import | Present in venv (guarded in STT) | — | Remove imports from llm_agent.py in Phase 3 |

**Missing dependencies with no fallback:** None — all required components present.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `kiro/voiquyr/pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`) |
| Quick run command | `pytest tests/test_llm_agent.py -v` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | `MistralModelManager.generate_response()` calls `client.chat.complete_async()` | unit (AsyncMock) | `pytest tests/test_llm_agent.py -k "test_real_chat" -x` | ❌ Wave 0 |
| LLM-02 | `_generate_mock_response` does not exist in codebase | unit (grep/import) | `pytest tests/test_llm_agent.py -k "test_no_mock_response" -x` | ❌ Wave 0 |
| LLM-03 | Tool schema in Mistral format (`{"type":"function","function":{...}}`) passed to API | unit | `pytest tests/test_llm_agent.py -k "test_tool_format" -x` | ❌ Wave 0 |
| LLM-04 | Full `messages` history passed to each Mistral call | unit (inspect call args) | `pytest tests/test_llm_agent.py -k "test_history_passed" -x` | ❌ Wave 0 |
| LLM-05 | 3-turn conversation with tool execution verified end-to-end | integration (may need real key or VCR cassette) | `pytest tests/test_llm_agent.py -k "test_multi_turn_tool" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_llm_agent.py -v`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_llm_agent.py` — rewrite as pytest-style async tests replacing current script-style file; covers LLM-01 through LLM-05
- [ ] `tests/conftest.py` — add `mistral_api_key` fixture (`os.environ["MISTRAL_API_KEY"] = "test-key"` with autouse for LLM tests) so mock tests don't need real key

*(No new framework install needed — pytest-asyncio already configured)*

---

## Sources

### Primary (HIGH confidence)
- Official Mistral function calling docs — https://docs.mistral.ai/capabilities/function_calling/ — tool format, multi-turn flow
- DeepWiki mistralai/client-python basic usage — https://deepwiki.com/mistralai/client-python/7.1-basic-usage-examples — sync/async patterns, method signatures
- DeepWiki mistralai/client-python async operations — https://deepwiki.com/mistralai/client-python/7.2-asynchronous-operations — `complete_async`, `_async` naming convention
- PyPI mistralai package — https://pypi.org/project/mistralai/ — confirmed v2.1.3 latest, v2.0.4 installed
- Project source — `kiro/voiquyr/src/agents/stt_agent.py` lines 244-251 — confirmed `from mistralai import Mistral` usage pattern in this codebase

### Secondary (MEDIUM confidence)
- GitHub mistralai/client-python README — https://github.com/mistralai/client-python/blob/main/README.md — context manager pattern, import path

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — installed version confirmed in venv, PyPI latest verified
- Architecture: HIGH — existing source code fully read; current state documented; target patterns from official docs
- Pitfalls: HIGH — Pitfalls 1-2 from official docs; Pitfalls 3-5 from codebase analysis and project decision log

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (Mistral API surface is stable; v2.x SDK minor releases unlikely to break these patterns)

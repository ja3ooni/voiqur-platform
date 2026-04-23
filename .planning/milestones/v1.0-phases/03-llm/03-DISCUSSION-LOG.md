# Phase 3: LLM - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 03-llm
**Areas discussed:** API Client Strategy, Tool Calling Format, Context Management, Mock Cleanup

---

## API Client Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mistral REST API | Use cloud API as primary, local models as fallback. Pros: Simpler, more reliable, no GPU needed. Cons: Requires API key, network dependency. | ✓ |
| Local transformers | Use local models as primary. Pros: Works offline, no API costs. Cons: Requires GPU/memory, slower startup. | |

**User's choice:** Mistral REST API (recommended default)
**Notes:** The existing codebase structure already favors REST API (the Mistral client is initialized in VoiceProcessingModels). This aligns with the roadmap's intent to use "Real Mistral API inference".

---

## Tool Calling Format

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI-compatible format | Convert to OpenAI function format. Pros: Consistent with existing code, well-tested. Cons: Translation layer. | ✓ |
| Native Mistral JSON schema | Use Mistral's native tool format directly. Pros: Cleaner integration. Cons: Less tested path. | |

**User's choice:** OpenAI-compatible format (recommended default)
**Notes:** The existing code already has `get_openai_functions()` suggesting OpenAI format is preferred.

---

## Context Management

| Option | Description | Selected |
|--------|-------------|----------|
| Full history array | Pass complete messages array to each API call. Pros: Full context, matches Mistral API natively. Cons: More tokens per request. | ✓ |
| Sliding window | Keep only last N messages. Pros: Cost control. Cons: Lost context. | |

**User's choice:** Full history array (recommended default)
**Notes:** The codebase already implements the correct format via `get_context_for_model()`. No changes needed.

---

## Mock Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove immediately | Delete mock function. Pros: Meets roadmap requirement. Cons: Breaks when API key missing. | |
| Fail gracefully | Raise an error when API key is missing instead of returning mock. Pros: Clear failure mode, matches production intent. | ✓ |

**User's choice:** Fail gracefully (recommended default)
**Notes:** The roadmap explicitly requires the mock to not exist. Instead of silently returning mock data, the system should fail with a clear error when MISTRAL_API_KEY is not configured.

---

## Agent's Discretion

- Temperature and top_p settings for Mistral API calls (use existing config: temperature=0.7, top_p=0.9)
- Retry logic and timeout values for API calls
- Error handling messages for failed tool executions

## Deferred Ideas

None — discussion stayed within phase scope
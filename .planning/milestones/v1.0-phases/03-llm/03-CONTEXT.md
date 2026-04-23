# Phase 3: LLM - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Real Mistral API inference replaces mock response generator. Conversions turn produce real Mistral API responses with tool calling and multi-turn history.

</domain>

<decisions>
## Implementation Decisions

### API Client Strategy
- **D-01:** Use Mistral REST API (`mistralai` Python SDK) as the primary path. Remove local model loading from `MistralModelManager` once the REST API works.

### Tool Calling Format
- **D-02:** Use OpenAI-compatible tool format via `tool_registry.get_openai_functions()`. This maintains consistency with the existing tool system.

### Context Management
- **D-03:** Pass the full `messages` array from `ConversationContext.get_context_for_model()` to Mistral's chat completion API. The existing implementation is correct.

### Mock Cleanup
- **D-04:** Remove `_generate_mock_response()`. When `MISTRAL_API_KEY` is missing, raise `ConfigurationError("MISTRAL_API_KEY is required")` rather than falling back to mock.

### Agent's Discretion
- Temperature and top_p settings for Mistral API calls (use existing config: temperature=0.7, top_p=0.9)
- Retry logic and timeout values for API calls
- Error handling messages for failed tool executions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `kiro/voiquyr/src/api/models/__init__.py` — Mistral client initialization (lines 49-92)
- `kiro/voiquyr/src/agents/llm_agent.py` — LLM agent with MistralModelManager, ConversationContext, tool_registry
- `kiro/voiquyr/src/agents/tool_integration.py` — ToolRegistry, ToolExecutor, ToolDefinition classes

### Roadmap
- `.planning/ROADMAP.md` — Phase 3: LLM goal and success criteria

### Requirements
- `.planning/REQUIREMENTS.md` — LLM-01 through LLM-05 requirements

</canonical_refs>

 郾湣
## Existing Code Insights

### Reusable Assets
- `MistralModelManager` class: Already handles model loading and response generation
- `ConversationContext` class: Already implements 32k token window with `get_context_for_model()`
- `ToolRegistry.get_openai_functions()`: Already converts tools to OpenAI format
- `VoiceProcessingModels._mistral_client`: Already initialized using `mistralai` SDK

### Established Patterns
- Token-based context trimming via `_trim_context_window()`
- Async model methods with try/except error handling
- Tool calling integration via `tool_executor.execute_tool_call()`

### Integration Points
- `src/api/models/__init__.py` line 88: `self._mistral_client = Mistral(api_key=...)`
- `llm_agent.py` line 1066: `self.tool_registry.get_openai_functions()` for tool definitions
- System prompts defined in `llm_agent.py` lines 618-626

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following the existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-llm*
*Context gathered: 2026-04-19*
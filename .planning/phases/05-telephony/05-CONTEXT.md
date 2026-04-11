# Phase 5: Telephony - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning
**Source:** Kiro spec gap analysis (euvoice-ai-platform/tasks.md + voiquyr-differentiators/tasks.md)

<domain>
## Phase Boundary

Wire real Twilio HTTP calls and a live Twilio Media Streams WebSocket bridge into the existing telephony abstraction layer. The abstraction layer (`src/telephony/`) and `TwilioIntegration` class (`src/api/integrations/telephony.py`) already exist but are not wired to real Twilio credentials or the STT agent. This phase does NOT re-implement the abstraction — it fills the real-HTTP gaps and wires the audio bridge.

</domain>

<decisions>
## What Already Exists (Do NOT Re-implement)

### TwilioIntegration class (`src/api/integrations/telephony.py`)
- Real `aiohttp` HTTP calls via `BaseIntegration._make_request`
- `authenticate()` — GETs `{base_url}.json` with Basic Auth header (`base64(SID:TOKEN)`) ✓
- `make_call(to_number, twiml_url, ...)` — POSTs to `{base_url}/Calls.json` with form data ✓
- `send_sms(to_number, message, ...)` — POSTs to `{base_url}/Messages.json` ✓
- `TwilioConfig` with `account_sid`, `auth_token`, `phone_number`, `edge_location="dublin"` ✓

### Telephony abstraction layer (`src/telephony/`)
- `call_controller.py` — load-balanced provider orchestrator (uses `TelephonyProvider` interface)
- `provider_registry.py` — SIP trunk provider registry
- `base.py`, `asterisk_provider.py`, `freeswitch_provider.py`, `sip_providers.py`, `cloud_providers.py`
- `byoc_adapter.py`, `media_processor.py`, `qos_monitor.py`, `webrtc.py`

### Test file
- `tests/test_telephony_abstraction.py` — tests the abstraction layer using `MockTelephonyProvider` (not Twilio credentials)

## Actual Gaps (What Phase 5 Must Fix)

### TEL-01 / TEL-02: Signature vs. GSD spec
GSD requires `make_call(to, from_, url)` and `send_sms(to, from_, body)` where `from_` is explicit. Current impl takes `from_` from `config.phone_number`. Plans must either:
- Add wrapper methods matching the GSD signature, OR
- Verify the existing methods satisfy TEL-01/TEL-02 per the success criteria (POST to `api.twilio.com/Calls` returns call SID)

**Decision: Verify existing implementation satisfies TEL-01/TEL-02. If signature mismatch prevents pytest passing, add thin wrapper — do not rewrite.**

### TEL-04: Twilio Media Streams WebSocket bridge (MISSING)
`call_controller.py` is the abstraction-layer orchestrator, NOT a Twilio Media Streams handler. Need a WebSocket endpoint that:
- Accepts Twilio's `wss://` Media Streams connection
- Receives μ-law 8kHz audio frames
- Passes frames to `STTAgent.process_audio_chunk()`
- Location: `src/telephony/twilio_media_stream.py` (new file)

### TEL-05: SIP trunk registry with real Twilio provider config (MISSING)
`provider_registry.py` has the registry but no Twilio-as-SIP-trunk config. Need to register Twilio as a SIP trunk provider with env-var-backed config.

### TEL-06: Test with Twilio test credentials (PARTIAL)
`test_telephony_abstraction.py` tests the abstraction layer with mocks. Need tests that exercise `TwilioIntegration` with Twilio's own test credentials (account SID `ACtest...`, auth token `test...`), verifying real HTTP structure.

## Implementation Constraints
- Use Twilio test credentials (`TWILIO_TEST_ACCOUNT_SID` / `TWILIO_TEST_AUTH_TOKEN`) — these hit real Twilio API without charging
- `TwilioIntegration` uses `aiohttp` — tests must use `aiohttp` compatible mocking (`aioresponses` library) or live test credentials
- Twilio Media Streams sends μ-law encoded audio over WebSocket with JSON control messages
- STT agent input: `stt_agent.process_audio_chunk(chunk: bytes)` — must bridge μ-law to the existing STT pipeline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### TwilioIntegration (existing)
- `kiro/voiquyr/src/api/integrations/telephony.py` — TwilioIntegration, TwilioConfig, make_call, send_sms, authenticate
- `kiro/voiquyr/src/api/integrations/base.py` — BaseIntegration._make_request (aiohttp, real HTTP)

### Telephony abstraction layer (existing)
- `kiro/voiquyr/src/telephony/call_controller.py` — abstraction-layer call controller
- `kiro/voiquyr/src/telephony/provider_registry.py` — SIP trunk registry
- `kiro/voiquyr/src/telephony/base.py` — TelephonyProvider interface, CallSession, ProviderType

### STT agent (bridge target)
- `kiro/voiquyr/src/agents/stt_agent.py` — STTAgent (input: audio chunks)

### Tests (reference, not replace)
- `kiro/voiquyr/tests/test_telephony_abstraction.py` — existing tests using MockTelephonyProvider

### GSD requirements
- `.planning/REQUIREMENTS.md` — TEL-01 through TEL-06

### Kiro specs (completed work, reference for what NOT to re-implement)
- `kiro/voiquyr/.kiro/specs/euvoice-ai-platform/tasks.md` — Task 14 (telephony abstraction, marked complete)
- `kiro/voiquyr/.kiro/specs/voiquyr-differentiators/tasks.md` — Task 2 (BYOC_Adapter, marked complete)

</canonical_refs>

<specifics>
## Specific Requirements

**TEL-01**: `TwilioIntegration.make_call(to, from_, url)` sends real HTTP POST to `api.twilio.com/Calls` and returns a call SID
**TEL-02**: `TwilioIntegration.send_sms(to, from_, body)` sends real HTTP POST to `api.twilio.com/Messages` and returns a message SID
**TEL-03**: `TwilioIntegration.authenticate()` succeeds with test credentials (Basic Auth: `base64(SID:TOKEN)`)
**TEL-04**: `call_controller.py` (or new `twilio_media_stream.py`) connects to Twilio Media Stream WebSocket and passes audio frames to STT agent
**TEL-05**: SIP trunk provider registry populated with real provider configs (Twilio as SIP trunk)
**TEL-06**: `pytest tests/test_telephony_abstraction.py` passes with Twilio test credentials

</specifics>

<deferred>
## Deferred

- Asterisk/FreeSWITCH/3CX PBX integrations (Task 14.2-14.4 in kiro spec — already marked complete, not in TEL-01 to TEL-06)
- VoIP QoS monitoring beyond Twilio (Task 14.5 — separate concern)
- Human agent handoff (Task 14.6 — Phase 6+)
- BYOC_Adapter Kamailio production deployment (Task 2 in voiquyr-differentiators — marked complete, out of Phase 5 scope)

</deferred>

---

*Phase: 05-telephony*
*Context gathered: 2026-04-11 via kiro spec gap analysis*

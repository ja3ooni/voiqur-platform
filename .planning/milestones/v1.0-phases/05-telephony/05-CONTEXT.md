# Phase 5: Telephony - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Real Twilio HTTP calls, SMS, and call controller audio bridging. The platform makes and receives real Twilio calls and SMS, with live audio bridging through the call controller.

</domain>

<decisions>
## Implementation Decisions

### Telephony Provider
- **D-01:** Twilio SDK as primary provider for outbound/inbound calls
- **D-02:** Multi-provider support enabled (Vonage SDK available as backup)
- **D-03:** FreeSWITCH available as gateway/backup path

### Call Flow
- **D-04:** Bidirectional support: Platform → Twilio → Caller (outbound) AND Caller → Twilio → Platform (webhook inbound)
- **D-05:** Twilio webhooks handle inbound call routing to platform

### SMS
- **D-06:** Twilio SMS as primary for outbound notifications
- **D-07:** Vonage SMS as backup provider

### Audio Bridging
- **D-08:** Twilio `<Dial>` with TwiML for straightforward audio handling
- **D-09:** Twilio Connect available for direct media streaming if needed
- **D-10:** WebRTC direct path available for future enhancement

### Agent's Discretion
- Codec selection for media negotiation — agent can decide based on quality/latency tradeoffs
-具体的 Webhook endpoint paths — agent can design RESTful routes
- Error handling retry strategies — agent can implement

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `kiro/voiquyr/src/telephony/__init__.py` — Existing telephony module structure
- `kiro/voiquyr/src/telephony/call_controller.py` — CallController class for orchestration
- `kiro/voiquyr/src/telephony/base.py` — ProviderType.TWILIO already defined
- `kiro/voiquyr/src/telephony/cloud_providers.py` — Existing cloud provider patterns

### Requirements
- `REQUIREMENTS.md` — TEL-01 through TEL-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TelephonyProvider` base class in `base.py` with `ProviderType.TWILIO`
- `CallController` class in `call_controller.py` for multi-provider orchestration
- `ProviderRegistry` for provider lookup and failover
- `cloud_providers.py` has Vonage, Plivo, Bandwidth, Telnyx — patterns to follow

### Established Patterns
- Async `make_call()` method signature across all providers
- `ProviderConfig` for credentials/storage
- `QoSMonitor` for call quality tracking

### Integration Points
- WebSocket to STT/LLM/TTS pipeline via call_controller.py
- Auth layer for authenticated call initiation
- Config for TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN env vars

</code_context>

<specifics>
## Specific Ideas

No specific examples provided — open to standard Twilio implementation patterns.

</specifics>

<deferred>
## Deferred Ideas

- WebRTC direct path — mentioned but not in scope for this phase
- BYOC (Bring Your Own Carrier) — infrastructure-only, not active
- Advanced QoS alerts — monitoring exists, rules TBD

</deferred>

---

*Phase: 05-telephony*
*Context gathered: 2026-04-19*
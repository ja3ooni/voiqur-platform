# Requirements Document

## Introduction

This spec covers the Voiquyr-specific competitive moat features that differentiate the platform from generic voice AI offerings. These features are NOT covered in the `euvoice-ai-platform` spec and represent the hard technical advantages that justify Voiquyr's premium positioning in EU regulated enterprises, UAE/Gulf BPOs, Indian contact centers, and SE Asian enterprise markets.

Pricing context: €0.09–0.15/min (EU), $0.09–0.14/min (ME), ₹6–9/min (India) — all-inclusive UCPM.

## Glossary

- **Edge_Orchestrator**: The component responsible for routing voice traffic and data to the correct regional edge node, enforcing data residency rules at the infrastructure level.
- **Edge_Node**: A regional compute and data processing unit deployed in a specific jurisdiction (Frankfurt, Bahrain, Mumbai, Singapore).
- **BYOC_Adapter**: Bring Your Own Carrier — the generic SIP adapter that connects any SIP-compliant carrier to the Voiquyr platform without per-carrier custom engineering.
- **SIP_Trunk**: A SIP-based telephony connection from a carrier (e.g., Tata Communications, Jio, Mobily, du) to the platform.
- **Semantic_VAD**: Semantic Voice Activity Detection — end-of-turn detection that uses prosody and intent signals in addition to silence detection.
- **Flash_Mode**: Speculative inference mode where LLM processing begins at 85% STT confidence before transcription is finalised.
- **Code_Switch_Handler**: The pipeline component that detects and processes mid-sentence language switches (Arabic↔English, Hindi↔English).
- **Compliance_Layer**: The per-jurisdiction data handling enforcement component that applies UAE PDPL, India DPDP Act, and GDPR rules.
- **Latency_Validator**: The automated benchmarking component that measures and reports p95 conversational latency per region.
- **UCPM**: Unified Cost Per Minute — the all-inclusive per-minute billing unit covering STT, LLM, TTS, and telephony.
- **PDPL**: UAE Personal Data Protection Law (Federal Decree Law No. 45/2021).
- **DPDP**: India Digital Personal Data Protection Act 2023.
- **GDPR**: EU General Data Protection Regulation.
- **p95**: 95th percentile latency — the latency value below which 95% of requests fall.
- **STT**: Speech-to-Text.
- **LLM**: Large Language Model.
- **TTS**: Text-to-Speech.
- **PBX**: Private Branch Exchange — an on-premises telephone switching system.

---

## Requirements

### Requirement 1: Region-Locked Edge Orchestration

**User Story:** As a compliance officer at an EU-regulated enterprise or Gulf BPO, I want all voice data to be processed and stored exclusively within my jurisdiction's edge node, so that my organisation achieves data sovereignty by architecture rather than relying solely on compliance certifications.

#### Acceptance Criteria

1. THE Edge_Orchestrator SHALL route all call audio, transcripts, and metadata exclusively to the edge node matching the tenant's configured jurisdiction (Frankfurt for EU, Bahrain for Gulf, Mumbai for India, Singapore for SE Asia).
2. WHEN a call is initiated, THE Edge_Orchestrator SHALL select the target edge node before any audio data is transmitted, based on the tenant's jurisdiction configuration.
3. WHILE a call is active, THE Edge_Orchestrator SHALL ensure no audio, transcript, or metadata crosses a jurisdictional boundary to a different edge node.
4. IF the designated edge node is unavailable, THEN THE Edge_Orchestrator SHALL reject the call with an explicit error code rather than rerouting data to an alternative jurisdiction.
5. THE Edge_Orchestrator SHALL provide a per-call audit log entry recording the edge node used, the jurisdiction enforced, and the timestamp of enforcement.
6. THE Edge_Node SHALL process STT, LLM inference, and TTS within the same jurisdictional boundary as the call routing.
7. WHEN a tenant's jurisdiction configuration is updated, THE Edge_Orchestrator SHALL apply the new routing rule to all subsequent calls within 60 seconds.

---

### Requirement 2: Generic SIP / BYOC Carrier Adapter

**User Story:** As a contact center operator in India or the Gulf, I want to connect my existing carrier (Tata Communications, Jio, Mobily, du, or a local PBX) to Voiquyr without requiring custom per-carrier engineering, so that I can go live quickly without vendor lock-in.

#### Acceptance Criteria

1. THE BYOC_Adapter SHALL accept inbound and outbound SIP connections from any RFC 3261-compliant SIP trunk without carrier-specific code modifications.
2. WHEN a new SIP trunk is registered, THE BYOC_Adapter SHALL complete SIP registration and be ready to accept calls within 120 seconds.
3. THE BYOC_Adapter SHALL support G.711 (µ-law and A-law), G.722, and Opus codec negotiation via SDP offer/answer exchange.
4. THE BYOC_Adapter SHALL support SRTP for media encryption on all SIP trunks that advertise SRTP capability.
5. IF a SIP trunk sends a re-INVITE mid-call, THEN THE BYOC_Adapter SHALL handle the re-INVITE without dropping the call.
6. THE BYOC_Adapter SHALL expose a self-service configuration interface where operators can register a new SIP trunk by providing host, port, credentials, and codec preferences — with no Voiquyr engineering involvement.
7. WHEN a SIP trunk registration fails, THE BYOC_Adapter SHALL return a structured error response identifying whether the failure is due to authentication, network reachability, or codec mismatch.
8. THE BYOC_Adapter SHALL support at least 500 concurrent SIP sessions per edge node without degradation in call setup time.

---

### Requirement 3: Semantic Voice Activity Detection (Semantic VAD)

**User Story:** As a contact center operator, I want the voice AI to detect when a caller has truly finished speaking based on meaning and prosody — not just silence — so that the AI does not interrupt callers mid-thought and conversations feel natural.

#### Acceptance Criteria

1. THE Semantic_VAD SHALL use prosodic features (pitch trajectory, energy envelope, speaking rate) in combination with partial intent completion signals to determine end-of-turn.
2. WHEN a caller pauses mid-sentence with an incomplete intent, THE Semantic_VAD SHALL suppress end-of-turn detection for up to 2,000ms to allow the caller to continue.
3. WHEN a caller completes a semantic unit (question, statement, or command), THE Semantic_VAD SHALL signal end-of-turn within 300ms of the final phoneme.
4. THE Semantic_VAD SHALL reduce false interruption rate to below 5% of turns compared to silence-only VAD baselines measured on the same test corpus.
5. THE Semantic_VAD SHALL operate with a processing latency of less than 50ms per audio frame to avoid introducing perceptible delay.
6. WHERE a language model is available for the active call language, THE Semantic_VAD SHALL incorporate partial transcript intent scoring as an additional end-of-turn signal.
7. IF the Semantic_VAD model is unavailable, THEN THE Semantic_VAD SHALL fall back to silence-based VAD with a configurable silence threshold, and log the fallback event.

---

### Requirement 4: Speculative Inference / Flash Mode

**User Story:** As a product manager targeting sub-500ms conversational latency, I want LLM inference to begin speculatively as soon as STT confidence reaches 85%, so that perceived response latency is reduced even before transcription is finalised.

#### Acceptance Criteria

1. WHEN the STT confidence score for a partial transcript reaches or exceeds 85%, THE Flash_Mode SHALL begin LLM inference on the partial transcript speculatively.
2. WHEN the final STT transcript is produced and differs from the speculative transcript, THE Flash_Mode SHALL discard the speculative LLM output and restart inference on the final transcript.
3. WHEN the final STT transcript matches the speculative transcript, THE Flash_Mode SHALL use the already-computed LLM output without recomputation.
4. THE Flash_Mode SHALL reduce median time-to-first-token (TTFT) by at least 80ms compared to non-speculative inference on the same hardware, measured across a representative test set of 1,000 utterances.
5. IF the STT confidence score does not reach 85% before end-of-turn is detected, THEN THE Flash_Mode SHALL begin LLM inference on the final transcript immediately upon end-of-turn signal.
6. THE Flash_Mode SHALL be configurable per tenant, with a default-on state and the ability to disable it for latency-sensitive debugging scenarios.
7. THE Flash_Mode SHALL log speculative hit rate (percentage of speculative outputs used without recomputation) per tenant per day.

---

### Requirement 5: Code-Switching as a First-Class Feature

**User Story:** As a Gulf or Indian contact center operator, I want the voice AI to handle callers who switch between Arabic and English, or Hindi and English, mid-sentence without degraded transcription or response quality, so that the AI serves multilingual callers naturally.

#### Acceptance Criteria

1. THE Code_Switch_Handler SHALL detect a language switch within a single utterance for Arabic↔English and Hindi↔English language pairs.
2. WHEN a language switch is detected mid-utterance, THE Code_Switch_Handler SHALL apply the appropriate acoustic model for each language segment within the same STT pass.
3. THE Code_Switch_Handler SHALL produce a single unified transcript that correctly represents both language segments, with no dropped words at the switch boundary.
4. THE Code_Switch_Handler SHALL maintain semantic coherence across the switch boundary so that the LLM receives a coherent mixed-language input and produces a contextually appropriate response.
5. THE Code_Switch_Handler SHALL handle code-switching at the word boundary level, not only at the sentence boundary level.
6. WHEN the LLM generates a response to a code-switched input, THE Code_Switch_Handler SHALL preserve the language mix ratio of the input in the response unless the tenant has configured a preferred response language.
7. WHERE a tenant has configured a preferred response language, THE Code_Switch_Handler SHALL generate the TTS response in the configured language regardless of the input language mix.
8. THE Code_Switch_Handler SHALL achieve a word error rate (WER) of less than 15% on a standard Arabic↔English and Hindi↔English code-switching benchmark corpus.

---

### Requirement 6: Multi-Jurisdiction Compliance Layer

**User Story:** As a data protection officer operating across EU, UAE, and India, I want the platform to enforce the specific data handling rules of each jurisdiction automatically, so that my organisation is compliant with GDPR, UAE PDPL, and India DPDP Act without manual per-jurisdiction configuration.

#### Acceptance Criteria

1. THE Compliance_Layer SHALL enforce GDPR (EU), UAE PDPL (Federal Decree Law No. 45/2021), and India DPDP Act 2023 data handling rules as distinct, configurable rule sets.
2. WHEN a call is processed in the Frankfurt edge node, THE Compliance_Layer SHALL apply GDPR rules including lawful basis recording, data minimisation, and right-to-erasure support.
3. WHEN a call is processed in the Bahrain edge node, THE Compliance_Layer SHALL apply UAE PDPL rules including consent recording, data localisation enforcement, and cross-border transfer restrictions.
4. WHEN a call is processed in the Mumbai edge node, THE Compliance_Layer SHALL apply India DPDP Act 2023 rules including consent notice requirements, data fiduciary obligations, and data principal rights.
5. THE Compliance_Layer SHALL generate a per-call compliance record identifying which jurisdiction's rules were applied, the lawful basis or consent status, and any data retention schedule.
6. WHEN a data subject submits a right-to-erasure or data principal rights request, THE Compliance_Layer SHALL identify and schedule deletion of all associated call records, transcripts, and metadata within the jurisdiction's mandated response window.
7. IF a call's data residency jurisdiction and the tenant's compliance jurisdiction configuration are mismatched, THEN THE Compliance_Layer SHALL block the call and generate a compliance alert.
8. THE Compliance_Layer SHALL produce a monthly compliance summary report per jurisdiction, listing total calls processed, consent rates, and any compliance exceptions.

---

### Requirement 7: Multi-Region Latency Validation

**User Story:** As a platform engineer, I want automated benchmarking to continuously validate that p95 conversational latency stays below 500ms in each deployed region, so that SLA commitments to customers are verifiable and regressions are caught before they affect production traffic.

#### Acceptance Criteria

1. THE Latency_Validator SHALL measure end-to-end conversational latency (from end-of-turn signal to first byte of TTS audio) for each of the four edge nodes: Frankfurt, Bahrain, Mumbai, and Singapore.
2. THE Latency_Validator SHALL report p95 latency per region on a continuous basis with a measurement interval of no more than 5 minutes.
3. WHEN p95 latency in any region exceeds 500ms, THE Latency_Validator SHALL generate an alert within 60 seconds of the threshold breach.
4. THE Latency_Validator SHALL decompose total latency into STT processing time, LLM TTFT, LLM generation time, and TTS first-byte time, and report each component separately.
5. THE Latency_Validator SHALL use synthetic test calls that exercise the full pipeline (STT → LLM → TTS) to produce latency measurements independent of real call volume.
6. THE Latency_Validator SHALL store latency measurements for a minimum of 90 days to support trend analysis and SLA reporting.
7. THE Latency_Validator SHALL expose a dashboard endpoint showing current p50, p95, and p99 latency per region and per pipeline component.
8. WHEN a new deployment is rolled out to an edge node, THE Latency_Validator SHALL run a pre-traffic latency validation suite and block traffic promotion if p95 exceeds 500ms.

---

### Requirement 8: BYOC Carrier Feasibility Validation (Engineering Spike)

**User Story:** As an engineering lead, I want a validated proof-of-concept demonstrating that the generic SIP adapter works with Tata Communications and Jio SIP trunks without any per-carrier custom code, so that we can commit to the BYOC value proposition with confidence before GA launch.

#### Acceptance Criteria

1. THE BYOC_Adapter SHALL successfully complete SIP registration with a Tata Communications SIP trunk using only the standard self-service configuration interface defined in Requirement 2.
2. THE BYOC_Adapter SHALL successfully complete SIP registration with a Jio SIP trunk using only the standard self-service configuration interface defined in Requirement 2.
3. WHEN a test call is placed over the Tata Communications SIP trunk, THE BYOC_Adapter SHALL establish the call, exchange audio, and terminate the call without any carrier-specific code path.
4. WHEN a test call is placed over the Jio SIP trunk, THE BYOC_Adapter SHALL establish the call, exchange audio, and terminate the call without any carrier-specific code path.
5. THE BYOC_Adapter SHALL handle any non-standard SIP header extensions sent by Tata Communications or Jio by ignoring unknown headers without call failure.
6. THE engineering spike SHALL produce a written feasibility report documenting: SIP stack compatibility findings, any RFC 3261 deviations observed in carrier behaviour, codec negotiation results, and a go/no-go recommendation for GA.
7. IF carrier-specific workarounds are required for either Tata Communications or Jio, THEN the feasibility report SHALL document each workaround, its scope, and whether it can be generalised to avoid per-carrier code.

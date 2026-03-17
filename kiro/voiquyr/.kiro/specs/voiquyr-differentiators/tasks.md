# Implementation Plan: Voiquyr Differentiators

## Overview

Eight competitive-moat components built on top of `euvoice-ai-platform`. All code is Python
(hypothesis for property tests) except Edge_Orchestrator (Go + gRPC) and BYOC_Adapter
(Kamailio config + Python management API). Tasks are ordered so each component is
self-contained and wired into the call pipeline at the end.

## Tasks

- [ ] 1. Edge_Orchestrator — jurisdiction-aware call routing service
  - Create `src/edge_orchestrator/` package with `models.py` (JurisdictionConfig,
    CallRoutingDecision, EdgeNodeStatus, AuditLogEntry dataclasses)
  - Implement `EdgeOrchestrator` class in `orchestrator.py`: `route_call`, `get_node_status`,
    `update_jurisdiction_config`, `get_audit_log` — backed by etcd client with 60 s TTL cache
  - Implement node-unavailable rejection path: return 503, write audit entry, never reroute
    to a different jurisdiction (Req 1.4)
  - Implement jurisdiction-mismatch block path: return 403, generate compliance alert (Req 1.3)
  - Implement config propagation: etcd watch triggers cache invalidation within 60 s (Req 1.7)
  - Expose gRPC service definition (`edge_orchestrator.proto`) and generated stubs
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ] 1.1 Write property test — jurisdiction routing invariant
    - **Property 1: Jurisdiction routing invariant**
    - **Validates: Requirements 1.1, 1.3, 1.6**
    - File: `tests/test_edge_orchestrator.py`
    - Strategy: `st.uuids()` × `st.sampled_from(["EU","Gulf","India","SEA"])`
    - Assert `decision.edge_node == JURISDICTION_TO_NODE[jurisdiction]`
    - `@settings(max_examples=100)`

  - [ ]* 1.2 Write property test — audit log completeness
    - **Property 2: Audit log completeness**
    - **Validates: Requirements 1.5**
    - File: `tests/test_edge_orchestrator.py`
    - Strategy: random call_id UUIDs
    - Assert every routed call has a corresponding audit entry with non-null fields

  - [ ]* 1.3 Write unit tests for Edge_Orchestrator
    - Test node-unavailable → 503, no cross-border reroute
    - Test jurisdiction-mismatch → 403 + compliance alert
    - Test config propagation latency ≤ 60 s (mock etcd watch)
    - Test stale-cache fallback when etcd is unreachable
    - _Requirements: 1.4, 1.7_


- [ ] 2. BYOC_Adapter — Kamailio + RTPEngine SIP proxy and management API
  - Create `src/byoc_adapter/` package with `models.py` (SIPTrunkConfig,
    SIPRegistrationResult, CodecNegotiationResult dataclasses)
  - Implement `BYOCAdapter` class in `adapter.py`: `register_trunk`, `negotiate_codecs`,
    `get_session_count`, `handle_reinvite`
  - Write Kamailio config template (`kamailio/voiquyr.cfg`) supporting G.711µ, G.711a,
    G.722, Opus SDP offer/answer; SRTP via RTPEngine; re-INVITE handling (Req 2.3, 2.4, 2.5)
  - Implement self-service REST API in `api.py` (FastAPI): POST/GET/PUT/DELETE `/api/v1/trunks`,
    GET `/api/v1/trunks/{id}/sessions` (Req 2.6)
  - Implement session-limit guard: reject with 503 + Retry-After when count ≥ 500 (Req 2.8)
  - Implement structured error classification: auth / network / codec_mismatch (Req 2.7)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [ ] 2.1 Write property test — SDP codec negotiation correctness
    - **Property 3: SIP codec negotiation correctness**
    - **Validates: Requirements 2.3**
    - File: `tests/test_byoc_adapter.py`
    - Strategy: `st.frozensets(st.sampled_from(["G711u","G711a","G722","Opus"]), min_size=1)`
    - Assert selected codec ∈ offer ∩ supported; empty intersection → 488

  - [ ]* 2.2 Write property test — SRTP negotiation invariant
    - **Property 4: SRTP negotiation invariant**
    - **Validates: Requirements 2.4**
    - File: `tests/test_byoc_adapter.py`
    - Strategy: `st.booleans()` for srtp_in_offer
    - Assert SRTP negotiated iff offer advertises SRTP

  - [ ]* 2.3 Write property test — registration error classification
    - **Property 5: SIP trunk registration error classification**
    - **Validates: Requirements 2.7**
    - File: `tests/test_byoc_adapter.py`
    - Strategy: simulated failure scenarios (auth/network/codec)
    - Assert error_type ∈ {"auth","network","codec_mismatch"} on every failure

  - [ ]* 2.4 Write unit tests for BYOC_Adapter
    - Test re-INVITE handling without call drop (Req 2.5)
    - Test 500-session limit enforcement (Req 2.8)
    - Test trunk registration completes within 120 s (mock SIP stack)
    - _Requirements: 2.2, 2.5, 2.8_


- [ ] 3. Checkpoint — Edge_Orchestrator and BYOC_Adapter
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Semantic_VAD — prosody + intent end-of-turn detector
  - Create `src/semantic_vad/` package with `models.py` (AudioFrame, VADResult dataclasses)
  - Implement `SemanticVAD` class in `vad.py`: `process_frame`, `reset_session`,
    `is_model_available`
  - Integrate pyannote.audio prosody feature extraction (F0, RMS energy, speaking rate,
    pause duration) per 20 ms frame (Req 3.1)
  - Integrate distilBERT intent completeness classifier: score every 200 ms on partial
    transcript; EOT threshold 0.7, suppression threshold 0.3 (Req 3.2, 3.3, 3.6)
  - Implement WebRTC VAD fallback with fallback logging (Req 3.7)
  - Enforce <50 ms processing latency per frame; log violation metric without blocking
    pipeline (Req 3.5)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ] 4.1 Write property test — VAD processing latency
    - **Property 6: Semantic VAD processing latency**
    - **Validates: Requirements 3.5**
    - File: `tests/test_semantic_vad.py`
    - Strategy: `st.binary(min_size=640, max_size=640)` (320 int16 samples)
    - Assert `result.processing_latency_ms < 50` for every frame

  - [ ]* 4.2 Write property test — VAD end-of-turn suppression window
    - **Property 7: VAD end-of-turn suppression window**
    - **Validates: Requirements 3.2**
    - File: `tests/test_semantic_vad.py`
    - Strategy: audio segments with intent_score < 0.3 followed by silence
    - Assert no EOT signal emitted within 2000 ms of pause start

  - [ ]* 4.3 Write unit tests for Semantic_VAD
    - Test false interruption rate < 5% on 100-utterance test corpus (Req 3.4)
    - Test EOT signal within 300 ms of final phoneme on complete utterances (Req 3.3)
    - Test fallback mode activation and logging (Req 3.7)
    - _Requirements: 3.3, 3.4, 3.7_


- [ ] 5. Flash_Mode — speculative LLM inference middleware
  - Create `src/flash_mode/` package with `models.py` (SpeculativeInferenceState,
    FlashModeResult dataclasses)
  - Implement `FlashMode` class in `flash_mode.py`: `on_partial_transcript`,
    `on_final_transcript`, `get_hit_rate`, `is_enabled_for_tenant`
  - Implement 85% confidence trigger: call `llm_agent.infer` speculatively on partial
    transcript when confidence ≥ 0.85 (Req 4.1)
  - Implement reconciliation logic: hash comparison → hit reuse or miss discard (Req 4.2, 4.3)
  - Implement per-tenant enable/disable flag read from TenantConfig (Req 4.6)
  - Implement daily hit-rate logging to Prometheus metric
    `voiquyr_flash_mode_hit_rate{tenant_id, date}` (Req 4.7)
  - Wire FlashMode between STT agent output and LLM agent input in the call pipeline
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ] 5.1 Write property test — speculative hit reuse
    - **Property 8: Flash_Mode speculative hit reuse**
    - **Validates: Requirements 4.3**
    - File: `tests/test_flash_mode.py`
    - Strategy: `st.text()` for transcript; use same string as both partial and final
    - Assert `result.was_speculative_hit == True` and no new LLM call issued

  - [ ]* 5.2 Write property test — speculative miss discard
    - **Property 9: Flash_Mode speculative miss discard**
    - **Validates: Requirements 4.2**
    - File: `tests/test_flash_mode.py`
    - Strategy: `st.text()` pairs where `assume(partial != final)`
    - Assert speculative state status == "discarded" and fresh inference used

  - [ ]* 5.3 Write property test — trigger threshold
    - **Property 10: Flash_Mode trigger threshold**
    - **Validates: Requirements 4.1, 4.5**
    - File: `tests/test_flash_mode.py`
    - Strategy: `st.floats(min_value=0.0, max_value=1.0)` for confidence
    - Assert speculative inference started iff confidence ≥ 0.85

  - [ ]* 5.4 Write property test — hit rate logging accuracy
    - **Property 11: Flash_Mode hit rate logging**
    - **Validates: Requirements 4.7**
    - File: `tests/test_flash_mode.py`
    - Strategy: `st.lists(st.booleans(), min_size=1, max_size=200)` for hit/miss sequence
    - Assert logged rate == hits/total within 0.1%

  - [ ]* 5.5 Write unit tests for Flash_Mode
    - Test TTFT reduction ≥ 80 ms on 1,000-utterance synthetic set (Req 4.4)
    - Test in-flight speculative inference cancelled correctly on miss
    - Test tenant disable flag suppresses all speculative activity (Req 4.6)
    - _Requirements: 4.4, 4.6_


- [ ] 6. Checkpoint — Semantic_VAD and Flash_Mode
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Code_Switch_Handler — multilingual STT with word-boundary language detection
  - Create `src/code_switch/` package with `models.py` (LanguageSegment,
    CodeSwitchTranscript, ResponseLanguageConfig dataclasses)
  - Implement `CodeSwitchHandler` class in `handler.py`: `transcribe`,
    `prepare_llm_input`, `apply_response_language`
  - Integrate MMS multilingual STT model; implement word-level CTC alignment and
    per-word language scoring (ar/hi/en argmax) (Req 5.1, 5.2, 5.5)
  - Implement segment merging: consecutive same-language words → LanguageSegment;
    produce unified_transcript preserving original word order (Req 5.3)
  - Implement language mix ratio calculation and preferred-response-language enforcement
    via TenantConfig (Req 5.6, 5.7)
  - Implement MMS-unavailable fallback: single-segment transcript, switch_count=0,
    log fallback event (design error handling)
  - Wire CodeSwitchHandler as the STT stage for ar/hi/en calls in the pipeline
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ] 7.1 Write property test — code-switch detection coverage
    - **Property 12: Code-switch detection coverage**
    - **Validates: Requirements 5.1, 5.5**
    - File: `tests/test_code_switch.py`
    - Strategy: synthetic word lists with ≥1 language boundary (ar↔en, hi↔en)
    - Assert `switch_count >= 1` and segments cover all words with no gaps

  - [ ]* 7.2 Write property test — unified transcript completeness
    - **Property 13: Unified transcript completeness**
    - **Validates: Requirements 5.3**
    - File: `tests/test_code_switch.py`
    - Strategy: random word sequences with language labels
    - Assert all words appear in unified_transcript in original order

  - [ ]* 7.3 Write property test — preferred response language enforcement
    - **Property 14: Preferred response language enforcement**
    - **Validates: Requirements 5.7**
    - File: `tests/test_code_switch.py`
    - Strategy: `st.sampled_from(["ar","hi","en"])` for preferred_response_language
    - Assert TTS input language == configured language regardless of input mix

  - [ ]* 7.4 Write unit tests for Code_Switch_Handler
    - Test WER < 15% on Arabic↔English benchmark corpus (Req 5.8)
    - Test WER < 15% on Hindi↔English benchmark corpus (Req 5.8)
    - Test semantic coherence: LLM receives coherent mixed-language input (Req 5.4)
    - _Requirements: 5.4, 5.8_


- [ ] 8. Compliance_Layer — per-jurisdiction data handling enforcement
  - Create `src/compliance/` package with `models.py` (ComplianceRecord, ErasureRequest,
    ComplianceSummaryReport dataclasses)
  - Implement `ComplianceLayer` class in `compliance.py`: `process_call`,
    `validate_jurisdiction_match`, `handle_erasure_request`, `generate_monthly_report`
  - Implement four rule-set classes: `GDPRRuleSet`, `UAEPDPLRuleSet`, `INDIADPDPRuleSet`,
    `PDPARuleSet` — each enforcing its jurisdiction's lawful basis, retention, and
    erasure SLA (Req 6.1, 6.2, 6.3, 6.4)
  - Implement per-call compliance record persistence to PostgreSQL with row-level security
    per jurisdiction (Req 6.5)
  - Implement erasure request handler: schedule deletion job with SLA timer
    (GDPR/PDPL: 30 days, DPDP: 7 days, PDPA: 30 days); retry 3× with backoff (Req 6.6)
  - Implement jurisdiction-mismatch block: raise ComplianceAlert severity=CRITICAL,
    do not create record (Req 6.7)
  - Implement `generate_monthly_report`: aggregate calls, consent rates, exceptions (Req 6.8)
  - Wire ComplianceLayer as a sidecar called by Edge_Orchestrator before call admission
    and by LLM agent after each turn
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [ ] 8.1 Write property test — jurisdiction-to-rule-set mapping
    - **Property 15: Jurisdiction-to-rule-set mapping**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    - File: `tests/test_compliance_layer.py`
    - Strategy: `st.sampled_from(["EU","Gulf","India","SEA"])` × random call metadata
    - Assert rule_set_applied matches JURISDICTION_RULE_MAP exactly for every record

  - [ ]* 8.2 Write property test — compliance record completeness
    - **Property 16: Compliance record completeness**
    - **Validates: Requirements 6.5**
    - File: `tests/test_compliance_layer.py`
    - Strategy: random call metadata across all jurisdictions
    - Assert all required fields non-null per rule-set spec

  - [ ]* 8.3 Write property test — erasure request completeness
    - **Property 17: Erasure request completeness**
    - **Validates: Requirements 6.6**
    - File: `tests/test_compliance_layer.py`
    - Strategy: random data_subject_id UUIDs with associated call records
    - Assert zero records returned for subject after erasure completes

  - [ ]* 8.4 Write unit tests for Compliance_Layer
    - Test jurisdiction-mismatch → call blocked + CRITICAL alert (Req 6.7)
    - Test monthly report structure and aggregation (Req 6.8)
    - Test in-memory queue flush when DB recovers (design error handling)
    - _Requirements: 6.7, 6.8_


- [ ] 9. Checkpoint — Code_Switch_Handler and Compliance_Layer
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Latency_Validator — synthetic benchmarking and deployment gate
  - Create `src/latency_validator/` package with `models.py` (LatencyMeasurement,
    RegionLatencyReport, DeploymentGateResult dataclasses)
  - Implement `LatencyValidator` class in `validator.py`: `run_synthetic_suite`,
    `get_region_report`, `check_sla_breach`, `run_deployment_gate`, `get_dashboard_data`
  - Implement synthetic test harness: replay 50 fixed utterances per region every 5 min
    using SIPp; collect OpenTelemetry spans for latency decomposition (Req 7.1, 7.2, 7.4, 7.5)
  - Implement p50/p95/p99 calculation and 90-day retention via Prometheus remote write
    (Req 7.2, 7.6)
  - Implement SLA breach alert: fire within 60 s when p95 > 500 ms; retry delivery 5×
    (Req 7.3)
  - Implement deployment gate: run validation suite pre-traffic; return gate_passed=False
    if p95 > 500 ms or suite times out (Req 7.8)
  - Expose dashboard endpoint returning current p50/p95/p99 per region and component
    (Req 7.7)
  - Register Prometheus metrics: `voiquyr_call_latency_ms{region,component,percentile,synthetic}`
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ] 10.1 Write property test — latency decomposition sum invariant
    - **Property 18: Latency decomposition sum invariant**
    - **Validates: Requirements 7.4**
    - File: `tests/test_latency_validator.py`
    - Strategy: `st.floats(min_value=0, max_value=500)` × 4 components
    - Assert `abs(sum(components) - total_latency_ms) <= 1.0`

  - [ ]* 10.2 Write property test — SLA breach alert generation
    - **Property 19: SLA breach alert generation**
    - **Validates: Requirements 7.3**
    - File: `tests/test_latency_validator.py`
    - Strategy: `st.floats(min_value=501, max_value=2000)` for p95
    - Assert alert generated within 60 s of measurement

  - [ ]* 10.3 Write property test — deployment gate enforcement
    - **Property 20: Deployment gate enforcement**
    - **Validates: Requirements 7.8**
    - File: `tests/test_latency_validator.py`
    - Strategy: `st.floats(min_value=501, max_value=2000)` for measured p95
    - Assert `gate_passed == False` whenever p95 > 500

  - [ ]* 10.4 Write unit tests for Latency_Validator
    - Test failed synthetic call skipped from p95 calculation (design error handling)
    - Test 90-day retention: measurements older than 90 days not returned (Req 7.6)
    - Test dashboard endpoint returns all four regions (Req 7.7)
    - _Requirements: 7.6, 7.7_


- [ ] 11. BYOC Carrier Feasibility Spike — Tata Communications and Jio validation
  - Create `src/byoc_spike/` package with `spike_harness.py`: SIPp test runner that
    places calls over a configured SIP trunk and captures SIP traces (Req 8.3, 8.4)
  - Implement `SIPTraceAnalyser` in `trace_analyser.py`: parse Wireshark PCAP/SIPp logs,
    extract RFC 3261 deviations (non-standard headers, timer values, re-INVITE behaviour),
    and produce a structured deviation log (Req 8.5, 8.6)
  - Implement `FeasibilityReporter` in `reporter.py`: consume deviation log + codec
    negotiation results → produce `FeasibilityReport` dataclass with fields:
    sip_compatibility_matrix, rfc3261_deviations, codec_results,
    nonstandard_headers, recommendation (go/no-go), workaround_scope (Req 8.6, 8.7)
  - Implement unknown-header ignore logic in Kamailio config: `remove_hf` for any header
    not in the RFC 3261 required set; verify call does not fail (Req 8.5)
  - Write `tests/test_byoc_spike.py` with unit tests covering:
    - Tata trunk registration via self-service API only (Req 8.1)
    - Jio trunk registration via self-service API only (Req 8.2)
    - Unknown SIP header present → call succeeds, header ignored (Req 8.5)
    - FeasibilityReport contains all required fields (Req 8.6)
    - Workaround scope documented when carrier-specific fix required (Req 8.7)
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ] 12. Final checkpoint — full pipeline integration
  - Wire all components into the call pipeline:
    - BYOC_Adapter → Edge_Orchestrator → Compliance_Layer (admission)
    - Edge_Orchestrator → Semantic_VAD → STT (MMS via Code_Switch_Handler or Whisper)
      → Flash_Mode → LLM Agent → TTS Agent → BYOC_Adapter
    - LLM Agent → Compliance_Layer (per-turn record)
    - All components → Latency_Validator (OpenTelemetry spans)
  - Verify Prometheus metrics registered: `voiquyr_call_latency_ms`,
    `voiquyr_flash_mode_hit_rate`, `voiquyr_vad_false_interruption_rate`,
    `voiquyr_code_switch_wer`, `voiquyr_sip_sessions_active`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis` with `@settings(max_examples=100)` and the tag format:
  `# Feature: voiquyr-differentiators, Property {N}: {property_text}`
- No task duplicates work already covered in `euvoice-ai-platform` (STT/LLM/TTS agents,
  multi-agent framework, Prometheus/Grafana setup, PostgreSQL, Kubernetes, GDPR audit logging)
- The BYOC Carrier Feasibility Spike (Task 11) is a time-boxed 2-week investigation;
  its output is code artefacts (harness, analyser, reporter) plus a FeasibilityReport,
  not a production component

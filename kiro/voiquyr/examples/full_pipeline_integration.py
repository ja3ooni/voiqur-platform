"""
Full pipeline integration example - All Voiquyr differentiators.

Demonstrates the complete call flow through all components:
Edge_Orchestrator → BYOC_Adapter → Semantic_VAD → Code_Switch_Handler
→ Flash_Mode → LLM → TTS → Compliance_Layer → Latency_Validator
"""

import asyncio
from src.core import (
    get_edge_orchestrator,
    get_semantic_vad,
    get_flash_mode,
    get_code_switch_handler,
    get_compliance_layer,
    get_latency_validator,
    Jurisdiction,
    RegionalEndpoint,
    CallContext,
    AudioFrame,
    Language,
    ResponseLanguageConfig,
    ComplianceJurisdiction,
    Region
)
from src.telephony import (
    get_byoc_adapter,
    SIPTrunk
)


class MockLLMAgent:
    """Mock LLM agent for testing."""
    async def infer(self, transcript: str) -> str:
        await asyncio.sleep(0.15)  # Simulate LLM latency
        return f"Response to: {transcript}"


async def process_call(call_id: str, source_country: str, audio_data: bytes):
    """Process a complete call through the pipeline."""
    print(f"\n{'='*60}")
    print(f"Processing Call: {call_id}")
    print(f"{'='*60}\n")
    
    # 1. Edge Orchestrator - Route call to appropriate jurisdiction
    print("1. Edge Orchestrator - Routing call...")
    edge_orch = get_edge_orchestrator()
    
    call_context = CallContext(
        call_id=call_id,
        source_country=source_country,
        requires_gdpr=(source_country in ["DE", "FR", "IT"]),
        requires_ai_act=(source_country in ["DE", "FR", "IT"])
    )
    
    endpoint = await edge_orch.route_call(call_context)
    if not endpoint:
        print("   ✗ No available endpoint")
        return
    
    print(f"   ✓ Routed to: {endpoint.region} ({endpoint.jurisdiction})")
    
    # 2. BYOC Adapter - Setup SIP call
    print("\n2. BYOC Adapter - Setting up SIP call...")
    byoc = get_byoc_adapter()
    
    sdp_offer = "v=0\no=- 123 123 IN IP4 192.168.1.1\ns=Call\nc=IN IP4 192.168.1.1\nt=0 0\nm=audio 10000 RTP/AVP 0\na=rtpmap:0 PCMU/8000"
    
    session = await byoc.setup_call(call_id, "from-tag-123", sdp_offer)
    if session:
        print(f"   ✓ SIP session established: {session.call_id}")
    
    # 3. Compliance Layer - Create compliance record
    print("\n3. Compliance Layer - Recording compliance...")
    compliance = get_compliance_layer()
    
    jurisdiction_map = {
        "DE": ComplianceJurisdiction.EU,
        "AE": ComplianceJurisdiction.GULF,
        "IN": ComplianceJurisdiction.INDIA,
        "SG": ComplianceJurisdiction.SEA
    }
    
    try:
        record = await compliance.process_call(
            call_id=call_id,
            jurisdiction=jurisdiction_map.get(source_country, ComplianceJurisdiction.EU),
            data_subject_id=f"user-{call_id}",
            lawful_basis="consent",
            consent_obtained=True
        )
        print(f"   ✓ Compliance record: {record.record_id}")
    except Exception as e:
        print(f"   ✗ Compliance error: {e}")
        return
    
    # 4. Semantic VAD - Process audio frames
    print("\n4. Semantic VAD - Processing audio...")
    vad = get_semantic_vad()
    
    # Simulate processing 10 frames (200ms of audio)
    eot_detected = False
    for i in range(10):
        frame = AudioFrame(
            samples=audio_data[i*640:(i+1)*640] if len(audio_data) >= (i+1)*640 else b'\x00'*640,
            timestamp_ms=i * 20,
            sequence_number=i
        )
        
        result = vad.process_frame(frame, partial_transcript="hello how are you")
        
        if result.is_eot:
            eot_detected = True
            print(f"   ✓ End-of-turn detected at frame {i} (latency: {result.processing_latency_ms:.1f}ms)")
            break
    
    if not eot_detected:
        print("   ○ No end-of-turn detected in sample")
    
    # 5. Code Switch Handler - Transcribe with language detection
    print("\n5. Code Switch Handler - Transcribing...")
    code_switch = get_code_switch_handler()
    
    transcript = await code_switch.transcribe(
        audio_data,
        expected_languages=[Language.ENGLISH, Language.ARABIC]
    )
    
    print(f"   ✓ Transcript: {transcript.unified_transcript}")
    print(f"   ✓ Languages: {list(transcript.language_mix_ratio.keys())}")
    print(f"   ✓ Code switches: {transcript.switch_count}")
    
    # 6. Flash Mode - Speculative inference
    print("\n6. Flash Mode - Speculative inference...")
    flash_mode = get_flash_mode()
    llm_agent = MockLLMAgent()
    
    # Trigger speculative inference on partial transcript
    await flash_mode.on_partial_transcript(
        call_id=call_id,
        partial_transcript=transcript.unified_transcript,
        confidence=0.9,
        tenant_id="tenant-001",
        llm_agent=llm_agent
    )
    print("   ✓ Speculative inference triggered")
    
    # Get final response
    result = await flash_mode.on_final_transcript(
        call_id=call_id,
        final_transcript=transcript.unified_transcript,
        llm_agent=llm_agent
    )
    
    if result.was_speculative_hit:
        print(f"   ✓ Speculative HIT! TTFT reduction: {result.ttft_reduction_ms:.1f}ms")
    else:
        print("   ○ Speculative miss, fresh inference used")
    
    print(f"   ✓ LLM Response: {result.final_response[:50]}...")
    
    # 7. Latency Validator - Record metrics
    print("\n7. Latency Validator - Recording latency...")
    validator = get_latency_validator()
    
    region_map = {
        "DE": Region.EU_CENTRAL,
        "AE": Region.ME_DUBAI,
        "IN": Region.ASIA_MUMBAI,
        "SG": Region.ASIA_SINGAPORE
    }
    
    region = region_map.get(source_country, Region.EU_CENTRAL)
    
    # Run synthetic suite
    measurements = await validator.run_synthetic_suite(region)
    print(f"   ✓ Recorded {len(measurements)} measurements")
    
    # Get report
    report = validator.get_region_report(region, hours=1)
    print(f"   ✓ p50: {report.p50_ms:.1f}ms, p95: {report.p95_ms:.1f}ms, p99: {report.p99_ms:.1f}ms")
    
    # Check SLA
    breach = await validator.check_sla_breach(region)
    if breach:
        print("   ⚠ SLA breach detected!")
    else:
        print("   ✓ SLA compliant")
    
    # 8. Cleanup
    print("\n8. Cleanup...")
    if session:
        await byoc.hangup_call(call_id, "from-tag-123", "to-tag-456")
        print("   ✓ SIP session terminated")
    
    print(f"\n{'='*60}")
    print(f"Call {call_id} completed successfully")
    print(f"{'='*60}\n")


async def main():
    """Main integration demo."""
    print("\n" + "="*60)
    print("Voiquyr Differentiators - Full Pipeline Integration")
    print("="*60)
    
    # Initialize all components
    print("\nInitializing components...")
    
    # Edge Orchestrator
    edge_orch = get_edge_orchestrator()
    edge_orch.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.EU,
        endpoint_url="https://eu-central-1.voiquyr.ai",
        region="eu-central-1"
    ))
    
    # BYOC Adapter
    byoc = get_byoc_adapter()
    byoc.register_trunk(SIPTrunk(
        trunk_id="trunk-001",
        name="Primary Carrier",
        host="sip.carrier.com",
        max_channels=100
    ))
    
    print("✓ All components initialized\n")
    
    # Process sample calls from different regions
    calls = [
        ("call-de-001", "DE", b'\x00' * 6400),  # Germany
        ("call-ae-001", "AE", b'\x00' * 6400),  # UAE
        ("call-in-001", "IN", b'\x00' * 6400),  # India
    ]
    
    for call_id, country, audio in calls:
        await process_call(call_id, country, audio)
        await asyncio.sleep(1)
    
    # Display system statistics
    print("\n" + "="*60)
    print("System Statistics")
    print("="*60 + "\n")
    
    # Edge Orchestrator stats
    print("Edge Orchestrator:")
    stats = edge_orch.get_jurisdiction_stats()
    for jurisdiction, data in stats.items():
        print(f"  {jurisdiction}: {data['available_endpoints']}/{data['total_endpoints']} endpoints")
    
    # Flash Mode stats
    print(f"\nFlash Mode:")
    flash_mode = get_flash_mode()
    print(f"  Hit rate: {flash_mode.get_hit_rate():.1%}")
    print(f"  Hits: {flash_mode.hit_count}, Misses: {flash_mode.miss_count}")
    
    # Latency Validator dashboard
    print(f"\nLatency Dashboard:")
    validator = get_latency_validator()
    dashboard = validator.get_dashboard_data()
    for region, data in dashboard.items():
        print(f"  {region}: p95={data['p95_ms']:.1f}ms ({data['measurement_count']} measurements)")
    
    print("\n" + "="*60)
    print("Integration demo completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

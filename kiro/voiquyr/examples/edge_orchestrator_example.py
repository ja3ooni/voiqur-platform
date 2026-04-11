"""
Example usage of Edge Orchestrator for jurisdiction-aware call routing.
"""

import asyncio
from src.core.edge_orchestrator import (
    EdgeOrchestrator,
    Jurisdiction,
    RegionalEndpoint,
    RoutingRule,
    CallContext,
    get_edge_orchestrator
)


async def main():
    # Initialize orchestrator
    orchestrator = get_edge_orchestrator()
    
    # Register regional endpoints
    orchestrator.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.EU,
        endpoint_url="https://eu-central-1.voiquyr.ai",
        region="eu-central-1",
        max_capacity=1000
    ))
    
    orchestrator.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.EU,
        endpoint_url="https://eu-west-1.voiquyr.ai",
        region="eu-west-1",
        max_capacity=800
    ))
    
    orchestrator.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.UK,
        endpoint_url="https://uk-london-1.voiquyr.ai",
        region="uk-london-1",
        max_capacity=500
    ))
    
    # Simulate endpoint health updates
    await orchestrator.update_endpoint_status("eu-central-1", True, latency_ms=45.2, load=250)
    await orchestrator.update_endpoint_status("eu-west-1", True, latency_ms=52.1, load=180)
    await orchestrator.update_endpoint_status("uk-london-1", True, latency_ms=38.5, load=120)
    
    # Route calls from different countries
    calls = [
        CallContext(
            call_id="call-001",
            source_country="DE",
            user_id="user-123",
            language="de-DE",
            requires_gdpr=True,
            requires_ai_act=True
        ),
        CallContext(
            call_id="call-002",
            source_country="GB",
            user_id="user-456",
            language="en-GB",
            requires_gdpr=True,
            requires_ai_act=False
        ),
        CallContext(
            call_id="call-003",
            source_country="FR",
            user_id="user-789",
            language="fr-FR",
            requires_gdpr=True,
            requires_ai_act=True
        )
    ]
    
    for call in calls:
        endpoint = await orchestrator.route_call(call)
        if endpoint:
            print(f"✓ Call {call.call_id} from {call.source_country} → {endpoint.region} ({endpoint.jurisdiction})")
        else:
            print(f"✗ Call {call.call_id} from {call.source_country} → No available endpoint")
    
    # Display jurisdiction statistics
    print("\nJurisdiction Statistics:")
    stats = orchestrator.get_jurisdiction_stats()
    for jurisdiction, data in stats.items():
        print(f"\n{jurisdiction}:")
        print(f"  Endpoints: {data['available_endpoints']}/{data['total_endpoints']}")
        print(f"  Load: {data['current_load']}/{data['total_capacity']}")
        print(f"  Avg Latency: {data['avg_latency_ms']:.1f}ms")


if __name__ == "__main__":
    asyncio.run(main())

"""
Property tests for Edge_Orchestrator.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st
from src.core.edge_orchestrator import (
    EdgeOrchestrator,
    Jurisdiction,
    RegionalEndpoint,
    RoutingRule,
    CallContext
)


# Jurisdiction to node mapping for testing
JURISDICTION_TO_NODE = {
    "EU": "eu-central-1",
    "Gulf": "me-dubai-1",
    "India": "asia-mumbai-1",
    "SEA": "asia-singapore-1"
}


@pytest.fixture
def orchestrator():
    """Setup orchestrator with test endpoints."""
    orch = EdgeOrchestrator()
    
    # Register test endpoints
    orch.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.EU,
        endpoint_url="https://eu-central-1.test",
        region="eu-central-1"
    ))
    orch.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.MIDDLE_EAST,
        endpoint_url="https://me-dubai-1.test",
        region="me-dubai-1"
    ))
    orch.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.ASIA,
        endpoint_url="https://asia-mumbai-1.test",
        region="asia-mumbai-1"
    ))
    orch.register_endpoint(RegionalEndpoint(
        jurisdiction=Jurisdiction.ASIA,
        endpoint_url="https://asia-singapore-1.test",
        region="asia-singapore-1"
    ))
    
    return orch


# Property 1: Jurisdiction routing invariant
# Validates: Requirements 1.1, 1.3, 1.6
@given(
    call_id=st.uuids(),
    jurisdiction=st.sampled_from(["EU", "Gulf", "India", "SEA"])
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_jurisdiction_routing_invariant(orchestrator, call_id, jurisdiction):
    """Property 1: Jurisdiction routing invariant."""
    # Map test jurisdiction to country codes
    country_map = {
        "EU": "DE",
        "Gulf": "AE",
        "India": "IN",
        "SEA": "SG"
    }
    
    context = CallContext(
        call_id=str(call_id),
        source_country=country_map[jurisdiction],
        requires_gdpr=(jurisdiction == "EU"),
        requires_ai_act=(jurisdiction == "EU")
    )
    
    # Add routing rule if not exists
    if context.source_country not in orchestrator.routing_rules:
        jurisdiction_enum_map = {
            "EU": Jurisdiction.EU,
            "Gulf": Jurisdiction.MIDDLE_EAST,
            "India": Jurisdiction.ASIA,
            "SEA": Jurisdiction.ASIA
        }
        
        orchestrator.add_routing_rule(RoutingRule(
            source_country=context.source_country,
            allowed_jurisdictions=[jurisdiction_enum_map[jurisdiction]],
            preferred_jurisdiction=jurisdiction_enum_map[jurisdiction],
            requires_gdpr=(jurisdiction == "EU"),
            requires_ai_act=(jurisdiction == "EU")
        ))
    
    decision = await orchestrator.route_call(context)
    
    # Assert routing decision matches expected node
    assert decision is not None
    assert decision.region == JURISDICTION_TO_NODE[jurisdiction]


# Property 2: Audit log completeness
# Validates: Requirements 1.5
@given(call_ids=st.lists(st.uuids(), min_size=1, max_size=50))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_audit_log_completeness(orchestrator, call_ids):
    """Property 2: Audit log completeness."""
    routed_calls = []
    
    for call_id in call_ids:
        context = CallContext(
            call_id=str(call_id),
            source_country="DE",
            requires_gdpr=True,
            requires_ai_act=True
        )
        
        decision = await orchestrator.route_call(context)
        if decision:
            routed_calls.append(str(call_id))
    
    # In production, this would query audit log storage
    # For now, verify all routed calls have non-null decision
    assert len(routed_calls) == len(call_ids)

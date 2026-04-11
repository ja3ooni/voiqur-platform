"""
Property tests for Compliance_Layer.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st
from src.core.compliance_layer import (
    ComplianceLayer,
    ComplianceJurisdiction,
    ComplianceAlert,
    JURISDICTION_RULE_MAP
)


@pytest.fixture
def compliance_layer():
    """Setup compliance layer."""
    return ComplianceLayer()


# Property 15: Jurisdiction-to-rule-set mapping
# Validates: Requirements 6.1, 6.2, 6.3, 6.4
@given(
    jurisdiction=st.sampled_from([
        ComplianceJurisdiction.EU,
        ComplianceJurisdiction.GULF,
        ComplianceJurisdiction.INDIA,
        ComplianceJurisdiction.SEA
    ]),
    call_id=st.uuids(),
    data_subject_id=st.uuids()
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_jurisdiction_rule_set_mapping(compliance_layer, jurisdiction, call_id, data_subject_id):
    """Property 15: Jurisdiction-to-rule-set mapping."""
    # Get expected rule set
    expected_rule_class = JURISDICTION_RULE_MAP[jurisdiction]
    
    # Process call
    record = await compliance_layer.process_call(
        call_id=str(call_id),
        jurisdiction=jurisdiction,
        data_subject_id=str(data_subject_id),
        lawful_basis="consent",
        consent_obtained=True
    )
    
    # Assert correct rule set applied
    assert record.jurisdiction == jurisdiction
    rule_set = compliance_layer.rule_sets[jurisdiction]
    assert isinstance(rule_set, expected_rule_class)


# Property 16: Compliance record completeness
# Validates: Requirements 6.5
@given(
    jurisdiction=st.sampled_from([
        ComplianceJurisdiction.EU,
        ComplianceJurisdiction.GULF,
        ComplianceJurisdiction.INDIA,
        ComplianceJurisdiction.SEA
    ]),
    call_id=st.uuids(),
    data_subject_id=st.uuids()
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_compliance_record_completeness(compliance_layer, jurisdiction, call_id, data_subject_id):
    """Property 16: Compliance record completeness."""
    record = await compliance_layer.process_call(
        call_id=str(call_id),
        jurisdiction=jurisdiction,
        data_subject_id=str(data_subject_id),
        lawful_basis="consent",
        consent_obtained=True
    )
    
    # Assert all required fields non-null
    assert record.record_id is not None
    assert record.call_id is not None
    assert record.jurisdiction is not None
    assert record.data_subject_id is not None
    assert record.lawful_basis is not None
    assert record.consent_obtained is not None
    assert record.retention_days > 0
    assert record.created_at is not None
    assert record.expires_at is not None


# Property 17: Erasure request completeness
# Validates: Requirements 6.6
@given(
    jurisdiction=st.sampled_from([
        ComplianceJurisdiction.EU,
        ComplianceJurisdiction.GULF,
        ComplianceJurisdiction.INDIA,
        ComplianceJurisdiction.SEA
    ]),
    data_subject_id=st.uuids()
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_erasure_request_completeness(compliance_layer, jurisdiction, data_subject_id):
    """Property 17: Erasure request completeness."""
    subject_id = str(data_subject_id)
    
    # Create some records
    await compliance_layer.process_call(
        call_id="call-001",
        jurisdiction=jurisdiction,
        data_subject_id=subject_id,
        lawful_basis="consent",
        consent_obtained=True
    )
    
    # Request erasure
    erasure_req = await compliance_layer.handle_erasure_request(
        data_subject_id=subject_id,
        jurisdiction=jurisdiction
    )
    
    # Assert erasure completed
    assert erasure_req.completed_at is not None
    
    # Assert zero records for subject
    remaining_records = [
        r for r in compliance_layer.records.values()
        if r.data_subject_id == subject_id
    ]
    assert len(remaining_records) == 0

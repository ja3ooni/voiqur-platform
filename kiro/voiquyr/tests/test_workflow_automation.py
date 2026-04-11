"""
Workflow Automation Tests (Task 18.6)
Tests for workflow execution, CRM integrations, database operations,
error handling, retry, and templates.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.workflow import (
    Workflow, WorkflowNode, NodeType, Condition, ConditionGroup, ConditionOperator,
    WorkflowEngine, WorkflowExecution, ExecutionStatus, TriggerType, ActionRegistry,
    SalesforceConnector, HubSpotConnector, MSDynamicsConnector,
    SAPConnector, ZohoConnector, PipedriveConnector, CRM_CONNECTORS,
    DataTransformer, RESTConnector,
    get_template, TEMPLATES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def simple_workflow(with_action: bool = True) -> Workflow:
    wf = Workflow(name="Test WF")
    trigger = WorkflowNode(node_type=NodeType.TRIGGER, name="Start")
    wf.add_node(trigger)
    if with_action:
        action = WorkflowNode(node_type=NodeType.ACTION, name="Do Thing",
                              config={"action": "test.action"})
        end = WorkflowNode(node_type=NodeType.END, name="End")
        wf.add_node(action)
        wf.add_node(end)
        wf.connect(trigger.node_id, action.node_id)
        wf.connect(action.node_id, end.node_id)
    return wf


def engine_with_action(action_fn=None) -> WorkflowEngine:
    registry = ActionRegistry()
    registry.register("test.action", action_fn or (lambda cfg, ctx: {"done": True}))
    return WorkflowEngine(action_registry=registry, max_retries=2, retry_delay=0.01)


# ---------------------------------------------------------------------------
# 18.1 Workflow Builder Tests
# ---------------------------------------------------------------------------

class TestWorkflowBuilder:
    def test_add_node_sets_entry(self):
        wf = Workflow(name="W")
        t = WorkflowNode(node_type=NodeType.TRIGGER, name="T")
        wf.add_node(t)
        assert wf.entry_node_id == t.node_id

    def test_connect_nodes(self):
        wf = Workflow()
        a = WorkflowNode(node_type=NodeType.TRIGGER, name="A")
        b = WorkflowNode(node_type=NodeType.ACTION, name="B")
        wf.add_node(a); wf.add_node(b)
        wf.connect(a.node_id, b.node_id)
        assert wf.nodes[a.node_id].next_node_id == b.node_id

    def test_connect_branches(self):
        wf = Workflow()
        c = WorkflowNode(node_type=NodeType.CONDITION, name="C")
        t = WorkflowNode(node_type=NodeType.ACTION, name="True")
        f = WorkflowNode(node_type=NodeType.ACTION, name="False")
        wf.add_node(c); wf.add_node(t); wf.add_node(f)
        wf.connect(c.node_id, t.node_id, "true")
        wf.connect(c.node_id, f.node_id, "false")
        assert wf.nodes[c.node_id].true_branch_id == t.node_id
        assert wf.nodes[c.node_id].false_branch_id == f.node_id

    def test_remove_node_cleans_refs(self):
        wf = Workflow()
        a = WorkflowNode(node_type=NodeType.TRIGGER, name="A")
        b = WorkflowNode(node_type=NodeType.ACTION, name="B")
        wf.add_node(a); wf.add_node(b)
        wf.connect(a.node_id, b.node_id)
        wf.remove_node(b.node_id)
        assert wf.nodes[a.node_id].next_node_id is None

    def test_move_node(self):
        wf = Workflow()
        n = WorkflowNode(node_type=NodeType.ACTION, name="N")
        wf.add_node(n)
        wf.move_node(n.node_id, 100.0, 200.0)
        assert wf.nodes[n.node_id].x == 100.0

    def test_validate_no_trigger(self):
        wf = Workflow()
        wf.add_node(WorkflowNode(node_type=NodeType.ACTION, name="A"))
        wf.entry_node_id = None
        errors = wf.validate()
        assert any("trigger" in e.lower() for e in errors)

    def test_validate_valid_workflow(self):
        wf = simple_workflow()
        assert wf.validate() == []

    def test_version_control_commit(self):
        wf = simple_workflow()
        v = wf.commit("initial")
        assert v.version == 1
        assert len(wf.get_versions()) == 1

    def test_version_control_rollback(self):
        wf = simple_workflow()
        wf.commit("v1")
        original_count = len(wf.nodes)
        wf.add_node(WorkflowNode(node_type=NodeType.ACTION, name="Extra"))
        wf.rollback(1)
        assert len(wf.nodes) == original_count

    def test_to_dict(self):
        wf = simple_workflow()
        d = wf.to_dict()
        assert d["name"] == "Test WF"
        assert "nodes" in d


class TestCondition:
    def test_eq(self):
        c = Condition("score", ConditionOperator.EQ, 100)
        assert c.evaluate({"score": 100}) is True
        assert c.evaluate({"score": 50}) is False

    def test_gt(self):
        c = Condition("score", ConditionOperator.GT, 70)
        assert c.evaluate({"score": 80}) is True
        assert c.evaluate({"score": 70}) is False

    def test_contains(self):
        c = Condition("email", ConditionOperator.CONTAINS, "@example.com")
        assert c.evaluate({"email": "user@example.com"}) is True

    def test_is_empty(self):
        c = Condition("name", ConditionOperator.IS_EMPTY)
        assert c.evaluate({"name": ""}) is True
        assert c.evaluate({"name": "Alice"}) is False

    def test_condition_group_and(self):
        cg = ConditionGroup(
            conditions=[
                Condition("a", ConditionOperator.EQ, 1),
                Condition("b", ConditionOperator.EQ, 2),
            ],
            logic="AND",
        )
        assert cg.evaluate({"a": 1, "b": 2}) is True
        assert cg.evaluate({"a": 1, "b": 9}) is False

    def test_condition_group_or(self):
        cg = ConditionGroup(
            conditions=[
                Condition("a", ConditionOperator.EQ, 1),
                Condition("b", ConditionOperator.EQ, 2),
            ],
            logic="OR",
        )
        assert cg.evaluate({"a": 1, "b": 9}) is True
        assert cg.evaluate({"a": 9, "b": 9}) is False


# ---------------------------------------------------------------------------
# 18.4 Execution Engine Tests
# ---------------------------------------------------------------------------

class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        wf = simple_workflow()
        engine = engine_with_action()
        ex = await engine.execute(wf, {"input": "test"})
        assert ex.status == ExecutionStatus.COMPLETED
        assert len(ex.node_logs) >= 2

    @pytest.mark.asyncio
    async def test_execute_stores_action_output(self):
        wf = simple_workflow()
        engine = engine_with_action(lambda cfg, ctx: {"result": 42})
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.COMPLETED
        assert any(v == {"result": 42} for v in ex.context.values())

    @pytest.mark.asyncio
    async def test_execute_condition_true_branch(self):
        wf = Workflow(name="Cond WF")
        trigger = WorkflowNode(node_type=NodeType.TRIGGER, name="T")
        cond = WorkflowNode(node_type=NodeType.CONDITION, name="Check",
                            config={"condition_group": {"conditions": [
                                {"field": "score", "operator": "gte", "value": 70}
                            ], "logic": "AND"}})
        yes = WorkflowNode(node_type=NodeType.ACTION, name="Yes", config={"action": "test.action"})
        no = WorkflowNode(node_type=NodeType.ACTION, name="No", config={"action": "test.action"})
        end = WorkflowNode(node_type=NodeType.END, name="End")
        for n in [trigger, cond, yes, no, end]:
            wf.add_node(n)
        wf.connect(trigger.node_id, cond.node_id)
        wf.connect(cond.node_id, yes.node_id, "true")
        wf.connect(cond.node_id, no.node_id, "false")
        wf.connect(yes.node_id, end.node_id)
        wf.connect(no.node_id, end.node_id)

        engine = engine_with_action()
        ex = await engine.execute(wf, {"score": 85})
        assert ex.status == ExecutionStatus.COMPLETED
        executed_names = [l.node_name for l in ex.node_logs]
        assert "Yes" in executed_names
        assert "No" not in executed_names

    @pytest.mark.asyncio
    async def test_execute_condition_false_branch(self):
        wf = Workflow(name="Cond WF")
        trigger = WorkflowNode(node_type=NodeType.TRIGGER, name="T")
        cond = WorkflowNode(node_type=NodeType.CONDITION, name="Check",
                            config={"condition_group": {"conditions": [
                                {"field": "score", "operator": "gte", "value": 70}
                            ], "logic": "AND"}})
        yes = WorkflowNode(node_type=NodeType.ACTION, name="Yes", config={"action": "test.action"})
        no = WorkflowNode(node_type=NodeType.ACTION, name="No", config={"action": "test.action"})
        end = WorkflowNode(node_type=NodeType.END, name="End")
        for n in [trigger, cond, yes, no, end]:
            wf.add_node(n)
        wf.connect(trigger.node_id, cond.node_id)
        wf.connect(cond.node_id, yes.node_id, "true")
        wf.connect(cond.node_id, no.node_id, "false")
        wf.connect(yes.node_id, end.node_id)
        wf.connect(no.node_id, end.node_id)

        engine = engine_with_action()
        ex = await engine.execute(wf, {"score": 30})
        executed_names = [l.node_name for l in ex.node_logs]
        assert "No" in executed_names
        assert "Yes" not in executed_names

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        attempts = []

        def flaky(cfg, ctx):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("Transient error")
            return {"ok": True}

        wf = simple_workflow()
        engine = engine_with_action(flaky)
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.COMPLETED
        assert len(attempts) == 2

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self):
        def always_fail(cfg, ctx):
            raise RuntimeError("Always fails")

        wf = simple_workflow()
        engine = engine_with_action(always_fail)
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.FAILED
        assert ex.error is not None

    @pytest.mark.asyncio
    async def test_event_trigger(self):
        wf = simple_workflow()
        engine = engine_with_action()
        engine.register_workflow(wf)
        engine.subscribe_to_event("lead.created", wf.workflow_id)
        executions = await engine.fire_event("lead.created", {"email": "test@example.com"})
        assert len(executions) == 1
        assert executions[0].status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delay_node(self):
        wf = Workflow(name="Delay WF")
        trigger = WorkflowNode(node_type=NodeType.TRIGGER, name="T")
        delay = WorkflowNode(node_type=NodeType.DELAY, name="Wait", config={"seconds": 0.01})
        end = WorkflowNode(node_type=NodeType.END, name="End")
        for n in [trigger, delay, end]:
            wf.add_node(n)
        wf.connect(trigger.node_id, delay.node_id)
        wf.connect(delay.node_id, end.node_id)
        engine = WorkflowEngine()
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_invalid_workflow_fails(self):
        wf = Workflow(name="Bad WF")
        wf.add_node(WorkflowNode(node_type=NodeType.ACTION, name="A"))
        wf.entry_node_id = None
        engine = WorkflowEngine()
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_get_execution(self):
        wf = simple_workflow()
        engine = engine_with_action()
        ex = await engine.execute(wf)
        fetched = engine.get_execution(ex.execution_id)
        assert fetched is not None
        assert fetched.execution_id == ex.execution_id

    @pytest.mark.asyncio
    async def test_async_action(self):
        async def async_action(cfg, ctx):
            await asyncio.sleep(0)
            return {"async": True}

        wf = simple_workflow()
        engine = engine_with_action(async_action)
        ex = await engine.execute(wf)
        assert ex.status == ExecutionStatus.COMPLETED


# ---------------------------------------------------------------------------
# 18.2 CRM Connector Tests
# ---------------------------------------------------------------------------

def _mock_crm(connector, status=200, data=None):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data or {"id": "123"})
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = cm
    session.post.return_value = cm
    session.patch.return_value = cm
    session.put.return_value = cm
    connector._get_session = AsyncMock(return_value=session)
    return session


class TestCRMConnectors:
    @pytest.mark.asyncio
    async def test_salesforce_create_contact(self):
        sf = SalesforceConnector("https://sf.example.com", "token")
        _mock_crm(sf, data={"id": "sf-001"})
        result = await sf.create_contact({"FirstName": "Alice", "Email": "a@example.com"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_hubspot_search_contacts(self):
        hs = HubSpotConnector("token")
        _mock_crm(hs, data={"results": [{"id": "hs-1"}]})
        results = await hs.search_contacts("alice")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_dynamics_get_contact(self):
        dyn = MSDynamicsConnector("https://org.crm.dynamics.com", "token")
        _mock_crm(dyn, data={"contactid": "d-001"})
        result = await dyn.get_contact("d-001")
        assert result is not None

    @pytest.mark.asyncio
    async def test_sap_create_contact(self):
        sap = SAPConnector("https://sap.example.com", "user", "pass")
        _mock_crm(sap, data={"BusinessPartner": "BP001"})
        result = await sap.create_contact({"BusinessPartnerFullName": "Alice"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_zoho_create_deal(self):
        zoho = ZohoConnector("token")
        _mock_crm(zoho, data={"data": [{"id": "z-deal-1"}]})
        result = await zoho.create_deal({"Deal_Name": "Big Deal"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_pipedrive_search_contacts(self):
        pd = PipedriveConnector("api_token")
        _mock_crm(pd, data={"data": {"items": [{"item": {"id": 1}}]}})
        results = await pd.search_contacts("alice")
        assert isinstance(results, list)

    def test_crm_registry_has_all_providers(self):
        assert "salesforce" in CRM_CONNECTORS
        assert "hubspot" in CRM_CONNECTORS
        assert "dynamics" in CRM_CONNECTORS
        assert "sap" in CRM_CONNECTORS
        assert "zoho" in CRM_CONNECTORS
        assert "pipedrive" in CRM_CONNECTORS


# ---------------------------------------------------------------------------
# 18.3 Data Transformation Tests
# ---------------------------------------------------------------------------

class TestDataTransformer:
    def test_map_fields(self):
        dt = DataTransformer()
        result = dt.transform(
            {"first_name": "Alice", "last_name": "Smith"},
            [{"type": "map", "mappings": {"first_name": "firstName", "last_name": "lastName"}}],
        )
        assert result["firstName"] == "Alice"
        assert "first_name" not in result

    def test_format_e164(self):
        dt = DataTransformer()
        result = dt.transform(
            {"phone": "44 7700 900123"},
            [{"type": "format", "field": "phone", "format": "e164"}],
        )
        assert result["phone"].startswith("+")

    def test_format_uppercase(self):
        dt = DataTransformer()
        result = dt.transform(
            {"name": "alice"},
            [{"type": "format", "field": "name", "format": "uppercase"}],
        )
        assert result["name"] == "ALICE"

    def test_filter_fields(self):
        dt = DataTransformer()
        result = dt.transform(
            {"a": 1, "b": 2, "c": 3},
            [{"type": "filter", "keep": ["a", "c"]}],
        )
        assert "b" not in result
        assert result["a"] == 1

    def test_enrich_fields(self):
        dt = DataTransformer()
        result = dt.transform(
            {"name": "Alice"},
            [{"type": "enrich", "fields": {"source": "voiquyr", "version": 1}}],
        )
        assert result["source"] == "voiquyr"

    def test_validate_required_passes(self):
        dt = DataTransformer()
        result = dt.transform(
            {"email": "a@b.com"},
            [{"type": "validate", "required": ["email"]}],
        )
        assert result["email"] == "a@b.com"

    def test_validate_required_fails(self):
        dt = DataTransformer()
        with pytest.raises(ValueError, match="Required field missing"):
            dt.transform({}, [{"type": "validate", "required": ["email"]}])

    def test_validate_type_fails(self):
        dt = DataTransformer()
        with pytest.raises(ValueError, match="must be int"):
            dt.transform(
                {"age": "not-a-number"},
                [{"type": "validate", "types": {"age": "int"}}],
            )

    def test_chained_operations(self):
        dt = DataTransformer()
        result = dt.transform(
            {"first_name": "alice", "last_name": "smith", "extra": "drop"},
            [
                {"type": "map", "mappings": {"first_name": "firstName"}},
                {"type": "format", "field": "firstName", "format": "uppercase"},
                {"type": "filter", "keep": ["firstName", "last_name"]},
            ],
        )
        assert result["firstName"] == "ALICE"
        assert "extra" not in result


# ---------------------------------------------------------------------------
# 18.5 Template Tests
# ---------------------------------------------------------------------------

class TestWorkflowTemplates:
    def test_all_templates_available(self):
        assert set(TEMPLATES.keys()) == {
            "lead_qualification", "appointment_booking",
            "order_processing", "customer_onboarding", "support_ticket_creation",
        }

    def test_get_template_returns_workflow(self):
        for name in TEMPLATES:
            wf = get_template(name)
            assert isinstance(wf, Workflow)
            assert wf.name

    def test_templates_are_valid(self):
        for name in TEMPLATES:
            wf = get_template(name)
            errors = wf.validate()
            assert errors == [], f"Template {name} has errors: {errors}"

    def test_templates_have_trigger(self):
        for name in TEMPLATES:
            wf = get_template(name)
            triggers = [n for n in wf.nodes.values() if n.node_type == NodeType.TRIGGER]
            assert len(triggers) == 1, f"{name} should have exactly 1 trigger"

    def test_templates_have_end(self):
        for name in TEMPLATES:
            wf = get_template(name)
            ends = [n for n in wf.nodes.values() if n.node_type == NodeType.END]
            assert len(ends) >= 1, f"{name} should have at least 1 end node"

    def test_templates_have_tags(self):
        for name in TEMPLATES:
            wf = get_template(name)
            assert len(wf.tags) > 0

    def test_get_unknown_template_raises(self):
        with pytest.raises(KeyError):
            get_template("nonexistent")

    @pytest.mark.asyncio
    async def test_lead_qualification_executes(self):
        wf = get_template("lead_qualification")
        registry = ActionRegistry()
        for action in ["crm.enrich_contact", "crm.create_deal",
                       "notification.send", "email.add_to_sequence"]:
            registry.register(action, lambda cfg, ctx: {"ok": True})
        engine = WorkflowEngine(action_registry=registry, retry_delay=0)
        ex = await engine.execute(wf, {"lead_score": 85})
        assert ex.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_support_ticket_executes(self):
        wf = get_template("support_ticket_creation")
        registry = ActionRegistry()
        for action in ["ai.classify_intent", "pagerduty.trigger",
                       "ticketing.create", "ticketing.assign_queue"]:
            registry.register(action, lambda cfg, ctx: {"ok": True})
        engine = WorkflowEngine(action_registry=registry, retry_delay=0)
        ex = await engine.execute(wf, {"priority": "normal"})
        assert ex.status == ExecutionStatus.COMPLETED

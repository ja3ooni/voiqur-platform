"""
Conversation Designer Tests (Task 21.7)
Tests for canvas, conditions, debugger, A/B testing, and templates.
"""

import pytest
from datetime import datetime

from src.designer import (
    ConversationFlow, ConvNode, ConvNodeType,
    ConvCondition, ConditionGroup, CondOp,
    ConversationDebugger, DebugStep, DebugStepStatus, TestCase,
    ABTestingFramework, ExperimentStatus,
    get_conv_template, CONV_TEMPLATES,
)


# ---------------------------------------------------------------------------
# 21.1 Canvas Tests
# ---------------------------------------------------------------------------

class TestConversationCanvas:
    def _flow(self) -> ConversationFlow:
        flow = ConversationFlow(name="Test")
        start = ConvNode(node_type=ConvNodeType.START, name="Start")
        resp = ConvNode(node_type=ConvNodeType.RESPONSE, name="Hello",
                        response_text="Hi!")
        end = ConvNode(node_type=ConvNodeType.END, name="End")
        flow.add_node(start); flow.add_node(resp); flow.add_node(end)
        flow.connect(start.node_id, resp.node_id)
        flow.connect(resp.node_id, end.node_id)
        return flow

    def test_add_node_sets_entry(self):
        flow = ConversationFlow()
        n = ConvNode(node_type=ConvNodeType.START, name="S")
        flow.add_node(n)
        assert flow.entry_node_id == n.node_id

    def test_connect_next(self):
        flow = self._flow()
        nodes = list(flow.nodes.values())
        assert nodes[0].next_node_id == nodes[1].node_id

    def test_connect_branches(self):
        flow = ConversationFlow()
        c = ConvNode(node_type=ConvNodeType.CONDITION, name="C")
        t = ConvNode(node_type=ConvNodeType.RESPONSE, name="T")
        f = ConvNode(node_type=ConvNodeType.RESPONSE, name="F")
        flow.add_node(c); flow.add_node(t); flow.add_node(f)
        flow.connect(c.node_id, t.node_id, "true")
        flow.connect(c.node_id, f.node_id, "false")
        assert flow.nodes[c.node_id].true_branch_id == t.node_id
        assert flow.nodes[c.node_id].false_branch_id == f.node_id

    def test_remove_node_cleans_refs(self):
        flow = self._flow()
        nodes = list(flow.nodes.values())
        resp_id = nodes[1].node_id
        flow.remove_node(resp_id)
        assert nodes[0].next_node_id is None

    def test_move_node(self):
        flow = self._flow()
        nid = list(flow.nodes.keys())[0]
        flow.move_node(nid, 100.0, 200.0)
        assert flow.nodes[nid].x == 100.0

    def test_validate_valid(self):
        flow = self._flow()
        assert flow.validate() == []

    def test_validate_no_start(self):
        flow = ConversationFlow()
        flow.add_node(ConvNode(node_type=ConvNodeType.RESPONSE, name="R"))
        flow.entry_node_id = None
        errors = flow.validate()
        assert any("START" in e for e in errors)

    def test_version_commit(self):
        flow = self._flow()
        v = flow.commit("initial", author="alice")
        assert v.version == 1
        assert v.author == "alice"

    def test_version_rollback(self):
        flow = self._flow()
        flow.commit("v1")
        original_count = len(flow.nodes)
        flow.add_node(ConvNode(node_type=ConvNodeType.ACTION, name="Extra"))
        flow.rollback(1)
        assert len(flow.nodes) == original_count

    def test_diff_summary(self):
        flow = self._flow()
        v1 = flow.commit("v1")
        flow.add_node(ConvNode(node_type=ConvNodeType.ACTION, name="New"))
        v2 = flow.commit("v2")
        assert "+1" in v2.diff_summary

    def test_annotation(self):
        flow = self._flow()
        nid = list(flow.nodes.keys())[0]
        ann = flow.add_annotation(nid, "alice", "Check this node")
        assert ann.annotation_id is not None
        assert not ann.resolved

    def test_resolve_annotation(self):
        flow = self._flow()
        nid = list(flow.nodes.keys())[0]
        ann = flow.add_annotation(nid, "bob", "TODO")
        assert flow.resolve_annotation(ann.annotation_id) is True
        assert ann.resolved is True

    def test_multi_user_editing(self):
        flow = self._flow()
        s1 = flow.join_editing("alice")
        s2 = flow.join_editing("bob")
        assert "alice" in flow._active_editors
        assert "bob" in flow._active_editors
        flow.leave_editing("alice")
        assert "alice" not in flow._active_editors

    def test_cursor_update(self):
        flow = self._flow()
        flow.join_editing("alice")
        nid = list(flow.nodes.keys())[0]
        flow.update_cursor("alice", nid)
        assert flow._active_editors["alice"].cursor_node_id == nid


# ---------------------------------------------------------------------------
# 21.2 Condition Builder Tests
# ---------------------------------------------------------------------------

class TestConditionBuilder:
    def test_eq(self):
        c = ConvCondition("intent", CondOp.EQ, "billing")
        assert c.evaluate({"intent": "billing"}) is True
        assert c.evaluate({"intent": "other"}) is False

    def test_gte(self):
        c = ConvCondition("score", CondOp.GTE, 70)
        assert c.evaluate({"score": 80}) is True
        assert c.evaluate({"score": 60}) is False

    def test_contains(self):
        c = ConvCondition("text", CondOp.CONTAINS, "hello")
        assert c.evaluate({"text": "say hello world"}) is True

    def test_matches_regex(self):
        c = ConvCondition("email", CondOp.MATCHES, r"@example\.com$")
        assert c.evaluate({"email": "user@example.com"}) is True
        assert c.evaluate({"email": "user@other.com"}) is False

    def test_is_set(self):
        c = ConvCondition("name", CondOp.IS_SET)
        assert c.evaluate({"name": "Alice"}) is True
        assert c.evaluate({"name": ""}) is False
        assert c.evaluate({}) is False

    def test_is_empty(self):
        c = ConvCondition("name", CondOp.IS_EMPTY)
        assert c.evaluate({"name": ""}) is True
        assert c.evaluate({"name": "Alice"}) is False

    def test_group_and(self):
        cg = ConditionGroup(
            conditions=[
                ConvCondition("a", CondOp.EQ, 1),
                ConvCondition("b", CondOp.EQ, 2),
            ],
            logic="AND",
        )
        assert cg.evaluate({"a": 1, "b": 2}) is True
        assert cg.evaluate({"a": 1, "b": 9}) is False

    def test_group_or(self):
        cg = ConditionGroup(
            conditions=[
                ConvCondition("a", CondOp.EQ, 1),
                ConvCondition("b", CondOp.EQ, 2),
            ],
            logic="OR",
        )
        assert cg.evaluate({"a": 1, "b": 9}) is True
        assert cg.evaluate({"a": 9, "b": 9}) is False

    def test_empty_group_returns_true(self):
        cg = ConditionGroup()
        assert cg.evaluate({}) is True


# ---------------------------------------------------------------------------
# 21.3 Debugger Tests
# ---------------------------------------------------------------------------

class TestConversationDebugger:
    def _simple_flow(self) -> ConversationFlow:
        flow = ConversationFlow(name="Debug Flow")
        start = ConvNode(node_type=ConvNodeType.START, name="Start")
        resp = ConvNode(node_type=ConvNodeType.RESPONSE, name="Hello",
                        response_text="Hi there!")
        end = ConvNode(node_type=ConvNodeType.END, name="End")
        flow.add_node(start); flow.add_node(resp); flow.add_node(end)
        flow.connect(start.node_id, resp.node_id)
        flow.connect(resp.node_id, end.node_id)
        return flow

    def test_step_through(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        steps = dbg.step_through({})
        assert len(steps) >= 2
        assert all(s.status == DebugStepStatus.COMPLETED for s in steps)

    def test_breakpoint_stops_execution(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        resp_id = [n.node_id for n in flow.nodes.values()
                   if n.node_type == ConvNodeType.RESPONSE][0]
        dbg.set_breakpoint(resp_id)
        steps = dbg.step_through({})
        last = steps[-1]
        assert last.output == "BREAKPOINT"

    def test_clear_breakpoint(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        resp_id = [n.node_id for n in flow.nodes.values()
                   if n.node_type == ConvNodeType.RESPONSE][0]
        dbg.set_breakpoint(resp_id)
        dbg.clear_breakpoint(resp_id)
        steps = dbg.step_through({})
        assert not any(s.output == "BREAKPOINT" for s in steps)

    def test_inspect_variables(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        ctx = {"name": "Alice", "score": 85}
        inspection = dbg.inspect_variables(ctx)
        assert inspection["name"]["type"] == "str"
        assert inspection["score"]["type"] == "int"

    def test_simulate_basic(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        turns = dbg.simulate(["Hello"])
        assert len(turns) == 1
        assert turns[0].bot_response == "Hi there!"

    def test_simulate_with_intent_resolver(self):
        flow = ConversationFlow(name="Intent Flow")
        start = ConvNode(node_type=ConvNodeType.START, name="S")
        intent = ConvNode(node_type=ConvNodeType.INTENT, name="I",
                          intents=["billing"])
        resp = ConvNode(node_type=ConvNodeType.RESPONSE, name="R",
                        response_text="Billing help!")
        end = ConvNode(node_type=ConvNodeType.END, name="E")
        flow.add_node(start); flow.add_node(intent)
        flow.add_node(resp); flow.add_node(end)
        flow.connect(start.node_id, intent.node_id)
        flow.connect(intent.node_id, resp.node_id)
        flow.connect(resp.node_id, end.node_id)

        dbg = ConversationDebugger(flow)
        resolver = lambda text: ("billing", {})
        turns = dbg.simulate(["I have a billing question"], intent_resolver=resolver)
        assert turns[0].matched_intent == "billing"

    def test_test_case_pass(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        tc = TestCase(name="Basic test",
                      turns=[{"user": "hi", "expected_response": "Hi there!"}])
        dbg.add_test_case(tc)
        result = dbg.run_test_case(tc.test_id)
        assert result.passed is True

    def test_test_case_fail(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        tc = TestCase(name="Fail test",
                      turns=[{"user": "hi", "expected_response": "Wrong answer"}])
        dbg.add_test_case(tc)
        result = dbg.run_test_case(tc.test_id)
        assert result.passed is False
        assert result.failure_reason is not None

    def test_run_all_tests(self):
        flow = self._simple_flow()
        dbg = ConversationDebugger(flow)
        tc1 = TestCase(name="Pass", turns=[{"user": "hi", "expected_response": "Hi there!"}])
        tc2 = TestCase(name="Fail", turns=[{"user": "hi", "expected_response": "Nope"}])
        dbg.add_test_case(tc1); dbg.add_test_case(tc2)
        results = dbg.run_all_tests()
        assert results["total"] == 2
        assert results["passed"] == 1
        assert results["failed"] == 1


# ---------------------------------------------------------------------------
# 21.5 A/B Testing Tests
# ---------------------------------------------------------------------------

class TestABTesting:
    def test_create_experiment(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["flow-a", "flow-b"])
        assert len(exp.variants) == 2
        assert abs(sum(v.traffic_pct for v in exp.variants) - 100.0) < 0.01

    def test_custom_split(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b", "c"], [60.0, 30.0, 10.0])
        assert exp.variants[0].traffic_pct == 60.0

    def test_invalid_split_raises(self):
        ab = ABTestingFramework()
        with pytest.raises(AssertionError):
            ab.create_experiment("Test", ["a", "b"], [60.0, 60.0])

    def test_assign_variant(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        v = ab.assign_variant(exp.experiment_id, "session-1")
        assert v is not None
        assert v.sessions == 1

    def test_same_session_same_variant(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        v1 = ab.assign_variant(exp.experiment_id, "sess-x")
        v2 = ab.assign_variant(exp.experiment_id, "sess-x")
        assert v1.variant_id == v2.variant_id

    def test_record_conversion(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        ab.assign_variant(exp.experiment_id, "s1")
        assert ab.record_conversion(exp.experiment_id, "s1") is True

    def test_significance_insufficient_data(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        sig = ab.check_significance(exp.experiment_id)
        assert sig["comparisons"][0]["p_value"] == 1.0

    def test_auto_winner_insufficient_sessions(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        winner = ab.auto_select_winner(exp.experiment_id)
        assert winner is None

    def test_auto_winner_with_enough_data(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.min_sessions = 10
        exp.start()
        # Simulate sessions: control 50% conversion, treatment 80%
        for i in range(10):
            ab.assign_variant(exp.experiment_id, f"ctrl-{i}")
            ab._session_assignments[f"ctrl-{i}"] = exp.variants[0].variant_id
            exp.variants[0].sessions += 1
            if i < 5:
                exp.variants[0].conversions += 1
        for i in range(10):
            ab.assign_variant(exp.experiment_id, f"treat-{i}")
            ab._session_assignments[f"treat-{i}"] = exp.variants[1].variant_id
            exp.variants[1].sessions += 1
            if i < 8:
                exp.variants[1].conversions += 1
        winner = ab.auto_select_winner(exp.experiment_id)
        # Winner should be declared (either by significance or best metric)
        assert winner is not None

    def test_comparison_report(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        exp.start()
        report = ab.get_comparison_report(exp.experiment_id)
        assert "variants" in report
        assert "significance" in report

    def test_not_running_returns_none(self):
        ab = ABTestingFramework()
        exp = ab.create_experiment("Test", ["a", "b"])
        # Not started
        v = ab.assign_variant(exp.experiment_id, "s1")
        assert v is None


# ---------------------------------------------------------------------------
# 21.6 Template Tests
# ---------------------------------------------------------------------------

class TestConvTemplates:
    def test_all_templates_available(self):
        assert set(CONV_TEMPLATES.keys()) == {
            "customer_support", "appointment_booking",
            "lead_qualification", "faq_bot",
        }

    def test_templates_are_valid(self):
        for name in CONV_TEMPLATES:
            flow = get_conv_template(name)
            errors = flow.validate()
            assert errors == [], f"{name}: {errors}"

    def test_templates_have_start(self):
        for name in CONV_TEMPLATES:
            flow = get_conv_template(name)
            starts = [n for n in flow.nodes.values() if n.node_type == ConvNodeType.START]
            assert len(starts) == 1

    def test_templates_have_end(self):
        for name in CONV_TEMPLATES:
            flow = get_conv_template(name)
            ends = [n for n in flow.nodes.values() if n.node_type == ConvNodeType.END]
            assert len(ends) >= 1

    def test_templates_have_tags(self):
        for name in CONV_TEMPLATES:
            flow = get_conv_template(name)
            assert len(flow.tags) > 0

    def test_unknown_template_raises(self):
        with pytest.raises(KeyError):
            get_conv_template("nonexistent")

    def test_customer_support_has_handoff(self):
        flow = get_conv_template("customer_support")
        handoffs = [n for n in flow.nodes.values() if n.node_type == ConvNodeType.HANDOFF]
        assert len(handoffs) >= 1

    def test_lead_qualification_has_condition(self):
        flow = get_conv_template("lead_qualification")
        conds = [n for n in flow.nodes.values() if n.node_type == ConvNodeType.CONDITION]
        assert len(conds) >= 1

    def test_appointment_booking_has_slot_filling(self):
        flow = get_conv_template("appointment_booking")
        slots = [n for n in flow.nodes.values() if n.node_type == ConvNodeType.SLOT_FILLING]
        assert len(slots) >= 1

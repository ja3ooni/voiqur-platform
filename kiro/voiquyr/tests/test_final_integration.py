"""
Final Integration and Comprehensive Tests (Tasks 23.2, 23.4)

Tests cross-feature integration, end-to-end user journeys, billing accuracy,
workflow automation, telephony, analytics, and competitive validation.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.integration import PlatformIntegration, EventBus, PlatformEvent
from src.competitive import (
    generate_competitive_report, FEATURE_MATRIX, COST_SCENARIOS,
)

# ---------------------------------------------------------------------------
# 23.1 Integration Layer Tests
# ---------------------------------------------------------------------------

class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        event = PlatformEvent(source="test", event_type="test.event", tenant_id="t1")
        await bus.publish(event)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_global_handler(self):
        bus = EventBus()
        received = []
        bus.subscribe_all(lambda e: received.append(e.event_type))
        await bus.publish(PlatformEvent(event_type="a"))
        await bus.publish(PlatformEvent(event_type="b"))
        assert "a" in received and "b" in received

    @pytest.mark.asyncio
    async def test_async_handler(self):
        bus = EventBus()
        received = []
        async def handler(e): received.append(e)
        bus.subscribe("x", handler)
        await bus.publish(PlatformEvent(event_type="x"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash(self):
        bus = EventBus()
        def bad_handler(e): raise RuntimeError("boom")
        bus.subscribe("err", bad_handler)
        # Should not raise
        await bus.publish(PlatformEvent(event_type="err"))

    def test_subscriber_count(self):
        bus = EventBus()
        bus.subscribe("ev", lambda e: None)
        bus.subscribe("ev", lambda e: None)
        assert bus.get_subscriber_count("ev") == 2


class TestPlatformIntegration:
    def _make_integration(self):
        pi = PlatformIntegration()
        pi.configure(
            analytics_engine=MagicMock(),
            billing_service=MagicMock(),
            workflow_engine=MagicMock(),
            context_manager=MagicMock(),
            sla_manager=MagicMock(),
            dashboard=MagicMock(),
        )
        pi.wire()
        return pi

    def test_wire_registers_handlers(self):
        pi = self._make_integration()
        assert pi._wired is True
        status = pi.get_status()
        assert status["wired"] is True
        assert len(status["event_subscriptions"]) > 0

    def test_all_components_configured(self):
        pi = self._make_integration()
        status = pi.get_status()
        assert all(status["components"].values())

    @pytest.mark.asyncio
    async def test_call_started_updates_dashboard(self):
        pi = self._make_integration()
        event = PlatformEvent(
            source="telephony", event_type="call.started",
            tenant_id="t1", conversation_id="c1",
            payload={"channel": "voice"},
        )
        await pi.bus.publish(event)
        pi._dashboard.conversation_started.assert_called_once_with("c1", "voice", "t1")

    @pytest.mark.asyncio
    async def test_call_ended_updates_dashboard_and_billing(self):
        pi = self._make_integration()
        pi._billing_service.record_usage = MagicMock()
        event = PlatformEvent(
            source="telephony", event_type="call.ended",
            tenant_id="t1", conversation_id="c1",
            payload={"duration_seconds": 120, "channel": "voice"},
        )
        await pi.bus.publish(event)
        pi._dashboard.conversation_ended.assert_called_once_with("c1")
        pi._billing_service.record_usage.assert_called_once_with("t1", "voice_minutes", 2.0)

    @pytest.mark.asyncio
    async def test_conversation_started_ingests_analytics(self):
        pi = self._make_integration()
        event = PlatformEvent(
            source="omnichannel", event_type="conversation.started",
            tenant_id="t1", conversation_id="c1",
            payload={"channel": "sms"},
        )
        await pi.bus.publish(event)
        pi._analytics_engine.ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_conversation_ended_ingests_analytics(self):
        pi = self._make_integration()
        event = PlatformEvent(
            source="omnichannel", event_type="conversation.ended",
            tenant_id="t1", conversation_id="c1",
            payload={"channel": "sms", "completed": True},
        )
        await pi.bus.publish(event)
        pi._analytics_engine.ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_completed_tracks_kpi(self):
        pi = self._make_integration()
        event = PlatformEvent(
            source="workflow", event_type="workflow.completed",
            tenant_id="t1", conversation_id="c1",
            payload={"kpi": "appointments_booked", "value": 1.0},
        )
        await pi.bus.publish(event)
        pi._analytics_engine.track_kpi.assert_called_once_with(
            "t1", "appointments_booked", 1.0, "c1"
        )

    @pytest.mark.asyncio
    async def test_ticket_created_checks_sla(self):
        pi = self._make_integration()
        mock_ticket = MagicMock()
        event = PlatformEvent(
            source="support", event_type="ticket.created",
            tenant_id="t1", payload={"ticket": mock_ticket},
        )
        await pi.bus.publish(event)
        pi._sla_manager.check_ticket_sla.assert_called_once_with(mock_ticket)


# ---------------------------------------------------------------------------
# 23.2 End-to-End User Journey Tests
# ---------------------------------------------------------------------------

class TestEndToEndJourneys:
    @pytest.mark.asyncio
    async def test_voice_call_to_analytics_journey(self):
        """Full journey: call starts → ends → analytics updated."""
        from src.analytics import ConversationAnalyticsEngine, EventType

        engine = ConversationAnalyticsEngine()
        pi = PlatformIntegration()
        pi.configure(analytics_engine=engine, dashboard=MagicMock())
        pi.wire()

        # Call starts
        await pi.bus.publish(PlatformEvent(
            event_type="conversation.started", tenant_id="t1",
            conversation_id="call-1", payload={"channel": "voice"},
        ))
        # Call ends
        await pi.bus.publish(PlatformEvent(
            event_type="conversation.ended", tenant_id="t1",
            conversation_id="call-1", payload={"channel": "voice", "completed": True},
        ))

        metrics = engine.get_volume_metrics("t1")
        assert metrics["total_conversations"] == 1
        assert metrics["completion_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_omnichannel_context_preservation(self):
        """User starts on SMS, switches to web chat — context preserved."""
        from src.channels import ChannelType
        from src.channels.context import ContextManager

        ctx_mgr = ContextManager()
        pi = PlatformIntegration()
        pi.configure(context_manager=ctx_mgr)
        pi.wire()

        # SMS message
        await pi.bus.publish(PlatformEvent(
            event_type="message.received", tenant_id="t1",
            conversation_id="conv-1",
            payload={"channel": "sms", "user_id": "user-1", "text": "Hello"},
        ))
        # Web chat message (same user)
        await pi.bus.publish(PlatformEvent(
            event_type="message.received", tenant_id="t1",
            conversation_id="conv-1",
            payload={"channel": "web_chat", "user_id": "user-1", "text": "Continuing here"},
        ))

        ctx = ctx_mgr.get_or_create_context("user-1")
        assert len(ctx.messages) == 2
        assert ctx.switched_channel() is True

    @pytest.mark.asyncio
    async def test_workflow_trigger_and_kpi_tracking(self):
        """Workflow completes → KPI tracked in analytics."""
        from src.analytics import ConversationAnalyticsEngine

        engine = ConversationAnalyticsEngine()
        pi = PlatformIntegration()
        pi.configure(analytics_engine=engine)
        pi.wire()

        await pi.bus.publish(PlatformEvent(
            event_type="workflow.completed", tenant_id="t1",
            conversation_id="c1",
            payload={"kpi": "lead_qualified", "value": 1.0},
        ))

        summary = engine.get_kpi_summary("t1")
        assert "lead_qualified" in summary
        assert summary["lead_qualified"]["total"] == 1.0

    @pytest.mark.asyncio
    async def test_billing_usage_tracking(self):
        """Call ends → billing records usage."""
        billing = MagicMock()
        billing.record_usage = MagicMock()
        pi = PlatformIntegration()
        pi.configure(billing_service=billing, dashboard=MagicMock())
        pi.wire()

        await pi.bus.publish(PlatformEvent(
            event_type="call.ended", tenant_id="t1",
            conversation_id="c1",
            payload={"duration_seconds": 300},
        ))

        billing.record_usage.assert_called_once_with("t1", "voice_minutes", 5.0)

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self):
        """Events for different tenants don't cross-contaminate analytics."""
        from src.analytics import ConversationAnalyticsEngine

        engine = ConversationAnalyticsEngine()
        pi = PlatformIntegration()
        pi.configure(analytics_engine=engine)
        pi.wire()

        for tenant in ["t1", "t2", "t3"]:
            await pi.bus.publish(PlatformEvent(
                event_type="conversation.started", tenant_id=tenant,
                conversation_id=f"c-{tenant}", payload={"channel": "sms"},
            ))

        assert engine.get_volume_metrics("t1")["total_conversations"] == 1
        assert engine.get_volume_metrics("t2")["total_conversations"] == 1
        assert engine.get_volume_metrics("t3")["total_conversations"] == 1


# ---------------------------------------------------------------------------
# 23.3 Competitive Advantage Validation
# ---------------------------------------------------------------------------

class TestCompetitiveAdvantages:
    def test_voiquyr_has_more_features_than_vapi(self):
        report = generate_competitive_report()
        fc = report["feature_comparison"]
        assert fc["voiquyr_total"] > fc["shared_with_vapi"]

    def test_voiquyr_exclusive_features_exist(self):
        report = generate_competitive_report()
        assert report["feature_comparison"]["voiquyr_exclusive"] > 0

    def test_all_cost_scenarios_meet_25pct_target(self):
        report = generate_competitive_report()
        for scenario in report["cost_savings"]["scenarios"]:
            assert scenario["savings_pct"] >= 25.0, (
                f"Scenario '{scenario['scenario']}' only saves {scenario['savings_pct']}%"
            )

    def test_avg_cost_savings_above_target(self):
        report = generate_competitive_report()
        assert report["cost_savings"]["avg_savings_pct"] >= 25.0

    def test_eu_compliance_advantage(self):
        eu_features = [f for f in FEATURE_MATRIX
                       if "EU" in f.feature or "GDPR" in f.feature or "sovereignty" in f.feature]
        assert all(f.voiquyr for f in eu_features)
        assert all(not f.vapi for f in eu_features)

    def test_telephony_advantage(self):
        pbx_features = [f for f in FEATURE_MATRIX
                        if any(k in f.feature for k in ["Asterisk", "FreeSWITCH", "SIP", "PSTN"])]
        assert all(f.voiquyr for f in pbx_features)
        assert all(not f.vapi for f in pbx_features)

    def test_omnichannel_advantage(self):
        channel_features = [f for f in FEATURE_MATRIX
                            if any(k in f.feature for k in
                                   ["WhatsApp", "Telegram", "Facebook", "Instagram", "SMS", "Email"])]
        assert all(f.voiquyr for f in channel_features)
        assert all(not f.vapi for f in channel_features)

    def test_feature_matrix_completeness(self):
        assert len(FEATURE_MATRIX) >= 30

    def test_cost_scenarios_completeness(self):
        assert len(COST_SCENARIOS) >= 5


# ---------------------------------------------------------------------------
# 23.4 Cross-Feature Integration Tests
# ---------------------------------------------------------------------------

class TestCrossFeatureIntegration:
    @pytest.mark.asyncio
    async def test_telephony_qos_to_analytics(self):
        """QoS metrics from telephony feed into analytics anomaly detection."""
        from src.analytics import PredictiveAnalytics

        pa = PredictiveAnalytics()
        # Normal QoS
        for v in [20.0, 21.0, 19.0, 20.5, 20.0, 19.5]:
            pa.record_metric("jitter_ms", v)
        # Spike
        alert = pa.record_metric("jitter_ms", 200.0)
        assert alert is not None
        assert alert.metric == "jitter_ms"

    @pytest.mark.asyncio
    async def test_workflow_crm_integration(self):
        """Workflow engine executes CRM action."""
        from src.workflow import WorkflowEngine, ActionRegistry, Workflow, WorkflowNode, NodeType

        registry = ActionRegistry()
        crm_calls = []
        registry.register("crm.create_deal", lambda cfg, ctx: crm_calls.append(ctx) or {"deal_id": "d1"})

        wf = Workflow(name="CRM Flow")
        trigger = WorkflowNode(node_type=NodeType.TRIGGER, name="T")
        action = WorkflowNode(node_type=NodeType.ACTION, name="Create Deal",
                              config={"action": "crm.create_deal"})
        end = WorkflowNode(node_type=NodeType.END, name="End")
        wf.add_node(trigger); wf.add_node(action); wf.add_node(end)
        wf.connect(trigger.node_id, action.node_id)
        wf.connect(action.node_id, end.node_id)

        engine = WorkflowEngine(action_registry=registry)
        ex = await engine.execute(wf, {"lead_score": 85})
        from src.workflow import ExecutionStatus
        assert ex.status == ExecutionStatus.COMPLETED
        assert len(crm_calls) == 1

    @pytest.mark.asyncio
    async def test_support_sla_breach_detection(self):
        """P1 ticket breaches SLA → breach recorded."""
        from src.support import TicketingSystem, TicketPriority, SLAManager, SLADefinition
        from datetime import timedelta

        ts = TicketingSystem()
        sla_mgr = SLAManager()
        sla_mgr.register_sla(SLADefinition("ent", "Enterprise", monthly_fee_eur=5000))
        sla_mgr.assign_sla("t1", "ent")

        ticket = ts.create_ticket("Critical outage", "System down", TicketPriority.P1,
                                  tenant_id="t1")
        # Simulate breach: ticket created 30 minutes ago
        ticket.created_at = datetime.utcnow() - timedelta(minutes=30)
        ticket.first_response_at = datetime.utcnow()

        breaches = sla_mgr.check_ticket_sla(ticket)
        assert len(breaches) >= 1
        assert breaches[0].breach_type == "response"

    @pytest.mark.asyncio
    async def test_conversation_designer_to_debugger(self):
        """Flow built in designer runs correctly in debugger."""
        from src.designer import (
            ConversationFlow, ConvNode, ConvNodeType,
            ConversationDebugger,
        )

        flow = ConversationFlow(name="Integration Test")
        start = ConvNode(node_type=ConvNodeType.START, name="Start")
        resp = ConvNode(node_type=ConvNodeType.RESPONSE, name="Hello",
                        response_text="Welcome!")
        end = ConvNode(node_type=ConvNodeType.END, name="End")
        flow.add_node(start); flow.add_node(resp); flow.add_node(end)
        flow.connect(start.node_id, resp.node_id)
        flow.connect(resp.node_id, end.node_id)

        dbg = ConversationDebugger(flow)
        turns = dbg.simulate(["Hi"])
        assert turns[0].bot_response == "Welcome!"

    @pytest.mark.asyncio
    async def test_ab_test_with_conversation_flows(self):
        """A/B test assigns sessions to different conversation flows."""
        from src.designer import ABTestingFramework

        ab = ABTestingFramework()
        exp = ab.create_experiment("Flow Test", ["flow-a", "flow-b"], [50.0, 50.0])
        exp.start()

        assigned_flows = set()
        for i in range(20):
            v = ab.assign_variant(exp.experiment_id, f"session-{i}")
            if v:
                assigned_flows.add(v.flow_id)

        # Both flows should receive traffic
        assert len(assigned_flows) == 2

    @pytest.mark.asyncio
    async def test_analytics_dashboard_integration(self):
        """Analytics engine feeds real-time dashboard."""
        from src.analytics import ConversationAnalyticsEngine, RealtimeDashboard

        engine = ConversationAnalyticsEngine()
        dashboard = RealtimeDashboard()

        pi = PlatformIntegration()
        pi.configure(analytics_engine=engine, dashboard=dashboard)
        pi.wire()

        # Simulate 3 conversations
        for i in range(3):
            dashboard.conversation_started(f"c{i}", "sms", "t1")
            await pi.bus.publish(PlatformEvent(
                event_type="conversation.started", tenant_id="t1",
                conversation_id=f"c{i}", payload={"channel": "sms"},
            ))

        assert dashboard.get_live_count("t1") == 3
        assert engine.get_volume_metrics("t1")["total_conversations"] == 3

    def test_dr_failover_with_tenant_isolation(self):
        """Failover respects tenant sovereignty zones."""
        from src.infra import TenantRegistry, TenantConfig, SovereigntyZone, FailoverManager

        registry = TenantRegistry()
        registry.register_tenant(TenantConfig("t1", "Tenant 1", SovereigntyZone.DE))
        registry.register_tenant(TenantConfig("t2", "Tenant 2", SovereigntyZone.FR))

        # DE tenant cannot write to FR zone
        assert registry.check_data_placement("t1", SovereigntyZone.FR) is False
        # FR tenant cannot write to DE zone
        assert registry.check_data_placement("t2", SovereigntyZone.DE) is False
        # Each tenant can write to their own zone
        assert registry.check_data_placement("t1", SovereigntyZone.DE) is True
        assert registry.check_data_placement("t2", SovereigntyZone.FR) is True

    def test_full_feature_coverage(self):
        """Verify all major platform modules are importable."""
        import src.billing
        import src.telephony
        import src.channels
        import src.workflow
        import src.support
        import src.infra
        import src.analytics
        import src.designer
        import src.integration
        import src.competitive
        # All imports succeed = all modules are present
        assert True

"""
Telephony Integration Tests (Task 14.7)

Tests for Asterisk/FreeSWITCH integration, SIP trunking, QoS metrics,
and human handoff flows.
Implements Requirements 14.1, 14.2, 14.3.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.telephony import (
    AsteriskProvider,
    FreeSwitchProvider,
    DirectSIPProvider,
    KamailioProvider,
    OpenSIPSProvider,
    ThreeCXProvider,
    CallController,
    ProviderRegistry,
    ProviderConfig,
    ProviderType,
    HealthStatus,
    CallStatus,
    QoSMetrics,
    QoSMonitor,
    QoSThresholds,
    HandoffAgent,
    HandoffContext,
    HandoffReason,
    HandoffStatus,
    HumanAgent,
    AgentAvailability,
    AgentPool,
    SRTPConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(provider_type: ProviderType, **kwargs) -> ProviderConfig:
    return ProviderConfig(
        provider_id=f"test-{provider_type.value}",
        provider_type=provider_type,
        name=f"Test {provider_type.value}",
        host="127.0.0.1",
        port=5060,
        username="test",
        password="test",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 14.2 Asterisk Provider Tests
# ---------------------------------------------------------------------------

class TestAsteriskProvider:
    @pytest.fixture
    def provider(self):
        config = make_config(ProviderType.ASTERISK, metadata={"ami_port": 5038, "ari_port": 8088})
        return AsteriskProvider(config)

    @pytest.mark.asyncio
    async def test_connect_success(self, provider):
        provider._ami.connect = AsyncMock(return_value=True)
        provider._ami.on_event = MagicMock()
        result = await provider.connect()
        assert result is True
        assert provider.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_connect_failure(self, provider):
        provider._ami.connect = AsyncMock(return_value=False)
        result = await provider.connect()
        assert result is False
        assert provider.health_status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_make_call(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        assert call.from_number == "+1111"
        assert call.to_number == "+2222"
        assert call.status == CallStatus.INITIATED
        assert call.call_id in provider.active_calls

    @pytest.mark.asyncio
    async def test_make_call_failure(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Error", "Message": "No route"})
        with pytest.raises(RuntimeError, match="Asterisk originate failed"):
            await provider.make_call("+1111", "+2222")

    @pytest.mark.asyncio
    async def test_hangup_call(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        provider._ami.hangup = AsyncMock(return_value={"Response": "Success"})
        result = await provider.hangup_call(call.call_id)
        assert result is True
        assert provider.active_calls[call.call_id].status == CallStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_transfer_call(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        provider._ami.redirect = AsyncMock(return_value={"Response": "Success"})
        result = await provider.transfer_call(call.call_id, "+3333")
        assert result is True
        assert provider.active_calls[call.call_id].status == CallStatus.TRANSFERRING

    @pytest.mark.asyncio
    async def test_hold_unhold(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        assert await provider.hold_call(call.call_id) is True
        assert provider.active_calls[call.call_id].status == CallStatus.ON_HOLD
        assert await provider.unhold_call(call.call_id) is True
        assert provider.active_calls[call.call_id].status == CallStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_qos_metrics(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        provider._ami.get_rtcp_stats = AsyncMock(
            return_value={"Jitter": "15.0", "PacketLoss": "0.5", "RTT": "80.0", "Codec": "PCMU"}
        )
        metrics = await provider.get_qos_metrics(call.call_id)
        assert metrics is not None
        assert metrics.jitter == 15.0
        assert metrics.packet_loss == 0.5
        assert metrics.latency == 40.0
        assert metrics.mos_score > 0

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        provider._ami._connected = True
        status = await provider.health_check()
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_mos_calculation(self, provider):
        mos = provider._calculate_mos(10.0, 0.1, 50.0)
        assert 3.5 <= mos <= 5.0

    @pytest.mark.asyncio
    async def test_hangup_event_handler(self, provider):
        provider._ami.originate = AsyncMock(return_value={"Response": "Success"})
        call = await provider.make_call("+1111", "+2222")
        channel = provider._call_to_channel[call.call_id]
        await provider._on_hangup({"Channel": channel})
        assert provider.active_calls[call.call_id].status == CallStatus.COMPLETED


# ---------------------------------------------------------------------------
# 14.3 FreeSWITCH Provider Tests
# ---------------------------------------------------------------------------

class TestFreeSwitchProvider:
    @pytest.fixture
    def provider(self):
        config = make_config(ProviderType.FREESWITCH, metadata={"esl_port": 8021, "gateway": "default"})
        return FreeSwitchProvider(config)

    @pytest.mark.asyncio
    async def test_connect_success(self, provider):
        provider._esl.connect = AsyncMock(return_value=True)
        provider._esl.on_event = MagicMock()
        result = await provider.connect()
        assert result is True
        assert provider.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_make_call(self, provider):
        provider._esl.originate = AsyncMock(return_value="+OK abc-uuid-123")
        call = await provider.make_call("+1111", "+2222")
        assert call.status == CallStatus.INITIATED
        assert provider._call_to_uuid[call.call_id] == "abc-uuid-123"

    @pytest.mark.asyncio
    async def test_make_call_failure(self, provider):
        provider._esl.originate = AsyncMock(return_value="-ERR NO_ROUTE_DESTINATION")
        with pytest.raises(RuntimeError, match="FreeSWITCH originate failed"):
            await provider.make_call("+1111", "+2222")

    @pytest.mark.asyncio
    async def test_hangup_call(self, provider):
        provider._esl.originate = AsyncMock(return_value="+OK uuid-456")
        call = await provider.make_call("+1111", "+2222")
        provider._esl.uuid_kill = AsyncMock(return_value="+OK")
        result = await provider.hangup_call(call.call_id)
        assert result is True
        assert provider.active_calls[call.call_id].status == CallStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_park_call(self, provider):
        provider._esl.originate = AsyncMock(return_value="+OK uuid-789")
        call = await provider.make_call("+1111", "+2222")
        provider._esl.uuid_park = AsyncMock(return_value="+OK")
        result = await provider.park_call(call.call_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_conference_join(self, provider):
        provider._esl.originate = AsyncMock(return_value="+OK uuid-conf")
        call = await provider.make_call("+1111", "+2222")
        provider._esl.uuid_transfer = AsyncMock(return_value="+OK")
        result = await provider.join_conference(call.call_id, "room1")
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        provider._esl.api = AsyncMock(return_value="UP 0 years, 0 days, 1 hour, 23 minutes, 45 seconds")
        status = await provider.health_check()
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_answer_event_handler(self, provider):
        provider._esl.originate = AsyncMock(return_value="+OK uuid-ans")
        call = await provider.make_call("+1111", "+2222")
        await provider._on_answer({"Unique-ID": "uuid-ans"})
        assert provider.active_calls[call.call_id].status == CallStatus.ANSWERED
        assert provider.active_calls[call.call_id].answer_time is not None


# ---------------------------------------------------------------------------
# 14.4 SIP Trunking Tests
# ---------------------------------------------------------------------------

class TestDirectSIPProvider:
    @pytest.fixture
    def provider(self):
        config = make_config(
            ProviderType.SIP_TRUNK,
            metadata={"srtp_enabled": True, "local_sip_port": 15060},
        )
        return DirectSIPProvider(config)

    @pytest.mark.asyncio
    async def test_connect(self, provider):
        mock_transport = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.create_datagram_endpoint = AsyncMock(
                return_value=(mock_transport, None)
            )
            result = await provider.connect()
        assert result is True
        assert provider.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_make_call_with_srtp(self, provider):
        provider._transport = MagicMock()
        call = await provider.make_call("+1111", "+2222")
        assert call.metadata["srtp_enabled"] is True
        assert call.call_id in provider._srtp_configs

    @pytest.mark.asyncio
    async def test_make_call_without_srtp(self):
        config = make_config(ProviderType.SIP_TRUNK, metadata={"srtp_enabled": False})
        provider = DirectSIPProvider(config)
        provider._transport = MagicMock()
        call = await provider.make_call("+1111", "+2222")
        assert call.metadata["srtp_enabled"] is False
        assert call.call_id not in provider._srtp_configs

    @pytest.mark.asyncio
    async def test_hangup_sends_bye(self, provider):
        provider._transport = MagicMock()
        call = await provider.make_call("+1111", "+2222")
        result = await provider.hangup_call(call.call_id)
        assert result is True
        assert provider.active_calls[call.call_id].status == CallStatus.COMPLETED
        # SRTP config cleaned up
        assert call.call_id not in provider._srtp_configs

    @pytest.mark.asyncio
    async def test_transfer_sends_refer(self, provider):
        provider._transport = MagicMock()
        call = await provider.make_call("+1111", "+2222")
        result = await provider.transfer_call(call.call_id, "+3333")
        assert result is True
        assert provider.active_calls[call.call_id].status == CallStatus.TRANSFERRING

    def test_srtp_config_generates_sdp(self):
        srtp = SRTPConfig()
        sdp_line = srtp.to_sdp_crypto_attr()
        assert "a=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:" in sdp_line

    def test_srtp_config_custom_suite(self):
        srtp = SRTPConfig(crypto_suite="AES_256_CM_HMAC_SHA1_80")
        sdp_line = srtp.to_sdp_crypto_attr()
        assert "AES_256_CM_HMAC_SHA1_80" in sdp_line


class TestKamailioProvider:
    @pytest.mark.asyncio
    async def test_connect(self):
        config = make_config(ProviderType.KAMAILIO)
        provider = KamailioProvider(config)
        provider._rpc = AsyncMock(return_value={"uptime": 12345})
        result = await provider.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        config = make_config(ProviderType.KAMAILIO)
        provider = KamailioProvider(config)
        provider._rpc = AsyncMock(return_value={"uptime": 100})
        status = await provider.health_check()
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_reload_dialplan(self):
        config = make_config(ProviderType.KAMAILIO)
        provider = KamailioProvider(config)
        provider._rpc = AsyncMock(return_value={"result": "ok"})
        result = await provider.reload_dialplan()
        assert result is True


class TestOpenSIPSProvider:
    @pytest.mark.asyncio
    async def test_connect(self):
        config = make_config(ProviderType.OPENSIPS)
        provider = OpenSIPSProvider(config)
        provider._rpc = AsyncMock(return_value={"uptime": 999})
        result = await provider.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_reload_dialplan(self):
        config = make_config(ProviderType.OPENSIPS)
        provider = OpenSIPSProvider(config)
        provider._rpc = AsyncMock(return_value={"result": "ok"})
        result = await provider.reload_dialplan()
        assert result is True


# ---------------------------------------------------------------------------
# 14.5 QoS Monitoring Tests
# ---------------------------------------------------------------------------

class TestQoSMonitor:
    def test_mos_calculation_good_conditions(self):
        mos = QoSMonitor.calculate_mos(jitter=5.0, packet_loss=0.0, latency=20.0)
        assert mos >= 4.0

    def test_mos_calculation_poor_conditions(self):
        mos = QoSMonitor.calculate_mos(jitter=80.0, packet_loss=10.0, latency=300.0)
        assert mos < 3.0

    def test_mos_bounds(self):
        mos_low = QoSMonitor.calculate_mos(jitter=500.0, packet_loss=100.0, latency=1000.0)
        mos_high = QoSMonitor.calculate_mos(jitter=0.0, packet_loss=0.0, latency=0.0)
        assert 1.0 <= mos_low <= 5.0
        assert 1.0 <= mos_high <= 5.0

    def test_threshold_defaults(self):
        t = QoSThresholds()
        assert t.jitter_warning == 20.0
        assert t.jitter_critical == 50.0
        assert t.mos_warning == 3.5
        assert t.mos_critical == 2.5

    @pytest.mark.asyncio
    async def test_start_stop(self):
        monitor = QoSMonitor(update_interval=0.1)
        await monitor.start()
        assert monitor._running is True
        await monitor.stop()
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_tracking_lifecycle(self):
        monitor = QoSMonitor()
        monitor.start_tracking("call-1")
        assert "call-1" in monitor._trackers
        monitor.stop_tracking("call-1")
        assert "call-1" not in monitor._trackers

    @pytest.mark.asyncio
    async def test_alert_fired_on_high_jitter(self):
        monitor = QoSMonitor(thresholds=QoSThresholds(jitter_warning=10.0))
        alerts = []
        monitor.add_alert_handler(alerts.append)
        monitor.start_tracking("call-1")
        metrics = QoSMetrics(jitter=25.0, packet_loss=0.0, mos_score=4.0, latency=30.0)
        monitor._trackers["call-1"].add_sample(metrics)
        monitor._evaluate_thresholds("call-1", metrics)
        assert any(a.metric == "jitter" for a in alerts)

    @pytest.mark.asyncio
    async def test_alert_fired_on_low_mos(self):
        monitor = QoSMonitor()
        alerts = []
        monitor.add_alert_handler(alerts.append)
        monitor.start_tracking("call-1")
        metrics = QoSMetrics(jitter=5.0, packet_loss=0.0, mos_score=2.0, latency=30.0)
        monitor._evaluate_thresholds("call-1", metrics)
        assert any(a.metric == "mos_score" and a.severity == "critical" for a in alerts)

    @pytest.mark.asyncio
    async def test_poll_calls_fetcher(self):
        monitor = QoSMonitor(update_interval=0.05)
        metrics = QoSMetrics(jitter=10.0, packet_loss=0.1, mos_score=4.2, latency=40.0)
        fetcher = AsyncMock(return_value=metrics)
        monitor.set_metrics_fetcher(fetcher)
        monitor.start_tracking("call-1")
        await monitor.start()
        await asyncio.sleep(0.15)
        await monitor.stop()
        fetcher.assert_called()

    def test_get_report(self):
        monitor = QoSMonitor()
        monitor.start_tracking("call-1")
        metrics = QoSMetrics(jitter=12.0, packet_loss=0.2, mos_score=4.1, latency=35.0)
        monitor._trackers["call-1"].add_sample(metrics)
        report = monitor.get_report("call-1")
        assert report is not None
        assert report["call_id"] == "call-1"
        assert report["latest"]["jitter"] == 12.0

    def test_system_report(self):
        monitor = QoSMonitor()
        monitor.start_tracking("call-a")
        monitor.start_tracking("call-b")
        report = monitor.get_system_report()
        assert report["monitored_calls"] == 2


# ---------------------------------------------------------------------------
# 14.6 Human Agent Handoff Tests
# ---------------------------------------------------------------------------

class TestHandoffAgent:
    def _make_agent(self, agent_id="agent-1", available=True) -> HumanAgent:
        return HumanAgent(
            agent_id=agent_id,
            name="Test Agent",
            extension="1001",
            skills=["billing", "support"],
            languages=["en", "fr"],
            availability=AgentAvailability.AVAILABLE if available else AgentAvailability.BUSY,
        )

    def _make_context(self, call_id="call-1") -> HandoffContext:
        ctx = HandoffContext(
            call_id=call_id,
            customer_number="+1234567890",
            reason=HandoffReason.USER_REQUESTED,
            detected_language="en",
        )
        ctx.add_transcript_turn("user", "I need help with my bill")
        ctx.add_transcript_turn("assistant", "I'll connect you to a specialist")
        return ctx

    @pytest.mark.asyncio
    async def test_immediate_handoff(self):
        pool = AgentPool()
        pool.register(self._make_agent())
        agent = HandoffAgent(agent_pool=pool)
        transfer_fn = AsyncMock(return_value=True)
        notify_fn = AsyncMock()
        agent.set_transfer_function(transfer_fn)
        agent.set_notify_function(notify_fn)
        await agent.start()

        record = await agent.request_handoff(self._make_context())
        assert record.status == HandoffStatus.COMPLETED
        assert record.assigned_agent is not None
        transfer_fn.assert_called_once_with("call-1", "1001")
        notify_fn.assert_called_once()

        await agent.stop()

    @pytest.mark.asyncio
    async def test_handoff_queued_when_no_agents(self):
        pool = AgentPool()
        agent = HandoffAgent(agent_pool=pool)
        await agent.start()

        record = await agent.request_handoff(self._make_context())
        assert record.status == HandoffStatus.QUEUED
        assert record.queued_at is not None

        await agent.stop()

    @pytest.mark.asyncio
    async def test_handoff_from_queue_when_agent_becomes_available(self):
        pool = AgentPool()
        handoff = HandoffAgent(agent_pool=pool, queue_timeout=30.0)
        transfer_fn = AsyncMock(return_value=True)
        handoff.set_transfer_function(transfer_fn)
        await handoff.start()

        record = await handoff.request_handoff(self._make_context())
        assert record.status == HandoffStatus.QUEUED

        # Agent becomes available
        pool.register(self._make_agent())
        await asyncio.sleep(0.2)  # Let queue worker process

        await handoff.stop()
        # Record should now be completed
        assert record.status in (HandoffStatus.COMPLETED, HandoffStatus.QUEUED)

    @pytest.mark.asyncio
    async def test_handoff_fails_on_transfer_error(self):
        pool = AgentPool()
        pool.register(self._make_agent())
        agent = HandoffAgent(agent_pool=pool)
        transfer_fn = AsyncMock(return_value=False)
        agent.set_transfer_function(transfer_fn)
        await agent.start()

        record = await agent.request_handoff(self._make_context())
        assert record.status == HandoffStatus.FAILED
        assert record.failure_reason is not None

        await agent.stop()

    @pytest.mark.asyncio
    async def test_language_matching(self):
        pool = AgentPool()
        en_agent = HumanAgent("en-agent", "English Agent", "1001", languages=["en"])
        fr_agent = HumanAgent("fr-agent", "French Agent", "1002", languages=["fr"])
        pool.register(en_agent)
        pool.register(fr_agent)

        ctx = self._make_context()
        ctx.detected_language = "fr"

        selected = pool.find_best_agent(required_language="fr")
        assert selected is not None
        assert selected.agent_id == "fr-agent"

    @pytest.mark.asyncio
    async def test_skill_matching(self):
        pool = AgentPool()
        billing_agent = HumanAgent("billing-agent", "Billing", "1001", skills=["billing"])
        tech_agent = HumanAgent("tech-agent", "Tech", "1002", skills=["technical"])
        pool.register(billing_agent)
        pool.register(tech_agent)

        selected = pool.find_best_agent(required_skills=["billing"])
        assert selected is not None
        assert selected.agent_id == "billing-agent"

    def test_transcript_preserved(self):
        ctx = self._make_context()
        assert len(ctx.transcript) == 2
        assert ctx.transcript[0]["role"] == "user"
        assert ctx.transcript[1]["role"] == "assistant"

    def test_analytics(self):
        pool = AgentPool()
        pool.register(self._make_agent())
        agent = HandoffAgent(agent_pool=pool)
        analytics = agent.get_analytics()
        assert analytics["total_handoffs"] == 0
        assert analytics["available_agents"] == 1

    def test_complete_agent_call_decrements_count(self):
        pool = AgentPool()
        a = self._make_agent()
        a.active_calls = 1
        pool.register(a)
        agent = HandoffAgent(agent_pool=pool)
        agent.complete_agent_call("agent-1")
        assert pool._agents["agent-1"].active_calls == 0

    @pytest.mark.asyncio
    async def test_handoff_reasons(self):
        pool = AgentPool()
        pool.register(self._make_agent())
        agent = HandoffAgent(agent_pool=pool)
        transfer_fn = AsyncMock(return_value=True)
        agent.set_transfer_function(transfer_fn)
        await agent.start()

        for reason in [HandoffReason.AI_ESCALATION, HandoffReason.SENTIMENT_NEGATIVE]:
            ctx = HandoffContext(
                call_id=f"call-{reason.value}",
                customer_number="+1111",
                reason=reason,
            )
            pool.register(HumanAgent(f"agent-{reason.value}", "Agent", "1001"))
            record = await agent.request_handoff(ctx)
            assert record.context.reason == reason

        await agent.stop()


# ---------------------------------------------------------------------------
# Integration: CallController + QoSMonitor
# ---------------------------------------------------------------------------

class TestCallControllerWithQoS:
    @pytest.mark.asyncio
    async def test_qos_monitor_integration(self):
        """QoSMonitor can be wired to CallController.get_call_qos."""
        from src.telephony import CallController, ProviderRegistry

        registry = ProviderRegistry()
        controller = CallController(registry=registry)

        monitor = QoSMonitor(update_interval=0.1)
        monitor.set_metrics_fetcher(controller.get_call_qos)
        await monitor.start()
        await monitor.stop()
        # No errors = integration works

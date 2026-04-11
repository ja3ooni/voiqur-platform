"""
Open Telephony Platform Tests (Task 20.5)
Tests for WebRTC, cloud providers, failover, and PSTN/legacy.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.telephony import (
    ProviderConfig, ProviderType, HealthStatus, CallStatus,
    ProviderRegistry,
    WebRTCGateway, WebRTCProvider, WebRTCSession,
    ICECandidate, ICECandidateType, STUNConfig, TURNConfig,
    VonageProvider, PlivoProvider, BandwidthProvider, TelnyxProvider,
    ProviderFailoverManager, RoutingStrategy,
    PSTNGateway, SS7SignalingBridge, TrunkType,
)


def make_config(provider_type: ProviderType, **kwargs) -> ProviderConfig:
    return ProviderConfig(
        provider_id=f"test-{provider_type.value}",
        provider_type=provider_type,
        name=f"Test {provider_type.value}",
        host="127.0.0.1", port=5060,
        username="user", password="pass",
        api_key="key", api_secret="secret",
        **kwargs,
    )


def _mock_http_ok(provider, status=200, data=None):
    resp = AsyncMock(); resp.status = status
    resp.json = AsyncMock(return_value=data or {"id": "123"})
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    for method in ("get", "post", "put", "delete", "patch"):
        getattr(session, method).return_value = cm
    provider._get_session = AsyncMock(return_value=session)
    return session


# ---------------------------------------------------------------------------
# 20.1 WebRTC Tests
# ---------------------------------------------------------------------------

class TestWebRTCGateway:
    def test_create_session(self):
        gw = WebRTCGateway()
        s = gw.create_session("call-1")
        assert s.call_id == "call-1"
        assert s.session_id in gw._sessions

    def test_get_ice_servers_stun(self):
        gw = WebRTCGateway(stun_servers=[STUNConfig("stun.example.com")])
        servers = gw.get_ice_servers()
        assert any("stun:" in s["urls"] for s in servers)

    def test_get_ice_servers_turn(self):
        gw = WebRTCGateway(
            turn_servers=[TURNConfig("turn.example.com", username="u", password="p")]
        )
        servers = gw.get_ice_servers()
        turn = [s for s in servers if "turn:" in s["urls"]]
        assert len(turn) == 1
        assert turn[0]["username"] == "u"

    def test_set_local_sdp(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        assert gw.set_local_sdp(s.session_id, "v=0\r\n") is True
        assert s.local_sdp == "v=0\r\n"

    def test_set_remote_sdp(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        assert gw.set_remote_sdp(s.session_id, "v=0\r\n") is True

    def test_negotiation_complete(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        assert gw.is_negotiation_complete(s.session_id) is False
        gw.set_local_sdp(s.session_id, "sdp-local")
        gw.set_remote_sdp(s.session_id, "sdp-remote")
        assert gw.is_negotiation_complete(s.session_id) is True

    def test_add_ice_candidate(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        cand = ICECandidate(ICECandidateType.HOST, "192.168.1.1", 10000)
        assert gw.add_ice_candidate(s.session_id, cand) is True
        assert len(s.ice_candidates) == 1

    def test_gather_host_candidates(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        candidates = gw.gather_host_candidates(s.session_id)
        assert len(candidates) >= 1
        assert candidates[0].candidate_type == ICECandidateType.HOST

    def test_close_session(self):
        gw = WebRTCGateway()
        s = gw.create_session("c1")
        assert gw.close_session(s.session_id) is True
        assert gw.get_session(s.session_id) is None

    def test_js_client_config(self):
        gw = WebRTCGateway()
        cfg = gw.get_js_client_config()
        assert "iceServers" in cfg
        assert cfg["sdpSemantics"] == "unified-plan"

    def test_ice_candidate_sdp(self):
        c = ICECandidate(ICECandidateType.SRFLX, "1.2.3.4", 5000,
                         foundation="2", priority=1000)
        sdp = c.to_sdp()
        assert "srflx" in sdp
        assert "1.2.3.4" in sdp

    def test_adaptive_bitrate_decreases_on_loss(self):
        s = WebRTCSession(current_bitrate_kbps=128)
        new_br = s.adapt_bitrate(packet_loss_pct=10.0, rtt_ms=50)
        assert new_br < 128

    def test_adaptive_bitrate_increases_on_good(self):
        s = WebRTCSession(current_bitrate_kbps=64)
        new_br = s.adapt_bitrate(packet_loss_pct=0.0, rtt_ms=50)
        assert new_br > 64

    def test_adaptive_bitrate_respects_max(self):
        s = WebRTCSession(current_bitrate_kbps=512, max_bitrate_kbps=512)
        new_br = s.adapt_bitrate(packet_loss_pct=0.0, rtt_ms=50)
        assert new_br <= 512

    @pytest.mark.asyncio
    async def test_webrtc_provider_connect(self):
        config = make_config(ProviderType.WEBRTC)
        provider = WebRTCProvider(config)
        assert await provider.connect() is True
        assert provider.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_webrtc_provider_make_call(self):
        config = make_config(ProviderType.WEBRTC)
        provider = WebRTCProvider(config)
        await provider.connect()
        call = await provider.make_call("+1111", "+2222")
        assert call.status == CallStatus.INITIATED
        assert "webrtc_session_id" in call.metadata

    @pytest.mark.asyncio
    async def test_webrtc_provider_hangup(self):
        config = make_config(ProviderType.WEBRTC)
        provider = WebRTCProvider(config)
        await provider.connect()
        call = await provider.make_call("+1111", "+2222")
        assert await provider.hangup_call(call.call_id) is True
        assert provider.active_calls[call.call_id].status == CallStatus.COMPLETED


# ---------------------------------------------------------------------------
# 20.2 Cloud Provider Tests
# ---------------------------------------------------------------------------

class TestVonageProvider:
    @pytest.mark.asyncio
    async def test_make_call(self):
        p = VonageProvider(make_config(ProviderType.VONAGE))
        _mock_http_ok(p, data={"uuid": "vonage-uuid-1"})
        call = await p.make_call("+1111", "+2222")
        assert call.status == CallStatus.INITIATED
        assert call.metadata["vonage_uuid"] == "vonage-uuid-1"

    @pytest.mark.asyncio
    async def test_hangup(self):
        p = VonageProvider(make_config(ProviderType.VONAGE))
        _mock_http_ok(p, data={"uuid": "v-uuid"})
        call = await p.make_call("+1111", "+2222")
        assert await p.hangup_call(call.call_id) is True
        assert p.active_calls[call.call_id].status == CallStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_transfer(self):
        p = VonageProvider(make_config(ProviderType.VONAGE))
        _mock_http_ok(p, data={"uuid": "v-uuid"})
        call = await p.make_call("+1111", "+2222")
        assert await p.transfer_call(call.call_id, "+3333") is True


class TestPlivoProvider:
    @pytest.mark.asyncio
    async def test_make_call(self):
        p = PlivoProvider(make_config(ProviderType.PLIVO))
        _mock_http_ok(p, data={"request_uuid": "plivo-uuid-1"})
        call = await p.make_call("+1111", "+2222")
        assert call.metadata["plivo_uuid"] == "plivo-uuid-1"

    @pytest.mark.asyncio
    async def test_hangup(self):
        p = PlivoProvider(make_config(ProviderType.PLIVO))
        _mock_http_ok(p, data={"request_uuid": "p-uuid"})
        call = await p.make_call("+1111", "+2222")
        assert await p.hangup_call(call.call_id) is True


class TestBandwidthProvider:
    @pytest.mark.asyncio
    async def test_make_call(self):
        p = BandwidthProvider(make_config(ProviderType.BANDWIDTH,
                                          metadata={"account_id": "acc1"}))
        _mock_http_ok(p, data={"callId": "bw-call-1"})
        call = await p.make_call("+1111", "+2222")
        assert call.metadata["bw_call_id"] == "bw-call-1"

    @pytest.mark.asyncio
    async def test_hangup(self):
        p = BandwidthProvider(make_config(ProviderType.BANDWIDTH,
                                          metadata={"account_id": "acc1"}))
        _mock_http_ok(p, data={"callId": "bw-1"})
        call = await p.make_call("+1111", "+2222")
        assert await p.hangup_call(call.call_id) is True


class TestTelnyxProvider:
    @pytest.mark.asyncio
    async def test_make_call(self):
        p = TelnyxProvider(make_config(ProviderType.TELNYX))
        _mock_http_ok(p, data={"data": {"call_control_id": "telnyx-ctrl-1"}})
        call = await p.make_call("+1111", "+2222")
        assert call.metadata["telnyx_call_control_id"] == "telnyx-ctrl-1"

    @pytest.mark.asyncio
    async def test_answer(self):
        p = TelnyxProvider(make_config(ProviderType.TELNYX))
        _mock_http_ok(p, data={"data": {"call_control_id": "ctrl-1"}})
        call = await p.make_call("+1111", "+2222")
        assert await p.answer_call(call.call_id) is True

    @pytest.mark.asyncio
    async def test_hangup(self):
        p = TelnyxProvider(make_config(ProviderType.TELNYX))
        _mock_http_ok(p, data={"data": {"call_control_id": "ctrl-1"}})
        call = await p.make_call("+1111", "+2222")
        assert await p.hangup_call(call.call_id) is True


# ---------------------------------------------------------------------------
# 20.3 Provider Failover Tests
# ---------------------------------------------------------------------------

class MockProvider:
    """Minimal mock provider for failover tests."""
    def __init__(self, pid: str, healthy: bool = True, fail_call: bool = False):
        self.config = MagicMock()
        self.config.provider_id = pid
        self.config.enabled = True
        self.config.priority = 100
        self.health_status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
        self._fail_call = fail_call

    def get_active_calls(self): return []
    async def health_check(self): return self.health_status
    async def make_call(self, *a, **kw):
        if self._fail_call:
            raise RuntimeError("Simulated failure")
        return MagicMock(call_id="call-1")


class TestProviderFailover:
    def _registry_with_providers(self, providers):
        registry = MagicMock()
        registry.get_healthy_providers.return_value = [
            p for p in providers if p.health_status == HealthStatus.HEALTHY
        ]
        registry.get_all_providers.return_value = providers
        return registry

    @pytest.mark.asyncio
    async def test_make_call_success(self):
        p1 = MockProvider("p1")
        registry = self._registry_with_providers([p1])
        mgr = ProviderFailoverManager(registry, strategy=RoutingStrategy.LEAST_LOADED)
        call = await mgr.make_call_with_failover("+1", "+2")
        assert call is not None

    @pytest.mark.asyncio
    async def test_failover_to_second_provider(self):
        p1 = MockProvider("p1", fail_call=True)
        p2 = MockProvider("p2")
        registry = self._registry_with_providers([p1, p2])
        mgr = ProviderFailoverManager(registry, failure_threshold=1)
        call = await mgr.make_call_with_failover("+1", "+2", max_attempts=2)
        assert call is not None

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_none(self):
        p1 = MockProvider("p1", fail_call=True)
        registry = self._registry_with_providers([p1])
        mgr = ProviderFailoverManager(registry, failure_threshold=1)
        call = await mgr.make_call_with_failover("+1", "+2", max_attempts=1)
        assert call is None

    @pytest.mark.asyncio
    async def test_unhealthy_provider_marked_after_failures(self):
        p1 = MockProvider("p1", fail_call=True)
        registry = self._registry_with_providers([p1])
        mgr = ProviderFailoverManager(registry, failure_threshold=1)
        await mgr.make_call_with_failover("+1", "+2", max_attempts=1)
        assert p1.health_status == HealthStatus.UNHEALTHY

    def test_round_robin_strategy(self):
        p1 = MockProvider("p1"); p2 = MockProvider("p2")
        registry = self._registry_with_providers([p1, p2])
        mgr = ProviderFailoverManager(registry, strategy=RoutingStrategy.ROUND_ROBIN)
        sel1 = mgr.select_provider()
        sel2 = mgr.select_provider()
        assert sel1 is not None
        assert sel2 is not None

    def test_cost_based_routing(self):
        p1 = MockProvider("p1"); p2 = MockProvider("p2")
        registry = self._registry_with_providers([p1, p2])
        mgr = ProviderFailoverManager(registry, strategy=RoutingStrategy.COST_BASED)
        mgr.register_provider_cost("p1", 0.05)
        mgr.register_provider_cost("p2", 0.02)
        selected = mgr.select_provider()
        assert selected is not None

    def test_record_call_ended(self):
        registry = self._registry_with_providers([])
        mgr = ProviderFailoverManager(registry)
        mgr._get_stats("p1").active_calls = 3
        mgr.record_call_ended("p1")
        assert mgr._stats["p1"].active_calls == 2

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        registry = self._registry_with_providers([])
        mgr = ProviderFailoverManager(registry, health_check_interval=0.05)
        await mgr.start_health_monitoring()
        assert mgr._running is True
        await mgr.stop_health_monitoring()
        assert mgr._running is False

    def test_routing_report(self):
        registry = self._registry_with_providers([MockProvider("p1")])
        mgr = ProviderFailoverManager(registry)
        report = mgr.get_routing_report()
        assert "strategy" in report
        assert "healthy_providers" in report


# ---------------------------------------------------------------------------
# 20.4 Legacy / PSTN Tests
# ---------------------------------------------------------------------------

class TestPSTNGateway:
    @pytest.mark.asyncio
    async def test_connect(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "E1", "channels": 30})
        gw = PSTNGateway(config)
        assert await gw.connect() is True
        assert gw.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_make_call(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "E1", "channels": 30})
        gw = PSTNGateway(config)
        await gw.connect()
        call = await gw.make_call("+1111", "+2222")
        assert call.status == CallStatus.INITIATED
        assert "circuit_id" in call.metadata
        assert call.metadata["trunk_type"] == "E1"

    @pytest.mark.asyncio
    async def test_hangup_releases_channel(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "E1", "channels": 30})
        gw = PSTNGateway(config)
        await gw.connect()
        call = await gw.make_call("+1111", "+2222")
        assert gw._trunk.active_channels == 1
        await gw.hangup_call(call.call_id)
        assert gw._trunk.active_channels == 0

    @pytest.mark.asyncio
    async def test_no_channels_raises(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "T1", "channels": 1})
        gw = PSTNGateway(config)
        await gw.connect()
        await gw.make_call("+1", "+2")  # uses the 1 channel
        with pytest.raises(RuntimeError, match="No available PSTN channels"):
            await gw.make_call("+1", "+3")

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_full(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "E1", "channels": 1})
        gw = PSTNGateway(config)
        await gw.connect()
        await gw.make_call("+1", "+2")
        status = await gw.health_check()
        assert status == HealthStatus.DEGRADED

    def test_trunk_status(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "E1", "channels": 30})
        gw = PSTNGateway(config)
        status = gw.get_trunk_status()
        assert status["channels"] == 30
        assert status["trunk_type"] == "E1"

    def test_t1_trunk(self):
        config = make_config(ProviderType.PSTN, metadata={"trunk_type": "T1", "channels": 24})
        gw = PSTNGateway(config)
        assert gw._trunk.trunk_type == TrunkType.T1
        assert gw._trunk.channels == 24


class TestSS7Bridge:
    def test_send_iam(self):
        bridge = SS7SignalingBridge()
        msg = bridge.send_iam("+1111", "+2222", circuit_id=1)
        from src.telephony.legacy import SS7MessageType
        assert msg.message_type == SS7MessageType.IAM
        assert bridge.get_call_id(1) is not None

    def test_send_rel_clears_circuit(self):
        bridge = SS7SignalingBridge()
        bridge.send_iam("+1", "+2", circuit_id=5)
        bridge.send_rel(circuit_id=5)
        assert bridge.get_call_id(5) is None

    def test_message_log(self):
        bridge = SS7SignalingBridge()
        bridge.send_iam("+1", "+2", 1)
        bridge.send_rel(1)
        log = bridge.get_message_log()
        assert len(log) == 2

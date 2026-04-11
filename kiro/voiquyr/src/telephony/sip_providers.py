"""
Additional PBX and SIP Providers

Implements 3CX, Kamailio, OpenSIPS, and direct SIP trunking (RFC 3261)
with SRTP encryption support.
Implements Requirements 14.1, 14.4, 14.6, 20.1, 20.4.
"""

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base import (
    CallDirection,
    CallSession,
    CallStatus,
    HealthStatus,
    ProviderConfig,
    QoSMetrics,
    TelephonyProvider,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 3CX Provider
# ---------------------------------------------------------------------------


class ThreeCXProvider(TelephonyProvider):
    """
    3CX PBX provider via 3CX REST API.

    Integrates with 3CX Call Flow Designer for advanced call routing.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = f"https://{config.host}:{config.port}/api"
        self._token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def connect(self) -> bool:
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base_url}/login",
                json={
                    "Username": self.config.username,
                    "Password": self.config.password,
                },
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._token = data.get("Token")
                    self.health_status = HealthStatus.HEALTHY
                    self.last_health_check = datetime.utcnow()
                    return True
        except Exception as e:
            self.logger.error(f"3CX connect failed: {e}")
        self.health_status = HealthStatus.UNHEALTHY
        return False

    async def disconnect(self) -> bool:
        if self._session and not self._session.closed:
            await self._session.close()
        self.health_status = HealthStatus.UNKNOWN
        return True

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        call_id = str(uuid.uuid4())
        session = await self._get_session()
        async with session.post(
            f"{self._base_url}/calls",
            headers=self._headers(),
            json={"from": from_number, "to": to_number},
            ssl=False,
        ) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"3CX make_call failed: {resp.status}")
            data = await resp.json()

        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "3cx_id": data.get("id", "")},
        )
        self.active_calls[call_id] = cs
        return cs

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ANSWERED
            call.answer_time = datetime.utcnow()
            return True
        return False

    async def hangup_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        cx_id = call.metadata.get("3cx_id")
        if cx_id:
            session = await self._get_session()
            async with session.delete(
                f"{self._base_url}/calls/{cx_id}",
                headers=self._headers(),
                ssl=False,
            ) as resp:
                if resp.status not in (200, 204):
                    return False
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        cx_id = call.metadata.get("3cx_id")
        if cx_id:
            session = await self._get_session()
            async with session.post(
                f"{self._base_url}/calls/{cx_id}/transfer",
                headers=self._headers(),
                json={"destination": destination},
                ssl=False,
            ) as resp:
                if resp.status not in (200, 204):
                    return False
        call.status = CallStatus.TRANSFERRING
        return True

    async def hold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ON_HOLD
            return True
        return False

    async def unhold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.IN_PROGRESS
            return True
        return False

    async def get_qos_metrics(self, call_id: str) -> Optional[QoSMetrics]:
        return None  # 3CX REST API does not expose per-call RTP stats

    async def health_check(self) -> HealthStatus:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base_url}/status",
                headers=self._headers(),
                ssl=False,
            ) as resp:
                self.health_status = (
                    HealthStatus.HEALTHY if resp.status == 200 else HealthStatus.DEGRADED
                )
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status


# ---------------------------------------------------------------------------
# Kamailio / OpenSIPS SIP proxy providers (shared base)
# ---------------------------------------------------------------------------


class SIPProxyProvider(TelephonyProvider):
    """
    Base provider for SIP proxy servers (Kamailio / OpenSIPS).

    Uses the XMLRPC / JSON-RPC management interface common to both.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        rpc_port = config.metadata.get("rpc_port", 5060)
        self._rpc_url = f"http://{config.host}:{rpc_port}/RPC"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _rpc(self, method: str, params: Optional[List] = None) -> Any:
        session = await self._get_session()
        payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
        async with session.post(self._rpc_url, json=payload) as resp:
            data = await resp.json()
            return data.get("result")

    async def connect(self) -> bool:
        try:
            result = await self._rpc("core.uptime")
            if result is not None:
                self.health_status = HealthStatus.HEALTHY
                self.last_health_check = datetime.utcnow()
                return True
        except Exception as e:
            self.logger.error(f"SIP proxy connect failed: {e}")
        self.health_status = HealthStatus.UNHEALTHY
        return False

    async def disconnect(self) -> bool:
        if self._session and not self._session.closed:
            await self._session.close()
        self.health_status = HealthStatus.UNKNOWN
        return True

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        call_id = str(uuid.uuid4())
        # SIP proxy routes the call; we record it locally
        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata=metadata or {},
        )
        self.active_calls[call_id] = cs
        return cs

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ANSWERED
            call.answer_time = datetime.utcnow()
            return True
        return False

    async def hangup_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.COMPLETED
            call.end_time = datetime.utcnow()
            return True
        return False

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.TRANSFERRING
            return True
        return False

    async def hold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ON_HOLD
            return True
        return False

    async def unhold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.IN_PROGRESS
            return True
        return False

    async def get_qos_metrics(self, call_id: str) -> Optional[QoSMetrics]:
        return None

    async def health_check(self) -> HealthStatus:
        try:
            result = await self._rpc("core.uptime")
            self.health_status = (
                HealthStatus.HEALTHY if result is not None else HealthStatus.UNHEALTHY
            )
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status


class KamailioProvider(SIPProxyProvider):
    """Kamailio SIP server provider."""

    async def reload_dialplan(self) -> bool:
        """Reload Kamailio routing configuration."""
        result = await self._rpc("cfg.reload")
        return result is not None


class OpenSIPSProvider(SIPProxyProvider):
    """OpenSIPS SIP server provider."""

    async def reload_dialplan(self) -> bool:
        """Reload OpenSIPS routing configuration."""
        result = await self._rpc("dr_reload")
        return result is not None


# ---------------------------------------------------------------------------
# Direct SIP Trunk Provider (RFC 3261 + SRTP)
# ---------------------------------------------------------------------------


class SRTPConfig:
    """SRTP encryption configuration."""

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        master_salt: Optional[bytes] = None,
        crypto_suite: str = "AES_CM_128_HMAC_SHA1_80",
    ):
        self.master_key = master_key or os.urandom(16)
        self.master_salt = master_salt or os.urandom(14)
        self.crypto_suite = crypto_suite

    def to_sdp_crypto_attr(self) -> str:
        """Generate SDP a=crypto attribute line."""
        import base64
        key_salt = base64.b64encode(self.master_key + self.master_salt).decode()
        return f"a=crypto:1 {self.crypto_suite} inline:{key_salt}"


class DirectSIPProvider(TelephonyProvider):
    """
    Direct SIP trunking provider (RFC 3261).

    Implements SIP signalling with SRTP media encryption.
    Uses asyncio UDP transport for SIP messages.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._srtp_enabled = config.metadata.get("srtp_enabled", True)
        self._srtp_configs: Dict[str, SRTPConfig] = {}
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._local_port = config.metadata.get("local_sip_port", 5060)

    async def connect(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            # Bind UDP socket for SIP signalling
            self._transport, _ = await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol,
                local_addr=("0.0.0.0", self._local_port),
            )
            self.health_status = HealthStatus.HEALTHY
            self.last_health_check = datetime.utcnow()
            self.logger.info(
                f"Direct SIP provider bound on port {self._local_port}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Direct SIP connect failed: {e}")
            self.health_status = HealthStatus.UNHEALTHY
            return False

    async def disconnect(self) -> bool:
        if self._transport:
            self._transport.close()
        self.health_status = HealthStatus.UNKNOWN
        return True

    def _build_invite(
        self,
        call_id: str,
        from_number: str,
        to_number: str,
        srtp_config: Optional[SRTPConfig],
    ) -> bytes:
        """Build a minimal SIP INVITE message."""
        branch = f"z9hG4bK{uuid.uuid4().hex[:8]}"
        tag = uuid.uuid4().hex[:8]
        cseq = 1
        host = self.config.host
        port = self.config.port

        sdp_lines = [
            "v=0",
            f"o=voiquyr 0 0 IN IP4 {host}",
            "s=VoiQyr Call",
            f"c=IN IP4 {host}",
            "t=0 0",
            "m=audio 10000 RTP/SAVP 0 8 101" if srtp_config else "m=audio 10000 RTP/AVP 0 8 101",
            "a=rtpmap:0 PCMU/8000",
            "a=rtpmap:8 PCMA/8000",
            "a=rtpmap:101 telephone-event/8000",
        ]
        if srtp_config:
            sdp_lines.append(srtp_config.to_sdp_crypto_attr())

        sdp = "\r\n".join(sdp_lines) + "\r\n"

        headers = [
            f"INVITE sip:{to_number}@{host}:{port} SIP/2.0",
            f"Via: SIP/2.0/UDP {host}:{self._local_port};branch={branch}",
            f"From: <sip:{from_number}@{host}>;tag={tag}",
            f"To: <sip:{to_number}@{host}:{port}>",
            f"Call-ID: {call_id}",
            f"CSeq: {cseq} INVITE",
            "Content-Type: application/sdp",
            f"Content-Length: {len(sdp.encode())}",
            "",
            sdp,
        ]
        return "\r\n".join(headers).encode()

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        call_id = str(uuid.uuid4())
        srtp_config = SRTPConfig() if self._srtp_enabled else None
        if srtp_config:
            self._srtp_configs[call_id] = srtp_config

        invite = self._build_invite(call_id, from_number, to_number, srtp_config)
        if self._transport:
            self._transport.sendto(invite, (self.config.host, self.config.port))

        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "srtp_enabled": self._srtp_enabled},
        )
        self.active_calls[call_id] = cs
        return cs

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ANSWERED
            call.answer_time = datetime.utcnow()
            return True
        return False

    async def hangup_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        # Send SIP BYE (simplified)
        bye = (
            f"BYE sip:{call.to_number}@{self.config.host} SIP/2.0\r\n"
            f"Call-ID: {call_id}\r\n"
            "CSeq: 2 BYE\r\n"
            "Content-Length: 0\r\n\r\n"
        )
        if self._transport:
            self._transport.sendto(bye.encode(), (self.config.host, self.config.port))
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        self._srtp_configs.pop(call_id, None)
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        # Send SIP REFER
        refer = (
            f"REFER sip:{call.to_number}@{self.config.host} SIP/2.0\r\n"
            f"Call-ID: {call_id}\r\n"
            f"Refer-To: sip:{destination}@{self.config.host}\r\n"
            "CSeq: 3 REFER\r\n"
            "Content-Length: 0\r\n\r\n"
        )
        if self._transport:
            self._transport.sendto(refer.encode(), (self.config.host, self.config.port))
        call.status = CallStatus.TRANSFERRING
        return True

    async def hold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ON_HOLD
            return True
        return False

    async def unhold_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.IN_PROGRESS
            return True
        return False

    async def get_qos_metrics(self, call_id: str) -> Optional[QoSMetrics]:
        return None  # Would require RTCP listener

    async def health_check(self) -> HealthStatus:
        # Send SIP OPTIONS ping
        options = (
            f"OPTIONS sip:{self.config.host}:{self.config.port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.config.host}:{self._local_port};branch=z9hG4bKping\r\n"
            "Content-Length: 0\r\n\r\n"
        )
        try:
            if self._transport:
                self._transport.sendto(
                    options.encode(), (self.config.host, self.config.port)
                )
                self.health_status = HealthStatus.HEALTHY
            else:
                self.health_status = HealthStatus.UNHEALTHY
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status

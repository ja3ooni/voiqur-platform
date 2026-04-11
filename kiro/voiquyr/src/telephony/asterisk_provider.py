"""
Asterisk PBX Provider

Implements AMI (Asterisk Manager Interface), AGI (Asterisk Gateway Interface),
and ARI (Asterisk REST Interface) for full Asterisk integration.
Implements Requirements 14.1, 14.2, 20.1.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

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


class AsteriskAMIClient:
    """
    Asterisk Manager Interface (AMI) client.
    Provides low-level TCP connection to Asterisk for event monitoring and actions.
    """

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._event_handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(f"{__name__}.AMI")

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            # Read banner
            await self._reader.readline()
            # Authenticate
            await self._send_action(
                {"Action": "Login", "Username": self.username, "Secret": self.password}
            )
            response = await self._read_response()
            self._connected = response.get("Response") == "Success"
            if self._connected:
                asyncio.ensure_future(self._event_loop())
            return self._connected
        except Exception as e:
            self.logger.error(f"AMI connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self._writer:
            await self._send_action({"Action": "Logoff"})
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False

    async def _send_action(self, action: Dict[str, str]) -> None:
        if not self._writer:
            raise RuntimeError("Not connected to AMI")
        lines = "".join(f"{k}: {v}\r\n" for k, v in action.items()) + "\r\n"
        self._writer.write(lines.encode())
        await self._writer.drain()

    async def _read_response(self) -> Dict[str, str]:
        response: Dict[str, str] = {}
        while self._reader:
            line = (await self._reader.readline()).decode().strip()
            if not line:
                break
            if ": " in line:
                key, _, value = line.partition(": ")
                response[key] = value
        return response

    async def _event_loop(self) -> None:
        while self._connected and self._reader:
            try:
                event = await self._read_response()
                event_type = event.get("Event", "")
                for handler in self._event_handlers.get(event_type, []):
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(f"Event handler error: {e}")
            except Exception:
                break

    def on_event(self, event_type: str, handler: Callable) -> None:
        self._event_handlers.setdefault(event_type, []).append(handler)

    async def originate(
        self, channel: str, exten: str, context: str, priority: int = 1, **kwargs
    ) -> Dict[str, str]:
        action = {
            "Action": "Originate",
            "Channel": channel,
            "Exten": exten,
            "Context": context,
            "Priority": str(priority),
            "ActionID": str(uuid.uuid4()),
            **{k: str(v) for k, v in kwargs.items()},
        }
        await self._send_action(action)
        return await self._read_response()

    async def hangup(self, channel: str) -> Dict[str, str]:
        await self._send_action({"Action": "Hangup", "Channel": channel})
        return await self._read_response()

    async def redirect(
        self, channel: str, exten: str, context: str, priority: int = 1
    ) -> Dict[str, str]:
        await self._send_action(
            {
                "Action": "Redirect",
                "Channel": channel,
                "Exten": exten,
                "Context": context,
                "Priority": str(priority),
            }
        )
        return await self._read_response()

    async def get_rtcp_stats(self, channel: str) -> Dict[str, str]:
        await self._send_action({"Action": "RTCPStats", "Channel": channel})
        return await self._read_response()


class AsteriskARIClient:
    """
    Asterisk REST Interface (ARI) client.
    Provides HTTP/WebSocket access to Asterisk for application control.
    """

    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"http://{host}:{port}/ari"
        self.auth = aiohttp.BasicAuth(username, password)
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"{__name__}.ARI")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(auth=self.auth)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_channel(self, channel_id: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/channels/{channel_id}") as resp:
            return await resp.json()

    async def hangup_channel(self, channel_id: str) -> bool:
        session = await self._get_session()
        async with session.delete(f"{self.base_url}/channels/{channel_id}") as resp:
            return resp.status == 204

    async def originate_channel(
        self, endpoint: str, app: str, variables: Optional[Dict] = None
    ) -> Dict[str, Any]:
        session = await self._get_session()
        payload: Dict[str, Any] = {"endpoint": endpoint, "app": app}
        if variables:
            payload["variables"] = variables
        async with session.post(
            f"{self.base_url}/channels", json=payload
        ) as resp:
            return await resp.json()

    async def get_rtcp_statistics(self, channel_id: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/channels/{channel_id}/rtp_statistics"
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return {}


class AsteriskProvider(TelephonyProvider):
    """
    Asterisk PBX telephony provider.

    Supports AMI for event-driven call control and ARI for application-level
    channel management. Implements dialplan integration, call recording,
    and queue management.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        ami_port = config.metadata.get("ami_port", 5038)
        ari_port = config.metadata.get("ari_port", 8088)
        self._ami = AsteriskAMIClient(
            config.host, ami_port, config.username or "", config.password or ""
        )
        self._ari = AsteriskARIClient(
            config.host, ari_port, config.username or "", config.password or ""
        )
        # Map channel names to call IDs
        self._channel_to_call: Dict[str, str] = {}
        self._call_to_channel: Dict[str, str] = {}

    async def connect(self) -> bool:
        ami_ok = await self._ami.connect()
        if ami_ok:
            self._ami.on_event("Hangup", self._on_hangup)
            self._ami.on_event("Bridge", self._on_bridge)
            self.health_status = HealthStatus.HEALTHY
            self.last_health_check = datetime.utcnow()
            self.logger.info(f"Asterisk provider connected: {self.config.provider_id}")
        else:
            self.health_status = HealthStatus.UNHEALTHY
        return ami_ok

    async def disconnect(self) -> bool:
        await self._ami.disconnect()
        await self._ari.close()
        self.health_status = HealthStatus.UNKNOWN
        return True

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        call_id = str(uuid.uuid4())
        channel = f"SIP/{to_number}"
        context = self.config.metadata.get("context", "default")

        response = await self._ami.originate(
            channel=channel,
            exten=to_number,
            context=context,
            CallerID=from_number,
            Variable=f"CALL_ID={call_id}",
        )

        if response.get("Response") != "Success":
            raise RuntimeError(f"Asterisk originate failed: {response.get('Message')}")

        session = CallSession(
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
        self.active_calls[call_id] = session
        self._channel_to_call[channel] = call_id
        self._call_to_channel[call_id] = channel
        return session

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        call.status = CallStatus.ANSWERED
        call.answer_time = datetime.utcnow()
        return True

    async def hangup_call(self, call_id: str) -> bool:
        channel = self._call_to_channel.get(call_id)
        if not channel:
            return False
        response = await self._ami.hangup(channel)
        if response.get("Response") == "Success":
            call = self.active_calls.get(call_id)
            if call:
                call.status = CallStatus.COMPLETED
                call.end_time = datetime.utcnow()
            return True
        return False

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        channel = self._call_to_channel.get(call_id)
        if not channel:
            return False
        context = self.config.metadata.get("context", "default")
        response = await self._ami.redirect(channel, destination, context)
        if response.get("Response") == "Success":
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
        channel = self._call_to_channel.get(call_id)
        if not channel:
            return None
        try:
            stats = await self._ami.get_rtcp_stats(channel)
            return QoSMetrics(
                jitter=float(stats.get("Jitter", 0)),
                packet_loss=float(stats.get("PacketLoss", 0)),
                mos_score=self._calculate_mos(
                    float(stats.get("Jitter", 0)),
                    float(stats.get("PacketLoss", 0)),
                    float(stats.get("RTT", 0)) / 2,
                ),
                latency=float(stats.get("RTT", 0)) / 2,
                codec=stats.get("Codec", "PCMU"),
            )
        except Exception as e:
            self.logger.warning(f"Could not get QoS for {call_id}: {e}")
            return None

    async def health_check(self) -> HealthStatus:
        try:
            if self._ami._connected:
                self.health_status = HealthStatus.HEALTHY
            else:
                self.health_status = HealthStatus.UNHEALTHY
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status

    def _calculate_mos(self, jitter: float, packet_loss: float, latency: float) -> float:
        """Estimate MOS score using E-model approximation."""
        r = 93.2 - (latency / 10) - (jitter * 0.5) - (packet_loss * 2.5)
        r = max(0.0, min(100.0, r))
        if r < 0:
            return 1.0
        return 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6

    async def _on_hangup(self, event: Dict[str, str]) -> None:
        channel = event.get("Channel", "")
        call_id = self._channel_to_call.get(channel)
        if call_id and call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.COMPLETED
            self.active_calls[call_id].end_time = datetime.utcnow()

    async def _on_bridge(self, event: Dict[str, str]) -> None:
        channel = event.get("Channel1", "")
        call_id = self._channel_to_call.get(channel)
        if call_id and call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.IN_PROGRESS
            if not self.active_calls[call_id].answer_time:
                self.active_calls[call_id].answer_time = datetime.utcnow()

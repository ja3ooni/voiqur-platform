"""
FreeSWITCH Provider

Implements ESL (Event Socket Library) integration for FreeSWITCH,
including conference bridge support and call parking.
Implements Requirements 14.1, 14.3, 20.1.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

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


class FreeSwitchESLClient:
    """
    FreeSWITCH Event Socket Library (ESL) client.
    Connects to FreeSWITCH inbound ESL socket for event-driven call control.
    """

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._event_handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(f"{__name__}.ESL")

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            # Read auth request
            await self._read_packet()
            # Send password
            await self._send(f"auth {self.password}\n\n")
            response = await self._read_packet()
            self._connected = "Reply-Text: +OK accepted" in response
            if self._connected:
                await self._send("event plain ALL\n\n")
                asyncio.ensure_future(self._event_loop())
            return self._connected
        except Exception as e:
            self.logger.error(f"ESL connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        if self._writer:
            await self._send("exit\n\n")
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False

    async def _send(self, data: str) -> None:
        if not self._writer:
            raise RuntimeError("Not connected to FreeSWITCH ESL")
        self._writer.write(data.encode())
        await self._writer.drain()

    async def _read_packet(self) -> str:
        if not self._reader:
            return ""
        lines = []
        while True:
            line = (await self._reader.readline()).decode()
            if line == "\n":
                break
            lines.append(line.strip())
        return "\n".join(lines)

    async def _event_loop(self) -> None:
        while self._connected and self._reader:
            try:
                packet = await self._read_packet()
                if not packet:
                    continue
                event: Dict[str, str] = {}
                for line in packet.splitlines():
                    if ": " in line:
                        k, _, v = line.partition(": ")
                        event[k.strip()] = v.strip()
                event_name = event.get("Event-Name", "")
                for handler in self._event_handlers.get(event_name, []):
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(f"Event handler error: {e}")
            except Exception:
                break

    def on_event(self, event_name: str, handler: Callable) -> None:
        self._event_handlers.setdefault(event_name, []).append(handler)

    async def api(self, command: str) -> str:
        await self._send(f"api {command}\n\n")
        return await self._read_packet()

    async def bgapi(self, command: str) -> str:
        job_id = str(uuid.uuid4())
        await self._send(f"bgapi {command}\nJob-UUID: {job_id}\n\n")
        return job_id

    async def originate(
        self,
        endpoint: str,
        destination: str,
        dialplan: str = "XML",
        context: str = "default",
        caller_id: str = "",
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        var_str = ""
        if variables:
            var_str = "{" + ",".join(f"{k}={v}" for k, v in variables.items()) + "}"
        cmd = f"originate {var_str}{endpoint} {destination} {dialplan} {context}"
        if caller_id:
            cmd += f" '{caller_id}'"
        return await self.api(cmd)

    async def uuid_kill(self, call_uuid: str) -> str:
        return await self.api(f"uuid_kill {call_uuid}")

    async def uuid_transfer(
        self, call_uuid: str, destination: str, context: str = "default"
    ) -> str:
        return await self.api(f"uuid_transfer {call_uuid} {destination} XML {context}")

    async def uuid_hold(self, call_uuid: str) -> str:
        return await self.api(f"uuid_hold {call_uuid}")

    async def uuid_unhold(self, call_uuid: str) -> str:
        return await self.api(f"uuid_hold off {call_uuid}")

    async def uuid_park(self, call_uuid: str) -> str:
        return await self.api(f"uuid_park {call_uuid}")

    async def conference(self, name: str, command: str, args: str = "") -> str:
        return await self.api(f"conference {name} {command} {args}")

    async def uuid_get_var(self, call_uuid: str, var_name: str) -> str:
        result = await self.api(f"uuid_getvar {call_uuid} {var_name}")
        return result.strip()


class FreeSwitchProvider(TelephonyProvider):
    """
    FreeSWITCH telephony provider.

    Uses ESL for event-driven call control with support for conference bridges,
    call parking, and dynamic routing via mod_xml_curl.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        esl_port = config.metadata.get("esl_port", 8021)
        self._esl = FreeSwitchESLClient(
            config.host, esl_port, config.password or "ClueCon"
        )
        # Map FreeSWITCH UUID to our call IDs
        self._uuid_to_call: Dict[str, str] = {}
        self._call_to_uuid: Dict[str, str] = {}

    async def connect(self) -> bool:
        ok = await self._esl.connect()
        if ok:
            self._esl.on_event("CHANNEL_HANGUP", self._on_hangup)
            self._esl.on_event("CHANNEL_ANSWER", self._on_answer)
            self.health_status = HealthStatus.HEALTHY
            self.last_health_check = datetime.utcnow()
            self.logger.info(f"FreeSWITCH provider connected: {self.config.provider_id}")
        else:
            self.health_status = HealthStatus.UNHEALTHY
        return ok

    async def disconnect(self) -> bool:
        await self._esl.disconnect()
        self.health_status = HealthStatus.UNKNOWN
        return True

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        call_id = str(uuid.uuid4())
        context = self.config.metadata.get("context", "default")
        endpoint = f"sofia/gateway/{self.config.metadata.get('gateway', 'default')}/{to_number}"

        response = await self._esl.originate(
            endpoint=endpoint,
            destination=to_number,
            context=context,
            caller_id=from_number,
            variables={"voiquyr_call_id": call_id},
        )

        # FreeSWITCH returns +OK <uuid> on success
        if not response.startswith("+OK"):
            raise RuntimeError(f"FreeSWITCH originate failed: {response}")

        fs_uuid = response.replace("+OK", "").strip()
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
        self._uuid_to_call[fs_uuid] = call_id
        self._call_to_uuid[call_id] = fs_uuid
        return session

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.ANSWERED
            call.answer_time = datetime.utcnow()
            return True
        return False

    async def hangup_call(self, call_id: str) -> bool:
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        response = await self._esl.uuid_kill(fs_uuid)
        if "+OK" in response:
            call = self.active_calls.get(call_id)
            if call:
                call.status = CallStatus.COMPLETED
                call.end_time = datetime.utcnow()
            return True
        return False

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        context = self.config.metadata.get("context", "default")
        response = await self._esl.uuid_transfer(fs_uuid, destination, context)
        if "+OK" in response:
            call = self.active_calls.get(call_id)
            if call:
                call.status = CallStatus.TRANSFERRING
            return True
        return False

    async def hold_call(self, call_id: str) -> bool:
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        response = await self._esl.uuid_hold(fs_uuid)
        if "+OK" in response:
            call = self.active_calls.get(call_id)
            if call:
                call.status = CallStatus.ON_HOLD
            return True
        return False

    async def unhold_call(self, call_id: str) -> bool:
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        response = await self._esl.uuid_unhold(fs_uuid)
        if "+OK" in response:
            call = self.active_calls.get(call_id)
            if call:
                call.status = CallStatus.IN_PROGRESS
            return True
        return False

    async def park_call(self, call_id: str) -> bool:
        """Park a call (FreeSWITCH-specific feature)."""
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        response = await self._esl.uuid_park(fs_uuid)
        return "+OK" in response

    async def join_conference(self, call_id: str, conference_name: str) -> bool:
        """Transfer call into a conference bridge."""
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return False
        response = await self._esl.uuid_transfer(
            fs_uuid, f"conference:{conference_name}", "default"
        )
        return "+OK" in response

    async def get_qos_metrics(self, call_id: str) -> Optional[QoSMetrics]:
        fs_uuid = self._call_to_uuid.get(call_id)
        if not fs_uuid:
            return None
        try:
            jitter_str = await self._esl.uuid_get_var(fs_uuid, "rtp_audio_in_jitter_burst_rate")
            loss_str = await self._esl.uuid_get_var(fs_uuid, "rtp_audio_in_packet_count")
            jitter = float(jitter_str) if jitter_str else 0.0
            packet_loss = 0.0  # Would need more vars for accurate loss
            latency = 0.0
            mos = self._calculate_mos(jitter, packet_loss, latency)
            return QoSMetrics(
                jitter=jitter,
                packet_loss=packet_loss,
                mos_score=mos,
                latency=latency,
                codec=self.config.metadata.get("codec", "PCMU"),
            )
        except Exception as e:
            self.logger.warning(f"Could not get QoS for {call_id}: {e}")
            return None

    async def health_check(self) -> HealthStatus:
        try:
            response = await self._esl.api("status")
            self.health_status = (
                HealthStatus.HEALTHY if response else HealthStatus.UNHEALTHY
            )
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status

    def _calculate_mos(self, jitter: float, packet_loss: float, latency: float) -> float:
        r = 93.2 - (latency / 10) - (jitter * 0.5) - (packet_loss * 2.5)
        r = max(0.0, min(100.0, r))
        return 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6

    async def _on_hangup(self, event: Dict[str, str]) -> None:
        fs_uuid = event.get("Unique-ID", "")
        call_id = self._uuid_to_call.get(fs_uuid)
        if call_id and call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.COMPLETED
            self.active_calls[call_id].end_time = datetime.utcnow()

    async def _on_answer(self, event: Dict[str, str]) -> None:
        fs_uuid = event.get("Unique-ID", "")
        call_id = self._uuid_to_call.get(fs_uuid)
        if call_id and call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.ANSWERED
            if not self.active_calls[call_id].answer_time:
                self.active_calls[call_id].answer_time = datetime.utcnow()

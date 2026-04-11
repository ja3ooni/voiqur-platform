"""
Cloud Telephony Providers — Vonage/Nexmo, Plivo, Bandwidth, Telnyx.
Implements Requirement 20.6.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from .base import (
    CallDirection, CallSession, CallStatus, HealthStatus,
    ProviderConfig, QoSMetrics, TelephonyProvider,
)

logger = logging.getLogger(__name__)


class _HTTPProvider(TelephonyProvider):
    """Shared async HTTP base for cloud providers."""

    def __init__(self, config: ProviderConfig, base_url: str):
        super().__init__(config)
        self._base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._auth_headers())
        return self._session

    def _auth_headers(self) -> Dict[str, str]:
        return {}

    async def _post(self, path: str, data: Dict) -> Optional[Dict]:
        s = await self._get_session()
        async with s.post(f"{self._base_url}{path}", json=data, ssl=False) as r:
            return await r.json() if r.status in (200, 201, 202) else None

    async def _get(self, path: str) -> Optional[Dict]:
        s = await self._get_session()
        async with s.get(f"{self._base_url}{path}", ssl=False) as r:
            return await r.json() if r.status == 200 else None

    async def disconnect(self) -> bool:
        if self._session and not self._session.closed:
            await self._session.close()
        self.health_status = HealthStatus.UNKNOWN
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
        return None


class VonageProvider(_HTTPProvider):
    """Vonage (Nexmo) Voice API provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, "https://api.nexmo.com/v1")
        self._api_key = config.api_key or ""
        self._api_secret = config.api_secret or ""

    def _auth_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def connect(self) -> bool:
        try:
            result = await self._get(f"/account/get-balance?api_key={self._api_key}&api_secret={self._api_secret}")
            self.health_status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status == HealthStatus.HEALTHY

    async def make_call(self, from_number: str, to_number: str,
                        metadata: Optional[Dict[str, Any]] = None) -> CallSession:
        call_id = str(uuid.uuid4())
        result = await self._post("/calls", {
            "to": [{"type": "phone", "number": to_number}],
            "from": {"type": "phone", "number": from_number},
            "ncco": [{"action": "talk", "text": "Connected"}],
        })
        if not result:
            raise RuntimeError("Vonage make_call failed")
        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number, to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "vonage_uuid": result.get("uuid", "")},
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
        vonage_uuid = call.metadata.get("vonage_uuid", "")
        if vonage_uuid:
            s = await self._get_session()
            async with s.delete(f"{self._base_url}/calls/{vonage_uuid}", ssl=False):
                pass
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        vonage_uuid = call.metadata.get("vonage_uuid", "")
        if vonage_uuid:
            s = await self._get_session()
            async with s.put(f"{self._base_url}/calls/{vonage_uuid}", json={
                "action": "transfer",
                "destination": {"type": "ncco", "ncco": [{"action": "connect",
                    "endpoint": [{"type": "phone", "number": destination}]}]}
            }, ssl=False):
                pass
        call.status = CallStatus.TRANSFERRING
        return True

    async def health_check(self) -> HealthStatus:
        return await self.connect() and HealthStatus.HEALTHY or HealthStatus.UNHEALTHY


class PlivoProvider(_HTTPProvider):
    """Plivo Voice API provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, f"https://api.plivo.com/v1/Account/{config.username}")
        self._auth = aiohttp.BasicAuth(config.username or "", config.password or "")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(auth=self._auth)
        return self._session

    async def connect(self) -> bool:
        try:
            result = await self._get("/")
            self.health_status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status == HealthStatus.HEALTHY

    async def make_call(self, from_number: str, to_number: str,
                        metadata: Optional[Dict[str, Any]] = None) -> CallSession:
        call_id = str(uuid.uuid4())
        result = await self._post("/Call/", {
            "from": from_number, "to": to_number,
            "answer_url": self.config.metadata.get("answer_url", "https://voiquyr.eu/answer"),
        })
        if not result:
            raise RuntimeError("Plivo make_call failed")
        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number, to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "plivo_uuid": result.get("request_uuid", "")},
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
        plivo_uuid = call.metadata.get("plivo_uuid", "")
        if plivo_uuid:
            s = await self._get_session()
            async with s.delete(f"{self._base_url}/Call/{plivo_uuid}/", ssl=False):
                pass
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.TRANSFERRING
            return True
        return False

    async def health_check(self) -> HealthStatus:
        ok = await self.connect()
        return HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY


class BandwidthProvider(_HTTPProvider):
    """Bandwidth.com Voice API provider."""

    def __init__(self, config: ProviderConfig):
        account_id = config.metadata.get("account_id", "")
        super().__init__(config, f"https://voice.bandwidth.com/api/v2/accounts/{account_id}")
        self._auth = aiohttp.BasicAuth(config.username or "", config.password or "")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(auth=self._auth)
        return self._session

    async def connect(self) -> bool:
        self.health_status = HealthStatus.HEALTHY
        self.last_health_check = datetime.utcnow()
        return True

    async def make_call(self, from_number: str, to_number: str,
                        metadata: Optional[Dict[str, Any]] = None) -> CallSession:
        call_id = str(uuid.uuid4())
        result = await self._post("/calls", {
            "from": from_number, "to": to_number,
            "applicationId": self.config.metadata.get("application_id", ""),
            "answerUrl": self.config.metadata.get("answer_url", "https://voiquyr.eu/answer"),
        })
        if not result:
            raise RuntimeError("Bandwidth make_call failed")
        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number, to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "bw_call_id": result.get("callId", "")},
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
        bw_id = call.metadata.get("bw_call_id", "")
        if bw_id:
            s = await self._get_session()
            async with s.post(f"{self._base_url}/calls/{bw_id}", json={"state": "completed"}, ssl=False):
                pass
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if call:
            call.status = CallStatus.TRANSFERRING
            return True
        return False

    async def health_check(self) -> HealthStatus:
        self.health_status = HealthStatus.HEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status


class TelnyxProvider(_HTTPProvider):
    """Telnyx Voice API v2 provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, "https://api.telnyx.com/v2")

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.config.api_key or ''}"}

    async def connect(self) -> bool:
        try:
            result = await self._get("/phone_numbers?page[size]=1")
            self.health_status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
        except Exception:
            self.health_status = HealthStatus.UNHEALTHY
        self.last_health_check = datetime.utcnow()
        return self.health_status == HealthStatus.HEALTHY

    async def make_call(self, from_number: str, to_number: str,
                        metadata: Optional[Dict[str, Any]] = None) -> CallSession:
        call_id = str(uuid.uuid4())
        result = await self._post("/calls", {
            "connection_id": self.config.metadata.get("connection_id", ""),
            "to": to_number, "from": from_number,
            "webhook_url": self.config.metadata.get("webhook_url", "https://voiquyr.eu/telnyx"),
        })
        if not result:
            raise RuntimeError("Telnyx make_call failed")
        data = result.get("data", {})
        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number, to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "telnyx_call_control_id": data.get("call_control_id", "")},
        )
        self.active_calls[call_id] = cs
        return cs

    async def answer_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        ctrl_id = call.metadata.get("telnyx_call_control_id", "")
        if ctrl_id:
            await self._post(f"/calls/{ctrl_id}/actions/answer", {})
        call.status = CallStatus.ANSWERED
        call.answer_time = datetime.utcnow()
        return True

    async def hangup_call(self, call_id: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        ctrl_id = call.metadata.get("telnyx_call_control_id", "")
        if ctrl_id:
            await self._post(f"/calls/{ctrl_id}/actions/hangup", {})
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        call = self.active_calls.get(call_id)
        if not call:
            return False
        ctrl_id = call.metadata.get("telnyx_call_control_id", "")
        if ctrl_id:
            await self._post(f"/calls/{ctrl_id}/actions/transfer", {"to": destination})
        call.status = CallStatus.TRANSFERRING
        return True

    async def health_check(self) -> HealthStatus:
        ok = await self.connect()
        return HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY

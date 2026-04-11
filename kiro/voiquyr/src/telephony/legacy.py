"""
Legacy Telephony Support — PSTN gateway, E1/T1, SS7 signaling bridge.
Implements Requirement 20.8.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import (
    CallDirection, CallSession, CallStatus, HealthStatus,
    ProviderConfig, QoSMetrics, TelephonyProvider,
)

logger = logging.getLogger(__name__)


class TrunkType(Enum):
    E1 = "E1"       # 30 channels, 2.048 Mbps (Europe)
    T1 = "T1"       # 24 channels, 1.544 Mbps (North America)
    BRI = "BRI"     # Basic Rate ISDN (2B+D)
    PRI = "PRI"     # Primary Rate ISDN (E1/T1 with D-channel)
    ANALOG = "analog"


class SS7MessageType(Enum):
    IAM = "IAM"   # Initial Address Message
    ACM = "ACM"   # Address Complete Message
    ANM = "ANM"   # Answer Message
    REL = "REL"   # Release
    RLC = "RLC"   # Release Complete


@dataclass
class TrunkConfig:
    trunk_id: str
    trunk_type: TrunkType
    channels: int
    active_channels: int = 0
    signaling_protocol: str = "ISDN"  # "ISDN" | "SS7" | "CAS"

    @property
    def available_channels(self) -> int:
        return self.channels - self.active_channels

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trunk_id": self.trunk_id,
            "trunk_type": self.trunk_type.value,
            "channels": self.channels,
            "active_channels": self.active_channels,
            "available_channels": self.available_channels,
        }


@dataclass
class SS7Message:
    message_type: SS7MessageType
    calling_party: str
    called_party: str
    circuit_id: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.message_type.value,
            "calling": self.calling_party,
            "called": self.called_party,
            "circuit": self.circuit_id,
            "timestamp": self.timestamp.isoformat(),
        }


class SS7SignalingBridge:
    """
    SS7 signaling bridge — translates SS7 ISUP messages to/from SIP.
    In production this wraps a hardware SS7 card or OpenSS7 stack.
    """

    def __init__(self):
        self._circuits: Dict[int, str] = {}   # circuit_id → call_id
        self._messages: List[SS7Message] = []
        self.logger = logging.getLogger(__name__)

    def send_iam(self, calling: str, called: str, circuit_id: int) -> SS7Message:
        msg = SS7Message(SS7MessageType.IAM, calling, called, circuit_id)
        self._messages.append(msg)
        self._circuits[circuit_id] = str(uuid.uuid4())
        self.logger.debug(f"SS7 IAM: {calling} → {called} on circuit {circuit_id}")
        return msg

    def send_rel(self, circuit_id: int, cause: int = 16) -> SS7Message:
        call_id = self._circuits.pop(circuit_id, "")
        msg = SS7Message(
            SS7MessageType.REL, "", "", circuit_id,
            parameters={"cause": cause, "call_id": call_id}
        )
        self._messages.append(msg)
        return msg

    def get_call_id(self, circuit_id: int) -> Optional[str]:
        return self._circuits.get(circuit_id)

    def get_message_log(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._messages]


class PSTNGateway(TelephonyProvider):
    """
    PSTN gateway provider — bridges VoIP to traditional PSTN via
    E1/T1 trunks with SS7 or ISDN signaling.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        trunk_type = TrunkType(config.metadata.get("trunk_type", "E1"))
        channels = config.metadata.get("channels", 30)
        self._trunk = TrunkConfig(
            trunk_id=config.provider_id,
            trunk_type=trunk_type,
            channels=channels,
        )
        self._ss7 = SS7SignalingBridge()
        self._circuit_counter = 1

    async def connect(self) -> bool:
        # Simulate trunk activation
        self.health_status = HealthStatus.HEALTHY
        self.last_health_check = datetime.utcnow()
        self.logger.info(
            f"PSTN gateway connected: {self._trunk.trunk_type.value} "
            f"({self._trunk.channels} channels)"
        )
        return True

    async def disconnect(self) -> bool:
        self.health_status = HealthStatus.UNKNOWN
        return True

    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSession:
        if self._trunk.available_channels == 0:
            raise RuntimeError("No available PSTN channels")

        call_id = str(uuid.uuid4())
        circuit_id = self._circuit_counter
        self._circuit_counter += 1
        self._trunk.active_channels += 1

        # Send SS7 IAM
        self._ss7.send_iam(from_number, to_number, circuit_id)

        cs = CallSession(
            call_id=call_id,
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata={**(metadata or {}), "circuit_id": circuit_id,
                      "trunk_type": self._trunk.trunk_type.value},
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
        circuit_id = call.metadata.get("circuit_id")
        if circuit_id:
            self._ss7.send_rel(circuit_id)
            self._trunk.active_channels = max(0, self._trunk.active_channels - 1)
        call.status = CallStatus.COMPLETED
        call.end_time = datetime.utcnow()
        return True

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
        self.health_status = (
            HealthStatus.HEALTHY
            if self._trunk.available_channels > 0
            else HealthStatus.DEGRADED
        )
        self.last_health_check = datetime.utcnow()
        return self.health_status

    def get_trunk_status(self) -> Dict[str, Any]:
        return {
            **self._trunk.to_dict(),
            "ss7_messages": len(self._ss7.get_message_log()),
        }

"""
Telephony Abstraction Layer - Base Classes

Provides provider-agnostic interfaces for telephony integration.
Implements Requirement 14.1 and 20.4 - Unified telephony interface.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Types of telephony providers"""
    ASTERISK = "asterisk"
    FREESWITCH = "freeswitch"
    THREE_CX = "3cx"
    KAMAILIO = "kamailio"
    OPENSIPS = "opensips"
    TWILIO = "twilio"
    VONAGE = "vonage"
    PLIVO = "plivo"
    BANDWIDTH = "bandwidth"
    TELNYX = "telnyx"
    SIP_TRUNK = "sip_trunk"
    WEBRTC = "webrtc"
    PSTN = "pstn"


class CallDirection(Enum):
    """Call direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(Enum):
    """Call status"""
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELLED = "cancelled"


class HealthStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Codec(Enum):
    """Supported audio codecs"""
    PCMU = "PCMU"  # G.711 μ-law
    PCMA = "PCMA"  # G.711 A-law
    OPUS = "opus"
    G722 = "G722"
    G729 = "G729"
    GSM = "GSM"
    SPEEX = "speex"


@dataclass
class QoSMetrics:
    """Quality of Service metrics for a call"""
    jitter: float = 0.0  # milliseconds
    packet_loss: float = 0.0  # percentage (0-100)
    mos_score: float = 0.0  # Mean Opinion Score (1-5)
    latency: float = 0.0  # milliseconds
    codec: str = "PCMU"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def is_acceptable(self) -> bool:
        """Check if QoS metrics meet acceptable thresholds"""
        return (
            self.jitter < 30 and  # <30ms jitter
            self.packet_loss < 1.0 and  # <1% packet loss
            self.mos_score >= 3.5 and  # MOS >= 3.5
            self.latency < 150  # <150ms latency
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "mos_score": self.mos_score,
            "latency": self.latency,
            "codec": self.codec,
            "timestamp": self.timestamp.isoformat(),
            "acceptable": self.is_acceptable()
        }


@dataclass
class CallSession:
    """Represents an active call session"""
    call_id: str
    provider_id: str
    provider_type: ProviderType
    direction: CallDirection
    from_number: str
    to_number: str
    status: CallStatus
    start_time: datetime
    answer_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    qos_metrics: Optional[QoSMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> int:
        """Get call duration in seconds"""
        if self.answer_time and self.end_time:
            return int((self.end_time - self.answer_time).total_seconds())
        return 0
    
    @property
    def is_active(self) -> bool:
        """Check if call is currently active"""
        return self.status in [
            CallStatus.RINGING,
            CallStatus.ANSWERED,
            CallStatus.IN_PROGRESS,
            CallStatus.ON_HOLD,
            CallStatus.TRANSFERRING
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "call_id": self.call_id,
            "provider_id": self.provider_id,
            "provider_type": self.provider_type.value,
            "direction": self.direction.value,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "answer_time": self.answer_time.isoformat() if self.answer_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "qos_metrics": self.qos_metrics.to_dict() if self.qos_metrics else None,
            "metadata": self.metadata
        }


@dataclass
class ProviderConfig:
    """Configuration for a telephony provider"""
    provider_id: str
    provider_type: ProviderType
    name: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type.value,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "enabled": self.enabled,
            "priority": self.priority,
            "capabilities": self.capabilities,
            "metadata": self.metadata
        }


class TelephonyProvider(ABC):
    """
    Abstract base class for telephony providers
    
    All telephony integrations must implement this interface to ensure
    consistent behavior across different providers.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize telephony provider
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.provider_type.value}")
        self.active_calls: Dict[str, CallSession] = {}
        self.health_status = HealthStatus.UNKNOWN
        self.last_health_check: Optional[datetime] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the telephony provider
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the telephony provider
        
        Returns:
            True if disconnection successful
        """
        pass
    
    @abstractmethod
    async def make_call(
        self,
        from_number: str,
        to_number: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CallSession:
        """
        Initiate an outbound call
        
        Args:
            from_number: Caller ID
            to_number: Destination number
            metadata: Additional call metadata
            
        Returns:
            CallSession object
        """
        pass
    
    @abstractmethod
    async def answer_call(self, call_id: str) -> bool:
        """
        Answer an inbound call
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def hangup_call(self, call_id: str) -> bool:
        """
        Hang up a call
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def transfer_call(
        self,
        call_id: str,
        destination: str
    ) -> bool:
        """
        Transfer a call to another destination
        
        Args:
            call_id: Call identifier
            destination: Transfer destination (number or extension)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def hold_call(self, call_id: str) -> bool:
        """
        Put a call on hold
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def unhold_call(self, call_id: str) -> bool:
        """
        Resume a call from hold
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def get_qos_metrics(self, call_id: str) -> Optional[QoSMetrics]:
        """
        Get QoS metrics for a call
        
        Args:
            call_id: Call identifier
            
        Returns:
            QoS metrics or None
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check provider health status
        
        Returns:
            Health status
        """
        pass
    
    def get_call(self, call_id: str) -> Optional[CallSession]:
        """Get call session by ID"""
        return self.active_calls.get(call_id)
    
    def get_active_calls(self) -> List[CallSession]:
        """Get all active calls"""
        return [call for call in self.active_calls.values() if call.is_active]
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            **self.config.to_dict(),
            "health_status": self.health_status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "active_calls": len(self.get_active_calls()),
            "total_calls": len(self.active_calls)
        }


class CallEventType(Enum):
    """Types of call events"""
    CALL_INITIATED = "call_initiated"
    CALL_RINGING = "call_ringing"
    CALL_ANSWERED = "call_answered"
    CALL_ENDED = "call_ended"
    CALL_FAILED = "call_failed"
    CALL_TRANSFERRED = "call_transferred"
    CALL_HELD = "call_held"
    CALL_RESUMED = "call_resumed"
    QOS_UPDATE = "qos_update"
    DTMF_RECEIVED = "dtmf_received"


@dataclass
class CallEvent:
    """Represents a call event"""
    event_type: CallEventType
    call_id: str
    provider_id: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type.value,
            "call_id": self.call_id,
            "provider_id": self.provider_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class CallEventHandler(ABC):
    """Abstract base class for handling call events"""
    
    @abstractmethod
    async def handle_event(self, event: CallEvent) -> None:
        """
        Handle a call event
        
        Args:
            event: Call event to handle
        """
        pass

"""
Open Telephony Platform

Multi-vendor telephony support including Asterisk, FreeSWITCH, 3CX,
Kamailio, OpenSIPS, direct SIP trunking, and cloud providers.
Implements Requirements 14 and 20.
"""

# Base classes and abstractions
from .base import (
    TelephonyProvider,
    CallSession,
    CallStatus,
    CallDirection,
    CallEvent,
    CallEventType,
    CallEventHandler,
    ProviderType,
    ProviderConfig,
    HealthStatus,
    QoSMetrics,
    Codec,
)

# Provider registry
from .provider_registry import (
    ProviderRegistry,
    get_registry,
    register_provider,
)

# Media processing
from .media_processor import (
    MediaProcessor,
    CodecNegotiator,
    AudioConfig,
    AudioFormat,
)

# Call controller
from .call_controller import (
    CallController,
    LoadBalancingStrategy,
)

# PBX providers
from .asterisk_provider import AsteriskProvider, AsteriskAMIClient, AsteriskARIClient
from .freeswitch_provider import FreeSwitchProvider, FreeSwitchESLClient

# Additional SIP providers
from .sip_providers import (
    ThreeCXProvider,
    KamailioProvider,
    OpenSIPSProvider,
    DirectSIPProvider,
    SRTPConfig,
)

# QoS monitoring
from .qos_monitor import QoSMonitor, QoSAlert, QoSThresholds, CallQoSTracker

# WebRTC
from .webrtc import (
    WebRTCGateway, WebRTCProvider, WebRTCSession,
    ICECandidate, ICECandidateType, STUNConfig, TURNConfig,
)

# Cloud providers
from .cloud_providers import (
    VonageProvider, PlivoProvider, BandwidthProvider, TelnyxProvider,
)

# Provider failover
from .failover import (
    ProviderFailoverManager, ProviderStats, RoutingStrategy,
)

# Legacy / PSTN
from .legacy import (
    PSTNGateway, SS7SignalingBridge, TrunkConfig, TrunkType, SS7Message,
)

# Human agent handoff
from .handoff_agent import (
    HandoffAgent,
    HandoffContext,
    HandoffRecord,
    HandoffReason,
    HandoffStatus,
    HumanAgent,
    AgentAvailability,
    AgentPool,
)

# BYOC adapter
from .byoc_adapter import (
    BYOCAdapter,
    KamailioClient,
    RTPEngineClient,
    SIPTrunk,
    RTPSession,
    SIPMethod,
    MediaDirection,
    get_byoc_adapter,
    set_byoc_adapter,
)

# BYOC feasibility spike
from .byoc_feasibility_spike import (
    BYOCFeasibilitySpike,
    Carrier,
    FeasibilityReport,
    SIPDeviation,
    CodecResult,
    Recommendation,
    SIPTraceAnalyser,
    SIPpTestHarness,
    FeasibilityReporter,
    get_feasibility_spike,
)

__all__ = [
    # Base classes
    "TelephonyProvider",
    "CallSession",
    "CallStatus",
    "CallDirection",
    "CallEvent",
    "CallEventType",
    "CallEventHandler",
    "ProviderType",
    "ProviderConfig",
    "HealthStatus",
    "QoSMetrics",
    "Codec",
    # Registry
    "ProviderRegistry",
    "get_registry",
    "register_provider",
    # Media processing
    "MediaProcessor",
    "CodecNegotiator",
    "AudioConfig",
    "AudioFormat",
    # Call controller
    "CallController",
    "LoadBalancingStrategy",
    # PBX providers
    "AsteriskProvider",
    "AsteriskAMIClient",
    "AsteriskARIClient",
    "FreeSwitchProvider",
    "FreeSwitchESLClient",
    # Additional SIP providers
    "ThreeCXProvider",
    "KamailioProvider",
    "OpenSIPSProvider",
    "DirectSIPProvider",
    "SRTPConfig",
    # QoS monitoring
    "QoSMonitor",
    "QoSAlert",
    "QoSThresholds",
    "CallQoSTracker",
    # WebRTC
    "WebRTCGateway", "WebRTCProvider", "WebRTCSession",
    "ICECandidate", "ICECandidateType", "STUNConfig", "TURNConfig",
    # Cloud providers
    "VonageProvider", "PlivoProvider", "BandwidthProvider", "TelnyxProvider",
    # Failover
    "ProviderFailoverManager", "ProviderStats", "RoutingStrategy",
    # Legacy
    "PSTNGateway", "SS7SignalingBridge", "TrunkConfig", "TrunkType",
    # Human agent handoff
    "HandoffAgent",
    "HandoffContext",
    "HandoffRecord",
    "HandoffReason",
    "HandoffStatus",
    "HumanAgent",
    "AgentAvailability",
    "AgentPool",
    # BYOC adapter
    "BYOCAdapter",
    "KamailioClient",
    "RTPEngineClient",
    "SIPTrunk",
    "RTPSession",
    "SIPMethod",
    "MediaDirection",
    "get_byoc_adapter",
    "set_byoc_adapter",
    # BYOC feasibility spike
    "BYOCFeasibilitySpike",
    "Carrier",
    "FeasibilityReport",
    "SIPDeviation",
    "CodecResult",
    "Recommendation",
    "SIPTraceAnalyser",
    "SIPpTestHarness",
    "FeasibilityReporter",
    "get_feasibility_spike",
]

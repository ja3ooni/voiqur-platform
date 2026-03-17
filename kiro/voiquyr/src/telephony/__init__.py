"""
Open Telephony Platform

Multi-vendor telephony support including Asterisk, FreeSWITCH, and cloud providers.
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
]

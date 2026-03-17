# Telephony Abstraction Layer

Provider-agnostic telephony integration framework for the EUVoice AI Platform.

## Overview

The telephony abstraction layer provides a unified interface for integrating with multiple telephony providers including:
- Open-source PBX systems (Asterisk, FreeSWITCH, 3CX)
- Cloud providers (Twilio, Vonage, Plivo, Bandwidth, Telnyx)
- Direct SIP trunking
- WebRTC
- PSTN gateways

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Call Controller                        │
│  (Load Balancing, Failover, Event Management)           │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────┐  ┌──────▼────────┐
│   Provider   │  │     Media     │
│   Registry   │  │   Processor   │
└───────┬──────┘  └───────────────┘
        │
   ┌────┴────┐
   │         │
┌──▼──┐  ┌──▼──┐  ┌──────┐
│ PBX │  │Cloud│  │  SIP │
└─────┘  └─────┘  └──────┘
```

## Components

### Base Classes (`base.py`)

Core abstractions and data models:

- **`TelephonyProvider`**: Abstract base class for all providers
- **`CallSession`**: Represents an active call
- **`QoSMetrics`**: Quality of Service metrics
- **`ProviderConfig`**: Provider configuration
- **`CallEvent`**: Call event notifications

### Provider Registry (`provider_registry.py`)

Manages provider registration and instantiation:

```python
from src.telephony import ProviderRegistry, ProviderType, ProviderConfig

registry = ProviderRegistry()

# Register a provider class
registry.register_provider_class(ProviderType.ASTERISK, AsteriskProvider)

# Create provider instance
config = ProviderConfig(
    provider_id="asterisk-1",
    provider_type=ProviderType.ASTERISK,
    name="Main Asterisk Server",
    host="pbx.example.com",
    port=5038
)
provider = registry.create_provider(config)
```

### Call Controller (`call_controller.py`)

Orchestrates calls across providers with load balancing and failover:

```python
from src.telephony import CallController

controller = CallController(
    registry=registry,
    load_balancing_strategy="least_loaded"
)

# Make a call (automatically selects best provider)
call = await controller.make_call(
    from_number="+1234567890",
    to_number="+0987654321"
)

# Answer, transfer, hangup
await controller.answer_call(call.call_id)
await controller.transfer_call(call.call_id, "+1111111111")
await controller.hangup_call(call.call_id)

# Get QoS metrics
qos = await controller.get_call_qos(call.call_id)
```

### Media Processor (`media_processor.py`)

Handles codec negotiation and audio processing:

```python
from src.telephony import MediaProcessor, Codec

processor = MediaProcessor()

# Negotiate codec
local_codecs = [Codec.PCMU, Codec.OPUS, Codec.G722]
remote_codecs = [Codec.OPUS, Codec.GSM]
codec = processor.codec_negotiator.negotiate_codec(local_codecs, remote_codecs)

# Process audio
processed = await processor.process_audio(
    audio_data,
    config,
    apply_echo_cancel=True,
    apply_noise_reduce=True
)
```

## Load Balancing Strategies

The call controller supports multiple load balancing strategies:

- **`least_loaded`**: Route to provider with fewest active calls (default)
- **`round_robin`**: Distribute calls evenly across providers
- **`priority`**: Use provider with highest priority (lowest number)
- **`cost`**: Route to lowest-cost provider

## Failover

Automatic failover is enabled by default:

- If a call fails, the controller automatically retries with another provider
- Configurable retry attempts (default: 3)
- Health checks ensure only healthy providers receive calls
- Failed providers are automatically excluded from routing

## QoS Monitoring

Real-time Quality of Service metrics:

- **Jitter**: Variation in packet arrival time (ms)
- **Packet Loss**: Percentage of lost packets
- **MOS Score**: Mean Opinion Score (1-5)
- **Latency**: Round-trip delay (ms)
- **Codec**: Audio codec in use

Acceptable thresholds:
- Jitter < 30ms
- Packet Loss < 1%
- MOS Score ≥ 3.5
- Latency < 150ms

## Event System

Subscribe to call events:

```python
from src.telephony import CallEventHandler, CallEvent

class MyEventHandler(CallEventHandler):
    async def handle_event(self, event: CallEvent):
        print(f"Event: {event.event_type.value} for call {event.call_id}")

controller.add_event_handler(MyEventHandler())
```

Event types:
- `CALL_INITIATED`
- `CALL_RINGING`
- `CALL_ANSWERED`
- `CALL_ENDED`
- `CALL_FAILED`
- `CALL_TRANSFERRED`
- `CALL_HELD`
- `CALL_RESUMED`
- `QOS_UPDATE`
- `DTMF_RECEIVED`

## Implementing a Provider

To add a new telephony provider:

```python
from src.telephony import TelephonyProvider, CallSession, HealthStatus

class MyProvider(TelephonyProvider):
    async def connect(self) -> bool:
        # Connect to provider
        self.health_status = HealthStatus.HEALTHY
        return True
    
    async def disconnect(self) -> bool:
        # Disconnect from provider
        return True
    
    async def make_call(self, from_number, to_number, metadata=None):
        # Initiate call
        call = CallSession(...)
        self.active_calls[call.call_id] = call
        return call
    
    async def answer_call(self, call_id: str) -> bool:
        # Answer call
        return True
    
    async def hangup_call(self, call_id: str) -> bool:
        # Hangup call
        return True
    
    async def transfer_call(self, call_id: str, destination: str) -> bool:
        # Transfer call
        return True
    
    async def hold_call(self, call_id: str) -> bool:
        # Hold call
        return True
    
    async def unhold_call(self, call_id: str) -> bool:
        # Unhold call
        return True
    
    async def get_qos_metrics(self, call_id: str):
        # Get QoS metrics
        return QoSMetrics(...)
    
    async def health_check(self):
        # Check health
        return HealthStatus.HEALTHY

# Register provider
from src.telephony import register_provider, ProviderType

register_provider(ProviderType.MY_PROVIDER, MyProvider)
```

## Supported Codecs

- **PCMU** (G.711 μ-law): 64kbps, good quality, high bandwidth
- **PCMA** (G.711 A-law): 64kbps, good quality, high bandwidth
- **OPUS**: 32kbps, excellent quality, medium bandwidth (preferred)
- **G.722**: 64kbps, very good quality, high bandwidth
- **G.729**: 8kbps, fair quality, low bandwidth
- **GSM**: 13kbps, fair quality, low bandwidth
- **Speex**: 24.6kbps, good quality, medium bandwidth

## Requirements

Implements:
- **Requirement 14.1**: Direct SIP trunking and PBX integration
- **Requirement 14.6**: Cloud-based and on-premise SIP with failover
- **Requirement 20.4**: Provider-agnostic call control

## Next Steps

The following provider implementations are planned:

1. **Asterisk Integration** (Task 14.2)
   - AMI, AGI, ARI support
   - Dialplan integration
   - Call recording

2. **FreeSWITCH Integration** (Task 14.3)
   - ESL support
   - mod_xml_curl
   - Conference bridges

3. **3CX, Kamailio, OpenSIPS** (Task 14.4)
   - Call Flow Designer
   - SIP server integration

4. **VoIP QoS Monitoring** (Task 14.5)
   - Real-time metrics
   - Alerting

5. **Human Agent Handoff** (Task 14.6)
   - Graceful transfers
   - Context preservation

## Testing

Run the test suite:

```bash
python test_telephony_abstraction.py
```

## License

Apache 2.0

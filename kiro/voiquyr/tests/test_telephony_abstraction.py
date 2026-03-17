"""
Test Telephony Abstraction Layer

Simple test to verify the telephony abstraction layer works correctly.
"""

import asyncio
from src.telephony import (
    TelephonyProvider,
    CallSession,
    CallStatus,
    CallDirection,
    ProviderType,
    ProviderConfig,
    HealthStatus,
    QoSMetrics,
    Codec,
    ProviderRegistry,
    CallController,
    MediaProcessor,
    AudioConfig,
)


# Mock provider for testing
class MockTelephonyProvider(TelephonyProvider):
    """Mock telephony provider for testing"""
    
    async def connect(self) -> bool:
        self.logger.info(f"Mock provider {self.config.provider_id} connected")
        self.health_status = HealthStatus.HEALTHY
        return True
    
    async def disconnect(self) -> bool:
        self.logger.info(f"Mock provider {self.config.provider_id} disconnected")
        return True
    
    async def make_call(self, from_number: str, to_number: str, metadata=None):
        import uuid
        from datetime import datetime
        
        call = CallSession(
            call_id=str(uuid.uuid4()),
            provider_id=self.config.provider_id,
            provider_type=self.config.provider_type,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            start_time=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.active_calls[call.call_id] = call
        self.logger.info(f"Mock call initiated: {call.call_id}")
        return call
    
    async def answer_call(self, call_id: str) -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.ANSWERED
            self.logger.info(f"Mock call answered: {call_id}")
            return True
        return False
    
    async def hangup_call(self, call_id: str) -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.COMPLETED
            self.logger.info(f"Mock call hung up: {call_id}")
            return True
        return False
    
    async def transfer_call(self, call_id: str, destination: str) -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.TRANSFERRING
            self.logger.info(f"Mock call transferred: {call_id} to {destination}")
            return True
        return False
    
    async def hold_call(self, call_id: str) -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.ON_HOLD
            return True
        return False
    
    async def unhold_call(self, call_id: str) -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id].status = CallStatus.IN_PROGRESS
            return True
        return False
    
    async def get_qos_metrics(self, call_id: str):
        if call_id in self.active_calls:
            return QoSMetrics(
                jitter=15.5,
                packet_loss=0.3,
                mos_score=4.2,
                latency=45.0,
                codec="PCMU"
            )
        return None
    
    async def health_check(self):
        self.health_status = HealthStatus.HEALTHY
        from datetime import datetime
        self.last_health_check = datetime.utcnow()
        return self.health_status


async def test_provider_registry():
    """Test provider registry"""
    print("\n=== Testing Provider Registry ===")
    
    registry = ProviderRegistry()
    
    # Register mock provider
    registry.register_provider_class(ProviderType.SIP_TRUNK, MockTelephonyProvider)
    
    # Create provider config
    config = ProviderConfig(
        provider_id="test-provider-1",
        provider_type=ProviderType.SIP_TRUNK,
        name="Test SIP Provider",
        host="sip.example.com",
        port=5060,
        enabled=True,
        priority=100
    )
    
    # Create provider instance
    provider = registry.create_provider(config)
    await provider.connect()
    
    # Verify provider
    assert provider is not None
    assert provider.config.provider_id == "test-provider-1"
    assert provider.health_status == HealthStatus.HEALTHY
    
    print(f"✓ Provider created: {provider.config.provider_id}")
    print(f"✓ Provider health: {provider.health_status.value}")
    
    return registry


async def test_call_controller():
    """Test call controller"""
    print("\n=== Testing Call Controller ===")
    
    # Create registry and register provider
    registry = ProviderRegistry()
    registry.register_provider_class(ProviderType.SIP_TRUNK, MockTelephonyProvider)
    
    # Create provider
    config = ProviderConfig(
        provider_id="test-provider-2",
        provider_type=ProviderType.SIP_TRUNK,
        name="Test Provider 2",
        host="sip.test.com",
        port=5060,
        enabled=True,
        priority=50
    )
    provider = registry.create_provider(config)
    await provider.connect()
    
    # Create call controller
    controller = CallController(registry=registry, load_balancing_strategy="least_loaded")
    
    # Make a call
    call = await controller.make_call(
        from_number="+1234567890",
        to_number="+0987654321",
        metadata={"test": "call"}
    )
    
    assert call is not None
    assert call.from_number == "+1234567890"
    assert call.to_number == "+0987654321"
    assert call.status == CallStatus.INITIATED
    
    print(f"✓ Call initiated: {call.call_id}")
    print(f"✓ Call status: {call.status.value}")
    
    # Answer call
    success = await controller.answer_call(call.call_id)
    assert success
    print(f"✓ Call answered")
    
    # Get QoS metrics
    qos = await controller.get_call_qos(call.call_id)
    assert qos is not None
    print(f"✓ QoS metrics: MOS={qos['mos_score']}, Jitter={qos['jitter']}ms")
    
    # Hangup call
    success = await controller.hangup_call(call.call_id)
    assert success
    print(f"✓ Call hung up")
    
    # Get statistics
    stats = controller.get_statistics()
    print(f"✓ Statistics: {stats['total_calls']} total calls, {stats['active_calls']} active")
    
    return controller


async def test_media_processor():
    """Test media processor"""
    print("\n=== Testing Media Processor ===")
    
    processor = MediaProcessor()
    
    # Test codec negotiation
    local_codecs = [Codec.PCMU, Codec.OPUS, Codec.G722]
    remote_codecs = [Codec.PCMA, Codec.OPUS, Codec.GSM]
    
    negotiated = processor.codec_negotiator.negotiate_codec(local_codecs, remote_codecs)
    assert negotiated == Codec.OPUS  # OPUS has highest preference
    print(f"✓ Codec negotiated: {negotiated.value}")
    
    # Test codec info
    codec_info = processor.codec_negotiator.get_codec_info(Codec.OPUS)
    print(f"✓ Codec info: {codec_info['name']}, {codec_info['quality']} quality")
    
    # Test audio config
    config = AudioConfig(
        sample_rate=48000,
        channels=1,
        bit_depth=16,
        codec=Codec.OPUS
    )
    print(f"✓ Audio config: {config.sample_rate}Hz, {config.codec.value}")
    
    return processor


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Telephony Abstraction Layer")
    print("=" * 60)
    
    try:
        # Test provider registry
        registry = await test_provider_registry()
        
        # Test call controller
        controller = await test_call_controller()
        
        # Test media processor
        processor = await test_media_processor()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Providers registered: {len(registry.get_all_providers())}")
        print(f"Provider types: {[t.value for t in registry.get_registered_types()]}")
        print(f"Total calls: {controller.get_statistics()['total_calls']}")
        print(f"Supported codecs: {len(processor.get_supported_codecs())}")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

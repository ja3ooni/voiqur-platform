"""
Example usage of BYOC Adapter with Kamailio and RTPEngine.
"""

import asyncio
from src.telephony.byoc_adapter import (
    BYOCAdapter,
    SIPTrunk,
    MediaDirection,
    get_byoc_adapter
)


async def main():
    # Initialize BYOC adapter
    adapter = get_byoc_adapter()
    
    # Register SIP trunks for different carriers
    adapter.register_trunk(SIPTrunk(
        trunk_id="trunk-001",
        name="Primary Carrier",
        host="sip.carrier1.com",
        port=5060,
        username="voiquyr_user",
        password="secure_pass",
        transport="UDP",
        max_channels=100
    ))
    
    adapter.register_trunk(SIPTrunk(
        trunk_id="trunk-002",
        name="Backup Carrier",
        host="sip.carrier2.com",
        port=5061,
        username="voiquyr_backup",
        password="backup_pass",
        transport="TLS",
        max_channels=50
    ))
    
    # Simulate incoming call setup
    call_id = "call-12345"
    from_tag = "tag-abc123"
    
    # SDP offer from caller
    sdp_offer = """v=0
o=- 123456 123456 IN IP4 192.168.1.100
s=Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=sendrecv"""
    
    print("Setting up call...")
    session = await adapter.setup_call(call_id, from_tag, sdp_offer, trunk_id="trunk-001")
    
    if session:
        print(f"✓ Call setup successful")
        print(f"  Call ID: {session.call_id}")
        print(f"  Media: {session.media_ip}:{session.media_port}")
        print(f"  Codec: {session.codec}")
        
        # Simulate call answer
        to_tag = "tag-xyz789"
        sdp_answer = """v=0
o=- 654321 654321 IN IP4 192.168.1.200
s=Call
c=IN IP4 192.168.1.200
t=0 0
m=audio 20000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv"""
        
        print("\nAnswering call...")
        answered = await adapter.answer_call(call_id, from_tag, to_tag, sdp_answer)
        
        if answered:
            print("✓ Call answered")
            
            # Simulate call duration
            await asyncio.sleep(2)
            
            # Get statistics
            print("\nSystem Statistics:")
            stats = await adapter.get_stats()
            
            print(f"\nKamailio:")
            print(f"  Active calls: {stats['kamailio']['active_calls']}")
            print(f"  Memory: {stats['kamailio']['memory_mb']:.1f} MB")
            
            print(f"\nRTPEngine:")
            print(f"  Active sessions: {stats['rtpengine']['active_sessions']}")
            
            print(f"\nTrunks:")
            for trunk_id, trunk_info in stats['trunks'].items():
                print(f"  {trunk_info['name']}: {trunk_info['channels']} channels")
            
            # Hangup call
            print("\nHanging up call...")
            await adapter.hangup_call(call_id, from_tag, to_tag, trunk_id="trunk-001")
            print("✓ Call terminated")
    else:
        print("✗ Call setup failed")
    
    # Cleanup
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
BYOC Adapter - Kamailio SIP proxy and RTPEngine management.

Provides integration with Kamailio for SIP signaling and RTPEngine for media handling,
enabling Bring Your Own Carrier functionality.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SIPMethod(str, Enum):
    """SIP methods."""
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    REGISTER = "REGISTER"
    OPTIONS = "OPTIONS"


class MediaDirection(str, Enum):
    """RTP media direction."""
    SENDRECV = "sendrecv"
    SENDONLY = "sendonly"
    RECVONLY = "recvonly"
    INACTIVE = "inactive"


@dataclass
class SIPTrunk:
    """SIP trunk configuration for carrier connection."""
    trunk_id: str
    name: str
    host: str
    port: int = 5060
    username: Optional[str] = None
    password: Optional[str] = None
    transport: str = "UDP"
    enabled: bool = True
    max_channels: int = 100
    current_channels: int = 0


@dataclass
class RTPSession:
    """RTP session managed by RTPEngine."""
    call_id: str
    from_tag: str
    to_tag: Optional[str] = None
    sdp_offer: Optional[str] = None
    sdp_answer: Optional[str] = None
    media_ip: Optional[str] = None
    media_port: Optional[int] = None
    codec: str = "PCMU"
    direction: MediaDirection = MediaDirection.SENDRECV
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KamailioStats:
    """Kamailio statistics."""
    active_calls: int = 0
    total_calls: int = 0
    failed_calls: int = 0
    cps: float = 0.0  # Calls per second
    memory_mb: float = 0.0
    uptime_seconds: int = 0


class KamailioClient:
    """Client for Kamailio management API (JSON-RPC)."""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}/RPC"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _rpc_call(self, method: str, params: List = None) -> Dict:
        """Execute JSON-RPC call to Kamailio."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1
        }
        
        try:
            async with self.session.post(self.base_url, json=payload) as resp:
                result = await resp.json()
                return result.get("result", {})
        except Exception as e:
            logger.error(f"Kamailio RPC error: {e}")
            return {}
    
    async def get_stats(self) -> KamailioStats:
        """Get Kamailio statistics."""
        stats = await self._rpc_call("stats.get_statistics", ["all"])
        
        return KamailioStats(
            active_calls=stats.get("dialog:active_dialogs", 0),
            total_calls=stats.get("core:rcv_requests", 0),
            failed_calls=stats.get("core:err_requests", 0),
            memory_mb=stats.get("core:shm_used_size", 0) / 1024 / 1024,
            uptime_seconds=stats.get("core:uptime", 0)
        )
    
    async def reload_routes(self) -> bool:
        """Reload routing configuration."""
        result = await self._rpc_call("cfg.reload")
        return result.get("status") == "ok"
    
    async def block_ip(self, ip: str, reason: str = "abuse") -> bool:
        """Block IP address."""
        result = await self._rpc_call("permissions.addressDump", [ip, reason])
        return bool(result)
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()


class RTPEngineClient:
    """Client for RTPEngine control protocol."""
    
    def __init__(self, host: str = "localhost", port: int = 22222):
        self.host = host
        self.port = port
        self.sessions: Dict[str, RTPSession] = {}
    
    async def _send_command(self, command: str, params: Dict) -> Dict:
        """Send command to RTPEngine via UDP."""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            
            # Build bencode message (simplified)
            message = f"{command} {self._dict_to_bencode(params)}\n"
            writer.write(message.encode())
            await writer.drain()
            
            response = await reader.read(4096)
            writer.close()
            await writer.wait_closed()
            
            return self._parse_response(response.decode())
        except Exception as e:
            logger.error(f"RTPEngine command error: {e}")
            return {}
    
    def _dict_to_bencode(self, data: Dict) -> str:
        """Simple bencode encoding."""
        # Simplified - production should use proper bencode library
        return str(data)
    
    def _parse_response(self, response: str) -> Dict:
        """Parse RTPEngine response."""
        # Simplified parser
        return {"result": "ok"}
    
    async def offer(self, call_id: str, from_tag: str, sdp: str, 
                   direction: MediaDirection = MediaDirection.SENDRECV) -> RTPSession:
        """Process SDP offer and allocate media resources."""
        params = {
            "call-id": call_id,
            "from-tag": from_tag,
            "sdp": sdp,
            "direction": [direction.value],
            "codec": {"transcode": ["PCMU", "PCMA", "opus"]}
        }
        
        result = await self._send_command("offer", params)
        
        session = RTPSession(
            call_id=call_id,
            from_tag=from_tag,
            sdp_offer=sdp,
            sdp_answer=result.get("sdp"),
            media_ip=result.get("media-ip"),
            media_port=result.get("media-port")
        )
        
        self.sessions[call_id] = session
        logger.info(f"RTP offer created for call {call_id}")
        return session
    
    async def answer(self, call_id: str, from_tag: str, to_tag: str, sdp: str) -> RTPSession:
        """Process SDP answer."""
        params = {
            "call-id": call_id,
            "from-tag": from_tag,
            "to-tag": to_tag,
            "sdp": sdp
        }
        
        result = await self._send_command("answer", params)
        
        if call_id in self.sessions:
            session = self.sessions[call_id]
            session.to_tag = to_tag
            session.sdp_answer = result.get("sdp")
            logger.info(f"RTP answer processed for call {call_id}")
            return session
        
        return None
    
    async def delete(self, call_id: str, from_tag: str, to_tag: Optional[str] = None):
        """Delete RTP session and free resources."""
        params = {
            "call-id": call_id,
            "from-tag": from_tag
        }
        if to_tag:
            params["to-tag"] = to_tag
        
        await self._send_command("delete", params)
        
        if call_id in self.sessions:
            del self.sessions[call_id]
            logger.info(f"RTP session deleted for call {call_id}")
    
    async def query(self, call_id: str) -> Optional[Dict]:
        """Query RTP session statistics."""
        params = {"call-id": call_id}
        return await self._send_command("query", params)


class BYOCAdapter:
    """BYOC adapter integrating Kamailio and RTPEngine."""
    
    def __init__(self, 
                 kamailio_host: str = "localhost",
                 kamailio_port: int = 8080,
                 rtpengine_host: str = "localhost", 
                 rtpengine_port: int = 22222):
        self.kamailio = KamailioClient(kamailio_host, kamailio_port)
        self.rtpengine = RTPEngineClient(rtpengine_host, rtpengine_port)
        self.trunks: Dict[str, SIPTrunk] = {}
    
    def register_trunk(self, trunk: SIPTrunk):
        """Register SIP trunk for carrier connection."""
        self.trunks[trunk.trunk_id] = trunk
        logger.info(f"Registered SIP trunk: {trunk.name} ({trunk.host}:{trunk.port})")
    
    def get_trunk(self, trunk_id: str) -> Optional[SIPTrunk]:
        """Get SIP trunk by ID."""
        return self.trunks.get(trunk_id)
    
    def get_available_trunk(self) -> Optional[SIPTrunk]:
        """Get available trunk with capacity."""
        for trunk in self.trunks.values():
            if trunk.enabled and trunk.current_channels < trunk.max_channels:
                return trunk
        return None
    
    async def setup_call(self, call_id: str, from_tag: str, 
                        sdp_offer: str, trunk_id: Optional[str] = None) -> Optional[RTPSession]:
        """Setup call with SIP trunk and RTP session."""
        trunk = self.get_trunk(trunk_id) if trunk_id else self.get_available_trunk()
        
        if not trunk:
            logger.error("No available SIP trunk")
            return None
        
        # Allocate RTP resources
        session = await self.rtpengine.offer(call_id, from_tag, sdp_offer)
        
        if session:
            trunk.current_channels += 1
            logger.info(f"Call {call_id} setup on trunk {trunk.name}")
        
        return session
    
    async def answer_call(self, call_id: str, from_tag: str, 
                         to_tag: str, sdp_answer: str) -> Optional[RTPSession]:
        """Process call answer."""
        return await self.rtpengine.answer(call_id, from_tag, to_tag, sdp_answer)
    
    async def hangup_call(self, call_id: str, from_tag: str, 
                         to_tag: Optional[str] = None, trunk_id: Optional[str] = None):
        """Hangup call and release resources."""
        await self.rtpengine.delete(call_id, from_tag, to_tag)
        
        if trunk_id:
            trunk = self.get_trunk(trunk_id)
            if trunk and trunk.current_channels > 0:
                trunk.current_channels -= 1
        
        logger.info(f"Call {call_id} terminated")
    
    async def get_stats(self) -> Dict:
        """Get combined statistics."""
        kamailio_stats = await self.kamailio.get_stats()
        
        return {
            "kamailio": {
                "active_calls": kamailio_stats.active_calls,
                "total_calls": kamailio_stats.total_calls,
                "failed_calls": kamailio_stats.failed_calls,
                "cps": kamailio_stats.cps,
                "memory_mb": kamailio_stats.memory_mb,
                "uptime_seconds": kamailio_stats.uptime_seconds
            },
            "rtpengine": {
                "active_sessions": len(self.rtpengine.sessions)
            },
            "trunks": {
                trunk_id: {
                    "name": trunk.name,
                    "enabled": trunk.enabled,
                    "channels": f"{trunk.current_channels}/{trunk.max_channels}"
                }
                for trunk_id, trunk in self.trunks.items()
            }
        }
    
    async def close(self):
        """Close connections."""
        await self.kamailio.close()


# Global instance
_byoc_adapter: Optional[BYOCAdapter] = None


def get_byoc_adapter() -> BYOCAdapter:
    """Get global BYOC adapter instance."""
    global _byoc_adapter
    if _byoc_adapter is None:
        _byoc_adapter = BYOCAdapter()
    return _byoc_adapter


def set_byoc_adapter(adapter: BYOCAdapter) -> None:
    """Set global BYOC adapter instance."""
    global _byoc_adapter
    _byoc_adapter = adapter

"""
Twilio Phone Provider - Voiquyr telephony integration via Twilio
Implements TEL-01, TEL-02, TEL-03
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import aiohttp

from .base import (
    TelephonyProvider,
    ProviderType,
    ProviderConfig,
    CallSession,
    CallDirection,
    CallStatus,
    HealthStatus,
    QoSMetrics,
)

logger = logging.getLogger(__name__)


class TwilioConfig(ProviderConfig):
    """Twilio-specific configuration"""
    account_sid: str = ""
    auth_token: str = ""
    phone_number: str = ""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.provider_type = ProviderType.TWILIO
        

class TwilioProvider(TelephonyProvider):
    """Twilio cloud telephony provider"""
    
    def __init__(self, config: TwilioConfig):
        super().__init__(config)
        self._base_url = "https://api.twilio.com/2010-04-01"
        self._session: Optional[aiohttp.ClientSession] = None
        
    def _auth_headers(self) -> Dict[str, str]:
        """Create Basic Auth headers for Twilio"""
        auth_string = f"{self.config.account_sid}:{self.config.auth_token}"
        encoded = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._auth_headers())
        return self._session
        
    async def authenticate(self) -> bool:
        """Verify credentials with Twilio API"""
        try:
            s = await self._get_session()
            url = f"{self._base_url}/Accounts/{self.config.account_sid}.json"
            async with s.get(url, ssl=False) as r:
                if r.status == 200:
                    self.health_status = HealthStatus.HEALTHY
                    return True
                self.health_status = HealthStatus.DEGRADED
                return False
        except Exception as e:
            logger.error(f"Twilio authentication failed: {e}")
            self.health_status = HealthStatus.UNHEALTHY
            return False
            
    async def make_call(
        self,
        to_number: str,
        from_number: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[str]:
        """Make outbound call via Twilio API
        
        Args:
            to_number: Target phone number
            from_number: Caller ID (uses config if not provided)
            url: TwiML URL for call handling
            
        Returns:
            Call SID if successful, None on failure
        """
        if not self.config.account_sid or not self.config.auth_token:
            logger.error("Twilio credentials not configured")
            return None
            
        from_number = from_number or self.config.phone_number
        
        try:
            s = await self._get_session()
            url = f"{self._base_url}/Accounts/{self.config.account_sid}/Calls.json"
            
            data = {
                "To": to_number,
                "From": from_number,
                "Url": url or "http://twiml.com/dummy",  # Required but can be dummy
            }
            
            async with s.post(url, data=data, ssl=False) as r:
                if r.status in (200, 201):
                    result = await r.json()
                    call_sid = result.get("sid") or result.get("call_sid")
                    logger.info(f"Call initiated: {call_sid}")
                    return call_sid
                else:
                    error = await r.text()
                    logger.error(f"Twilio call failed: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"make_call error: {e}")
            return None
            
    async def send_sms(
        self,
        to_number: str,
        body: str,
        from_number: Optional[str] = None,
    ) -> Optional[str]:
        """Send SMS via Twilio API
        
        Args:
            to_number: Target phone number
            body: SMS message body
            from_number: Sender ID (uses config if not provided)
            
        Returns:
            Message SID if successful, None on failure
        """
        if not self.config.account_sid or not self.config.auth_token:
            logger.error("Twilio credentials not configured")
            return None
            
        from_number = from_number or self.config.phone_number
        
        try:
            s = await self._get_session()
            url = f"{self._base_url}/Accounts/{self.config.account_sid}/Messages.json"
            
            data = {
                "To": to_number,
                "From": from_number,
                "Body": body,
            }
            
            async with s.post(url, data=data, ssl=False) as r:
                if r.status in (200, 201):
                    result = await r.json()
                    msg_sid = result.get("sid") or result.get("message_sid")
                    logger.info(f"SMS sent: {msg_sid}")
                    return msg_sid
                else:
                    error = await r.text()
                    logger.error(f"Twilio SMS failed: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"send_sms error: {e}")
            return None
            
    async def end_call(self, call_id: str) -> bool:
        """End an active call"""
        try:
            s = await self._get_session()
            url = f"{self._base_url}/Accounts/{self.config.account_sid}/Calls/{call_id}"
            
            data = {"Status": "completed"}
            async with s.post(url, data=data, ssl=False) as r:
                return r.status in (200, 201)
        except Exception as e:
            logger.error(f"end_call error: {e}")
            return False
            
    async def get_call_status(self, call_id: str) -> Optional[CallSession]:
        """Get call status from Twilio"""
        try:
            s = await self._get_session()
            url = f"{self._base_url}/Accounts/{self.config.account_sid}/Calls/{call_id}.json"
            async with s.get(url, ssl=False) as r:
                if r.status == 200:
                    data = await r.json()
                    return CallSession(
                        call_id=data.get("sid", call_id),
                        provider_id=self.config.account_sid,
                        provider_type=ProviderType.TWILIO,
                        direction=CallDirection.OUTBOUND,
                        from_number=data.get("from", ""),
                        to_number=data.get("to", ""),
                        status=CallStatus.IN_PROGRESS,  # Map from Twilio status
                        start_time=datetime.now(),
                    )
        except Exception as e:
            logger.error(f"get_call_status error: {e}")
            return None
            
    async def disconnect(self) -> bool:
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
        self.health_status = HealthStatus.UNKNOWN
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize provider config"""
        return {
            "provider_type": "twilio",
            "account_sid": self.config.account_sid[:8] + "..." if self.config.account_sid else None,
            "phone_number": self.config.phone_number,
        }
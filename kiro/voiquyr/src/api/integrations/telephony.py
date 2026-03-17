"""
Telephony Integrations

Twilio EU integration for voice calls, SMS, and WhatsApp messaging
with the EUVoice AI Platform.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import base64
from urllib.parse import urlencode

from .base import BaseIntegration, IntegrationConfig, IntegrationType, AuthenticationError, IntegrationError
from ..utils.webhook_publisher import get_global_publisher


class TwilioConfig(IntegrationConfig):
    """Twilio-specific configuration."""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = IntegrationType.TELEPHONY
        self.provider = "twilio"
    
    # Twilio-specific settings
    account_sid: str = ""
    auth_token: str = ""
    phone_number: str = ""
    
    # EU compliance settings
    edge_location: str = "dublin"  # Twilio EU edge location
    region: str = "ie1"  # Ireland region for EU compliance
    
    # Voice settings
    voice_url: Optional[str] = None
    voice_method: str = "POST"
    status_callback_url: Optional[str] = None
    
    # SMS settings
    sms_url: Optional[str] = None
    sms_method: str = "POST"
    
    # WhatsApp settings
    whatsapp_number: Optional[str] = None
    
    # Recording settings
    record_calls: bool = False
    recording_channels: str = "dual"
    recording_status_callback_url: Optional[str] = None


class TwilioCall:
    """Twilio call representation."""
    
    def __init__(self, call_data: Dict[str, Any]):
        self.sid = call_data.get("sid")
        self.from_number = call_data.get("from")
        self.to_number = call_data.get("to")
        self.status = call_data.get("status")
        self.direction = call_data.get("direction")
        self.duration = call_data.get("duration")
        self.price = call_data.get("price")
        self.date_created = call_data.get("date_created")
        self.date_updated = call_data.get("date_updated")
        self.recording_url = call_data.get("recording_url")


class TwilioMessage:
    """Twilio message representation."""
    
    def __init__(self, message_data: Dict[str, Any]):
        self.sid = message_data.get("sid")
        self.from_number = message_data.get("from")
        self.to_number = message_data.get("to")
        self.body = message_data.get("body")
        self.status = message_data.get("status")
        self.direction = message_data.get("direction")
        self.price = message_data.get("price")
        self.date_created = message_data.get("date_created")
        self.date_updated = message_data.get("date_updated")
        self.media_urls = message_data.get("media_urls", [])


class TwilioIntegration(BaseIntegration):
    """
    Twilio integration for telephony services.
    
    Provides voice calling, SMS, and WhatsApp messaging capabilities
    with EU compliance and GDPR support.
    """
    
    def __init__(self, config: TwilioConfig):
        """
        Initialize Twilio integration.
        
        Args:
            config: Twilio configuration
        """
        super().__init__(config)
        self.config: TwilioConfig = config
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}"
        
        # EU compliance - use Dublin edge location
        if config.eu_region:
            self.base_url = f"https://{config.edge_location}.api.twilio.com/2010-04-01/Accounts/{config.account_sid}"
        
        # Active calls and messages tracking
        self.active_calls = {}
        self.active_messages = {}
        
        # Webhook publisher for events
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize Twilio integration."""
        try:
            self.logger.info("Initializing Twilio integration")
            
            # Validate required configuration
            if not self.config.account_sid:
                raise ConfigurationError("Twilio Account SID is required")
            
            if not self.config.auth_token:
                raise ConfigurationError("Twilio Auth Token is required")
            
            if not self.config.phone_number:
                raise ConfigurationError("Twilio phone number is required")
            
            # Set up authentication headers
            self._auth_header = self._create_auth_header()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Twilio integration: {e}")
            return False
    
    def _create_auth_header(self) -> str:
        """Create HTTP Basic Auth header for Twilio API."""
        credentials = f"{self.config.account_sid}:{self.config.auth_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    async def authenticate(self) -> bool:
        """Authenticate with Twilio API."""
        try:
            # Test authentication by fetching account info
            response = await self._make_request(
                "GET",
                f"{self.base_url}.json",
                headers={"Authorization": self._auth_header}
            )
            
            if response["success"]:
                account_data = response["data"]
                self.logger.info(f"Authenticated with Twilio account: {account_data.get('friendly_name', 'Unknown')}")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with Twilio")
                
        except Exception as e:
            self.logger.error(f"Twilio authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Twilio integration."""
        try:
            # Check account status
            response = await self._make_request(
                "GET",
                f"{self.base_url}.json",
                headers={"Authorization": self._auth_header}
            )
            
            if response["success"]:
                account_data = response["data"]
                account_status = account_data.get("status", "unknown")
                
                if account_status == "active":
                    self._last_health_check = datetime.utcnow()
                    return True
                else:
                    self.logger.warning(f"Twilio account status: {account_status}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Twilio health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Twilio (cleanup resources)."""
        try:
            # End any active calls
            for call_sid in list(self.active_calls.keys()):
                await self.end_call(call_sid)
            
            self.active_calls.clear()
            self.active_messages.clear()
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during Twilio disconnect: {e}")
    
    # Voice Call Methods
    
    async def make_call(self, 
                       to_number: str,
                       twiml_url: Optional[str] = None,
                       twiml: Optional[str] = None,
                       record: bool = None,
                       timeout: int = 30,
                       **kwargs) -> TwilioCall:
        """
        Make an outbound voice call.
        
        Args:
            to_number: Destination phone number
            twiml_url: URL that returns TwiML instructions
            twiml: TwiML instructions directly
            record: Whether to record the call
            timeout: Call timeout in seconds
            **kwargs: Additional call parameters
            
        Returns:
            TwilioCall object
        """
        try:
            # Prepare call data
            call_data = {
                "To": to_number,
                "From": self.config.phone_number,
                "Timeout": timeout
            }
            
            # Add TwiML instructions
            if twiml_url:
                call_data["Url"] = twiml_url
                call_data["Method"] = self.config.voice_method
            elif twiml:
                call_data["Twiml"] = twiml
            elif self.config.voice_url:
                call_data["Url"] = self.config.voice_url
                call_data["Method"] = self.config.voice_method
            else:
                raise IntegrationError("No TwiML URL or instructions provided")
            
            # Recording settings
            if record is not None:
                call_data["Record"] = "true" if record else "false"
            elif self.config.record_calls:
                call_data["Record"] = "true"
                call_data["RecordingChannels"] = self.config.recording_channels
                if self.config.recording_status_callback_url:
                    call_data["RecordingStatusCallback"] = self.config.recording_status_callback_url
            
            # Status callback
            if self.config.status_callback_url:
                call_data["StatusCallback"] = self.config.status_callback_url
                call_data["StatusCallbackMethod"] = "POST"
            
            # Additional parameters
            call_data.update(kwargs)
            
            # Make API call
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Calls.json",
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=urlencode(call_data)
            )
            
            if response["success"]:
                call_info = TwilioCall(response["data"])
                self.active_calls[call_info.sid] = call_info
                
                # Emit call started event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="call.started",
                        data={
                            "call_sid": call_info.sid,
                            "from": call_info.from_number,
                            "to": call_info.to_number,
                            "direction": "outbound"
                        },
                        source="twilio_integration"
                    )
                
                return call_info
            else:
                raise IntegrationError(f"Failed to make call: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Failed to make call to {to_number}: {e}")
            raise
    
    async def end_call(self, call_sid: str) -> bool:
        """
        End an active call.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            True if call ended successfully
        """
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Calls/{call_sid}.json",
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=urlencode({"Status": "completed"})
            )
            
            if response["success"]:
                # Remove from active calls
                if call_sid in self.active_calls:
                    call_info = self.active_calls.pop(call_sid)
                    
                    # Emit call ended event
                    if self.webhook_publisher:
                        await self.webhook_publisher.publish_custom_event(
                            event_type="call.ended",
                            data={
                                "call_sid": call_sid,
                                "from": call_info.from_number,
                                "to": call_info.to_number,
                                "duration": call_info.duration
                            },
                            source="twilio_integration"
                        )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to end call {call_sid}: {e}")
            return False
    
    async def get_call_status(self, call_sid: str) -> Optional[TwilioCall]:
        """
        Get call status and information.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            TwilioCall object or None if not found
        """
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/Calls/{call_sid}.json",
                headers={"Authorization": self._auth_header}
            )
            
            if response["success"]:
                return TwilioCall(response["data"])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get call status for {call_sid}: {e}")
            return None
    
    # SMS Methods
    
    async def send_sms(self, 
                      to_number: str,
                      message: str,
                      media_urls: Optional[List[str]] = None,
                      **kwargs) -> TwilioMessage:
        """
        Send SMS message.
        
        Args:
            to_number: Destination phone number
            message: Message text
            media_urls: Optional media URLs for MMS
            **kwargs: Additional message parameters
            
        Returns:
            TwilioMessage object
        """
        try:
            # Prepare message data
            message_data = {
                "To": to_number,
                "From": self.config.phone_number,
                "Body": message
            }
            
            # Add media URLs for MMS
            if media_urls:
                for i, url in enumerate(media_urls):
                    message_data[f"MediaUrl{i}"] = url
            
            # Status callback
            if self.config.sms_url:
                message_data["StatusCallback"] = self.config.sms_url
            
            # Additional parameters
            message_data.update(kwargs)
            
            # Make API call
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Messages.json",
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=urlencode(message_data)
            )
            
            if response["success"]:
                message_info = TwilioMessage(response["data"])
                self.active_messages[message_info.sid] = message_info
                
                # Emit message sent event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.sent",
                        data={
                            "message_sid": message_info.sid,
                            "from": message_info.from_number,
                            "to": message_info.to_number,
                            "body": message_info.body,
                            "type": "sms"
                        },
                        source="twilio_integration"
                    )
                
                return message_info
            else:
                raise IntegrationError(f"Failed to send SMS: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Failed to send SMS to {to_number}: {e}")
            raise
    
    # WhatsApp Methods
    
    async def send_whatsapp_message(self, 
                                   to_number: str,
                                   message: str,
                                   media_urls: Optional[List[str]] = None,
                                   **kwargs) -> TwilioMessage:
        """
        Send WhatsApp message.
        
        Args:
            to_number: Destination WhatsApp number (with whatsapp: prefix)
            message: Message text
            media_urls: Optional media URLs
            **kwargs: Additional message parameters
            
        Returns:
            TwilioMessage object
        """
        try:
            if not self.config.whatsapp_number:
                raise IntegrationError("WhatsApp number not configured")
            
            # Ensure WhatsApp prefix
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Prepare message data
            message_data = {
                "To": to_number,
                "From": f"whatsapp:{self.config.whatsapp_number}",
                "Body": message
            }
            
            # Add media URLs
            if media_urls:
                for i, url in enumerate(media_urls):
                    message_data[f"MediaUrl{i}"] = url
            
            # Additional parameters
            message_data.update(kwargs)
            
            # Make API call
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Messages.json",
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=urlencode(message_data)
            )
            
            if response["success"]:
                message_info = TwilioMessage(response["data"])
                self.active_messages[message_info.sid] = message_info
                
                # Emit WhatsApp message sent event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.sent",
                        data={
                            "message_sid": message_info.sid,
                            "from": message_info.from_number,
                            "to": message_info.to_number,
                            "body": message_info.body,
                            "type": "whatsapp"
                        },
                        source="twilio_integration"
                    )
                
                return message_info
            else:
                raise IntegrationError(f"Failed to send WhatsApp message: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Failed to send WhatsApp message to {to_number}: {e}")
            raise
    
    # TwiML Generation Helpers
    
    def generate_voice_twiml(self, 
                           text: Optional[str] = None,
                           voice: str = "alice",
                           language: str = "en-US",
                           gather_input: bool = False,
                           gather_timeout: int = 5,
                           record_message: bool = False,
                           **kwargs) -> str:
        """
        Generate TwiML for voice responses.
        
        Args:
            text: Text to speak
            voice: Voice to use
            language: Language code
            gather_input: Whether to gather user input
            gather_timeout: Timeout for input gathering
            record_message: Whether to record user message
            **kwargs: Additional TwiML parameters
            
        Returns:
            TwiML XML string
        """
        twiml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<Response>']
        
        if text:
            twiml_parts.append(f'<Say voice="{voice}" language="{language}">{text}</Say>')
        
        if gather_input:
            gather_attrs = f'timeout="{gather_timeout}"'
            if kwargs.get('gather_action'):
                gather_attrs += f' action="{kwargs["gather_action"]}"'
            if kwargs.get('gather_method'):
                gather_attrs += f' method="{kwargs["gather_method"]}"'
            
            twiml_parts.append(f'<Gather {gather_attrs}>')
            if kwargs.get('gather_say'):
                twiml_parts.append(f'<Say voice="{voice}" language="{language}">{kwargs["gather_say"]}</Say>')
            twiml_parts.append('</Gather>')
        
        if record_message:
            record_attrs = 'maxLength="30" finishOnKey="#"'
            if kwargs.get('record_action'):
                record_attrs += f' action="{kwargs["record_action"]}"'
            twiml_parts.append(f'<Record {record_attrs}/>')
        
        if kwargs.get('redirect_url'):
            twiml_parts.append(f'<Redirect>{kwargs["redirect_url"]}</Redirect>')
        
        twiml_parts.append('</Response>')
        
        return '\n'.join(twiml_parts)
    
    # Webhook Handlers
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Twilio webhook.
        
        Args:
            webhook_data: Webhook payload from Twilio
            
        Returns:
            Response data
        """
        try:
            event_type = webhook_data.get("EventType", "unknown")
            
            if event_type == "call-status":
                return await self._handle_call_status_webhook(webhook_data)
            elif event_type == "message-status":
                return await self._handle_message_status_webhook(webhook_data)
            elif event_type == "recording-status":
                return await self._handle_recording_status_webhook(webhook_data)
            else:
                self.logger.warning(f"Unknown webhook event type: {event_type}")
                return {"status": "ignored"}
                
        except Exception as e:
            self.logger.error(f"Error handling Twilio webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_call_status_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call status webhook."""
        call_sid = data.get("CallSid")
        call_status = data.get("CallStatus")
        
        if call_sid and self.webhook_publisher:
            await self.webhook_publisher.publish_custom_event(
                event_type=f"call.{call_status}",
                data={
                    "call_sid": call_sid,
                    "status": call_status,
                    "from": data.get("From"),
                    "to": data.get("To"),
                    "duration": data.get("CallDuration"),
                    "direction": data.get("Direction")
                },
                source="twilio_integration"
            )
        
        return {"status": "processed"}
    
    async def _handle_message_status_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message status webhook."""
        message_sid = data.get("MessageSid")
        message_status = data.get("MessageStatus")
        
        if message_sid and self.webhook_publisher:
            await self.webhook_publisher.publish_custom_event(
                event_type=f"message.{message_status}",
                data={
                    "message_sid": message_sid,
                    "status": message_status,
                    "from": data.get("From"),
                    "to": data.get("To"),
                    "body": data.get("Body")
                },
                source="twilio_integration"
            )
        
        return {"status": "processed"}
    
    async def _handle_recording_status_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recording status webhook."""
        recording_sid = data.get("RecordingSid")
        recording_status = data.get("RecordingStatus")
        
        if recording_sid and self.webhook_publisher:
            await self.webhook_publisher.publish_custom_event(
                event_type=f"recording.{recording_status}",
                data={
                    "recording_sid": recording_sid,
                    "status": recording_status,
                    "call_sid": data.get("CallSid"),
                    "recording_url": data.get("RecordingUrl"),
                    "duration": data.get("RecordingDuration")
                },
                source="twilio_integration"
            )
        
        return {"status": "processed"}
    
    # Utility Methods
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Twilio account information."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}.json",
                headers={"Authorization": self._auth_header}
            )
            
            if response["success"]:
                return response["data"]
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {}
    
    async def list_phone_numbers(self) -> List[Dict[str, Any]]:
        """List available phone numbers."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/IncomingPhoneNumbers.json",
                headers={"Authorization": self._auth_header}
            )
            
            if response["success"]:
                return response["data"].get("incoming_phone_numbers", [])
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to list phone numbers: {e}")
            return []
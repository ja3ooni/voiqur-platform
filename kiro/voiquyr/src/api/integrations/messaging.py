"""
Messaging Platform Integrations

WhatsApp, Telegram, and Slack integrations for multi-channel
voice assistant communication.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import base64
from urllib.parse import urlencode, quote

from .base import BaseIntegration, IntegrationConfig, IntegrationType, AuthenticationError, IntegrationError
from ..utils.webhook_publisher import get_global_publisher


class WhatsAppConfig(IntegrationConfig):
    """WhatsApp Business API configuration."""
    
    type: IntegrationType = IntegrationType.MESSAGING
    provider: str = "whatsapp"
    
    # WhatsApp Business API settings
    access_token: str = ""
    phone_number_id: str = ""
    business_account_id: str = ""
    
    # Webhook settings
    verify_token: str = ""
    webhook_secret: str = ""
    
    # Message settings
    enable_read_receipts: bool = True
    enable_delivery_receipts: bool = True


class TelegramConfig(IntegrationConfig):
    """Telegram Bot API configuration."""
    
    type: IntegrationType = IntegrationType.MESSAGING
    provider: str = "telegram"
    
    # Bot settings
    bot_token: str = ""
    bot_username: str = ""
    
    # Webhook settings
    webhook_secret: str = ""
    
    # Message settings
    parse_mode: str = "HTML"  # HTML, Markdown, MarkdownV2
    disable_web_page_preview: bool = True


class SlackConfig(IntegrationConfig):
    """Slack App configuration."""
    
    type: IntegrationType = IntegrationType.MESSAGING
    provider: str = "slack"
    
    # OAuth settings
    client_id: str = ""
    client_secret: str = ""
    bot_token: str = ""
    user_token: str = ""
    
    # App settings
    app_id: str = ""
    signing_secret: str = ""
    
    # Workspace settings
    workspace_id: str = ""
    default_channel: str = "#general"


class MessagingMessage:
    """Generic messaging platform message."""
    
    def __init__(self, message_data: Dict[str, Any], platform: str):
        self.id = message_data.get("id")
        self.platform = platform
        self.from_user = message_data.get("from_user")
        self.to_user = message_data.get("to_user")
        self.chat_id = message_data.get("chat_id")
        self.text = message_data.get("text")
        self.message_type = message_data.get("type", "text")
        self.timestamp = message_data.get("timestamp", datetime.utcnow())
        self.media_urls = message_data.get("media_urls", [])
        self.metadata = message_data.get("metadata", {})


class WhatsAppIntegration(BaseIntegration):
    """
    WhatsApp Business API integration.
    
    Provides messaging capabilities through WhatsApp Business API
    with support for text, media, and interactive messages.
    """
    
    def __init__(self, config: WhatsAppConfig):
        """
        Initialize WhatsApp integration.
        
        Args:
            config: WhatsApp configuration
        """
        super().__init__(config)
        self.config: WhatsAppConfig = config
        self.api_base = "https://graph.facebook.com/v18.0"
        
        # Webhook publisher
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize WhatsApp integration."""
        try:
            self.logger.info("Initializing WhatsApp integration")
            
            # Validate configuration
            if not self.config.access_token:
                raise ConfigurationError("WhatsApp Access Token is required")
            
            if not self.config.phone_number_id:
                raise ConfigurationError("WhatsApp Phone Number ID is required")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WhatsApp integration: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with WhatsApp Business API."""
        try:
            # Test authentication by getting phone number info
            response = await self._make_request(
                "GET",
                f"{self.api_base}/{self.config.phone_number_id}",
                headers={"Authorization": f"Bearer {self.config.access_token}"}
            )
            
            if response["success"]:
                phone_info = response["data"]
                self.logger.info(f"Authenticated with WhatsApp number: {phone_info.get('display_phone_number', 'Unknown')}")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with WhatsApp")
                
        except Exception as e:
            self.logger.error(f"WhatsApp authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on WhatsApp integration."""
        try:
            # Check phone number status
            response = await self._make_request(
                "GET",
                f"{self.api_base}/{self.config.phone_number_id}",
                headers={"Authorization": f"Bearer {self.config.access_token}"}
            )
            
            if response["success"]:
                phone_info = response["data"]
                status = phone_info.get("status", "unknown")
                
                if status == "CONNECTED":
                    self._last_health_check = datetime.utcnow()
                    return True
                else:
                    self.logger.warning(f"WhatsApp phone number status: {status}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"WhatsApp health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from WhatsApp (cleanup resources)."""
        try:
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during WhatsApp disconnect: {e}")
    
    async def send_message(self, 
                          to_number: str,
                          message: str,
                          message_type: str = "text",
                          media_url: Optional[str] = None,
                          **kwargs) -> Optional[MessagingMessage]:
        """
        Send WhatsApp message.
        
        Args:
            to_number: Recipient phone number
            message: Message text
            message_type: Type of message (text, image, audio, video, document)
            media_url: URL for media messages
            **kwargs: Additional message parameters
            
        Returns:
            MessagingMessage object or None if failed
        """
        try:
            # Prepare message data
            message_data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": message_type
            }
            
            if message_type == "text":
                message_data["text"] = {"body": message}
            elif message_type in ["image", "audio", "video", "document"]:
                if not media_url:
                    raise IntegrationError(f"Media URL required for {message_type} messages")
                
                message_data[message_type] = {"link": media_url}
                if message:
                    message_data[message_type]["caption"] = message
            
            # Send message
            response = await self._make_request(
                "POST",
                f"{self.api_base}/{self.config.phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {self.config.access_token}",
                    "Content-Type": "application/json"
                },
                json=message_data
            )
            
            if response["success"]:
                message_id = response["data"]["messages"][0]["id"]
                
                # Create message object
                msg_data = {
                    "id": message_id,
                    "to_user": to_number,
                    "text": message,
                    "type": message_type,
                    "media_urls": [media_url] if media_url else []
                }
                
                msg = MessagingMessage(msg_data, "whatsapp")
                
                # Emit message sent event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.sent",
                        data={
                            "message_id": message_id,
                            "platform": "whatsapp",
                            "to": to_number,
                            "text": message,
                            "type": message_type
                        },
                        source="whatsapp_integration"
                    )
                
                return msg
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to send WhatsApp message to {to_number}: {e}")
            return None
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp webhook.
        
        Args:
            webhook_data: Webhook payload from WhatsApp
            
        Returns:
            Response data
        """
        try:
            # Verify webhook (simplified - should verify signature in production)
            if webhook_data.get("object") != "whatsapp_business_account":
                return {"status": "ignored"}
            
            # Process webhook entries
            for entry in webhook_data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        await self._handle_message_webhook(change["value"])
            
            return {"status": "processed"}
            
        except Exception as e:
            self.logger.error(f"Error handling WhatsApp webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_message_webhook(self, message_data: Dict[str, Any]) -> None:
        """Handle incoming message webhook."""
        try:
            messages = message_data.get("messages", [])
            
            for message in messages:
                message_id = message.get("id")
                from_number = message.get("from")
                message_type = message.get("type", "text")
                
                # Extract message content based on type
                text = ""
                if message_type == "text":
                    text = message.get("text", {}).get("body", "")
                elif message_type == "audio":
                    text = "[Audio Message]"
                elif message_type == "image":
                    text = message.get("image", {}).get("caption", "[Image]")
                
                # Emit message received event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.received",
                        data={
                            "message_id": message_id,
                            "platform": "whatsapp",
                            "from": from_number,
                            "text": text,
                            "type": message_type,
                            "timestamp": message.get("timestamp")
                        },
                        source="whatsapp_integration"
                    )
                
        except Exception as e:
            self.logger.error(f"Error handling WhatsApp message webhook: {e}")


class TelegramIntegration(BaseIntegration):
    """
    Telegram Bot API integration.
    
    Provides messaging capabilities through Telegram Bot API
    with support for text, media, and inline keyboards.
    """
    
    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram integration.
        
        Args:
            config: Telegram configuration
        """
        super().__init__(config)
        self.config: TelegramConfig = config
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"
        
        # Webhook publisher
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize Telegram integration."""
        try:
            self.logger.info("Initializing Telegram integration")
            
            # Validate configuration
            if not self.config.bot_token:
                raise ConfigurationError("Telegram Bot Token is required")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram integration: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Telegram Bot API."""
        try:
            # Test authentication by getting bot info
            response = await self._make_request(
                "GET",
                f"{self.api_base}/getMe"
            )
            
            if response["success"] and response["data"]["ok"]:
                bot_info = response["data"]["result"]
                self.logger.info(f"Authenticated with Telegram bot: @{bot_info.get('username', 'Unknown')}")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with Telegram")
                
        except Exception as e:
            self.logger.error(f"Telegram authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Telegram integration."""
        try:
            # Check bot status
            response = await self._make_request(
                "GET",
                f"{self.api_base}/getMe"
            )
            
            if response["success"] and response["data"]["ok"]:
                self._last_health_check = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Telegram health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram (cleanup resources)."""
        try:
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during Telegram disconnect: {e}")
    
    async def send_message(self, 
                          chat_id: Union[str, int],
                          message: str,
                          parse_mode: Optional[str] = None,
                          reply_markup: Optional[Dict] = None,
                          **kwargs) -> Optional[MessagingMessage]:
        """
        Send Telegram message.
        
        Args:
            chat_id: Chat ID or username
            message: Message text
            parse_mode: Message parse mode (HTML, Markdown, MarkdownV2)
            reply_markup: Inline keyboard or reply markup
            **kwargs: Additional message parameters
            
        Returns:
            MessagingMessage object or None if failed
        """
        try:
            # Prepare message data
            message_data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode or self.config.parse_mode,
                "disable_web_page_preview": self.config.disable_web_page_preview
            }
            
            if reply_markup:
                message_data["reply_markup"] = json.dumps(reply_markup)
            
            # Additional parameters
            message_data.update(kwargs)
            
            # Send message
            response = await self._make_request(
                "POST",
                f"{self.api_base}/sendMessage",
                headers={"Content-Type": "application/json"},
                json=message_data
            )
            
            if response["success"] and response["data"]["ok"]:
                result = response["data"]["result"]
                message_id = result["message_id"]
                
                # Create message object
                msg_data = {
                    "id": str(message_id),
                    "chat_id": str(chat_id),
                    "text": message,
                    "type": "text"
                }
                
                msg = MessagingMessage(msg_data, "telegram")
                
                # Emit message sent event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.sent",
                        data={
                            "message_id": message_id,
                            "platform": "telegram",
                            "chat_id": chat_id,
                            "text": message
                        },
                        source="telegram_integration"
                    )
                
                return msg
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return None
    
    async def send_voice_message(self, 
                                chat_id: Union[str, int],
                                voice_url: str,
                                caption: Optional[str] = None,
                                **kwargs) -> Optional[MessagingMessage]:
        """
        Send voice message via Telegram.
        
        Args:
            chat_id: Chat ID or username
            voice_url: URL to voice file
            caption: Optional caption
            **kwargs: Additional parameters
            
        Returns:
            MessagingMessage object or None if failed
        """
        try:
            message_data = {
                "chat_id": chat_id,
                "voice": voice_url
            }
            
            if caption:
                message_data["caption"] = caption
            
            message_data.update(kwargs)
            
            # Send voice message
            response = await self._make_request(
                "POST",
                f"{self.api_base}/sendVoice",
                headers={"Content-Type": "application/json"},
                json=message_data
            )
            
            if response["success"] and response["data"]["ok"]:
                result = response["data"]["result"]
                message_id = result["message_id"]
                
                # Create message object
                msg_data = {
                    "id": str(message_id),
                    "chat_id": str(chat_id),
                    "text": caption or "[Voice Message]",
                    "type": "voice",
                    "media_urls": [voice_url]
                }
                
                return MessagingMessage(msg_data, "telegram")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram voice message to {chat_id}: {e}")
            return None
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Telegram webhook.
        
        Args:
            webhook_data: Webhook payload from Telegram
            
        Returns:
            Response data
        """
        try:
            # Process update
            if "message" in webhook_data:
                await self._handle_message_webhook(webhook_data["message"])
            elif "callback_query" in webhook_data:
                await self._handle_callback_query_webhook(webhook_data["callback_query"])
            
            return {"status": "processed"}
            
        except Exception as e:
            self.logger.error(f"Error handling Telegram webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_message_webhook(self, message_data: Dict[str, Any]) -> None:
        """Handle incoming message webhook."""
        try:
            message_id = message_data.get("message_id")
            chat_id = message_data.get("chat", {}).get("id")
            from_user = message_data.get("from", {})
            text = message_data.get("text", "")
            
            # Determine message type
            message_type = "text"
            if "voice" in message_data:
                message_type = "voice"
                text = "[Voice Message]"
            elif "photo" in message_data:
                message_type = "photo"
                text = message_data.get("caption", "[Photo]")
            elif "document" in message_data:
                message_type = "document"
                text = message_data.get("caption", "[Document]")
            
            # Emit message received event
            if self.webhook_publisher:
                await self.webhook_publisher.publish_custom_event(
                    event_type="message.received",
                    data={
                        "message_id": message_id,
                        "platform": "telegram",
                        "chat_id": chat_id,
                        "from_user": from_user.get("username", from_user.get("first_name", "Unknown")),
                        "text": text,
                        "type": message_type
                    },
                    source="telegram_integration"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling Telegram message webhook: {e}")
    
    async def _handle_callback_query_webhook(self, callback_data: Dict[str, Any]) -> None:
        """Handle callback query webhook."""
        try:
            query_id = callback_data.get("id")
            from_user = callback_data.get("from", {})
            data = callback_data.get("data", "")
            
            # Emit callback query event
            if self.webhook_publisher:
                await self.webhook_publisher.publish_custom_event(
                    event_type="callback_query.received",
                    data={
                        "query_id": query_id,
                        "platform": "telegram",
                        "from_user": from_user.get("username", from_user.get("first_name", "Unknown")),
                        "data": data
                    },
                    source="telegram_integration"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling Telegram callback query webhook: {e}")


class SlackIntegration(BaseIntegration):
    """
    Slack App integration.
    
    Provides messaging capabilities through Slack Web API
    with support for channels, direct messages, and interactive components.
    """
    
    def __init__(self, config: SlackConfig):
        """
        Initialize Slack integration.
        
        Args:
            config: Slack configuration
        """
        super().__init__(config)
        self.config: SlackConfig = config
        self.api_base = "https://slack.com/api"
        
        # Webhook publisher
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize Slack integration."""
        try:
            self.logger.info("Initializing Slack integration")
            
            # Validate configuration
            if not self.config.bot_token:
                raise ConfigurationError("Slack Bot Token is required")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Slack integration: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Slack Web API."""
        try:
            # Test authentication
            response = await self._make_request(
                "GET",
                f"{self.api_base}/auth.test",
                headers={"Authorization": f"Bearer {self.config.bot_token}"}
            )
            
            if response["success"] and response["data"]["ok"]:
                auth_info = response["data"]
                self.logger.info(f"Authenticated with Slack team: {auth_info.get('team', 'Unknown')}")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with Slack")
                
        except Exception as e:
            self.logger.error(f"Slack authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Slack integration."""
        try:
            # Check API status
            response = await self._make_request(
                "GET",
                f"{self.api_base}/auth.test",
                headers={"Authorization": f"Bearer {self.config.bot_token}"}
            )
            
            if response["success"] and response["data"]["ok"]:
                self._last_health_check = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Slack health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Slack (cleanup resources)."""
        try:
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during Slack disconnect: {e}")
    
    async def send_message(self, 
                          channel: str,
                          message: str,
                          blocks: Optional[List[Dict]] = None,
                          attachments: Optional[List[Dict]] = None,
                          **kwargs) -> Optional[MessagingMessage]:
        """
        Send Slack message.
        
        Args:
            channel: Channel ID or name
            message: Message text
            blocks: Slack Block Kit blocks
            attachments: Message attachments
            **kwargs: Additional message parameters
            
        Returns:
            MessagingMessage object or None if failed
        """
        try:
            # Prepare message data
            message_data = {
                "channel": channel,
                "text": message
            }
            
            if blocks:
                message_data["blocks"] = blocks
            
            if attachments:
                message_data["attachments"] = attachments
            
            # Additional parameters
            message_data.update(kwargs)
            
            # Send message
            response = await self._make_request(
                "POST",
                f"{self.api_base}/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self.config.bot_token}",
                    "Content-Type": "application/json"
                },
                json=message_data
            )
            
            if response["success"] and response["data"]["ok"]:
                result = response["data"]
                message_ts = result["ts"]
                
                # Create message object
                msg_data = {
                    "id": message_ts,
                    "chat_id": channel,
                    "text": message,
                    "type": "text"
                }
                
                msg = MessagingMessage(msg_data, "slack")
                
                # Emit message sent event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="message.sent",
                        data={
                            "message_ts": message_ts,
                            "platform": "slack",
                            "channel": channel,
                            "text": message
                        },
                        source="slack_integration"
                    )
                
                return msg
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack message to {channel}: {e}")
            return None
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Slack webhook.
        
        Args:
            webhook_data: Webhook payload from Slack
            
        Returns:
            Response data
        """
        try:
            # Handle URL verification challenge
            if webhook_data.get("type") == "url_verification":
                return {"challenge": webhook_data.get("challenge")}
            
            # Handle events
            if webhook_data.get("type") == "event_callback":
                event = webhook_data.get("event", {})
                event_type = event.get("type")
                
                if event_type == "message":
                    await self._handle_message_webhook(event)
                elif event_type == "app_mention":
                    await self._handle_mention_webhook(event)
            
            return {"status": "processed"}
            
        except Exception as e:
            self.logger.error(f"Error handling Slack webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_message_webhook(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming message webhook."""
        try:
            # Skip bot messages
            if event_data.get("bot_id"):
                return
            
            message_ts = event_data.get("ts")
            channel = event_data.get("channel")
            user = event_data.get("user")
            text = event_data.get("text", "")
            
            # Emit message received event
            if self.webhook_publisher:
                await self.webhook_publisher.publish_custom_event(
                    event_type="message.received",
                    data={
                        "message_ts": message_ts,
                        "platform": "slack",
                        "channel": channel,
                        "user": user,
                        "text": text
                    },
                    source="slack_integration"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling Slack message webhook: {e}")
    
    async def _handle_mention_webhook(self, event_data: Dict[str, Any]) -> None:
        """Handle app mention webhook."""
        try:
            message_ts = event_data.get("ts")
            channel = event_data.get("channel")
            user = event_data.get("user")
            text = event_data.get("text", "")
            
            # Emit mention event
            if self.webhook_publisher:
                await self.webhook_publisher.publish_custom_event(
                    event_type="app.mentioned",
                    data={
                        "message_ts": message_ts,
                        "platform": "slack",
                        "channel": channel,
                        "user": user,
                        "text": text
                    },
                    source="slack_integration"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling Slack mention webhook: {e}")
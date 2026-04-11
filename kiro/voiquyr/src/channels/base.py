"""
Channel Adapter Framework — Base Classes

Unified message format, base channel adapter interface, and channel router.
Implements Requirement 17.1.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Channel types
# ---------------------------------------------------------------------------

class ChannelType(Enum):
    VOICE = "voice"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB_CHAT = "web_chat"
    EMAIL = "email"
    FACEBOOK_MESSENGER = "facebook_messenger"
    INSTAGRAM_DM = "instagram_dm"


class MessageDirection(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ContentType(Enum):
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    TEMPLATE = "template"
    QUICK_REPLY = "quick_reply"
    CARD = "card"


# ---------------------------------------------------------------------------
# Unified message format
# ---------------------------------------------------------------------------

@dataclass
class Attachment:
    content_type: ContentType
    url: Optional[str] = None
    data: Optional[bytes] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    size_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type.value,
            "url": self.url,
            "mime_type": self.mime_type,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
        }


@dataclass
class QuickReply:
    title: str
    payload: str
    image_url: Optional[str] = None


@dataclass
class UnifiedMessage:
    """
    Channel-agnostic message format.
    All adapters convert to/from this format.
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: ChannelType = ChannelType.WEB_CHAT
    direction: MessageDirection = MessageDirection.INBOUND
    conversation_id: str = ""
    user_id: str = ""
    text: Optional[str] = None
    attachments: List[Attachment] = field(default_factory=list)
    quick_replies: List[QuickReply] = field(default_factory=list)
    status: MessageStatus = MessageStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Original raw payload from the channel (for debugging)
    raw_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "channel": self.channel.value,
            "direction": self.direction.value,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "text": self.text,
            "attachments": [a.to_dict() for a in self.attachments],
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Base channel adapter
# ---------------------------------------------------------------------------

class ChannelAdapter(ABC):
    """
    Abstract base class for all channel adapters.

    Each adapter handles one channel type and is responsible for:
    - Converting inbound channel-specific payloads → UnifiedMessage
    - Converting UnifiedMessage → channel-specific outbound payload
    - Sending outbound messages
    - Reporting delivery status
    """

    def __init__(self, channel: ChannelType):
        self.channel = channel
        self.logger = logging.getLogger(f"{__name__}.{channel.value}")
        self._message_handlers: List[Callable[[UnifiedMessage], Any]] = []

    @abstractmethod
    async def send(self, message: UnifiedMessage) -> bool:
        """Send an outbound message. Returns True on success."""

    @abstractmethod
    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        """Parse a raw inbound webhook payload into a UnifiedMessage."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the channel is reachable."""

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        """
        Apply channel-specific transformations to an outbound message.
        Override in subclasses for rich formatting, template mapping, etc.
        Default: return text payload.
        """
        return {"text": message.text or ""}

    def add_message_handler(self, handler: Callable[[UnifiedMessage], Any]) -> None:
        self._message_handlers.append(handler)

    async def _dispatch(self, message: UnifiedMessage) -> None:
        for handler in self._message_handlers:
            try:
                await handler(message) if callable(handler) else None
            except Exception as e:
                self.logger.error(f"Message handler error: {e}")

    def get_channel_info(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "adapter": self.__class__.__name__,
        }


# ---------------------------------------------------------------------------
# Channel router
# ---------------------------------------------------------------------------

class ChannelRouter:
    """
    Routes inbound messages to the correct adapter and dispatches outbound
    messages through the appropriate channel.
    """

    def __init__(self):
        self._adapters: Dict[ChannelType, ChannelAdapter] = {}
        self._global_handlers: List[Callable[[UnifiedMessage], Any]] = []
        self.logger = logging.getLogger(__name__)

    def register(self, adapter: ChannelAdapter) -> None:
        self._adapters[adapter.channel] = adapter
        self.logger.info(f"Registered adapter: {adapter.channel.value}")

    def add_global_handler(self, handler: Callable[[UnifiedMessage], Any]) -> None:
        """Handler called for every inbound message regardless of channel."""
        self._global_handlers.append(handler)

    def get_adapter(self, channel: ChannelType) -> Optional[ChannelAdapter]:
        return self._adapters.get(channel)

    async def route_inbound(
        self, channel: ChannelType, raw_payload: Dict[str, Any]
    ) -> Optional[UnifiedMessage]:
        """Parse and dispatch an inbound message from a channel webhook."""
        adapter = self._adapters.get(channel)
        if not adapter:
            self.logger.warning(f"No adapter registered for channel: {channel.value}")
            return None

        message = adapter.parse_inbound(raw_payload)
        if not message:
            return None

        # Dispatch to channel-specific handlers
        await adapter._dispatch(message)

        # Dispatch to global handlers
        for handler in self._global_handlers:
            try:
                result = handler(message)
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                self.logger.error(f"Global handler error: {e}")

        return message

    async def send(self, message: UnifiedMessage) -> bool:
        """Send an outbound message through the appropriate channel adapter."""
        adapter = self._adapters.get(message.channel)
        if not adapter:
            self.logger.error(f"No adapter for channel: {message.channel.value}")
            return False
        return await adapter.send(message)

    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        for channel, adapter in self._adapters.items():
            try:
                results[channel.value] = await adapter.health_check()
            except Exception:
                results[channel.value] = False
        return results

    def registered_channels(self) -> List[ChannelType]:
        return list(self._adapters.keys())

    def get_status(self) -> Dict[str, Any]:
        return {
            "registered_channels": [c.value for c in self._adapters],
            "adapter_count": len(self._adapters),
            "global_handlers": len(self._global_handlers),
        }

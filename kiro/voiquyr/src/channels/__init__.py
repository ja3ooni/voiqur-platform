"""
Omnichannel Communication Platform
"""
from .base import (
    ChannelType, ChannelAdapter, ChannelRouter,
    UnifiedMessage, MessageDirection, MessageStatus,
    ContentType, Attachment, QuickReply,
)
from .messaging import SMSAdapter, WhatsAppAdapter, TelegramAdapter
from .social import FacebookMessengerAdapter, InstagramDMAdapter
from .webchat_email import WebChatAdapter, EmailAdapter
from .context import ContextManager, ConversationContext, UserProfile
from .analytics import OmnichannelAnalytics, ChannelMetrics

__all__ = [
    "ChannelType", "ChannelAdapter", "ChannelRouter",
    "UnifiedMessage", "MessageDirection", "MessageStatus",
    "ContentType", "Attachment", "QuickReply",
    "SMSAdapter", "WhatsAppAdapter", "TelegramAdapter",
    "FacebookMessengerAdapter", "InstagramDMAdapter",
    "WebChatAdapter", "EmailAdapter",
    "ContextManager", "ConversationContext", "UserProfile",
    "OmnichannelAnalytics", "ChannelMetrics",
]

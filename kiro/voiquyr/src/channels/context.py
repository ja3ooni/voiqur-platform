"""
Unified Context Management — cross-channel conversation history,
context preservation on channel switch, user profiles, channel preferences.
Implements Requirements 17.2, 17.3.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ChannelType, UnifiedMessage


@dataclass
class UserProfile:
    user_id: str
    display_name: Optional[str] = None
    preferred_channel: Optional[ChannelType] = None
    channel_ids: Dict[str, str] = field(default_factory=dict)  # channel → channel-specific id
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "preferred_channel": self.preferred_channel.value if self.preferred_channel else None,
            "channel_ids": {k: v for k, v in self.channel_ids.items()},
            "language": self.language,
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class ConversationContext:
    """Full cross-channel conversation state for one user."""
    conversation_id: str
    user_id: str
    messages: List[UnifiedMessage] = field(default_factory=list)
    current_channel: Optional[ChannelType] = None
    channel_history: List[ChannelType] = field(default_factory=list)
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, message: UnifiedMessage) -> None:
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        if message.channel != self.current_channel:
            if self.current_channel:
                self.channel_history.append(self.current_channel)
            self.current_channel = message.channel

    def get_transcript(self, last_n: int = 20) -> List[Dict[str, Any]]:
        return [
            {"role": m.direction.value, "text": m.text, "channel": m.channel.value,
             "timestamp": m.timestamp.isoformat()}
            for m in self.messages[-last_n:]
        ]

    def switched_channel(self) -> bool:
        return len(self.channel_history) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "current_channel": self.current_channel.value if self.current_channel else None,
            "channel_history": [c.value for c in self.channel_history],
            "message_count": len(self.messages),
            "intent": self.intent,
            "entities": self.entities,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ContextManager:
    """
    Stores and retrieves cross-channel conversation context.
    Resolves user identity across channels via channel_id mapping.
    """

    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}   # conversation_id → ctx
        self._user_convs: Dict[str, str] = {}                 # user_id → conversation_id
        self._profiles: Dict[str, UserProfile] = {}           # user_id → profile
        # channel_type:channel_user_id → canonical user_id
        self._channel_id_map: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # User identity resolution
    # ------------------------------------------------------------------

    def register_channel_id(
        self, user_id: str, channel: ChannelType, channel_user_id: str
    ) -> None:
        key = f"{channel.value}:{channel_user_id}"
        self._channel_id_map[key] = user_id
        profile = self._get_or_create_profile(user_id)
        profile.channel_ids[channel.value] = channel_user_id

    def resolve_user_id(
        self, channel: ChannelType, channel_user_id: str
    ) -> str:
        key = f"{channel.value}:{channel_user_id}"
        return self._channel_id_map.get(key, channel_user_id)

    # ------------------------------------------------------------------
    # Context lifecycle
    # ------------------------------------------------------------------

    def get_or_create_context(self, user_id: str) -> ConversationContext:
        conv_id = self._user_convs.get(user_id)
        if conv_id and conv_id in self._contexts:
            return self._contexts[conv_id]
        conv_id = str(uuid.uuid4())
        ctx = ConversationContext(conversation_id=conv_id, user_id=user_id)
        self._contexts[conv_id] = ctx
        self._user_convs[user_id] = conv_id
        return ctx

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        return self._contexts.get(conversation_id)

    def ingest_message(self, message: UnifiedMessage) -> ConversationContext:
        """Resolve user, attach message to context, update profile."""
        user_id = self.resolve_user_id(message.channel, message.user_id)
        ctx = self.get_or_create_context(user_id)
        ctx.add_message(message)
        profile = self._get_or_create_profile(user_id)
        profile.last_seen = datetime.utcnow()
        if not profile.preferred_channel:
            profile.preferred_channel = message.channel
        return ctx

    def update_context(
        self,
        conversation_id: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
    ) -> None:
        ctx = self._contexts.get(conversation_id)
        if not ctx:
            return
        if intent is not None:
            ctx.intent = intent
        if entities is not None:
            ctx.entities.update(entities)
        if summary is not None:
            ctx.summary = summary
        ctx.updated_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # User profiles
    # ------------------------------------------------------------------

    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, **kwargs: Any) -> UserProfile:
        profile = self._get_or_create_profile(user_id)
        for k, v in kwargs.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        return profile

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------

    def get_channel_preferences(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self._profiles.values():
            if p.preferred_channel:
                key = p.preferred_channel.value
                counts[key] = counts.get(key, 0) + 1
        return counts

    def get_cross_channel_users(self) -> List[str]:
        """Users who have used more than one channel."""
        return [
            uid for uid, conv_id in self._user_convs.items()
            if conv_id in self._contexts
            and self._contexts[conv_id].switched_channel()
        ]

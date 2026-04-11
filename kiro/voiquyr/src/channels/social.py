"""
Social Media Adapters — Facebook Messenger & Instagram Direct
Implements Requirements 17.1, 17.3, 17.4.
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from .base import (
    Attachment, ChannelAdapter, ChannelType, ContentType,
    MessageDirection, QuickReply, UnifiedMessage,
)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


class FacebookMessengerAdapter(ChannelAdapter):
    """
    Facebook Messenger adapter via Graph API Send API.
    Supports text, quick replies, generic card templates, and media attachments.
    """

    def __init__(self, page_access_token: str, verify_token: str = ""):
        super().__init__(ChannelType.FACEBOOK_MESSENGER)
        self.page_access_token = page_access_token
        self.verify_token = verify_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            session = await self._get_session()
            payload = self.transform_for_channel(message)
            payload["recipient"] = {"id": message.user_id}
            async with session.post(
                f"{GRAPH_BASE}/me/messages",
                params={"access_token": self.page_access_token},
                json=payload,
            ) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"Messenger send failed: {e}")
            return False

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        # Card template
        if message.metadata.get("cards"):
            cards = message.metadata["cards"]
            return {
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "elements": [
                                {
                                    "title": c.get("title", ""),
                                    "subtitle": c.get("subtitle", ""),
                                    "image_url": c.get("image_url"),
                                    "buttons": c.get("buttons", []),
                                }
                                for c in cards[:10]
                            ],
                        },
                    }
                }
            }
        # Media attachment
        if message.attachments:
            att = message.attachments[0]
            type_map = {
                ContentType.IMAGE: "image",
                ContentType.AUDIO: "audio",
                ContentType.VIDEO: "video",
                ContentType.FILE: "file",
            }
            fb_type = type_map.get(att.content_type, "file")
            return {
                "message": {
                    "attachment": {
                        "type": fb_type,
                        "payload": {"url": att.url, "is_reusable": True},
                    }
                }
            }
        # Quick replies
        if message.quick_replies:
            return {
                "message": {
                    "text": message.text or "",
                    "quick_replies": [
                        {
                            "content_type": "text",
                            "title": qr.title,
                            "payload": qr.payload,
                            **({"image_url": qr.image_url} if qr.image_url else {}),
                        }
                        for qr in message.quick_replies[:13]
                    ],
                }
            }
        return {"message": {"text": message.text or ""}}

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        try:
            entry = raw.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]
            sender_id = messaging.get("sender", {}).get("id", "")
            msg = messaging.get("message", {})
            postback = messaging.get("postback")

            text = msg.get("text") or (postback.get("payload") if postback else None)
            attachments = []

            for att in msg.get("attachments", []):
                ct_map = {"image": ContentType.IMAGE, "audio": ContentType.AUDIO,
                          "video": ContentType.VIDEO, "file": ContentType.FILE}
                ct = ct_map.get(att.get("type", ""), ContentType.FILE)
                attachments.append(Attachment(
                    content_type=ct,
                    url=att.get("payload", {}).get("url"),
                ))

            if not text and not attachments:
                return None

            return UnifiedMessage(
                channel=ChannelType.FACEBOOK_MESSENGER,
                direction=MessageDirection.INBOUND,
                conversation_id=sender_id,
                user_id=sender_id,
                text=text,
                attachments=attachments,
                raw_payload=raw,
            )
        except Exception as e:
            self.logger.warning(f"Messenger parse failed: {e}")
            return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{GRAPH_BASE}/me",
                params={"access_token": self.page_access_token},
            ) as resp:
                return resp.status == 200
        except Exception:
            return False


class InstagramDMAdapter(ChannelAdapter):
    """
    Instagram Direct Messages adapter via Graph API.
    Shares the same Send API as Messenger but uses IG-scoped user IDs.
    """

    def __init__(self, page_access_token: str, ig_account_id: str):
        super().__init__(ChannelType.INSTAGRAM_DM)
        self.page_access_token = page_access_token
        self.ig_account_id = ig_account_id
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            session = await self._get_session()
            payload = self.transform_for_channel(message)
            payload["recipient"] = {"id": message.user_id}
            async with session.post(
                f"{GRAPH_BASE}/{self.ig_account_id}/messages",
                params={"access_token": self.page_access_token},
                json=payload,
            ) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"Instagram DM send failed: {e}")
            return False

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        # Instagram supports text and image attachments; no generic templates
        if message.attachments:
            att = message.attachments[0]
            if att.content_type == ContentType.IMAGE:
                return {
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": att.url},
                        }
                    }
                }
        return {"message": {"text": message.text or ""}}

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        try:
            entry = raw.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]
            sender_id = messaging.get("sender", {}).get("id", "")
            msg = messaging.get("message", {})
            text = msg.get("text")
            attachments = []

            for att in msg.get("attachments", []):
                if att.get("type") == "image":
                    attachments.append(Attachment(
                        content_type=ContentType.IMAGE,
                        url=att.get("payload", {}).get("url"),
                    ))

            if not text and not attachments:
                return None

            return UnifiedMessage(
                channel=ChannelType.INSTAGRAM_DM,
                direction=MessageDirection.INBOUND,
                conversation_id=sender_id,
                user_id=sender_id,
                text=text,
                attachments=attachments,
                raw_payload=raw,
            )
        except Exception as e:
            self.logger.warning(f"Instagram parse failed: {e}")
            return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{GRAPH_BASE}/{self.ig_account_id}",
                params={"access_token": self.page_access_token, "fields": "id"},
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

"""
Messaging Channel Adapters — SMS (Twilio/Vonage/Plivo), WhatsApp, Telegram
Implements Requirement 17.1, 17.2.
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from .base import (
    Attachment, ChannelAdapter, ChannelType, ContentType,
    MessageDirection, MessageStatus, QuickReply, UnifiedMessage,
)


# ---------------------------------------------------------------------------
# SMS — multi-provider (Twilio / Vonage / Plivo)
# ---------------------------------------------------------------------------

class SMSAdapter(ChannelAdapter):
    """
    SMS adapter supporting Twilio, Vonage, and Plivo.
    Provider is selected via `provider` config key.
    """

    PROVIDERS = ("twilio", "vonage", "plivo")

    def __init__(
        self,
        provider: str,
        account_sid: str,
        auth_token: str,
        from_number: str,
        **kwargs: Any,
    ):
        super().__init__(ChannelType.SMS)
        assert provider in self.PROVIDERS, f"Unknown SMS provider: {provider}"
        self.provider = provider
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            if self.provider == "twilio":
                return await self._send_twilio(message)
            elif self.provider == "vonage":
                return await self._send_vonage(message)
            else:
                return await self._send_plivo(message)
        except Exception as e:
            self.logger.error(f"SMS send failed ({self.provider}): {e}")
            return False

    async def _send_twilio(self, message: UnifiedMessage) -> bool:
        session = await self._get_session()
        async with session.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json",
            auth=aiohttp.BasicAuth(self.account_sid, self.auth_token),
            data={"From": self.from_number, "To": message.user_id, "Body": message.text or ""},
        ) as resp:
            return resp.status in (200, 201)

    async def _send_vonage(self, message: UnifiedMessage) -> bool:
        session = await self._get_session()
        async with session.post(
            "https://rest.nexmo.com/sms/json",
            json={
                "api_key": self.account_sid,
                "api_secret": self.auth_token,
                "from": self.from_number,
                "to": message.user_id,
                "text": message.text or "",
            },
        ) as resp:
            return resp.status == 200

    async def _send_plivo(self, message: UnifiedMessage) -> bool:
        session = await self._get_session()
        async with session.post(
            f"https://api.plivo.com/v1/Account/{self.account_sid}/Message/",
            auth=aiohttp.BasicAuth(self.account_sid, self.auth_token),
            json={"src": self.from_number, "dst": message.user_id, "text": message.text or ""},
        ) as resp:
            return resp.status in (200, 202)

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        # Twilio: From, Body; Vonage: msisdn, text; Plivo: From, Text
        text = raw.get("Body") or raw.get("text") or raw.get("Text")
        user_id = raw.get("From") or raw.get("msisdn") or ""
        if not text:
            return None
        return UnifiedMessage(
            channel=ChannelType.SMS,
            direction=MessageDirection.INBOUND,
            conversation_id=user_id,
            user_id=user_id,
            text=text,
            raw_payload=raw,
        )

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        # SMS: plain text only, strip rich content
        return {"text": (message.text or "")[:160]}

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            if self.provider == "twilio":
                async with session.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json",
                    auth=aiohttp.BasicAuth(self.account_sid, self.auth_token),
                ) as resp:
                    return resp.status == 200
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# WhatsApp Business API
# ---------------------------------------------------------------------------

class WhatsAppAdapter(ChannelAdapter):
    def __init__(self, access_token: str, phone_number_id: str):
        super().__init__(ChannelType.WHATSAPP)
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self._base = f"https://graph.facebook.com/v19.0/{phone_number_id}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        return self._session

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            session = await self._get_session()
            payload: Dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": message.user_id,
            }
            if message.quick_replies:
                payload["type"] = "interactive"
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message.text or ""},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": qr.payload, "title": qr.title}}
                            for qr in message.quick_replies[:3]
                        ]
                    },
                }
            elif message.attachments:
                att = message.attachments[0]
                payload["type"] = att.content_type.value
                payload[att.content_type.value] = {"link": att.url}
            else:
                payload["type"] = "text"
                payload["text"] = {"body": message.text or "", "preview_url": False}

            async with session.post(f"{self._base}/messages", json=payload) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            self.logger.error(f"WhatsApp send failed: {e}")
            return False

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        try:
            entry = raw.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0].get("value", {})
            msg = change.get("messages", [{}])[0]
            user_id = msg.get("from", "")
            msg_type = msg.get("type", "text")
            text = None
            attachments = []

            if msg_type == "text":
                text = msg.get("text", {}).get("body")
            elif msg_type in ("image", "audio", "video", "document"):
                media = msg.get(msg_type, {})
                ct_map = {"image": ContentType.IMAGE, "audio": ContentType.AUDIO,
                          "video": ContentType.VIDEO, "document": ContentType.FILE}
                attachments.append(Attachment(
                    content_type=ct_map.get(msg_type, ContentType.FILE),
                    url=media.get("url"),
                    mime_type=media.get("mime_type"),
                ))
            elif msg_type == "interactive":
                text = msg.get("interactive", {}).get("button_reply", {}).get("title")

            if not text and not attachments:
                return None

            return UnifiedMessage(
                channel=ChannelType.WHATSAPP,
                direction=MessageDirection.INBOUND,
                conversation_id=user_id,
                user_id=user_id,
                text=text,
                attachments=attachments,
                raw_payload=raw,
            )
        except Exception as e:
            self.logger.warning(f"WhatsApp parse failed: {e}")
            return None

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        if message.quick_replies:
            return {
                "type": "interactive",
                "buttons": [{"id": qr.payload, "title": qr.title} for qr in message.quick_replies[:3]],
            }
        return {"type": "text", "body": message.text or ""}

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self._base}?fields=id") as resp:
                return resp.status == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Telegram Bot API
# ---------------------------------------------------------------------------

class TelegramAdapter(ChannelAdapter):
    def __init__(self, bot_token: str):
        super().__init__(ChannelType.TELEGRAM)
        self.bot_token = bot_token
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            session = await self._get_session()
            chat_id = message.user_id

            if message.attachments:
                att = message.attachments[0]
                if att.content_type == ContentType.IMAGE:
                    endpoint, key = "sendPhoto", "photo"
                elif att.content_type == ContentType.AUDIO:
                    endpoint, key = "sendAudio", "audio"
                else:
                    endpoint, key = "sendDocument", "document"
                async with session.post(
                    f"{self._base}/{endpoint}",
                    json={"chat_id": chat_id, key: att.url, "caption": message.text or ""},
                ) as resp:
                    return resp.status == 200

            if message.quick_replies:
                keyboard = {
                    "keyboard": [[{"text": qr.title}] for qr in message.quick_replies],
                    "one_time_keyboard": True,
                    "resize_keyboard": True,
                }
                async with session.post(
                    f"{self._base}/sendMessage",
                    json={"chat_id": chat_id, "text": message.text or "", "reply_markup": keyboard},
                ) as resp:
                    return resp.status == 200

            async with session.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": message.text or "", "parse_mode": "HTML"},
            ) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")
            return False

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        try:
            update = raw.get("message") or raw.get("callback_query", {}).get("message", {})
            if not update:
                return None
            chat_id = str(update.get("chat", {}).get("id", ""))
            text = update.get("text") or raw.get("callback_query", {}).get("data")
            attachments = []

            if not text:
                for media_type, ct in [
                    ("photo", ContentType.IMAGE),
                    ("audio", ContentType.AUDIO),
                    ("video", ContentType.VIDEO),
                    ("document", ContentType.FILE),
                ]:
                    if media_type in update:
                        item = update[media_type]
                        if isinstance(item, list):
                            item = item[-1]
                        attachments.append(Attachment(
                            content_type=ct,
                            metadata={"file_id": item.get("file_id", "")},
                        ))
                        break

            if not text and not attachments:
                return None

            return UnifiedMessage(
                channel=ChannelType.TELEGRAM,
                direction=MessageDirection.INBOUND,
                conversation_id=chat_id,
                user_id=chat_id,
                text=text,
                attachments=attachments,
                raw_payload=raw,
            )
        except Exception as e:
            self.logger.warning(f"Telegram parse failed: {e}")
            return None

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        result: Dict[str, Any] = {"text": message.text or "", "parse_mode": "HTML"}
        if message.quick_replies:
            result["reply_markup"] = {
                "keyboard": [[{"text": qr.title}] for qr in message.quick_replies],
                "one_time_keyboard": True,
            }
        return result

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self._base}/getMe") as resp:
                return resp.status == 200
        except Exception:
            return False

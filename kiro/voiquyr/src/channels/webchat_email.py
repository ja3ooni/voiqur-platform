"""
Web Chat and Email Adapters
Implements Requirements 17.1, 17.4, 17.6.
"""

import asyncio
import email as email_lib
import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from .base import (
    Attachment, ChannelAdapter, ChannelType, ContentType,
    MessageDirection, MessageStatus, QuickReply, UnifiedMessage,
)


# ---------------------------------------------------------------------------
# Web Chat adapter (server-side; JS widget is in webchat_widget.js)
# ---------------------------------------------------------------------------

class WebChatAdapter(ChannelAdapter):
    """
    Server-side web chat adapter.
    Receives messages from the embeddable JS widget via WebSocket/HTTP.
    Supports typing indicators and presence tracking.
    """

    def __init__(self):
        super().__init__(ChannelType.WEB_CHAT)
        # session_id → asyncio.Queue for outbound messages
        self._sessions: Dict[str, asyncio.Queue] = {}
        self._typing: Dict[str, bool] = {}   # session_id → is_typing

    def create_session(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._sessions[session_id] = q
        return q

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._typing.pop(session_id, None)

    def set_typing(self, session_id: str, is_typing: bool) -> None:
        self._typing[session_id] = is_typing

    def is_typing(self, session_id: str) -> bool:
        return self._typing.get(session_id, False)

    async def send(self, message: UnifiedMessage) -> bool:
        q = self._sessions.get(message.conversation_id)
        if q is None:
            self.logger.warning(f"No web chat session: {message.conversation_id}")
            return False
        await q.put(message.to_dict())
        return True

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        text = raw.get("text")
        session_id = raw.get("session_id", "")
        if not text and not raw.get("attachments"):
            return None
        attachments = [
            Attachment(
                content_type=ContentType[a.get("type", "FILE").upper()],
                url=a.get("url"),
                filename=a.get("filename"),
            )
            for a in raw.get("attachments", [])
        ]
        return UnifiedMessage(
            channel=ChannelType.WEB_CHAT,
            direction=MessageDirection.INBOUND,
            conversation_id=session_id,
            user_id=raw.get("user_id", session_id),
            text=text,
            attachments=attachments,
            raw_payload=raw,
        )

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        result: Dict[str, Any] = {"text": message.text or ""}
        if message.quick_replies:
            result["quick_replies"] = [
                {"title": qr.title, "payload": qr.payload} for qr in message.quick_replies
            ]
        if message.attachments:
            result["attachments"] = [a.to_dict() for a in message.attachments]
        return result

    async def health_check(self) -> bool:
        return True

    def get_active_sessions(self) -> List[str]:
        return list(self._sessions.keys())


# ---------------------------------------------------------------------------
# Email adapter (SMTP send / IMAP-style inbound parsing)
# ---------------------------------------------------------------------------

class EmailAdapter(ChannelAdapter):
    """
    Email adapter using SMTP for outbound and raw MIME parsing for inbound.
    Generates HTML-formatted emails with plain-text fallback.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True,
    ):
        super().__init__(ChannelType.EMAIL)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls

    async def send(self, message: UnifiedMessage) -> bool:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_sync, message)
        except Exception as e:
            self.logger.error(f"Email send failed: {e}")
            return False

    def _send_sync(self, message: UnifiedMessage) -> bool:
        subject = message.metadata.get("subject", "Message from VoiQyr")
        to_addr = message.user_id

        mime = MIMEMultipart("alternative")
        mime["Subject"] = subject
        mime["From"] = self.from_address
        mime["To"] = to_addr

        plain = message.text or ""
        html = self._render_html(message)

        mime.attach(MIMEText(plain, "plain", "utf-8"))
        mime.attach(MIMEText(html, "html", "utf-8"))

        if self.use_tls:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
                smtp.login(self.username, self.password)
                smtp.sendmail(self.from_address, to_addr, mime.as_string())
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.sendmail(self.from_address, to_addr, mime.as_string())
        return True

    def _render_html(self, message: UnifiedMessage) -> str:
        body = f"<p>{message.text or ''}</p>"
        if message.quick_replies:
            buttons = "".join(
                f'<a href="#" style="margin:4px;padding:8px 16px;background:#0084ff;'
                f'color:#fff;border-radius:4px;text-decoration:none">{qr.title}</a>'
                for qr in message.quick_replies
            )
            body += f"<div>{buttons}</div>"
        if message.attachments:
            for att in message.attachments:
                if att.content_type == ContentType.IMAGE and att.url:
                    body += f'<img src="{att.url}" style="max-width:100%"/>'
        return (
            f"<!DOCTYPE html><html><body style='font-family:sans-serif'>"
            f"{body}</body></html>"
        )

    def parse_inbound(self, raw: Dict[str, Any]) -> Optional[UnifiedMessage]:
        """
        Parse an inbound email. `raw` can be:
        - A dict with 'from', 'subject', 'text', 'html' keys (webhook format)
        - A dict with 'raw_mime' key (raw MIME string)
        """
        if "raw_mime" in raw:
            return self._parse_mime(raw["raw_mime"])

        from_addr = raw.get("from", "")
        text = raw.get("text") or raw.get("subject", "")
        if not text:
            return None
        return UnifiedMessage(
            channel=ChannelType.EMAIL,
            direction=MessageDirection.INBOUND,
            conversation_id=from_addr,
            user_id=from_addr,
            text=text,
            metadata={"subject": raw.get("subject", ""), "html": raw.get("html", "")},
            raw_payload=raw,
        )

    def _parse_mime(self, raw_mime: str) -> Optional[UnifiedMessage]:
        try:
            msg = email_lib.message_from_string(raw_mime)
            from_addr = msg.get("From", "")
            subject = msg.get("Subject", "")
            text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                text = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            return UnifiedMessage(
                channel=ChannelType.EMAIL,
                direction=MessageDirection.INBOUND,
                conversation_id=from_addr,
                user_id=from_addr,
                text=text,
                metadata={"subject": subject},
            )
        except Exception as e:
            self.logger.warning(f"MIME parse failed: {e}")
            return None

    def transform_for_channel(self, message: UnifiedMessage) -> Dict[str, Any]:
        return {
            "subject": message.metadata.get("subject", "Message from VoiQyr"),
            "text": message.text or "",
            "html": self._render_html(message),
        }

    async def health_check(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._smtp_ping)
        except Exception:
            return False

    def _smtp_ping(self) -> bool:
        try:
            if self.use_tls:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=5):
                    return True
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5):
                    return True
        except Exception:
            return False

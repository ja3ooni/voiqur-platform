"""
Omnichannel Tests (Task 17.7)
Tests for all channel adapters, context preservation, cross-channel flows,
and message delivery.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.channels import (
    ChannelType, ChannelRouter, UnifiedMessage, MessageDirection,
    ContentType, Attachment, QuickReply,
    SMSAdapter, WhatsAppAdapter, TelegramAdapter,
    FacebookMessengerAdapter, InstagramDMAdapter,
    WebChatAdapter, EmailAdapter,
    ContextManager, ConversationContext,
    OmnichannelAnalytics,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _mock_http_ok(adapter, method="post"):
    resp = AsyncMock()
    resp.status = 200
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    getattr(session, method).return_value = cm
    adapter._get_session = AsyncMock(return_value=session)
    return session


def _msg(channel: ChannelType, text: str = "Hello", user_id: str = "u1") -> UnifiedMessage:
    return UnifiedMessage(
        channel=channel, direction=MessageDirection.OUTBOUND,
        user_id=user_id, conversation_id=user_id, text=text,
    )


# ---------------------------------------------------------------------------
# 17.2 SMS Adapter
# ---------------------------------------------------------------------------

class TestSMSAdapter:
    @pytest.mark.asyncio
    async def test_send_twilio(self):
        adapter = SMSAdapter("twilio", "AC123", "token", "+1555")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.SMS, user_id="+1999")) is True

    @pytest.mark.asyncio
    async def test_send_vonage(self):
        adapter = SMSAdapter("vonage", "key", "secret", "VoiQyr")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.SMS)) is True

    @pytest.mark.asyncio
    async def test_send_plivo(self):
        adapter = SMSAdapter("plivo", "AUTH", "token", "+1555")
        resp = AsyncMock(); resp.status = 202
        cm = AsyncMock(); cm.__aenter__ = AsyncMock(return_value=resp); cm.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock(); session.post.return_value = cm
        adapter._get_session = AsyncMock(return_value=session)
        assert await adapter.send(_msg(ChannelType.SMS)) is True

    def test_parse_twilio(self):
        adapter = SMSAdapter("twilio", "AC", "t", "+1")
        msg = adapter.parse_inbound({"From": "+1999", "Body": "Hi"})
        assert msg is not None
        assert msg.text == "Hi"
        assert msg.user_id == "+1999"

    def test_parse_vonage(self):
        adapter = SMSAdapter("vonage", "k", "s", "V")
        msg = adapter.parse_inbound({"msisdn": "+44123", "text": "Hey"})
        assert msg is not None
        assert msg.text == "Hey"

    def test_parse_empty_returns_none(self):
        adapter = SMSAdapter("twilio", "AC", "t", "+1")
        assert adapter.parse_inbound({"From": "+1"}) is None

    def test_transform_truncates_to_160(self):
        adapter = SMSAdapter("twilio", "AC", "t", "+1")
        msg = _msg(ChannelType.SMS, text="x" * 200)
        result = adapter.transform_for_channel(msg)
        assert len(result["text"]) == 160

    def test_invalid_provider_raises(self):
        with pytest.raises(AssertionError):
            SMSAdapter("unknown", "k", "s", "+1")


# ---------------------------------------------------------------------------
# 17.2 WhatsApp Adapter
# ---------------------------------------------------------------------------

class TestWhatsAppAdapter:
    @pytest.mark.asyncio
    async def test_send_text(self):
        adapter = WhatsAppAdapter("token", "phone123")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.WHATSAPP)) is True

    @pytest.mark.asyncio
    async def test_send_quick_replies(self):
        adapter = WhatsAppAdapter("token", "phone123")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.WHATSAPP, user_id="u1",
            text="Choose:", quick_replies=[QuickReply("Yes", "yes"), QuickReply("No", "no")],
        )
        assert await adapter.send(msg) is True

    @pytest.mark.asyncio
    async def test_send_image(self):
        adapter = WhatsAppAdapter("token", "phone123")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.WHATSAPP, user_id="u1",
            attachments=[Attachment(ContentType.IMAGE, url="https://img.example.com/a.jpg")],
        )
        assert await adapter.send(msg) is True

    def test_parse_text(self):
        adapter = WhatsAppAdapter("t", "p")
        raw = {"entry": [{"changes": [{"value": {"messages": [
            {"from": "+1234", "type": "text", "text": {"body": "Hello WA"}}
        ]}}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "Hello WA"

    def test_parse_image(self):
        adapter = WhatsAppAdapter("t", "p")
        raw = {"entry": [{"changes": [{"value": {"messages": [
            {"from": "+1234", "type": "image", "image": {"url": "https://img.example.com/x.jpg", "mime_type": "image/jpeg"}}
        ]}}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.attachments[0].content_type == ContentType.IMAGE

    def test_parse_empty_returns_none(self):
        adapter = WhatsAppAdapter("t", "p")
        assert adapter.parse_inbound({}) is None

    def test_transform_quick_replies(self):
        adapter = WhatsAppAdapter("t", "p")
        msg = UnifiedMessage(text="Pick:", quick_replies=[QuickReply("A", "a")])
        result = adapter.transform_for_channel(msg)
        assert result["type"] == "interactive"


# ---------------------------------------------------------------------------
# 17.2 Telegram Adapter
# ---------------------------------------------------------------------------

class TestTelegramAdapter:
    @pytest.mark.asyncio
    async def test_send_text(self):
        adapter = TelegramAdapter("bot_token")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.TELEGRAM, user_id="123456")) is True

    @pytest.mark.asyncio
    async def test_send_with_keyboard(self):
        adapter = TelegramAdapter("bot_token")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.TELEGRAM, user_id="123",
            text="Choose:", quick_replies=[QuickReply("Option A", "a")],
        )
        assert await adapter.send(msg) is True

    @pytest.mark.asyncio
    async def test_send_photo(self):
        adapter = TelegramAdapter("bot_token")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.TELEGRAM, user_id="123",
            attachments=[Attachment(ContentType.IMAGE, url="https://img.example.com/p.jpg")],
        )
        assert await adapter.send(msg) is True

    def test_parse_text(self):
        adapter = TelegramAdapter("t")
        raw = {"message": {"chat": {"id": 999}, "text": "Hello TG"}}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "Hello TG"
        assert msg.user_id == "999"

    def test_parse_callback_query(self):
        adapter = TelegramAdapter("t")
        raw = {"callback_query": {"data": "yes", "message": {"chat": {"id": 42}}}}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "yes"

    def test_parse_empty_returns_none(self):
        adapter = TelegramAdapter("t")
        assert adapter.parse_inbound({}) is None

    def test_transform_with_keyboard(self):
        adapter = TelegramAdapter("t")
        msg = UnifiedMessage(text="Hi", quick_replies=[QuickReply("Yes", "yes")])
        result = adapter.transform_for_channel(msg)
        assert "reply_markup" in result


# ---------------------------------------------------------------------------
# 17.3 Social Media Adapters
# ---------------------------------------------------------------------------

class TestFacebookMessengerAdapter:
    @pytest.mark.asyncio
    async def test_send_text(self):
        adapter = FacebookMessengerAdapter("page_token")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.FACEBOOK_MESSENGER)) is True

    @pytest.mark.asyncio
    async def test_send_quick_replies(self):
        adapter = FacebookMessengerAdapter("page_token")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.FACEBOOK_MESSENGER, user_id="u1",
            text="Pick:", quick_replies=[QuickReply("A", "a"), QuickReply("B", "b")],
        )
        assert await adapter.send(msg) is True

    @pytest.mark.asyncio
    async def test_send_card_template(self):
        adapter = FacebookMessengerAdapter("page_token")
        _mock_http_ok(adapter, "post")
        msg = UnifiedMessage(
            channel=ChannelType.FACEBOOK_MESSENGER, user_id="u1",
            metadata={"cards": [{"title": "Card 1", "subtitle": "Sub", "buttons": []}]},
        )
        assert await adapter.send(msg) is True

    def test_parse_text(self):
        adapter = FacebookMessengerAdapter("t")
        raw = {"entry": [{"messaging": [{"sender": {"id": "u1"}, "message": {"text": "Hi FB"}}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "Hi FB"

    def test_parse_postback(self):
        adapter = FacebookMessengerAdapter("t")
        raw = {"entry": [{"messaging": [{"sender": {"id": "u1"}, "postback": {"payload": "GET_STARTED"}, "message": {}}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "GET_STARTED"

    def test_parse_attachment(self):
        adapter = FacebookMessengerAdapter("t")
        raw = {"entry": [{"messaging": [{"sender": {"id": "u1"}, "message": {
            "attachments": [{"type": "image", "payload": {"url": "https://img.example.com/x.jpg"}}]
        }}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.attachments[0].content_type == ContentType.IMAGE

    def test_transform_card(self):
        adapter = FacebookMessengerAdapter("t")
        msg = UnifiedMessage(metadata={"cards": [{"title": "T"}]})
        result = adapter.transform_for_channel(msg)
        assert result["message"]["attachment"]["payload"]["template_type"] == "generic"


class TestInstagramDMAdapter:
    @pytest.mark.asyncio
    async def test_send_text(self):
        adapter = InstagramDMAdapter("token", "ig123")
        _mock_http_ok(adapter, "post")
        assert await adapter.send(_msg(ChannelType.INSTAGRAM_DM)) is True

    def test_parse_text(self):
        adapter = InstagramDMAdapter("t", "ig")
        raw = {"entry": [{"messaging": [{"sender": {"id": "ig_u1"}, "message": {"text": "Hi IG"}}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.text == "Hi IG"

    def test_parse_image(self):
        adapter = InstagramDMAdapter("t", "ig")
        raw = {"entry": [{"messaging": [{"sender": {"id": "u1"}, "message": {
            "attachments": [{"type": "image", "payload": {"url": "https://img.example.com/ig.jpg"}}]
        }}]}]}
        msg = adapter.parse_inbound(raw)
        assert msg is not None
        assert msg.attachments[0].content_type == ContentType.IMAGE

    def test_transform_image(self):
        adapter = InstagramDMAdapter("t", "ig")
        msg = UnifiedMessage(attachments=[Attachment(ContentType.IMAGE, url="https://img.example.com/x.jpg")])
        result = adapter.transform_for_channel(msg)
        assert result["message"]["attachment"]["type"] == "image"


# ---------------------------------------------------------------------------
# 17.4 Web Chat & Email Adapters
# ---------------------------------------------------------------------------

class TestWebChatAdapter:
    @pytest.mark.asyncio
    async def test_send_to_session(self):
        adapter = WebChatAdapter()
        q = adapter.create_session("sess-1")
        msg = UnifiedMessage(channel=ChannelType.WEB_CHAT, conversation_id="sess-1", text="Hi")
        assert await adapter.send(msg) is True
        item = await q.get()
        assert item["text"] == "Hi"

    @pytest.mark.asyncio
    async def test_send_no_session_returns_false(self):
        adapter = WebChatAdapter()
        msg = UnifiedMessage(channel=ChannelType.WEB_CHAT, conversation_id="missing", text="Hi")
        assert await adapter.send(msg) is False

    def test_typing_indicator(self):
        adapter = WebChatAdapter()
        adapter.create_session("s1")
        adapter.set_typing("s1", True)
        assert adapter.is_typing("s1") is True
        adapter.set_typing("s1", False)
        assert adapter.is_typing("s1") is False

    def test_parse_inbound(self):
        adapter = WebChatAdapter()
        msg = adapter.parse_inbound({"session_id": "s1", "user_id": "u1", "text": "Hello web"})
        assert msg is not None
        assert msg.text == "Hello web"

    def test_parse_empty_returns_none(self):
        adapter = WebChatAdapter()
        assert adapter.parse_inbound({"session_id": "s1"}) is None

    def test_close_session(self):
        adapter = WebChatAdapter()
        adapter.create_session("s1")
        adapter.close_session("s1")
        assert "s1" not in adapter.get_active_sessions()

    def test_transform_with_quick_replies(self):
        adapter = WebChatAdapter()
        msg = UnifiedMessage(text="Pick:", quick_replies=[QuickReply("A", "a")])
        result = adapter.transform_for_channel(msg)
        assert "quick_replies" in result


class TestEmailAdapter:
    def _make_adapter(self):
        return EmailAdapter("smtp.example.com", 465, "user", "pass", "noreply@example.com")

    def test_parse_dict_inbound(self):
        adapter = self._make_adapter()
        msg = adapter.parse_inbound({"from": "user@example.com", "subject": "Hello", "text": "Body"})
        assert msg is not None
        assert msg.text == "Body"
        assert msg.user_id == "user@example.com"

    def test_parse_mime_inbound(self):
        adapter = self._make_adapter()
        raw_mime = (
            "From: sender@example.com\r\n"
            "Subject: Test\r\n"
            "Content-Type: text/plain\r\n\r\n"
            "Hello from MIME"
        )
        msg = adapter.parse_inbound({"raw_mime": raw_mime})
        assert msg is not None
        assert "Hello from MIME" in msg.text

    def test_parse_empty_returns_none(self):
        adapter = self._make_adapter()
        assert adapter.parse_inbound({"from": "x@x.com"}) is None

    def test_render_html_with_quick_replies(self):
        adapter = self._make_adapter()
        msg = UnifiedMessage(text="Choose:", quick_replies=[QuickReply("Yes", "yes")])
        html = adapter._render_html(msg)
        assert "Yes" in html
        assert "<a href" in html

    def test_render_html_with_image(self):
        adapter = self._make_adapter()
        msg = UnifiedMessage(
            text="See:",
            attachments=[Attachment(ContentType.IMAGE, url="https://img.example.com/x.jpg")],
        )
        html = adapter._render_html(msg)
        assert "<img" in html

    def test_transform_for_channel(self):
        adapter = self._make_adapter()
        msg = UnifiedMessage(text="Hi", metadata={"subject": "Greetings"})
        result = adapter.transform_for_channel(msg)
        assert result["subject"] == "Greetings"
        assert "html" in result


# ---------------------------------------------------------------------------
# 17.5 Context Management
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_get_or_create_context(self):
        ctx_mgr = ContextManager()
        ctx = ctx_mgr.get_or_create_context("user-1")
        assert ctx.user_id == "user-1"
        # Same user → same context
        ctx2 = ctx_mgr.get_or_create_context("user-1")
        assert ctx.conversation_id == ctx2.conversation_id

    def test_ingest_message(self):
        ctx_mgr = ContextManager()
        msg = UnifiedMessage(channel=ChannelType.SMS, user_id="u1", text="Hi")
        ctx = ctx_mgr.ingest_message(msg)
        assert len(ctx.messages) == 1
        assert ctx.current_channel == ChannelType.SMS

    def test_channel_switch_tracked(self):
        ctx_mgr = ContextManager()
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1", text="SMS"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.WEB_CHAT, user_id="u1", text="Web"))
        ctx = ctx_mgr.get_or_create_context("u1")
        assert ctx.switched_channel() is True
        assert ChannelType.SMS in ctx.channel_history

    def test_register_and_resolve_channel_id(self):
        ctx_mgr = ContextManager()
        ctx_mgr.register_channel_id("canonical-user", ChannelType.TELEGRAM, "tg-12345")
        resolved = ctx_mgr.resolve_user_id(ChannelType.TELEGRAM, "tg-12345")
        assert resolved == "canonical-user"

    def test_resolve_unknown_returns_original(self):
        ctx_mgr = ContextManager()
        assert ctx_mgr.resolve_user_id(ChannelType.SMS, "+1999") == "+1999"

    def test_update_context(self):
        ctx_mgr = ContextManager()
        ctx = ctx_mgr.get_or_create_context("u1")
        ctx_mgr.update_context(ctx.conversation_id, intent="book_appointment", entities={"date": "tomorrow"})
        assert ctx.intent == "book_appointment"
        assert ctx.entities["date"] == "tomorrow"

    def test_update_profile(self):
        ctx_mgr = ContextManager()
        ctx_mgr.get_or_create_context("u1")
        ctx_mgr.update_profile("u1", display_name="Alice", language="fr")
        profile = ctx_mgr.get_profile("u1")
        assert profile.display_name == "Alice"
        assert profile.language == "fr"

    def test_get_transcript(self):
        ctx_mgr = ContextManager()
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1", text="Msg 1"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1", text="Msg 2"))
        ctx = ctx_mgr.get_or_create_context("u1")
        transcript = ctx.get_transcript()
        assert len(transcript) == 2

    def test_channel_preferences(self):
        ctx_mgr = ContextManager()
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.WHATSAPP, user_id="u1", text="Hi"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u2", text="Hi"))
        prefs = ctx_mgr.get_channel_preferences()
        assert "whatsapp" in prefs or "sms" in prefs

    def test_cross_channel_users(self):
        ctx_mgr = ContextManager()
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1", text="A"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.WEB_CHAT, user_id="u1", text="B"))
        assert "u1" in ctx_mgr.get_cross_channel_users()


# ---------------------------------------------------------------------------
# 17.6 Analytics
# ---------------------------------------------------------------------------

class TestOmnichannelAnalytics:
    def _setup(self):
        ctx_mgr = ContextManager()
        analytics = OmnichannelAnalytics(ctx_mgr)
        # Simulate 3 messages across 2 channels for user u1
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1",
                                               direction=MessageDirection.INBOUND, text="Hi"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.SMS, user_id="u1",
                                               direction=MessageDirection.OUTBOUND, text="Hello"))
        ctx_mgr.ingest_message(UnifiedMessage(channel=ChannelType.WEB_CHAT, user_id="u1",
                                               direction=MessageDirection.INBOUND, text="Switch"))
        return analytics, ctx_mgr

    def test_channel_metrics(self):
        analytics, _ = self._setup()
        metrics = analytics.get_channel_metrics()
        channels = {m.channel for m in metrics}
        assert ChannelType.SMS in channels
        assert ChannelType.WEB_CHAT in channels

    def test_sms_inbound_outbound_counts(self):
        analytics, _ = self._setup()
        sms = next(m for m in analytics.get_channel_metrics() if m.channel == ChannelType.SMS)
        assert sms.inbound == 1
        assert sms.outbound == 1

    def test_customer_journeys(self):
        analytics, _ = self._setup()
        journeys = analytics.get_customer_journeys()
        assert len(journeys) == 1
        assert journeys[0]["channel_switches"] == 1

    def test_cross_channel_attribution(self):
        analytics, _ = self._setup()
        attr = analytics.get_cross_channel_attribution()
        assert "sms" in attr  # conversation started on SMS

    def test_dashboard_structure(self):
        analytics, _ = self._setup()
        dashboard = analytics.get_dashboard()
        assert "total_conversations" in dashboard
        assert "channel_metrics" in dashboard
        assert "cross_channel_users" in dashboard
        assert "generated_at" in dashboard

    def test_response_time_recording(self):
        analytics, _ = self._setup()
        analytics.record_response_time(ChannelType.SMS, 1.5)
        analytics.record_response_time(ChannelType.SMS, 2.5)
        metrics = analytics.get_channel_metrics()
        sms = next(m for m in metrics if m.channel == ChannelType.SMS)
        assert sms.avg_response_time_s == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 17.7 Cross-channel flow integration test
# ---------------------------------------------------------------------------

class TestCrossChannelFlow:
    @pytest.mark.asyncio
    async def test_full_cross_channel_flow(self):
        """User starts on SMS, switches to web chat — context preserved."""
        router = ChannelRouter()
        ctx_mgr = ContextManager()

        # Register adapters
        sms = SMSAdapter("twilio", "AC", "token", "+1555")
        web = WebChatAdapter()
        router.register(sms)
        router.register(web)

        # Wire context manager as global handler
        router.add_global_handler(lambda m: ctx_mgr.ingest_message(m))

        # Step 1: inbound SMS
        await router.route_inbound(ChannelType.SMS, {"From": "+1999", "Body": "Book appointment"})

        # Step 2: switch to web chat
        web.create_session("sess-abc")
        await router.route_inbound(ChannelType.WEB_CHAT, {"session_id": "sess-abc", "user_id": "+1999", "text": "Continue here"})

        ctx = ctx_mgr.get_or_create_context("+1999")
        assert len(ctx.messages) == 2
        assert ctx.switched_channel() is True
        assert ctx.channel_history[0] == ChannelType.SMS
        assert ctx.current_channel == ChannelType.WEB_CHAT

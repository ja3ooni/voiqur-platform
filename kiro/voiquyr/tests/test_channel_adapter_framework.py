"""
Tests for Channel Adapter Framework (Task 17.1)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.channels import (
    ChannelType, ChannelAdapter, ChannelRouter,
    UnifiedMessage, MessageDirection, MessageStatus,
    ContentType, Attachment, QuickReply,
)


# ---------------------------------------------------------------------------
# Concrete test adapter
# ---------------------------------------------------------------------------

class MockAdapter(ChannelAdapter):
    def __init__(self, channel: ChannelType, healthy: bool = True):
        super().__init__(channel)
        self._healthy = healthy
        self.sent: list = []

    async def send(self, message: UnifiedMessage) -> bool:
        self.sent.append(message)
        return True

    def parse_inbound(self, raw: dict):
        text = raw.get("text")
        if not text:
            return None
        return UnifiedMessage(
            channel=self.channel,
            direction=MessageDirection.INBOUND,
            conversation_id=raw.get("conversation_id", "conv-1"),
            user_id=raw.get("user_id", "user-1"),
            text=text,
            raw_payload=raw,
        )

    async def health_check(self) -> bool:
        return self._healthy

    def transform_for_channel(self, message: UnifiedMessage) -> dict:
        return {"body": message.text, "channel": self.channel.value}


# ---------------------------------------------------------------------------
# UnifiedMessage tests
# ---------------------------------------------------------------------------

class TestUnifiedMessage:
    def test_defaults(self):
        msg = UnifiedMessage()
        assert msg.message_id is not None
        assert msg.status == MessageStatus.PENDING
        assert msg.attachments == []
        assert msg.quick_replies == []

    def test_to_dict(self):
        msg = UnifiedMessage(
            channel=ChannelType.SMS,
            text="Hello",
            user_id="u1",
            conversation_id="c1",
        )
        d = msg.to_dict()
        assert d["channel"] == "sms"
        assert d["text"] == "Hello"
        assert d["user_id"] == "u1"

    def test_with_attachment(self):
        att = Attachment(content_type=ContentType.IMAGE, url="https://example.com/img.png")
        msg = UnifiedMessage(text="See image", attachments=[att])
        d = msg.to_dict()
        assert len(d["attachments"]) == 1
        assert d["attachments"][0]["content_type"] == "image"

    def test_with_quick_replies(self):
        msg = UnifiedMessage(
            text="Choose:",
            quick_replies=[QuickReply("Yes", "yes"), QuickReply("No", "no")],
        )
        assert len(msg.quick_replies) == 2


# ---------------------------------------------------------------------------
# ChannelAdapter tests
# ---------------------------------------------------------------------------

class TestChannelAdapter:
    def test_channel_info(self):
        adapter = MockAdapter(ChannelType.WHATSAPP)
        info = adapter.get_channel_info()
        assert info["channel"] == "whatsapp"
        assert info["adapter"] == "MockAdapter"

    def test_parse_inbound_valid(self):
        adapter = MockAdapter(ChannelType.SMS)
        msg = adapter.parse_inbound({"text": "Hi", "user_id": "u1"})
        assert msg is not None
        assert msg.text == "Hi"
        assert msg.channel == ChannelType.SMS
        assert msg.direction == MessageDirection.INBOUND

    def test_parse_inbound_invalid_returns_none(self):
        adapter = MockAdapter(ChannelType.SMS)
        msg = adapter.parse_inbound({"no_text": True})
        assert msg is None

    @pytest.mark.asyncio
    async def test_send(self):
        adapter = MockAdapter(ChannelType.TELEGRAM)
        msg = UnifiedMessage(channel=ChannelType.TELEGRAM, text="Hello")
        result = await adapter.send(msg)
        assert result is True
        assert len(adapter.sent) == 1

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        adapter = MockAdapter(ChannelType.WEB_CHAT, healthy=True)
        assert await adapter.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        adapter = MockAdapter(ChannelType.WEB_CHAT, healthy=False)
        assert await adapter.health_check() is False

    def test_transform_for_channel(self):
        adapter = MockAdapter(ChannelType.FACEBOOK_MESSENGER)
        msg = UnifiedMessage(text="Hi there")
        result = adapter.transform_for_channel(msg)
        assert result["body"] == "Hi there"
        assert result["channel"] == "facebook_messenger"

    @pytest.mark.asyncio
    async def test_message_handler_called(self):
        adapter = MockAdapter(ChannelType.SMS)
        received = []
        adapter.add_message_handler(lambda m: received.append(m))
        msg = UnifiedMessage(channel=ChannelType.SMS, text="test")
        await adapter._dispatch(msg)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_async_message_handler(self):
        adapter = MockAdapter(ChannelType.SMS)
        received = []

        async def async_handler(m):
            received.append(m)

        adapter.add_message_handler(async_handler)
        msg = UnifiedMessage(channel=ChannelType.SMS, text="async test")
        await adapter._dispatch(msg)
        assert len(received) == 1


# ---------------------------------------------------------------------------
# ChannelRouter tests
# ---------------------------------------------------------------------------

class TestChannelRouter:
    def test_register_adapter(self):
        router = ChannelRouter()
        adapter = MockAdapter(ChannelType.SMS)
        router.register(adapter)
        assert ChannelType.SMS in router.registered_channels()

    def test_get_adapter(self):
        router = ChannelRouter()
        adapter = MockAdapter(ChannelType.WHATSAPP)
        router.register(adapter)
        assert router.get_adapter(ChannelType.WHATSAPP) is adapter

    def test_get_adapter_unregistered(self):
        router = ChannelRouter()
        assert router.get_adapter(ChannelType.EMAIL) is None

    @pytest.mark.asyncio
    async def test_route_inbound_dispatches(self):
        router = ChannelRouter()
        adapter = MockAdapter(ChannelType.TELEGRAM)
        router.register(adapter)

        received = []
        adapter.add_message_handler(lambda m: received.append(m))

        msg = await router.route_inbound(
            ChannelType.TELEGRAM, {"text": "Hello", "user_id": "u1"}
        )
        assert msg is not None
        assert msg.text == "Hello"
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_route_inbound_no_adapter(self):
        router = ChannelRouter()
        msg = await router.route_inbound(ChannelType.EMAIL, {"text": "Hi"})
        assert msg is None

    @pytest.mark.asyncio
    async def test_route_inbound_invalid_payload(self):
        router = ChannelRouter()
        router.register(MockAdapter(ChannelType.SMS))
        msg = await router.route_inbound(ChannelType.SMS, {"no_text": True})
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_routes_to_correct_adapter(self):
        router = ChannelRouter()
        sms = MockAdapter(ChannelType.SMS)
        wa = MockAdapter(ChannelType.WHATSAPP)
        router.register(sms)
        router.register(wa)

        msg = UnifiedMessage(channel=ChannelType.WHATSAPP, text="Hi WA")
        await router.send(msg)

        assert len(wa.sent) == 1
        assert len(sms.sent) == 0

    @pytest.mark.asyncio
    async def test_send_no_adapter_returns_false(self):
        router = ChannelRouter()
        msg = UnifiedMessage(channel=ChannelType.EMAIL, text="Hi")
        result = await router.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_global_handler_called_for_all_channels(self):
        router = ChannelRouter()
        router.register(MockAdapter(ChannelType.SMS))
        router.register(MockAdapter(ChannelType.TELEGRAM))

        received = []
        router.add_global_handler(lambda m: received.append(m.channel))

        await router.route_inbound(ChannelType.SMS, {"text": "sms msg"})
        await router.route_inbound(ChannelType.TELEGRAM, {"text": "tg msg"})

        assert ChannelType.SMS in received
        assert ChannelType.TELEGRAM in received

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        router = ChannelRouter()
        router.register(MockAdapter(ChannelType.SMS, healthy=True))
        router.register(MockAdapter(ChannelType.WHATSAPP, healthy=False))

        results = await router.health_check_all()
        assert results["sms"] is True
        assert results["whatsapp"] is False

    def test_status(self):
        router = ChannelRouter()
        router.register(MockAdapter(ChannelType.SMS))
        router.register(MockAdapter(ChannelType.TELEGRAM))
        status = router.get_status()
        assert status["adapter_count"] == 2
        assert "sms" in status["registered_channels"]

    def test_multiple_adapters_registered(self):
        router = ChannelRouter()
        for ch in ChannelType:
            router.register(MockAdapter(ch))
        assert len(router.registered_channels()) == len(ChannelType)

    @pytest.mark.asyncio
    async def test_global_async_handler(self):
        router = ChannelRouter()
        router.register(MockAdapter(ChannelType.SMS))
        received = []

        async def async_handler(m):
            received.append(m)

        router.add_global_handler(async_handler)
        await router.route_inbound(ChannelType.SMS, {"text": "test"})
        assert len(received) == 1

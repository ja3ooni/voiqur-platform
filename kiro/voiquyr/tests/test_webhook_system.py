"""
Test Webhook System

Simple test to verify the webhook registration and notification system works correctly.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.api.models.webhooks import (
    WebhookRegistration, WebhookEvent, WebhookEventType, WebhookFilter,
    RetryPolicy, WebhookSecurity, WebhookStatus
)
from src.api.services.webhook_service import WebhookService
from src.api.utils.webhook_publisher import WebhookEventPublisher


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.webhooks = {}
        self.events = {}
        self.deliveries = {}
    
    async def execute(self, query, *args):
        """Mock execute method."""
        if "INSERT INTO webhooks" in query:
            webhook_id = args[0]
            self.webhooks[webhook_id] = {
                "id": args[0],
                "user_id": args[1],
                "name": args[2],
                "status": "active"
            }
        return "INSERT 0 1"
    
    async def fetchrow(self, query, *args):
        """Mock fetchrow method."""
        if "SELECT * FROM webhooks WHERE id" in query:
            webhook_id = args[0]
            return self.webhooks.get(webhook_id)
        return None
    
    async def fetch(self, query, *args):
        """Mock fetch method."""
        return []
    
    async def fetchval(self, query, *args):
        """Mock fetchval method."""
        return 0


class MockRedis:
    """Mock Redis for testing."""
    
    def __init__(self):
        self.data = {}
    
    def lpush(self, key, value):
        """Mock lpush method."""
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)
    
    def close(self):
        """Mock close method."""
        pass


async def create_webhook_service():
    """Create a webhook service for testing."""
    service = WebhookService(
        postgres_url="mock://localhost",
        redis_url="mock://localhost",
        max_concurrent_deliveries=10,
        delivery_timeout=5
    )
    
    # Mock the database connections
    mock_db = MockDatabase()
    mock_pool = MagicMock()
    # pg_pool.acquire() is used as `async with pool.acquire() as conn:`
    # asyncpg returns an async context manager directly from acquire()
    mock_acquire_ctx = AsyncMock()
    mock_acquire_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_pool.acquire = MagicMock(return_value=mock_acquire_ctx)
    service.pg_pool = mock_pool
    service.redis_client = MockRedis()
    
    return service


async def test_webhook_registration():
    """Test webhook registration."""
    webhook_service = await create_webhook_service()
    
    # Create a webhook registration
    webhook = WebhookRegistration(
        user_id="test_user",
        name="Test Webhook",
        description="Test webhook for unit testing",
        url="https://example.com/webhook",
        filters=WebhookFilter(
            event_types=[WebhookEventType.TRANSCRIPTION_COMPLETED]
        ),
        retry_policy=RetryPolicy(),
        security=WebhookSecurity()
    )
    
    # Register the webhook
    webhook_id = await webhook_service.register_webhook(webhook)
    
    # Verify registration
    assert webhook_id == webhook.id
    print("✓ Webhook registration test passed")


async def test_event_publishing():
    """Test event publishing."""
    webhook_service = await create_webhook_service()
    
    # Create a test event
    event = WebhookEvent(
        event_type=WebhookEventType.TRANSCRIPTION_COMPLETED,
        data={
            "request_id": "test_request",
            "text": "Hello world",
            "confidence": 0.95,
            "language": "en"
        },
        user_id="test_user",
        source="test_agent"
    )
    
    # Publish the event
    await webhook_service.publish_event(event)
    
    # Verify event was queued
    redis_data = webhook_service.redis_client.data
    assert "webhook_events" in redis_data
    assert len(redis_data["webhook_events"]) > 0
    print("✓ Event publishing test passed")


async def test_webhook_publisher():
    """Test webhook event publisher."""
    
    # Create mock webhook service
    mock_service = AsyncMock()
    
    # Create publisher
    publisher = WebhookEventPublisher(mock_service)
    
    # Test conversation started event
    await publisher.publish_conversation_started(
        conversation_id="conv_123",
        user_id="user_456",
        language="en"
    )
    
    # Verify service was called
    mock_service.publish_event.assert_called_once()
    
    # Get the published event
    published_event = mock_service.publish_event.call_args[0][0]
    assert published_event.event_type == WebhookEventType.CONVERSATION_STARTED
    assert published_event.user_id == "user_456"
    assert published_event.data["conversation_id"] == "conv_123"


async def test_transcription_event_publishing():
    """Test transcription event publishing."""
    
    mock_service = AsyncMock()
    publisher = WebhookEventPublisher(mock_service)
    
    # Test transcription completed event
    await publisher.publish_transcription_completed(
        request_id="req_789",
        text="This is a test transcription",
        confidence=0.98,
        language="en",
        processing_time_ms=150.5,
        user_id="user_123",
        conversation_id="conv_456"
    )
    
    # Verify event was published
    mock_service.publish_event.assert_called_once()
    
    published_event = mock_service.publish_event.call_args[0][0]
    assert published_event.event_type == WebhookEventType.TRANSCRIPTION_COMPLETED
    assert published_event.data["text"] == "This is a test transcription"
    assert published_event.data["confidence"] == 0.98
    assert published_event.data["processing_time_ms"] == 150.5


async def test_error_event_publishing():
    """Test error event publishing."""
    
    mock_service = AsyncMock()
    publisher = WebhookEventPublisher(mock_service)
    
    # Test error event
    await publisher.publish_error_occurred(
        error_code="STT_MODEL_ERROR",
        error_message="Model inference failed",
        component="stt_agent",
        severity="high",
        user_id="user_123"
    )
    
    # Verify event was published
    mock_service.publish_event.assert_called_once()
    
    published_event = mock_service.publish_event.call_args[0][0]
    assert published_event.event_type == WebhookEventType.ERROR_OCCURRED
    assert published_event.data["error_code"] == "STT_MODEL_ERROR"
    assert published_event.data["severity"] == "high"


def test_webhook_models():
    """Test webhook model validation."""
    
    # Test valid webhook registration
    webhook = WebhookRegistration(
        user_id="test_user",
        name="Test Webhook",
        url="https://example.com/webhook",
        filters=WebhookFilter(
            event_types=[WebhookEventType.CONVERSATION_STARTED]
        )
    )
    
    assert webhook.user_id == "test_user"
    assert webhook.status == WebhookStatus.ACTIVE
    assert len(webhook.filters.event_types) == 1
    
    # Test webhook event
    event = WebhookEvent(
        event_type=WebhookEventType.SYNTHESIS_COMPLETED,
        data={"test": "data"},
        source="test_source"
    )
    
    assert event.event_type == WebhookEventType.SYNTHESIS_COMPLETED
    assert event.data == {"test": "data"}
    assert isinstance(event.timestamp, datetime)


if __name__ == "__main__":
    # Run a simple integration test
    async def integration_test():
        """Simple integration test."""
        print("Testing webhook system...")
        
        # Test webhook models
        test_webhook_models()
        print("✓ Webhook models validation passed")
        
        # Run individual tests
        await test_webhook_registration()
        await test_event_publishing()
        await test_webhook_publisher()
        await test_transcription_event_publishing()
        await test_error_event_publishing()
        
        print("All webhook system tests passed! ✅")
    
    asyncio.run(integration_test())
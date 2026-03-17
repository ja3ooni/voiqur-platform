"""
Webhooks Router

Webhook registration and management endpoints with event-driven notifications,
delivery guarantees, and comprehensive monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..auth import AuthManager, User
from ..models.webhooks import (
    WebhookRegistration, WebhookRegistrationRequest, WebhookRegistrationResponse,
    WebhookUpdateRequest, WebhookListResponse, WebhookDeliveryListResponse,
    WebhookTestRequest, WebhookTestResponse, WebhookEventType, WebhookStatus,
    WebhookFilter, RetryPolicy, WebhookSecurity, WebhookEvent
)
from ..services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize webhook service (will be injected via dependency)
webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Dependency to get webhook service instance."""
    if webhook_service is None:
        raise HTTPException(status_code=503, detail="Webhook service not available")
    return webhook_service


def set_webhook_service(service: WebhookService) -> None:
    """Set the webhook service instance."""
    global webhook_service
    webhook_service = service


# Webhook Registration and Management

@router.post("/", response_model=WebhookRegistrationResponse)
async def register_webhook(
    request: WebhookRegistrationRequest,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Register a new webhook endpoint.
    
    Creates a webhook subscription for specified event types with customizable
    filtering, retry policies, and security settings.
    """
    try:
        # Create webhook registration
        webhook = WebhookRegistration(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            url=request.url,
            method=request.method,
            filters=WebhookFilter(
                event_types=request.event_types,
                conditions=request.filters
            ),
            retry_policy=request.retry_policy or RetryPolicy(),
            security=request.security or WebhookSecurity()
        )
        
        # Register webhook
        webhook_id = await service.register_webhook(webhook)
        
        return WebhookRegistrationResponse(
            webhook_id=webhook_id,
            status=WebhookStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to register webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register webhook: {str(e)}")


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    List all webhooks for the current user.
    
    Returns paginated list of webhook registrations with their current status
    and delivery statistics.
    """
    try:
        webhooks, total = await service.list_webhooks(
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        return WebhookListResponse(
            webhooks=webhooks,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list webhooks: {str(e)}")


@router.get("/{webhook_id}", response_model=WebhookRegistration)
async def get_webhook(
    webhook_id: str,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Get webhook details by ID.
    
    Returns complete webhook configuration including filters, retry policy,
    and delivery statistics.
    """
    try:
        webhook = await service.get_webhook(webhook_id, current_user.id)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get webhook: {str(e)}")


@router.put("/{webhook_id}", response_model=WebhookRegistration)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Update webhook configuration.
    
    Allows updating webhook URL, event filters, retry policy, and security settings.
    Changes take effect immediately for new events.
    """
    try:
        # Prepare update data
        updates = {}
        
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.url is not None:
            updates["url"] = str(request.url)
        if request.status is not None:
            updates["status"] = request.status.value
        
        if request.event_types is not None:
            updates["filters"] = WebhookFilter(
                event_types=request.event_types,
                conditions=request.filters
            ).dict()
        
        if request.retry_policy is not None:
            updates["retry_policy"] = request.retry_policy.dict()
        
        if request.security is not None:
            updates["security"] = request.security.dict()
        
        # Update webhook
        success = await service.update_webhook(webhook_id, current_user.id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Return updated webhook
        webhook = await service.get_webhook(webhook_id, current_user.id)
        return webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update webhook: {str(e)}")


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Delete a webhook.
    
    Removes webhook registration and stops all future event deliveries.
    Existing delivery attempts will continue until completion.
    """
    try:
        success = await service.delete_webhook(webhook_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return {"message": "Webhook deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete webhook: {str(e)}")


# Webhook Testing

@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    request: WebhookTestRequest,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Test webhook delivery.
    
    Sends a test event to the webhook endpoint to verify configuration
    and connectivity. Returns delivery status and response details.
    """
    try:
        delivery = await service.test_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id,
            event_type=request.event_type,
            test_data=request.test_data
        )
        
        if not delivery:
            raise HTTPException(status_code=404, detail="Webhook not found or test failed")
        
        return WebhookTestResponse(
            delivery_id=delivery.id,
            status=delivery.status,
            response_status=delivery.response_status,
            response_time_ms=delivery.duration_ms,
            error_message=delivery.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test webhook: {str(e)}")


# Delivery History and Monitoring

@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def get_delivery_history(
    webhook_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Get webhook delivery history.
    
    Returns paginated list of delivery attempts with status, response details,
    and retry information.
    """
    try:
        deliveries, total = await service.get_delivery_history(
            webhook_id=webhook_id,
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        return WebhookDeliveryListResponse(
            deliveries=deliveries,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to get delivery history for webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get delivery history: {str(e)}")


@router.get("/{webhook_id}/stats")
async def get_webhook_stats(
    webhook_id: str,
    days: int = Query(7, ge=1, le=90, description="Number of days for statistics"),
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Get webhook delivery statistics.
    
    Returns delivery success rates, average latency, error breakdown,
    and other performance metrics for the specified time period.
    """
    try:
        stats = await service.get_webhook_stats(
            webhook_id=webhook_id,
            user_id=current_user.id,
            days=days
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get webhook stats for {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get webhook stats: {str(e)}")


# Event Publishing (Internal API)

@router.post("/events/publish")
async def publish_event(
    event: WebhookEvent,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Publish an event to matching webhooks.
    
    Internal API endpoint for publishing events from voice processing agents.
    Events are processed asynchronously and delivered to all matching webhooks.
    """
    try:
        # Add event publishing to background tasks for async processing
        background_tasks.add_task(service.publish_event, event)
        
        return {
            "event_id": event.id,
            "status": "queued",
            "message": "Event queued for delivery to matching webhooks"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish event {event.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {str(e)}")


# System Information and Health

@router.get("/system/info")
async def get_webhook_system_info():
    """
    Get webhook system information and capabilities.
    
    Returns supported event types, configuration options, and system limits.
    """
    return {
        "service": "EUVoice AI Webhook System",
        "version": "1.0.0",
        "supported_events": [event.value for event in WebhookEventType],
        "features": {
            "event_filtering": {
                "description": "Filter events by type, user, conversation, language, and custom conditions",
                "supported_filters": [
                    "event_types", "user_ids", "conversation_ids", 
                    "languages", "agent_types", "custom_conditions"
                ]
            },
            "retry_policy": {
                "description": "Configurable retry policy with exponential backoff",
                "max_attempts": 10,
                "max_delay_seconds": 3600,
                "supported_backoff": "exponential"
            },
            "security": {
                "description": "HMAC signature verification and IP filtering",
                "features": ["hmac_sha256", "custom_headers", "ip_filtering", "ssl_verification"]
            },
            "delivery_guarantees": {
                "description": "At-least-once delivery with comprehensive retry logic",
                "features": ["retry_with_backoff", "delivery_tracking", "failure_analysis"]
            }
        },
        "limits": {
            "max_webhooks_per_user": 50,
            "max_concurrent_deliveries": 100,
            "delivery_timeout_seconds": 30,
            "max_retry_attempts": 10,
            "max_payload_size_bytes": 1048576  # 1MB
        },
        "compliance": {
            "gdpr": True,
            "data_residency": "EU/EEA only",
            "audit_logging": True,
            "encryption": "TLS 1.3"
        }
    }


@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(AuthManager(None).get_current_user),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Get webhook system statistics.
    
    Returns overall system performance metrics, delivery statistics,
    and health indicators. Requires authentication.
    """
    try:
        stats = service.get_service_stats()
        
        return {
            "system_status": "healthy" if stats["is_running"] else "unhealthy",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


# Event Type Information

@router.get("/events/types")
async def get_event_types():
    """
    Get supported webhook event types.
    
    Returns list of all supported event types with descriptions
    and example payloads.
    """
    event_info = {
        # Conversation events
        WebhookEventType.CONVERSATION_STARTED: {
            "description": "Triggered when a new conversation session begins",
            "example_data": {
                "conversation_id": "conv_123",
                "user_id": "user_456",
                "language": "en",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        },
        WebhookEventType.CONVERSATION_ENDED: {
            "description": "Triggered when a conversation session ends",
            "example_data": {
                "conversation_id": "conv_123",
                "duration_seconds": 120,
                "message_count": 5,
                "end_reason": "user_ended"
            }
        },
        
        # Processing events
        WebhookEventType.TRANSCRIPTION_COMPLETED: {
            "description": "Triggered when speech-to-text processing completes",
            "example_data": {
                "request_id": "req_789",
                "text": "Hello, how can I help you?",
                "confidence": 0.95,
                "language": "en",
                "processing_time_ms": 150
            }
        },
        WebhookEventType.SYNTHESIS_COMPLETED: {
            "description": "Triggered when text-to-speech synthesis completes",
            "example_data": {
                "request_id": "req_890",
                "text": "Thank you for your question.",
                "voice_id": "voice_123",
                "duration_seconds": 2.5,
                "processing_time_ms": 800
            }
        },
        
        # System events
        WebhookEventType.ERROR_OCCURRED: {
            "description": "Triggered when a system error occurs",
            "example_data": {
                "error_code": "STT_MODEL_ERROR",
                "error_message": "Model inference failed",
                "component": "stt_agent",
                "severity": "high"
            }
        }
    }
    
    return {
        "event_types": [
            {
                "type": event_type.value,
                "category": event_type.value.split('.')[0],
                "description": event_info.get(event_type, {}).get("description", ""),
                "example_data": event_info.get(event_type, {}).get("example_data", {})
            }
            for event_type in WebhookEventType
        ],
        "categories": {
            "conversation": "Events related to conversation lifecycle",
            "transcription": "Events from speech-to-text processing",
            "synthesis": "Events from text-to-speech processing",
            "pipeline": "Events from complete voice processing pipeline",
            "batch": "Events from batch processing operations",
            "agent": "Events from individual agents",
            "system": "System-level events and alerts",
            "user": "User account and management events"
        }
    }
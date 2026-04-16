"""
Webhook Models and Data Structures

Defines webhook registration, event types, and delivery tracking models
for the EUVoice AI Platform webhook system.
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    
    # Conversation events
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    CONVERSATION_UPDATED = "conversation.updated"
    
    # Processing events
    TRANSCRIPTION_STARTED = "transcription.started"
    TRANSCRIPTION_COMPLETED = "transcription.completed"
    TRANSCRIPTION_FAILED = "transcription.failed"
    
    SYNTHESIS_STARTED = "synthesis.started"
    SYNTHESIS_COMPLETED = "synthesis.completed"
    SYNTHESIS_FAILED = "synthesis.failed"
    
    # Pipeline events
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    
    # Batch processing events
    BATCH_STARTED = "batch.started"
    BATCH_COMPLETED = "batch.completed"
    BATCH_FAILED = "batch.failed"
    BATCH_PROGRESS = "batch.progress"
    
    # System events
    AGENT_STATUS_CHANGED = "agent.status_changed"
    SYSTEM_ALERT = "system.alert"
    ERROR_OCCURRED = "error.occurred"
    
    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Telephony events
    CALL_STARTED = "call.started"
    CALL_ENDED = "call.ended"
    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"
    SMS_SENT = "sms.sent"
    SMS_RECEIVED = "sms.received"
    
    # CRM events
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    
    # Messaging events
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"


class WebhookStatus(str, Enum):
    """Webhook registration status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class RetryPolicy(BaseModel):
    """Webhook retry policy configuration."""
    
    max_attempts: int = Field(default=5, ge=1, le=10, description="Maximum retry attempts")
    initial_delay: int = Field(default=1, ge=1, le=300, description="Initial delay in seconds")
    max_delay: int = Field(default=300, ge=1, le=3600, description="Maximum delay in seconds")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0, description="Backoff multiplier")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")
    
    @validator('max_delay')
    def validate_max_delay(cls, v, values):
        if 'initial_delay' in values and v < values['initial_delay']:
            raise ValueError('max_delay must be >= initial_delay')
        return v


class WebhookFilter(BaseModel):
    """Webhook event filtering configuration."""
    
    event_types: List[WebhookEventType] = Field(description="Event types to subscribe to")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Additional filtering conditions")
    
    # User-specific filters
    user_ids: Optional[List[str]] = Field(default=None, description="Filter by specific user IDs")
    
    # Conversation-specific filters
    conversation_ids: Optional[List[str]] = Field(default=None, description="Filter by conversation IDs")
    
    # Language filters
    languages: Optional[List[str]] = Field(default=None, description="Filter by languages")
    
    # Agent filters
    agent_types: Optional[List[str]] = Field(default=None, description="Filter by agent types")


class WebhookSecurity(BaseModel):
    """Webhook security configuration."""
    
    secret_token: Optional[str] = Field(default=None, description="Secret token for HMAC verification")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    allowed_ips: Optional[List[str]] = Field(default=None, description="Allowed IP addresses")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers to include")


class WebhookRegistration(BaseModel):
    """Webhook registration model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique webhook ID")
    user_id: str = Field(description="User ID who registered the webhook")
    name: str = Field(description="Human-readable webhook name")
    description: Optional[str] = Field(default=None, description="Webhook description")
    
    # Endpoint configuration
    url: HttpUrl = Field(description="Webhook endpoint URL")
    method: str = Field(default="POST", pattern="^(POST|PUT|PATCH)$", description="HTTP method")
    
    # Event configuration
    filters: WebhookFilter = Field(description="Event filtering configuration")
    
    # Delivery configuration
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="Retry policy")
    security: WebhookSecurity = Field(default_factory=WebhookSecurity, description="Security settings")
    
    # Status and metadata
    status: WebhookStatus = Field(default=WebhookStatus.ACTIVE, description="Webhook status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_delivery_at: Optional[datetime] = Field(default=None, description="Last successful delivery")
    
    # Statistics
    total_deliveries: int = Field(default=0, description="Total delivery attempts")
    successful_deliveries: int = Field(default=0, description="Successful deliveries")
    failed_deliveries: int = Field(default=0, description="Failed deliveries")
    
    # EU compliance
    data_residency: str = Field(default="eu", description="Data residency requirement")
    gdpr_compliant: bool = Field(default=True, description="GDPR compliance flag")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str
        }


class WebhookEvent(BaseModel):
    """Webhook event payload model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: WebhookEventType = Field(description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    # Event data
    data: Dict[str, Any] = Field(description="Event-specific data")
    
    # Context information
    user_id: Optional[str] = Field(default=None, description="Associated user ID")
    conversation_id: Optional[str] = Field(default=None, description="Associated conversation ID")
    request_id: Optional[str] = Field(default=None, description="Associated request ID")
    
    # Metadata
    source: str = Field(description="Event source (agent/service)")
    version: str = Field(default="1.0", description="Event schema version")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookDelivery(BaseModel):
    """Webhook delivery tracking model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique delivery ID")
    webhook_id: str = Field(description="Associated webhook ID")
    event_id: str = Field(description="Associated event ID")
    
    # Delivery details
    url: str = Field(description="Delivery URL")
    method: str = Field(description="HTTP method used")
    headers: Dict[str, str] = Field(description="Request headers")
    payload: str = Field(description="Request payload (JSON)")
    
    # Status and timing
    status: DeliveryStatus = Field(description="Delivery status")
    attempt_number: int = Field(description="Attempt number (1-based)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    attempted_at: Optional[datetime] = Field(default=None, description="Attempt timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    next_retry_at: Optional[datetime] = Field(default=None, description="Next retry timestamp")
    
    # Response details
    response_status: Optional[int] = Field(default=None, description="HTTP response status")
    response_headers: Optional[Dict[str, str]] = Field(default=None, description="Response headers")
    response_body: Optional[str] = Field(default=None, description="Response body")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    
    # Performance metrics
    duration_ms: Optional[int] = Field(default=None, description="Request duration in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookDeliveryStats(BaseModel):
    """Webhook delivery statistics."""
    
    webhook_id: str = Field(description="Webhook ID")
    period_start: datetime = Field(description="Statistics period start")
    period_end: datetime = Field(description="Statistics period end")
    
    # Delivery counts
    total_events: int = Field(description="Total events generated")
    total_deliveries: int = Field(description="Total delivery attempts")
    successful_deliveries: int = Field(description="Successful deliveries")
    failed_deliveries: int = Field(description="Failed deliveries")
    
    # Performance metrics
    average_latency_ms: float = Field(description="Average delivery latency")
    success_rate: float = Field(description="Success rate (0.0-1.0)")
    
    # Error breakdown
    error_breakdown: Dict[str, int] = Field(description="Error counts by type")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request/Response Models for API

class WebhookRegistrationRequest(BaseModel):
    """Request model for webhook registration."""
    
    name: str = Field(description="Webhook name")
    description: Optional[str] = Field(default=None, description="Webhook description")
    url: HttpUrl = Field(description="Webhook endpoint URL")
    method: str = Field(default="POST", pattern="^(POST|PUT|PATCH)$")
    
    # Event configuration
    event_types: List[WebhookEventType] = Field(description="Event types to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")
    
    # Optional configurations
    retry_policy: Optional[RetryPolicy] = Field(default=None, description="Custom retry policy")
    security: Optional[WebhookSecurity] = Field(default=None, description="Security settings")


class WebhookRegistrationResponse(BaseModel):
    """Response model for webhook registration."""
    
    webhook_id: str = Field(description="Created webhook ID")
    status: WebhookStatus = Field(description="Webhook status")
    created_at: datetime = Field(description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookUpdateRequest(BaseModel):
    """Request model for webhook updates."""
    
    name: Optional[str] = Field(default=None, description="Updated name")
    description: Optional[str] = Field(default=None, description="Updated description")
    url: Optional[HttpUrl] = Field(default=None, description="Updated URL")
    status: Optional[WebhookStatus] = Field(default=None, description="Updated status")
    
    # Configuration updates
    event_types: Optional[List[WebhookEventType]] = Field(default=None, description="Updated event types")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Updated filters")
    retry_policy: Optional[RetryPolicy] = Field(default=None, description="Updated retry policy")
    security: Optional[WebhookSecurity] = Field(default=None, description="Updated security settings")


class WebhookListResponse(BaseModel):
    """Response model for webhook listing."""
    
    webhooks: List[WebhookRegistration] = Field(description="List of webhooks")
    total: int = Field(description="Total webhook count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")


class WebhookDeliveryListResponse(BaseModel):
    """Response model for delivery history."""
    
    deliveries: List[WebhookDelivery] = Field(description="List of deliveries")
    total: int = Field(description="Total delivery count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")


class WebhookTestRequest(BaseModel):
    """Request model for webhook testing."""
    
    event_type: WebhookEventType = Field(description="Event type to test")
    test_data: Optional[Dict[str, Any]] = Field(default=None, description="Custom test data")


class WebhookTestResponse(BaseModel):
    """Response model for webhook testing."""
    
    delivery_id: str = Field(description="Test delivery ID")
    status: DeliveryStatus = Field(description="Test delivery status")
    response_status: Optional[int] = Field(default=None, description="HTTP response status")
    response_time_ms: Optional[int] = Field(default=None, description="Response time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
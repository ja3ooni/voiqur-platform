"""
Base Integration Framework

Base classes and interfaces for third-party integrations with the EUVoice AI Platform.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import uuid
import json


class IntegrationStatus(str, Enum):
    """Integration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"
    TESTING = "testing"


class IntegrationType(str, Enum):
    """Integration type enumeration."""
    TELEPHONY = "telephony"
    CRM = "crm"
    MESSAGING = "messaging"
    SOCIAL_MEDIA = "social_media"
    ANALYTICS = "analytics"
    STORAGE = "storage"


class IntegrationConfig(BaseModel):
    """Base configuration for integrations."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Integration name")
    type: IntegrationType = Field(description="Integration type")
    provider: str = Field(description="Integration provider (e.g., twilio, salesforce)")
    
    # Connection settings
    enabled: bool = Field(default=True, description="Whether integration is enabled")
    credentials: Dict[str, str] = Field(default_factory=dict, description="API credentials")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific settings")
    
    # EU compliance
    eu_region: bool = Field(default=True, description="Use EU region endpoints")
    data_residency: str = Field(default="eu", description="Data residency requirement")
    gdpr_compliant: bool = Field(default=True, description="GDPR compliance flag")
    
    # Webhook configuration
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for events")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook secret for verification")
    
    # Rate limiting
    rate_limit: int = Field(default=100, description="Requests per minute limit")
    burst_limit: int = Field(default=200, description="Burst requests limit")
    
    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=1, description="Initial retry delay in seconds")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, description="User who created the integration")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntegrationEvent(BaseModel):
    """Integration event model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    integration_id: str = Field(description="Integration ID")
    event_type: str = Field(description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event data
    data: Dict[str, Any] = Field(description="Event data")
    source: str = Field(description="Event source")
    
    # Context
    user_id: Optional[str] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None)
    
    # Processing status
    processed: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntegrationMetrics(BaseModel):
    """Integration performance metrics."""
    
    integration_id: str
    period_start: datetime
    period_end: datetime
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Performance metrics
    average_latency_ms: float = 0.0
    success_rate: float = 0.0
    
    # Error breakdown
    error_breakdown: Dict[str, int] = Field(default_factory=dict)
    
    # Usage metrics
    data_transferred_bytes: int = 0
    api_calls_made: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseIntegration(ABC):
    """
    Base class for all third-party integrations.
    
    Provides common functionality for authentication, rate limiting,
    error handling, and event processing.
    """
    
    def __init__(self, config: IntegrationConfig):
        """
        Initialize base integration.
        
        Args:
            config: Integration configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.provider}")
        self.status = IntegrationStatus.INACTIVE
        
        # Rate limiting
        self._request_timestamps = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Metrics tracking
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0.0,
            "errors": {}
        }
        
        # Event handlers
        self.event_handlers = {}
        
        # Connection state
        self._authenticated = False
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the integration.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the third-party service.
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Perform health check on the integration.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the third-party service."""
        pass
    
    async def start(self) -> bool:
        """
        Start the integration.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            self.logger.info(f"Starting {self.config.provider} integration")
            self.status = IntegrationStatus.CONFIGURING
            
            # Initialize and authenticate
            if not await self.initialize():
                self.status = IntegrationStatus.ERROR
                return False
            
            if not await self.authenticate():
                self.status = IntegrationStatus.ERROR
                return False
            
            # Perform initial health check
            if not await self.health_check():
                self.status = IntegrationStatus.ERROR
                return False
            
            self.status = IntegrationStatus.ACTIVE
            self.logger.info(f"{self.config.provider} integration started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.config.provider} integration: {e}")
            self.status = IntegrationStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop the integration."""
        try:
            self.logger.info(f"Stopping {self.config.provider} integration")
            await self.disconnect()
            self.status = IntegrationStatus.INACTIVE
            self.logger.info(f"{self.config.provider} integration stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping {self.config.provider} integration: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the integration connection.
        
        Returns:
            Test results
        """
        try:
            self.status = IntegrationStatus.TESTING
            
            # Test authentication
            auth_success = await self.authenticate()
            
            # Test health check
            health_success = await self.health_check() if auth_success else False
            
            # Restore previous status
            self.status = IntegrationStatus.ACTIVE if auth_success and health_success else IntegrationStatus.ERROR
            
            return {
                "success": auth_success and health_success,
                "authentication": auth_success,
                "health_check": health_success,
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": 0  # Would be measured in real implementation
            }
            
        except Exception as e:
            self.status = IntegrationStatus.ERROR
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_rate_limit(self) -> bool:
        """
        Check if request is within rate limits.
        
        Returns:
            True if within limits, False otherwise
        """
        async with self._rate_limit_lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            # Remove old timestamps
            self._request_timestamps = [
                ts for ts in self._request_timestamps if ts > minute_ago
            ]
            
            # Check rate limit
            if len(self._request_timestamps) >= self.config.rate_limit:
                return False
            
            # Add current timestamp
            self._request_timestamps.append(now)
            return True
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        import aiohttp
        import time
        
        # Check rate limit
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        start_time = time.time()
        
        try:
            self.metrics["total_requests"] += 1
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, **kwargs) as response:
                    latency = (time.time() - start_time) * 1000
                    self.metrics["total_latency"] += latency
                    
                    if response.status < 400:
                        self.metrics["successful_requests"] += 1
                        data = await response.json() if response.content_type == 'application/json' else await response.text()
                        return {
                            "success": True,
                            "status": response.status,
                            "data": data,
                            "latency_ms": latency
                        }
                    else:
                        self.metrics["failed_requests"] += 1
                        error_key = f"http_{response.status}"
                        self.metrics["errors"][error_key] = self.metrics["errors"].get(error_key, 0) + 1
                        
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
        
        except Exception as e:
            self.metrics["failed_requests"] += 1
            error_key = type(e).__name__
            self.metrics["errors"][error_key] = self.metrics["errors"].get(error_key, 0) + 1
            raise
    
    def register_event_handler(self, event_type: str, handler):
        """
        Register event handler for specific event type.
        
        Args:
            event_type: Event type to handle
            handler: Event handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any], **kwargs):
        """
        Emit integration event.
        
        Args:
            event_type: Event type
            data: Event data
            **kwargs: Additional event parameters
        """
        try:
            event = IntegrationEvent(
                integration_id=self.config.id,
                event_type=event_type,
                data=data,
                source=self.config.provider,
                **kwargs
            )
            
            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(f"Error in event handler for {event_type}: {e}")
            
            self.logger.debug(f"Emitted event {event_type} for integration {self.config.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to emit event {event_type}: {e}")
    
    def get_metrics(self) -> IntegrationMetrics:
        """
        Get integration metrics.
        
        Returns:
            Integration metrics
        """
        success_rate = 0.0
        avg_latency = 0.0
        
        if self.metrics["total_requests"] > 0:
            success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]
            avg_latency = self.metrics["total_latency"] / self.metrics["total_requests"]
        
        return IntegrationMetrics(
            integration_id=self.config.id,
            period_start=self.config.created_at,
            period_end=datetime.utcnow(),
            total_requests=self.metrics["total_requests"],
            successful_requests=self.metrics["successful_requests"],
            failed_requests=self.metrics["failed_requests"],
            average_latency_ms=avg_latency,
            success_rate=success_rate,
            error_breakdown=self.metrics["errors"].copy()
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get integration status information.
        
        Returns:
            Status information
        """
        return {
            "id": self.config.id,
            "name": self.config.name,
            "provider": self.config.provider,
            "type": self.config.type.value,
            "status": self.status.value,
            "enabled": self.config.enabled,
            "authenticated": self._authenticated,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "metrics": self.get_metrics().dict()
        }
    
    async def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update integration configuration.
        
        Args:
            updates: Configuration updates
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Update configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            self.config.updated_at = datetime.utcnow()
            
            # Re-authenticate if credentials changed
            if any(key in updates for key in ['credentials', 'settings']):
                self._authenticated = False
                if self.status == IntegrationStatus.ACTIVE:
                    await self.authenticate()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False


class IntegrationError(Exception):
    """Base exception for integration errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(IntegrationError):
    """Authentication error."""
    pass


class RateLimitError(IntegrationError):
    """Rate limit exceeded error."""
    pass


class ConfigurationError(IntegrationError):
    """Configuration error."""
    pass
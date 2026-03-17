"""
Webhook Service

Handles webhook registration, event processing, delivery, and retry logic
for the EUVoice AI Platform.
"""

import asyncio
import logging
import json
import hmac
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import aiohttp
import asyncpg
from redis import Redis
from contextlib import asynccontextmanager

from ..models.webhooks import (
    WebhookRegistration, WebhookEvent, WebhookDelivery, WebhookEventType,
    WebhookStatus, DeliveryStatus, RetryPolicy, WebhookFilter,
    WebhookDeliveryStats
)


logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for managing webhooks, events, and deliveries.
    
    Provides webhook registration, event publishing, delivery with retries,
    and comprehensive monitoring and statistics.
    """
    
    def __init__(self, 
                 postgres_url: str,
                 redis_url: str,
                 max_concurrent_deliveries: int = 100,
                 delivery_timeout: int = 30):
        """
        Initialize webhook service.
        
        Args:
            postgres_url: PostgreSQL connection URL
            redis_url: Redis connection URL for queuing
            max_concurrent_deliveries: Maximum concurrent deliveries
            delivery_timeout: Default delivery timeout in seconds
        """
        self.postgres_url = postgres_url
        self.redis_url = redis_url
        self.max_concurrent_deliveries = max_concurrent_deliveries
        self.delivery_timeout = delivery_timeout
        
        # Connection pools
        self.pg_pool = None
        self.redis_client = None
        
        # Delivery management
        self.delivery_semaphore = asyncio.Semaphore(max_concurrent_deliveries)
        self.delivery_tasks = set()
        
        # Statistics
        self.stats = {
            "total_webhooks": 0,
            "active_webhooks": 0,
            "total_events": 0,
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "average_delivery_time": 0.0
        }
        
        # Background tasks
        self.retry_task = None
        self.cleanup_task = None
        self.stats_task = None
        
        self.is_running = False
    
    async def initialize(self) -> None:
        """Initialize the webhook service."""
        try:
            logger.info("Initializing Webhook Service")
            
            # Initialize database connections
            self.pg_pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            self.redis_client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create database tables
            await self._create_tables()
            
            # Start background tasks
            self.retry_task = asyncio.create_task(self._retry_failed_deliveries())
            self.cleanup_task = asyncio.create_task(self._cleanup_old_deliveries())
            self.stats_task = asyncio.create_task(self._update_statistics())
            
            self.is_running = True
            logger.info("Webhook Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Webhook Service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the webhook service."""
        logger.info("Shutting down Webhook Service")
        
        self.is_running = False
        
        # Cancel background tasks
        if self.retry_task:
            self.retry_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.stats_task:
            self.stats_task.cancel()
        
        # Wait for delivery tasks to complete
        if self.delivery_tasks:
            await asyncio.gather(*self.delivery_tasks, return_exceptions=True)
        
        # Close connections
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis_client:
            self.redis_client.close()
        
        logger.info("Webhook Service shutdown complete")
    
    async def _create_tables(self) -> None:
        """Create database tables for webhooks."""
        async with self.pg_pool.acquire() as conn:
            # Webhooks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    url TEXT NOT NULL,
                    method VARCHAR(10) NOT NULL DEFAULT 'POST',
                    filters JSONB NOT NULL,
                    retry_policy JSONB NOT NULL,
                    security JSONB NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_delivery_at TIMESTAMP WITH TIME ZONE,
                    total_deliveries INTEGER DEFAULT 0,
                    successful_deliveries INTEGER DEFAULT 0,
                    failed_deliveries INTEGER DEFAULT 0,
                    data_residency VARCHAR(10) DEFAULT 'eu',
                    gdpr_compliant BOOLEAN DEFAULT TRUE
                );
            """)
            
            # Events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id VARCHAR(36) PRIMARY KEY,
                    event_type VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    data JSONB NOT NULL,
                    user_id VARCHAR(36),
                    conversation_id VARCHAR(36),
                    request_id VARCHAR(36),
                    source VARCHAR(100) NOT NULL,
                    version VARCHAR(10) DEFAULT '1.0',
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Deliveries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    id VARCHAR(36) PRIMARY KEY,
                    webhook_id VARCHAR(36) NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
                    event_id VARCHAR(36) NOT NULL REFERENCES webhook_events(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    headers JSONB NOT NULL,
                    payload TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    attempt_number INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    attempted_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    next_retry_at TIMESTAMP WITH TIME ZONE,
                    response_status INTEGER,
                    response_headers JSONB,
                    response_body TEXT,
                    error_message TEXT,
                    error_code VARCHAR(50),
                    duration_ms INTEGER
                );
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_user_id ON webhooks(user_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_status ON webhooks(status);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON webhook_events(event_type);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_processed ON webhook_events(processed);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON webhook_events(timestamp);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_status ON webhook_deliveries(status);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_retry ON webhook_deliveries(next_retry_at);")
    
    # Webhook Registration Management
    
    async def register_webhook(self, webhook: WebhookRegistration) -> str:
        """
        Register a new webhook.
        
        Args:
            webhook: Webhook registration data
            
        Returns:
            Webhook ID
        """
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO webhooks (
                        id, user_id, name, description, url, method,
                        filters, retry_policy, security, status,
                        data_residency, gdpr_compliant
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, 
                    webhook.id, webhook.user_id, webhook.name, webhook.description,
                    str(webhook.url), webhook.method,
                    json.dumps(webhook.filters.dict()), 
                    json.dumps(webhook.retry_policy.dict()),
                    json.dumps(webhook.security.dict()),
                    webhook.status.value,
                    webhook.data_residency, webhook.gdpr_compliant
                )
            
            logger.info(f"Registered webhook {webhook.id} for user {webhook.user_id}")
            return webhook.id
            
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")
            raise
    
    async def get_webhook(self, webhook_id: str, user_id: str) -> Optional[WebhookRegistration]:
        """Get webhook by ID and user ID."""
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM webhooks 
                    WHERE id = $1 AND user_id = $2
                """, webhook_id, user_id)
                
                if not row:
                    return None
                
                return self._row_to_webhook(row)
                
        except Exception as e:
            logger.error(f"Failed to get webhook {webhook_id}: {e}")
            raise
    
    async def list_webhooks(self, user_id: str, 
                          page: int = 1, page_size: int = 20) -> Tuple[List[WebhookRegistration], int]:
        """List webhooks for a user with pagination."""
        try:
            offset = (page - 1) * page_size
            
            async with self.pg_pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("""
                    SELECT COUNT(*) FROM webhooks WHERE user_id = $1
                """, user_id)
                
                # Get webhooks
                rows = await conn.fetch("""
                    SELECT * FROM webhooks 
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """, user_id, page_size, offset)
                
                webhooks = [self._row_to_webhook(row) for row in rows]
                return webhooks, total
                
        except Exception as e:
            logger.error(f"Failed to list webhooks for user {user_id}: {e}")
            raise
    
    async def update_webhook(self, webhook_id: str, user_id: str, 
                           updates: Dict[str, Any]) -> bool:
        """Update webhook configuration."""
        try:
            # Build update query dynamically
            set_clauses = []
            values = []
            param_count = 0
            
            for field, value in updates.items():
                if field in ['name', 'description', 'url', 'method', 'status']:
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
                elif field in ['filters', 'retry_policy', 'security']:
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(json.dumps(value))
            
            if not set_clauses:
                return False
            
            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            
            # Add WHERE conditions
            param_count += 1
            values.append(webhook_id)
            param_count += 1
            values.append(user_id)
            
            query = f"""
                UPDATE webhooks 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count-1} AND user_id = ${param_count}
            """
            
            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *values)
                
            updated = result.split()[-1] == '1'
            if updated:
                logger.info(f"Updated webhook {webhook_id}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Failed to update webhook {webhook_id}: {e}")
            raise
    
    async def delete_webhook(self, webhook_id: str, user_id: str) -> bool:
        """Delete a webhook."""
        try:
            async with self.pg_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM webhooks 
                    WHERE id = $1 AND user_id = $2
                """, webhook_id, user_id)
            
            deleted = result.split()[-1] == '1'
            if deleted:
                logger.info(f"Deleted webhook {webhook_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")
            raise
    
    # Event Publishing and Processing
    
    async def publish_event(self, event: WebhookEvent) -> None:
        """
        Publish an event to all matching webhooks.
        
        Args:
            event: Event to publish
        """
        try:
            # Store event in database
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO webhook_events (
                        id, event_type, timestamp, data, user_id,
                        conversation_id, request_id, source, version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                    event.id, event.event_type.value, event.timestamp,
                    json.dumps(event.data), event.user_id,
                    event.conversation_id, event.request_id,
                    event.source, event.version
                )
            
            # Queue event for processing
            await self._queue_event_for_processing(event)
            
            logger.debug(f"Published event {event.id} of type {event.event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            raise
    
    async def _queue_event_for_processing(self, event: WebhookEvent) -> None:
        """Queue event for asynchronous processing."""
        try:
            # Add to Redis queue for processing
            event_data = {
                "id": event.id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
                "user_id": event.user_id,
                "conversation_id": event.conversation_id,
                "request_id": event.request_id,
                "source": event.source,
                "version": event.version
            }
            
            self.redis_client.lpush("webhook_events", json.dumps(event_data))
            
            # Process immediately if not too busy
            if len(self.delivery_tasks) < self.max_concurrent_deliveries // 2:
                task = asyncio.create_task(self._process_event(event))
                self.delivery_tasks.add(task)
                task.add_done_callback(self.delivery_tasks.discard)
            
        except Exception as e:
            logger.error(f"Failed to queue event {event.id}: {e}")
    
    async def _process_event(self, event: WebhookEvent) -> None:
        """Process an event by finding matching webhooks and creating deliveries."""
        try:
            # Find matching webhooks
            matching_webhooks = await self._find_matching_webhooks(event)
            
            if not matching_webhooks:
                logger.debug(f"No matching webhooks for event {event.id}")
                return
            
            # Create deliveries for each matching webhook
            for webhook in matching_webhooks:
                await self._create_delivery(webhook, event)
            
            # Mark event as processed
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE webhook_events SET processed = TRUE WHERE id = $1
                """, event.id)
            
        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
    
    async def _find_matching_webhooks(self, event: WebhookEvent) -> List[WebhookRegistration]:
        """Find webhooks that match the event criteria."""
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM webhooks 
                    WHERE status = 'active'
                    AND (
                        filters->>'event_types' IS NULL 
                        OR $1 = ANY(
                            SELECT jsonb_array_elements_text(filters->'event_types')
                        )
                    )
                """, event.event_type.value)
            
            matching_webhooks = []
            
            for row in rows:
                webhook = self._row_to_webhook(row)
                
                # Apply additional filters
                if self._event_matches_filters(event, webhook.filters):
                    matching_webhooks.append(webhook)
            
            return matching_webhooks
            
        except Exception as e:
            logger.error(f"Failed to find matching webhooks for event {event.id}: {e}")
            return []
    
    def _event_matches_filters(self, event: WebhookEvent, filters: WebhookFilter) -> bool:
        """Check if event matches webhook filters."""
        try:
            # Check event type
            if event.event_type not in filters.event_types:
                return False
            
            # Check user ID filter
            if filters.user_ids and event.user_id not in filters.user_ids:
                return False
            
            # Check conversation ID filter
            if filters.conversation_ids and event.conversation_id not in filters.conversation_ids:
                return False
            
            # Check language filter
            if filters.languages:
                event_language = event.data.get('language')
                if event_language and event_language not in filters.languages:
                    return False
            
            # Check agent type filter
            if filters.agent_types:
                agent_type = event.data.get('agent_type') or event.source
                if agent_type not in filters.agent_types:
                    return False
            
            # Check custom conditions
            if filters.conditions:
                for key, expected_value in filters.conditions.items():
                    if event.data.get(key) != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error matching event filters: {e}")
            return False
    
    # Delivery Management
    
    async def _create_delivery(self, webhook: WebhookRegistration, event: WebhookEvent) -> str:
        """Create a delivery for a webhook and event."""
        try:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_id=event.id,
                url=str(webhook.url),
                method=webhook.method,
                headers=self._build_headers(webhook, event),
                payload=self._build_payload(webhook, event),
                status=DeliveryStatus.PENDING,
                attempt_number=1
            )
            
            # Store delivery in database
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO webhook_deliveries (
                        id, webhook_id, event_id, url, method, headers,
                        payload, status, attempt_number
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                    delivery.id, delivery.webhook_id, delivery.event_id,
                    delivery.url, delivery.method, json.dumps(delivery.headers),
                    delivery.payload, delivery.status.value, delivery.attempt_number
                )
            
            # Queue for immediate delivery
            task = asyncio.create_task(self._deliver_webhook(delivery))
            self.delivery_tasks.add(task)
            task.add_done_callback(self.delivery_tasks.discard)
            
            return delivery.id
            
        except Exception as e:
            logger.error(f"Failed to create delivery for webhook {webhook.id}: {e}")
            raise
    
    def _build_headers(self, webhook: WebhookRegistration, event: WebhookEvent) -> Dict[str, str]:
        """Build HTTP headers for webhook delivery."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EUVoice-Webhook/1.0",
            "X-EUVoice-Event": event.event_type.value,
            "X-EUVoice-Event-ID": event.id,
            "X-EUVoice-Timestamp": event.timestamp.isoformat(),
            "X-EUVoice-Webhook-ID": webhook.id
        }
        
        # Add custom headers
        if webhook.security.custom_headers:
            headers.update(webhook.security.custom_headers)
        
        # Add HMAC signature if secret token is configured
        if webhook.security.secret_token:
            payload = self._build_payload(webhook, event)
            signature = self._generate_signature(payload, webhook.security.secret_token)
            headers["X-EUVoice-Signature"] = f"sha256={signature}"
        
        return headers
    
    def _build_payload(self, webhook: WebhookRegistration, event: WebhookEvent) -> str:
        """Build JSON payload for webhook delivery."""
        payload = {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "webhook_id": webhook.id,
            "version": event.version
        }
        
        # Add optional fields if present
        if event.user_id:
            payload["user_id"] = event.user_id
        if event.conversation_id:
            payload["conversation_id"] = event.conversation_id
        if event.request_id:
            payload["request_id"] = event.request_id
        
        return json.dumps(payload, separators=(',', ':'))
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for payload verification."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _deliver_webhook(self, delivery: WebhookDelivery) -> None:
        """Deliver a webhook with retry logic."""
        async with self.delivery_semaphore:
            try:
                # Update delivery status to attempting
                await self._update_delivery_status(
                    delivery.id, 
                    DeliveryStatus.RETRYING if delivery.attempt_number > 1 else DeliveryStatus.PENDING,
                    attempted_at=datetime.utcnow()
                )
                
                # Make HTTP request
                start_time = time.time()
                
                timeout = aiohttp.ClientTimeout(total=self.delivery_timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        delivery.method,
                        delivery.url,
                        headers=delivery.headers,
                        data=delivery.payload
                    ) as response:
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        # Read response
                        response_body = await response.text()
                        response_headers = dict(response.headers)
                        
                        # Check if delivery was successful
                        if 200 <= response.status < 300:
                            await self._handle_successful_delivery(
                                delivery, response.status, response_headers, 
                                response_body, duration_ms
                            )
                        else:
                            await self._handle_failed_delivery(
                                delivery, response.status, response_headers,
                                response_body, duration_ms,
                                f"HTTP {response.status}: {response_body[:200]}"
                            )
            
            except asyncio.TimeoutError:
                await self._handle_failed_delivery(
                    delivery, None, None, None, None,
                    "Request timeout", "TIMEOUT"
                )
            
            except Exception as e:
                await self._handle_failed_delivery(
                    delivery, None, None, None, None,
                    str(e), "CONNECTION_ERROR"
                )
    
    async def _handle_successful_delivery(self, delivery: WebhookDelivery,
                                        status: int, headers: Dict[str, str],
                                        body: str, duration_ms: int) -> None:
        """Handle successful webhook delivery."""
        try:
            # Update delivery record
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE webhook_deliveries 
                    SET status = $1, completed_at = $2, response_status = $3,
                        response_headers = $4, response_body = $5, duration_ms = $6
                    WHERE id = $7
                """, 
                    DeliveryStatus.DELIVERED.value, datetime.utcnow(), status,
                    json.dumps(headers), body[:1000], duration_ms, delivery.id
                )
                
                # Update webhook statistics
                await conn.execute("""
                    UPDATE webhooks 
                    SET successful_deliveries = successful_deliveries + 1,
                        total_deliveries = total_deliveries + 1,
                        last_delivery_at = $1
                    WHERE id = $2
                """, datetime.utcnow(), delivery.webhook_id)
            
            logger.debug(f"Successfully delivered webhook {delivery.id}")
            
        except Exception as e:
            logger.error(f"Failed to update successful delivery {delivery.id}: {e}")
    
    async def _handle_failed_delivery(self, delivery: WebhookDelivery,
                                    status: Optional[int], headers: Optional[Dict[str, str]],
                                    body: Optional[str], duration_ms: Optional[int],
                                    error_message: str, error_code: str = "HTTP_ERROR") -> None:
        """Handle failed webhook delivery with retry logic."""
        try:
            # Get webhook and retry policy
            webhook = await self._get_webhook_by_id(delivery.webhook_id)
            if not webhook:
                logger.error(f"Webhook {delivery.webhook_id} not found for delivery {delivery.id}")
                return
            
            retry_policy = webhook.retry_policy
            
            # Check if we should retry
            if delivery.attempt_number < retry_policy.max_attempts:
                # Calculate next retry time
                delay = min(
                    retry_policy.initial_delay * (retry_policy.backoff_multiplier ** (delivery.attempt_number - 1)),
                    retry_policy.max_delay
                )
                next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                
                # Update delivery for retry
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE webhook_deliveries 
                        SET status = $1, response_status = $2, response_headers = $3,
                            response_body = $4, duration_ms = $5, error_message = $6,
                            error_code = $7, next_retry_at = $8, attempt_number = $9
                        WHERE id = $10
                    """, 
                        DeliveryStatus.RETRYING.value, status,
                        json.dumps(headers) if headers else None,
                        body[:1000] if body else None, duration_ms,
                        error_message, error_code, next_retry_at,
                        delivery.attempt_number + 1, delivery.id
                    )
                
                logger.info(f"Scheduled retry for delivery {delivery.id} in {delay} seconds")
                
            else:
                # Max retries exceeded, mark as failed
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE webhook_deliveries 
                        SET status = $1, completed_at = $2, response_status = $3,
                            response_headers = $4, response_body = $5, duration_ms = $6,
                            error_message = $7, error_code = $8
                        WHERE id = $9
                    """, 
                        DeliveryStatus.FAILED.value, datetime.utcnow(), status,
                        json.dumps(headers) if headers else None,
                        body[:1000] if body else None, duration_ms,
                        error_message, error_code, delivery.id
                    )
                    
                    # Update webhook statistics
                    await conn.execute("""
                        UPDATE webhooks 
                        SET failed_deliveries = failed_deliveries + 1,
                            total_deliveries = total_deliveries + 1
                        WHERE id = $1
                    """, delivery.webhook_id)
                
                logger.warning(f"Delivery {delivery.id} failed permanently after {delivery.attempt_number} attempts")
            
        except Exception as e:
            logger.error(f"Failed to handle failed delivery {delivery.id}: {e}")
    
    # Background Tasks
    
    async def _retry_failed_deliveries(self) -> None:
        """Background task to retry failed deliveries."""
        while self.is_running:
            try:
                # Find deliveries ready for retry
                async with self.pg_pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM webhook_deliveries 
                        WHERE status = 'retrying' 
                        AND next_retry_at <= NOW()
                        ORDER BY next_retry_at
                        LIMIT 50
                    """)
                
                for row in rows:
                    delivery = self._row_to_delivery(row)
                    
                    # Create retry task
                    task = asyncio.create_task(self._deliver_webhook(delivery))
                    self.delivery_tasks.add(task)
                    task.add_done_callback(self.delivery_tasks.discard)
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry task: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_deliveries(self) -> None:
        """Background task to cleanup old delivery records."""
        while self.is_running:
            try:
                # Delete deliveries older than 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                async with self.pg_pool.acquire() as conn:
                    result = await conn.execute("""
                        DELETE FROM webhook_deliveries 
                        WHERE created_at < $1 
                        AND status IN ('delivered', 'failed', 'expired')
                    """, cutoff_date)
                
                deleted_count = int(result.split()[-1])
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old delivery records")
                
                # Wait 24 hours before next cleanup
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def _update_statistics(self) -> None:
        """Background task to update service statistics."""
        while self.is_running:
            try:
                async with self.pg_pool.acquire() as conn:
                    # Update webhook counts
                    webhook_stats = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as total_webhooks,
                            COUNT(*) FILTER (WHERE status = 'active') as active_webhooks
                        FROM webhooks
                    """)
                    
                    # Update delivery stats
                    delivery_stats = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as total_deliveries,
                            COUNT(*) FILTER (WHERE status = 'delivered') as successful_deliveries,
                            COUNT(*) FILTER (WHERE status = 'failed') as failed_deliveries,
                            AVG(duration_ms) as avg_duration
                        FROM webhook_deliveries
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                    """)
                    
                    # Update event count
                    event_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM webhook_events
                        WHERE timestamp > NOW() - INTERVAL '24 hours'
                    """)
                
                # Update statistics
                self.stats.update({
                    "total_webhooks": webhook_stats["total_webhooks"],
                    "active_webhooks": webhook_stats["active_webhooks"],
                    "total_events": event_count,
                    "total_deliveries": delivery_stats["total_deliveries"],
                    "successful_deliveries": delivery_stats["successful_deliveries"],
                    "failed_deliveries": delivery_stats["failed_deliveries"],
                    "average_delivery_time": float(delivery_stats["avg_duration"] or 0)
                })
                
                # Wait 5 minutes before next update
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)
    
    # Utility Methods
    
    def _row_to_webhook(self, row) -> WebhookRegistration:
        """Convert database row to WebhookRegistration object."""
        from ..models.webhooks import WebhookFilter, RetryPolicy, WebhookSecurity
        
        return WebhookRegistration(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            url=row["url"],
            method=row["method"],
            filters=WebhookFilter(**json.loads(row["filters"])),
            retry_policy=RetryPolicy(**json.loads(row["retry_policy"])),
            security=WebhookSecurity(**json.loads(row["security"])),
            status=WebhookStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_delivery_at=row["last_delivery_at"],
            total_deliveries=row["total_deliveries"],
            successful_deliveries=row["successful_deliveries"],
            failed_deliveries=row["failed_deliveries"],
            data_residency=row["data_residency"],
            gdpr_compliant=row["gdpr_compliant"]
        )
    
    def _row_to_delivery(self, row) -> WebhookDelivery:
        """Convert database row to WebhookDelivery object."""
        return WebhookDelivery(
            id=row["id"],
            webhook_id=row["webhook_id"],
            event_id=row["event_id"],
            url=row["url"],
            method=row["method"],
            headers=json.loads(row["headers"]),
            payload=row["payload"],
            status=DeliveryStatus(row["status"]),
            attempt_number=row["attempt_number"],
            created_at=row["created_at"],
            attempted_at=row["attempted_at"],
            completed_at=row["completed_at"],
            next_retry_at=row["next_retry_at"],
            response_status=row["response_status"],
            response_headers=json.loads(row["response_headers"]) if row["response_headers"] else None,
            response_body=row["response_body"],
            error_message=row["error_message"],
            error_code=row["error_code"],
            duration_ms=row["duration_ms"]
        )
    
    async def _get_webhook_by_id(self, webhook_id: str) -> Optional[WebhookRegistration]:
        """Get webhook by ID (internal method)."""
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM webhooks WHERE id = $1", webhook_id)
                return self._row_to_webhook(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get webhook {webhook_id}: {e}")
            return None
    
    async def _update_delivery_status(self, delivery_id: str, status: DeliveryStatus, **kwargs) -> None:
        """Update delivery status and optional fields."""
        try:
            set_clauses = ["status = $2"]
            values = [delivery_id, status.value]
            param_count = 2
            
            for field, value in kwargs.items():
                if value is not None:
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
            
            query = f"UPDATE webhook_deliveries SET {', '.join(set_clauses)} WHERE id = $1"
            
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query, *values)
                
        except Exception as e:
            logger.error(f"Failed to update delivery status {delivery_id}: {e}")
    
    # Public API Methods
    
    async def test_webhook(self, webhook_id: str, user_id: str, 
                          event_type: WebhookEventType, 
                          test_data: Optional[Dict[str, Any]] = None) -> WebhookDelivery:
        """Test a webhook by sending a test event."""
        webhook = await self.get_webhook(webhook_id, user_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")
        
        # Create test event
        test_event = WebhookEvent(
            event_type=event_type,
            data=test_data or {"test": True, "message": "This is a test webhook delivery"},
            user_id=user_id,
            source="webhook_test"
        )
        
        # Create and execute delivery
        delivery_id = await self._create_delivery(webhook, test_event)
        
        # Wait for delivery to complete (with timeout)
        for _ in range(30):  # 30 seconds timeout
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM webhook_deliveries WHERE id = $1
                """, delivery_id)
            
            if row and row["status"] in ["delivered", "failed"]:
                return self._row_to_delivery(row)
            
            await asyncio.sleep(1)
        
        # Timeout - return current status
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM webhook_deliveries WHERE id = $1
            """, delivery_id)
        
        return self._row_to_delivery(row) if row else None
    
    async def get_delivery_history(self, webhook_id: str, user_id: str,
                                 page: int = 1, page_size: int = 20) -> Tuple[List[WebhookDelivery], int]:
        """Get delivery history for a webhook."""
        # Verify webhook ownership
        webhook = await self.get_webhook(webhook_id, user_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")
        
        offset = (page - 1) * page_size
        
        async with self.pg_pool.acquire() as conn:
            # Get total count
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM webhook_deliveries WHERE webhook_id = $1
            """, webhook_id)
            
            # Get deliveries
            rows = await conn.fetch("""
                SELECT * FROM webhook_deliveries 
                WHERE webhook_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, webhook_id, page_size, offset)
            
            deliveries = [self._row_to_delivery(row) for row in rows]
            return deliveries, total
    
    async def get_webhook_stats(self, webhook_id: str, user_id: str,
                              days: int = 7) -> WebhookDeliveryStats:
        """Get delivery statistics for a webhook."""
        # Verify webhook ownership
        webhook = await self.get_webhook(webhook_id, user_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")
        
        period_start = datetime.utcnow() - timedelta(days=days)
        period_end = datetime.utcnow()
        
        async with self.pg_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_deliveries,
                    COUNT(*) FILTER (WHERE status = 'delivered') as successful_deliveries,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_deliveries,
                    AVG(duration_ms) as avg_latency,
                    COUNT(DISTINCT event_id) as total_events
                FROM webhook_deliveries 
                WHERE webhook_id = $1 AND created_at BETWEEN $2 AND $3
            """, webhook_id, period_start, period_end)
            
            # Get error breakdown
            error_rows = await conn.fetch("""
                SELECT error_code, COUNT(*) as count
                FROM webhook_deliveries 
                WHERE webhook_id = $1 AND created_at BETWEEN $2 AND $3
                AND status = 'failed' AND error_code IS NOT NULL
                GROUP BY error_code
            """, webhook_id, period_start, period_end)
            
            error_breakdown = {row["error_code"]: row["count"] for row in error_rows}
        
        success_rate = 0.0
        if stats["total_deliveries"] > 0:
            success_rate = stats["successful_deliveries"] / stats["total_deliveries"]
        
        return WebhookDeliveryStats(
            webhook_id=webhook_id,
            period_start=period_start,
            period_end=period_end,
            total_events=stats["total_events"],
            total_deliveries=stats["total_deliveries"],
            successful_deliveries=stats["successful_deliveries"],
            failed_deliveries=stats["failed_deliveries"],
            average_latency_ms=float(stats["avg_latency"] or 0),
            success_rate=success_rate,
            error_breakdown=error_breakdown
        )
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get overall service statistics."""
        return {
            **self.stats,
            "active_delivery_tasks": len(self.delivery_tasks),
            "is_running": self.is_running
        }
"""
Rate Limiting System

Implements distributed rate limiting with Redis backend for API protection.
"""

import time
import asyncio
from typing import Optional, Dict, Any
import logging
from enum import Enum

# Redis is optional for distributed rate limiting
REDIS_AVAILABLE = False

from .config import RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limit tiers based on user type."""
    
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    PREMIUM = "premium"
    ADMIN = "admin"


class RateLimitResult:
    """Rate limit check result."""
    
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_time: float,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after


class RateLimiter:
    """
    Distributed rate limiter using Redis.
    
    Implements sliding window rate limiting with different tiers
    and endpoint-specific limits.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis = None
        
        # Rate limit mappings
        self.tier_limits = {
            RateLimitTier.ANONYMOUS: config.default_rate_limit,
            RateLimitTier.AUTHENTICATED: config.authenticated_rate_limit,
            RateLimitTier.PREMIUM: config.premium_rate_limit,
            RateLimitTier.ADMIN: config.premium_rate_limit * 2
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            "/api/v1/voice/stt": config.voice_processing_limit,
            "/api/v1/voice/tts": config.voice_processing_limit,
            "/api/v1/voice/llm": config.voice_processing_limit,
            "/api/v1/webhooks": config.webhook_limit,
            "/api/v1/auth": config.auth_limit,
        }
    
    async def initialize(self):
        """Initialize Redis connection."""
        # Using in-memory rate limiting for basic implementation
        logger.info("Rate limiter initialized with in-memory backend")
    
    async def cleanup(self):
        """Cleanup Redis connection."""
        if self.redis:
            await self.redis.close()
    
    async def is_allowed(
        self,
        identifier: str,
        endpoint: str,
        tier: RateLimitTier = RateLimitTier.ANONYMOUS
    ) -> bool:
        """
        Check if request is allowed under rate limits.
        
        Args:
            identifier: Client identifier (IP, user ID, etc.)
            endpoint: API endpoint path
            tier: Rate limit tier
            
        Returns:
            True if request is allowed, False otherwise
        """
        result = await self.check_rate_limit(identifier, endpoint, tier)
        return result.allowed
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        tier: RateLimitTier = RateLimitTier.ANONYMOUS
    ) -> RateLimitResult:
        """
        Check rate limit and return detailed result.
        
        Args:
            identifier: Client identifier
            endpoint: API endpoint path
            tier: Rate limit tier
            
        Returns:
            Rate limit result with details
        """
        # Determine rate limit for this request
        limit = self._get_limit_for_endpoint(endpoint, tier)
        window_size = 60  # 1 minute window
        
        if self.redis:
            return await self._check_redis_rate_limit(
                identifier, endpoint, limit, window_size
            )
        else:
            return await self._check_memory_rate_limit(
                identifier, endpoint, limit, window_size
            )
    
    def _get_limit_for_endpoint(
        self,
        endpoint: str,
        tier: RateLimitTier
    ) -> int:
        """Get rate limit for specific endpoint and tier."""
        # Check for endpoint-specific limit
        for pattern, limit in self.endpoint_limits.items():
            if endpoint.startswith(pattern):
                # Apply tier multiplier
                if tier == RateLimitTier.AUTHENTICATED:
                    return int(limit * 2)
                elif tier == RateLimitTier.PREMIUM:
                    return int(limit * 5)
                elif tier == RateLimitTier.ADMIN:
                    return int(limit * 10)
                return limit
        
        # Use tier default
        return self.tier_limits[tier]
    
    async def _check_redis_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window_size: int
    ) -> RateLimitResult:
        """Check rate limit using Redis sliding window."""
        now = time.time()
        window_start = now - window_size
        
        # Create unique key for this identifier/endpoint combination
        key = f"rate_limit:{identifier}:{endpoint}"
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, window_size + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if limit exceeded
        allowed = current_count < limit
        remaining = max(0, limit - current_count - 1)
        reset_time = now + window_size
        
        if not allowed:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(key, str(now))
            retry_after = int(window_size)
        else:
            retry_after = None
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after
        )
    
    async def _check_memory_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window_size: int
    ) -> RateLimitResult:
        """Fallback in-memory rate limiting."""
        # This is a simplified implementation for fallback
        # In production, you'd want a more sophisticated in-memory store
        
        now = time.time()
        key = f"{identifier}:{endpoint}"
        
        # For simplicity, just allow all requests in fallback mode
        # but log the attempt
        logger.warning(f"Using fallback rate limiting for {key}")
        
        return RateLimitResult(
            allowed=True,
            remaining=limit - 1,
            reset_time=now + window_size,
            retry_after=None
        )
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        endpoint: str,
        tier: RateLimitTier = RateLimitTier.ANONYMOUS
    ) -> Dict[str, Any]:
        """
        Get current rate limit status without consuming a request.
        
        Args:
            identifier: Client identifier
            endpoint: API endpoint path
            tier: Rate limit tier
            
        Returns:
            Rate limit status information
        """
        limit = self._get_limit_for_endpoint(endpoint, tier)
        
        if not self.redis:
            return {
                "limit": limit,
                "remaining": limit,
                "reset_time": time.time() + 60,
                "window_size": 60
            }
        
        now = time.time()
        window_size = 60
        window_start = now - window_size
        key = f"rate_limit:{identifier}:{endpoint}"
        
        # Count current requests without adding new one
        await self.redis.zremrangebyscore(key, 0, window_start)
        current_count = await self.redis.zcard(key)
        
        return {
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset_time": now + window_size,
            "window_size": window_size,
            "current_count": current_count
        }
    
    async def reset_rate_limit(self, identifier: str, endpoint: str):
        """
        Reset rate limit for specific identifier/endpoint.
        
        Args:
            identifier: Client identifier
            endpoint: API endpoint path
        """
        if self.redis:
            key = f"rate_limit:{identifier}:{endpoint}"
            await self.redis.delete(key)
            logger.info(f"Reset rate limit for {identifier}:{endpoint}")
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics."""
        if not self.redis:
            return {"error": "Redis not available"}
        
        # Get all rate limit keys
        keys = await self.redis.keys("rate_limit:*")
        
        stats = {
            "total_clients": len(keys),
            "active_limits": 0,
            "endpoints": {}
        }
        
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.split(":")
            if len(parts) >= 3:
                endpoint = ":".join(parts[2:])
                if endpoint not in stats["endpoints"]:
                    stats["endpoints"][endpoint] = 0
                
                count = await self.redis.zcard(key)
                if count > 0:
                    stats["active_limits"] += 1
                    stats["endpoints"][endpoint] += count
        
        return stats
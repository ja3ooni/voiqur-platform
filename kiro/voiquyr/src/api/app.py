"""
FastAPI Application Factory

Creates and configures the main FastAPI application with all necessary
middleware, routers, and documentation.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
import time
import logging
from typing import Optional
import asyncpg
import redis.asyncio as aioredis

from .auth import AuthManager
from .rate_limiter import RateLimiter
from .routers import voice_processing, webhooks, health, integrations
from .middleware import SecurityMiddleware, LoggingMiddleware
from .config import APIConfig
from .services.webhook_service import WebhookService
from .utils.webhook_publisher import WebhookEventPublisher, set_global_publisher
from .routers.webhooks import set_webhook_service
from .integrations.manager import IntegrationManager, set_integration_manager

logger = logging.getLogger(__name__)


def create_app(config: Optional[APIConfig] = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        config: API configuration object
        
    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = APIConfig()
    
    app = FastAPI(
        title="EUVoice AI Platform API",
        description="REST/GraphQL APIs for voice processing and integrations",
        version="1.0.0",
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
        openapi_url="/openapi.json" if config.enable_docs else None,
    )
    
    # Initialize components
    auth_manager = AuthManager(config.auth_config)
    rate_limiter = RateLimiter(config.rate_limit_config)
    
    # Initialize webhook service
    webhook_service = WebhookService(
        postgres_url=config.database_url,
        redis_url=config.redis_url,
        max_concurrent_deliveries=config.max_concurrent_webhooks,
        delivery_timeout=config.webhook_timeout
    )
    
    # Initialize webhook publisher
    webhook_publisher = WebhookEventPublisher(webhook_service)
    set_global_publisher(webhook_publisher)
    set_webhook_service(webhook_service)
    
    # Initialize integration manager
    integration_manager = IntegrationManager()
    set_integration_manager(integration_manager)
    
    # Add security middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for EU compliance
    if config.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.trusted_hosts
        )
    
    # Add rate limiting middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Apply rate limiting to all requests."""
        client_ip = request.client.host
        
        if not await rate_limiter.is_allowed(client_ip, request.url.path):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        response = await call_next(request)
        return response
    
    # Add request timing middleware
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        """Add request timing headers."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include routers
    app.include_router(
        voice_processing.router,
        prefix="/api/v1/voice",
        tags=["Voice Processing"]
    )
    
    app.include_router(
        webhooks.router,
        prefix="/api/v1/webhooks",
        tags=["Webhooks"]
    )
    
    app.include_router(
        health.router,
        prefix="/api/v1/health",
        tags=["Health"]
    )
    
    app.include_router(
        integrations.router,
        prefix="/api/v1/integrations",
        tags=["Integrations"]
    )

    from .routers import auth as auth_router
    app.include_router(
        auth_router.router,
        prefix="/api/v1/auth",
        tags=["Auth"]
    )

    # Store components in app state
    app.state.auth_manager = auth_manager
    app.state.rate_limiter = rate_limiter
    app.state.webhook_service = webhook_service
    app.state.webhook_publisher = webhook_publisher
    app.state.integration_manager = integration_manager
    app.state.config = config
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = get_openapi(
            title="EUVoice AI Platform API",
            version="1.0.0",
            description="REST/GraphQL APIs for voice processing and integrations",
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "/api/v1/auth/authorize",
                        "tokenUrl": "/api/v1/auth/token",
                        "scopes": {
                            "voice:read": "Read voice processing results",
                            "voice:write": "Submit voice processing requests",
                            "webhooks:manage": "Manage webhook subscriptions",
                            "admin": "Administrative access"
                        }
                    }
                }
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("Starting EUVoice AI Platform API")

        # Initialize shared connection pools
        try:
            app.state.db_pool = await asyncpg.create_pool(
                dsn=config.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL pool initialized")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}")
            app.state.db_pool = None

        # Initialize schema (after db_pool is ready)
        if app.state.db_pool is not None:
            from .db import create_schema
            await create_schema(app.state.db_pool)

        try:
            app.state.redis = aioredis.from_url(
                config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await app.state.redis.ping()
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            app.state.redis = None

        await auth_manager.initialize()
        await rate_limiter.initialize()
        await webhook_service.initialize()
        await integration_manager.start()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down EUVoice AI Platform API")

        # Close connection pools before other cleanup
        if getattr(app.state, "db_pool", None):
            await app.state.db_pool.close()
            logger.info("PostgreSQL pool closed")
        if getattr(app.state, "redis", None):
            await app.state.redis.aclose()
            logger.info("Redis client closed")

        await integration_manager.stop()
        await webhook_service.shutdown()
        await auth_manager.cleanup()
        await rate_limiter.cleanup()
    
    return app
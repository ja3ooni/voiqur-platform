"""
Database and cache dependency injection for FastAPI route handlers.

Provides FastAPI Depends() functions that yield database connections
and the Redis client from the app-level connection pools stored on app.state.

Pools are created in app.py startup_event and closed in shutdown_event.
Route handlers should not create their own connections.

Usage in route handlers:
    from .db import get_db, get_redis

    @router.get("/example")
    async def example(
        request: Request,
        conn: asyncpg.Connection = Depends(get_db),
    ):
        row = await conn.fetchrow("SELECT 1")
"""

import logging as _logging

import asyncpg
from fastapi import Request, HTTPException, status

_schema_logger = _logging.getLogger(__name__)


async def get_db(request: Request) -> asyncpg.Connection:
    """
    FastAPI dependency that yields a DB connection from the app-level asyncpg pool.

    The pool is created in app.py startup_event and stored as app.state.db_pool.
    Raises HTTP 503 if the pool has not been initialized (e.g., during tests without
    startup or when PostgreSQL is unreachable at boot time).

    Use as a Depends() parameter:
        async def my_route(conn: asyncpg.Connection = Depends(get_db)):
            ...
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database pool not initialized",
        )
    async with pool.acquire() as conn:
        yield conn


async def get_redis(request: Request):
    """
    FastAPI dependency that returns the app-level Redis client.

    The client is created in app.py startup_event and stored as app.state.redis.
    Uses redis.asyncio (redis-py v4+) which provides the same from_url() API as
    aioredis and is compatible with Python 3.12+.

    Raises HTTP 503 if the client has not been initialized.

    Use as a Depends() parameter:
        async def my_route(redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client not initialized",
        )
    return redis


async def create_schema(pool: asyncpg.Pool) -> None:
    """
    Create all required database tables if they do not exist.

    Called once during app startup. Uses CREATE TABLE IF NOT EXISTS so it is
    safe to call on a database that already has the tables.
    Matches the raw DDL pattern used by src/core/knowledge_base.py.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                scopes TEXT[] DEFAULT '{}',
                eu_resident BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_login TIMESTAMPTZ
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                refresh_token TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key VARCHAR(500) UNIQUE NOT NULL,
                value TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS webhook_registrations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                url TEXT NOT NULL,
                events TEXT[] DEFAULT '{}',
                secret VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_triggered TIMESTAMPTZ
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_type VARCHAR(100) NOT NULL,
                user_id UUID,
                details JSONB DEFAULT '{}',
                ip_address INET,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        _schema_logger.info("Database schema initialized (all tables created or already exist)")

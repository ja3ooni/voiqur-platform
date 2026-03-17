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

import asyncpg
from fastapi import Request, HTTPException, status


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

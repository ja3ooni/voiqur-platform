"""
Pytest fixtures for Foundation phase tests.

Uses httpx.AsyncClient as the test HTTP client against the FastAPI app.
Pool fixtures connect to TEST_DATABASE_URL and TEST_REDIS_URL from environment
(or fall back to defaults if not set — integration tests skip gracefully if infra is absent).
"""
import os
import asyncio
import pytest
import asyncpg
from httpx import AsyncClient, ASGITransport

# aioredis 2.x uses distutils which was removed in Python 3.12+.
# Use redis.asyncio (redis-py v4+) which is the supported replacement
# and provides the same from_url() API.
try:
    import redis.asyncio as aioredis
    _AIOREDIS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    aioredis = None  # type: ignore[assignment]
    _AIOREDIS_AVAILABLE = False

# Test infrastructure URLs — override with TEST_DATABASE_URL / TEST_REDIS_URL env vars
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/euvoice"))
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379"))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def app():
    """Create the FastAPI app for testing."""
    # load_dotenv() will be called by main.py in production;
    # tests read from environment directly.
    from src.api.app import create_app
    from src.api.config import APIConfig
    application = create_app(APIConfig())
    # Trigger startup events
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://testserver") as client:
        # Yield the client, not just the app, to keep startup context alive
        pass
    return application


@pytest.fixture(scope="session")
async def app_client():
    """Async HTTP test client for the FastAPI app."""
    from src.api.app import create_app
    from src.api.config import APIConfig
    application = create_app(APIConfig())
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="session")
async def db_pool():
    """Real asyncpg pool connected to TEST_DATABASE_URL. Skips if DB unavailable."""
    try:
        pool = await asyncpg.create_pool(dsn=TEST_DATABASE_URL, min_size=1, max_size=3, timeout=5)
        yield pool
        await pool.close()
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available at {TEST_DATABASE_URL}: {exc}")


@pytest.fixture(scope="session")
async def redis_client():
    """Real aioredis client connected to TEST_REDIS_URL. Skips if Redis unavailable."""
    if not _AIOREDIS_AVAILABLE:
        pytest.skip("redis.asyncio not available — install redis>=4.0")
    try:
        client = aioredis.from_url(TEST_REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        await client.ping()
        yield client
        await client.close()
    except Exception as exc:
        pytest.skip(f"Redis not available at {TEST_REDIS_URL}: {exc}")

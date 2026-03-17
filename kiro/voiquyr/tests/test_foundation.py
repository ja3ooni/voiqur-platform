"""
Foundation phase tests — FOUND-01 through FOUND-09.

These stubs are created in Wave 0. Each test is initially marked xfail.
Implementation is filled in as Wave 1 and Wave 2 plans complete their tasks.
"""
import os
import pytest


# ---------------------------------------------------------------------------
# FOUND-01: .env vars loaded into APIConfig
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 1 Plan 01-01 wires load_dotenv() — not yet implemented")
async def test_env_loading():
    """APIConfig reads values from .env file when load_dotenv() is called first."""
    from dotenv import load_dotenv
    load_dotenv()
    from src.api.config import APIConfig
    config = APIConfig()
    # After Wave 1, JWT_SECRET_KEY in .env must appear in config.auth_config.jwt_secret_key
    assert config.auth_config.jwt_secret_key != "your-secret-key-change-in-production"


# ---------------------------------------------------------------------------
# FOUND-02: .env.example exists with all required vars
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 1 Plan 01-01 creates .env.example — not yet implemented")
def test_env_example_exists():
    """kiro/voiquyr/.env.example exists and documents all required environment variables."""
    env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.isfile(env_example_path), ".env.example not found"
    content = open(env_example_path).read()
    required_vars = [
        "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL",
        "MISTRAL_API_KEY", "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "STRIPE_API_KEY",
    ]
    for var in required_vars:
        assert var in content, f"Missing {var} in .env.example"


# ---------------------------------------------------------------------------
# FOUND-03: Redis health check returns "ok"
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 1 Plan 01-02 adds redis probe to /health — not yet implemented")
async def test_redis_connection(app_client):
    """GET /api/v1/health/ returns redis: ok when Redis is reachable."""
    response = await app_client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["redis"] == "ok"


# ---------------------------------------------------------------------------
# FOUND-04: PostgreSQL health check returns "ok"
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 1 Plan 01-02 adds postgres probe to /health — not yet implemented")
async def test_postgres_connection(app_client):
    """GET /api/v1/health/ returns postgres: ok when PostgreSQL is reachable."""
    response = await app_client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["postgres"] == "ok"


# ---------------------------------------------------------------------------
# FOUND-05: DB migration creates required tables
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 2 Plan 01-03 creates schema — not yet implemented")
async def test_schema_tables(db_pool):
    """All required tables exist after app startup schema init."""
    required_tables = ["users", "sessions", "knowledge_items", "webhook_registrations", "audit_logs"]
    async with db_pool.acquire() as conn:
        for table in required_tables:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            assert exists, f"Table '{table}' does not exist"


# ---------------------------------------------------------------------------
# FOUND-06: verify_token() does real DB lookup
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 2 Plan 01-03 replaces mock get_current_user — not yet implemented")
async def test_verify_token_db_lookup(app_client, db_pool):
    """verify_token() returns user data fetched from the users table, not a mock."""
    # Register a user, then call /auth/me and verify the response matches DB row
    reg_resp = await app_client.post("/api/v1/auth/register", json={
        "email": "verify@test.eu", "username": "verifyuser",
        "password": "SecurePass1!", "eu_resident": True
    })
    assert reg_resp.status_code == 201
    login_resp = await app_client.post("/api/v1/auth/login", json={
        "username": "verifyuser", "password": "SecurePass1!"
    })
    token = login_resp.json()["access_token"]
    me_resp = await app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    # Email must match the DB row, not a mock "@example.com" address
    assert me_resp.json()["email"] == "verify@test.eu"


# ---------------------------------------------------------------------------
# FOUND-07: POST /auth/register stores bcrypt hash
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 2 Plan 01-03 creates auth router — not yet implemented")
async def test_register_endpoint(app_client, db_pool):
    """POST /api/v1/auth/register stores a row with a bcrypt-hashed password."""
    response = await app_client.post("/api/v1/auth/register", json={
        "email": "newuser@test.eu", "username": "newuser",
        "password": "SecurePass1!", "eu_resident": True
    })
    assert response.status_code == 201
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT hashed_password FROM users WHERE email = 'newuser@test.eu'")
    assert row is not None
    assert row["hashed_password"].startswith("$2b$")  # bcrypt signature


# ---------------------------------------------------------------------------
# FOUND-08: POST /auth/login returns signed JWT
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 2 Plan 01-03 creates auth router — not yet implemented")
async def test_login_endpoint(app_client):
    """POST /api/v1/auth/login returns an access_token for valid credentials."""
    # Register first
    await app_client.post("/api/v1/auth/register", json={
        "email": "logintest@test.eu", "username": "logintest",
        "password": "SecurePass1!", "eu_resident": True
    })
    response = await app_client.post("/api/v1/auth/login", json={
        "username": "logintest", "password": "SecurePass1!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Token must be decodable
    import jwt
    from src.api.config import APIConfig
    config = APIConfig()
    payload = jwt.decode(data["access_token"], config.auth_config.jwt_secret_key, algorithms=["HS256"])
    assert payload["username"] == "logintest"


# ---------------------------------------------------------------------------
# FOUND-09: /health returns real Redis + PostgreSQL status
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="Wave 1 Plan 01-02 updates health router — not yet implemented")
async def test_health_real_connections(app_client):
    """GET /api/v1/health/ checks include redis and postgres keys."""
    response = await app_client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data["checks"], "health checks missing 'redis' key"
    assert "postgres" in data["checks"], "health checks missing 'postgres' key"

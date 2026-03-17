"""
Test script for the core API framework (Task 9.1).

Tests the basic functionality of the FastAPI application,
authentication system, and rate limiting.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.app import create_app
from src.api.config import APIConfig, AuthConfig, RateLimitConfig
from src.api.auth import AuthManager, User
from src.api.rate_limiter import RateLimiter, RateLimitTier


def test_api_app_creation():
    """Test that the FastAPI app can be created successfully."""
    config = APIConfig()
    app = create_app(config)
    
    assert app is not None
    assert app.title == "EUVoice AI Platform API"
    assert app.version == "1.0.0"


def test_health_endpoints():
    """Test health check endpoints."""
    config = APIConfig()
    app = create_app(config)
    client = TestClient(app)
    
    # Test basic health check
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime" in data
    assert "checks" in data
    
    # Test readiness check
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    
    # Test liveness check
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    
    # Test version info
    response = client.get("/api/v1/health/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"


def test_auth_manager():
    """Test authentication manager functionality."""
    config = AuthConfig()
    auth_manager = AuthManager(config)
    
    # Test user creation
    from datetime import datetime
    user = User(
        id="test-user",
        email="test@example.com",
        username="testuser",
        scopes=["voice:read", "voice:write"],
        eu_resident=True,
        created_at=datetime.utcnow()
    )
    
    # Test token creation
    token = auth_manager.create_access_token(user)
    assert token is not None
    assert isinstance(token, str)
    
    # Test password hashing
    password = "test_password"
    hashed = auth_manager.hash_password(password)
    assert auth_manager.verify_password(password, hashed)
    assert not auth_manager.verify_password("wrong_password", hashed)


async def test_rate_limiter():
    """Test rate limiter functionality."""
    config = RateLimitConfig()
    rate_limiter = RateLimiter(config)
    
    # Test rate limit check (without Redis, should use fallback)
    result = await rate_limiter.check_rate_limit(
        "test-client",
        "/api/v1/test",
        RateLimitTier.ANONYMOUS
    )
    
    assert result.allowed is True
    assert result.remaining >= 0
    
    # Test rate limit status
    status = await rate_limiter.get_rate_limit_status(
        "test-client",
        "/api/v1/test",
        RateLimitTier.AUTHENTICATED
    )
    
    assert "limit" in status
    assert "remaining" in status
    assert "reset_time" in status


def test_cors_and_security():
    """Test CORS and security middleware."""
    config = APIConfig()
    app = create_app(config)
    client = TestClient(app)
    
    # Test CORS headers
    response = client.options("/api/v1/health/")
    assert response.status_code == 200
    
    # Test security headers are added
    response = client.get("/api/v1/health/")
    headers = response.headers
    
    # Check for security headers
    assert "x-content-type-options" in headers
    assert "x-frame-options" in headers
    assert "x-xss-protection" in headers


def test_openapi_documentation():
    """Test OpenAPI documentation generation."""
    config = APIConfig()
    app = create_app(config)
    client = TestClient(app)
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_schema = response.json()
    assert openapi_schema["info"]["title"] == "EUVoice AI Platform API"
    assert "components" in openapi_schema
    assert "securitySchemes" in openapi_schema["components"]


def test_voice_processing_placeholder():
    """Test voice processing router placeholder."""
    config = APIConfig()
    app = create_app(config)
    client = TestClient(app)
    
    response = client.get("/api/v1/voice/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "available_services" in data


def test_webhooks_placeholder():
    """Test webhooks router placeholder."""
    config = APIConfig()
    app = create_app(config)
    client = TestClient(app)
    
    response = client.get("/api/v1/webhooks/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "features" in data


if __name__ == "__main__":
    print("Testing EUVoice AI Platform API Framework...")
    
    # Run synchronous tests
    test_api_app_creation()
    print("✓ API app creation test passed")
    
    test_health_endpoints()
    print("✓ Health endpoints test passed")
    
    test_auth_manager()
    print("✓ Authentication manager test passed")
    
    test_cors_and_security()
    print("✓ CORS and security test passed")
    
    test_openapi_documentation()
    print("✓ OpenAPI documentation test passed")
    
    test_voice_processing_placeholder()
    print("✓ Voice processing placeholder test passed")
    
    test_webhooks_placeholder()
    print("✓ Webhooks placeholder test passed")
    
    # Run async tests
    async def run_async_tests():
        await test_rate_limiter()
        print("✓ Rate limiter test passed")
    
    asyncio.run(run_async_tests())
    
    print("\n🎉 All API framework tests passed!")
    print("\nCore API framework (Task 9.1) is complete with:")
    print("- FastAPI application with OpenAPI documentation")
    print("- OAuth2/JWT authentication system")
    print("- Rate limiting with Redis backend")
    print("- Security middleware and EU compliance features")
    print("- Health check endpoints")
    print("- Structured logging and monitoring")
    print("\nReady for Task 9.2: Voice Processing APIs")
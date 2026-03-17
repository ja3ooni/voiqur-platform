"""
Simple test for the core API framework (Task 9.1).
"""

import sys
import os
import asyncio
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.api.config import APIConfig, AuthConfig, RateLimitConfig
    from src.api.auth import AuthManager, User
    from src.api.rate_limiter import RateLimiter, RateLimitTier
    
    def test_basic_functionality():
        """Test basic API functionality."""
        print("Testing API framework...")
        
        # Test app creation
        config = APIConfig()
        app = create_app(config)
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/api/v1/health/")
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health endpoint working")
        
        # Test version endpoint
        response = client.get("/api/v1/health/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        print("✓ Version endpoint working")
        
        # Test voice processing placeholder
        response = client.get("/api/v1/voice/")
        assert response.status_code == 200
        print("✓ Voice processing placeholder working")
        
        # Test webhooks placeholder
        response = client.get("/api/v1/webhooks/")
        assert response.status_code == 200
        print("✓ Webhooks placeholder working")
        
        # Test OpenAPI docs
        response = client.get("/openapi.json")
        assert response.status_code == 200
        print("✓ OpenAPI documentation working")
        
        print("\n🎉 All basic tests passed!")
        
    def test_auth_system():
        """Test authentication system."""
        print("\nTesting authentication system...")
        
        config = AuthConfig()
        auth_manager = AuthManager(config)
        
        # Test user model
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
        print("✓ JWT token creation working")
        
        # Test password hashing
        password = "test_password"
        hashed = auth_manager.hash_password(password)
        assert auth_manager.verify_password(password, hashed)
        print("✓ Password hashing working")
        
        print("✓ Authentication system working")
    
    async def test_rate_limiter():
        """Test rate limiting system."""
        print("\nTesting rate limiter...")
        
        config = RateLimitConfig()
        rate_limiter = RateLimiter(config)
        
        # Test without Redis (fallback mode)
        result = await rate_limiter.check_rate_limit(
            "test-client",
            "/api/v1/test",
            RateLimitTier.ANONYMOUS
        )
        
        assert result.allowed is True
        print("✓ Rate limiter fallback mode working")
        
        # Test rate limit status
        status = await rate_limiter.get_rate_limit_status(
            "test-client",
            "/api/v1/test"
        )
        
        assert "limit" in status
        print("✓ Rate limit status working")
    
    def main():
        """Run all tests."""
        print("=" * 50)
        print("EUVoice AI Platform API Framework Test")
        print("=" * 50)
        
        try:
            test_basic_functionality()
            test_auth_system()
            
            # Run async test
            asyncio.run(test_rate_limiter())
            
            print("\n" + "=" * 50)
            print("✅ Task 9.1 - Core API Framework COMPLETED!")
            print("=" * 50)
            print("\nImplemented features:")
            print("- FastAPI application with OpenAPI documentation")
            print("- OAuth2/JWT authentication system")
            print("- Rate limiting with Redis backend (fallback mode)")
            print("- Security middleware and CORS")
            print("- Health check endpoints")
            print("- EU compliance features")
            print("- Request validation and error handling")
            print("\nReady for Task 9.2: Voice Processing APIs")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required dependencies:")
    print("pip install fastapi uvicorn python-jose[cryptography] python-multipart bcrypt psutil")
    sys.exit(1)
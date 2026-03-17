"""
API Configuration

Configuration classes for the FastAPI application and its components.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os


class AuthConfig(BaseModel):
    """Authentication configuration."""
    
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    refresh_token_expiration_days: int = 7
    
    # OAuth2 settings
    oauth2_client_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("OAUTH2_CLIENT_ID")
    )
    oauth2_client_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("OAUTH2_CLIENT_SECRET")
    )
    oauth2_redirect_uri: Optional[str] = Field(
        default_factory=lambda: os.getenv("OAUTH2_REDIRECT_URI")
    )
    
    # EU compliance settings
    require_eu_residency: bool = True
    gdpr_compliance_mode: bool = True


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    # Default rate limits (requests per minute)
    default_rate_limit: int = 100
    authenticated_rate_limit: int = 1000
    premium_rate_limit: int = 5000
    
    # Specific endpoint limits
    voice_processing_limit: int = 50  # More restrictive for compute-intensive operations
    webhook_limit: int = 200
    auth_limit: int = 10  # Prevent brute force attacks
    
    # Burst allowance
    burst_multiplier: float = 1.5
    
    # Redis configuration for distributed rate limiting
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    # HTTPS enforcement
    force_https: bool = True
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "https://*.eu",
            "https://*.europa.eu", 
            "https://localhost:3000"  # Development
        ]
    )
    
    # Trusted hosts (EU compliance)
    trusted_hosts: List[str] = Field(
        default_factory=lambda: [
            "*.eu",
            "*.europa.eu",
            "localhost",
            "127.0.0.1",
            "testserver"  # For FastAPI TestClient
        ]
    )
    
    # Security headers
    security_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    )


class APIConfig(BaseModel):
    """Main API configuration."""
    
    # Environment
    environment: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    
    # API settings
    host: str = Field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    
    # Documentation
    enable_docs: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_DOCS", "true").lower() == "true"
    )
    
    # Database
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", 
            "postgresql://user:password@localhost/euvoice"
        )
    )
    
    # Redis
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    
    # Component configurations
    auth_config: AuthConfig = Field(default_factory=AuthConfig)
    rate_limit_config: RateLimitConfig = Field(default_factory=RateLimitConfig)
    security_config: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Webhook configuration
    max_concurrent_webhooks: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_WEBHOOKS", "100"))
    )
    webhook_timeout: int = Field(
        default_factory=lambda: int(os.getenv("WEBHOOK_TIMEOUT", "30"))
    )
    webhook_max_retries: int = Field(
        default_factory=lambda: int(os.getenv("WEBHOOK_MAX_RETRIES", "5"))
    )
    webhook_cleanup_days: int = Field(
        default_factory=lambda: int(os.getenv("WEBHOOK_CLEANUP_DAYS", "30"))
    )
    
    # EU compliance
    eu_data_residency: bool = True
    gdpr_mode: bool = True
    
    # Logging
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed CORS origins."""
        return self.security_config.allowed_origins
    
    @property
    def trusted_hosts(self) -> List[str]:
        """Get trusted hosts."""
        return self.security_config.trusted_hosts
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
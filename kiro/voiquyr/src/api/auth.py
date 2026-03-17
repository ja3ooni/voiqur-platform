"""
Authentication and Authorization System

Implements OAuth2/JWT authentication with EU compliance features.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import asyncpg
import logging

# Redis is optional for token blacklisting
REDIS_AVAILABLE = False

from .config import AuthConfig

logger = logging.getLogger(__name__)

security = HTTPBearer()


class User(BaseModel):
    """User model."""
    
    id: str
    email: str
    username: str
    is_active: bool = True
    is_verified: bool = False
    scopes: List[str] = []
    eu_resident: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """Token payload data."""
    
    user_id: str
    username: str
    scopes: List[str]
    exp: datetime
    iat: datetime
    eu_resident: bool


class AuthManager:
    """
    Authentication and authorization manager.
    
    Handles JWT tokens, OAuth2 flows, and user management with EU compliance.
    """
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis = None
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            # Initialize database pool (placeholder - would connect to actual DB)
            logger.info("Initializing authentication system")
            
            # Redis not configured for this basic implementation
            logger.info("Token blacklisting disabled (Redis not configured)")
            
        except Exception as e:
            logger.error(f"Failed to initialize auth manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.redis:
            await self.redis.close()
    
    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token.
        
        Args:
            user: User object
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.config.jwt_expiration_minutes)
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "scopes": user.scopes,
            "exp": expire,
            "iat": now,
            "eu_resident": user.eu_resident
        }
        
        token = jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
        
        return token
    
    def create_refresh_token(self, user: User) -> str:
        """
        Create JWT refresh token.
        
        Args:
            user: User object
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.config.refresh_token_expiration_days)
        
        payload = {
            "user_id": user.id,
            "type": "refresh",
            "exp": expire,
            "iat": now
        }
        
        token = jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
        
        return token
    
    async def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token data
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Check if token is blacklisted
            if self.redis and await self.redis.get(f"blacklist:{token}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Validate EU residency requirement
            if self.config.require_eu_residency and not payload.get("eu_resident", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="EU residency required"
                )
            
            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                scopes=payload.get("scopes", []),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                eu_resident=payload.get("eu_resident", False)
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """
        Get current authenticated user.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Current user
        """
        token_data = await self.verify_token(credentials.credentials)
        
        # In a real implementation, fetch user from database
        # For now, return a mock user based on token data
        user = User(
            id=token_data.user_id,
            email=f"{token_data.username}@example.com",
            username=token_data.username,
            scopes=token_data.scopes,
            eu_resident=token_data.eu_resident,
            created_at=token_data.iat
        )
        
        return user
    
    def require_scopes(self, required_scopes: List[str]):
        """
        Create dependency that requires specific scopes.
        
        Args:
            required_scopes: List of required scopes
            
        Returns:
            FastAPI dependency function
        """
        async def check_scopes(user: User = Depends(self.get_current_user)) -> User:
            for scope in required_scopes:
                if scope not in user.scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required scope: {scope}"
                    )
            return user
        
        return check_scopes
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        # In a real implementation, this would query the database
        # For now, return a mock user for demonstration
        if username == "demo" and password == "password":
            return User(
                id="demo-user-id",
                email="demo@euvoice.ai",
                username="demo",
                scopes=["voice:read", "voice:write", "webhooks:manage"],
                eu_resident=True,
                created_at=datetime.utcnow()
            )
        
        return None
    
    async def revoke_token(self, token: str):
        """
        Revoke (blacklist) a token.
        
        Args:
            token: JWT token to revoke
        """
        if self.redis:
            # Add token to blacklist with expiration
            token_data = await self.verify_token(token)
            ttl = int((token_data.exp - datetime.utcnow()).total_seconds())
            
            if ttl > 0:
                await self.redis.setex(f"blacklist:{token}", ttl, "1")
    
    async def create_oauth2_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: List[str],
        state: str
    ) -> str:
        """
        Create OAuth2 authorization URL.
        
        Args:
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI
            scopes: Requested scopes
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        # This would integrate with actual OAuth2 providers
        # For now, return a placeholder URL
        scope_str = " ".join(scopes)
        return (
            f"/api/v1/auth/authorize?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scope_str}&"
            f"state={state}&"
            f"response_type=code"
        )
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
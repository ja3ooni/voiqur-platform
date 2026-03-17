"""
Auth Router — /api/v1/auth/

Endpoints:
    POST /register   — Create a new user account
    POST /login      — Authenticate and receive JWT
    GET  /me         — Return the current authenticated user (real DB lookup)
"""
from datetime import datetime
from typing import List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..auth import AuthManager, User
from ..db import get_db

router = APIRouter()
_security = HTTPBearer()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    eu_resident: bool = False
    scopes: List[str] = []


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Helper — fetch auth_manager from app.state
# ---------------------------------------------------------------------------

def _get_auth_manager(request: Request) -> AuthManager:
    return request.app.state.auth_manager


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Register a new user. Stores bcrypt-hashed password in the users table."""
    auth_manager: AuthManager = _get_auth_manager(request)

    # Check for duplicate email or username
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1 OR username = $2",
        body.email, body.username
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )

    hashed = auth_manager.hash_password(body.password)

    row = await conn.fetchrow(
        """
        INSERT INTO users (email, username, hashed_password, scopes, eu_resident)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, email, username, is_active, is_verified, scopes, eu_resident, created_at
        """,
        body.email, body.username, hashed, body.scopes, body.eu_resident
    )

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "username": row["username"],
        "eu_resident": row["eu_resident"],
        "created_at": row["created_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Authenticate with username + password. Returns a signed JWT."""
    auth_manager: AuthManager = _get_auth_manager(request)

    row = await conn.fetchrow(
        "SELECT * FROM users WHERE username = $1 AND is_active = TRUE",
        body.username
    )
    if row is None or not auth_manager.verify_password(body.password, row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Update last_login
    await conn.execute(
        "UPDATE users SET last_login = NOW() WHERE id = $1",
        row["id"]
    )

    user = User(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        is_active=row["is_active"],
        is_verified=row["is_verified"],
        scopes=list(row["scopes"] or []),
        eu_resident=row["eu_resident"],
        created_at=row["created_at"],
        last_login=datetime.utcnow(),
    )

    token = auth_manager.create_access_token(user)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=User)
async def me(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return the currently authenticated user. Performs real DB lookup."""
    auth_manager: AuthManager = _get_auth_manager(request)
    token_data = await auth_manager.verify_token(credentials.credentials)

    row = await conn.fetchrow(
        "SELECT * FROM users WHERE id = $1 AND is_active = TRUE",
        token_data.user_id
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return User(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        is_active=row["is_active"],
        is_verified=row["is_verified"],
        scopes=list(row["scopes"] or []),
        eu_resident=row["eu_resident"],
        created_at=row["created_at"],
        last_login=row["last_login"],
    )

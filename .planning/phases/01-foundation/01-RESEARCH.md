# Phase 1: Foundation - Research

**Researched:** 2026-03-16
**Domain:** FastAPI infrastructure wiring — environment config, asyncpg/aioredis connection pools, Alembic DB migrations, JWT auth endpoints
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | System loads all secrets from environment variables (`.env` + `APIConfig`) | python-dotenv is installed (1.2.2); APIConfig already reads from `os.getenv()` but no `.env` file loading at startup |
| FOUND-02 | `.env.example` documents all required vars (MISTRAL, DEEPGRAM, STRIPE, REDIS, POSTGRES, JWT, TWILIO) | APIConfig fields reveal required var names; needs a new file |
| FOUND-03 | Redis connects via real `aioredis` connection pool (health check passes) | aioredis 2.0.1 is installed; `knowledge_base.py` already shows `aioredis.from_url()` pattern |
| FOUND-04 | PostgreSQL connects via real `asyncpg` connection pool (health check passes) | asyncpg 0.30.0 is installed; `asyncpg.create_pool()` pattern used in `knowledge_base.py` |
| FOUND-05 | DB migration creates tables: users, sessions, knowledge_items, webhook_registrations, audit_logs | Alembic is NOT installed; `_initialize_schema()` in knowledge_base uses raw DDL; needs decision: Alembic vs raw DDL |
| FOUND-06 | `verify_token()` decodes real JWT and looks up user in PostgreSQL | JWT decode is implemented via `python-jose`; DB lookup is mocked (`get_current_user` returns fake user) |
| FOUND-07 | User registration endpoint stores bcrypt-hashed passwords in DB | `hash_password()` with bcrypt exists; no `/auth/register` router or DB write |
| FOUND-08 | User login endpoint returns real JWT token | `create_access_token()` exists; no `/auth/login` router or DB lookup |
| FOUND-09 | `/health` endpoint reports real Redis + PostgreSQL connection status | `/api/v1/health/` exists but checks only `"api": "healthy"` — no real connectivity probes |
</phase_requirements>

---

## Summary

Phase 1 wires existing skeleton code to real infrastructure. The codebase is further along than it might appear: the JWT encode/decode logic in `auth.py` is functional (python-jose 3.5.0 installed), bcrypt hashing works (bcrypt 5.0.0 installed), aioredis 2.0.1 and asyncpg 0.30.0 are installed, and the `knowledge_base.py` already demonstrates the correct connection patterns for both. The gap is not in libraries — it is in plumbing: no `.env` loading at app startup, no auth router with register/login endpoints, no real DB lookup in `get_current_user`, no real connectivity probes in the health endpoint, and no DB schema for user/session tables.

The `auth.py` file uses `import jwt` (PyJWT 2.10.1) but `requirements.txt` lists `python-jose`. Both are installed. This is an inconsistency: the code imports from `jwt` (PyJWT) directly, not from `jose`. This is important for planning — tasks must pick one and be consistent. python-jose wraps PyJWT and adds JWKS/RSA support but the simpler PyJWT direct import will also work for HS256 tokens.

Alembic is not installed and not in `requirements.txt`. The existing codebase uses raw `CREATE TABLE IF NOT EXISTS` DDL executed at startup (in `_initialize_schema()`). This pattern is consistent and usable for Phase 1. Phase 10 adds proper Alembic migrations. For Phase 1, raw DDL startup scripts are the right approach and match existing conventions.

**Primary recommendation:** Wire everything with minimal new code — add `load_dotenv()` at app startup, create `src/api/routers/auth.py` with register/login endpoints that use the already-implemented `hash_password`/`verify_password`/`create_access_token` methods, add real DB lookup in `get_current_user`, initialize aioredis + asyncpg pools in `app.py` startup, and update the health router to actually ping them.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-dotenv | 1.2.2 (installed) | Load `.env` file into `os.environ` at startup | Standard FastAPI pattern; already in venv |
| aioredis | 2.0.1 (installed) | Async Redis connection pool | Already in requirements.txt; used in knowledge_base.py |
| asyncpg | 0.30.0 (installed) | Async PostgreSQL connection pool | Already in requirements.txt; used in knowledge_base.py |
| PyJWT / python-jose | PyJWT 2.10.1 + python-jose 3.5.0 (both installed) | JWT encode/decode | python-jose listed in requirements; PyJWT imported in auth.py |
| bcrypt | 5.0.0 (installed) | Password hashing | Already implemented in `AuthManager.hash_password()` |
| FastAPI | >=0.104.0 (installed) | Web framework + routing | Existing project choice |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | NOT installed | Test runner | Must install for Wave 0 tests |
| pytest-asyncio | NOT installed | Async test support | Must install alongside pytest |
| httpx | installed (fastapi dep) | ASGI test client (TestClient alternative) | FastAPI async test client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT direct import | python-jose | python-jose adds JWKS/key rotation support; PyJWT is simpler; current code uses PyJWT import |
| Raw DDL at startup | Alembic | Alembic tracks migration history; raw DDL is simpler and matches existing knowledge_base.py pattern; Alembic reserved for Phase 10 |

**Installation (missing packages only):**
```bash
# From kiro/voiquyr/ with venv active:
pip install pytest pytest-asyncio httpx
```

---

## Architecture Patterns

### Recommended Project Structure (changes only)
```
kiro/voiquyr/
├── .env                          # NEW: real secrets (git-ignored)
├── .env.example                  # NEW: documented template
├── src/api/
│   ├── app.py                    # MODIFY: add load_dotenv(), pool init
│   ├── auth.py                   # MODIFY: get_current_user -> real DB lookup
│   ├── routers/
│   │   ├── auth.py               # NEW: /auth/register, /auth/login, /auth/me
│   │   └── health.py             # MODIFY: real Redis + PG probes
│   └── db.py                     # NEW: shared asyncpg pool + aioredis pool
└── tests/
    ├── conftest.py               # NEW: pytest fixtures (test DB, app client)
    └── test_foundation.py        # NEW: covers FOUND-01 through FOUND-09
```

### Pattern 1: App-Level Connection Pool (asyncpg)
**What:** Create the asyncpg pool once at startup, store on `app.state`, close at shutdown.
**When to use:** Any endpoint that needs PostgreSQL.
**Example:**
```python
# In app.py startup event
@app.on_event("startup")
async def startup_event():
    app.state.db_pool = await asyncpg.create_pool(config.database_url)
    app.state.redis = aioredis.from_url(config.redis_url)
    # ... rest of startup

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.db_pool.close()
    await app.state.redis.close()
```

### Pattern 2: Dependency-Injected Pool
**What:** FastAPI `Depends()` function that yields a connection from the pool.
**When to use:** Route handlers that need a DB connection.
**Example:**
```python
# In src/api/db.py
async def get_db(request: Request) -> asyncpg.Connection:
    async with request.app.state.db_pool.acquire() as conn:
        yield conn
```

### Pattern 3: Auth Router Registration
**What:** A separate `auth.py` router registered under `/api/v1/auth`.
**When to use:** Always — matches existing project router pattern.
**Example:**
```python
# In app.py
from .routers import auth as auth_router
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])
```

### Pattern 4: python-dotenv Loading
**What:** Call `load_dotenv()` before `APIConfig()` is instantiated.
**When to use:** Entry point — `main.py` or top of `app.py`.
**Example:**
```python
# In src/api/main.py, before create_app()
from dotenv import load_dotenv
load_dotenv()  # loads .env from cwd or searches parent dirs
```

### Anti-Patterns to Avoid
- **Hardcoded fallback secrets:** `os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")` — the fallback should raise an error in production. Use `os.getenv("JWT_SECRET_KEY")` and assert it is not None when `ENVIRONMENT=production`.
- **Creating a new connection per request:** Never do `await asyncpg.connect(...)` inside a route handler. Always use the pool from `app.state`.
- **Two JWT libraries in the same module:** `auth.py` imports `import jwt` (PyJWT) but `requirements.txt` specifies `python-jose`. Pick one. Stick with the direct `import jwt` from PyJWT since that is what the code actually uses.
- **Skipping EU residency check on health endpoint:** The health endpoint must remain unauthenticated (k8s probes), but `/auth/me` and all protected routes must enforce `eu_resident` flag.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | `bcrypt` (already in AuthManager) | Timing-safe comparison, work factor |
| JWT signing/verification | Custom token format | PyJWT `jwt.encode`/`jwt.decode` (already in auth.py) | Handles expiry, algorithm, signature validation |
| Connection pool management | Manual connection tracking | asyncpg pool (`create_pool`) | Built-in max_size, timeout, health checks |
| Redis connection pool | Raw socket management | `aioredis.from_url()` | Auto-reconnect, pipeline support |
| `.env` parsing | Custom env file reader | `python-dotenv` `load_dotenv()` | Handles quoting, comments, multiline |

**Key insight:** Almost all the code for this phase already exists in `auth.py` and `knowledge_base.py` — the work is wiring, not implementing new logic.

---

## Common Pitfalls

### Pitfall 1: JWT Library Mismatch
**What goes wrong:** `auth.py` does `import jwt` (PyJWT) and calls `jwt.encode()` / `jwt.decode()`. If someone switches to `python-jose` they would need `from jose import jwt` — same namespace, different module. Mixing both causes `AttributeError` at runtime.
**Why it happens:** Both libraries are installed; `requirements.txt` lists python-jose but the implementation file imports PyJWT.
**How to avoid:** Keep `import jwt` (PyJWT). PyJWT's `jwt.decode()` raises `jwt.ExpiredSignatureError` and `jwt.JWTError` exactly as the code already catches them.
**Warning signs:** `jwt.JWTError` not found (python-jose uses `jose.exceptions.JWTError`).

### Pitfall 2: asyncpg Pool Not Available Before First Request
**What goes wrong:** If `app.state.db_pool` is accessed before the `startup` event fires (e.g., in middleware or module-level code), it raises `AttributeError`.
**Why it happens:** FastAPI's `on_event("startup")` runs after middleware setup but before first request. Module-level access happens at import time.
**How to avoid:** Only access `request.app.state.db_pool` inside route handlers or async dependency functions, never at module level.
**Warning signs:** `AttributeError: 'State' object has no attribute 'db_pool'` on first request.

### Pitfall 3: aioredis 2.x API vs 1.x
**What goes wrong:** aioredis 2.x (installed: 2.0.1) has a completely different API from 1.x. The correct factory is `aioredis.from_url(url)` which returns a `Redis` client directly (not a pool object with `.get_connection()`).
**Why it happens:** Many StackOverflow answers reference aioredis 1.x patterns (`await aioredis.create_redis_pool()`).
**How to avoid:** Use `aioredis.from_url(url)` — this is what `knowledge_base.py` already uses correctly.
**Warning signs:** `AttributeError: module 'aioredis' has no attribute 'create_redis_pool'`.

### Pitfall 4: asyncpg DSN Format
**What goes wrong:** asyncpg requires `postgresql://` scheme. The default in `APIConfig` is `postgresql://user:password@localhost/euvoice` which lacks the port. If PostgreSQL is on a non-default port this silently fails.
**Why it happens:** Port defaults to 5432 when omitted — fine for localhost dev.
**How to avoid:** Document the full DSN format in `.env.example`: `postgresql://user:password@localhost:5432/euvoice`.
**Warning signs:** `asyncpg.exceptions.ConnectionFailureError` on startup.

### Pitfall 5: No Auth Router Registered
**What goes wrong:** `app.py` does not import or register any auth router. `/auth/register` and `/auth/login` do not exist as endpoints — they will return 404.
**Why it happens:** Auth functionality only exists as class methods in `auth.py`, not as HTTP endpoints.
**How to avoid:** Create `src/api/routers/auth.py` and register it in `app.py` as shown in Architecture Pattern 3.
**Warning signs:** `POST /api/v1/auth/login` returns 404.

### Pitfall 6: load_dotenv() Ordering
**What goes wrong:** `APIConfig()` reads `os.getenv()` at instantiation. If `load_dotenv()` is called after `APIConfig()` is created, the `.env` values are not present when the config object reads them.
**Why it happens:** `APIConfig` uses `default_factory=lambda: os.getenv(...)` which is evaluated at `APIConfig()` call time, not at class definition time.
**How to avoid:** Call `load_dotenv()` in `main.py` before `create_app(config)`, or at the very top of `app.py` before any config instantiation.
**Warning signs:** Env vars in `.env` are ignored; server uses fallback defaults.

### Pitfall 7: `users` Table Does Not Exist
**What goes wrong:** `knowledge_base.py`'s `_initialize_schema()` creates `knowledge_items` and `knowledge_conflicts` tables, but no `users`, `sessions`, `webhook_registrations`, or `audit_logs` tables. Register endpoint fails with `UndefinedTableError`.
**Why it happens:** The schema initialization is only in `SharedKnowledgeBase`, not in a shared app-level init.
**How to avoid:** Create a `src/api/db.py` module with a `create_schema()` coroutine that runs on app startup and creates all required tables.
**Warning signs:** `asyncpg.exceptions.UndefinedTableError: relation "users" does not exist`.

---

## Code Examples

### Load .env at startup
```python
# Source: python-dotenv docs (dotenv 1.2.2 installed)
# In kiro/voiquyr/src/api/main.py — before create_app()
from dotenv import load_dotenv
load_dotenv()  # searches for .env starting from cwd, then parent dirs
```

### asyncpg pool creation
```python
# Source: asyncpg 0.30.0 installed; pattern from knowledge_base.py line 234
import asyncpg
pool = await asyncpg.create_pool(
    dsn=config.database_url,
    min_size=2,
    max_size=10
)
```

### aioredis 2.x connection
```python
# Source: aioredis 2.0.1 installed; pattern from knowledge_base.py line 229
import aioredis
redis = aioredis.from_url(config.redis_url, decode_responses=True)
await redis.ping()  # verify connectivity
```

### users table DDL (raw, matching existing project pattern)
```sql
-- Create once at app startup via asyncpg
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
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### JWT decode (existing pattern in auth.py — PyJWT)
```python
# Source: existing kiro/voiquyr/src/api/auth.py lines 161-192
import jwt  # PyJWT — already installed
payload = jwt.decode(
    token,
    self.config.jwt_secret_key,
    algorithms=[self.config.jwt_algorithm]  # "HS256"
)
```

### Real DB lookup in get_current_user
```python
# Pattern to replace mock in auth.py get_current_user()
async with request.app.state.db_pool.acquire() as conn:
    row = await conn.fetchrow(
        "SELECT * FROM users WHERE id = $1 AND is_active = TRUE",
        token_data.user_id
    )
if row is None:
    raise HTTPException(status_code=401, detail="User not found")
```

### Health endpoint with real probes
```python
# Pattern for health.py — replace hardcoded "healthy" strings
async def health_check(request: Request):
    checks = {}
    try:
        await request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
    return checks
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| aioredis 1.x `create_redis_pool()` | aioredis 2.x `from_url()` | 2021 (v2.0) | Many old code samples are wrong; use 2.x API |
| PyJWT 1.x `jwt.decode(token, key)` | PyJWT 2.x `jwt.decode(token, key, algorithms=[...])` | 2021 (v2.0) | `algorithms` parameter is now required |
| FastAPI `@app.on_event("startup")` | FastAPI `lifespan` context manager | 0.95+ | `on_event` is deprecated but still works; Phase 1 can keep it |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Deprecated in favor of `lifespan` context manager since FastAPI 0.95. Current code uses it; acceptable for Phase 1, can migrate in Phase 10.
- aioredis 1.x patterns: Do not use. Only 2.x patterns (`from_url`, no `create_redis_pool`).

---

## Open Questions

1. **PyJWT vs python-jose — which is authoritative?**
   - What we know: Both installed; `requirements.txt` lists `python-jose`; `auth.py` imports PyJWT.
   - What's unclear: Whether any other module uses python-jose directly.
   - Recommendation: Keep PyJWT import in `auth.py` (it works, tests pass); add a comment explaining the discrepancy; clean up in a future phase.

2. **asyncpg pool on `app.state` vs dedicated `db.py` module**
   - What we know: knowledge_base.py creates its own pool; app.py creates a separate webhook_service with its own pool.
   - What's unclear: Whether to create a single shared pool or let each subsystem own its pool.
   - Recommendation: Create a single shared pool on `app.state.db_pool` for auth operations. knowledge_base and webhook_service may continue to own their own pools — do not refactor them in Phase 1.

3. **EU residency enforcement on register endpoint**
   - What we know: `AuthConfig.require_eu_residency = True`; token verify checks `eu_resident` flag.
   - What's unclear: How to determine EU residency at registration time (IP geolocation? self-declaration?).
   - Recommendation: Accept `eu_resident: bool` as a request body field from the client for Phase 1 (self-declaration). Proper IP-based enforcement is v2.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (NOT YET INSTALLED — Wave 0 gap) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest tests/test_foundation.py -x -v` |
| Full suite command | `pytest -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | `.env` vars loaded into APIConfig | unit | `pytest tests/test_foundation.py::test_env_loading -x` | Wave 0 |
| FOUND-02 | `.env.example` file exists with all required vars | smoke | `pytest tests/test_foundation.py::test_env_example_exists -x` | Wave 0 |
| FOUND-03 | Redis health check returns "ok" | integration | `pytest tests/test_foundation.py::test_redis_connection -x` | Wave 0 |
| FOUND-04 | PostgreSQL health check returns "ok" | integration | `pytest tests/test_foundation.py::test_postgres_connection -x` | Wave 0 |
| FOUND-05 | DB tables exist after schema init | integration | `pytest tests/test_foundation.py::test_schema_tables -x` | Wave 0 |
| FOUND-06 | `verify_token()` returns user from DB | unit | `pytest tests/test_foundation.py::test_verify_token_db_lookup -x` | Wave 0 |
| FOUND-07 | `POST /auth/register` stores bcrypt hash | integration | `pytest tests/test_foundation.py::test_register_endpoint -x` | Wave 0 |
| FOUND-08 | `POST /auth/login` returns signed JWT | integration | `pytest tests/test_foundation.py::test_login_endpoint -x` | Wave 0 |
| FOUND-09 | `GET /health` returns redis+postgres status | integration | `pytest tests/test_foundation.py::test_health_real_connections -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_foundation.py -x -v`
- **Per wave merge:** `pytest -v` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — pytest fixtures: test DB URL, asyncpg pool, test FastAPI client
- [ ] `tests/test_foundation.py` — covers FOUND-01 through FOUND-09
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` — none of these are in the venv currently
- [ ] `pytest.ini` or `pyproject.toml` — configure `asyncio_mode = auto` for pytest-asyncio

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `kiro/voiquyr/src/api/auth.py` — confirmed mock patterns and existing JWT/bcrypt implementation
- Direct file inspection: `kiro/voiquyr/src/api/config.py` — confirmed env var reading pattern
- Direct file inspection: `kiro/voiquyr/src/core/knowledge_base.py` — confirmed aioredis 2.x and asyncpg patterns
- Direct file inspection: `kiro/voiquyr/src/api/routers/health.py` — confirmed no real probes
- Direct file inspection: `kiro/voiquyr/src/api/app.py` — confirmed no auth router registered
- Venv inspection: confirmed installed packages (aioredis 2.0.1, asyncpg 0.30.0, PyJWT 2.10.1, python-jose 3.5.0, bcrypt 5.0.0, python-dotenv 1.2.2)
- Venv Scripts inspection: confirmed pytest, alembic, passlib are NOT installed

### Secondary (MEDIUM confidence)
- aioredis 2.x API: `from_url()` pattern cross-verified against knowledge_base.py which already uses it correctly
- PyJWT 2.x `algorithms` required parameter: confirmed by existing `auth.py` code which passes `algorithms=[self.config.jwt_algorithm]`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via venv inspection and existing code
- Architecture: HIGH — patterns derived from existing working code in same project
- Pitfalls: HIGH — identified from direct code inspection (actual mock/missing implementations found)

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable libraries; risk of aioredis/asyncpg minor API changes is low)

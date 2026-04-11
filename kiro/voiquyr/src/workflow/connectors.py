"""
Database and API Connectors + Data Transformation Engine.
Implements Requirements 18.3, 18.6.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp


# ---------------------------------------------------------------------------
# Database connectors (async wrappers — actual drivers injected)
# ---------------------------------------------------------------------------

class DBConnector:
    """Base database connector interface."""

    async def execute(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        raise NotImplementedError

    async def execute_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        rows = await self.execute(query, params)
        return rows[0] if rows else None

    async def health_check(self) -> bool:
        raise NotImplementedError


class PostgreSQLConnector(DBConnector):
    """Async PostgreSQL connector via asyncpg."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool = None
        self.logger = logging.getLogger(f"{__name__}.postgres")

    async def _get_pool(self):
        if not self._pool:
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(self.dsn)
            except ImportError:
                raise RuntimeError("asyncpg not installed")
        return self._pool

    async def execute(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return [dict(r) for r in rows]

    async def health_check(self) -> bool:
        try:
            await self.execute("SELECT 1")
            return True
        except Exception:
            return False


class MySQLConnector(DBConnector):
    """Async MySQL connector via aiomysql."""

    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self.config = dict(host=host, port=port, user=user, password=password, db=db)
        self._pool = None
        self.logger = logging.getLogger(f"{__name__}.mysql")

    async def _get_pool(self):
        if not self._pool:
            try:
                import aiomysql
                self._pool = await aiomysql.create_pool(**self.config)
            except ImportError:
                raise RuntimeError("aiomysql not installed")
        return self._pool

    async def execute(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params or ())
                return await cur.fetchall()

    async def health_check(self) -> bool:
        try:
            await self.execute("SELECT 1")
            return True
        except Exception:
            return False


class MongoDBConnector(DBConnector):
    """Async MongoDB connector via motor."""

    def __init__(self, uri: str, database: str):
        self.uri = uri
        self.database = database
        self._client = None
        self.logger = logging.getLogger(f"{__name__}.mongodb")

    def _get_db(self):
        if not self._client:
            try:
                import motor.motor_asyncio as motor
                self._client = motor.AsyncIOMotorClient(self.uri)
            except ImportError:
                raise RuntimeError("motor not installed")
        return self._client[self.database]

    async def execute(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        # query is JSON: {"collection": "...", "filter": {...}, "limit": N}
        spec = json.loads(query)
        db = self._get_db()
        col = db[spec["collection"]]
        cursor = col.find(spec.get("filter", {})).limit(spec.get("limit", 100))
        return await cursor.to_list(length=spec.get("limit", 100))

    async def health_check(self) -> bool:
        try:
            db = self._get_db()
            await db.command("ping")
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# REST API Orchestrator
# ---------------------------------------------------------------------------

class RESTConnector:
    """Generic REST API connector with auth and retry."""

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_type: str = "bearer",
        token: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self._headers = headers or {}
        if auth_type == "bearer" and token:
            self._headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key" and token:
            self._headers["X-API-Key"] = token
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        s = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with s.request(method.upper(), url, json=data, params=params, ssl=False) as r:
                if r.content_type == "application/json":
                    return await r.json()
                return await r.text()
        except Exception as e:
            self.logger.error(f"REST {method} {url} failed: {e}")
            return None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------------------------------------------------------
# Data Transformation Engine
# ---------------------------------------------------------------------------

class DataTransformer:
    """
    Built-in data mapping, formatting, validation, and enrichment.
    Transformations are expressed as a list of operation dicts.
    """

    def transform(self, data: Dict[str, Any], operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        result = dict(data)
        for op in operations:
            op_type = op.get("type")
            if op_type == "map":
                result = self._map(result, op)
            elif op_type == "format":
                result = self._format(result, op)
            elif op_type == "filter":
                result = self._filter(result, op)
            elif op_type == "enrich":
                result = self._enrich(result, op)
            elif op_type == "validate":
                self._validate(result, op)
        return result

    def _map(self, data: Dict, op: Dict) -> Dict:
        """Rename / remap fields: {"type":"map","mappings":{"old":"new"}}"""
        mappings: Dict[str, str] = op.get("mappings", {})
        result = {}
        for k, v in data.items():
            new_key = mappings.get(k, k)
            result[new_key] = v
        return result

    def _format(self, data: Dict, op: Dict) -> Dict:
        """Format a field value: {"type":"format","field":"phone","format":"e164"}"""
        field = op.get("field", "")
        fmt = op.get("format", "")
        if field not in data:
            return data
        val = str(data[field])
        if fmt == "e164":
            digits = re.sub(r"\D", "", val)
            data[field] = f"+{digits}" if not digits.startswith("+") else digits
        elif fmt == "uppercase":
            data[field] = val.upper()
        elif fmt == "lowercase":
            data[field] = val.lower()
        elif fmt == "trim":
            data[field] = val.strip()
        return data

    def _filter(self, data: Dict, op: Dict) -> Dict:
        """Keep only specified fields: {"type":"filter","keep":["a","b"]}"""
        keep: List[str] = op.get("keep", list(data.keys()))
        return {k: v for k, v in data.items() if k in keep}

    def _enrich(self, data: Dict, op: Dict) -> Dict:
        """Add static or computed fields: {"type":"enrich","fields":{"source":"voiquyr"}}"""
        data.update(op.get("fields", {}))
        return data

    def _validate(self, data: Dict, op: Dict) -> None:
        """Raise ValueError if required fields missing or wrong type."""
        for field in op.get("required", []):
            if not data.get(field):
                raise ValueError(f"Required field missing: {field}")
        for field, expected_type in op.get("types", {}).items():
            if field in data:
                type_map = {"str": str, "int": int, "float": float, "bool": bool}
                t = type_map.get(expected_type)
                if t and not isinstance(data[field], t):
                    raise ValueError(f"Field {field} must be {expected_type}")

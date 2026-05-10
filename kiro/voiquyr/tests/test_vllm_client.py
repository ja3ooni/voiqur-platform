"""
Tests for vLLM client and OpenAI-compatible API endpoints.

SELF-02: Self-hosted LLM API endpoint with OpenAI-compatible interface.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.vllm_client import VLLMClient, VLLMError, get_vllm_client, set_vllm_client


# ---------------------------------------------------------------------------
# VLLMClient unit tests
# ---------------------------------------------------------------------------


class TestVLLMClientInit:
    def test_default_values(self):
        client = VLLMClient()
        assert client.base_url == "http://localhost:8000"
        assert client.model == "mistral-7b"
        assert client.timeout == 120

    def test_trailing_slash_stripped(self):
        client = VLLMClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_custom_params(self):
        client = VLLMClient(base_url="http://gpu-box:9000", model="mistral-large", timeout=60)
        assert client.base_url == "http://gpu-box:9000"
        assert client.model == "mistral-large"
        assert client.timeout == 60


def _make_mock_session(post_resp=None, get_resp=None):
    """Build a mock aiohttp session with post/get returning context managers."""
    mock_session = AsyncMock()

    if post_resp is not None:
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=post_resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=ctx)

    if get_resp is not None:
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=get_resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=ctx)

    return mock_session


class TestVLLMClientComplete:
    """Completion endpoint — success and error paths."""

    @pytest.mark.asyncio
    async def test_complete_success(self):
        client = VLLMClient()
        mock_resp_data = {
            "id": "cmpl-1",
            "object": "text_completion",
            "choices": [{"text": "Paris", "index": 0}],
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_resp_data)

        client._get_session = AsyncMock(return_value=_make_mock_session(post_resp=mock_response))

        result = await client.complete("The capital of France is", stream=False)
        assert result == mock_resp_data

    @pytest.mark.asyncio
    async def test_complete_raises_vllm_error_on_non_200(self):
        client = VLLMClient()

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        client._get_session = AsyncMock(return_value=_make_mock_session(post_resp=mock_response))

        with pytest.raises(VLLMError, match="vLLM error: 500"):
            await client.complete("test prompt", stream=False)


class TestVLLMClientChatComplete:
    """Chat completion endpoint."""

    @pytest.mark.asyncio
    async def test_chat_complete_success(self):
        client = VLLMClient()
        mock_resp_data = {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "choices": [{"message": {"role": "assistant", "content": "Hello!"}, "index": 0}],
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_resp_data)

        client._get_session = AsyncMock(return_value=_make_mock_session(post_resp=mock_response))

        messages = [{"role": "user", "content": "Say hello"}]
        result = await client.chat_complete(messages, stream=False)
        assert result["object"] == "chat.completion"

    @pytest.mark.asyncio
    async def test_chat_complete_raises_on_error(self):
        client = VLLMClient()

        mock_response = AsyncMock()
        mock_response.status = 422
        mock_response.text = AsyncMock(return_value="Unprocessable Entity")

        client._get_session = AsyncMock(return_value=_make_mock_session(post_resp=mock_response))

        with pytest.raises(VLLMError):
            await client.chat_complete([{"role": "user", "content": "hi"}], stream=False)


class TestVLLMClientHealth:
    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self):
        client = VLLMClient()

        mock_response = AsyncMock()
        mock_response.status = 200

        client._get_session = AsyncMock(return_value=_make_mock_session(get_resp=mock_response))

        result = await client.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_exception(self):
        client = VLLMClient()

        async def raise_exc():
            raise Exception("Connection refused")

        client._get_session = AsyncMock(side_effect=Exception("Connection refused"))

        result = await client.health_check()
        assert result is False


class TestVLLMClientGlobal:
    """Global singleton helpers."""

    def test_set_and_get_client(self):
        custom_client = VLLMClient(base_url="http://custom:9999")
        set_vllm_client(custom_client)
        retrieved = get_vllm_client()
        assert retrieved is custom_client

    def teardown_method(self):
        # Reset global state
        set_vllm_client(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# API router integration tests (using FastAPI TestClient)
# ---------------------------------------------------------------------------


class TestVLLMRouter:
    """Test the /v1/* endpoints via FastAPI TestClient."""

    def _make_app(self, vllm_enabled: bool = False):
        from fastapi.testclient import TestClient

        from src.api.app import create_app
        from src.api.config import APIConfig

        config = APIConfig(vllm_enabled=vllm_enabled, vllm_url="http://localhost:8001")
        app = create_app(config)
        return TestClient(app, raise_server_exceptions=False)

    def test_health_endpoint_when_disabled(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")

        config = APIConfig(vllm_enabled=False)
        test_app.state.config = config

        client = TestClient(test_app)
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is False
        assert body["healthy"] is False

    def test_health_endpoint_when_enabled_server_unreachable(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")

        config = APIConfig(vllm_enabled=True, vllm_url="http://localhost:8001")
        test_app.state.config = config

        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=False)

        with patch("src.agents.vllm_client.get_vllm_client", return_value=mock_client):
            client = TestClient(test_app)
            resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["healthy"] is False

    def test_completions_returns_503_when_disabled(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")
        test_app.state.config = APIConfig(vllm_enabled=False)

        client = TestClient(test_app)
        resp = client.post("/v1/completions", json={"model": "mistral-7b", "prompt": "hello"})
        assert resp.status_code == 503

    def test_chat_completions_returns_503_when_disabled(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")
        test_app.state.config = APIConfig(vllm_enabled=False)

        client = TestClient(test_app)
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "mistral-7b", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 503

    def test_completions_success_when_enabled(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")
        test_app.state.config = APIConfig(vllm_enabled=True)

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(
            return_value={
                "id": "cmpl-1",
                "object": "text_completion",
                "choices": [{"text": "answer", "index": 0}],
            }
        )

        with patch("src.agents.vllm_client.get_vllm_client", return_value=mock_client):
            client = TestClient(test_app)
            resp = client.post(
                "/v1/completions",
                json={"model": "mistral-7b", "prompt": "hello", "stream": False},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "text_completion"

    def test_chat_completions_success_when_enabled(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.vllm import router
        from src.api.config import APIConfig

        test_app = FastAPI()
        test_app.include_router(router, prefix="/v1")
        test_app.state.config = APIConfig(vllm_enabled=True)

        mock_client = AsyncMock()
        mock_client.chat_complete = AsyncMock(
            return_value={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "choices": [{"message": {"role": "assistant", "content": "Hi!"}, "index": 0}],
            }
        )

        with patch("src.agents.vllm_client.get_vllm_client", return_value=mock_client):
            client = TestClient(test_app)
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "mistral-7b",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "chat.completion"

    def test_api_config_has_vllm_fields(self):
        from src.api.config import APIConfig
        config = APIConfig()
        assert hasattr(config, "vllm_url")
        assert hasattr(config, "vllm_model")
        assert hasattr(config, "vllm_enabled")
        assert hasattr(config, "vllm_timeout")

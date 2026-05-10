"""
vLLM Client for self-hosted Mistral inference.

Provides OpenAI-compatible API client for vLLM server.
"""

import json
import logging
from typing import Any, AsyncIterator, Optional

import aiohttp

logger = logging.getLogger(__name__)


class VLLMClient:
    """Client for vLLM self-hosted inference server."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str = "mistral-7b",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs
    ) -> dict | AsyncIterator[dict]:
        """
        Send completion request to vLLM server.

        OpenAI-compatible /v1/completions endpoint.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }

        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/v1/completions",
            json=payload,
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise VLLMError(f"vLLM error: {response.status} — {error}")

            if stream:
                return self._stream_response(response)
            return await response.json()

    async def chat_complete(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs
    ) -> dict | AsyncIterator[dict]:
        """
        Send chat completion request to vLLM server.

        OpenAI-compatible /v1/chat/completions endpoint.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }

        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise VLLMError(f"vLLM error: {response.status} — {error}")

            if stream:
                return self._stream_response(response)
            return await response.json()

    async def _stream_response(
        self,
        response: aiohttp.ClientResponse
    ) -> AsyncIterator[dict]:
        """Parse streaming SSE response."""
        async for line in response.content:
            line = line.decode("utf-8").strip()
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                yield json.loads(data)

    async def health_check(self) -> bool:
        """Check if vLLM server is healthy."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"vLLM health check failed: {e}")
            return False

    async def models(self) -> list[dict]:
        """List available models."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/v1/models") as response:
            if response.status != 200:
                return []
            data = await response.json()
            return data.get("data", [])


class VLLMError(Exception):
    """vLLM client error."""
    pass


# Global client instance
_vllm_client: Optional[VLLMClient] = None


def get_vllm_client() -> VLLMClient:
    """Get global vLLM client instance."""
    global _vllm_client
    if _vllm_client is None:
        from src.api.config import APIConfig
        config = APIConfig()
        vllm_url = getattr(config, "vllm_url", "http://localhost:8000")
        vllm_model = getattr(config, "vllm_model", "mistral-7b")
        _vllm_client = VLLMClient(base_url=vllm_url, model=vllm_model)
    return _vllm_client


def set_vllm_client(client: VLLMClient) -> None:
    """Set global vLLM client instance."""
    global _vllm_client
    _vllm_client = client
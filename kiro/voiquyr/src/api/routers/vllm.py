"""
vLLM API Router — OpenAI-compatible endpoints for self-hosted Mistral inference.

Provides /v1/completions and /v1/chat/completions endpoints that proxy
requests to the local vLLM server.

Requirements: SELF-02
"""

import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..config import APIConfig

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CompletionRequest(BaseModel):
    """OpenAI-compatible /v1/completions request body."""

    model: str = "mistral-7b"
    prompt: str
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False
    stop: Optional[list[str]] = None
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=16)


class ChatMessage(BaseModel):
    """A single chat turn."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible /v1/chat/completions request body."""

    model: str = "mistral-7b"
    messages: list[ChatMessage]
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False
    stop: Optional[list[str]] = None
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=16)


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def get_config(request: Request) -> APIConfig:
    """Pull API config from app state."""
    return request.app.state.config


def _require_vllm(config: APIConfig) -> None:
    """Raise 503 if vLLM is not enabled."""
    if not config.vllm_enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "Self-hosted vLLM is not enabled. "
                "Set VLLM_ENABLED=true and ensure the vLLM server is running."
            ),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/models")
async def list_models(
    config: APIConfig = Depends(get_config),
) -> dict:
    """
    List models available on the vLLM server.

    Returns OpenAI-compatible model list.
    """
    _require_vllm(config)

    from ...agents.vllm_client import get_vllm_client

    client = get_vllm_client()
    healthy = await client.health_check()
    if not healthy:
        raise HTTPException(
            status_code=503,
            detail="vLLM server is not reachable.",
        )

    models = await client.models()
    return {"object": "list", "data": models}


@router.post("/completions")
async def create_completion(
    body: CompletionRequest,
    config: APIConfig = Depends(get_config),
) -> Any:
    """
    OpenAI-compatible text completion via self-hosted vLLM.

    When `stream=true`, returns a Server-Sent Events stream.
    """
    _require_vllm(config)

    from ...agents.vllm_client import get_vllm_client

    client = get_vllm_client()

    kwargs: dict = {"stop": body.stop, "top_p": body.top_p, "n": body.n}
    # Remove None values — vLLM is strict about unexpected null fields
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        result = await client.complete(
            prompt=body.prompt,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            stream=body.stream,
            **kwargs,
        )
    except Exception as exc:
        logger.error("vLLM completion failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"vLLM error: {exc}") from exc

    if body.stream:
        return StreamingResponse(
            _sse_wrap(result),
            media_type="text/event-stream",
        )
    return result


@router.post("/chat/completions")
async def create_chat_completion(
    body: ChatCompletionRequest,
    config: APIConfig = Depends(get_config),
) -> Any:
    """
    OpenAI-compatible chat completion via self-hosted vLLM.

    When `stream=true`, returns a Server-Sent Events stream.
    """
    _require_vllm(config)

    from ...agents.vllm_client import get_vllm_client

    client = get_vllm_client()

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    kwargs: dict = {"stop": body.stop, "top_p": body.top_p, "n": body.n}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        result = await client.chat_complete(
            messages=messages,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            stream=body.stream,
            **kwargs,
        )
    except Exception as exc:
        logger.error("vLLM chat completion failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"vLLM error: {exc}") from exc

    if body.stream:
        return StreamingResponse(
            _sse_wrap(result),
            media_type="text/event-stream",
        )
    return result


@router.get("/health")
async def vllm_health(
    config: APIConfig = Depends(get_config),
) -> dict:
    """
    Check health of the vLLM server.

    Returns status and whether vLLM is enabled and reachable.
    """
    if not config.vllm_enabled:
        return {"enabled": False, "healthy": False}

    from ...agents.vllm_client import get_vllm_client

    client = get_vllm_client()
    healthy = await client.health_check()
    return {"enabled": True, "healthy": healthy, "url": config.vllm_url}


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------


async def _sse_wrap(iterator: AsyncIterator[dict]) -> AsyncIterator[str]:
    """Wrap an async dict iterator as SSE lines."""
    import json

    async for chunk in iterator:
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"

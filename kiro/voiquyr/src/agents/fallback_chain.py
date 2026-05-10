"""
Model Fallback Chain for LLM inference.

Implements circuit breaker pattern for automatic failover between
Mistral API and self-hosted vLLM.

Requirements: SELF-04
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """LLM model provider types."""
    MISTRAL_API = "mistral_api"
    VLLM = "vllm"
    LOCAL = "local"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, not calling
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class ModelHealth:
    """Health status for a model provider."""
    provider: ModelProvider
    last_success: float = 0.0
    last_failure: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    latency_avg_ms: float = 0.0


@dataclass
class FallbackConfig:
    """Fallback chain configuration."""
    timeout_seconds: float = 30.0
    max_retries: int = 2
    failure_threshold: int = 3
    recovery_timeout: int = 60
    circuit_open_timeout: int = 300


class FallbackOrchestrator:
    """Orchestrates fallback between model providers."""

    def __init__(self, config: Optional[FallbackConfig] = None) -> None:
        self.config = config or FallbackConfig()
        self._circuit_state = CircuitState.CLOSED
        self._circuit_opened_at: float = 0.0
        self._health: dict[ModelProvider, ModelHealth] = {
            ModelProvider.MISTRAL_API: ModelHealth(provider=ModelProvider.MISTRAL_API),
            ModelProvider.VLLM: ModelHealth(provider=ModelProvider.VLLM),
        }

    async def complete(
        self,
        prompt: str,
        provider_order: Optional[list[ModelProvider]] = None,
        **kwargs: Any,
    ) -> dict:
        """
        Execute completion with fallback chain.

        Tries providers in order until one succeeds.
        Raises FallbackError if all providers fail.
        """
        if provider_order is None:
            provider_order = [ModelProvider.MISTRAL_API, ModelProvider.VLLM]

        last_error: Optional[Exception] = None

        for provider in provider_order:
            if not self._can_attempt(provider):
                logger.debug("Skipping %s — circuit open", provider)
                continue

            try:
                result = await self._call_provider(provider, prompt, **kwargs)
                self._record_success(provider)
                logger.info("Completion succeeded via %s", provider)
                return result
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"{provider} timed out")
                self._record_failure(provider)
                logger.warning("%s timed out, trying next...", provider)
            except Exception as exc:
                last_error = exc
                self._record_failure(provider)
                logger.warning("%s failed: %s, trying next...", provider, exc)

        self._open_circuit()
        raise FallbackError(f"All providers failed. Last error: {last_error}")

    async def _call_provider(
        self,
        provider: ModelProvider,
        prompt: str,
        **kwargs: Any,
    ) -> dict:
        """Call a specific provider and track latency."""
        start_time = time.monotonic()

        if provider == ModelProvider.MISTRAL_API:
            from src.agents.llm_agent import generate_response
            result = await asyncio.wait_for(
                generate_response(prompt, **kwargs),
                timeout=self.config.timeout_seconds,
            )
        elif provider == ModelProvider.VLLM:
            from src.agents.vllm_client import get_vllm_client
            client = get_vllm_client()
            result = await asyncio.wait_for(
                client.complete(prompt, **kwargs),
                timeout=self.config.timeout_seconds,
            )
        else:
            raise FallbackError(f"Unknown provider: {provider}")

        latency = (time.monotonic() - start_time) * 1000
        health = self._health[provider]
        # Exponential moving average (10% new, 90% history)
        health.latency_avg_ms = health.latency_avg_ms * 0.9 + latency * 0.1
        return result

    def _can_attempt(self, provider: ModelProvider) -> bool:
        """Return True if provider can be called given current circuit state."""
        if self._circuit_state == CircuitState.CLOSED:
            return True

        if self._circuit_state == CircuitState.OPEN:
            elapsed = time.time() - self._circuit_opened_at
            if elapsed > self.config.circuit_open_timeout:
                self._circuit_state = CircuitState.HALF_OPEN
                logger.info("Circuit half-open, testing providers...")
                return True
            return False

        # HALF_OPEN: allow one attempt
        return True

    def _record_success(self, provider: ModelProvider) -> None:
        """Record a successful call; reset failure count; close circuit if half-open."""
        health = self._health[provider]
        health.last_success = time.time()
        health.success_count += 1
        health.failure_count = 0

        if self._circuit_state == CircuitState.HALF_OPEN:
            self._circuit_state = CircuitState.CLOSED
            logger.info("Circuit closed, recovery successful")

    def _record_failure(self, provider: ModelProvider) -> None:
        """Record a failed call; open circuit if failure threshold reached."""
        health = self._health[provider]
        health.last_failure = time.time()
        health.failure_count += 1

        if health.failure_count >= self.config.failure_threshold:
            self._open_circuit()

    def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        if self._circuit_state != CircuitState.OPEN:
            self._circuit_state = CircuitState.OPEN
            self._circuit_opened_at = time.time()
            logger.warning("Circuit opened — all providers blocked")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._circuit_state

    @property
    def health_report(self) -> dict:
        """Get health report for all providers."""
        return {
            "circuit_state": self._circuit_state.value,
            "providers": {
                provider.value: {
                    "last_success": health.last_success,
                    "failure_count": health.failure_count,
                    "latency_avg_ms": health.latency_avg_ms,
                }
                for provider, health in self._health.items()
            },
        }


class FallbackError(Exception):
    """Fallback chain error — all providers failed."""
    pass


# ---------------------------------------------------------------------------
# Global orchestrator singleton
# ---------------------------------------------------------------------------

_orchestrator: Optional[FallbackOrchestrator] = None


def get_fallback_orchestrator() -> FallbackOrchestrator:
    """Get (or lazily create) the global fallback orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FallbackOrchestrator()
    return _orchestrator


def set_fallback_orchestrator(orchestrator: FallbackOrchestrator) -> None:
    """Replace the global fallback orchestrator (e.g., for testing)."""
    global _orchestrator
    _orchestrator = orchestrator

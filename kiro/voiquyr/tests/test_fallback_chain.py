"""
Tests for the model fallback chain with circuit breaker.

SELF-04: Model fallback chain — Mistral API → self-hosted vLLM → error.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.fallback_chain import (
    CircuitState,
    FallbackConfig,
    FallbackError,
    FallbackOrchestrator,
    ModelHealth,
    ModelProvider,
    get_fallback_orchestrator,
    set_fallback_orchestrator,
)


# ---------------------------------------------------------------------------
# ModelHealth and FallbackConfig
# ---------------------------------------------------------------------------


class TestModelHealth:
    def test_default_values(self):
        h = ModelHealth(provider=ModelProvider.MISTRAL_API)
        assert h.failure_count == 0
        assert h.success_count == 0
        assert h.latency_avg_ms == 0.0

    def test_provider_assignment(self):
        h = ModelHealth(provider=ModelProvider.VLLM)
        assert h.provider == ModelProvider.VLLM


class TestFallbackConfig:
    def test_defaults(self):
        cfg = FallbackConfig()
        assert cfg.timeout_seconds == 30.0
        assert cfg.failure_threshold == 3
        assert cfg.circuit_open_timeout == 300

    def test_custom_config(self):
        cfg = FallbackConfig(timeout_seconds=10.0, failure_threshold=2)
        assert cfg.timeout_seconds == 10.0
        assert cfg.failure_threshold == 2


# ---------------------------------------------------------------------------
# FallbackOrchestrator — circuit state transitions
# ---------------------------------------------------------------------------


class TestCircuitBreakerStates:
    def test_initial_state_is_closed(self):
        orch = FallbackOrchestrator()
        assert orch.state == CircuitState.CLOSED

    def test_open_circuit_transitions_to_open(self):
        orch = FallbackOrchestrator()
        orch._open_circuit()
        assert orch.state == CircuitState.OPEN

    def test_open_circuit_idempotent(self):
        orch = FallbackOrchestrator()
        orch._open_circuit()
        t1 = orch._circuit_opened_at
        orch._open_circuit()
        assert orch._circuit_opened_at == t1  # second call does not reset timer

    def test_record_success_in_half_open_closes_circuit(self):
        orch = FallbackOrchestrator()
        orch._circuit_state = CircuitState.HALF_OPEN
        orch._record_success(ModelProvider.MISTRAL_API)
        assert orch.state == CircuitState.CLOSED

    def test_record_success_in_closed_stays_closed(self):
        orch = FallbackOrchestrator()
        orch._record_success(ModelProvider.MISTRAL_API)
        assert orch.state == CircuitState.CLOSED

    def test_failure_threshold_opens_circuit(self):
        cfg = FallbackConfig(failure_threshold=2)
        orch = FallbackOrchestrator(config=cfg)
        orch._record_failure(ModelProvider.MISTRAL_API)
        assert orch.state == CircuitState.CLOSED
        orch._record_failure(ModelProvider.MISTRAL_API)
        assert orch.state == CircuitState.OPEN


class TestCanAttempt:
    def test_closed_always_allows(self):
        orch = FallbackOrchestrator()
        assert orch._can_attempt(ModelProvider.MISTRAL_API) is True
        assert orch._can_attempt(ModelProvider.VLLM) is True

    def test_open_blocks_within_timeout(self):
        orch = FallbackOrchestrator(config=FallbackConfig(circuit_open_timeout=300))
        orch._open_circuit()
        assert orch._can_attempt(ModelProvider.MISTRAL_API) is False

    def test_open_transitions_to_half_open_after_timeout(self):
        orch = FallbackOrchestrator(config=FallbackConfig(circuit_open_timeout=0))
        orch._circuit_state = CircuitState.OPEN
        orch._circuit_opened_at = time.time() - 1  # already expired
        result = orch._can_attempt(ModelProvider.VLLM)
        assert result is True
        assert orch.state == CircuitState.HALF_OPEN

    def test_half_open_allows_attempt(self):
        orch = FallbackOrchestrator()
        orch._circuit_state = CircuitState.HALF_OPEN
        assert orch._can_attempt(ModelProvider.VLLM) is True


# ---------------------------------------------------------------------------
# FallbackOrchestrator.complete — end-to-end
# ---------------------------------------------------------------------------


MOCK_COMPLETION = {"id": "test-1", "choices": [{"text": "answer"}]}


class TestFallbackComplete:
    @pytest.mark.asyncio
    async def test_uses_primary_provider_when_healthy(self):
        orch = FallbackOrchestrator()

        with patch.object(orch, "_call_provider", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MOCK_COMPLETION
            result = await orch.complete("hello")

        assert result == MOCK_COMPLETION
        mock_call.assert_called_once_with(ModelProvider.MISTRAL_API, "hello")

    @pytest.mark.asyncio
    async def test_falls_back_to_vllm_on_primary_failure(self):
        orch = FallbackOrchestrator()
        call_order = []

        async def fake_call(provider, prompt, **kwargs):
            call_order.append(provider)
            if provider == ModelProvider.MISTRAL_API:
                raise RuntimeError("Mistral API down")
            return MOCK_COMPLETION

        with patch.object(orch, "_call_provider", side_effect=fake_call):
            result = await orch.complete("hello")

        assert result == MOCK_COMPLETION
        assert call_order == [ModelProvider.MISTRAL_API, ModelProvider.VLLM]

    @pytest.mark.asyncio
    async def test_raises_fallback_error_when_all_providers_fail(self):
        orch = FallbackOrchestrator()

        async def fake_call(provider, prompt, **kwargs):
            raise RuntimeError(f"{provider} failed")

        with patch.object(orch, "_call_provider", side_effect=fake_call):
            with pytest.raises(FallbackError, match="All providers failed"):
                await orch.complete("hello")

    @pytest.mark.asyncio
    async def test_skips_provider_when_circuit_open(self):
        orch = FallbackOrchestrator(config=FallbackConfig(circuit_open_timeout=9999))
        orch._open_circuit()  # open circuit — both providers skipped

        with pytest.raises(FallbackError):
            await orch.complete("hello", provider_order=[ModelProvider.MISTRAL_API])

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self):
        orch = FallbackOrchestrator(config=FallbackConfig(timeout_seconds=0.01))
        call_order = []

        async def fake_call(provider, prompt, **kwargs):
            call_order.append(provider)
            if provider == ModelProvider.MISTRAL_API:
                raise asyncio.TimeoutError()
            return MOCK_COMPLETION

        with patch.object(orch, "_call_provider", side_effect=fake_call):
            result = await orch.complete("hello")

        assert result == MOCK_COMPLETION
        assert ModelProvider.MISTRAL_API in call_order
        assert ModelProvider.VLLM in call_order

    @pytest.mark.asyncio
    async def test_records_success_increments_count(self):
        orch = FallbackOrchestrator()

        with patch.object(orch, "_call_provider", new_callable=AsyncMock, return_value=MOCK_COMPLETION):
            await orch.complete("hello")

        assert orch._health[ModelProvider.MISTRAL_API].success_count == 1
        assert orch._health[ModelProvider.MISTRAL_API].failure_count == 0

    @pytest.mark.asyncio
    async def test_records_failure_increments_count(self):
        cfg = FallbackConfig(failure_threshold=999)  # prevent circuit open
        orch = FallbackOrchestrator(config=cfg)
        call_count = 0

        async def fake_call(provider, prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        with patch.object(orch, "_call_provider", side_effect=fake_call):
            with pytest.raises(FallbackError):
                await orch.complete("hello")

        assert orch._health[ModelProvider.MISTRAL_API].failure_count >= 1


# ---------------------------------------------------------------------------
# Health report
# ---------------------------------------------------------------------------


class TestHealthReport:
    def test_health_report_structure(self):
        orch = FallbackOrchestrator()
        report = orch.health_report
        assert "circuit_state" in report
        assert "providers" in report
        assert ModelProvider.MISTRAL_API.value in report["providers"]
        assert ModelProvider.VLLM.value in report["providers"]

    def test_health_report_reflects_circuit_state(self):
        orch = FallbackOrchestrator()
        orch._open_circuit()
        report = orch.health_report
        assert report["circuit_state"] == CircuitState.OPEN.value


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


class TestGlobalSingleton:
    def test_get_returns_same_instance(self):
        set_fallback_orchestrator(None)  # type: ignore[arg-type]
        a = get_fallback_orchestrator()
        b = get_fallback_orchestrator()
        assert a is b

    def test_set_replaces_instance(self):
        custom = FallbackOrchestrator(config=FallbackConfig(timeout_seconds=5.0))
        set_fallback_orchestrator(custom)
        assert get_fallback_orchestrator() is custom

    def teardown_method(self):
        set_fallback_orchestrator(None)  # type: ignore[arg-type]

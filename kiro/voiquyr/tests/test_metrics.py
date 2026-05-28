import pytest

pytestmark = pytest.mark.unit


class _FakeLlm:
    async def infer(self, text: str) -> str:
        return f"response: {text}"


def _sample_value(metric, name: str, labels=None) -> float:
    labels = labels or {}
    for sample in metric.collect()[0].samples:
        if sample.name == name and all(sample.labels.get(k) == v for k, v in labels.items()):
            return sample.value
    return 0.0


def test_metrics_module_exports_all_canonical_metrics():
    from src.core.metrics import get_metrics

    metrics = get_metrics()
    assert hasattr(metrics, "voiquyr_stt_latency_ms")
    assert hasattr(metrics, "voiquyr_llm_latency_ms")
    assert hasattr(metrics, "voiquyr_tts_latency_ms")
    assert hasattr(metrics, "voiquyr_call_latency_ms")
    assert hasattr(metrics, "voiquyr_flash_mode_hits_total")
    assert hasattr(metrics, "voiquyr_flash_mode_misses_total")
    assert hasattr(metrics, "voiquyr_fallback_activations_total")
    assert hasattr(metrics, "voiquyr_circuit_breaker_state")


def test_latency_buckets_are_canonical():
    from src.core.metrics import LATENCY_BUCKETS

    assert LATENCY_BUCKETS == (10, 25, 50, 100, 250, 500, 1000, 2500)


def test_stt_histogram_observes_ok_latency():
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_stt_latency_ms.labels(status="ok").observe(100)


def test_llm_histogram_observes_error_latency():
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_llm_latency_ms.labels(status="error").observe(250)


def test_tts_histogram_observes_ok_latency():
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_tts_latency_ms.labels(status="ok").observe(75)


def test_call_histogram_observes_ok_latency():
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_call_latency_ms.labels(status="ok").observe(300)


def test_record_stage_latency_dispatches_to_stt():
    from src.core.metrics import record_stage_latency

    record_stage_latency("stt", 50.0, "ok")


def test_record_stage_latency_dispatches_to_llm():
    from src.core.metrics import record_stage_latency

    record_stage_latency("llm", 200.0, "ok")


def test_record_stage_latency_dispatches_to_tts():
    from src.core.metrics import record_stage_latency

    record_stage_latency("tts", 75.0, "error")


def test_record_stage_latency_dispatches_to_call():
    from src.core.metrics import record_stage_latency

    record_stage_latency("call", 300.0, "ok")


def test_record_stage_latency_unknown_stage_raises_value_error():
    from src.core.metrics import record_stage_latency

    with pytest.raises(ValueError):
        record_stage_latency("unknown", 50.0, "ok")


def test_metrics_endpoint_returns_200():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.api.config import APIConfig

    client = TestClient(create_app(APIConfig()))
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_endpoint_content_type_is_prometheus():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.api.config import APIConfig

    client = TestClient(create_app(APIConfig()))
    response = client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]
    assert "version=0.0.4" in response.headers["content-type"]


def test_metrics_endpoint_contains_voiquyr_metric_names():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.api.config import APIConfig
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_stt_latency_ms.labels(status="ok").observe(50)
    client = TestClient(create_app(APIConfig()))
    response = client.get("/metrics")
    assert "voiquyr_stt_latency_ms" in response.text


def test_metrics_endpoint_not_in_openapi_schema():
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    from src.api.config import APIConfig

    client = TestClient(create_app(APIConfig()))
    response = client.get("/openapi.json")
    if response.status_code == 200:
        assert "/metrics" not in response.json().get("paths", {})


@pytest.mark.asyncio
async def test_flash_mode_hit_increments_counter():
    from src.core.flash_mode import FlashMode
    from src.core.metrics import get_metrics

    metrics = get_metrics()
    before = _sample_value(metrics.voiquyr_flash_mode_hits_total, "voiquyr_flash_mode_hits_total")
    flash_mode = FlashMode()
    await flash_mode.on_partial_transcript("call-1", "hello", 0.95, "tenant-1", _FakeLlm())
    result = await flash_mode.on_final_transcript("call-1", "hello", _FakeLlm())
    after = _sample_value(metrics.voiquyr_flash_mode_hits_total, "voiquyr_flash_mode_hits_total")
    assert result.was_speculative_hit is True
    assert after == before + 1.0


@pytest.mark.asyncio
async def test_flash_mode_miss_increments_counter():
    from src.core.flash_mode import FlashMode
    from src.core.metrics import get_metrics

    metrics = get_metrics()
    before = _sample_value(metrics.voiquyr_flash_mode_misses_total, "voiquyr_flash_mode_misses_total")
    flash_mode = FlashMode()
    await flash_mode.on_partial_transcript("call-2", "hello", 0.95, "tenant-1", _FakeLlm())
    result = await flash_mode.on_final_transcript("call-2", "goodbye", _FakeLlm())
    after = _sample_value(metrics.voiquyr_flash_mode_misses_total, "voiquyr_flash_mode_misses_total")
    assert result.was_speculative_hit is False
    assert after == before + 1.0


def test_circuit_breaker_gauge_starts_closed():
    from src.agents.fallback_chain import FallbackOrchestrator
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_circuit_breaker_state.set(0)
    FallbackOrchestrator()
    assert get_metrics().voiquyr_circuit_breaker_state._value.get() == 0.0


def test_circuit_breaker_open_sets_gauge_to_1():
    from src.agents.fallback_chain import FallbackOrchestrator
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_circuit_breaker_state.set(0)
    orchestrator = FallbackOrchestrator()
    orchestrator._open_circuit()
    assert get_metrics().voiquyr_circuit_breaker_state._value.get() == 1.0


def test_circuit_breaker_half_open_sets_gauge_to_2():
    import time

    from src.agents.fallback_chain import CircuitState, FallbackConfig, FallbackOrchestrator
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_circuit_breaker_state.set(0)
    orchestrator = FallbackOrchestrator(FallbackConfig(circuit_open_timeout=1))
    orchestrator._circuit_state = CircuitState.OPEN
    orchestrator._circuit_opened_at = time.time() - 2
    assert orchestrator._can_attempt(next(iter(orchestrator._health))) is True
    assert get_metrics().voiquyr_circuit_breaker_state._value.get() == 2.0


def test_circuit_breaker_success_sets_gauge_to_0_from_half_open():
    from src.agents.fallback_chain import CircuitState, FallbackOrchestrator, ModelProvider
    from src.core.metrics import get_metrics

    get_metrics().voiquyr_circuit_breaker_state.set(2)
    orchestrator = FallbackOrchestrator()
    orchestrator._circuit_state = CircuitState.HALF_OPEN
    orchestrator._record_success(ModelProvider.MISTRAL_API)
    assert get_metrics().voiquyr_circuit_breaker_state._value.get() == 0.0


def test_fallback_activations_counter_increments_on_circuit_open():
    from src.agents.fallback_chain import FallbackOrchestrator
    from src.core.metrics import get_metrics

    metrics = get_metrics()
    before = metrics.voiquyr_fallback_activations_total.labels(provider="all")._value.get()
    FallbackOrchestrator()._open_circuit()
    after = metrics.voiquyr_fallback_activations_total.labels(provider="all")._value.get()
    assert after == before + 1.0


def test_no_tenant_id_or_call_id_label_on_stt_histogram():
    from src.core.metrics import get_metrics

    label_names = get_metrics().voiquyr_stt_latency_ms._labelnames
    assert "tenant_id" not in label_names
    assert "call_id" not in label_names


def test_no_tenant_id_or_call_id_label_on_call_histogram():
    from src.core.metrics import get_metrics

    label_names = get_metrics().voiquyr_call_latency_ms._labelnames
    assert "tenant_id" not in label_names
    assert "call_id" not in label_names


def test_fallback_counter_uses_provider_label_only():
    from src.core.metrics import get_metrics

    label_names = get_metrics().voiquyr_fallback_activations_total._labelnames
    assert label_names == ("provider",)


def test_circuit_breaker_gauge_has_no_labels():
    from src.core.metrics import get_metrics

    assert get_metrics().voiquyr_circuit_breaker_state._labelnames == ()

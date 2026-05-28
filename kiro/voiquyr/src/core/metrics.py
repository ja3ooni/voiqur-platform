"""
Prometheus metrics for the Voiquyr pipeline.

Metric names match the canonical Phase 13 / CLAUDE.md names and intentionally
keep labels low-cardinality.
"""

from dataclasses import dataclass

from prometheus_client import Counter, Gauge, Histogram

LATENCY_BUCKETS = (10, 25, 50, 100, 250, 500, 1000, 2500)


@dataclass(frozen=True)
class PrometheusMetrics:
    """Container for canonical Prometheus collectors."""

    voiquyr_stt_latency_ms: Histogram
    voiquyr_llm_latency_ms: Histogram
    voiquyr_tts_latency_ms: Histogram
    voiquyr_call_latency_ms: Histogram
    voiquyr_flash_mode_hits_total: Counter
    voiquyr_flash_mode_misses_total: Counter
    voiquyr_fallback_activations_total: Counter
    voiquyr_circuit_breaker_state: Gauge


_METRICS = PrometheusMetrics(
    voiquyr_stt_latency_ms=Histogram(
        "voiquyr_stt_latency_ms",
        "STT stage latency in milliseconds",
        labelnames=("status",),
        buckets=LATENCY_BUCKETS,
    ),
    voiquyr_llm_latency_ms=Histogram(
        "voiquyr_llm_latency_ms",
        "LLM stage latency in milliseconds",
        labelnames=("status",),
        buckets=LATENCY_BUCKETS,
    ),
    voiquyr_tts_latency_ms=Histogram(
        "voiquyr_tts_latency_ms",
        "TTS stage latency in milliseconds",
        labelnames=("status",),
        buckets=LATENCY_BUCKETS,
    ),
    voiquyr_call_latency_ms=Histogram(
        "voiquyr_call_latency_ms",
        "End-to-end call latency in milliseconds",
        labelnames=("status",),
        buckets=LATENCY_BUCKETS,
    ),
    voiquyr_flash_mode_hits_total=Counter(
        "voiquyr_flash_mode_hits_total",
        "Flash mode speculative inference hits",
    ),
    voiquyr_flash_mode_misses_total=Counter(
        "voiquyr_flash_mode_misses_total",
        "Flash mode speculative inference misses",
    ),
    voiquyr_fallback_activations_total=Counter(
        "voiquyr_fallback_activations_total",
        "LLM fallback activations by provider",
        labelnames=("provider",),
    ),
    voiquyr_circuit_breaker_state=Gauge(
        "voiquyr_circuit_breaker_state",
        "Circuit breaker state: 0=CLOSED, 1=OPEN, 2=HALF_OPEN",
    ),
)


def get_metrics() -> PrometheusMetrics:
    """Return the module-level metrics singleton."""
    return _METRICS


def record_stage_latency(stage: str, latency_ms: float, status: str = "ok") -> None:
    """Record a pipeline stage latency observation."""
    metrics = get_metrics()
    histograms = {
        "stt": metrics.voiquyr_stt_latency_ms,
        "llm": metrics.voiquyr_llm_latency_ms,
        "tts": metrics.voiquyr_tts_latency_ms,
        "call": metrics.voiquyr_call_latency_ms,
    }
    try:
        histogram = histograms[stage]
    except KeyError as exc:
        raise ValueError(f"Unknown pipeline stage: {stage}") from exc
    histogram.labels(status=status).observe(latency_ms)

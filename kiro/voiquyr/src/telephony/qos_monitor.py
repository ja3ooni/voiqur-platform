"""
VoIP QoS Monitor

Real-time jitter, packet loss, MOS score, and latency monitoring
with <5s update intervals and alerting.
Implements Requirements 14.2, 14.7, 20.7.
"""

import asyncio
import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional

from .base import QoSMetrics

logger = logging.getLogger(__name__)


@dataclass
class QoSAlert:
    """Represents a QoS threshold violation alert."""

    call_id: str
    metric: str
    value: float
    threshold: float
    severity: str  # "warning" | "critical"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QoSThresholds:
    """Configurable QoS thresholds."""

    jitter_warning: float = 20.0   # ms
    jitter_critical: float = 50.0  # ms
    packet_loss_warning: float = 1.0   # %
    packet_loss_critical: float = 5.0  # %
    mos_warning: float = 3.5
    mos_critical: float = 2.5
    latency_warning: float = 100.0   # ms
    latency_critical: float = 200.0  # ms


class CallQoSTracker:
    """Tracks QoS metrics history for a single call."""

    def __init__(self, call_id: str, window_size: int = 60):
        self.call_id = call_id
        self._samples: Deque[QoSMetrics] = deque(maxlen=window_size)

    def add_sample(self, metrics: QoSMetrics) -> None:
        self._samples.append(metrics)

    @property
    def latest(self) -> Optional[QoSMetrics]:
        return self._samples[-1] if self._samples else None

    def average(self) -> Optional[QoSMetrics]:
        if not self._samples:
            return None
        return QoSMetrics(
            jitter=statistics.mean(s.jitter for s in self._samples),
            packet_loss=statistics.mean(s.packet_loss for s in self._samples),
            mos_score=statistics.mean(s.mos_score for s in self._samples),
            latency=statistics.mean(s.latency for s in self._samples),
            codec=self._samples[-1].codec,
        )

    def to_report(self) -> Dict[str, Any]:
        avg = self.average()
        latest = self.latest
        return {
            "call_id": self.call_id,
            "samples": len(self._samples),
            "latest": latest.to_dict() if latest else None,
            "average": avg.to_dict() if avg else None,
        }


class QoSMonitor:
    """
    Real-time VoIP QoS monitor.

    Polls active calls for QoS metrics at configurable intervals (default 5s),
    evaluates thresholds, and fires alerts.
    """

    def __init__(
        self,
        update_interval: float = 5.0,
        thresholds: Optional[QoSThresholds] = None,
    ):
        self.update_interval = update_interval
        self.thresholds = thresholds or QoSThresholds()
        self._trackers: Dict[str, CallQoSTracker] = {}
        self._alert_handlers: List[Callable[[QoSAlert], None]] = []
        self._active_alerts: Dict[str, List[QoSAlert]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # Injected by the call controller: async fn(call_id) -> Optional[QoSMetrics]
        self._metrics_fetcher: Optional[Callable] = None
        self.logger = logging.getLogger(__name__)

    def set_metrics_fetcher(self, fetcher: Callable) -> None:
        """Set the async function used to fetch QoS metrics per call."""
        self._metrics_fetcher = fetcher

    def add_alert_handler(self, handler: Callable[[QoSAlert], None]) -> None:
        self._alert_handlers.append(handler)

    def start_tracking(self, call_id: str) -> None:
        self._trackers[call_id] = CallQoSTracker(call_id)
        self._active_alerts[call_id] = []

    def stop_tracking(self, call_id: str) -> None:
        self._trackers.pop(call_id, None)
        self._active_alerts.pop(call_id, None)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.ensure_future(self._monitor_loop())
        self.logger.info(
            f"QoS monitor started (interval={self.update_interval}s)"
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.update_interval)
            await self._poll_all()

    async def _poll_all(self) -> None:
        if not self._metrics_fetcher:
            return
        for call_id in list(self._trackers.keys()):
            try:
                metrics: Optional[QoSMetrics] = await self._metrics_fetcher(call_id)
                if metrics:
                    self._trackers[call_id].add_sample(metrics)
                    self._evaluate_thresholds(call_id, metrics)
            except Exception as e:
                self.logger.warning(f"QoS poll failed for {call_id}: {e}")

    def _evaluate_thresholds(self, call_id: str, metrics: QoSMetrics) -> None:
        checks = [
            ("jitter", metrics.jitter, self.thresholds.jitter_warning, self.thresholds.jitter_critical, True),
            ("packet_loss", metrics.packet_loss, self.thresholds.packet_loss_warning, self.thresholds.packet_loss_critical, True),
            ("mos_score", metrics.mos_score, self.thresholds.mos_warning, self.thresholds.mos_critical, False),
            ("latency", metrics.latency, self.thresholds.latency_warning, self.thresholds.latency_critical, True),
        ]
        for metric, value, warn_thresh, crit_thresh, higher_is_worse in checks:
            if higher_is_worse:
                if value >= crit_thresh:
                    self._fire_alert(call_id, metric, value, crit_thresh, "critical")
                elif value >= warn_thresh:
                    self._fire_alert(call_id, metric, value, warn_thresh, "warning")
            else:
                # Lower is worse (MOS)
                if value <= crit_thresh:
                    self._fire_alert(call_id, metric, value, crit_thresh, "critical")
                elif value <= warn_thresh:
                    self._fire_alert(call_id, metric, value, warn_thresh, "warning")

    def _fire_alert(
        self, call_id: str, metric: str, value: float, threshold: float, severity: str
    ) -> None:
        alert = QoSAlert(
            call_id=call_id,
            metric=metric,
            value=value,
            threshold=threshold,
            severity=severity,
        )
        self._active_alerts.setdefault(call_id, []).append(alert)
        self.logger.warning(
            f"QoS {severity} alert [{call_id}] {metric}={value:.2f} "
            f"(threshold={threshold})"
        )
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler error: {e}")

    def get_report(self, call_id: str) -> Optional[Dict[str, Any]]:
        tracker = self._trackers.get(call_id)
        if not tracker:
            return None
        report = tracker.to_report()
        report["alerts"] = [a.to_dict() for a in self._active_alerts.get(call_id, [])]
        return report

    def get_system_report(self) -> Dict[str, Any]:
        return {
            "monitored_calls": len(self._trackers),
            "update_interval": self.update_interval,
            "calls": {cid: self.get_report(cid) for cid in self._trackers},
        }

    @staticmethod
    def calculate_mos(jitter: float, packet_loss: float, latency: float) -> float:
        """
        E-model MOS estimation (ITU-T G.107).

        Args:
            jitter: Jitter in milliseconds
            packet_loss: Packet loss percentage (0-100)
            latency: One-way latency in milliseconds

        Returns:
            MOS score (1.0 - 5.0)
        """
        r = 93.2 - (latency / 10.0) - (jitter * 0.5) - (packet_loss * 2.5)
        r = max(0.0, min(100.0, r))
        mos = 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6
        return round(max(1.0, min(5.0, mos)), 2)

"""
Predictive Analytics — churn prediction, success scoring,
intervention detection, capacity forecasting, anomaly detection.
Implements Requirement 22.5.
"""

import math
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ChurnPrediction:
    tenant_id: str
    user_id: str
    churn_probability: float   # 0.0 – 1.0
    risk_level: str            # "low" | "medium" | "high"
    factors: List[str] = field(default_factory=list)
    predicted_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "churn_probability": round(self.churn_probability, 3),
            "risk_level": self.risk_level,
            "factors": self.factors,
        }


@dataclass
class AnomalyAlert:
    metric: str
    value: float
    expected: float
    z_score: float
    detected_at: datetime = field(default_factory=datetime.utcnow)
    severity: str = "warning"   # "warning" | "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value": round(self.value, 3),
            "expected": round(self.expected, 3),
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
        }


class PredictiveAnalytics:
    """
    Lightweight predictive models using statistical heuristics.
    No ML framework dependency — uses z-scores, moving averages, and
    logistic-style scoring for production-ready predictions.
    """

    def __init__(self, anomaly_window: int = 30):
        self._metric_history: Dict[str, deque] = {}
        self._anomaly_window = anomaly_window
        self._anomalies: List[AnomalyAlert] = []

    # ------------------------------------------------------------------
    # Churn prediction (logistic scoring)
    # ------------------------------------------------------------------

    def predict_churn(
        self,
        user_id: str,
        tenant_id: str,
        days_since_last_login: int,
        satisfaction_avg: Optional[float],
        open_tickets: int,
        feature_adoption_pct: float,
        conversations_last_30d: int,
    ) -> ChurnPrediction:
        score = 0.0
        factors = []

        if days_since_last_login > 30:
            score += 0.35; factors.append("inactive_30d")
        elif days_since_last_login > 14:
            score += 0.15; factors.append("inactive_14d")

        if satisfaction_avg is not None and satisfaction_avg < 3.0:
            score += 0.25; factors.append("low_satisfaction")
        elif satisfaction_avg is not None and satisfaction_avg < 3.5:
            score += 0.10; factors.append("below_avg_satisfaction")

        if open_tickets > 3:
            score += 0.20; factors.append("many_open_tickets")

        if feature_adoption_pct < 20:
            score += 0.15; factors.append("low_feature_adoption")

        if conversations_last_30d == 0:
            score += 0.20; factors.append("no_recent_conversations")
        elif conversations_last_30d < 3:
            score += 0.05; factors.append("low_engagement")

        prob = min(1.0, score)
        risk = "high" if prob >= 0.6 else ("medium" if prob >= 0.3 else "low")
        return ChurnPrediction(
            tenant_id=tenant_id, user_id=user_id,
            churn_probability=prob, risk_level=risk, factors=factors,
        )

    # ------------------------------------------------------------------
    # Success probability scoring
    # ------------------------------------------------------------------

    def score_conversation_success(
        self,
        turn_count: int,
        avg_sentiment: float,
        intent_match_rate: float,
        channel: str,
    ) -> float:
        """Returns 0.0–1.0 probability of successful completion."""
        score = 0.5
        # Sentiment contribution
        score += avg_sentiment * 0.2
        # Intent match rate
        score += (intent_match_rate - 0.5) * 0.2
        # Turn count penalty (too many = struggling)
        if turn_count > 10:
            score -= 0.1
        # Channel bonus (web chat tends to complete better)
        if channel in ("web_chat", "whatsapp"):
            score += 0.05
        return round(max(0.0, min(1.0, score)), 3)

    # ------------------------------------------------------------------
    # Optimal intervention detection
    # ------------------------------------------------------------------

    def detect_intervention_point(
        self,
        turn_count: int,
        sentiment_trend: List[float],
        time_in_conversation_s: float,
    ) -> Optional[str]:
        """
        Returns intervention type if one is recommended, else None.
        Types: "handoff_to_agent" | "offer_callback" | "send_faq"
        """
        if not sentiment_trend:
            return None
        recent_sentiment = statistics.mean(sentiment_trend[-3:]) if len(sentiment_trend) >= 3 else sentiment_trend[-1]
        if recent_sentiment < -0.3 and turn_count > 5:
            return "handoff_to_agent"
        if time_in_conversation_s > 300 and turn_count > 8:
            return "offer_callback"
        if turn_count > 6 and recent_sentiment < 0.0:
            return "send_faq"
        return None

    # ------------------------------------------------------------------
    # Capacity forecasting (simple linear extrapolation)
    # ------------------------------------------------------------------

    def forecast_capacity(
        self,
        historical_volumes: List[int],
        forecast_periods: int = 7,
    ) -> List[int]:
        """
        Forecast next N periods using linear regression on historical volumes.
        """
        n = len(historical_volumes)
        if n < 2:
            return [historical_volumes[-1]] * forecast_periods if historical_volumes else [0] * forecast_periods

        x_mean = (n - 1) / 2
        y_mean = statistics.mean(historical_volumes)
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(historical_volumes))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den else 0
        intercept = y_mean - slope * x_mean

        return [max(0, round(intercept + slope * (n + i))) for i in range(forecast_periods)]

    # ------------------------------------------------------------------
    # Anomaly detection (z-score based)
    # ------------------------------------------------------------------

    def record_metric(self, metric_name: str, value: float) -> Optional[AnomalyAlert]:
        if metric_name not in self._metric_history:
            self._metric_history[metric_name] = deque(maxlen=self._anomaly_window)
        history = self._metric_history[metric_name]

        # Compute z-score BEFORE appending so the new value isn't in the baseline
        if len(history) >= 5:
            mean = statistics.mean(history)
            stdev = statistics.stdev(history) if len(history) > 1 else 0
            if stdev > 0:
                z = abs(value - mean) / stdev
                if z > 3.0:
                    alert = AnomalyAlert(
                        metric=metric_name, value=value, expected=mean,
                        z_score=z, severity="critical" if z > 4.0 else "warning",
                    )
                    self._anomalies.append(alert)
                    history.append(value)
                    return alert

        history.append(value)
        return None

    def get_anomalies(self, since: Optional[datetime] = None) -> List[AnomalyAlert]:
        if since:
            return [a for a in self._anomalies if a.detected_at >= since]
        return list(self._anomalies)

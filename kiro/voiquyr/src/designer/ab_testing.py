"""
A/B Testing Framework — traffic splitting, variant management,
performance comparison, automatic winner selection, statistical analysis.
Implements Requirement 21.5.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    variant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    flow_id: str = ""
    traffic_pct: float = 50.0   # 0-100
    # Metrics
    sessions: int = 0
    conversions: int = 0
    total_turns: int = 0
    satisfaction_sum: float = 0.0

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.sessions if self.sessions else 0.0

    @property
    def avg_turns(self) -> float:
        return self.total_turns / self.sessions if self.sessions else 0.0

    @property
    def avg_satisfaction(self) -> float:
        return self.satisfaction_sum / self.sessions if self.sessions else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "flow_id": self.flow_id,
            "traffic_pct": self.traffic_pct,
            "sessions": self.sessions,
            "conversions": self.conversions,
            "conversion_rate": round(self.conversion_rate, 4),
            "avg_turns": round(self.avg_turns, 2),
            "avg_satisfaction": round(self.avg_satisfaction, 2),
        }


@dataclass
class Experiment:
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    metric: str = "conversion_rate"   # primary metric
    variants: List[Variant] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    min_sessions: int = 100           # minimum before declaring winner
    confidence_threshold: float = 0.95
    winner_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def start(self) -> None:
        self.status = ExperimentStatus.RUNNING
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        self.status = ExperimentStatus.PAUSED

    def resume(self) -> None:
        self.status = ExperimentStatus.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "metric": self.metric,
            "status": self.status.value,
            "variants": [v.to_dict() for v in self.variants],
            "winner_id": self.winner_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


class ABTestingFramework:
    """
    Manages A/B experiments with traffic splitting, metric tracking,
    and statistical significance testing (z-test for proportions).
    """

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._session_assignments: Dict[str, str] = {}  # session_id → variant_id

    def create_experiment(
        self,
        name: str,
        flow_ids: List[str],
        traffic_split: Optional[List[float]] = None,
        metric: str = "conversion_rate",
    ) -> Experiment:
        n = len(flow_ids)
        split = traffic_split or [100.0 / n] * n
        assert abs(sum(split) - 100.0) < 0.01, "Traffic split must sum to 100"
        variants = [
            Variant(name=f"Variant {chr(65+i)}", flow_id=fid, traffic_pct=pct)
            for i, (fid, pct) in enumerate(zip(flow_ids, split))
        ]
        exp = Experiment(name=name, variants=variants, metric=metric)
        self._experiments[exp.experiment_id] = exp
        return exp

    def assign_variant(self, experiment_id: str, session_id: str) -> Optional[Variant]:
        """Assign a session to a variant using weighted random selection."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None
        if session_id in self._session_assignments:
            vid = self._session_assignments[session_id]
            return next((v for v in exp.variants if v.variant_id == vid), None)

        import random
        r = random.uniform(0, 100)
        cumulative = 0.0
        for v in exp.variants:
            cumulative += v.traffic_pct
            if r <= cumulative:
                self._session_assignments[session_id] = v.variant_id
                v.sessions += 1
                return v
        # Fallback to last variant
        last = exp.variants[-1]
        self._session_assignments[session_id] = last.variant_id
        last.sessions += 1
        return last

    def record_conversion(self, experiment_id: str, session_id: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        vid = self._session_assignments.get(session_id)
        variant = next((v for v in exp.variants if v.variant_id == vid), None)
        if variant:
            variant.conversions += 1
            return True
        return False

    def record_turn(self, experiment_id: str, session_id: str) -> None:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        vid = self._session_assignments.get(session_id)
        variant = next((v for v in exp.variants if v.variant_id == vid), None)
        if variant:
            variant.total_turns += 1

    def check_significance(self, experiment_id: str) -> Dict[str, Any]:
        """
        Two-proportion z-test between control (first variant) and each treatment.
        Returns p-values and whether each comparison is significant.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or len(exp.variants) < 2:
            return {}

        control = exp.variants[0]
        results = []
        for treatment in exp.variants[1:]:
            p_val = self._z_test(control, treatment)
            significant = p_val < (1 - exp.confidence_threshold)
            results.append({
                "control": control.variant_id,
                "treatment": treatment.variant_id,
                "control_rate": round(control.conversion_rate, 4),
                "treatment_rate": round(treatment.conversion_rate, 4),
                "p_value": round(p_val, 4),
                "significant": significant,
                "lift": round(
                    (treatment.conversion_rate - control.conversion_rate)
                    / max(control.conversion_rate, 1e-9), 4
                ),
            })
        return {"experiment_id": experiment_id, "comparisons": results}

    def _z_test(self, control: Variant, treatment: Variant) -> float:
        """Two-proportion z-test, returns p-value (one-tailed)."""
        n1, n2 = control.sessions, treatment.sessions
        if n1 == 0 or n2 == 0:
            return 1.0
        p1, p2 = control.conversion_rate, treatment.conversion_rate
        p_pool = (control.conversions + treatment.conversions) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se == 0:
            return 1.0
        z = (p2 - p1) / se
        # Approximate p-value using normal CDF
        return 1 - self._norm_cdf(abs(z))

    @staticmethod
    def _norm_cdf(z: float) -> float:
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    def auto_select_winner(self, experiment_id: str) -> Optional[str]:
        """Declare winner if significance threshold met and min sessions reached."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        total = sum(v.sessions for v in exp.variants)
        if total < exp.min_sessions:
            return None

        sig = self.check_significance(experiment_id)
        for comp in sig.get("comparisons", []):
            if comp["significant"] and comp["lift"] > 0:
                exp.winner_id = comp["treatment"]
                exp.status = ExperimentStatus.COMPLETED
                exp.completed_at = datetime.utcnow()
                return exp.winner_id

        # No significant winner — pick best by metric
        best = max(exp.variants, key=lambda v: v.conversion_rate)
        if best.sessions >= exp.min_sessions:
            exp.winner_id = best.variant_id
            exp.status = ExperimentStatus.COMPLETED
            exp.completed_at = datetime.utcnow()
        return exp.winner_id

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def get_comparison_report(self, experiment_id: str) -> Dict[str, Any]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        return {
            **exp.to_dict(),
            "significance": self.check_significance(experiment_id),
        }

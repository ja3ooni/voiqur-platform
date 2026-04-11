"""
SLA Management — definition, tracking, uptime monitoring (99.9% target),
breach detection, financial penalty calculation, and reporting.
Implements Requirement 19.2.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

UPTIME_TARGET = 0.999  # 99.9%
UPTIME_ALLOWED_DOWNTIME_MINUTES_PER_MONTH = (1 - UPTIME_TARGET) * 30 * 24 * 60  # ~43.8 min


@dataclass
class SLADefinition:
    sla_id: str
    name: str
    uptime_target: float = UPTIME_TARGET
    # Response / resolution targets in minutes per priority
    response_targets: Dict[str, int] = field(default_factory=lambda: {
        "P1": 15, "P2": 60, "P3": 240, "P4": 1440
    })
    resolution_targets: Dict[str, int] = field(default_factory=lambda: {
        "P1": 60, "P2": 240, "P3": 1440, "P4": 5760
    })
    # Financial penalty: % of monthly fee per hour of excess downtime
    penalty_pct_per_hour: float = 5.0
    monthly_fee_eur: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_id": self.sla_id,
            "name": self.name,
            "uptime_target": self.uptime_target,
            "response_targets": self.response_targets,
            "resolution_targets": self.resolution_targets,
            "penalty_pct_per_hour": self.penalty_pct_per_hour,
        }


@dataclass
class UptimeRecord:
    period_start: datetime
    period_end: datetime
    total_minutes: float
    downtime_minutes: float

    @property
    def uptime_pct(self) -> float:
        if self.total_minutes == 0:
            return 1.0
        return 1.0 - (self.downtime_minutes / self.total_minutes)

    @property
    def sla_met(self) -> bool:
        return self.uptime_pct >= UPTIME_TARGET

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "uptime_pct": round(self.uptime_pct * 100, 4),
            "downtime_minutes": round(self.downtime_minutes, 2),
            "sla_met": self.sla_met,
        }


@dataclass
class SLABreach:
    breach_id: str
    tenant_id: str
    sla_id: str
    breach_type: str   # "uptime" | "response" | "resolution"
    ticket_id: Optional[str]
    detected_at: datetime
    excess_minutes: float
    penalty_eur: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breach_id": self.breach_id,
            "tenant_id": self.tenant_id,
            "breach_type": self.breach_type,
            "ticket_id": self.ticket_id,
            "detected_at": self.detected_at.isoformat(),
            "excess_minutes": round(self.excess_minutes, 2),
            "penalty_eur": round(self.penalty_eur, 2),
        }


class SLAManager:
    """
    Tracks SLA compliance per tenant, detects breaches, calculates penalties.
    """

    def __init__(self):
        self._slas: Dict[str, SLADefinition] = {}
        self._tenant_sla: Dict[str, str] = {}   # tenant_id → sla_id
        self._uptime: Dict[str, List[UptimeRecord]] = {}
        self._breaches: List[SLABreach] = []
        import uuid
        self._uuid = uuid

    def register_sla(self, sla: SLADefinition) -> None:
        self._slas[sla.sla_id] = sla

    def assign_sla(self, tenant_id: str, sla_id: str) -> None:
        self._tenant_sla[tenant_id] = sla_id

    def record_uptime(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        downtime_minutes: float,
    ) -> UptimeRecord:
        total = (period_end - period_start).total_seconds() / 60
        record = UptimeRecord(period_start, period_end, total, downtime_minutes)
        self._uptime.setdefault(tenant_id, []).append(record)

        if not record.sla_met:
            sla_id = self._tenant_sla.get(tenant_id, "default")
            sla = self._slas.get(sla_id)
            allowed = (1 - UPTIME_TARGET) * total
            excess_min = downtime_minutes - allowed
            penalty = self._calc_penalty(sla, excess_min) if sla else 0.0
            self._breaches.append(SLABreach(
                breach_id=str(self._uuid.uuid4()),
                tenant_id=tenant_id,
                sla_id=sla_id,
                breach_type="uptime",
                ticket_id=None,
                detected_at=datetime.utcnow(),
                excess_minutes=excess_min,
                penalty_eur=penalty,
            ))
        return record

    def check_ticket_sla(self, ticket: Any) -> List[SLABreach]:
        """Check a ticket for response/resolution SLA breaches."""
        breaches = []
        sla_id = self._tenant_sla.get(ticket.tenant_id, "default")
        sla = self._slas.get(sla_id)

        if ticket.response_breached:
            excess = (
                (ticket.first_response_at or datetime.utcnow()) - ticket.response_deadline
            ).total_seconds() / 60
            penalty = self._calc_penalty(sla, excess) if sla else 0.0
            b = SLABreach(
                breach_id=str(self._uuid.uuid4()),
                tenant_id=ticket.tenant_id,
                sla_id=sla_id,
                breach_type="response",
                ticket_id=ticket.ticket_id,
                detected_at=datetime.utcnow(),
                excess_minutes=max(0, excess),
                penalty_eur=penalty,
            )
            self._breaches.append(b)
            breaches.append(b)

        if ticket.resolution_breached:
            excess = (
                (ticket.resolved_at or datetime.utcnow()) - ticket.resolution_deadline
            ).total_seconds() / 60
            penalty = self._calc_penalty(sla, excess) if sla else 0.0
            b = SLABreach(
                breach_id=str(self._uuid.uuid4()),
                tenant_id=ticket.tenant_id,
                sla_id=sla_id,
                breach_type="resolution",
                ticket_id=ticket.ticket_id,
                detected_at=datetime.utcnow(),
                excess_minutes=max(0, excess),
                penalty_eur=penalty,
            )
            self._breaches.append(b)
            breaches.append(b)

        return breaches

    def _calc_penalty(self, sla: Optional[SLADefinition], excess_minutes: float) -> float:
        if not sla or sla.monthly_fee_eur == 0:
            return 0.0
        excess_hours = excess_minutes / 60
        return min(sla.monthly_fee_eur, sla.monthly_fee_eur * (sla.penalty_pct_per_hour / 100) * excess_hours)

    def get_uptime_report(self, tenant_id: str) -> Dict[str, Any]:
        records = self._uptime.get(tenant_id, [])
        if not records:
            return {"tenant_id": tenant_id, "records": [], "overall_uptime_pct": 100.0}
        total_min = sum(r.total_minutes for r in records)
        down_min = sum(r.downtime_minutes for r in records)
        overall = 1.0 - (down_min / total_min) if total_min else 1.0
        return {
            "tenant_id": tenant_id,
            "overall_uptime_pct": round(overall * 100, 4),
            "sla_target_pct": UPTIME_TARGET * 100,
            "sla_met": overall >= UPTIME_TARGET,
            "total_downtime_minutes": round(down_min, 2),
            "records": [r.to_dict() for r in records],
        }

    def get_breach_report(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        breaches = self._breaches
        if tenant_id:
            breaches = [b for b in breaches if b.tenant_id == tenant_id]
        return [b.to_dict() for b in breaches]

    def get_total_penalties(self, tenant_id: str) -> float:
        return sum(b.penalty_eur for b in self._breaches if b.tenant_id == tenant_id)

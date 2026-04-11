"""
Account Management — TAM/CSM assignment, proactive monitoring,
health checks, and escalation procedures.
Implements Requirements 19.3, 19.7.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AccountTier(Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    STRATEGIC = "strategic"


class HealthScore(Enum):
    HEALTHY = "healthy"       # 80-100
    AT_RISK = "at_risk"       # 50-79
    CRITICAL = "critical"     # 0-49


class EscalationLevel(Enum):
    L1 = "L1"   # Support agent
    L2 = "L2"   # Senior engineer
    L3 = "L3"   # Engineering lead
    EXEC = "EXEC"  # Executive escalation


@dataclass
class AccountManager:
    manager_id: str
    name: str
    email: str
    role: str   # "TAM" | "CSM"
    max_accounts: int = 20
    assigned_accounts: List[str] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return len(self.assigned_accounts) < self.max_accounts

    def to_dict(self) -> Dict[str, Any]:
        return {"manager_id": self.manager_id, "name": self.name,
                "role": self.role, "assigned_accounts": len(self.assigned_accounts)}


@dataclass
class AccountHealth:
    tenant_id: str
    score: int = 100          # 0-100
    uptime_pct: float = 100.0
    open_p1_tickets: int = 0
    open_p2_tickets: int = 0
    last_login_days_ago: int = 0
    feature_adoption_pct: float = 0.0
    nps_score: Optional[int] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def health_status(self) -> HealthScore:
        if self.score >= 80:
            return HealthScore.HEALTHY
        if self.score >= 50:
            return HealthScore.AT_RISK
        return HealthScore.CRITICAL

    def recalculate(self) -> int:
        score = 100
        if self.uptime_pct < 99.9:
            score -= int((99.9 - self.uptime_pct) * 10)
        score -= self.open_p1_tickets * 20
        score -= self.open_p2_tickets * 5
        if self.last_login_days_ago > 30:
            score -= 15
        if self.feature_adoption_pct < 30:
            score -= 10
        self.score = max(0, min(100, score))
        self.updated_at = datetime.utcnow()
        return self.score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "score": self.score,
            "health_status": self.health_status.value,
            "uptime_pct": self.uptime_pct,
            "open_p1_tickets": self.open_p1_tickets,
            "open_p2_tickets": self.open_p2_tickets,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class EscalationRecord:
    escalation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    ticket_id: Optional[str] = None
    level: EscalationLevel = EscalationLevel.L2
    reason: str = ""
    escalated_by: str = ""
    escalated_to: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "tenant_id": self.tenant_id,
            "ticket_id": self.ticket_id,
            "level": self.level.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class AccountManagementSystem:
    """
    Manages TAM/CSM assignments, account health, and escalations.
    """

    def __init__(self):
        self._managers: Dict[str, AccountManager] = {}
        self._assignments: Dict[str, Dict[str, str]] = {}  # tenant_id → {TAM, CSM}
        self._health: Dict[str, AccountHealth] = {}
        self._escalations: List[EscalationRecord] = []

    def register_manager(self, manager: AccountManager) -> None:
        self._managers[manager.manager_id] = manager

    def assign_managers(
        self,
        tenant_id: str,
        tam_id: Optional[str] = None,
        csm_id: Optional[str] = None,
    ) -> Dict[str, str]:
        assignment: Dict[str, str] = {}
        for role, mid in [("TAM", tam_id), ("CSM", csm_id)]:
            if mid and mid in self._managers:
                m = self._managers[mid]
                if tenant_id not in m.assigned_accounts:
                    m.assigned_accounts.append(tenant_id)
                assignment[role] = mid
        self._assignments[tenant_id] = assignment
        return assignment

    def auto_assign(self, tenant_id: str, tier: AccountTier) -> Dict[str, str]:
        """Auto-assign least-loaded TAM and CSM for enterprise+ tiers."""
        if tier not in (AccountTier.ENTERPRISE, AccountTier.STRATEGIC):
            return {}
        assignment: Dict[str, str] = {}
        for role in ("TAM", "CSM"):
            candidates = [m for m in self._managers.values()
                          if m.role == role and m.is_available]
            if candidates:
                best = min(candidates, key=lambda m: len(m.assigned_accounts))
                assignment[role] = best.manager_id
                if tenant_id not in best.assigned_accounts:
                    best.assigned_accounts.append(tenant_id)
        self._assignments[tenant_id] = assignment
        return assignment

    def update_health(self, health: AccountHealth) -> AccountHealth:
        health.recalculate()
        self._health[health.tenant_id] = health
        return health

    def get_health(self, tenant_id: str) -> Optional[AccountHealth]:
        return self._health.get(tenant_id)

    def get_at_risk_accounts(self) -> List[AccountHealth]:
        return [h for h in self._health.values()
                if h.health_status in (HealthScore.AT_RISK, HealthScore.CRITICAL)]

    def escalate(
        self,
        tenant_id: str,
        level: EscalationLevel,
        reason: str,
        escalated_by: str,
        ticket_id: Optional[str] = None,
    ) -> EscalationRecord:
        # Determine escalation target
        assignment = self._assignments.get(tenant_id, {})
        target_map = {
            EscalationLevel.L1: "support_queue",
            EscalationLevel.L2: assignment.get("TAM", "senior_engineer"),
            EscalationLevel.L3: "engineering_lead",
            EscalationLevel.EXEC: "executive_team",
        }
        record = EscalationRecord(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            level=level,
            reason=reason,
            escalated_by=escalated_by,
            escalated_to=target_map[level],
        )
        self._escalations.append(record)
        return record

    def resolve_escalation(self, escalation_id: str) -> bool:
        for e in self._escalations:
            if e.escalation_id == escalation_id:
                e.resolved_at = datetime.utcnow()
                return True
        return False

    def get_dashboard(self) -> Dict[str, Any]:
        health_list = list(self._health.values())
        return {
            "total_accounts": len(self._assignments),
            "healthy": sum(1 for h in health_list if h.health_status == HealthScore.HEALTHY),
            "at_risk": sum(1 for h in health_list if h.health_status == HealthScore.AT_RISK),
            "critical": sum(1 for h in health_list if h.health_status == HealthScore.CRITICAL),
            "open_escalations": sum(1 for e in self._escalations if not e.resolved_at),
            "managers": len(self._managers),
        }

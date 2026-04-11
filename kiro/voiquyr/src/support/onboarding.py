"""
Onboarding & Training System — onboarding workflow, training scheduling,
certification program, and success metrics.
Implements Requirement 19.4.

Regional Support — multi-language portal, routing, business hours.
Implements Requirement 19.5.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Onboarding & Training (19.4)
# ---------------------------------------------------------------------------

class OnboardingStage(Enum):
    KICKOFF = "kickoff"
    SETUP = "setup"
    TRAINING = "training"
    PILOT = "pilot"
    GO_LIVE = "go_live"
    COMPLETED = "completed"


class TrainingStatus(Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TrainingSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    title: str = ""
    description: str = ""
    scheduled_at: Optional[datetime] = None
    duration_minutes: int = 60
    trainer: str = ""
    attendees: List[str] = field(default_factory=list)
    status: TrainingStatus = TrainingStatus.SCHEDULED
    recording_url: Optional[str] = None
    materials_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "attendees": len(self.attendees),
        }


@dataclass
class CertificationRecord:
    cert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    tenant_id: str = ""
    certification: str = ""   # e.g. "VoiQyr Platform Administrator"
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cert_id": self.cert_id,
            "user_id": self.user_id,
            "certification": self.certification,
            "issued_at": self.issued_at.isoformat(),
            "score": self.score,
        }


@dataclass
class OnboardingPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    tier: str = "enterprise"
    stage: OnboardingStage = OnboardingStage.KICKOFF
    start_date: datetime = field(default_factory=datetime.utcnow)
    target_go_live: Optional[datetime] = None
    assigned_specialist: str = ""
    training_sessions: List[TrainingSession] = field(default_factory=list)
    completed_stages: List[str] = field(default_factory=list)
    success_metrics: Dict[str, Any] = field(default_factory=dict)

    def advance_stage(self) -> OnboardingStage:
        order = list(OnboardingStage)
        idx = order.index(self.stage)
        self.completed_stages.append(self.stage.value)
        if idx + 1 < len(order):
            self.stage = order[idx + 1]
        return self.stage

    def completion_pct(self) -> float:
        total = len(OnboardingStage)
        done = len(self.completed_stages)
        return round(done / total * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tenant_id": self.tenant_id,
            "stage": self.stage.value,
            "completion_pct": self.completion_pct(),
            "training_sessions": len(self.training_sessions),
            "completed_stages": self.completed_stages,
        }


class OnboardingSystem:
    def __init__(self):
        self._plans: Dict[str, OnboardingPlan] = {}
        self._sessions: Dict[str, TrainingSession] = {}
        self._certs: List[CertificationRecord] = []

    def create_plan(self, tenant_id: str, tier: str = "enterprise",
                    specialist: str = "") -> OnboardingPlan:
        plan = OnboardingPlan(tenant_id=tenant_id, tier=tier,
                              assigned_specialist=specialist)
        self._plans[tenant_id] = plan
        return plan

    def schedule_training(self, session: TrainingSession) -> TrainingSession:
        self._sessions[session.session_id] = session
        plan = self._plans.get(session.tenant_id)
        if plan:
            plan.training_sessions.append(session)
        return session

    def complete_training(self, session_id: str, recording_url: str = "") -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        s.status = TrainingStatus.COMPLETED
        s.recording_url = recording_url or None
        return True

    def issue_certification(
        self, user_id: str, tenant_id: str, certification: str, score: float
    ) -> Optional[CertificationRecord]:
        if score < 70.0:
            return None
        cert = CertificationRecord(user_id=user_id, tenant_id=tenant_id,
                                   certification=certification, score=score)
        self._certs.append(cert)
        return cert

    def get_plan(self, tenant_id: str) -> Optional[OnboardingPlan]:
        return self._plans.get(tenant_id)

    def get_success_metrics(self, tenant_id: str) -> Dict[str, Any]:
        plan = self._plans.get(tenant_id)
        if not plan:
            return {}
        sessions = [s for s in self._sessions.values() if s.tenant_id == tenant_id]
        certs = [c for c in self._certs if c.tenant_id == tenant_id]
        return {
            "tenant_id": tenant_id,
            "stage": plan.stage.value,
            "completion_pct": plan.completion_pct(),
            "training_sessions_completed": sum(1 for s in sessions if s.status == TrainingStatus.COMPLETED),
            "certifications_issued": len(certs),
            "success_metrics": plan.success_metrics,
        }


# ---------------------------------------------------------------------------
# Regional Support (19.5)
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = ["en", "fr", "de", "es", "it", "nl", "pl", "ar", "pt"]

# Business hours per region (UTC)
REGIONAL_HOURS: Dict[str, Dict[str, Any]] = {
    "eu-west":  {"start": time(8, 0),  "end": time(18, 0), "tz": "Europe/Paris"},
    "eu-east":  {"start": time(7, 0),  "end": time(17, 0), "tz": "Europe/Warsaw"},
    "mea":      {"start": time(6, 0),  "end": time(16, 0), "tz": "Asia/Dubai"},
    "global":   {"start": time(0, 0),  "end": time(23, 59), "tz": "UTC"},
}


@dataclass
class RegionalQueue:
    region: str
    language: str
    agent_ids: List[str] = field(default_factory=list)
    ticket_ids: List[str] = field(default_factory=list)

    def is_business_hours(self) -> bool:
        hours = REGIONAL_HOURS.get(self.region, REGIONAL_HOURS["global"])
        now = datetime.utcnow().time()
        return hours["start"] <= now <= hours["end"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region": self.region,
            "language": self.language,
            "queue_depth": len(self.ticket_ids),
            "agents": len(self.agent_ids),
            "business_hours": self.is_business_hours(),
        }


class RegionalSupportRouter:
    """Routes tickets to the correct regional queue based on language and timezone."""

    def __init__(self):
        self._queues: Dict[str, RegionalQueue] = {}

    def register_queue(self, queue: RegionalQueue) -> None:
        key = f"{queue.region}:{queue.language}"
        self._queues[key] = queue

    def route_ticket(self, ticket_id: str, language: str, tenant_region: str) -> Optional[str]:
        """Returns the queue key the ticket was routed to."""
        # Try exact region+language match
        key = f"{tenant_region}:{language}"
        if key in self._queues:
            self._queues[key].ticket_ids.append(ticket_id)
            return key
        # Fallback: language match in any region
        for k, q in self._queues.items():
            if q.language == language:
                q.ticket_ids.append(ticket_id)
                return k
        # Final fallback: global English
        fallback = "global:en"
        if fallback in self._queues:
            self._queues[fallback].ticket_ids.append(ticket_id)
            return fallback
        return None

    def get_queue_status(self) -> List[Dict[str, Any]]:
        return [q.to_dict() for q in self._queues.values()]

    def get_supported_languages(self) -> List[str]:
        return SUPPORTED_LANGUAGES

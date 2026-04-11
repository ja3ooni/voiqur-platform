"""
Human Agent Handoff System

Graceful transfer of AI-handled calls to human agents with full context
and transcript preservation.
Implements Requirement 14.3.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentAvailability(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_BREAK = "on_break"


class HandoffReason(Enum):
    USER_REQUESTED = "user_requested"
    AI_ESCALATION = "ai_escalation"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    COMPLEX_QUERY = "complex_query"
    COMPLIANCE_REQUIRED = "compliance_required"
    TIMEOUT = "timeout"


class HandoffStatus(Enum):
    PENDING = "pending"
    AGENT_FOUND = "agent_found"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"


@dataclass
class HumanAgent:
    """Represents a human agent available for handoff."""

    agent_id: str
    name: str
    extension: str
    skills: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    availability: AgentAvailability = AgentAvailability.AVAILABLE
    active_calls: int = 0
    max_concurrent_calls: int = 1

    @property
    def is_available(self) -> bool:
        return (
            self.availability == AgentAvailability.AVAILABLE
            and self.active_calls < self.max_concurrent_calls
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "extension": self.extension,
            "skills": self.skills,
            "languages": self.languages,
            "availability": self.availability.value,
            "active_calls": self.active_calls,
        }


@dataclass
class HandoffContext:
    """Context transferred to the human agent during handoff."""

    call_id: str
    customer_number: str
    reason: HandoffReason
    transcript: List[Dict[str, str]] = field(default_factory=list)
    sentiment: Optional[str] = None
    detected_language: Optional[str] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    ai_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_transcript_turn(self, role: str, text: str) -> None:
        self.transcript.append(
            {"role": role, "text": text, "timestamp": datetime.utcnow().isoformat()}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "customer_number": self.customer_number,
            "reason": self.reason.value,
            "transcript": self.transcript,
            "sentiment": self.sentiment,
            "detected_language": self.detected_language,
            "intent": self.intent,
            "entities": self.entities,
            "ai_summary": self.ai_summary,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HandoffRecord:
    """Tracks the lifecycle of a handoff request."""

    handoff_id: str
    context: HandoffContext
    status: HandoffStatus = HandoffStatus.PENDING
    assigned_agent: Optional[HumanAgent] = None
    queued_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "status": self.status.value,
            "context": self.context.to_dict(),
            "assigned_agent": self.assigned_agent.to_dict() if self.assigned_agent else None,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "failure_reason": self.failure_reason,
        }


class AgentPool:
    """Manages the pool of available human agents."""

    def __init__(self):
        self._agents: Dict[str, HumanAgent] = {}
        self.logger = logging.getLogger(f"{__name__}.AgentPool")

    def register(self, agent: HumanAgent) -> None:
        self._agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def update_availability(
        self, agent_id: str, availability: AgentAvailability
    ) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].availability = availability

    def find_best_agent(
        self,
        required_skills: Optional[List[str]] = None,
        required_language: Optional[str] = None,
    ) -> Optional[HumanAgent]:
        """Select the best available agent matching skills and language."""
        candidates = [a for a in self._agents.values() if a.is_available]

        if required_language:
            lang_match = [
                a for a in candidates if required_language in a.languages
            ]
            if lang_match:
                candidates = lang_match

        if required_skills:
            skill_match = [
                a
                for a in candidates
                if any(s in a.skills for s in required_skills)
            ]
            if skill_match:
                candidates = skill_match

        if not candidates:
            return None

        # Prefer agent with fewest active calls
        return min(candidates, key=lambda a: a.active_calls)

    def get_all(self) -> List[HumanAgent]:
        return list(self._agents.values())

    def available_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.is_available)


class HandoffAgent:
    """
    Orchestrates graceful AI-to-human handoffs.

    Preserves full transcript and context, finds the best available agent,
    and performs the call transfer via the injected transfer function.
    """

    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        queue_timeout: float = 300.0,
    ):
        self.agent_pool = agent_pool or AgentPool()
        self.queue_timeout = queue_timeout
        self._records: Dict[str, HandoffRecord] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._transfer_fn: Optional[Callable] = None
        self._notify_fn: Optional[Callable] = None
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

    def set_transfer_function(self, fn: Callable) -> None:
        """
        Set the async function that performs the actual call transfer.
        Signature: async fn(call_id: str, destination: str) -> bool
        """
        self._transfer_fn = fn

    def set_notify_function(self, fn: Callable) -> None:
        """
        Set the async function that notifies the human agent of incoming handoff.
        Signature: async fn(agent: HumanAgent, context: HandoffContext) -> None
        """
        self._notify_fn = fn

    async def start(self) -> None:
        self._running = True
        self._worker_task = asyncio.ensure_future(self._queue_worker())
        self.logger.info("HandoffAgent started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def request_handoff(
        self,
        context: HandoffContext,
        required_skills: Optional[List[str]] = None,
    ) -> HandoffRecord:
        """
        Initiate a handoff request.

        Tries to find an available agent immediately; if none found, queues
        the request for retry.
        """
        handoff_id = str(uuid.uuid4())
        record = HandoffRecord(handoff_id=handoff_id, context=context)
        self._records[handoff_id] = record

        agent = self.agent_pool.find_best_agent(
            required_skills=required_skills,
            required_language=context.detected_language,
        )

        if agent:
            await self._execute_handoff(record, agent)
        else:
            record.status = HandoffStatus.QUEUED
            record.queued_at = datetime.utcnow()
            await self._queue.put((record, required_skills))
            self.logger.info(
                f"No agents available, queued handoff {handoff_id} "
                f"for call {context.call_id}"
            )

        return record

    async def _execute_handoff(
        self, record: HandoffRecord, agent: HumanAgent
    ) -> None:
        record.status = HandoffStatus.AGENT_FOUND
        record.assigned_agent = agent
        record.assigned_at = datetime.utcnow()
        agent.active_calls += 1

        self.logger.info(
            f"Handoff {record.handoff_id}: assigning to agent "
            f"{agent.agent_id} ({agent.name})"
        )

        try:
            # Notify the human agent with full context
            if self._notify_fn:
                await self._notify_fn(agent, record.context)

            # Perform the actual call transfer
            if self._transfer_fn:
                record.status = HandoffStatus.TRANSFERRING
                success = await self._transfer_fn(
                    record.context.call_id, agent.extension
                )
                if not success:
                    raise RuntimeError("Transfer function returned False")

            record.status = HandoffStatus.COMPLETED
            record.completed_at = datetime.utcnow()
            self.logger.info(f"Handoff {record.handoff_id} completed successfully")

        except Exception as e:
            record.status = HandoffStatus.FAILED
            record.failure_reason = str(e)
            agent.active_calls = max(0, agent.active_calls - 1)
            self.logger.error(f"Handoff {record.handoff_id} failed: {e}")

    async def _queue_worker(self) -> None:
        while self._running:
            try:
                record, required_skills = await asyncio.wait_for(
                    self._queue.get(), timeout=5.0
                )
                if record.status != HandoffStatus.QUEUED:
                    continue

                # Check if timed out
                if record.queued_at:
                    elapsed = (datetime.utcnow() - record.queued_at).total_seconds()
                    if elapsed > self.queue_timeout:
                        record.status = HandoffStatus.FAILED
                        record.failure_reason = "Queue timeout exceeded"
                        self.logger.warning(
                            f"Handoff {record.handoff_id} timed out in queue"
                        )
                        continue

                agent = self.agent_pool.find_best_agent(
                    required_skills=required_skills,
                    required_language=record.context.detected_language,
                )
                if agent:
                    await self._execute_handoff(record, agent)
                else:
                    # Re-queue
                    await self._queue.put((record, required_skills))
                    await asyncio.sleep(5.0)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Queue worker error: {e}")

    def complete_agent_call(self, agent_id: str) -> None:
        """Mark an agent's call as finished (decrement active count)."""
        agent = self.agent_pool._agents.get(agent_id)
        if agent:
            agent.active_calls = max(0, agent.active_calls - 1)

    def get_record(self, handoff_id: str) -> Optional[HandoffRecord]:
        return self._records.get(handoff_id)

    def get_analytics(self) -> Dict[str, Any]:
        records = list(self._records.values())
        completed = [r for r in records if r.status == HandoffStatus.COMPLETED]
        failed = [r for r in records if r.status == HandoffStatus.FAILED]
        queued = [r for r in records if r.status == HandoffStatus.QUEUED]

        avg_wait = 0.0
        wait_times = []
        for r in completed:
            if r.queued_at and r.assigned_at:
                wait_times.append(
                    (r.assigned_at - r.queued_at).total_seconds()
                )
        if wait_times:
            avg_wait = sum(wait_times) / len(wait_times)

        return {
            "total_handoffs": len(records),
            "completed": len(completed),
            "failed": len(failed),
            "queued": len(queued),
            "available_agents": self.agent_pool.available_count(),
            "total_agents": len(self.agent_pool.get_all()),
            "avg_wait_seconds": round(avg_wait, 2),
            "reasons": {
                reason.value: sum(
                    1 for r in records if r.context.reason == reason
                )
                for reason in HandoffReason
            },
        }

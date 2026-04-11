"""
Support Ticketing System — multi-channel ticket creation, priority routing,
SLA tracking, and agent dashboard.
Implements Requirements 19.1, 19.6.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class TicketPriority(Enum):
    P1 = "P1"   # Critical — <15 min response
    P2 = "P2"   # High — <1 hour
    P3 = "P3"   # Medium — <4 hours
    P4 = "P4"   # Low — <24 hours


class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketChannel(Enum):
    PHONE = "phone"
    EMAIL = "email"
    CHAT = "chat"
    PORTAL = "portal"
    API = "api"


# SLA response time targets in minutes
SLA_RESPONSE_MINUTES: Dict[TicketPriority, int] = {
    TicketPriority.P1: 15,
    TicketPriority.P2: 60,
    TicketPriority.P3: 240,
    TicketPriority.P4: 1440,
}

# SLA resolution time targets in minutes
SLA_RESOLUTION_MINUTES: Dict[TicketPriority, int] = {
    TicketPriority.P1: 60,
    TicketPriority.P2: 240,
    TicketPriority.P3: 1440,
    TicketPriority.P4: 5760,
}


@dataclass
class TicketComment:
    author: str
    body: str
    internal: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {"author": self.author, "body": self.body,
                "internal": self.internal, "created_at": self.created_at.isoformat()}


@dataclass
class Ticket:
    ticket_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: str = ""
    description: str = ""
    priority: TicketPriority = TicketPriority.P3
    status: TicketStatus = TicketStatus.OPEN
    channel: TicketChannel = TicketChannel.EMAIL
    tenant_id: str = ""
    customer_id: str = ""
    assigned_agent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    comments: List[TicketComment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def response_deadline(self) -> datetime:
        return self.created_at + timedelta(minutes=SLA_RESPONSE_MINUTES[self.priority])

    @property
    def resolution_deadline(self) -> datetime:
        return self.created_at + timedelta(minutes=SLA_RESOLUTION_MINUTES[self.priority])

    @property
    def response_breached(self) -> bool:
        if self.first_response_at:
            return self.first_response_at > self.response_deadline
        return datetime.utcnow() > self.response_deadline

    @property
    def resolution_breached(self) -> bool:
        if self.resolved_at:
            return self.resolved_at > self.resolution_deadline
        return (self.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
                and datetime.utcnow() > self.resolution_deadline)

    def add_comment(self, author: str, body: str, internal: bool = False) -> TicketComment:
        c = TicketComment(author=author, body=body, internal=internal)
        self.comments.append(c)
        if not self.first_response_at and not internal:
            self.first_response_at = c.created_at
        return c

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "subject": self.subject,
            "priority": self.priority.value,
            "status": self.status.value,
            "channel": self.channel.value,
            "tenant_id": self.tenant_id,
            "assigned_agent_id": self.assigned_agent_id,
            "created_at": self.created_at.isoformat(),
            "response_deadline": self.response_deadline.isoformat(),
            "resolution_deadline": self.resolution_deadline.isoformat(),
            "response_breached": self.response_breached,
            "resolution_breached": self.resolution_breached,
            "comment_count": len(self.comments),
        }


@dataclass
class SupportAgent:
    agent_id: str
    name: str
    email: str
    languages: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    max_tickets: int = 10
    active_tickets: int = 0
    available: bool = True

    @property
    def is_available(self) -> bool:
        return self.available and self.active_tickets < self.max_tickets

    def to_dict(self) -> Dict[str, Any]:
        return {"agent_id": self.agent_id, "name": self.name,
                "active_tickets": self.active_tickets, "available": self.available}


class TicketingSystem:
    """
    Core ticketing system with priority routing and agent assignment.
    """

    def __init__(self):
        self._tickets: Dict[str, Ticket] = {}
        self._agents: Dict[str, SupportAgent] = {}
        self._queues: Dict[TicketPriority, List[str]] = {p: [] for p in TicketPriority}

    def register_agent(self, agent: SupportAgent) -> None:
        self._agents[agent.agent_id] = agent

    def create_ticket(
        self,
        subject: str,
        description: str,
        priority: TicketPriority = TicketPriority.P3,
        channel: TicketChannel = TicketChannel.EMAIL,
        tenant_id: str = "",
        customer_id: str = "",
        **kwargs: Any,
    ) -> Ticket:
        ticket = Ticket(
            subject=subject, description=description,
            priority=priority, channel=channel,
            tenant_id=tenant_id, customer_id=customer_id,
            **kwargs,
        )
        self._tickets[ticket.ticket_id] = ticket
        self._queues[priority].append(ticket.ticket_id)
        self._auto_assign(ticket)
        return ticket

    def _auto_assign(self, ticket: Ticket) -> None:
        """Assign to least-loaded available agent."""
        candidates = [a for a in self._agents.values() if a.is_available]
        if not candidates:
            return
        agent = min(candidates, key=lambda a: a.active_tickets)
        ticket.assigned_agent_id = agent.agent_id
        agent.active_tickets += 1

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self._tickets.get(ticket_id)

    def update_status(self, ticket_id: str, status: TicketStatus) -> bool:
        t = self._tickets.get(ticket_id)
        if not t:
            return False
        t.status = status
        if status == TicketStatus.RESOLVED:
            t.resolved_at = datetime.utcnow()
            if t.assigned_agent_id and t.assigned_agent_id in self._agents:
                self._agents[t.assigned_agent_id].active_tickets = max(
                    0, self._agents[t.assigned_agent_id].active_tickets - 1
                )
        return True

    def get_breached_tickets(self) -> List[Ticket]:
        return [t for t in self._tickets.values()
                if t.response_breached or t.resolution_breached]

    def get_agent_dashboard(self, agent_id: str) -> Dict[str, Any]:
        tickets = [t for t in self._tickets.values() if t.assigned_agent_id == agent_id]
        return {
            "agent_id": agent_id,
            "total_assigned": len(tickets),
            "open": sum(1 for t in tickets if t.status == TicketStatus.OPEN),
            "in_progress": sum(1 for t in tickets if t.status == TicketStatus.IN_PROGRESS),
            "breached": sum(1 for t in tickets if t.response_breached or t.resolution_breached),
            "by_priority": {p.value: sum(1 for t in tickets if t.priority == p) for p in TicketPriority},
        }

    def get_queue_stats(self) -> Dict[str, Any]:
        return {
            "total_open": sum(len(q) for q in self._queues.values()),
            "by_priority": {p.value: len(q) for p, q in self._queues.items()},
            "available_agents": sum(1 for a in self._agents.values() if a.is_available),
        }

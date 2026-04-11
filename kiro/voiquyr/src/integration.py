"""
Platform Integration Layer — wires billing, omnichannel, workflow automation,
telephony, and analytics into a unified platform facade.
Implements Requirements 23.1 (13-22).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformEvent:
    """Unified event bus message."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""          # "telephony" | "omnichannel" | "workflow" | "billing" | "analytics"
    event_type: str = ""
    tenant_id: str = ""
    conversation_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "event_type": self.event_type,
            "tenant_id": self.tenant_id,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """Simple in-process pub/sub event bus."""

    def __init__(self):
        self._handlers: Dict[str, List[Any]] = {}

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Any) -> None:
        self._handlers.setdefault("*", []).append(handler)

    async def publish(self, event: PlatformEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error [{event.event_type}]: {e}")
        for handler in self._handlers.get("*", []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Global handler error: {e}")

    def get_subscriber_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))


class PlatformIntegration:
    """
    Wires all platform subsystems together via the event bus.

    Integration points:
    - Telephony call events → Analytics ingestion + Billing usage tracking
    - Omnichannel messages → Analytics ingestion + Workflow triggers
    - Workflow completions → Analytics KPI tracking + Billing
    - Support tickets → Analytics + SLA monitoring
    """

    def __init__(self):
        self.bus = EventBus()
        self._analytics_engine = None
        self._billing_service = None
        self._workflow_engine = None
        self._context_manager = None
        self._sla_manager = None
        self._dashboard = None
        self._wired = False

    def configure(
        self,
        analytics_engine=None,
        billing_service=None,
        workflow_engine=None,
        context_manager=None,
        sla_manager=None,
        dashboard=None,
    ) -> None:
        self._analytics_engine = analytics_engine
        self._billing_service = billing_service
        self._workflow_engine = workflow_engine
        self._context_manager = context_manager
        self._sla_manager = sla_manager
        self._dashboard = dashboard

    def wire(self) -> None:
        """Register all cross-component event handlers."""
        # Telephony → Analytics + Dashboard
        self.bus.subscribe("call.started", self._on_call_started)
        self.bus.subscribe("call.ended", self._on_call_ended)

        # Omnichannel → Analytics + Context + Workflow
        self.bus.subscribe("message.received", self._on_message_received)
        self.bus.subscribe("conversation.started", self._on_conversation_started)
        self.bus.subscribe("conversation.ended", self._on_conversation_ended)

        # Workflow → Analytics KPI
        self.bus.subscribe("workflow.completed", self._on_workflow_completed)

        # Support → SLA check
        self.bus.subscribe("ticket.created", self._on_ticket_created)

        self._wired = True
        logger.info("Platform integration wired")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_call_started(self, event: PlatformEvent) -> None:
        if self._dashboard:
            self._dashboard.conversation_started(
                event.conversation_id,
                event.payload.get("channel", "voice"),
                event.tenant_id,
            )

    def _on_call_ended(self, event: PlatformEvent) -> None:
        if self._dashboard:
            self._dashboard.conversation_ended(event.conversation_id)
        # Billing: record usage minutes
        if self._billing_service:
            try:
                duration_min = event.payload.get("duration_seconds", 0) / 60
                if hasattr(self._billing_service, "record_usage"):
                    self._billing_service.record_usage(
                        event.tenant_id, "voice_minutes", duration_min
                    )
            except Exception as e:
                logger.warning(f"Billing record_usage failed: {e}")

    def _on_message_received(self, event: PlatformEvent) -> None:
        if self._context_manager:
            try:
                from src.channels import UnifiedMessage, ChannelType, MessageDirection
                channel_str = event.payload.get("channel", "web_chat")
                try:
                    channel = ChannelType(channel_str)
                except ValueError:
                    channel = ChannelType.WEB_CHAT
                msg = UnifiedMessage(
                    channel=channel,
                    direction=MessageDirection.INBOUND,
                    conversation_id=event.conversation_id,
                    user_id=event.payload.get("user_id", ""),
                    text=event.payload.get("text", ""),
                )
                self._context_manager.ingest_message(msg)
            except Exception as e:
                logger.warning(f"Context ingest failed: {e}")

    def _on_conversation_started(self, event: PlatformEvent) -> None:
        if self._analytics_engine:
            try:
                from src.analytics import AnalyticsEvent, EventType
                self._analytics_engine.ingest(AnalyticsEvent(
                    event_id=event.event_id,
                    event_type=EventType.CONVERSATION_START,
                    conversation_id=event.conversation_id,
                    tenant_id=event.tenant_id,
                    channel=event.payload.get("channel", "unknown"),
                    timestamp=event.timestamp,
                ))
            except Exception as e:
                logger.warning(f"Analytics ingest failed: {e}")

    def _on_conversation_ended(self, event: PlatformEvent) -> None:
        if self._analytics_engine:
            try:
                from src.analytics import AnalyticsEvent, EventType
                self._analytics_engine.ingest(AnalyticsEvent(
                    event_id=event.event_id,
                    event_type=EventType.CONVERSATION_END,
                    conversation_id=event.conversation_id,
                    tenant_id=event.tenant_id,
                    channel=event.payload.get("channel", "unknown"),
                    timestamp=event.timestamp,
                    data={"completed": event.payload.get("completed", True)},
                ))
            except Exception as e:
                logger.warning(f"Analytics ingest failed: {e}")

    def _on_workflow_completed(self, event: PlatformEvent) -> None:
        if self._analytics_engine:
            try:
                self._analytics_engine.track_kpi(
                    event.tenant_id,
                    event.payload.get("kpi", "workflow_completed"),
                    event.payload.get("value", 1.0),
                    event.conversation_id or None,
                )
            except Exception as e:
                logger.warning(f"KPI tracking failed: {e}")

    def _on_ticket_created(self, event: PlatformEvent) -> None:
        if self._sla_manager:
            try:
                ticket = event.payload.get("ticket")
                if ticket:
                    self._sla_manager.check_ticket_sla(ticket)
            except Exception as e:
                logger.warning(f"SLA check failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "wired": self._wired,
            "components": {
                "analytics": self._analytics_engine is not None,
                "billing": self._billing_service is not None,
                "workflow": self._workflow_engine is not None,
                "context_manager": self._context_manager is not None,
                "sla_manager": self._sla_manager is not None,
                "dashboard": self._dashboard is not None,
            },
            "event_subscriptions": {
                k: len(v) for k, v in self.bus._handlers.items()
            },
        }

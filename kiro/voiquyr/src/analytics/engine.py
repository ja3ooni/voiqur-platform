"""
Conversation Analytics Engine — real-time metrics, volume, completion,
satisfaction, intent analytics, customer journey, sentiment, and KPIs.
Implements Requirements 22.1, 22.2, 22.3, 22.4.
"""

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Core event model
# ---------------------------------------------------------------------------

class EventType(Enum):
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    INTENT_MATCHED = "intent_matched"
    ENTITY_EXTRACTED = "entity_extracted"
    HANDOFF = "handoff"
    CONVERSION = "conversion"
    SATISFACTION_RATED = "satisfaction_rated"
    ERROR = "error"


@dataclass
class AnalyticsEvent:
    event_id: str
    event_type: EventType
    conversation_id: str
    tenant_id: str
    channel: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "channel": self.channel,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# ---------------------------------------------------------------------------
# 22.1 Conversation Analytics Engine
# ---------------------------------------------------------------------------

@dataclass
class ConversationMetrics:
    conversation_id: str
    tenant_id: str
    channel: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    turn_count: int = 0
    completed: bool = False
    converted: bool = False
    satisfaction_score: Optional[float] = None
    intents: List[str] = field(default_factory=list)
    sentiment_scores: List[float] = field(default_factory=list)
    drop_off_node: Optional[str] = None
    node_path: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return (datetime.utcnow() - self.started_at).total_seconds()

    @property
    def avg_sentiment(self) -> Optional[float]:
        return statistics.mean(self.sentiment_scores) if self.sentiment_scores else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "channel": self.channel,
            "turn_count": self.turn_count,
            "completed": self.completed,
            "converted": self.converted,
            "satisfaction_score": self.satisfaction_score,
            "duration_seconds": round(self.duration_seconds, 2),
            "avg_sentiment": self.avg_sentiment,
            "intents": self.intents,
        }


class ConversationAnalyticsEngine:
    """
    Collects and aggregates conversation analytics in real-time.
    """

    def __init__(self):
        self._conversations: Dict[str, ConversationMetrics] = {}
        self._events: List[AnalyticsEvent] = []

    def ingest(self, event: AnalyticsEvent) -> None:
        self._events.append(event)
        cid = event.conversation_id

        if event.event_type == EventType.CONVERSATION_START:
            self._conversations[cid] = ConversationMetrics(
                conversation_id=cid,
                tenant_id=event.tenant_id,
                channel=event.channel,
                started_at=event.timestamp,
            )

        elif event.event_type == EventType.CONVERSATION_END:
            if cid in self._conversations:
                c = self._conversations[cid]
                c.ended_at = event.timestamp
                c.completed = event.data.get("completed", True)

        elif event.event_type == EventType.MESSAGE_RECEIVED:
            if cid in self._conversations:
                self._conversations[cid].turn_count += 1

        elif event.event_type == EventType.INTENT_MATCHED:
            if cid in self._conversations:
                intent = event.data.get("intent", "")
                if intent:
                    self._conversations[cid].intents.append(intent)

        elif event.event_type == EventType.CONVERSION:
            if cid in self._conversations:
                self._conversations[cid].converted = True

        elif event.event_type == EventType.SATISFACTION_RATED:
            if cid in self._conversations:
                self._conversations[cid].satisfaction_score = event.data.get("score")

    def get_volume_metrics(
        self,
        tenant_id: str,
        since: Optional[datetime] = None,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        convs = [
            c for c in self._conversations.values()
            if c.tenant_id == tenant_id
            and (since is None or c.started_at >= since)
            and (channel is None or c.channel == channel)
        ]
        completed = [c for c in convs if c.completed]
        converted = [c for c in convs if c.converted]
        sat_scores = [c.satisfaction_score for c in convs if c.satisfaction_score is not None]
        durations = [c.duration_seconds for c in completed]

        return {
            "total_conversations": len(convs),
            "completed": len(completed),
            "completion_rate": len(completed) / len(convs) if convs else 0.0,
            "conversions": len(converted),
            "conversion_rate": len(converted) / len(convs) if convs else 0.0,
            "avg_satisfaction": statistics.mean(sat_scores) if sat_scores else None,
            "avg_duration_seconds": statistics.mean(durations) if durations else None,
            "avg_turns": statistics.mean(c.turn_count for c in convs) if convs else None,
        }

    def get_intent_analytics(self, tenant_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for c in self._conversations.values():
            if c.tenant_id == tenant_id:
                for intent in c.intents:
                    counts[intent] += 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    # ------------------------------------------------------------------
    # 22.2 Customer Journey Analysis
    # ------------------------------------------------------------------

    def get_journey_paths(self, tenant_id: str) -> List[Dict[str, Any]]:
        return [
            {
                "conversation_id": c.conversation_id,
                "channel": c.channel,
                "node_path": c.node_path,
                "drop_off_node": c.drop_off_node,
                "completed": c.completed,
            }
            for c in self._conversations.values()
            if c.tenant_id == tenant_id and c.node_path
        ]

    def get_drop_off_analysis(self, tenant_id: str) -> Dict[str, int]:
        drop_offs: Dict[str, int] = defaultdict(int)
        for c in self._conversations.values():
            if c.tenant_id == tenant_id and not c.completed and c.drop_off_node:
                drop_offs[c.drop_off_node] += 1
        return dict(sorted(drop_offs.items(), key=lambda x: x[1], reverse=True))

    def get_conversion_funnel(
        self, tenant_id: str, stages: List[str]
    ) -> List[Dict[str, Any]]:
        """Count conversations that reached each stage node."""
        funnel = []
        total = len([c for c in self._conversations.values() if c.tenant_id == tenant_id])
        for stage in stages:
            reached = sum(
                1 for c in self._conversations.values()
                if c.tenant_id == tenant_id and stage in c.node_path
            )
            funnel.append({
                "stage": stage,
                "count": reached,
                "rate": reached / total if total else 0.0,
            })
        return funnel

    def get_cohort_analysis(
        self, tenant_id: str, period_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Group conversations by week cohort and compute completion rates."""
        cohorts: Dict[str, List[ConversationMetrics]] = defaultdict(list)
        for c in self._conversations.values():
            if c.tenant_id != tenant_id:
                continue
            week = c.started_at.isocalendar()[:2]
            cohorts[f"{week[0]}-W{week[1]:02d}"].append(c)
        return [
            {
                "cohort": k,
                "conversations": len(v),
                "completion_rate": sum(1 for c in v if c.completed) / len(v),
                "conversion_rate": sum(1 for c in v if c.converted) / len(v),
            }
            for k, v in sorted(cohorts.items())
        ]

    # ------------------------------------------------------------------
    # 22.3 Sentiment & Emotion Analytics
    # ------------------------------------------------------------------

    def record_sentiment(
        self, conversation_id: str, score: float, topic: Optional[str] = None
    ) -> None:
        """score: -1.0 (negative) to +1.0 (positive)"""
        if conversation_id in self._conversations:
            self._conversations[conversation_id].sentiment_scores.append(score)

    def get_sentiment_trends(
        self, tenant_id: str, bucket_hours: int = 1
    ) -> List[Dict[str, Any]]:
        buckets: Dict[datetime, List[float]] = defaultdict(list)
        for c in self._conversations.values():
            if c.tenant_id != tenant_id or not c.sentiment_scores:
                continue
            bucket = c.started_at.replace(
                minute=0, second=0, microsecond=0,
                hour=(c.started_at.hour // bucket_hours) * bucket_hours
            )
            buckets[bucket].extend(c.sentiment_scores)
        return [
            {
                "timestamp": ts.isoformat(),
                "avg_sentiment": round(statistics.mean(scores), 3),
                "sample_count": len(scores),
            }
            for ts, scores in sorted(buckets.items())
        ]

    def get_sentiment_by_channel(self, tenant_id: str) -> Dict[str, float]:
        by_channel: Dict[str, List[float]] = defaultdict(list)
        for c in self._conversations.values():
            if c.tenant_id == tenant_id and c.sentiment_scores:
                by_channel[c.channel].extend(c.sentiment_scores)
        return {
            ch: round(statistics.mean(scores), 3)
            for ch, scores in by_channel.items()
        }

    # ------------------------------------------------------------------
    # 22.4 Business Outcome Tracking
    # ------------------------------------------------------------------

    def track_kpi(
        self,
        tenant_id: str,
        kpi_name: str,
        value: float,
        conversation_id: Optional[str] = None,
    ) -> None:
        self._events.append(AnalyticsEvent(
            event_id=f"kpi-{len(self._events)}",
            event_type=EventType.CONVERSION,
            conversation_id=conversation_id or "",
            tenant_id=tenant_id,
            channel="system",
            timestamp=datetime.utcnow(),
            data={"kpi": kpi_name, "value": value},
        ))

    def get_kpi_summary(self, tenant_id: str) -> Dict[str, Any]:
        kpi_events = [
            e for e in self._events
            if e.tenant_id == tenant_id
            and e.event_type == EventType.CONVERSION
            and "kpi" in e.data
        ]
        by_kpi: Dict[str, List[float]] = defaultdict(list)
        for e in kpi_events:
            by_kpi[e.data["kpi"]].append(e.data["value"])
        return {
            kpi: {
                "count": len(vals),
                "total": round(sum(vals), 2),
                "avg": round(statistics.mean(vals), 2),
            }
            for kpi, vals in by_kpi.items()
        }

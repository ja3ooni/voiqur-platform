"""
Omnichannel Analytics — unified dashboard, customer journey, channel metrics.
Implements Requirement 17.5.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ChannelType, MessageDirection, UnifiedMessage
from .context import ContextManager


@dataclass
class ChannelMetrics:
    channel: ChannelType
    total_messages: int = 0
    inbound: int = 0
    outbound: int = 0
    unique_users: int = 0
    avg_response_time_s: float = 0.0
    delivery_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "total_messages": self.total_messages,
            "inbound": self.inbound,
            "outbound": self.outbound,
            "unique_users": self.unique_users,
            "avg_response_time_s": round(self.avg_response_time_s, 2),
            "delivery_rate": round(self.delivery_rate, 4),
        }


class OmnichannelAnalytics:
    """
    Collects and aggregates omnichannel metrics from the ContextManager.
    """

    def __init__(self, context_manager: ContextManager):
        self._ctx = context_manager
        self._response_times: Dict[str, List[float]] = defaultdict(list)

    def record_response_time(self, channel: ChannelType, seconds: float) -> None:
        self._response_times[channel.value].append(seconds)

    def get_channel_metrics(self) -> List[ChannelMetrics]:
        counts: Dict[str, ChannelMetrics] = {}
        users_per_channel: Dict[str, set] = defaultdict(set)

        for ctx in self._ctx._contexts.values():
            for msg in ctx.messages:
                ch = msg.channel.value
                if ch not in counts:
                    counts[ch] = ChannelMetrics(channel=msg.channel)
                m = counts[ch]
                m.total_messages += 1
                if msg.direction == MessageDirection.INBOUND:
                    m.inbound += 1
                else:
                    m.outbound += 1
                users_per_channel[ch].add(ctx.user_id)

        for ch, m in counts.items():
            m.unique_users = len(users_per_channel[ch])
            times = self._response_times.get(ch, [])
            if times:
                m.avg_response_time_s = sum(times) / len(times)

        return list(counts.values())

    def get_customer_journeys(self) -> List[Dict[str, Any]]:
        """Return channel journey per conversation."""
        journeys = []
        for ctx in self._ctx._contexts.values():
            if not ctx.messages:
                continue
            journey = [ctx.messages[0].channel.value]
            for msg in ctx.messages[1:]:
                if msg.channel.value != journey[-1]:
                    journey.append(msg.channel.value)
            journeys.append({
                "conversation_id": ctx.conversation_id,
                "user_id": ctx.user_id,
                "journey": journey,
                "channel_switches": len(journey) - 1,
                "message_count": len(ctx.messages),
            })
        return journeys

    def get_cross_channel_attribution(self) -> Dict[str, int]:
        """Count how many conversations started on each channel."""
        attribution: Dict[str, int] = defaultdict(int)
        for ctx in self._ctx._contexts.values():
            if ctx.messages:
                attribution[ctx.messages[0].channel.value] += 1
        return dict(attribution)

    def get_dashboard(self) -> Dict[str, Any]:
        metrics = self.get_channel_metrics()
        journeys = self.get_customer_journeys()
        cross_channel = [j for j in journeys if j["channel_switches"] > 0]
        return {
            "total_conversations": len(self._ctx._contexts),
            "total_users": len(self._ctx._profiles),
            "cross_channel_users": len(self._ctx.get_cross_channel_users()),
            "channel_metrics": [m.to_dict() for m in metrics],
            "channel_preferences": self._ctx.get_channel_preferences(),
            "cross_channel_attribution": self.get_cross_channel_attribution(),
            "cross_channel_journeys": len(cross_channel),
            "generated_at": datetime.utcnow().isoformat(),
        }

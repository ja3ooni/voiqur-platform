"""
Provider Failover & Load Balancing — automatic failover, health checking,
load balancing strategies, and cost-based routing.
Implements Requirement 20.6.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .base import (
    CallSession, HealthStatus, ProviderType, TelephonyProvider,
)
from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    PRIORITY = "priority"
    COST_BASED = "cost_based"
    LATENCY_BASED = "latency_based"


@dataclass
class ProviderStats:
    provider_id: str
    total_calls: int = 0
    failed_calls: int = 0
    active_calls: int = 0
    avg_latency_ms: float = 0.0
    cost_per_minute_eur: float = 0.0
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return 1.0 - (self.failed_calls / self.total_calls)

    @property
    def score(self) -> float:
        """Lower is better for routing selection."""
        return (
            self.active_calls * 10
            + self.cost_per_minute_eur * 100
            + self.avg_latency_ms * 0.1
            + self.consecutive_failures * 50
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "active_calls": self.active_calls,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "cost_per_minute_eur": self.cost_per_minute_eur,
            "consecutive_failures": self.consecutive_failures,
        }


class ProviderFailoverManager:
    """
    Manages automatic failover, health checking, and load balancing
    across multiple telephony providers.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED,
        health_check_interval: float = 30.0,
        failure_threshold: int = 3,
    ):
        self.registry = registry
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.failure_threshold = failure_threshold
        self._stats: Dict[str, ProviderStats] = {}
        self._round_robin_idx: int = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

    def register_provider_cost(self, provider_id: str, cost_per_minute_eur: float) -> None:
        self._get_stats(provider_id).cost_per_minute_eur = cost_per_minute_eur

    def _get_stats(self, provider_id: str) -> ProviderStats:
        if provider_id not in self._stats:
            self._stats[provider_id] = ProviderStats(provider_id=provider_id)
        return self._stats[provider_id]

    def select_provider(
        self,
        provider_type: Optional[ProviderType] = None,
        exclude: Optional[List[str]] = None,
    ) -> Optional[TelephonyProvider]:
        """Select the best provider based on the routing strategy."""
        exclude = exclude or []
        candidates = [
            p for p in self.registry.get_healthy_providers()
            if p.config.enabled
            and p.config.provider_id not in exclude
            and (provider_type is None or p.config.provider_type == provider_type)
        ]
        if not candidates:
            return None

        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            p = candidates[self._round_robin_idx % len(candidates)]
            self._round_robin_idx += 1
            return p

        if self.strategy == RoutingStrategy.LEAST_LOADED:
            return min(candidates, key=lambda p: len(p.get_active_calls()))

        if self.strategy == RoutingStrategy.PRIORITY:
            return min(candidates, key=lambda p: p.config.priority)

        if self.strategy in (RoutingStrategy.COST_BASED, RoutingStrategy.LATENCY_BASED):
            return min(candidates, key=lambda p: self._get_stats(p.config.provider_id).score)

        return candidates[0]

    async def make_call_with_failover(
        self,
        from_number: str,
        to_number: str,
        provider_type: Optional[ProviderType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> Optional[CallSession]:
        """Attempt call with automatic failover on failure."""
        tried: List[str] = []
        for attempt in range(max_attempts):
            provider = self.select_provider(provider_type, exclude=tried)
            if not provider:
                self.logger.error("No healthy providers available for failover")
                break
            pid = provider.config.provider_id
            stats = self._get_stats(pid)
            t0 = time.monotonic()
            try:
                call = await provider.make_call(from_number, to_number, metadata)
                latency = (time.monotonic() - t0) * 1000
                stats.total_calls += 1
                stats.active_calls += 1
                stats.consecutive_failures = 0
                stats.avg_latency_ms = (stats.avg_latency_ms * 0.9 + latency * 0.1)
                self.logger.info(
                    f"Call placed via {pid} (attempt {attempt + 1})"
                )
                return call
            except Exception as e:
                stats.total_calls += 1
                stats.failed_calls += 1
                stats.consecutive_failures += 1
                tried.append(pid)
                self.logger.warning(
                    f"Provider {pid} failed (attempt {attempt + 1}): {e}"
                )
                if stats.consecutive_failures >= self.failure_threshold:
                    provider.health_status = HealthStatus.UNHEALTHY
                    self.logger.error(f"Provider {pid} marked unhealthy")
        return None

    def record_call_ended(self, provider_id: str, success: bool = True) -> None:
        stats = self._get_stats(provider_id)
        stats.active_calls = max(0, stats.active_calls - 1)
        if not success:
            stats.failed_calls += 1

    async def start_health_monitoring(self) -> None:
        self._running = True
        self._task = asyncio.ensure_future(self._health_loop())

    async def stop_health_monitoring(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _health_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.health_check_interval)
            for provider in self.registry.get_all_providers():
                try:
                    status = await provider.health_check()
                    stats = self._get_stats(provider.config.provider_id)
                    stats.last_health_check = datetime.utcnow()
                    if status == HealthStatus.HEALTHY:
                        stats.consecutive_failures = 0
                except Exception as e:
                    self.logger.warning(
                        f"Health check failed for {provider.config.provider_id}: {e}"
                    )

    def get_provider_stats(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._stats.values()]

    def get_routing_report(self) -> Dict[str, Any]:
        providers = self.registry.get_all_providers()
        healthy = self.registry.get_healthy_providers()
        return {
            "strategy": self.strategy.value,
            "total_providers": len(providers),
            "healthy_providers": len(healthy),
            "provider_stats": self.get_provider_stats(),
        }

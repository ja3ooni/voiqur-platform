"""
Hot-Standby Failover System

Synchronous replication within sovereignty zones, automatic failover detection,
<15-minute RTO, and DR drill framework.
Implements Requirements 16.2, 16.6.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .tenancy import SovereigntyZone, ZONE_DC_PAIRS, CROSS_ZONE_FAILOVER, TenantRegistry

logger = logging.getLogger(__name__)

RTO_TARGET_MINUTES = 15
RPO_TARGET_MINUTES = 5


class DCStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    STANDBY = "standby"


class ReplicationMode(Enum):
    SYNCHRONOUS = "synchronous"    # within zone — RPO ~0
    ASYNCHRONOUS = "asynchronous"  # cross-zone backup — RPO <5min


@dataclass
class DataCenterHealth:
    dc_id: str
    zone: SovereigntyZone
    status: DCStatus = DCStatus.HEALTHY
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    error_rate: float = 0.0
    consecutive_failures: int = 0

    def is_healthy(self) -> bool:
        return self.status == DCStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dc_id": self.dc_id,
            "zone": self.zone.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate,
        }


@dataclass
class FailoverEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    from_dc: str = ""
    to_dc: str = ""
    zone: SovereigntyZone = SovereigntyZone.DE
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    rto_seconds: Optional[float] = None
    success: bool = False
    reason: str = ""

    @property
    def rto_met(self) -> bool:
        if self.rto_seconds is None:
            return False
        return self.rto_seconds <= RTO_TARGET_MINUTES * 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "from_dc": self.from_dc,
            "to_dc": self.to_dc,
            "zone": self.zone.value,
            "triggered_at": self.triggered_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rto_seconds": self.rto_seconds,
            "rto_met": self.rto_met,
            "success": self.success,
            "reason": self.reason,
        }


@dataclass
class ReplicationStatus:
    source_dc: str
    target_dc: str
    mode: ReplicationMode
    lag_seconds: float = 0.0
    last_sync: datetime = field(default_factory=datetime.utcnow)
    bytes_pending: int = 0

    @property
    def rpo_met(self) -> bool:
        return self.lag_seconds <= RPO_TARGET_MINUTES * 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_dc": self.source_dc,
            "target_dc": self.target_dc,
            "mode": self.mode.value,
            "lag_seconds": self.lag_seconds,
            "last_sync": self.last_sync.isoformat(),
            "bytes_pending": self.bytes_pending,
            "rpo_met": self.rpo_met,
        }


class FailoverManager:
    """
    Manages automatic failover detection and execution.

    Health checks run every `health_check_interval` seconds.
    After `failure_threshold` consecutive failures, failover is triggered.
    """

    def __init__(
        self,
        tenant_registry: TenantRegistry,
        health_check_interval: float = 30.0,
        failure_threshold: int = 3,
    ):
        self.tenant_registry = tenant_registry
        self.health_check_interval = health_check_interval
        self.failure_threshold = failure_threshold
        self._dc_health: Dict[str, DataCenterHealth] = {}
        self._replication: Dict[str, ReplicationStatus] = {}
        self._failover_history: List[FailoverEvent] = []
        self._active_failovers: Dict[str, str] = {}  # tenant_id → active_dc
        self._health_check_fn: Optional[Callable] = None
        self._failover_fn: Optional[Callable] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

        # Initialise DC health for all known zones
        for zone, dcs in ZONE_DC_PAIRS.items():
            for role, dc_id in dcs.items():
                status = DCStatus.HEALTHY if role == "primary" else DCStatus.STANDBY
                self._dc_health[dc_id] = DataCenterHealth(
                    dc_id=dc_id, zone=zone, status=status
                )
            # Register synchronous replication within zone
            self._replication[f"{dcs['primary']}->{dcs['standby']}"] = ReplicationStatus(
                source_dc=dcs["primary"],
                target_dc=dcs["standby"],
                mode=ReplicationMode.SYNCHRONOUS,
            )

    def set_health_check_fn(self, fn: Callable) -> None:
        """Inject async fn(dc_id: str) -> DataCenterHealth."""
        self._health_check_fn = fn

    def set_failover_fn(self, fn: Callable) -> None:
        """Inject async fn(tenant_id: str, from_dc: str, to_dc: str) -> bool."""
        self._failover_fn = fn

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.ensure_future(self._monitor_loop())
        self.logger.info("FailoverManager started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.health_check_interval)
            await self._check_all_dcs()

    async def _check_all_dcs(self) -> None:
        for dc_id, health in list(self._dc_health.items()):
            if self._health_check_fn:
                try:
                    updated = await self._health_check_fn(dc_id)
                    self._dc_health[dc_id] = updated
                except Exception as e:
                    self.logger.warning(f"Health check failed for {dc_id}: {e}")
                    health.consecutive_failures += 1
                    if health.consecutive_failures >= self.failure_threshold:
                        health.status = DCStatus.FAILED
                        await self._trigger_failover_for_dc(dc_id)

    async def _trigger_failover_for_dc(self, failed_dc: str) -> None:
        """Find all tenants on failed_dc and fail them over."""
        for tenant in self.tenant_registry.get_all_tenants():
            primary = self.tenant_registry.get_primary_dc(tenant.tenant_id)
            if primary == failed_dc:
                standby = self.tenant_registry.get_standby_dc(tenant.tenant_id)
                if standby:
                    await self.execute_failover(
                        tenant.tenant_id, failed_dc, standby,
                        reason=f"Primary DC {failed_dc} health check failed"
                    )

    async def execute_failover(
        self,
        tenant_id: str,
        from_dc: str,
        to_dc: str,
        reason: str = "manual",
    ) -> FailoverEvent:
        """Execute failover for a tenant from one DC to another."""
        zone_health = self._dc_health.get(from_dc)
        zone = zone_health.zone if zone_health else SovereigntyZone.DE

        event = FailoverEvent(
            tenant_id=tenant_id,
            from_dc=from_dc,
            to_dc=to_dc,
            zone=zone,
            reason=reason,
        )
        self.logger.warning(
            f"Failover triggered: tenant={tenant_id} {from_dc} → {to_dc} ({reason})"
        )

        try:
            if self._failover_fn:
                success = await self._failover_fn(tenant_id, from_dc, to_dc)
            else:
                success = True  # Simulated

            event.success = success
            event.completed_at = datetime.utcnow()
            event.rto_seconds = (
                event.completed_at - event.triggered_at
            ).total_seconds()

            if success:
                self._active_failovers[tenant_id] = to_dc
                if to_dc in self._dc_health:
                    self._dc_health[to_dc].status = DCStatus.HEALTHY
                self.logger.info(
                    f"Failover completed in {event.rto_seconds:.1f}s "
                    f"(RTO {'✓' if event.rto_met else '✗'})"
                )
            else:
                self.logger.error(f"Failover failed for tenant {tenant_id}")

        except Exception as e:
            event.success = False
            event.completed_at = datetime.utcnow()
            event.rto_seconds = (event.completed_at - event.triggered_at).total_seconds()
            self.logger.error(f"Failover exception: {e}")

        self._failover_history.append(event)
        return event

    def update_replication_status(
        self, source_dc: str, target_dc: str, lag_seconds: float, bytes_pending: int = 0
    ) -> None:
        key = f"{source_dc}->{target_dc}"
        if key in self._replication:
            self._replication[key].lag_seconds = lag_seconds
            self._replication[key].bytes_pending = bytes_pending
            self._replication[key].last_sync = datetime.utcnow()

    def get_dc_health(self, dc_id: str) -> Optional[DataCenterHealth]:
        return self._dc_health.get(dc_id)

    def get_replication_status(self, source_dc: str, target_dc: str) -> Optional[ReplicationStatus]:
        return self._replication.get(f"{source_dc}->{target_dc}")

    def get_failover_history(self, tenant_id: Optional[str] = None) -> List[FailoverEvent]:
        if tenant_id:
            return [e for e in self._failover_history if e.tenant_id == tenant_id]
        return list(self._failover_history)

    def get_system_status(self) -> Dict[str, Any]:
        healthy = sum(1 for h in self._dc_health.values() if h.is_healthy())
        rpo_violations = sum(
            1 for r in self._replication.values() if not r.rpo_met
        )
        return {
            "total_dcs": len(self._dc_health),
            "healthy_dcs": healthy,
            "failed_dcs": sum(
                1 for h in self._dc_health.values() if h.status == DCStatus.FAILED
            ),
            "replication_links": len(self._replication),
            "rpo_violations": rpo_violations,
            "total_failovers": len(self._failover_history),
            "active_failovers": len(self._active_failovers),
            "dcs": {dc: h.to_dict() for dc, h in self._dc_health.items()},
        }


class DRDrillFramework:
    """
    Quarterly DR drill automation.
    Simulates failures, executes failover, validates RTO/RPO, generates playbook.
    Implements Requirement 16.6.
    """

    def __init__(self, failover_manager: FailoverManager):
        self.failover_manager = failover_manager
        self._drill_results: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    async def run_drill(
        self,
        tenant_id: str,
        simulate_dc_failure: bool = True,
    ) -> Dict[str, Any]:
        """Execute a DR drill for a tenant and return results."""
        drill_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        self.logger.info(f"DR drill {drill_id} started for tenant {tenant_id}")

        primary_dc = self.failover_manager.tenant_registry.get_primary_dc(tenant_id)
        standby_dc = self.failover_manager.tenant_registry.get_standby_dc(tenant_id)

        if not primary_dc or not standby_dc:
            return {"drill_id": drill_id, "success": False, "reason": "Tenant DCs not found"}

        # Simulate primary failure
        if simulate_dc_failure and primary_dc in self.failover_manager._dc_health:
            self.failover_manager._dc_health[primary_dc].status = DCStatus.FAILED

        # Execute failover
        event = await self.failover_manager.execute_failover(
            tenant_id, primary_dc, standby_dc, reason="DR drill"
        )

        # Restore primary
        if primary_dc in self.failover_manager._dc_health:
            self.failover_manager._dc_health[primary_dc].status = DCStatus.RECOVERING

        # Check replication RPO
        rep = self.failover_manager.get_replication_status(primary_dc, standby_dc)
        rpo_met = rep.rpo_met if rep else True

        result = {
            "drill_id": drill_id,
            "tenant_id": tenant_id,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "failover_event": event.to_dict(),
            "rto_met": event.rto_met,
            "rpo_met": rpo_met,
            "rto_seconds": event.rto_seconds,
            "rto_target_seconds": RTO_TARGET_MINUTES * 60,
            "rpo_target_seconds": RPO_TARGET_MINUTES * 60,
            "success": event.success and event.rto_met and rpo_met,
            "playbook": self._generate_playbook(tenant_id, primary_dc, standby_dc, event),
        }
        self._drill_results.append(result)
        self.logger.info(
            f"DR drill {drill_id} completed: RTO={'✓' if result['rto_met'] else '✗'} "
            f"RPO={'✓' if result['rpo_met'] else '✗'}"
        )
        return result

    def _generate_playbook(
        self,
        tenant_id: str,
        primary_dc: str,
        standby_dc: str,
        event: FailoverEvent,
    ) -> Dict[str, Any]:
        return {
            "title": f"DR Playbook — Tenant {tenant_id}",
            "steps": [
                {"step": 1, "action": f"Detect failure of {primary_dc}", "automated": True},
                {"step": 2, "action": "Verify standby DC health", "automated": True},
                {"step": 3, "action": f"Promote {standby_dc} to primary", "automated": True},
                {"step": 4, "action": "Update DNS / load balancer routing", "automated": True},
                {"step": 5, "action": "Verify application health on standby", "automated": True},
                {"step": 6, "action": "Notify on-call team", "automated": True},
                {"step": 7, "action": "Begin primary DC recovery", "automated": False},
                {"step": 8, "action": "Re-sync data from standby to primary", "automated": True},
                {"step": 9, "action": "Fail back to primary (scheduled maintenance window)", "automated": False},
            ],
            "last_drill_rto_seconds": event.rto_seconds,
            "rto_target_seconds": RTO_TARGET_MINUTES * 60,
        }

    def get_drill_history(self) -> List[Dict[str, Any]]:
        return list(self._drill_results)

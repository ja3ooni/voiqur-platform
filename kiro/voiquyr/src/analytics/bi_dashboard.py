"""
BI Tool Integration — CSV/Excel export, Tableau, Power BI, Looker connectors,
and custom analytics API.
Implements Requirement 22.6.

Real-time Monitoring Dashboard — live metrics, queue depth, agent availability,
system health, and alert management.
Implements Requirement 22.7.
"""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 22.6 BI Tool Integration
# ---------------------------------------------------------------------------

class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"   # CSV-compatible for simplicity without openpyxl dep


class BIConnectorType(Enum):
    TABLEAU = "tableau"
    POWER_BI = "power_bi"
    LOOKER = "looker"
    CUSTOM = "custom"


@dataclass
class DataExport:
    export_id: str
    format: ExportFormat
    tenant_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    row_count: int = 0
    content: str = ""   # CSV/JSON string

    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_id": self.export_id,
            "format": self.format.value,
            "tenant_id": self.tenant_id,
            "row_count": self.row_count,
            "created_at": self.created_at.isoformat(),
        }


class BIExporter:
    """Exports analytics data to CSV, JSON, and BI-tool-compatible formats."""

    def export_conversations(
        self,
        conversations: List[Dict[str, Any]],
        fmt: ExportFormat = ExportFormat.CSV,
        tenant_id: str = "",
    ) -> DataExport:
        import uuid
        export_id = str(uuid.uuid4())

        if fmt in (ExportFormat.CSV, ExportFormat.EXCEL):
            content = self._to_csv(conversations)
        else:
            content = json.dumps(conversations, indent=2, default=str)

        return DataExport(
            export_id=export_id,
            format=fmt,
            tenant_id=tenant_id,
            row_count=len(conversations),
            content=content,
        )

    def _to_csv(self, rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    def get_tableau_extract(
        self, conversations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tableau Hyper API-compatible JSON structure."""
        return {
            "type": "tableau_extract",
            "schema": {
                "columns": list(conversations[0].keys()) if conversations else [],
            },
            "rows": conversations,
            "row_count": len(conversations),
        }

    def get_power_bi_dataset(
        self, conversations: List[Dict[str, Any]], dataset_name: str = "VoiQyr Analytics"
    ) -> Dict[str, Any]:
        """Power BI REST API push dataset format."""
        if not conversations:
            return {}
        columns = [{"name": k, "dataType": "String"} for k in conversations[0].keys()]
        return {
            "name": dataset_name,
            "tables": [
                {
                    "name": "Conversations",
                    "columns": columns,
                    "rows": conversations,
                }
            ],
        }

    def get_looker_explore(
        self, conversations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Looker API-compatible explore format."""
        return {
            "model": "voiquyr",
            "explore": "conversations",
            "fields": list(conversations[0].keys()) if conversations else [],
            "data": conversations,
        }


# ---------------------------------------------------------------------------
# 22.7 Real-time Monitoring Dashboard
# ---------------------------------------------------------------------------

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DashboardAlert:
    alert_id: str
    metric: str
    message: str
    severity: AlertSeverity
    value: float
    threshold: float
    tenant_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "metric": self.metric,
            "message": self.message,
            "severity": self.severity.value,
            "value": self.value,
            "threshold": self.threshold,
            "resolved": self.resolved,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class QueueMetrics:
    channel: str
    depth: int = 0
    avg_wait_seconds: float = 0.0
    oldest_wait_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "depth": self.depth,
            "avg_wait_seconds": round(self.avg_wait_seconds, 1),
            "oldest_wait_seconds": round(self.oldest_wait_seconds, 1),
        }


class RealtimeDashboard:
    """
    Live monitoring dashboard aggregating conversation, queue,
    agent, and system health metrics.
    """

    def __init__(self):
        self._live_conversations: Dict[str, Dict[str, Any]] = {}
        self._queue_metrics: Dict[str, QueueMetrics] = {}
        self._agent_status: Dict[str, Dict[str, Any]] = {}
        self._system_health: Dict[str, float] = {}
        self._alerts: List[DashboardAlert] = []
        self._alert_thresholds: Dict[str, float] = {
            "queue_depth": 50,
            "avg_wait_seconds": 120,
            "error_rate": 0.05,
            "cpu_pct": 85.0,
            "memory_pct": 90.0,
        }

    # ------------------------------------------------------------------
    # Live conversation tracking
    # ------------------------------------------------------------------

    def conversation_started(self, conv_id: str, channel: str, tenant_id: str) -> None:
        self._live_conversations[conv_id] = {
            "conv_id": conv_id, "channel": channel,
            "tenant_id": tenant_id, "started_at": datetime.utcnow().isoformat(),
        }

    def conversation_ended(self, conv_id: str) -> None:
        self._live_conversations.pop(conv_id, None)

    def get_live_count(self, tenant_id: Optional[str] = None) -> int:
        if tenant_id:
            return sum(1 for c in self._live_conversations.values()
                       if c["tenant_id"] == tenant_id)
        return len(self._live_conversations)

    # ------------------------------------------------------------------
    # Queue depth monitoring
    # ------------------------------------------------------------------

    def update_queue(self, channel: str, depth: int,
                     avg_wait: float = 0.0, oldest_wait: float = 0.0) -> None:
        self._queue_metrics[channel] = QueueMetrics(
            channel=channel, depth=depth,
            avg_wait_seconds=avg_wait, oldest_wait_seconds=oldest_wait,
        )
        if depth > self._alert_thresholds["queue_depth"]:
            self._fire_alert(
                f"queue_{channel}", "queue_depth",
                f"Queue depth {depth} exceeds threshold",
                AlertSeverity.WARNING, depth,
                self._alert_thresholds["queue_depth"], "",
            )

    # ------------------------------------------------------------------
    # Agent availability
    # ------------------------------------------------------------------

    def update_agent(self, agent_id: str, status: str, active_convs: int) -> None:
        self._agent_status[agent_id] = {
            "agent_id": agent_id, "status": status,
            "active_conversations": active_convs,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_agent_summary(self) -> Dict[str, Any]:
        agents = list(self._agent_status.values())
        return {
            "total": len(agents),
            "available": sum(1 for a in agents if a["status"] == "available"),
            "busy": sum(1 for a in agents if a["status"] == "busy"),
            "offline": sum(1 for a in agents if a["status"] == "offline"),
        }

    # ------------------------------------------------------------------
    # System health
    # ------------------------------------------------------------------

    def update_health(self, component: str, value: float) -> None:
        self._system_health[component] = value
        threshold = self._alert_thresholds.get(component)
        if threshold and value > threshold:
            self._fire_alert(
                f"health_{component}", component,
                f"{component} at {value:.1f}% exceeds {threshold}%",
                AlertSeverity.CRITICAL if value > threshold * 1.1 else AlertSeverity.WARNING,
                value, threshold, "",
            )

    # ------------------------------------------------------------------
    # Alert management
    # ------------------------------------------------------------------

    def _fire_alert(
        self, alert_id: str, metric: str, message: str,
        severity: AlertSeverity, value: float, threshold: float, tenant_id: str,
    ) -> None:
        # Deduplicate: don't re-fire same alert if already active
        if any(a.alert_id == alert_id and not a.resolved for a in self._alerts):
            return
        import uuid
        self._alerts.append(DashboardAlert(
            alert_id=alert_id, metric=metric, message=message,
            severity=severity, value=value, threshold=threshold,
            tenant_id=tenant_id,
        ))

    def resolve_alert(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.resolved = True
                return True
        return False

    def get_active_alerts(self) -> List[DashboardAlert]:
        return [a for a in self._alerts if not a.resolved]

    def set_threshold(self, metric: str, value: float) -> None:
        self._alert_thresholds[metric] = value

    # ------------------------------------------------------------------
    # Full dashboard snapshot
    # ------------------------------------------------------------------

    def get_snapshot(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "live_conversations": self.get_live_count(tenant_id),
            "queues": [q.to_dict() for q in self._queue_metrics.values()],
            "agents": self.get_agent_summary(),
            "system_health": self._system_health,
            "active_alerts": len(self.get_active_alerts()),
            "snapshot_at": datetime.utcnow().isoformat(),
        }

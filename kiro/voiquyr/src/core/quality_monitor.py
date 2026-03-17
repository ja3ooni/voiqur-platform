"""
Quality Monitor for tracking agent performance and health.
Monitors system metrics, agent performance, and provides quality assurance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

from .models import (
    AgentState, AgentMessage, TaskStatus, AgentStatus, 
    Priority, MessageType, Task
)
from .messaging import MessageRouter, MessageBus


logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    """Types of metrics to track."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    RESOURCE_USAGE = "resource_usage"
    AVAILABILITY = "availability"


class Alert:
    """Represents a system alert."""
    
    def __init__(self, alert_id: str, severity: str, message: str, 
                 agent_id: Optional[str] = None, metric_type: Optional[MetricType] = None):
        self.alert_id = alert_id
        self.severity = severity  # INFO, WARNING, CRITICAL
        self.message = message
        self.agent_id = agent_id
        self.metric_type = metric_type
        self.created_at = datetime.utcnow()
        self.acknowledged = False
        self.resolved = False
        self.resolved_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
    
    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.acknowledged = True
    
    def resolve(self) -> None:
        """Resolve the alert."""
        self.resolved = True
        self.resolved_at = datetime.utcnow()


class PerformanceMetric:
    """Tracks a specific performance metric."""
    
    def __init__(self, metric_name: str, metric_type: MetricType, window_size: int = 100):
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.values: deque = deque(maxlen=window_size)
        self.timestamps: deque = deque(maxlen=window_size)
        self.window_size = window_size
    
    def add_value(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a new metric value."""
        timestamp = timestamp or datetime.utcnow()
        self.values.append(value)
        self.timestamps.append(timestamp)
    
    def get_average(self, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Get average value, optionally within a time window."""
        if not self.values:
            return None
        
        if time_window is None:
            return statistics.mean(self.values)
        
        # Filter values within time window
        cutoff_time = datetime.utcnow() - time_window
        recent_values = [
            value for value, timestamp in zip(self.values, self.timestamps)
            if timestamp >= cutoff_time
        ]
        
        return statistics.mean(recent_values) if recent_values else None
    
    def get_percentile(self, percentile: float, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Get percentile value."""
        if not self.values:
            return None
        
        values_to_use = list(self.values)
        
        if time_window is not None:
            cutoff_time = datetime.utcnow() - time_window
            values_to_use = [
                value for value, timestamp in zip(self.values, self.timestamps)
                if timestamp >= cutoff_time
            ]
        
        if not values_to_use:
            return None
        
        return statistics.quantiles(values_to_use, n=100)[int(percentile) - 1] if len(values_to_use) > 1 else values_to_use[0]
    
    def get_trend(self, time_window: Optional[timedelta] = None) -> str:
        """Get trend direction (increasing, decreasing, stable)."""
        if len(self.values) < 2:
            return "unknown"
        
        values_to_use = list(self.values)
        
        if time_window is not None:
            cutoff_time = datetime.utcnow() - time_window
            values_to_use = [
                value for value, timestamp in zip(self.values, self.timestamps)
                if timestamp >= cutoff_time
            ]
        
        if len(values_to_use) < 2:
            return "unknown"
        
        # Simple trend calculation
        first_half = values_to_use[:len(values_to_use)//2]
        second_half = values_to_use[len(values_to_use)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"


class AgentHealthMonitor:
    """Monitors health of individual agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.health_status = HealthStatus.UNKNOWN
        self.last_health_check = datetime.utcnow()
        self.consecutive_failures = 0
        self.total_health_checks = 0
        self.successful_health_checks = 0
        
        # Performance metrics
        self.metrics: Dict[str, PerformanceMetric] = {
            MetricType.LATENCY.value: PerformanceMetric("latency", MetricType.LATENCY),
            MetricType.THROUGHPUT.value: PerformanceMetric("throughput", MetricType.THROUGHPUT),
            MetricType.ERROR_RATE.value: PerformanceMetric("error_rate", MetricType.ERROR_RATE),
            MetricType.SUCCESS_RATE.value: PerformanceMetric("success_rate", MetricType.SUCCESS_RATE),
            MetricType.RESOURCE_USAGE.value: PerformanceMetric("resource_usage", MetricType.RESOURCE_USAGE),
            MetricType.AVAILABILITY.value: PerformanceMetric("availability", MetricType.AVAILABILITY)
        }
        
        # Health thresholds
        self.thresholds = {
            "max_consecutive_failures": 3,
            "min_success_rate": 0.95,
            "max_error_rate": 0.05,
            "max_latency_ms": 1000,
            "min_availability": 0.99
        }
    
    def update_health_check(self, success: bool) -> None:
        """Update health check result."""
        self.total_health_checks += 1
        self.last_health_check = datetime.utcnow()
        
        if success:
            self.successful_health_checks += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
        
        # Update health status
        self._calculate_health_status()
    
    def add_metric_value(self, metric_type: MetricType, value: float) -> None:
        """Add a metric value."""
        if metric_type.value in self.metrics:
            self.metrics[metric_type.value].add_value(value)
            self._calculate_health_status()
    
    def _calculate_health_status(self) -> None:
        """Calculate overall health status based on metrics and thresholds."""
        if self.consecutive_failures >= self.thresholds["max_consecutive_failures"]:
            self.health_status = HealthStatus.CRITICAL
            return
        
        # Check success rate
        if self.total_health_checks > 0:
            success_rate = self.successful_health_checks / self.total_health_checks
            if success_rate < self.thresholds["min_success_rate"]:
                self.health_status = HealthStatus.WARNING
                return
        
        # Check error rate
        error_rate_metric = self.metrics[MetricType.ERROR_RATE.value]
        avg_error_rate = error_rate_metric.get_average(timedelta(minutes=5))
        if avg_error_rate and avg_error_rate > self.thresholds["max_error_rate"]:
            self.health_status = HealthStatus.WARNING
            return
        
        # Check latency
        latency_metric = self.metrics[MetricType.LATENCY.value]
        avg_latency = latency_metric.get_average(timedelta(minutes=5))
        if avg_latency and avg_latency > self.thresholds["max_latency_ms"]:
            self.health_status = HealthStatus.WARNING
            return
        
        # Check availability
        availability_metric = self.metrics[MetricType.AVAILABILITY.value]
        avg_availability = availability_metric.get_average(timedelta(minutes=5))
        if avg_availability and avg_availability < self.thresholds["min_availability"]:
            self.health_status = HealthStatus.WARNING
            return
        
        # If all checks pass
        self.health_status = HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for this agent."""
        return {
            "agent_id": self.agent_id,
            "health_status": self.health_status.value,
            "last_health_check": self.last_health_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "success_rate": self.successful_health_checks / max(self.total_health_checks, 1),
            "metrics": {
                name: {
                    "average": metric.get_average(timedelta(minutes=5)),
                    "p95": metric.get_percentile(95, timedelta(minutes=5)),
                    "trend": metric.get_trend(timedelta(minutes=5))
                }
                for name, metric in self.metrics.items()
            }
        }


class QualityMonitor:
    """
    Central quality monitor for tracking agent performance and system health.
    Provides comprehensive monitoring, alerting, and quality assurance.
    """
    
    def __init__(self, message_router: MessageRouter):
        self.message_router = message_router
        self.message_bus = MessageBus(message_router)
        
        # Agent monitoring
        self.agent_monitors: Dict[str, AgentHealthMonitor] = {}
        
        # System-wide metrics
        self.system_metrics: Dict[str, PerformanceMetric] = {
            "total_throughput": PerformanceMetric("total_throughput", MetricType.THROUGHPUT),
            "average_latency": PerformanceMetric("average_latency", MetricType.LATENCY),
            "system_error_rate": PerformanceMetric("system_error_rate", MetricType.ERROR_RATE),
            "active_agents": PerformanceMetric("active_agents", MetricType.AVAILABILITY)
        }
        
        # Alerting
        self.alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Quality thresholds
        self.quality_thresholds = {
            "min_system_availability": 0.99,
            "max_system_error_rate": 0.01,
            "max_average_latency": 100,  # ms
            "min_agent_health_percentage": 0.95
        }
        
        # Configuration
        self.monitoring_interval = 5.0  # seconds
        self.health_check_interval = 30.0  # seconds
        self.alert_cooldown = timedelta(minutes=5)
        
        # Runtime state
        self.monitoring_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Statistics
        self.monitoring_stats = {
            "total_alerts_generated": 0,
            "total_health_checks": 0,
            "monitoring_start_time": datetime.utcnow()
        }
    
    async def start(self) -> None:
        """Start the quality monitor."""
        if self.is_running:
            return
        
        logger.info("Starting Quality Monitor")
        self.is_running = True
        self.monitoring_stats["monitoring_start_time"] = datetime.utcnow()
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop(self) -> None:
        """Stop the quality monitor."""
        if not self.is_running:
            return
        
        logger.info("Stopping Quality Monitor")
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
    
    async def register_agent(self, agent_id: str) -> None:
        """Register an agent for monitoring."""
        if agent_id not in self.agent_monitors:
            self.agent_monitors[agent_id] = AgentHealthMonitor(agent_id)
            logger.info(f"Agent {agent_id} registered for monitoring")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from monitoring."""
        if agent_id in self.agent_monitors:
            del self.agent_monitors[agent_id]
            logger.info(f"Agent {agent_id} unregistered from monitoring")
    
    async def record_task_completion(self, agent_id: str, task: Task, 
                                   execution_time: float, success: bool) -> None:
        """Record task completion metrics."""
        if agent_id not in self.agent_monitors:
            await self.register_agent(agent_id)
        
        monitor = self.agent_monitors[agent_id]
        
        # Record metrics
        monitor.add_metric_value(MetricType.LATENCY, execution_time * 1000)  # Convert to ms
        monitor.add_metric_value(MetricType.SUCCESS_RATE, 1.0 if success else 0.0)
        monitor.add_metric_value(MetricType.ERROR_RATE, 0.0 if success else 1.0)
        
        # Update system metrics
        self.system_metrics["average_latency"].add_value(execution_time * 1000)
        self.system_metrics["system_error_rate"].add_value(0.0 if success else 1.0)
        
        # Check for quality issues
        await self._check_quality_thresholds(agent_id)
    
    async def record_agent_throughput(self, agent_id: str, throughput: float) -> None:
        """Record agent throughput."""
        if agent_id not in self.agent_monitors:
            await self.register_agent(agent_id)
        
        monitor = self.agent_monitors[agent_id]
        monitor.add_metric_value(MetricType.THROUGHPUT, throughput)
        
        # Update system throughput
        total_throughput = sum(
            monitor.metrics[MetricType.THROUGHPUT.value].get_average(timedelta(minutes=1)) or 0
            for monitor in self.agent_monitors.values()
        )
        self.system_metrics["total_throughput"].add_value(total_throughput)
    
    async def record_resource_usage(self, agent_id: str, cpu_percent: float, 
                                  memory_percent: float) -> None:
        """Record agent resource usage."""
        if agent_id not in self.agent_monitors:
            await self.register_agent(agent_id)
        
        monitor = self.agent_monitors[agent_id]
        # Use average of CPU and memory as overall resource usage
        resource_usage = (cpu_percent + memory_percent) / 2
        monitor.add_metric_value(MetricType.RESOURCE_USAGE, resource_usage)
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._collect_system_metrics()
                await self._check_system_health()
                await self._process_alerts()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _health_check_loop(self) -> None:
        """Health check loop for all agents."""
        while self.is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-wide metrics."""
        # Count active agents
        active_agents = 0
        for agent_id, agent_state in self.message_router.get_all_agents().items():
            if agent_state.status != AgentStatus.OFFLINE:
                active_agents += 1
        
        self.system_metrics["active_agents"].add_value(active_agents)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered agents."""
        health_check_tasks = []
        
        for agent_id in self.agent_monitors.keys():
            task = asyncio.create_task(self._check_agent_health(agent_id))
            health_check_tasks.append(task)
        
        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)
        
        self.monitoring_stats["total_health_checks"] += len(health_check_tasks)
    
    async def _check_agent_health(self, agent_id: str) -> None:
        """Check health of a specific agent."""
        try:
            agent_state = self.message_router.get_agent_state(agent_id)
            if not agent_state:
                return
            
            # Simple health check based on heartbeat
            is_healthy = agent_state.is_healthy()
            
            # Update monitor
            monitor = self.agent_monitors[agent_id]
            monitor.update_health_check(is_healthy)
            
            # Record availability
            monitor.add_metric_value(MetricType.AVAILABILITY, 1.0 if is_healthy else 0.0)
            
            # Generate alerts if needed
            if not is_healthy and monitor.health_status == HealthStatus.CRITICAL:
                await self._generate_alert(
                    f"agent_critical_{agent_id}",
                    "CRITICAL",
                    f"Agent {agent_id} is in critical health state",
                    agent_id,
                    MetricType.AVAILABILITY
                )
            
        except Exception as e:
            logger.error(f"Error checking health of agent {agent_id}: {e}")
    
    async def _check_system_health(self) -> None:
        """Check overall system health."""
        # Check system availability
        total_agents = len(self.agent_monitors)
        if total_agents > 0:
            healthy_agents = sum(
                1 for monitor in self.agent_monitors.values()
                if monitor.health_status == HealthStatus.HEALTHY
            )
            system_health_percentage = healthy_agents / total_agents
            
            if system_health_percentage < self.quality_thresholds["min_agent_health_percentage"]:
                await self._generate_alert(
                    "system_health_low",
                    "WARNING",
                    f"System health is low: {system_health_percentage:.2%} of agents are healthy"
                )
        
        # Check system error rate
        avg_error_rate = self.system_metrics["system_error_rate"].get_average(timedelta(minutes=5))
        if avg_error_rate and avg_error_rate > self.quality_thresholds["max_system_error_rate"]:
            await self._generate_alert(
                "system_error_rate_high",
                "WARNING",
                f"System error rate is high: {avg_error_rate:.2%}"
            )
        
        # Check system latency
        avg_latency = self.system_metrics["average_latency"].get_average(timedelta(minutes=5))
        if avg_latency and avg_latency > self.quality_thresholds["max_average_latency"]:
            await self._generate_alert(
                "system_latency_high",
                "WARNING",
                f"System average latency is high: {avg_latency:.2f}ms"
            )
    
    async def _check_quality_thresholds(self, agent_id: str) -> None:
        """Check quality thresholds for a specific agent."""
        monitor = self.agent_monitors[agent_id]
        
        # Check error rate
        error_rate = monitor.metrics[MetricType.ERROR_RATE.value].get_average(timedelta(minutes=5))
        if error_rate and error_rate > 0.1:  # 10% error rate threshold
            await self._generate_alert(
                f"agent_error_rate_{agent_id}",
                "WARNING",
                f"Agent {agent_id} has high error rate: {error_rate:.2%}",
                agent_id,
                MetricType.ERROR_RATE
            )
        
        # Check latency
        latency = monitor.metrics[MetricType.LATENCY.value].get_average(timedelta(minutes=5))
        if latency and latency > 1000:  # 1 second threshold
            await self._generate_alert(
                f"agent_latency_{agent_id}",
                "WARNING",
                f"Agent {agent_id} has high latency: {latency:.2f}ms",
                agent_id,
                MetricType.LATENCY
            )
    
    async def _generate_alert(self, alert_id: str, severity: str, message: str,
                            agent_id: Optional[str] = None, 
                            metric_type: Optional[MetricType] = None) -> None:
        """Generate a new alert."""
        # Check if alert already exists and is within cooldown period
        if alert_id in self.alerts:
            existing_alert = self.alerts[alert_id]
            if not existing_alert.resolved:
                time_since_created = datetime.utcnow() - existing_alert.created_at
                if time_since_created < self.alert_cooldown:
                    return  # Skip duplicate alert within cooldown
        
        # Create new alert
        alert = Alert(alert_id, severity, message, agent_id, metric_type)
        self.alerts[alert_id] = alert
        
        logger.warning(f"Alert generated: {alert_id} - {message}")
        self.monitoring_stats["total_alerts_generated"] += 1
        
        # Notify alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Send alert notification
        await self._send_alert_notification(alert)
    
    async def _send_alert_notification(self, alert: Alert) -> None:
        """Send alert notification to relevant agents."""
        recipients = []
        
        if alert.agent_id:
            recipients.append(alert.agent_id)
        
        # Also notify system administrators (if any registered)
        admin_agents = [
            agent_id for agent_id, state in self.message_router.get_all_agents().items()
            if "admin" in state.agent_type.lower()
        ]
        recipients.extend(admin_agents)
        
        if recipients:
            await self.message_bus.send_notification(
                sender_id="quality_monitor",
                notification_data={
                    "event": "alert_generated",
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "message": alert.message,
                    "agent_id": alert.agent_id,
                    "metric_type": alert.metric_type.value if alert.metric_type else None
                },
                recipients=recipients
            )
    
    async def _process_alerts(self) -> None:
        """Process and clean up alerts."""
        # Auto-resolve old alerts
        current_time = datetime.utcnow()
        alerts_to_resolve = []
        
        for alert_id, alert in self.alerts.items():
            if not alert.resolved:
                # Auto-resolve alerts older than 1 hour if conditions are met
                age = current_time - alert.created_at
                if age > timedelta(hours=1):
                    # Check if the condition that triggered the alert is still present
                    should_resolve = await self._should_auto_resolve_alert(alert)
                    if should_resolve:
                        alerts_to_resolve.append(alert_id)
        
        # Resolve alerts
        for alert_id in alerts_to_resolve:
            await self.resolve_alert(alert_id)
    
    async def _should_auto_resolve_alert(self, alert: Alert) -> bool:
        """Check if an alert should be auto-resolved."""
        if not alert.agent_id or not alert.metric_type:
            return True  # Resolve system-wide alerts after timeout
        
        monitor = self.agent_monitors.get(alert.agent_id)
        if not monitor:
            return True  # Agent no longer exists
        
        # Check if the metric that triggered the alert has improved
        if alert.metric_type == MetricType.ERROR_RATE:
            current_error_rate = monitor.metrics[MetricType.ERROR_RATE.value].get_average(timedelta(minutes=5))
            return current_error_rate is None or current_error_rate < 0.05
        
        elif alert.metric_type == MetricType.LATENCY:
            current_latency = monitor.metrics[MetricType.LATENCY.value].get_average(timedelta(minutes=5))
            return current_latency is None or current_latency < 500
        
        elif alert.metric_type == MetricType.AVAILABILITY:
            return monitor.health_status == HealthStatus.HEALTHY
        
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.resolve()
        
        logger.info(f"Alert resolved: {alert_id}")
        
        # Send resolution notification
        await self.message_bus.send_notification(
            sender_id="quality_monitor",
            notification_data={
                "event": "alert_resolved",
                "alert_id": alert_id
            }
        )
        
        return True
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add a callback for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def get_agent_health_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get health summary for a specific agent."""
        if agent_id not in self.agent_monitors:
            return None
        
        return self.agent_monitors[agent_id].get_health_summary()
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        total_agents = len(self.agent_monitors)
        healthy_agents = sum(
            1 for monitor in self.agent_monitors.values()
            if monitor.health_status == HealthStatus.HEALTHY
        )
        
        active_alerts = sum(1 for alert in self.alerts.values() if not alert.resolved)
        
        return {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "health_percentage": healthy_agents / max(total_agents, 1),
            "active_alerts": active_alerts,
            "system_metrics": {
                name: {
                    "current": metric.get_average(timedelta(minutes=1)),
                    "average_5min": metric.get_average(timedelta(minutes=5)),
                    "trend": metric.get_trend(timedelta(minutes=5))
                }
                for name, metric in self.system_metrics.items()
            },
            "monitoring_stats": self.monitoring_stats
        }
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Get comprehensive quality report."""
        return {
            "system_health": self.get_system_health_summary(),
            "agent_health": {
                agent_id: monitor.get_health_summary()
                for agent_id, monitor in self.agent_monitors.items()
            },
            "active_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "message": alert.message,
                    "agent_id": alert.agent_id,
                    "created_at": alert.created_at.isoformat(),
                    "acknowledged": alert.acknowledged
                }
                for alert in self.alerts.values()
                if not alert.resolved
            ],
            "quality_thresholds": self.quality_thresholds
        }
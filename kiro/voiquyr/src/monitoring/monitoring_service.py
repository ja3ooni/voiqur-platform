"""
Monitoring Service

Integrated monitoring service that coordinates performance monitoring,
resource tracking, and provides unified monitoring dashboard and alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .performance_monitor import PerformanceMonitor, ComponentType, MetricType
from .resource_tracker import ResourceTracker, ResourceType

logger = logging.getLogger(__name__)


@dataclass
class MonitoringStatus:
    """Overall monitoring system status."""
    performance_monitoring_active: bool
    resource_tracking_active: bool
    active_alerts: int
    optimization_opportunities: int
    overall_health_score: float
    last_updated: datetime


@dataclass
class SystemHealthSummary:
    """System health summary."""
    overall_status: str  # "healthy", "warning", "critical"
    performance_score: float
    resource_efficiency_score: float
    cost_optimization_score: float
    active_issues: List[str]
    recommendations: List[str]


class MonitoringService:
    """
    Integrated monitoring service for the EUVoice AI Platform.
    
    Coordinates:
    - Performance monitoring across all components
    - Resource usage tracking and optimization
    - Cost analysis and recommendations
    - Unified alerting and dashboard
    - Health scoring and trend analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize monitoring service."""
        self.config = config or {}
        
        # Initialize monitoring components
        self.performance_monitor = PerformanceMonitor(
            self.config.get("performance", {})
        )
        self.resource_tracker = ResourceTracker(
            self.config.get("resources", {})
        )
        
        # Service state
        self.monitoring_active = False
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # Health scoring weights
        self.health_weights = {
            "performance": 0.4,
            "resources": 0.3,
            "cost": 0.2,
            "alerts": 0.1
        }
        
        logger.info("Monitoring Service initialized")
    
    async def start_monitoring(self) -> None:
        """Start comprehensive monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring service is already active")
            return
        
        self.monitoring_active = True
        
        # Start performance monitoring
        await self.performance_monitor.start_monitoring()
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._resource_monitoring_loop()),
            asyncio.create_task(self._health_assessment_loop()),
            asyncio.create_task(self._optimization_analysis_loop())
        ]
        
        logger.info("Comprehensive monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop comprehensive monitoring."""
        self.monitoring_active = False
        
        # Stop performance monitoring
        await self.performance_monitor.stop_monitoring()
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        
        logger.info("Comprehensive monitoring stopped")
    
    async def _resource_monitoring_loop(self) -> None:
        """Resource monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect resource metrics
                await self.resource_tracker.collect_resource_metrics()
                
                # Sleep for resource monitoring interval
                await asyncio.sleep(self.config.get("resource_interval", 30))
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _health_assessment_loop(self) -> None:
        """System health assessment loop."""
        while self.monitoring_active:
            try:
                # Assess system health
                await self._assess_system_health()
                
                # Sleep for health assessment interval
                await asyncio.sleep(self.config.get("health_interval", 60))
                
            except Exception as e:
                logger.error(f"Error in health assessment loop: {e}")
                await asyncio.sleep(10)
    
    async def _optimization_analysis_loop(self) -> None:
        """Optimization analysis loop."""
        while self.monitoring_active:
            try:
                # Generate optimization recommendations
                await self.resource_tracker.generate_cost_optimizations()
                
                # Sleep for optimization analysis interval
                await asyncio.sleep(self.config.get("optimization_interval", 300))  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in optimization analysis loop: {e}")
                await asyncio.sleep(30)
    
    async def _assess_system_health(self) -> None:
        """Assess overall system health."""
        try:
            # Get performance summary
            perf_summary = self.performance_monitor.get_performance_summary(60)
            
            # Get resource efficiency
            resource_efficiency = await self.resource_tracker.analyze_resource_efficiency()
            
            # Calculate health scores and log if needed
            performance_score = self._calculate_performance_score(perf_summary)
            resource_score = self._calculate_resource_score(resource_efficiency)
            
            # Log health assessment results
            logger.debug(f"Health assessment - Performance: {performance_score}, Resources: {resource_score}")
            
        except Exception as e:
            logger.error(f"Error assessing system health: {e}")
    
    def _calculate_performance_score(self, perf_summary: Dict[str, Any]) -> float:
        """Calculate performance health score (0-100)."""
        if "components" not in perf_summary:
            return 50.0  # Default score when no data
        
        component_scores = []
        
        for component, metrics in perf_summary["components"].items():
            component_score = 100.0
            
            # Latency scoring
            if "latency" in metrics:
                avg_latency = metrics["latency"]["avg"]
                if avg_latency > 1000:  # > 1 second
                    component_score -= 30
                elif avg_latency > 500:  # > 500ms
                    component_score -= 15
                elif avg_latency > 200:  # > 200ms
                    component_score -= 5
            
            # Error rate scoring
            if "error_rate" in metrics:
                error_rate = metrics["error_rate"]["avg"]
                if error_rate > 5:  # > 5%
                    component_score -= 40
                elif error_rate > 1:  # > 1%
                    component_score -= 20
                elif error_rate > 0.1:  # > 0.1%
                    component_score -= 5
            
            # Accuracy scoring
            if "accuracy" in metrics:
                accuracy = metrics["accuracy"]["avg"]
                if accuracy < 85:  # < 85%
                    component_score -= 30
                elif accuracy < 90:  # < 90%
                    component_score -= 15
                elif accuracy < 95:  # < 95%
                    component_score -= 5
            
            component_scores.append(max(0, component_score))
        
        return sum(component_scores) / len(component_scores) if component_scores else 50.0
    
    def _calculate_resource_score(self, resource_efficiency: Dict[str, Any]) -> float:
        """Calculate resource efficiency score (0-100)."""
        if "overall_efficiency" in resource_efficiency:
            return resource_efficiency["overall_efficiency"]
        
        return 50.0  # Default score when no data
    
    async def get_system_health_summary(self) -> SystemHealthSummary:
        """Get a comprehensive system health summary."""
        perf_summary = self.performance_monitor.get_performance_summary(60)
        resource_efficiency = await self.resource_tracker.analyze_resource_efficiency()
        active_alerts = self.performance_monitor.get_active_alerts()
        optimizations = await self.resource_tracker.get_optimization_recommendations()

        performance_score = self._calculate_performance_score(perf_summary)
        resource_score = self._calculate_resource_score(resource_efficiency)
        cost_score = 80.0  # Placeholder

        alert_penalty = min(len(active_alerts) * 5, 30)
        overall = (
            performance_score * self.health_weights["performance"] +
            resource_score * self.health_weights["resources"] +
            cost_score * self.health_weights["cost"] +
            max(0, 100 - alert_penalty) * self.health_weights["alerts"]
        )

        if overall >= 80:
            status = "healthy"
        elif overall >= 60:
            status = "warning"
        else:
            status = "critical"

        active_issues = [str(alert) for alert in active_alerts[:5]]
        recommendations = [str(opt) for opt in optimizations[:5]]

        return SystemHealthSummary(
            overall_status=status,
            performance_score=round(performance_score, 1),
            resource_efficiency_score=round(resource_score, 1),
            cost_optimization_score=round(cost_score, 1),
            active_issues=active_issues,
            recommendations=recommendations
        )

    async def get_component_analysis(self, component: "ComponentType") -> Dict[str, Any]:
        """Get detailed analysis for a specific component."""
        perf_summary = self.performance_monitor.get_performance_summary(60)
        component_data = perf_summary.get("components", {}).get(component.value, {})

        health_score = 100.0
        if "latency" in component_data:
            avg_latency = component_data["latency"].get("avg", 0)
            if avg_latency > 1000:
                health_score -= 30
            elif avg_latency > 500:
                health_score -= 15
        if "error_rate" in component_data:
            error_rate = component_data["error_rate"].get("avg", 0)
            if error_rate > 5:
                health_score -= 40
            elif error_rate > 1:
                health_score -= 20

        return {
            "component": component.value,
            "health_score": max(0.0, health_score),
            "performance_metrics": component_data,
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
        }

    async def get_unified_dashboard(self) -> Dict[str, Any]:
        """Get a unified monitoring dashboard."""
        health_summary = await self.get_system_health_summary()
        perf_summary = self.performance_monitor.get_performance_summary(60)
        resource_efficiency = await self.resource_tracker.analyze_resource_efficiency()

        return {
            "system_health": {
                "overall_status": health_summary.overall_status,
                "performance_score": health_summary.performance_score,
                "resource_efficiency_score": health_summary.resource_efficiency_score,
            },
            "performance": {
                "dashboard": {
                    "current_status": {
                        "overall": health_summary.overall_status,
                    },
                    "summary": perf_summary,
                }
            },
            "resources": {
                "dashboard": {
                    "current_usage": resource_efficiency.get("by_resource", {}),
                    "efficiency": resource_efficiency.get("overall_efficiency", 50.0),
                }
            },
        }

    async def generate_monitoring_report(self, report_type: str = "full", hours: int = 24) -> Dict[str, Any]:
        """Generate a comprehensive monitoring report."""
        from datetime import datetime
        import uuid

        health_summary = await self.get_system_health_summary()
        active_alerts = self.performance_monitor.get_active_alerts()
        optimizations = await self.resource_tracker.get_optimization_recommendations()

        return {
            "report_metadata": {
                "report_id": str(uuid.uuid4()),
                "report_type": report_type,
                "period_hours": hours,
                "generated_at": datetime.utcnow().isoformat(),
            },
            "executive_summary": {
                "overall_health_status": health_summary.overall_status,
                "performance_score": health_summary.performance_score,
                "resource_efficiency_score": health_summary.resource_efficiency_score,
                "active_issues_count": len(active_alerts),
                "optimization_opportunities": len(optimizations),
            },
            "action_items": {
                "immediate_actions": health_summary.active_issues[:3],
                "recommended_optimizations": health_summary.recommendations[:5],
            },
        }

    async def get_monitoring_status(self) -> MonitoringStatus:
        """Get current monitoring status."""
        # Get active alerts
        active_alerts = self.performance_monitor.get_active_alerts()
        
        # Get optimization opportunities
        optimizations = await self.resource_tracker.get_optimization_recommendations()
        
        # Calculate overall health score
        perf_summary = self.performance_monitor.get_performance_summary(60)
        resource_efficiency = await self.resource_tracker.analyze_resource_efficiency()
        
        performance_score = self._calculate_performance_score(perf_summary)
        resource_score = self._calculate_resource_score(resource_efficiency)
        alert_penalty = min(len(active_alerts) * 5, 30)  # Max 30 point penalty
        
        overall_health = (
            performance_score * self.health_weights["performance"] +
            resource_score * self.health_weights["resources"] +
            80 * self.health_weights["cost"] +  # Placeholder cost score
            max(0, 100 - alert_penalty) * self.health_weights["alerts"]
        )
        
        return MonitoringStatus(
            performance_monitoring_active=self.monitoring_active,
            resource_tracking_active=self.monitoring_active,
            active_alerts=len(active_alerts),
            optimization_opportunities=len(optimizations),
            overall_health_score=round(overall_health, 1),
            last_updated=datetime.utcnow()
        )
    
    async def record_component_metrics(
        self,
        component: ComponentType,
        metrics: Dict[str, Any]
    ) -> None:
        """Record metrics for a specific component."""
        # Record latency if provided
        if "latency_ms" in metrics:
            await self.performance_monitor.record_latency(
                component,
                metrics.get("operation", "unknown"),
                metrics["latency_ms"],
                metrics.get("metadata", {})
            )
        
        # Record accuracy if provided
        if "accuracy" in metrics:
            await self.performance_monitor.record_accuracy(
                component,
                metrics["accuracy"],
                metrics.get("accuracy_type", "accuracy"),
                metrics.get("metadata", {})
            )
        
        # Record throughput if provided
        if "throughput" in metrics:
            await self.performance_monitor.record_throughput(
                component,
                metrics["throughput"],
                metrics.get("metadata", {})
            )
        
        # Record error rate if provided
        if "error_rate" in metrics:
            await self.performance_monitor.record_error_rate(
                component,
                metrics["error_rate"],
                metrics.get("metadata", {})
            )


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


def set_monitoring_service(service: MonitoringService) -> None:
    """Set the global monitoring service instance."""
    global _monitoring_service
    _monitoring_service = service
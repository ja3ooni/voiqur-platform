"""
Performance Monitoring Agent

Real-time performance monitoring system for the EUVoice AI Platform
that tracks latency, throughput, resource usage, and provides optimization recommendations.
"""

import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import statistics
import json
from pathlib import Path
import threading
import queue

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Performance metric types."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ACCURACY = "accuracy"
    RESOURCE_USAGE = "resource_usage"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"


class ComponentType(str, Enum):
    """System component types."""
    STT_AGENT = "stt_agent"
    LLM_AGENT = "llm_agent"
    TTS_AGENT = "tts_agent"
    EMOTION_AGENT = "emotion_agent"
    ACCENT_AGENT = "accent_agent"
    API_GATEWAY = "api_gateway"
    WEBHOOK_SERVICE = "webhook_service"
    INTEGRATION_SERVICE = "integration_service"
    DATABASE = "database"
    REDIS = "redis"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    component: ComponentType
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    component: ComponentType
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    unit: str
    direction: str = "above"  # "above" or "below"


@dataclass
class PerformanceAlert:
    """Performance alert."""
    id: str
    component: ComponentType
    metric_type: MetricType
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    id: str
    component: ComponentType
    issue: str
    recommendation: str
    expected_improvement: str
    priority: str
    implementation_effort: str
    created_at: datetime


class PerformanceMonitor:
    """
    Performance monitoring agent for the EUVoice AI Platform.
    
    Monitors real-time performance metrics including:
    - Latency and response times
    - Throughput and request rates
    - Resource utilization (CPU, memory, disk, network)
    - Accuracy and quality metrics
    - Error rates and availability
    - Cost optimization opportunities
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance monitor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Metric storage (in-memory for now, could be extended to use time-series DB)
        self.metrics: deque = deque(maxlen=10000)  # Last 10k metrics
        self.metric_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Alerts and recommendations
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[PerformanceAlert] = []
        self.recommendations: List[OptimizationRecommendation] = []
        
        # Performance thresholds
        self.thresholds = self._initialize_thresholds()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.metric_queue: queue.Queue = queue.Queue()
        
        # Performance baselines
        self.baselines: Dict[str, Dict[str, float]] = {}
        
        # Optimization engine
        self.optimization_rules = self._initialize_optimization_rules()
        
        logger.info("Performance Monitor initialized")
    
    def _initialize_thresholds(self) -> List[PerformanceThreshold]:
        """Initialize performance thresholds based on requirements."""
        return [
            # Latency thresholds (Requirement 5.2: <100ms end-to-end)
            PerformanceThreshold(
                ComponentType.STT_AGENT, MetricType.LATENCY, 400, 500, "ms", "above"
            ),
            PerformanceThreshold(
                ComponentType.LLM_AGENT, MetricType.LATENCY, 800, 1000, "ms", "above"
            ),
            PerformanceThreshold(
                ComponentType.TTS_AGENT, MetricType.LATENCY, 400, 500, "ms", "above"
            ),
            PerformanceThreshold(
                ComponentType.API_GATEWAY, MetricType.LATENCY, 50, 100, "ms", "above"
            ),
            
            # Accuracy thresholds (Requirement 5.1: >95% accuracy)
            PerformanceThreshold(
                ComponentType.STT_AGENT, MetricType.ACCURACY, 90, 95, "%", "below"
            ),
            PerformanceThreshold(
                ComponentType.LLM_AGENT, MetricType.ACCURACY, 85, 90, "%", "below"
            ),
            PerformanceThreshold(
                ComponentType.TTS_AGENT, MetricType.ACCURACY, 3.5, 4.0, "MOS", "below"
            ),
            
            # Resource usage thresholds
            PerformanceThreshold(
                ComponentType.STT_AGENT, MetricType.RESOURCE_USAGE, 80, 90, "%", "above"
            ),
            PerformanceThreshold(
                ComponentType.LLM_AGENT, MetricType.RESOURCE_USAGE, 80, 90, "%", "above"
            ),
            
            # Error rate thresholds
            PerformanceThreshold(
                ComponentType.API_GATEWAY, MetricType.ERROR_RATE, 1, 5, "%", "above"
            ),
            
            # Availability thresholds
            PerformanceThreshold(
                ComponentType.API_GATEWAY, MetricType.AVAILABILITY, 99.5, 99.9, "%", "below"
            )
        ]
    
    def _initialize_optimization_rules(self) -> List[Dict[str, Any]]:
        """Initialize optimization rules for recommendations."""
        return [
            {
                "condition": lambda metrics: self._check_high_latency(metrics, ComponentType.STT_AGENT),
                "recommendation": OptimizationRecommendation(
                    id="stt_latency_optimization",
                    component=ComponentType.STT_AGENT,
                    issue="High STT processing latency detected",
                    recommendation="Consider model quantization, batch processing optimization, or GPU acceleration",
                    expected_improvement="20-40% latency reduction",
                    priority="high",
                    implementation_effort="medium",
                    created_at=datetime.utcnow()
                )
            },
            {
                "condition": lambda metrics: self._check_high_memory_usage(metrics),
                "recommendation": OptimizationRecommendation(
                    id="memory_optimization",
                    component=ComponentType.LLM_AGENT,
                    issue="High memory usage detected",
                    recommendation="Implement model sharding, reduce batch size, or add memory pooling",
                    expected_improvement="30-50% memory reduction",
                    priority="medium",
                    implementation_effort="high",
                    created_at=datetime.utcnow()
                )
            },
            {
                "condition": lambda metrics: self._check_low_throughput(metrics),
                "recommendation": OptimizationRecommendation(
                    id="throughput_optimization",
                    component=ComponentType.API_GATEWAY,
                    issue="Low request throughput detected",
                    recommendation="Increase worker processes, implement connection pooling, or add load balancing",
                    expected_improvement="50-100% throughput increase",
                    priority="high",
                    implementation_effort="low",
                    created_at=datetime.utcnow()
                )
            }
        ]
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self.monitoring_active:
            logger.warning("Performance monitoring is already active")
            return
        
        self.monitoring_active = True
        
        # Start background monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Start metric processing
        asyncio.create_task(self._process_metrics())
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.monitoring_active = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Sleep for monitoring interval
                time.sleep(self.config.get("monitoring_interval", 5))
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        timestamp = datetime.utcnow()
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self._add_metric(
            ComponentType.API_GATEWAY,
            MetricType.RESOURCE_USAGE,
            cpu_percent,
            "%",
            timestamp,
            {"resource_type": "cpu"}
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        self._add_metric(
            ComponentType.API_GATEWAY,
            MetricType.RESOURCE_USAGE,
            memory.percent,
            "%",
            timestamp,
            {"resource_type": "memory", "available_gb": memory.available / (1024**3)}
        )
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self._add_metric(
            ComponentType.API_GATEWAY,
            MetricType.RESOURCE_USAGE,
            disk_percent,
            "%",
            timestamp,
            {"resource_type": "disk", "free_gb": disk.free / (1024**3)}
        )
        
        # Network I/O
        network = psutil.net_io_counters()
        self._add_metric(
            ComponentType.API_GATEWAY,
            MetricType.THROUGHPUT,
            network.bytes_sent + network.bytes_recv,
            "bytes/s",
            timestamp,
            {"network_type": "total_io"}
        )
    
    def _add_metric(
        self,
        component: ComponentType,
        metric_type: MetricType,
        value: float,
        unit: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a performance metric."""
        metric = PerformanceMetric(
            component=component,
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=timestamp,
            metadata=metadata or {}
        )
        
        # Add to queue for processing
        self.metric_queue.put(metric)
    
    async def _process_metrics(self) -> None:
        """Process metrics from the queue."""
        while self.monitoring_active:
            try:
                # Process metrics from queue
                while not self.metric_queue.empty():
                    metric = self.metric_queue.get_nowait()
                    
                    # Store metric
                    self.metrics.append(metric)
                    
                    # Add to component-specific buffer
                    buffer_key = f"{metric.component.value}_{metric.metric_type.value}"
                    self.metric_buffers[buffer_key].append(metric)
                    
                    # Check thresholds
                    await self._check_thresholds(metric)
                
                # Generate recommendations periodically
                await self._generate_recommendations()
                
                # Sleep before next processing cycle
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing metrics: {e}")
                await asyncio.sleep(1)
    
    async def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric violates thresholds."""
        for threshold in self.thresholds:
            if (threshold.component == metric.component and 
                threshold.metric_type == metric.metric_type):
                
                # Check if threshold is violated
                violated = False
                severity = None
                threshold_value = None
                
                if threshold.direction == "above":
                    if metric.value > threshold.critical_threshold:
                        violated = True
                        severity = AlertSeverity.CRITICAL
                        threshold_value = threshold.critical_threshold
                    elif metric.value > threshold.warning_threshold:
                        violated = True
                        severity = AlertSeverity.HIGH
                        threshold_value = threshold.warning_threshold
                else:  # "below"
                    if metric.value < threshold.critical_threshold:
                        violated = True
                        severity = AlertSeverity.CRITICAL
                        threshold_value = threshold.critical_threshold
                    elif metric.value < threshold.warning_threshold:
                        violated = True
                        severity = AlertSeverity.HIGH
                        threshold_value = threshold.warning_threshold
                
                if violated:
                    await self._create_alert(
                        metric, threshold, severity, threshold_value
                    )
    
    async def _create_alert(
        self,
        metric: PerformanceMetric,
        threshold: PerformanceThreshold,
        severity: AlertSeverity,
        threshold_value: float
    ) -> None:
        """Create performance alert."""
        alert_id = f"{metric.component.value}_{metric.metric_type.value}_{severity.value}"
        
        # Check if alert already exists
        if alert_id in self.active_alerts:
            return
        
        alert = PerformanceAlert(
            id=alert_id,
            component=metric.component,
            metric_type=metric.metric_type,
            severity=severity,
            message=f"{metric.component.value} {metric.metric_type.value} "
                   f"{'above' if threshold.direction == 'above' else 'below'} "
                   f"threshold: {metric.value}{metric.unit} "
                   f"(threshold: {threshold_value}{threshold.unit})",
            current_value=metric.value,
            threshold_value=threshold_value,
            timestamp=metric.timestamp
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"Performance alert created: {alert.message}")
    
    async def _generate_recommendations(self) -> None:
        """Generate optimization recommendations based on metrics."""
        # Get recent metrics for analysis
        recent_metrics = [
            m for m in self.metrics 
            if m.timestamp > datetime.utcnow() - timedelta(minutes=5)
        ]
        
        if not recent_metrics:
            return
        
        # Check optimization rules
        for rule in self.optimization_rules:
            try:
                if rule["condition"](recent_metrics):
                    recommendation = rule["recommendation"]
                    
                    # Check if recommendation already exists
                    existing = any(
                        r.id == recommendation.id 
                        for r in self.recommendations
                    )
                    
                    if not existing:
                        recommendation.created_at = datetime.utcnow()
                        self.recommendations.append(recommendation)
                        logger.info(f"Generated optimization recommendation: {recommendation.id}")
            
            except Exception as e:
                logger.error(f"Error evaluating optimization rule: {e}")
    
    def _check_high_latency(self, metrics: List[PerformanceMetric], component: ComponentType) -> bool:
        """Check if component has high latency."""
        component_metrics = [
            m for m in metrics 
            if m.component == component and m.metric_type == MetricType.LATENCY
        ]
        
        if len(component_metrics) < 5:
            return False
        
        avg_latency = statistics.mean([m.value for m in component_metrics])
        return avg_latency > 300  # 300ms threshold
    
    def _check_high_memory_usage(self, metrics: List[PerformanceMetric]) -> bool:
        """Check if system has high memory usage."""
        memory_metrics = [
            m for m in metrics 
            if (m.metric_type == MetricType.RESOURCE_USAGE and 
                m.metadata.get("resource_type") == "memory")
        ]
        
        if len(memory_metrics) < 3:
            return False
        
        avg_memory = statistics.mean([m.value for m in memory_metrics])
        return avg_memory > 85  # 85% threshold
    
    def _check_low_throughput(self, metrics: List[PerformanceMetric]) -> bool:
        """Check if system has low throughput."""
        throughput_metrics = [
            m for m in metrics 
            if m.metric_type == MetricType.THROUGHPUT
        ]
        
        if len(throughput_metrics) < 5:
            return False
        
        avg_throughput = statistics.mean([m.value for m in throughput_metrics])
        return avg_throughput < 1000  # Low throughput threshold
    
    # Public API methods
    
    async def record_latency(
        self,
        component: ComponentType,
        operation: str,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record latency metric for a component operation."""
        self._add_metric(
            component,
            MetricType.LATENCY,
            latency_ms,
            "ms",
            datetime.utcnow(),
            {**(metadata or {}), "operation": operation}
        )
    
    async def record_accuracy(
        self,
        component: ComponentType,
        accuracy: float,
        metric_name: str = "accuracy",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record accuracy metric for a component."""
        unit = "%" if metric_name == "accuracy" else "MOS"
        self._add_metric(
            component,
            MetricType.ACCURACY,
            accuracy,
            unit,
            datetime.utcnow(),
            {**(metadata or {}), "metric_name": metric_name}
        )
    
    async def record_throughput(
        self,
        component: ComponentType,
        requests_per_second: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record throughput metric for a component."""
        self._add_metric(
            component,
            MetricType.THROUGHPUT,
            requests_per_second,
            "req/s",
            datetime.utcnow(),
            metadata
        )
    
    async def record_error_rate(
        self,
        component: ComponentType,
        error_rate: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record error rate metric for a component."""
        self._add_metric(
            component,
            MetricType.ERROR_RATE,
            error_rate,
            "%",
            datetime.utcnow(),
            metadata
        )
    
    def get_performance_summary(
        self,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_metrics = [
            m for m in self.metrics 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {"message": "No metrics available for the specified time window"}
        
        # Group metrics by component and type
        grouped_metrics = defaultdict(lambda: defaultdict(list))
        for metric in recent_metrics:
            grouped_metrics[metric.component.value][metric.metric_type.value].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for component, metric_types in grouped_metrics.items():
            summary[component] = {}
            for metric_type, values in metric_types.items():
                if values:
                    summary[component][metric_type] = {
                        "count": len(values),
                        "avg": round(statistics.mean(values), 2),
                        "min": round(min(values), 2),
                        "max": round(max(values), 2),
                        "median": round(statistics.median(values), 2)
                    }
        
        return {
            "time_window_minutes": time_window_minutes,
            "total_metrics": len(recent_metrics),
            "components": summary,
            "active_alerts": len(self.active_alerts),
            "recommendations": len(self.recommendations)
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active performance alerts."""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get optimization recommendations."""
        # Sort by priority and creation time
        priority_order = {"high": 3, "medium": 2, "low": 1}
        sorted_recommendations = sorted(
            self.recommendations,
            key=lambda r: (priority_order.get(r.priority, 0), r.created_at),
            reverse=True
        )
        
        return [asdict(rec) for rec in sorted_recommendations[:limit]]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            del self.active_alerts[alert_id]
            logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
    
    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get performance trends over time."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        historical_metrics = [
            m for m in self.metrics 
            if m.timestamp > cutoff_time
        ]
        
        if not historical_metrics:
            return {"message": "No historical data available"}
        
        # Group by day and calculate daily averages
        daily_metrics = defaultdict(lambda: defaultdict(list))
        
        for metric in historical_metrics:
            day_key = metric.timestamp.strftime("%Y-%m-%d")
            metric_key = f"{metric.component.value}_{metric.metric_type.value}"
            daily_metrics[day_key][metric_key].append(metric.value)
        
        # Calculate trends
        trends = {}
        for day, metrics_by_type in daily_metrics.items():
            trends[day] = {}
            for metric_key, values in metrics_by_type.items():
                if values:
                    trends[day][metric_key] = {
                        "avg": round(statistics.mean(values), 2),
                        "count": len(values)
                    }
        
        return {
            "period_days": days,
            "daily_trends": trends,
            "total_data_points": len(historical_metrics)
        }
    
    async def optimize_component(self, component: ComponentType) -> Dict[str, Any]:
        """Get optimization suggestions for a specific component."""
        # Get recent metrics for the component
        recent_metrics = [
            m for m in self.metrics 
            if (m.component == component and 
                m.timestamp > datetime.utcnow() - timedelta(minutes=30))
        ]
        
        if not recent_metrics:
            return {"message": f"No recent metrics available for {component.value}"}
        
        # Analyze performance patterns
        latency_metrics = [m for m in recent_metrics if m.metric_type == MetricType.LATENCY]
        accuracy_metrics = [m for m in recent_metrics if m.metric_type == MetricType.ACCURACY]
        resource_metrics = [m for m in recent_metrics if m.metric_type == MetricType.RESOURCE_USAGE]
        
        suggestions = []
        
        # Latency optimization
        if latency_metrics:
            avg_latency = statistics.mean([m.value for m in latency_metrics])
            if avg_latency > 200:
                suggestions.append({
                    "type": "latency_optimization",
                    "current_avg_latency_ms": round(avg_latency, 2),
                    "suggestions": [
                        "Consider model quantization to reduce inference time",
                        "Implement request batching for better throughput",
                        "Add caching for frequently requested operations",
                        "Optimize model loading and initialization"
                    ]
                })
        
        # Resource optimization
        if resource_metrics:
            avg_resource = statistics.mean([m.value for m in resource_metrics])
            if avg_resource > 70:
                suggestions.append({
                    "type": "resource_optimization",
                    "current_avg_usage_percent": round(avg_resource, 2),
                    "suggestions": [
                        "Implement memory pooling to reduce allocation overhead",
                        "Add model sharding for large models",
                        "Optimize batch sizes for better memory utilization",
                        "Consider using smaller model variants for non-critical operations"
                    ]
                })
        
        # Accuracy optimization
        if accuracy_metrics:
            avg_accuracy = statistics.mean([m.value for m in accuracy_metrics])
            if avg_accuracy < 90:
                suggestions.append({
                    "type": "accuracy_optimization",
                    "current_avg_accuracy": round(avg_accuracy, 2),
                    "suggestions": [
                        "Fine-tune models on domain-specific data",
                        "Implement ensemble methods for better accuracy",
                        "Add data preprocessing and cleaning steps",
                        "Consider using larger, more accurate model variants"
                    ]
                })
        
        return {
            "component": component.value,
            "analysis_period_minutes": 30,
            "metrics_analyzed": len(recent_metrics),
            "optimization_suggestions": suggestions
        }


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """Set the global performance monitor instance."""
    global _performance_monitor
    _performance_monitor = monitor


# Decorator for automatic latency tracking
def track_performance(component: ComponentType, operation: str):
    """Decorator to automatically track performance metrics."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                await monitor.record_latency(
                    component, operation, latency_ms,
                    {"success": success}
                )
            return result
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                # For sync functions, we can't await, so we'll add to queue directly
                monitor._add_metric(
                    component, MetricType.LATENCY, latency_ms, "ms",
                    datetime.utcnow(), {"operation": operation, "success": success}
                )
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
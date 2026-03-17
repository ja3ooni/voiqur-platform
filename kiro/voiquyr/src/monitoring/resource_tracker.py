"""
Resource Usage Tracker

Tracks system resource usage, cost optimization opportunities,
and provides recommendations for efficient resource utilization.
"""

import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import statistics

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types for tracking."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    STORAGE = "storage"


class CostCategory(str, Enum):
    """Cost categories for optimization."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    LICENSING = "licensing"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class ResourceUsage:
    """Resource usage data point."""
    resource_type: ResourceType
    usage_percent: float
    absolute_value: float
    unit: str
    timestamp: datetime
    component: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CostOptimization:
    """Cost optimization recommendation."""
    id: str
    category: CostCategory
    current_cost: float
    potential_savings: float
    savings_percent: float
    recommendation: str
    implementation_effort: str
    risk_level: str
    created_at: datetime


class ResourceTracker:
    """
    Resource usage tracker for cost optimization and performance monitoring.
    
    Tracks:
    - CPU, memory, disk, network usage
    - GPU utilization (if available)
    - Storage consumption
    - Cost optimization opportunities
    - Resource allocation recommendations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize resource tracker."""
        self.config = config or {}
        
        # Resource usage history
        self.usage_history: List[ResourceUsage] = []
        self.cost_optimizations: List[CostOptimization] = []
        
        # Resource baselines and targets
        self.resource_targets = {
            ResourceType.CPU: 70.0,      # Target CPU usage %
            ResourceType.MEMORY: 75.0,   # Target memory usage %
            ResourceType.DISK: 80.0,     # Target disk usage %
            ResourceType.NETWORK: 60.0,  # Target network usage %
            ResourceType.GPU: 80.0       # Target GPU usage %
        }
        
        # Cost tracking (placeholder values - would integrate with cloud billing APIs)
        self.cost_per_hour = {
            "cpu_core": 0.05,      # €0.05 per CPU core per hour
            "memory_gb": 0.01,     # €0.01 per GB memory per hour
            "storage_gb": 0.0001,  # €0.0001 per GB storage per hour
            "network_gb": 0.02,    # €0.02 per GB network transfer
            "gpu_hour": 2.50       # €2.50 per GPU hour
        }
        
        logger.info("Resource Tracker initialized")
    
    async def collect_resource_metrics(self) -> Dict[str, ResourceUsage]:
        """Collect current resource usage metrics."""
        timestamp = datetime.utcnow()
        metrics = {}
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        metrics["cpu"] = ResourceUsage(
            resource_type=ResourceType.CPU,
            usage_percent=cpu_percent,
            absolute_value=cpu_count,
            unit="cores",
            timestamp=timestamp,
            metadata={"logical_cores": psutil.cpu_count(logical=True)}
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        metrics["memory"] = ResourceUsage(
            resource_type=ResourceType.MEMORY,
            usage_percent=memory.percent,
            absolute_value=memory.used / (1024**3),  # GB
            unit="GB",
            timestamp=timestamp,
            metadata={
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3)
            }
        )
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        metrics["disk"] = ResourceUsage(
            resource_type=ResourceType.DISK,
            usage_percent=disk_percent,
            absolute_value=disk.used / (1024**3),  # GB
            unit="GB",
            timestamp=timestamp,
            metadata={
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3)
            }
        )
        
        # Network I/O
        network = psutil.net_io_counters()
        # Calculate network usage as a percentage of a baseline (e.g., 1 Gbps)
        baseline_bps = 1024**3  # 1 Gbps baseline
        current_bps = network.bytes_sent + network.bytes_recv
        network_percent = min((current_bps / baseline_bps) * 100, 100)
        
        metrics["network"] = ResourceUsage(
            resource_type=ResourceType.NETWORK,
            usage_percent=network_percent,
            absolute_value=current_bps / (1024**2),  # MB/s
            unit="MB/s",
            timestamp=timestamp,
            metadata={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        )
        
        # GPU usage (if available)
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                metrics["gpu"] = ResourceUsage(
                    resource_type=ResourceType.GPU,
                    usage_percent=gpu.load * 100,
                    absolute_value=gpu.memoryUsed,
                    unit="MB",
                    timestamp=timestamp,
                    metadata={
                        "gpu_name": gpu.name,
                        "memory_total": gpu.memoryTotal,
                        "memory_free": gpu.memoryFree,
                        "temperature": gpu.temperature
                    }
                )
        except ImportError:
            # GPU monitoring not available
            pass
        except Exception as e:
            logger.warning(f"Could not collect GPU metrics: {e}")
        
        # Store metrics
        for metric in metrics.values():
            self.usage_history.append(metric)
        
        # Keep only recent history (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.usage_history = [
            m for m in self.usage_history 
            if m.timestamp > cutoff
        ]
        
        return metrics
    
    async def analyze_resource_efficiency(self) -> Dict[str, Any]:
        """Analyze resource efficiency and identify optimization opportunities."""
        if not self.usage_history:
            return {"message": "No resource usage data available"}
        
        # Get recent metrics (last hour)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.usage_history 
            if m.timestamp > recent_cutoff
        ]
        
        if not recent_metrics:
            return {"message": "No recent resource usage data available"}
        
        # Group by resource type
        resource_analysis = {}
        
        for resource_type in ResourceType:
            type_metrics = [
                m for m in recent_metrics 
                if m.resource_type == resource_type
            ]
            
            if not type_metrics:
                continue
            
            usage_values = [m.usage_percent for m in type_metrics]
            target = self.resource_targets.get(resource_type, 70.0)
            
            avg_usage = statistics.mean(usage_values)
            max_usage = max(usage_values)
            min_usage = min(usage_values)
            
            # Efficiency analysis
            efficiency_score = 100 - abs(avg_usage - target)  # Closer to target = higher score
            
            # Optimization opportunities
            optimization_potential = "low"
            if avg_usage < target * 0.5:
                optimization_potential = "high"  # Under-utilized
            elif avg_usage > target * 1.2:
                optimization_potential = "high"  # Over-utilized
            elif abs(avg_usage - target) > 15:
                optimization_potential = "medium"
            
            resource_analysis[resource_type.value] = {
                "current_usage": {
                    "avg_percent": round(avg_usage, 2),
                    "max_percent": round(max_usage, 2),
                    "min_percent": round(min_usage, 2)
                },
                "target_percent": target,
                "efficiency_score": round(efficiency_score, 1),
                "optimization_potential": optimization_potential,
                "data_points": len(type_metrics)
            }
        
        return {
            "analysis_period_hours": 1,
            "resource_analysis": resource_analysis,
            "overall_efficiency": round(
                statistics.mean([
                    analysis["efficiency_score"] 
                    for analysis in resource_analysis.values()
                ]), 1
            )
        }
    
    async def generate_cost_optimizations(self) -> List[CostOptimization]:
        """Generate cost optimization recommendations."""
        optimizations = []
        
        # Analyze recent resource usage for cost optimization
        efficiency_analysis = await self.analyze_resource_efficiency()
        
        if "resource_analysis" not in efficiency_analysis:
            return optimizations
        
        resource_analysis = efficiency_analysis["resource_analysis"]
        
        # CPU optimization
        if "cpu" in resource_analysis:
            cpu_data = resource_analysis["cpu"]
            if cpu_data["optimization_potential"] == "high":
                if cpu_data["current_usage"]["avg_percent"] < 30:
                    # Under-utilized CPU
                    current_cost = self.cost_per_hour["cpu_core"] * 24 * 30  # Monthly
                    potential_savings = current_cost * 0.5  # 50% savings
                    
                    optimizations.append(CostOptimization(
                        id="cpu_underutilization",
                        category=CostCategory.COMPUTE,
                        current_cost=current_cost,
                        potential_savings=potential_savings,
                        savings_percent=50.0,
                        recommendation="Reduce CPU allocation or consolidate workloads",
                        implementation_effort="low",
                        risk_level="low",
                        created_at=datetime.utcnow()
                    ))
        
        # Memory optimization
        if "memory" in resource_analysis:
            memory_data = resource_analysis["memory"]
            if memory_data["optimization_potential"] == "high":
                if memory_data["current_usage"]["avg_percent"] < 40:
                    # Under-utilized memory
                    current_cost = self.cost_per_hour["memory_gb"] * 32 * 24 * 30  # 32GB monthly
                    potential_savings = current_cost * 0.3  # 30% savings
                    
                    optimizations.append(CostOptimization(
                        id="memory_underutilization",
                        category=CostCategory.COMPUTE,
                        current_cost=current_cost,
                        potential_savings=potential_savings,
                        savings_percent=30.0,
                        recommendation="Reduce memory allocation or implement memory pooling",
                        implementation_effort="medium",
                        risk_level="low",
                        created_at=datetime.utcnow()
                    ))
        
        # Storage optimization
        if "disk" in resource_analysis:
            disk_data = resource_analysis["disk"]
            if disk_data["current_usage"]["avg_percent"] > 85:
                # High disk usage
                current_cost = self.cost_per_hour["storage_gb"] * 1000 * 24 * 30  # 1TB monthly
                potential_savings = current_cost * 0.2  # 20% savings through cleanup
                
                optimizations.append(CostOptimization(
                    id="storage_cleanup",
                    category=CostCategory.STORAGE,
                    current_cost=current_cost,
                    potential_savings=potential_savings,
                    savings_percent=20.0,
                    recommendation="Implement data lifecycle management and cleanup old files",
                    implementation_effort="medium",
                    risk_level="medium",
                    created_at=datetime.utcnow()
                ))
        
        # Add to internal list
        self.cost_optimizations.extend(optimizations)
        
        return optimizations
    
    def get_resource_dashboard(self) -> Dict[str, Any]:
        """Get resource usage dashboard data."""
        if not self.usage_history:
            return {"message": "No resource usage data available"}
        
        # Get latest metrics
        latest_metrics = {}
        for resource_type in ResourceType:
            type_metrics = [
                m for m in self.usage_history 
                if m.resource_type == resource_type
            ]
            
            if type_metrics:
                latest = max(type_metrics, key=lambda m: m.timestamp)
                latest_metrics[resource_type.value] = {
                    "usage_percent": latest.usage_percent,
                    "absolute_value": latest.absolute_value,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp.isoformat(),
                    "metadata": latest.metadata
                }
        
        # Calculate cost estimates
        cost_estimates = self._calculate_cost_estimates()
        
        # Get optimization opportunities
        optimization_count = len([
            opt for opt in self.cost_optimizations 
            if opt.created_at > datetime.utcnow() - timedelta(days=1)
        ])
        
        return {
            "current_usage": latest_metrics,
            "cost_estimates": cost_estimates,
            "optimization_opportunities": optimization_count,
            "efficiency_targets": {k.value: v for k, v in self.resource_targets.items()},
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _calculate_cost_estimates(self) -> Dict[str, Any]:
        """Calculate cost estimates based on current usage."""
        if not self.usage_history:
            return {}
        
        # Get average usage over last hour
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.usage_history 
            if m.timestamp > recent_cutoff
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate average usage by resource type
        avg_usage = {}
        for resource_type in ResourceType:
            type_metrics = [
                m for m in recent_metrics 
                if m.resource_type == resource_type
            ]
            
            if type_metrics:
                avg_usage[resource_type.value] = statistics.mean([
                    m.absolute_value for m in type_metrics
                ])
        
        # Calculate costs
        hourly_costs = {}
        monthly_costs = {}
        
        if "cpu" in avg_usage:
            hourly_costs["cpu"] = avg_usage["cpu"] * self.cost_per_hour["cpu_core"]
            monthly_costs["cpu"] = hourly_costs["cpu"] * 24 * 30
        
        if "memory" in avg_usage:
            hourly_costs["memory"] = avg_usage["memory"] * self.cost_per_hour["memory_gb"]
            monthly_costs["memory"] = hourly_costs["memory"] * 24 * 30
        
        if "disk" in avg_usage:
            hourly_costs["storage"] = avg_usage["disk"] * self.cost_per_hour["storage_gb"]
            monthly_costs["storage"] = hourly_costs["storage"] * 24 * 30
        
        if "network" in avg_usage:
            hourly_costs["network"] = avg_usage["network"] * self.cost_per_hour["network_gb"]
            monthly_costs["network"] = hourly_costs["network"] * 24 * 30
        
        total_hourly = sum(hourly_costs.values())
        total_monthly = sum(monthly_costs.values())
        
        return {
            "hourly_costs": {k: round(v, 4) for k, v in hourly_costs.items()},
            "monthly_costs": {k: round(v, 2) for k, v in monthly_costs.items()},
            "total_hourly_eur": round(total_hourly, 4),
            "total_monthly_eur": round(total_monthly, 2),
            "currency": "EUR"
        }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get resource optimization recommendations."""
        # Generate fresh optimizations
        await self.generate_cost_optimizations()
        
        # Sort by potential savings
        sorted_optimizations = sorted(
            self.cost_optimizations,
            key=lambda opt: opt.potential_savings,
            reverse=True
        )
        
        return [asdict(opt) for opt in sorted_optimizations[:10]]  # Top 10
    
    def get_resource_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get resource usage trends over time."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        historical_metrics = [
            m for m in self.usage_history 
            if m.timestamp > cutoff_time
        ]
        
        if not historical_metrics:
            return {"message": "No historical resource data available"}
        
        # Group by hour and resource type
        hourly_usage = defaultdict(lambda: defaultdict(list))
        
        for metric in historical_metrics:
            hour_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_usage[hour_key][metric.resource_type.value].append(metric.usage_percent)
        
        # Calculate hourly averages
        trends = {}
        for hour, resource_data in hourly_usage.items():
            trends[hour] = {}
            for resource_type, usage_values in resource_data.items():
                if usage_values:
                    trends[hour][resource_type] = {
                        "avg_usage": round(statistics.mean(usage_values), 2),
                        "max_usage": round(max(usage_values), 2),
                        "data_points": len(usage_values)
                    }
        
        return {
            "period_hours": hours,
            "hourly_trends": trends,
            "total_data_points": len(historical_metrics)
        }
    
    async def predict_resource_needs(self, forecast_hours: int = 24) -> Dict[str, Any]:
        """Predict future resource needs based on trends."""
        if len(self.usage_history) < 10:
            return {"message": "Insufficient data for prediction"}
        
        # Get recent metrics for trend analysis
        recent_cutoff = datetime.utcnow() - timedelta(hours=6)
        recent_metrics = [
            m for m in self.usage_history 
            if m.timestamp > recent_cutoff
        ]
        
        predictions = {}
        
        for resource_type in ResourceType:
            type_metrics = [
                m for m in recent_metrics 
                if m.resource_type == resource_type
            ]
            
            if len(type_metrics) < 5:
                continue
            
            # Simple linear trend prediction
            usage_values = [m.usage_percent for m in type_metrics]
            time_points = [(m.timestamp - recent_metrics[0].timestamp).total_seconds() / 3600 for m in type_metrics]
            
            if len(usage_values) >= 2:
                # Calculate trend slope
                avg_time = statistics.mean(time_points)
                avg_usage = statistics.mean(usage_values)
                
                numerator = sum((t - avg_time) * (u - avg_usage) for t, u in zip(time_points, usage_values))
                denominator = sum((t - avg_time) ** 2 for t in time_points)
                
                if denominator != 0:
                    slope = numerator / denominator
                    predicted_usage = avg_usage + (slope * forecast_hours)
                    
                    predictions[resource_type.value] = {
                        "current_avg_usage": round(avg_usage, 2),
                        "predicted_usage": round(max(0, min(100, predicted_usage)), 2),
                        "trend_slope": round(slope, 4),
                        "forecast_hours": forecast_hours,
                        "confidence": "medium" if len(usage_values) > 10 else "low"
                    }
        
        return {
            "predictions": predictions,
            "forecast_period_hours": forecast_hours,
            "data_points_analyzed": len(recent_metrics)
        }
    
    async def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown and optimization opportunities."""
        cost_estimates = self._calculate_cost_estimates()
        
        if not cost_estimates:
            return {"message": "No cost data available"}
        
        # Calculate potential savings
        total_monthly = cost_estimates["total_monthly_eur"]
        
        # Estimate savings from optimizations
        total_potential_savings = sum(
            opt.potential_savings for opt in self.cost_optimizations
        )
        
        savings_percent = (total_potential_savings / total_monthly * 100) if total_monthly > 0 else 0
        
        # Cost breakdown by category
        cost_by_category = {
            CostCategory.COMPUTE.value: (
                cost_estimates["monthly_costs"].get("cpu", 0) + 
                cost_estimates["monthly_costs"].get("memory", 0)
            ),
            CostCategory.STORAGE.value: cost_estimates["monthly_costs"].get("storage", 0),
            CostCategory.NETWORK.value: cost_estimates["monthly_costs"].get("network", 0)
        }
        
        return {
            "current_costs": cost_estimates,
            "cost_by_category": cost_by_category,
            "optimization_opportunities": {
                "total_potential_savings_eur": round(total_potential_savings, 2),
                "savings_percent": round(savings_percent, 1),
                "optimization_count": len(self.cost_optimizations)
            },
            "cost_efficiency_score": round(100 - savings_percent, 1)
        }


# Global resource tracker instance
_resource_tracker: Optional[ResourceTracker] = None


def get_resource_tracker() -> ResourceTracker:
    """Get the global resource tracker instance."""
    global _resource_tracker
    if _resource_tracker is None:
        _resource_tracker = ResourceTracker()
    return _resource_tracker


def set_resource_tracker(tracker: ResourceTracker) -> None:
    """Set the global resource tracker instance."""
    global _resource_tracker
    _resource_tracker = tracker
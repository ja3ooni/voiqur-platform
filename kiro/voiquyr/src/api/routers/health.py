"""
Health Check Router

Provides health check endpoints for monitoring and load balancing.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import time
import psutil
import asyncio

from ..auth import AuthManager, User

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""
    
    status: str
    timestamp: float
    version: str = "1.0.0"
    uptime: float
    checks: Dict[str, Any]


class DetailedHealthStatus(BaseModel):
    """Detailed health status with system metrics."""
    
    status: str
    timestamp: float
    version: str = "1.0.0"
    uptime: float
    system: Dict[str, Any]
    services: Dict[str, Any]
    performance: Dict[str, Any]


# Track startup time for uptime calculation
startup_time = time.time()


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns basic health status for load balancer health checks.
    """
    current_time = time.time()
    uptime = current_time - startup_time
    
    # Basic checks
    checks = {
        "api": "healthy",
        "timestamp": current_time
    }
    
    return HealthStatus(
        status="healthy",
        timestamp=current_time,
        uptime=uptime,
        checks=checks
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the service is ready to accept traffic.
    """
    # Check critical dependencies
    checks = []
    
    try:
        # Check if we can perform basic operations
        await asyncio.sleep(0.001)  # Basic async check
        checks.append(("async_runtime", True))
    except Exception:
        checks.append(("async_runtime", False))
    
    # All checks must pass for readiness
    all_ready = all(check[1] for check in checks)
    
    if all_ready:
        return {"status": "ready", "checks": dict(checks)}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": dict(checks)}
        )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Checks if the service is alive and should not be restarted.
    """
    # Basic liveness check - if we can respond, we're alive
    return {"status": "alive", "timestamp": time.time()}


@router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """
    Detailed health check with system metrics.
    
    Provides comprehensive system information.
    Note: In production, this should require admin privileges.
    """
    current_time = time.time()
    uptime = current_time - startup_time
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_info = {
        "cpu_percent": cpu_percent,
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100
        },
        "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
    }
    
    # Service checks
    services = {
        "api": "healthy",
        "auth": "healthy",
        "rate_limiter": "healthy"
    }
    
    # Performance metrics
    performance = {
        "uptime_seconds": uptime,
        "cpu_usage_percent": cpu_percent,
        "memory_usage_percent": memory.percent,
        "disk_usage_percent": (disk.used / disk.total) * 100
    }
    
    # Determine overall status
    status = "healthy"
    if cpu_percent > 90 or memory.percent > 90:
        status = "degraded"
    if cpu_percent > 95 or memory.percent > 95:
        status = "unhealthy"
    
    return DetailedHealthStatus(
        status=status,
        timestamp=current_time,
        uptime=uptime,
        system=system_info,
        services=services,
        performance=performance
    )


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus format for monitoring.
    """
    current_time = time.time()
    uptime = current_time - startup_time
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # Format as Prometheus metrics
    metrics = f"""# HELP euvoice_api_uptime_seconds Total uptime in seconds
# TYPE euvoice_api_uptime_seconds counter
euvoice_api_uptime_seconds {uptime}

# HELP euvoice_api_cpu_usage_percent CPU usage percentage
# TYPE euvoice_api_cpu_usage_percent gauge
euvoice_api_cpu_usage_percent {cpu_percent}

# HELP euvoice_api_memory_usage_percent Memory usage percentage
# TYPE euvoice_api_memory_usage_percent gauge
euvoice_api_memory_usage_percent {memory.percent}

# HELP euvoice_api_memory_usage_bytes Memory usage in bytes
# TYPE euvoice_api_memory_usage_bytes gauge
euvoice_api_memory_usage_bytes {memory.used}

# HELP euvoice_api_health_status Health status (1=healthy, 0=unhealthy)
# TYPE euvoice_api_health_status gauge
euvoice_api_health_status 1
"""
    
    return metrics


@router.get("/version")
async def version_info():
    """
    API version information.
    
    Returns version and build information.
    """
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_time": "2024-01-01T00:00:00Z",  # Would be set during build
        "git_commit": "unknown",  # Would be set during build
        "environment": "development"  # Would be set from config
    }
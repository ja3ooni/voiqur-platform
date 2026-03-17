#!/usr/bin/env python3
"""
Simple test for the monitoring system to verify basic functionality.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitoring.monitoring_service import MonitoringService, ComponentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_monitoring_basic():
    """Test basic monitoring functionality."""
    logger.info("Starting basic monitoring test...")
    
    # Initialize monitoring service
    config = {
        "monitoring_interval": 2,
        "resource_interval": 5,
        "health_interval": 10,
        "optimization_interval": 15
    }
    
    monitoring_service = MonitoringService(config)
    
    try:
        # Start monitoring
        logger.info("Starting monitoring...")
        await monitoring_service.start_monitoring()
        
        # Wait a bit for monitoring to initialize
        await asyncio.sleep(2)
        
        # Record some test metrics
        logger.info("Recording test metrics...")
        
        await monitoring_service.record_component_metrics(
            ComponentType.STT_AGENT,
            {
                "latency_ms": 150.5,
                "accuracy": 96.2,
                "throughput": 45.0,
                "error_rate": 0.5,
                "operation": "transcribe_audio"
            }
        )
        
        await monitoring_service.record_component_metrics(
            ComponentType.LLM_AGENT,
            {
                "latency_ms": 320.8,
                "accuracy": 89.7,
                "throughput": 12.0,
                "error_rate": 1.2,
                "operation": "generate_response"
            }
        )
        
        # Wait for metrics to be processed
        await asyncio.sleep(2)
        
        # Get monitoring status
        logger.info("Getting monitoring status...")
        status = await monitoring_service.get_monitoring_status()
        
        print("\\n" + "="*50)
        print("MONITORING STATUS")
        print("="*50)
        print(f"Performance Monitoring: {status.performance_monitoring_active}")
        print(f"Resource Tracking: {status.resource_tracking_active}")
        print(f"Active Alerts: {status.active_alerts}")
        print(f"Optimization Opportunities: {status.optimization_opportunities}")
        print(f"Overall Health Score: {status.overall_health_score}")
        print(f"Last Updated: {status.last_updated}")
        
        print("\\n" + "="*50)
        print("MONITORING TEST COMPLETED SUCCESSFULLY")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error during monitoring test: {e}")
        raise
    
    finally:
        # Stop monitoring
        logger.info("Stopping monitoring...")
        await monitoring_service.stop_monitoring()


async def main():
    """Main test function."""
    try:
        await test_monitoring_basic()
        print("\\n✅ Basic monitoring test passed!")
        return 0
    except Exception as e:
        print(f"\\n❌ Basic monitoring test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
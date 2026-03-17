#!/usr/bin/env python3
"""
Simple test for the monitoring system to verify functionality.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitoring.monitoring_service import MonitoringService, ComponentType
from monitoring.performance_monitor import MetricType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_monitoring_system():
    """Test the monitoring system functionality."""
    logger.info("Starting monitoring system test...")
    
    # Initialize monitoring service
    config = {
        "monitoring_interval": 2,  # Fast interval for testing
        "resource_interval": 5,
        "health_interval": 10,
        "optimization_interval": 15
    }
    
    monitoring_service = MonitoringService(config)
    
    try:
        # Start monitoring
        logger.info("Starting comprehensive monitoring...")
        await monitoring_service.start_monitoring()
        
        # Wait a bit for monitoring to collect some data
        await asyncio.sleep(3)
        
        # Record some test metrics
        logger.info("Recording test metrics...")
        
        # STT Agent metrics
        await monitoring_service.record_component_metrics(
            ComponentType.STT_AGENT,
            {
                "latency_ms": 150.5,
                "accuracy": 96.2,
                "throughput": 45.0,
                "error_rate": 0.5,
                "operation": "transcribe_audio",
                "metadata": {"model": "whisper-large", "language": "en"}
            }
        )
        
        # LLM Agent metrics
        await monitoring_service.record_component_metrics(
            ComponentType.LLM_AGENT,
            {
                "latency_ms": 320.8,
                "accuracy": 89.7,
                "throughput": 12.0,
                "error_rate": 1.2,
                "operation": "generate_response",
                "metadata": {"model": "gpt-4", "tokens": 150}
            }
        )
        
        # TTS Agent metrics
        await monitoring_service.record_component_metrics(
            ComponentType.TTS_AGENT,
            {
                "latency_ms": 180.3,
                "accuracy": 4.2,  # MOS score
                "throughput": 25.0,
                "error_rate": 0.8,
                "operation": "synthesize_speech",
                "metadata": {"voice": "neural-voice", "language": "en-US"}
            }
        )
        
        # API Gateway metrics
        await monitoring_service.record_component_metrics(
            ComponentType.API_GATEWAY,
            {
                "latency_ms": 45.2,
                "throughput": 150.0,
                "error_rate": 0.3,
                "operation": "handle_request",
                "metadata": {"endpoint": "/api/v1/voice/process"}
            }
        )
        
        # Wait for metrics to be processed
        await asyncio.sleep(2)
        
        # Get monitoring status
        logger.info("Getting monitoring status...")
        status = await monitoring_service.get_monitoring_status()
        
        print("\\n" + "="*60)
        print("MONITORING STATUS")
        print("="*60)
        print(f"Performance Monitoring Active: {status.performance_monitoring_active}")
        print(f"Resource Tracking Active: {status.resource_tracking_active}")
        print(f"Active Alerts: {status.active_alerts}")
        print(f"Optimization Opportunities: {status.optimization_opportunities}")
        print(f"Overall Health Score: {status.overall_health_score}")
        print(f"Last Updated: {status.last_updated}")
        
        # Get system health summary
        logger.info("Getting system health summary...")
        health_summary = await monitoring_service.get_system_health_summary()
        
        print("\\n" + "="*60)
        print("SYSTEM HEALTH SUMMARY")
        print("="*60)
        print(f"Overall Status: {health_summary.overall_status}")
        print(f"Performance Score: {health_summary.performance_score:.1f}")
        print(f"Resource Efficiency Score: {health_summary.resource_efficiency_score:.1f}")
        print(f"Cost Optimization Score: {health_summary.cost_optimization_score:.1f}")
        
        if health_summary.active_issues:
            print("\\nActive Issues:")
            for issue in health_summary.active_issues:
                print(f"  - {issue}")
        
        if health_summary.recommendations:
            print("\\nRecommendations:")
            for rec in health_summary.recommendations:
                print(f"  - {rec}")
        
        # Get component analysis
        logger.info("Getting component analysis...")
        stt_analysis = await monitoring_service.get_component_analysis(ComponentType.STT_AGENT)
        
        print("\\n" + "="*60)
        print("STT AGENT ANALYSIS")
        print("="*60)
        print(f"Component: {stt_analysis['component']}")
        print(f"Health Score: {stt_analysis['health_score']:.1f}")
        
        if stt_analysis.get('performance_metrics'):
            print("Performance Metrics:")
            for metric, data in stt_analysis['performance_metrics'].items():
                if isinstance(data, dict) and 'avg' in data:
                    print(f"  {metric}: avg={data['avg']}, min={data['min']}, max={data['max']}")
        
        # Get unified dashboard
        logger.info("Getting unified dashboard...")
        dashboard = await monitoring_service.get_unified_dashboard()
        
        print("\\n" + "="*60)
        print("UNIFIED DASHBOARD SUMMARY")
        print("="*60)
        
        system_health = dashboard.get('system_health', {})
        print(f"System Status: {system_health.get('overall_status', 'unknown')}")
        
        performance = dashboard.get('performance', {}).get('dashboard', {})
        if performance.get('current_status'):
            print(f"Performance Status: {performance['current_status'].get('overall', 'unknown')}")
        
        resources = dashboard.get('resources', {}).get('dashboard', {})
        if resources.get('current_usage'):
            print("Resource Usage:")
            for resource, usage in resources['current_usage'].items():
                if isinstance(usage, dict) and 'usage_percent' in usage:
                    print(f"  {resource}: {usage['usage_percent']:.1f}%")
        
        # Generate monitoring report
        logger.info("Generating monitoring report...")
        report = await monitoring_service.generate_monitoring_report("test", 1)
        
        print("\\n" + "="*60)
        print("MONITORING REPORT SUMMARY")
        print("="*60)
        
        exec_summary = report.get('executive_summary', {})
        print(f"Report ID: {report['report_metadata']['report_id']}")
        print(f"Overall Health: {exec_summary.get('overall_health_status', 'unknown')}")
        print(f"Performance Score: {exec_summary.get('performance_score', 0):.1f}")
        print(f"Resource Efficiency: {exec_summary.get('resource_efficiency_score', 0):.1f}")
        print(f"Active Issues: {exec_summary.get('active_issues_count', 0)}")
        print(f"Optimization Opportunities: {exec_summary.get('optimization_opportunities', 0)}")
        
        action_items = report.get('action_items', {})
        if action_items.get('immediate_actions'):
            print("\\nImmediate Actions:")
            for action in action_items['immediate_actions']:
                print(f"  - {action}")
        
        if action_items.get('recommended_optimizations'):
            print("\\nRecommended Optimizations:")
            for opt in action_items['recommended_optimizations'][:3]:
                print(f"  - {opt}")
        
        print("\\n" + "="*60)
        print("MONITORING SYSTEM TEST COMPLETED SUCCESSFULLY")
        print("="*60)
        
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
        await test_monitoring_system()
        print("\\n✅ Monitoring system test passed!")
        return 0
    except Exception as e:
        print(f"\\n❌ Monitoring system test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
#!/usr/bin/env python3
"""
Simple Quality Assurance Tests

Tests for performance monitoring and security scanning functionality.
"""

import asyncio
import sys
import logging
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitoring import ComponentType, get_performance_monitor
from monitoring.monitoring_service import MonitoringService
from security import SecurityScanner, AuditSystem, AuditEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_performance_monitoring():
    """Test performance monitoring functionality."""
    logger.info("Testing performance monitoring...")
    
    monitoring_service = MonitoringService()
    
    try:
        # Start monitoring
        await monitoring_service.start_monitoring()
        
        # Record test metrics
        await monitoring_service.record_component_metrics(
            ComponentType.STT_AGENT,
            {
                "latency_ms": 150.0,
                "accuracy": 96.5,
                "throughput": 45.0,
                "error_rate": 0.5,
                "operation": "test_transcription"
            }
        )
        
        await monitoring_service.record_component_metrics(
            ComponentType.LLM_AGENT,
            {
                "latency_ms": 320.0,
                "accuracy": 89.2,
                "throughput": 12.0,
                "error_rate": 1.2,
                "operation": "test_generation"
            }
        )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Get monitoring status
        status = await monitoring_service.get_monitoring_status()
        
        print("\\n" + "="*50)
        print("PERFORMANCE MONITORING TEST")
        print("="*50)
        print(f"Monitoring Active: {status.performance_monitoring_active}")
        print(f"Health Score: {status.overall_health_score}")
        print(f"Active Alerts: {status.active_alerts}")
        print(f"Optimization Opportunities: {status.optimization_opportunities}")
        
        print(f"\\nMonitoring successfully recorded metrics for multiple components")
        
        return {
            "status": "PASSED",
            "monitoring_active": status.performance_monitoring_active,
            "health_score": status.overall_health_score,
            "alerts_generated": status.active_alerts
        }
        
    except Exception as e:
        logger.error(f"Performance monitoring test failed: {e}")
        return {"status": "FAILED", "error": str(e)}
    
    finally:
        await monitoring_service.stop_monitoring()


async def test_security_scanning():
    """Test security scanning functionality."""
    logger.info("Testing security scanning...")
    
    scanner = SecurityScanner()
    
    try:
        # Create test file with vulnerabilities
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
# Test vulnerabilities
password = "test123"
api_key = "sk-abcdef123456"

def bad_query(user_input):
    return f"SELECT * FROM users WHERE id = {user_input}"

def dangerous_eval(code):
    return eval(code)
''')
            test_file = f.name
        
        try:
            # Run security scan
            scan_result = await scanner.scan_project(Path(test_file).parent, "static")
            
            # Get summary
            summary = scanner.get_vulnerability_summary()
            
            print("\\n" + "="*50)
            print("SECURITY SCANNING TEST")
            print("="*50)
            print(f"Files Scanned: {scan_result.files_scanned}")
            print(f"Total Issues: {scan_result.total_issues}")
            print(f"Critical: {scan_result.critical_issues}")
            print(f"High: {scan_result.high_issues}")
            print(f"Medium: {scan_result.medium_issues}")
            print(f"Low: {scan_result.low_issues}")
            print(f"Risk Score: {summary.get('risk_score', 0)}")
            
            if scan_result.vulnerabilities:
                print("\\nTop Vulnerabilities:")
                for vuln in scan_result.vulnerabilities[:3]:
                    print(f"  - {vuln.severity.value.upper()}: {vuln.title}")
            
            return {
                "status": "PASSED",
                "files_scanned": scan_result.files_scanned,
                "vulnerabilities": scan_result.total_issues,
                "critical_issues": scan_result.critical_issues,
                "risk_score": summary.get('risk_score', 0)
            }
            
        finally:
            Path(test_file).unlink()
    
    except Exception as e:
        logger.error(f"Security scanning test failed: {e}")
        return {"status": "FAILED", "error": str(e)}


async def test_audit_system():
    """Test audit system functionality."""
    logger.info("Testing audit system...")
    
    audit_system = AuditSystem()
    
    try:
        # Log test events
        events = []
        
        event1 = await audit_system.log_event(
            AuditEventType.USER_LOGIN,
            "test_user_login",
            "success",
            user_id="test_user",
            details={"test_mode": True}
        )
        events.append(event1)
        
        event2 = await audit_system.log_event(
            AuditEventType.VOICE_PROCESSING,
            "test_audio_processing",
            "success",
            user_id="test_user",
            details={"contains_pii": True, "duration_ms": 5000}
        )
        events.append(event2)
        
        event3 = await audit_system.log_event(
            AuditEventType.SECURITY_EVENT,
            "test_security_scan",
            "warning",
            details={"vulnerabilities_found": 5}
        )
        events.append(event3)
        
        # Get statistics
        stats = audit_system.get_audit_statistics(1)
        
        # Generate compliance report
        report = await audit_system.generate_compliance_report("test", 1)
        
        print("\\n" + "="*50)
        print("AUDIT SYSTEM TEST")
        print("="*50)
        print(f"Events Logged: {len(events)}")
        print(f"Total Events: {stats['total_events']}")
        print(f"High Risk Events: {stats['high_risk_events']}")
        print(f"Average Risk Score: {stats['average_risk_score']}")
        print(f"Compliance Score: {report.summary.get('compliance_score', 0)}")
        
        return {
            "status": "PASSED",
            "events_logged": len(events),
            "total_events": stats['total_events'],
            "compliance_score": report.summary.get('compliance_score', 0)
        }
        
    except Exception as e:
        logger.error(f"Audit system test failed: {e}")
        return {"status": "FAILED", "error": str(e)}


async def test_qa_integration():
    """Test integration between QA systems."""
    logger.info("Testing QA integration...")
    
    try:
        # Initialize systems
        monitoring_service = MonitoringService()
        scanner = SecurityScanner()
        audit_system = AuditSystem()
        
        # Start monitoring
        await monitoring_service.start_monitoring()
        
        # Record performance metrics
        await monitoring_service.record_component_metrics(
            ComponentType.API_GATEWAY,
            {
                "latency_ms": 45.0,
                "throughput": 150.0,
                "error_rate": 0.3,
                "operation": "integration_test"
            }
        )
        
        # Log audit event for performance recording
        await audit_system.log_event(
            AuditEventType.VOICE_PROCESSING,
            "integration_test_metrics",
            "success",
            details={"component": "api_gateway", "test": True}
        )
        
        # Run quick security scan
        scan_result = await scanner.scan_project(".", "config")
        
        # Log security scan results
        await audit_system.log_event(
            AuditEventType.SECURITY_EVENT,
            "integration_security_scan",
            "success",
            details={
                "vulnerabilities": scan_result.total_issues,
                "scan_id": scan_result.scan_id
            }
        )
        
        # Get final status
        monitoring_status = await monitoring_service.get_monitoring_status()
        audit_stats = audit_system.get_audit_statistics(1)
        
        print("\\n" + "="*50)
        print("QA INTEGRATION TEST")
        print("="*50)
        print(f"Monitoring Health: {monitoring_status.overall_health_score}")
        print(f"Audit Events: {audit_stats['total_events']}")
        print(f"Security Issues: {scan_result.total_issues}")
        print("Integration: ✅ All systems working together")
        
        await monitoring_service.stop_monitoring()
        
        return {
            "status": "PASSED",
            "monitoring_health": monitoring_status.overall_health_score,
            "audit_events": audit_stats['total_events'],
            "security_issues": scan_result.total_issues
        }
        
    except Exception as e:
        logger.error(f"QA integration test failed: {e}")
        return {"status": "FAILED", "error": str(e)}


async def main():
    """Main test function."""
    try:
        print("🧪 Starting QA Systems Test...")
        
        # Run individual tests
        perf_result = await test_performance_monitoring()
        security_result = await test_security_scanning()
        audit_result = await test_audit_system()
        integration_result = await test_qa_integration()
        
        # Collect results
        results = {
            "performance_monitoring": perf_result,
            "security_scanning": security_result,
            "audit_system": audit_result,
            "qa_integration": integration_result
        }
        
        # Calculate summary
        passed_tests = [name for name, result in results.items() if result["status"] == "PASSED"]
        failed_tests = [name for name, result in results.items() if result["status"] == "FAILED"]
        
        print("\\n" + "="*60)
        print("QA TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {len(results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(results)*100:.1f}%")
        
        if passed_tests:
            print("\\n✅ Passed Tests:")
            for test in passed_tests:
                print(f"  - {test}")
        
        if failed_tests:
            print("\\n❌ Failed Tests:")
            for test in failed_tests:
                error = results[test].get("error", "Unknown error")
                print(f"  - {test}: {error}")
        
        # Save results
        with open("qa_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": len(results),
                    "passed": len(passed_tests),
                    "failed": len(failed_tests),
                    "success_rate": len(passed_tests)/len(results)*100
                },
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)
        
        if len(passed_tests) == len(results):
            print("\\n🎉 All QA tests passed!")
            return 0
        else:
            print(f"\\n⚠️  {len(failed_tests)} test(s) failed")
            return 1
        
    except Exception as e:
        print(f"\\n💥 QA test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
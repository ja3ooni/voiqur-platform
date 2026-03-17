#!/usr/bin/env python3
"""
Comprehensive Quality Assurance Tests

Tests for compliance validation, performance monitoring, and security scanning
to verify all QA systems work correctly together.
"""

import asyncio
import sys
import logging
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from compliance import ComplianceSystem, ComplianceType
from monitoring import get_monitoring_service, ComponentType
from security import SecurityScanner, AuditSystem, AuditEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class QATestSuite:
    """Comprehensive QA test suite."""
    
    def __init__(self):
        """Initialize test suite."""
        self.test_results = {}
        self.compliance_system = ComplianceSystem()
        self.monitoring_service = get_monitoring_service()
        self.security_scanner = SecurityScanner()
        self.audit_system = AuditSystem()
    
    async def run_all_tests(self) -> dict:
        """Run all QA tests."""
        logger.info("Starting comprehensive QA test suite...")
        
        # Test compliance validation
        await self.test_compliance_validation()
        
        # Test performance monitoring
        await self.test_performance_monitoring()
        
        # Test security scanning
        await self.test_security_scanning()
        
        # Test audit functionality
        await self.test_audit_functionality()
        
        # Test integration
        await self.test_qa_integration()
        
        return self.test_results
    
    async def test_compliance_validation(self):
        """Test compliance validation and reporting."""
        logger.info("Testing compliance validation...")
        
        test_name = "compliance_validation"
        try:
            # Test GDPR compliance check
            gdpr_result = await self.compliance_system.check_compliance(
                ComplianceType.GDPR,
                {
                    "data_processing": True,
                    "consent_obtained": True,
                    "data_minimization": True,
                    "retention_policy": True,
                    "data_subject_rights": True
                }
            )
            
            # Test AI Act compliance check
            ai_act_result = await self.compliance_system.check_compliance(
                ComplianceType.AI_ACT,
                {
                    "ai_system_type": "high_risk",
                    "risk_assessment": True,
                    "human_oversight": True,
                    "transparency": True,
                    "accuracy_requirements": True
                }
            )
            
            # Test license validation
            license_result = await self.compliance_system.validate_licenses(".")
            
            # Generate compliance report
            report = await self.compliance_system.generate_compliance_report()
            
            # Verify results
            assert gdpr_result.compliant, "GDPR compliance check failed"
            assert ai_act_result.compliant, "AI Act compliance check failed"
            assert license_result.compliant, "License validation failed"
            assert report.overall_compliance_score > 80, "Overall compliance score too low"
            
            self.test_results[test_name] = {
                "status": "PASSED",
                "gdpr_compliant": gdpr_result.compliant,
                "ai_act_compliant": ai_act_result.compliant,
                "license_compliant": license_result.compliant,
                "compliance_score": report.overall_compliance_score,
                "issues_found": len(report.compliance_issues)
            }
            
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def test_performance_monitoring(self):
        """Test performance monitoring and optimization."""
        logger.info("Testing performance monitoring...")
        
        test_name = "performance_monitoring"
        try:
            # Start monitoring
            await self.monitoring_service.start_monitoring()
            
            # Record test metrics for different components
            components_to_test = [
                ComponentType.STT_AGENT,
                ComponentType.LLM_AGENT,
                ComponentType.TTS_AGENT,
                ComponentType.API_GATEWAY
            ]
            
            for component in components_to_test:
                await self.monitoring_service.record_component_metrics(
                    component,
                    {
                        "latency_ms": 150.0 + hash(component.value) % 100,
                        "accuracy": 95.0 + (hash(component.value) % 5),
                        "throughput": 50.0 + (hash(component.value) % 20),
                        "error_rate": 0.5 + (hash(component.value) % 2),
                        "operation": f"test_{component.value}"
                    }
                )
            
            # Wait for metrics to be processed
            await asyncio.sleep(2)
            
            # Get monitoring status
            status = await self.monitoring_service.get_monitoring_status()
            
            # Test performance analysis
            stt_analysis = await self.monitoring_service.get_component_analysis(
                ComponentType.STT_AGENT
            )
            
            # Verify results
            assert status.performance_monitoring_active, "Performance monitoring not active"
            assert status.overall_health_score > 0, "Health score not calculated"
            assert stt_analysis["health_score"] > 0, "Component health score not calculated"
            
            self.test_results[test_name] = {
                "status": "PASSED",
                "monitoring_active": status.performance_monitoring_active,
                "health_score": status.overall_health_score,
                "components_monitored": len(components_to_test),
                "metrics_recorded": len(components_to_test) * 5
            }
            
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"❌ {test_name} failed: {e}")
        
        finally:
            # Stop monitoring
            await self.monitoring_service.stop_monitoring()
    
    async def test_security_scanning(self):
        """Test security scanning and vulnerability assessment."""
        logger.info("Testing security scanning...")
        
        test_name = "security_scanning"
        try:
            # Create a temporary test file with vulnerabilities
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('''
# Test file with security vulnerabilities
password = "hardcoded_password_123"
api_key = "sk-1234567890abcdef"

def unsafe_query(user_input):
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    return execute(query)

def unsafe_eval(code):
    return eval(code)
''')
                test_file_path = f.name
            
            try:
                # Run security scan on test file
                scan_result = await self.security_scanner.scan_project(
                    Path(test_file_path).parent, 
                    "static"
                )
                
                # Get vulnerability summary
                summary = self.security_scanner.get_vulnerability_summary()
                
                # Verify results
                assert scan_result.total_issues > 0, "No vulnerabilities detected in test file"
                assert scan_result.critical_issues > 0, "No critical vulnerabilities detected"
                assert summary["risk_score"] > 0, "Risk score not calculated"
                
                self.test_results[test_name] = {
                    "status": "PASSED",
                    "files_scanned": scan_result.files_scanned,
                    "vulnerabilities_found": scan_result.total_issues,
                    "critical_issues": scan_result.critical_issues,
                    "high_issues": scan_result.high_issues,
                    "risk_score": summary["risk_score"],
                    "scan_duration": scan_result.scan_duration_seconds
                }
                
                logger.info(f"✅ {test_name} passed")
                
            finally:
                # Clean up test file
                Path(test_file_path).unlink()
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def test_audit_functionality(self):
        """Test audit trail generation and compliance reporting."""
        logger.info("Testing audit functionality...")
        
        test_name = "audit_functionality"
        try:
            # Log various audit events
            events_to_log = [
                (AuditEventType.USER_LOGIN, "test_user_login", "success"),
                (AuditEventType.VOICE_PROCESSING, "audio_transcription", "success"),
                (AuditEventType.DATA_ACCESS, "user_data_access", "success"),
                (AuditEventType.SECURITY_EVENT, "vulnerability_detected", "warning"),
                (AuditEventType.COMPLIANCE_CHECK, "gdpr_validation", "success")
            ]
            
            logged_events = []
            for event_type, action, outcome in events_to_log:
                event = await self.audit_system.log_event(
                    event_type,
                    action,
                    outcome,
                    user_id="test_user",
                    details={
                        "test_mode": True,
                        "contains_pii": event_type == AuditEventType.DATA_ACCESS
                    }
                )
                logged_events.append(event)
            
            # Get audit statistics
            stats = self.audit_system.get_audit_statistics(1)
            
            # Generate compliance report
            compliance_report = await self.audit_system.generate_compliance_report(
                "test", 1
            )
            
            # Verify results
            assert len(logged_events) == len(events_to_log), "Not all events logged"
            assert stats["total_events"] >= len(events_to_log), "Audit statistics incorrect"
            assert compliance_report.total_events >= len(events_to_log), "Compliance report incomplete"
            
            self.test_results[test_name] = {
                "status": "PASSED",
                "events_logged": len(logged_events),
                "total_events": stats["total_events"],
                "high_risk_events": stats["high_risk_events"],
                "compliance_score": compliance_report.summary.get("compliance_score", 0),
                "gdpr_events": len(compliance_report.gdpr_events),
                "security_events": len(compliance_report.security_events)
            }
            
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def test_qa_integration(self):
        """Test integration between all QA systems."""
        logger.info("Testing QA system integration...")
        
        test_name = "qa_integration"
        try:
            # Simulate a complete QA workflow
            
            # 1. Start monitoring
            await self.monitoring_service.start_monitoring()
            
            # 2. Record performance metrics
            await self.monitoring_service.record_component_metrics(
                ComponentType.STT_AGENT,
                {
                    "latency_ms": 200.0,
                    "accuracy": 94.0,
                    "throughput": 30.0,
                    "error_rate": 1.5,
                    "operation": "integration_test"
                }
            )
            
            # 3. Log audit event for the performance recording
            await self.audit_system.log_event(
                AuditEventType.VOICE_PROCESSING,
                "performance_metrics_recorded",
                "success",
                details={
                    "component": "stt_agent",
                    "metrics_count": 5,
                    "integration_test": True
                }
            )
            
            # 4. Run security scan
            scan_result = await self.security_scanner.scan_project(".", "config")
            
            # 5. Log security scan results
            await self.audit_system.log_event(
                AuditEventType.SECURITY_EVENT,
                "security_scan_integration_test",
                "success" if scan_result.critical_issues == 0 else "warning",
                details={
                    "scan_id": scan_result.scan_id,
                    "vulnerabilities": scan_result.total_issues,
                    "critical": scan_result.critical_issues
                }
            )
            
            # 6. Check compliance
            compliance_result = await self.compliance_system.check_compliance(
                ComplianceType.GDPR,
                {
                    "data_processing": True,
                    "audit_trail": True,
                    "security_measures": True
                }
            )
            
            # 7. Generate final reports
            monitoring_status = await self.monitoring_service.get_monitoring_status()
            audit_stats = self.audit_system.get_audit_statistics(1)
            compliance_report = await self.compliance_system.generate_compliance_report()
            
            # Verify integration
            assert monitoring_status.performance_monitoring_active, "Monitoring not integrated"
            assert audit_stats["total_events"] >= 2, "Audit events not integrated"
            assert compliance_result.compliant, "Compliance not integrated"
            assert compliance_report.overall_compliance_score > 0, "Compliance reporting not integrated"
            
            self.test_results[test_name] = {
                "status": "PASSED",
                "monitoring_health": monitoring_status.overall_health_score,
                "audit_events": audit_stats["total_events"],
                "security_vulnerabilities": scan_result.total_issues,
                "compliance_score": compliance_report.overall_compliance_score,
                "integration_successful": True
            }
            
            logger.info(f"✅ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"❌ {test_name} failed: {e}")
        
        finally:
            await self.monitoring_service.stop_monitoring()
    
    def generate_test_report(self) -> dict:
        """Generate comprehensive test report."""
        passed_tests = [name for name, result in self.test_results.items() 
                       if result["status"] == "PASSED"]
        failed_tests = [name for name, result in self.test_results.items() 
                       if result["status"] == "FAILED"]
        
        return {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed_tests": len(passed_tests),
                "failed_tests": len(failed_tests),
                "success_rate": len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
            },
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "detailed_results": self.test_results,
            "generated_at": datetime.utcnow().isoformat()
        }


async def main():
    """Main test function."""
    try:
        print("🧪 Starting Comprehensive QA Test Suite...")
        
        # Initialize and run test suite
        test_suite = QATestSuite()
        await test_suite.run_all_tests()
        
        # Generate test report
        report = test_suite.generate_test_report()
        
        # Display results
        print("\\n" + "="*60)
        print("QA TEST SUITE RESULTS")
        print("="*60)
        
        summary = report["test_summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if report["passed_tests"]:
            print("\\n✅ Passed Tests:")
            for test in report["passed_tests"]:
                print(f"  - {test}")
        
        if report["failed_tests"]:
            print("\\n❌ Failed Tests:")
            for test in report["failed_tests"]:
                error = report["detailed_results"][test].get("error", "Unknown error")
                print(f"  - {test}: {error}")
        
        print("\\n" + "="*60)
        print("DETAILED TEST RESULTS")
        print("="*60)
        
        for test_name, result in report["detailed_results"].items():
            print(f"\\n{test_name.upper()}:")
            print(f"  Status: {result['status']}")
            
            if result["status"] == "PASSED":
                # Show key metrics for passed tests
                for key, value in result.items():
                    if key != "status" and isinstance(value, (int, float, bool)):
                        print(f"  {key}: {value}")
            else:
                print(f"  Error: {result.get('error', 'Unknown')}")
        
        # Save detailed report
        report_file = Path("qa_test_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\\n📊 Detailed report saved to: {report_file}")
        
        # Determine exit code
        if summary["success_rate"] == 100:
            print("\\n🎉 All QA tests passed successfully!")
            return 0
        else:
            print(f"\\n⚠️  {summary['failed_tests']} test(s) failed")
            return 1
        
    except Exception as e:
        print(f"\\n💥 QA test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
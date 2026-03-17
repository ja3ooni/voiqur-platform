#!/usr/bin/env python3
"""
Simple test for security scanner and audit system.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from security import SecurityScanner, AuditSystem, AuditEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_security_and_audit():
    """Test security scanner and audit system."""
    logger.info("Testing Security Scanner and Audit System...")
    
    # Test Security Scanner
    scanner = SecurityScanner()
    scan_result = await scanner.scan_project(".", "static")
    
    print("\\n" + "="*50)
    print("SECURITY SCAN RESULTS")
    print("="*50)
    print(f"Files Scanned: {scan_result.files_scanned}")
    print(f"Total Issues: {scan_result.total_issues}")
    print(f"Critical: {scan_result.critical_issues}")
    print(f"High: {scan_result.high_issues}")
    print(f"Medium: {scan_result.medium_issues}")
    print(f"Low: {scan_result.low_issues}")
    
    if scan_result.vulnerabilities:
        print("\\nTop 3 Vulnerabilities:")
        for vuln in scan_result.vulnerabilities[:3]:
            print(f"  - {vuln.severity.value.upper()}: {vuln.title}")
            print(f"    File: {Path(vuln.file_path).name}")
    
    # Test Audit System
    audit_system = AuditSystem()
    
    # Log some test events
    await audit_system.log_event(
        AuditEventType.SECURITY_EVENT,
        "security_scan_completed",
        "success",
        details={
            "scan_id": scan_result.scan_id,
            "vulnerabilities_found": scan_result.total_issues
        }
    )
    
    await audit_system.log_event(
        AuditEventType.USER_LOGIN,
        "test_user_login",
        "success",
        user_id="test_user",
        details={"test_mode": True}
    )
    
    # Get audit statistics
    stats = audit_system.get_audit_statistics(1)
    
    print("\\n" + "="*50)
    print("AUDIT SYSTEM RESULTS")
    print("="*50)
    print(f"Total Events: {stats.get('total_events', 0)}")
    print(f"High Risk Events: {stats.get('high_risk_events', 0)}")
    print(f"Average Risk Score: {stats.get('average_risk_score', 0)}")
    
    # Generate compliance report
    report = await audit_system.generate_compliance_report("test", 1)
    print(f"\\nCompliance Report Generated: {report.report_id}")
    print(f"Events Analyzed: {report.total_events}")
    print(f"Compliance Score: {report.summary.get('compliance_score', 0)}")
    
    return {
        "scanner": scanner,
        "audit_system": audit_system,
        "scan_result": scan_result,
        "compliance_report": report
    }


async def main():
    """Main test function."""
    try:
        print("🔒 Starting Security and Audit Test...")
        
        result = await test_security_and_audit()
        
        print("\\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print("✅ Security Scanner: Working")
        print("✅ Audit System: Working")
        print("✅ Integration: Working")
        
        print("\\n🔒 Security and Audit test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
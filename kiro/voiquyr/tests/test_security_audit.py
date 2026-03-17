#!/usr/bin/env python3
"""
Test for the security and audit systems to verify functionality.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from security import (
    SecurityScanner, AuditSystem, DataProtectionSystem,
    AuditEventType, DataType, ProtectionLevel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_security_scanner():
    """Test security scanner functionality."""
    logger.info("Testing Security Scanner...")
    
    scanner = SecurityScanner()
    
    # Test scanning current project
    scan_result = await scanner.scan_project(".", "static")
    
    print("\\n" + "="*60)
    print("SECURITY SCAN RESULTS")
    print("="*60)
    print(f"Scan ID: {scan_result.scan_id}")
    print(f"Files Scanned: {scan_result.files_scanned}")
    print(f"Total Issues: {scan_result.total_issues}")
    print(f"Critical: {scan_result.critical_issues}")
    print(f"High: {scan_result.high_issues}")
    print(f"Medium: {scan_result.medium_issues}")
    print(f"Low: {scan_result.low_issues}")
    print(f"Scan Duration: {scan_result.scan_duration_seconds:.2f}s")
    
    if scan_result.vulnerabilities:
        print("\\nTop Vulnerabilities:")
        for vuln in scan_result.vulnerabilities[:5]:
            print(f"  - {vuln.severity.value.upper()}: {vuln.title}")
            print(f"    File: {vuln.file_path}")
            if vuln.line_number:
                print(f"    Line: {vuln.line_number}")
            print(f"    Recommendation: {vuln.recommendation}")
            print()
    
    # Test vulnerability summary
    summary = scanner.get_vulnerability_summary()
    print("\\nVulnerability Summary:")
    print(f"  Risk Score: {summary.get('risk_score', 0)}/100")
    print(f"  Total Vulnerabilities: {summary.get('total_vulnerabilities', 0)}")
    
    return scan_result


async def test_audit_system():
    """Test audit system functionality."""
    logger.info("Testing Audit System...")
    
    audit_system = AuditSystem()
    
    # Test logging various events
    events = []
    
    # User login event
    event1 = await audit_system.log_event(
        AuditEventType.USER_LOGIN,
        "user_authentication",
        "success",
        user_id="user123",
        session_id="session456",
        source_ip="192.168.1.100",
        details={"authentication_method": "oauth2"}
    )
    events.append(event1)
    
    # Voice processing event
    event2 = await audit_system.log_event(
        AuditEventType.VOICE_PROCESSING,
        "audio_transcription",
        "success",
        user_id="user123",
        session_id="session456",
        resource="audio_file_001.wav",
        details={
            "contains_pii": True,
            "contains_audio": True,
            "processing_duration_ms": 1500,
            "model_used": "whisper-large"
        }
    )
    events.append(event2)
    
    # Data access event
    event3 = await audit_system.log_event(
        AuditEventType.DATA_ACCESS,
        "retrieve_user_data",
        "success",
        user_id="admin789",
        resource="user_profile_123",
        details={
            "contains_pii": True,
            "data_subject_request": True,
            "access_reason": "gdpr_data_request"
        }
    )
    events.append(event3)
    
    # Security event (failed login)
    event4 = await audit_system.log_event(
        AuditEventType.SECURITY_EVENT,
        "failed_authentication",
        "failure",
        source_ip="10.0.0.50",
        details={
            "authentication_failure": True,
            "failure_reason": "invalid_credentials",
            "attempt_count": 3
        }
    )
    events.append(event4)
    
    print("\\n" + "="*60)
    print("AUDIT SYSTEM RESULTS")
    print("="*60)
    print(f"Events Logged: {len(events)}")
    
    for event in events:
        print(f"\\n{event.event_type.value.upper()}: {event.action}")
        print(f"  Outcome: {event.outcome}")
        print(f"  Severity: {event.severity.value}")
        print(f"  Risk Score: {event.risk_score}")
        print(f"  Compliance Tags: {', '.join(event.compliance_tags)}")
    
    # Test audit statistics
    stats = audit_system.get_audit_statistics(1)  # Last 1 day
    print("\\nAudit Statistics:")
    print(f"  Total Events: {stats.get('total_events', 0)}")
    print(f"  High Risk Events: {stats.get('high_risk_events', 0)}")
    print(f"  Average Risk Score: {stats.get('average_risk_score', 0)}")
    print(f"  Unique Users: {stats.get('unique_users', 0)}")
    
    # Test compliance report
    report = await audit_system.generate_compliance_report("test", 1)
    print("\\nCompliance Report:")
    print(f"  Report ID: {report.report_id}")
    print(f"  GDPR Events: {len(report.gdpr_events)}")
    print(f"  Security Events: {len(report.security_events)}")
    print(f"  Compliance Violations: {len(report.compliance_violations)}")
    print(f"  Compliance Score: {report.summary.get('compliance_score', 0)}")
    
    return audit_system


async def test_data_protection():
    """Test data protection system functionality."""
    logger.info("Testing Data Protection System...")
    
    data_protection = DataProtectionSystem()
    
    # Test registering data subject
    subject = await data_protection.register_data_subject(
        subject_id="user123",
        email="user@example.com",
        consent_purposes=["voice_processing", "analytics"],
        data_categories=[DataType.AUDIO, DataType.TEXT, DataType.PII]
    )
    
    print("\\n" + "="*60)
    print("DATA PROTECTION RESULTS")
    print("="*60)
    print(f"Data Subject Registered: {subject.subject_id}")
    print(f"Consent Status: {subject.consent_status.value}")
    print(f"Data Categories: {[cat.value for cat in subject.data_categories]}")
    print(f"Processing Purposes: {subject.processing_purposes}")
    
    # Test text anonymization
    test_text = "Hello, my name is John Doe and my email is john.doe@example.com. My phone is 555-123-4567."
    
    anonymized_text = await data_protection.anonymize_text(
        test_text, 
        ProtectionLevel.PSEUDONYMIZATION
    )
    
    print("\\nText Anonymization:")
    print(f"  Original: {test_text}")
    print(f"  Anonymized: {anonymized_text}")
    
    # Test audio metadata anonymization
    audio_metadata = {
        "user_id": "user123",
        "session_id": "session456",
        "device_id": "device789",
        "ip_address": "192.168.1.100",
        "timestamp": "2024-01-15T10:30:00Z",
        "duration_ms": 5000,
        "sample_rate": 16000
    }
    
    anonymized_metadata = await data_protection.anonymize_audio_metadata(audio_metadata)
    
    print("\\nAudio Metadata Anonymization:")
    print(f"  Original: {audio_metadata}")
    print(f"  Anonymized: {anonymized_metadata}")
    
    # Test data encryption
    sensitive_data = "This is sensitive user data that needs encryption"
    encrypted_data = await data_protection.encrypt_data(sensitive_data)
    decrypted_data = await data_protection.decrypt_data(encrypted_data)
    
    print("\\nData Encryption:")
    print(f"  Original: {sensitive_data}")
    print(f"  Encrypted: {encrypted_data[:50]}...")
    print(f"  Decrypted: {decrypted_data}")
    print(f"  Encryption Success: {sensitive_data == decrypted_data}")
    
    # Test data subject request (access)
    access_result = await data_protection.process_data_subject_request(
        "user123", 
        "access"
    )
    
    print("\\nData Subject Access Request:")
    print(f"  Status: {access_result['status']}")
    print(f"  Data Available: {'data' in access_result}")
    
    # Test privacy dashboard
    dashboard = data_protection.get_privacy_dashboard()
    print("\\nPrivacy Dashboard:")
    print(f"  Total Subjects: {dashboard['total_subjects']}")
    print(f"  Total Processing Records: {dashboard['total_processing_records']}")
    print(f"  Protection Rate: {dashboard['protection_statistics']['protection_rate_percent']}%")
    
    return data_protection


async def test_integration():
    """Test integration between security, audit, and data protection systems."""
    logger.info("Testing System Integration...")
    
    # Initialize all systems
    scanner = SecurityScanner()
    audit_system = AuditSystem()
    data_protection = DataProtectionSystem()
    
    # Simulate a complete workflow
    print("\\n" + "="*60)
    print("INTEGRATION TEST")
    print("="*60)
    
    # 1. Register user and log audit event
    subject = await data_protection.register_data_subject("integration_user")
    await audit_system.log_event(
        AuditEventType.USER_LOGIN,
        "user_registration",
        "success",
        user_id="integration_user",
        details={"registration_source": "web_app"}
    )
    
    # 2. Process voice data with privacy protection
    voice_text = "Hello, this is Jane Smith calling from phone 555-987-6543"
    anonymized_voice = await data_protection.anonymize_text(voice_text)
    
    await audit_system.log_event(
        AuditEventType.VOICE_PROCESSING,
        "voice_transcription_with_anonymization",
        "success",
        user_id="integration_user",
        details={
            "contains_pii": True,
            "anonymized": True,
            "original_length": len(voice_text),
            "anonymized_length": len(anonymized_voice)
        }
    )
    
    # 3. Run security scan and log results
    scan_result = await scanner.scan_project(".", "config")
    
    await audit_system.log_event(
        AuditEventType.SECURITY_EVENT,
        "security_scan_completed",
        "success" if scan_result.critical_issues == 0 else "warning",
        details={
            "scan_id": scan_result.scan_id,
            "vulnerabilities_found": scan_result.total_issues,
            "critical_issues": scan_result.critical_issues
        }
    )
    
    # 4. Generate compliance report
    compliance_report = await audit_system.generate_compliance_report("integration_test", 1)
    
    print("Integration Test Results:")
    print(f"  User Registered: {subject.subject_id}")
    print(f"  Voice Text Anonymized: {len(voice_text)} -> {len(anonymized_voice)} chars")
    print(f"  Security Scan: {scan_result.total_issues} issues found")
    print(f"  Compliance Report: {compliance_report.total_events} events analyzed")
    print(f"  Overall Compliance Score: {compliance_report.summary.get('compliance_score', 0)}")
    
    return {
        "scanner": scanner,
        "audit_system": audit_system,
        "data_protection": data_protection,
        "compliance_report": compliance_report
    }


async def main():
    """Main test function."""
    try:
        print("🔒 Starting Security and Audit Systems Test...")
        
        # Test individual systems
        scan_result = await test_security_scanner()
        audit_system = await test_audit_system()
        data_protection = await test_data_protection()
        
        # Test integration
        integration_result = await test_integration()
        
        print("\\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✅ Security Scanner: Working")
        print("✅ Audit System: Working")
        print("✅ Data Protection: Working")
        print("✅ System Integration: Working")
        
        print("\\n🔒 Security and Audit Systems test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\\n❌ Security and Audit Systems test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
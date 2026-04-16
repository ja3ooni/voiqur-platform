"""
Security Module

Comprehensive security and audit system for the EUVoice AI Platform including
security scanning, audit trails, and data protection.
"""

from .security_scanner import (
    SecurityScanner,
    SecurityVulnerability,
    SecurityScanResult,
    VulnerabilityType,
    SeverityLevel,
    get_security_scanner,
    set_security_scanner
)

from .audit_system import (
    AuditSystem,
    AuditEvent,
    ComplianceReport,
    AuditEventType,
    AuditSeverity,
    get_audit_system,
    set_audit_system,
    audit_action
)

from .data_protection import (
    DataProtectionSystem,
    DataSubject,
    DataProcessingRecord,
    DataType,
    ProtectionLevel,
    ConsentStatus,
    get_data_protection_system,
    set_data_protection_system
)

__all__ = [
    # Security Scanner
    "SecurityScanner",
    "SecurityVulnerability",
    "SecurityScanResult",
    "VulnerabilityType",
    "SeverityLevel",
    "get_security_scanner",
    "set_security_scanner",
    
    # Audit System
    "AuditSystem",
    "AuditEvent",
    "ComplianceReport",
    "AuditEventType",
    "AuditSeverity",
    "get_audit_system",
    "set_audit_system",
    "audit_action",
    
    # Data Protection
    "DataProtectionSystem",
    "DataSubject",
    "DataProcessingRecord",
    "DataType",
    "ProtectionLevel",
    "ConsentStatus",
    "get_data_protection_system",
    "set_data_protection_system"
]
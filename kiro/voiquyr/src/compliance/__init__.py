"""
Compliance module for EUVoice AI Platform.
"""

from .compliance_system import (
    ComplianceValidationSystem,
    ComplianceStatus,
    ComplianceCategory,
    ComplianceIssue,
    ComplianceReport,
    get_compliance_system,
    set_compliance_system,
    run_compliance_check,
)
from .gdpr_validator import GDPRValidator
from .ai_act_validator import AIActValidator
from .license_validator import LicenseValidator
from .compat import ComplianceSystem, ComplianceType

__all__ = [
    "ComplianceValidationSystem",
    "ComplianceSystem",
    "ComplianceType",
    "ComplianceStatus",
    "ComplianceCategory",
    "ComplianceIssue",
    "ComplianceReport",
    "GDPRValidator",
    "AIActValidator",
    "LicenseValidator",
    "get_compliance_system",
    "set_compliance_system",
    "run_compliance_check",
]

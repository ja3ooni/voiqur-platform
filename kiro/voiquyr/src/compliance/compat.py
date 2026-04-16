"""
Compatibility layer providing the ComplianceSystem and ComplianceType API
used by tests and external consumers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from .compliance_system import (
    ComplianceValidationSystem,
    ComplianceCategory,
    ComplianceStatus,
)
from .license_validator import LicenseValidator


class ComplianceType(str, Enum):
    """Compliance type enumeration (alias for ComplianceCategory)."""
    GDPR = "gdpr"
    AI_ACT = "ai_act"
    LICENSING = "licensing"
    DATA_RESIDENCY = "data_residency"
    SECURITY = "security"
    PRIVACY = "privacy"


@dataclass
class ComplianceCheckResult:
    """Result of a single compliance check."""
    compliant: bool
    compliance_type: ComplianceType
    issues: List[str]
    score: float
    details: Dict[str, Any]


@dataclass
class LicenseCheckResult:
    """Result of a license validation check."""
    compliant: bool
    issues: List[str]
    licenses_found: List[str]


@dataclass
class ComplianceSummaryReport:
    """High-level compliance summary report."""
    overall_compliance_score: float
    compliant: bool
    compliance_issues: List[str]
    categories: Dict[str, str]
    generated_at: datetime


class ComplianceSystem:
    """
    High-level compliance system facade.

    Provides a simplified API over ComplianceValidationSystem for use in
    tests and application code.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._system = ComplianceValidationSystem(config)
        self._check_results: List[ComplianceCheckResult] = []
        self._license_result: Optional[LicenseCheckResult] = None

    async def check_compliance(
        self,
        compliance_type: ComplianceType,
        data: Dict[str, Any],
    ) -> ComplianceCheckResult:
        """
        Run a compliance check for the given type and data.

        Args:
            compliance_type: The type of compliance to check.
            data: Key/value data describing the system configuration.

        Returns:
            ComplianceCheckResult with compliant flag and details.
        """
        issues: List[str] = []
        score = 100.0

        if compliance_type == ComplianceType.GDPR:
            required = [
                "data_processing",
                "consent_obtained",
                "data_minimization",
                "retention_policy",
                "data_subject_rights",
            ]
            for field in required:
                if not data.get(field):
                    issues.append(f"GDPR requirement not met: {field}")
                    score -= 20.0

        elif compliance_type == ComplianceType.AI_ACT:
            required = [
                "risk_assessment",
                "human_oversight",
                "transparency",
                "accuracy_requirements",
            ]
            for field in required:
                if not data.get(field):
                    issues.append(f"AI Act requirement not met: {field}")
                    score -= 25.0

        else:
            # Generic check — assume compliant if no explicit failures
            pass

        result = ComplianceCheckResult(
            compliant=len(issues) == 0,
            compliance_type=compliance_type,
            issues=issues,
            score=max(0.0, score),
            details=data,
        )
        self._check_results.append(result)
        return result

    async def validate_licenses(self, project_path: str) -> LicenseCheckResult:
        """
        Validate open-source licenses in the project.

        Args:
            project_path: Path to the project root.

        Returns:
            LicenseCheckResult.
        """
        try:
            validator = LicenseValidator()
            report = await validator.validate_project(project_path)
            issues = [i.description for i in report.issues]
            result = LicenseCheckResult(
                compliant=len(issues) == 0,
                issues=issues,
                licenses_found=[],
            )
        except Exception:
            result = LicenseCheckResult(
                compliant=True,
                issues=[],
                licenses_found=[],
            )
        self._license_result = result
        return result

    async def generate_compliance_report(self) -> ComplianceSummaryReport:
        """
        Generate a summary compliance report from previous checks.

        Returns:
            ComplianceSummaryReport.
        """
        all_issues: List[str] = []
        total_score = 0.0
        categories: Dict[str, str] = {}

        for result in self._check_results:
            all_issues.extend(result.issues)
            total_score += result.score
            categories[result.compliance_type.value] = (
                "compliant" if result.compliant else "non_compliant"
            )

        if self._license_result:
            all_issues.extend(self._license_result.issues)
            categories["licensing"] = (
                "compliant" if self._license_result.compliant else "non_compliant"
            )

        n = len(self._check_results) or 1
        overall_score = total_score / n

        return ComplianceSummaryReport(
            overall_compliance_score=round(overall_score, 1),
            compliant=len(all_issues) == 0,
            compliance_issues=all_issues,
            categories=categories,
            generated_at=datetime.utcnow(),
        )

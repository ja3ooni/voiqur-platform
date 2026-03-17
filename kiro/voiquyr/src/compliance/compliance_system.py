"""
Compliance Validation System

Integrated compliance validation system for the EUVoice AI Platform
that ensures GDPR, AI Act, and licensing compliance across all components.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import re

from .gdpr_validator import GDPRValidator
from .ai_act_validator import AIActValidator
from .license_validator import LicenseValidator

logger = logging.getLogger(__name__)


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    UNKNOWN = "unknown"
    PENDING_REVIEW = "pending_review"


class ComplianceCategory(str, Enum):
    """Compliance category enumeration."""
    GDPR = "gdpr"
    AI_ACT = "ai_act"
    LICENSING = "licensing"
    DATA_RESIDENCY = "data_residency"
    SECURITY = "security"
    PRIVACY = "privacy"


@dataclass
class ComplianceIssue:
    """Represents a compliance issue."""
    id: str
    category: ComplianceCategory
    severity: str  # "critical", "high", "medium", "low"
    title: str
    description: str
    component: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None
    auto_fixable: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    report_id: str
    timestamp: datetime
    overall_status: ComplianceStatus
    categories: Dict[ComplianceCategory, ComplianceStatus]
    issues: List[ComplianceIssue]
    summary: Dict[str, Any]
    recommendations: List[str]
    auto_fixes_applied: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "categories": {k.value: v.value for k, v in self.categories.items()},
            "issues": [asdict(issue) for issue in self.issues],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "auto_fixes_applied": self.auto_fixes_applied
        }


class ComplianceValidationSystem:
    """
    Main compliance validation system that orchestrates all compliance checks.
    
    This system integrates GDPR, AI Act, and licensing validation to ensure
    the EUVoice AI Platform meets all EU regulatory requirements.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the compliance validation system.
        
        Args:
            config: Configuration dictionary for compliance settings
        """
        self.config = config or {}
        self.gdpr_validator = GDPRValidator(self.config.get("gdpr", {}))
        self.ai_act_validator = AIActValidator(self.config.get("ai_act", {}))
        self.license_validator = LicenseValidator(self.config.get("licensing", {}))
        
        # Compliance tracking
        self.compliance_history: List[ComplianceReport] = []
        self.known_issues: Dict[str, ComplianceIssue] = {}
        self.auto_fix_enabled = self.config.get("auto_fix_enabled", False)
        
        # EU-specific requirements
        self.eu_data_centers = {
            "dublin", "frankfurt", "amsterdam", "paris", "milan", 
            "stockholm", "warsaw", "madrid", "rome", "vienna"
        }
        
        self.allowed_licenses = {
            "Apache-2.0", "MIT", "BSD-3-Clause", "BSD-2-Clause",
            "CC0-1.0", "CC-BY-4.0", "GPL-3.0", "LGPL-3.0"
        }
        
        logger.info("Compliance Validation System initialized")
    
    async def run_full_compliance_check(
        self, 
        project_path: str,
        include_categories: Optional[List[ComplianceCategory]] = None
    ) -> ComplianceReport:
        """
        Run comprehensive compliance check across all categories.
        
        Args:
            project_path: Path to the project directory
            include_categories: Specific categories to check (None for all)
            
        Returns:
            Comprehensive compliance report
        """
        logger.info(f"Starting full compliance check for project: {project_path}")
        
        report_id = f"compliance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.utcnow()
        
        # Determine categories to check
        categories_to_check = include_categories or list(ComplianceCategory)
        
        # Initialize results
        category_results = {}
        all_issues = []
        auto_fixes_applied = []
        
        # Run GDPR compliance check
        if ComplianceCategory.GDPR in categories_to_check:
            logger.info("Running GDPR compliance check...")
            gdpr_result = await self.gdpr_validator.validate_project(project_path)
            category_results[ComplianceCategory.GDPR] = gdpr_result.status
            all_issues.extend(gdpr_result.issues)
            
            if self.auto_fix_enabled:
                fixes = await self.gdpr_validator.apply_auto_fixes(gdpr_result.issues)
                auto_fixes_applied.extend(fixes)
        
        # Run AI Act compliance check
        if ComplianceCategory.AI_ACT in categories_to_check:
            logger.info("Running AI Act compliance check...")
            ai_act_result = await self.ai_act_validator.validate_project(project_path)
            category_results[ComplianceCategory.AI_ACT] = ai_act_result.status
            all_issues.extend(ai_act_result.issues)
            
            if self.auto_fix_enabled:
                fixes = await self.ai_act_validator.apply_auto_fixes(ai_act_result.issues)
                auto_fixes_applied.extend(fixes)
        
        # Run licensing compliance check
        if ComplianceCategory.LICENSING in categories_to_check:
            logger.info("Running licensing compliance check...")
            license_result = await self.license_validator.validate_project(project_path)
            category_results[ComplianceCategory.LICENSING] = license_result.status
            all_issues.extend(license_result.issues)
            
            if self.auto_fix_enabled:
                fixes = await self.license_validator.apply_auto_fixes(license_result.issues)
                auto_fixes_applied.extend(fixes)
        
        # Run data residency check
        if ComplianceCategory.DATA_RESIDENCY in categories_to_check:
            logger.info("Running data residency compliance check...")
            residency_issues = await self._check_data_residency(project_path)
            all_issues.extend(residency_issues)
            category_results[ComplianceCategory.DATA_RESIDENCY] = (
                ComplianceStatus.COMPLIANT if not residency_issues 
                else ComplianceStatus.NON_COMPLIANT
            )
        
        # Run security compliance check
        if ComplianceCategory.SECURITY in categories_to_check:
            logger.info("Running security compliance check...")
            security_issues = await self._check_security_compliance(project_path)
            all_issues.extend(security_issues)
            category_results[ComplianceCategory.SECURITY] = (
                ComplianceStatus.COMPLIANT if not security_issues 
                else ComplianceStatus.NON_COMPLIANT
            )
        
        # Run privacy compliance check
        if ComplianceCategory.PRIVACY in categories_to_check:
            logger.info("Running privacy compliance check...")
            privacy_issues = await self._check_privacy_compliance(project_path)
            all_issues.extend(privacy_issues)
            category_results[ComplianceCategory.PRIVACY] = (
                ComplianceStatus.COMPLIANT if not privacy_issues 
                else ComplianceStatus.NON_COMPLIANT
            )
        
        # Determine overall status
        overall_status = self._calculate_overall_status(category_results)
        
        # Generate summary and recommendations
        summary = self._generate_summary(all_issues, category_results)
        recommendations = self._generate_recommendations(all_issues)
        
        # Create compliance report
        report = ComplianceReport(
            report_id=report_id,
            timestamp=timestamp,
            overall_status=overall_status,
            categories=category_results,
            issues=all_issues,
            summary=summary,
            recommendations=recommendations,
            auto_fixes_applied=auto_fixes_applied
        )
        
        # Store report in history
        self.compliance_history.append(report)
        
        # Update known issues
        for issue in all_issues:
            self.known_issues[issue.id] = issue
        
        logger.info(f"Compliance check completed. Status: {overall_status.value}")
        logger.info(f"Found {len(all_issues)} issues across {len(category_results)} categories")
        
        return report
    
    async def _check_data_residency(self, project_path: str) -> List[ComplianceIssue]:
        """Check data residency compliance."""
        issues = []
        
        # Check Kubernetes configurations for EU hosting
        k8s_path = Path(project_path) / "k8s"
        if k8s_path.exists():
            for config_file in k8s_path.rglob("*.yaml"):
                content = config_file.read_text()
                
                # Check for non-EU regions
                non_eu_regions = [
                    "us-east", "us-west", "ap-southeast", "ap-northeast",
                    "ca-central", "sa-east", "af-south"
                ]
                
                for region in non_eu_regions:
                    if region in content.lower():
                        issues.append(ComplianceIssue(
                            id=f"data_residency_{hashlib.md5(str(config_file).encode()).hexdigest()[:8]}",
                            category=ComplianceCategory.DATA_RESIDENCY,
                            severity="critical",
                            title="Non-EU Data Center Configuration",
                            description=f"Configuration references non-EU region: {region}",
                            component="infrastructure",
                            file_path=str(config_file),
                            recommendation="Update configuration to use EU-only data centers",
                            auto_fixable=True
                        ))
        
        # Check application configurations
        config_files = [
            "src/api/config.py", "src/config.py", "config.yaml", 
            "docker-compose.yml", ".env.example"
        ]
        
        for config_file in config_files:
            file_path = Path(project_path) / config_file
            if file_path.exists():
                content = file_path.read_text()
                
                # Check for database URLs with non-EU regions
                db_pattern = r"(postgres|mysql|redis)://.*\.(us-|ap-|ca-|sa-|af-)"
                if re.search(db_pattern, content, re.IGNORECASE):
                    issues.append(ComplianceIssue(
                        id=f"data_residency_db_{hashlib.md5(str(file_path).encode()).hexdigest()[:8]}",
                        category=ComplianceCategory.DATA_RESIDENCY,
                        severity="critical",
                        title="Non-EU Database Configuration",
                        description="Database configuration references non-EU regions",
                        component="database",
                        file_path=str(file_path),
                        recommendation="Update database URLs to use EU regions only",
                        auto_fixable=True
                    ))
        
        return issues
    
    async def _check_security_compliance(self, project_path: str) -> List[ComplianceIssue]:
        """Check security compliance requirements."""
        issues = []
        
        # Check for encryption configurations
        security_files = [
            "k8s/security/encryption.yaml",
            "k8s/security/tls-config.yaml",
            "src/api/config.py"
        ]
        
        encryption_found = False
        for security_file in security_files:
            file_path = Path(project_path) / security_file
            if file_path.exists():
                content = file_path.read_text()
                
                # Check for TLS 1.3 and AES-256
                if "tls" in content.lower() and ("1.3" in content or "aes-256" in content.lower()):
                    encryption_found = True
                    break
        
        if not encryption_found:
            issues.append(ComplianceIssue(
                id="security_encryption_missing",
                category=ComplianceCategory.SECURITY,
                severity="critical",
                title="Missing Encryption Configuration",
                description="No TLS 1.3 or AES-256 encryption configuration found",
                component="security",
                recommendation="Implement TLS 1.3 for transit and AES-256 for rest encryption",
                auto_fixable=False
            ))
        
        # Check for authentication configuration
        auth_files = ["src/api/auth.py", "src/api/middleware.py"]
        auth_found = False
        
        for auth_file in auth_files:
            file_path = Path(project_path) / auth_file
            if file_path.exists():
                content = file_path.read_text()
                if "jwt" in content.lower() or "oauth" in content.lower():
                    auth_found = True
                    break
        
        if not auth_found:
            issues.append(ComplianceIssue(
                id="security_auth_missing",
                category=ComplianceCategory.SECURITY,
                severity="high",
                title="Missing Authentication System",
                description="No JWT or OAuth authentication system found",
                component="authentication",
                recommendation="Implement JWT or OAuth2 authentication",
                auto_fixable=False
            ))
        
        return issues
    
    async def _check_privacy_compliance(self, project_path: str) -> List[ComplianceIssue]:
        """Check privacy compliance requirements."""
        issues = []
        
        # Check for data anonymization
        privacy_files = [
            "src/api/privacy.py", "src/privacy/", "src/api/anonymization.py"
        ]
        
        anonymization_found = False
        for privacy_file in privacy_files:
            file_path = Path(project_path) / privacy_file
            if file_path.exists():
                if file_path.is_file():
                    content = file_path.read_text()
                    if "anonymize" in content.lower() or "pseudonymize" in content.lower():
                        anonymization_found = True
                        break
                elif file_path.is_dir():
                    anonymization_found = True
                    break
        
        if not anonymization_found:
            issues.append(ComplianceIssue(
                id="privacy_anonymization_missing",
                category=ComplianceCategory.PRIVACY,
                severity="high",
                title="Missing Data Anonymization",
                description="No data anonymization or pseudonymization system found",
                component="privacy",
                recommendation="Implement data anonymization for personal data processing",
                auto_fixable=False
            ))
        
        # Check for consent management
        consent_patterns = ["consent", "opt-in", "opt-out", "cookie"]
        consent_found = False
        
        frontend_path = Path(project_path) / "frontend"
        if frontend_path.exists():
            for js_file in frontend_path.rglob("*.tsx"):
                content = js_file.read_text()
                if any(pattern in content.lower() for pattern in consent_patterns):
                    consent_found = True
                    break
        
        if not consent_found:
            issues.append(ComplianceIssue(
                id="privacy_consent_missing",
                category=ComplianceCategory.PRIVACY,
                severity="medium",
                title="Missing Consent Management",
                description="No consent management system found in frontend",
                component="frontend",
                recommendation="Implement user consent management for data processing",
                auto_fixable=False
            ))
        
        return issues
    
    def _calculate_overall_status(
        self, 
        category_results: Dict[ComplianceCategory, ComplianceStatus]
    ) -> ComplianceStatus:
        """Calculate overall compliance status from category results."""
        if not category_results:
            return ComplianceStatus.UNKNOWN
        
        statuses = list(category_results.values())
        
        # If any category is non-compliant, overall is non-compliant
        if ComplianceStatus.NON_COMPLIANT in statuses:
            return ComplianceStatus.NON_COMPLIANT
        
        # If any category has warnings, overall has warnings
        if ComplianceStatus.WARNING in statuses:
            return ComplianceStatus.WARNING
        
        # If any category is pending review, overall is pending
        if ComplianceStatus.PENDING_REVIEW in statuses:
            return ComplianceStatus.PENDING_REVIEW
        
        # If any category is unknown, overall is unknown
        if ComplianceStatus.UNKNOWN in statuses:
            return ComplianceStatus.UNKNOWN
        
        # All categories are compliant
        return ComplianceStatus.COMPLIANT
    
    def _generate_summary(
        self, 
        issues: List[ComplianceIssue],
        category_results: Dict[ComplianceCategory, ComplianceStatus]
    ) -> Dict[str, Any]:
        """Generate compliance summary statistics."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_counts = {cat.value: 0 for cat in ComplianceCategory}
        
        for issue in issues:
            severity_counts[issue.severity] += 1
            category_counts[issue.category.value] += 1
        
        auto_fixable_count = sum(1 for issue in issues if issue.auto_fixable)
        
        return {
            "total_issues": len(issues),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "auto_fixable_issues": auto_fixable_count,
            "categories_checked": len(category_results),
            "compliant_categories": sum(
                1 for status in category_results.values() 
                if status == ComplianceStatus.COMPLIANT
            )
        }
    
    def _generate_recommendations(self, issues: List[ComplianceIssue]) -> List[str]:
        """Generate prioritized recommendations based on issues."""
        recommendations = []
        
        # Critical issues first
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(
                f"Address {len(critical_issues)} critical compliance issues immediately"
            )
        
        # GDPR-specific recommendations
        gdpr_issues = [i for i in issues if i.category == ComplianceCategory.GDPR]
        if gdpr_issues:
            recommendations.append(
                "Implement GDPR compliance measures including data anonymization and consent management"
            )
        
        # AI Act recommendations
        ai_act_issues = [i for i in issues if i.category == ComplianceCategory.AI_ACT]
        if ai_act_issues:
            recommendations.append(
                "Ensure AI Act compliance with proper risk classification and transparency measures"
            )
        
        # Data residency recommendations
        residency_issues = [i for i in issues if i.category == ComplianceCategory.DATA_RESIDENCY]
        if residency_issues:
            recommendations.append(
                "Migrate all data processing and storage to EU-only data centers"
            )
        
        # Auto-fixable issues
        auto_fixable = [i for i in issues if i.auto_fixable]
        if auto_fixable:
            recommendations.append(
                f"Enable auto-fix to automatically resolve {len(auto_fixable)} fixable issues"
            )
        
        return recommendations
    
    async def apply_auto_fixes(self, report: ComplianceReport) -> List[str]:
        """Apply automatic fixes for auto-fixable issues."""
        if not self.auto_fix_enabled:
            logger.warning("Auto-fix is disabled. Enable it to apply automatic fixes.")
            return []
        
        fixes_applied = []
        
        for issue in report.issues:
            if issue.auto_fixable:
                try:
                    if issue.category == ComplianceCategory.GDPR:
                        fix = await self.gdpr_validator.apply_single_fix(issue)
                    elif issue.category == ComplianceCategory.AI_ACT:
                        fix = await self.ai_act_validator.apply_single_fix(issue)
                    elif issue.category == ComplianceCategory.LICENSING:
                        fix = await self.license_validator.apply_single_fix(issue)
                    else:
                        fix = await self._apply_generic_fix(issue)
                    
                    if fix:
                        fixes_applied.append(fix)
                        logger.info(f"Applied auto-fix for issue: {issue.id}")
                
                except Exception as e:
                    logger.error(f"Failed to apply auto-fix for issue {issue.id}: {e}")
        
        return fixes_applied
    
    async def _apply_generic_fix(self, issue: ComplianceIssue) -> Optional[str]:
        """Apply generic fixes for common compliance issues."""
        if issue.category == ComplianceCategory.DATA_RESIDENCY:
            if issue.file_path and "non-eu region" in issue.description.lower():
                # Replace non-EU regions with EU equivalents
                file_path = Path(issue.file_path)
                if file_path.exists():
                    content = file_path.read_text()
                    
                    # Replace common non-EU regions
                    replacements = {
                        "us-east-1": "eu-west-1",
                        "us-west-2": "eu-central-1",
                        "ap-southeast-1": "eu-west-1",
                        "ap-northeast-1": "eu-central-1"
                    }
                    
                    for old_region, new_region in replacements.items():
                        if old_region in content:
                            content = content.replace(old_region, new_region)
                            file_path.write_text(content)
                            return f"Replaced {old_region} with {new_region} in {file_path}"
        
        return None
    
    def get_compliance_history(self, limit: int = 10) -> List[ComplianceReport]:
        """Get recent compliance reports."""
        return sorted(
            self.compliance_history, 
            key=lambda r: r.timestamp, 
            reverse=True
        )[:limit]
    
    def get_compliance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get compliance trends over time."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_reports = [
            r for r in self.compliance_history 
            if r.timestamp >= cutoff_date
        ]
        
        if not recent_reports:
            return {"message": "No recent compliance data available"}
        
        # Calculate trends
        status_trend = []
        issue_count_trend = []
        
        for report in sorted(recent_reports, key=lambda r: r.timestamp):
            status_trend.append({
                "date": report.timestamp.isoformat(),
                "status": report.overall_status.value,
                "compliant_categories": report.summary["compliant_categories"]
            })
            
            issue_count_trend.append({
                "date": report.timestamp.isoformat(),
                "total_issues": report.summary["total_issues"],
                "critical_issues": report.summary["severity_breakdown"]["critical"]
            })
        
        return {
            "period_days": days,
            "reports_analyzed": len(recent_reports),
            "status_trend": status_trend,
            "issue_count_trend": issue_count_trend,
            "latest_status": recent_reports[-1].overall_status.value,
            "improvement_trend": self._calculate_improvement_trend(recent_reports)
        }
    
    def _calculate_improvement_trend(self, reports: List[ComplianceReport]) -> str:
        """Calculate whether compliance is improving or declining."""
        if len(reports) < 2:
            return "insufficient_data"
        
        latest = reports[-1]
        previous = reports[-2]
        
        latest_issues = latest.summary["total_issues"]
        previous_issues = previous.summary["total_issues"]
        
        if latest_issues < previous_issues:
            return "improving"
        elif latest_issues > previous_issues:
            return "declining"
        else:
            return "stable"
    
    async def generate_compliance_dashboard(self) -> Dict[str, Any]:
        """Generate compliance dashboard data."""
        if not self.compliance_history:
            return {"message": "No compliance data available"}
        
        latest_report = self.compliance_history[-1]
        trends = self.get_compliance_trends(30)
        
        return {
            "current_status": {
                "overall": latest_report.overall_status.value,
                "categories": {k.value: v.value for k, v in latest_report.categories.items()},
                "last_check": latest_report.timestamp.isoformat(),
                "total_issues": len(latest_report.issues)
            },
            "issue_breakdown": latest_report.summary["severity_breakdown"],
            "category_breakdown": latest_report.summary["category_breakdown"],
            "trends": trends,
            "recommendations": latest_report.recommendations[:5],  # Top 5
            "auto_fix_available": latest_report.summary["auto_fixable_issues"] > 0,
            "compliance_score": self._calculate_compliance_score(latest_report)
        }
    
    def _calculate_compliance_score(self, report: ComplianceReport) -> float:
        """Calculate a compliance score from 0-100."""
        if not report.categories:
            return 0.0
        
        # Base score from compliant categories
        compliant_categories = sum(
            1 for status in report.categories.values() 
            if status == ComplianceStatus.COMPLIANT
        )
        base_score = (compliant_categories / len(report.categories)) * 100
        
        # Penalty for issues
        critical_penalty = report.summary["severity_breakdown"]["critical"] * 10
        high_penalty = report.summary["severity_breakdown"]["high"] * 5
        medium_penalty = report.summary["severity_breakdown"]["medium"] * 2
        low_penalty = report.summary["severity_breakdown"]["low"] * 1
        
        total_penalty = critical_penalty + high_penalty + medium_penalty + low_penalty
        
        # Calculate final score
        final_score = max(0, base_score - total_penalty)
        return round(final_score, 1)


# Global compliance system instance
_compliance_system: Optional[ComplianceValidationSystem] = None


def get_compliance_system() -> ComplianceValidationSystem:
    """Get the global compliance system instance."""
    global _compliance_system
    if _compliance_system is None:
        _compliance_system = ComplianceValidationSystem()
    return _compliance_system


def set_compliance_system(system: ComplianceValidationSystem) -> None:
    """Set the global compliance system instance."""
    global _compliance_system
    _compliance_system = system


async def run_compliance_check(
    project_path: str,
    categories: Optional[List[str]] = None
) -> ComplianceReport:
    """
    Convenience function to run compliance check.
    
    Args:
        project_path: Path to project directory
        categories: List of category names to check
        
    Returns:
        Compliance report
    """
    system = get_compliance_system()
    
    # Convert category names to enums
    category_enums = None
    if categories:
        category_enums = [
            ComplianceCategory(cat) for cat in categories 
            if cat in [c.value for c in ComplianceCategory]
        ]
    
    return await system.run_full_compliance_check(project_path, category_enums)
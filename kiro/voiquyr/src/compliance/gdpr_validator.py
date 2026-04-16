"""
GDPR Compliance Validator

Validates GDPR compliance for the EUVoice AI Platform including
data protection, privacy rights, and consent management.
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GDPRPrinciple(str, Enum):
    """GDPR principles enumeration."""
    LAWFULNESS = "lawfulness"
    FAIRNESS = "fairness"
    TRANSPARENCY = "transparency"
    PURPOSE_LIMITATION = "purpose_limitation"
    DATA_MINIMIZATION = "data_minimization"
    ACCURACY = "accuracy"
    STORAGE_LIMITATION = "storage_limitation"
    INTEGRITY_CONFIDENTIALITY = "integrity_confidentiality"
    ACCOUNTABILITY = "accountability"


@dataclass
class GDPRValidationResult:
    """GDPR validation result."""
    status: str  # "compliant", "non_compliant", "warning"
    issues: List[Any]  # ComplianceIssue objects
    principles_checked: List[GDPRPrinciple]
    data_processing_activities: List[Dict[str, Any]]
    recommendations: List[str]


class GDPRValidator:
    """
    GDPR compliance validator for the EUVoice AI Platform.
    
    Validates compliance with GDPR requirements including:
    - Data protection principles
    - Individual rights
    - Data processing lawfulness
    - Privacy by design
    - Data residency requirements
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize GDPR validator."""
        self.config = config
        self.personal_data_patterns = [
            r'\b(email|phone|address|name|ip_address|user_id)\b',
            r'\b(first_name|last_name|full_name|surname)\b',
            r'\b(date_of_birth|dob|birthday)\b',
            r'\b(ssn|social_security|passport|id_number)\b',
            r'\b(credit_card|payment|billing)\b',
            r'\b(location|gps|coordinates|geolocation)\b',
            r'\b(biometric|fingerprint|voice_print|facial)\b'
        ]
        
        self.sensitive_data_patterns = [
            r'\b(health|medical|diagnosis|treatment)\b',
            r'\b(race|ethnicity|religion|political)\b',
            r'\b(sexual|orientation|gender|identity)\b',
            r'\b(criminal|conviction|offense)\b',
            r'\b(genetic|biometric|physiological)\b'
        ]
        
        # EU member states for data residency validation
        self.eu_countries = {
            'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
            'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
            'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
        }
        
        logger.info("GDPR Validator initialized")
    
    async def validate_project(self, project_path: str) -> GDPRValidationResult:
        """
        Validate GDPR compliance for the entire project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            GDPR validation result
        """
        logger.info(f"Starting GDPR validation for project: {project_path}")
        
        issues = []
        data_processing_activities = []
        principles_checked = []
        
        # Check data protection principles
        issues.extend(await self._check_data_minimization(project_path))
        principles_checked.append(GDPRPrinciple.DATA_MINIMIZATION)
        
        issues.extend(await self._check_purpose_limitation(project_path))
        principles_checked.append(GDPRPrinciple.PURPOSE_LIMITATION)
        
        issues.extend(await self._check_storage_limitation(project_path))
        principles_checked.append(GDPRPrinciple.STORAGE_LIMITATION)
        
        issues.extend(await self._check_transparency(project_path))
        principles_checked.append(GDPRPrinciple.TRANSPARENCY)
        
        # Check individual rights implementation
        issues.extend(await self._check_individual_rights(project_path))
        
        # Check data processing lawfulness
        issues.extend(await self._check_lawful_basis(project_path))
        principles_checked.append(GDPRPrinciple.LAWFULNESS)
        
        # Check privacy by design
        issues.extend(await self._check_privacy_by_design(project_path))
        
        # Check data residency
        issues.extend(await self._check_data_residency(project_path))
        
        # Check consent management
        issues.extend(await self._check_consent_management(project_path))
        
        # Check data security measures
        issues.extend(await self._check_data_security(project_path))
        principles_checked.append(GDPRPrinciple.INTEGRITY_CONFIDENTIALITY)
        
        # Analyze data processing activities
        data_processing_activities = await self._analyze_data_processing(project_path)
        
        # Determine overall status
        critical_issues = [i for i in issues if i.severity == "critical"]
        high_issues = [i for i in issues if i.severity == "high"]
        
        if critical_issues:
            status = "non_compliant"
        elif high_issues:
            status = "warning"
        else:
            status = "compliant"
        
        # Generate recommendations
        recommendations = self._generate_gdpr_recommendations(issues)
        
        result = GDPRValidationResult(
            status=status,
            issues=issues,
            principles_checked=principles_checked,
            data_processing_activities=data_processing_activities,
            recommendations=recommendations
        )
        
        logger.info(f"GDPR validation completed. Status: {status}, Issues: {len(issues)}")
        return result
    
    async def _check_data_minimization(self, project_path: str) -> List[Any]:
        """Check data minimization principle compliance."""
        issues = []
        
        # Check database models for excessive data collection
        model_files = list(Path(project_path).rglob("*model*.py"))
        model_files.extend(list(Path(project_path).rglob("*schema*.py")))
        
        for model_file in model_files:
            try:
                content = model_file.read_text()
                
                # Check for excessive personal data fields
                personal_data_count = 0
                for pattern in self.personal_data_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    personal_data_count += len(matches)
                
                if personal_data_count > 10:  # Threshold for excessive data
                    issues.append(self._create_issue(
                        "gdpr_data_minimization_excessive",
                        "high",
                        "Excessive Personal Data Collection",
                        f"Model contains {personal_data_count} personal data fields. "
                        "Consider data minimization.",
                        "data_models",
                        str(model_file),
                        "Review and remove unnecessary personal data fields"
                    ))
                
                # Check for sensitive data without proper handling
                for pattern in self.sensitive_data_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        if "encrypt" not in content.lower() and "hash" not in content.lower():
                            issues.append(self._create_issue(
                                "gdpr_sensitive_data_unprotected",
                                "critical",
                                "Unprotected Sensitive Data",
                                "Sensitive personal data found without encryption/hashing",
                                "data_models",
                                str(model_file),
                                "Implement encryption or hashing for sensitive data"
                            ))
            
            except Exception as e:
                logger.warning(f"Could not analyze model file {model_file}: {e}")
        
        return issues
    
    async def _check_purpose_limitation(self, project_path: str) -> List[Any]:
        """Check purpose limitation principle compliance."""
        issues = []
        
        # Check for privacy policy or data usage documentation
        policy_files = [
            "PRIVACY_POLICY.md", "privacy-policy.md", "DATA_USAGE.md",
            "docs/privacy.md", "docs/data-usage.md"
        ]
        
        policy_found = False
        for policy_file in policy_files:
            if (Path(project_path) / policy_file).exists():
                policy_found = True
                break
        
        if not policy_found:
            issues.append(self._create_issue(
                "gdpr_purpose_limitation_no_policy",
                "high",
                "Missing Privacy Policy",
                "No privacy policy found documenting data processing purposes",
                "documentation",
                None,
                "Create a comprehensive privacy policy documenting all data processing purposes"
            ))
        
        # Check API endpoints for purpose documentation
        api_files = list(Path(project_path).rglob("*router*.py"))
        api_files.extend(list(Path(project_path).rglob("*api*.py")))
        
        for api_file in api_files:
            try:
                content = api_file.read_text()
                
                # Check for data collection endpoints without purpose documentation
                if re.search(r'@app\.(post|put)', content) or re.search(r'@router\.(post|put)', content):
                    if not re.search(r'(purpose|reason|why)', content, re.IGNORECASE):
                        issues.append(self._create_issue(
                            "gdpr_purpose_undocumented",
                            "medium",
                            "Undocumented Data Processing Purpose",
                            "API endpoint processes data without documented purpose",
                            "api",
                            str(api_file),
                            "Document the purpose for each data processing operation"
                        ))
            
            except Exception as e:
                logger.warning(f"Could not analyze API file {api_file}: {e}")
        
        return issues
    
    async def _check_storage_limitation(self, project_path: str) -> List[Any]:
        """Check storage limitation principle compliance."""
        issues = []
        
        # Check for data retention policies
        config_files = [
            "src/config.py", "config.yaml", "settings.py",
            "src/api/config.py"
        ]
        
        retention_policy_found = False
        for config_file in config_files:
            file_path = Path(project_path) / config_file
            if file_path.exists():
                content = file_path.read_text()
                if re.search(r'(retention|expire|ttl|delete_after)', content, re.IGNORECASE):
                    retention_policy_found = True
                    break
        
        if not retention_policy_found:
            issues.append(self._create_issue(
                "gdpr_storage_limitation_no_retention",
                "high",
                "Missing Data Retention Policy",
                "No data retention policy or automatic deletion found",
                "configuration",
                None,
                "Implement data retention policies with automatic deletion"
            ))
        
        # Check database configurations for backup retention
        db_files = list(Path(project_path).rglob("*database*.py"))
        db_files.extend(list(Path(project_path).rglob("docker-compose*.yml")))
        
        for db_file in db_files:
            try:
                content = db_file.read_text()
                
                # Check for indefinite data storage
                if "backup" in content.lower() and "retention" not in content.lower():
                    issues.append(self._create_issue(
                        "gdpr_backup_retention_missing",
                        "medium",
                        "Missing Backup Retention Policy",
                        "Database backups without retention policy found",
                        "database",
                        str(db_file),
                        "Implement backup retention policies"
                    ))
            
            except Exception as e:
                logger.warning(f"Could not analyze database file {db_file}: {e}")
        
        return issues
    
    async def _check_transparency(self, project_path: str) -> List[Any]:
        """Check transparency principle compliance."""
        issues = []
        
        # Check for user-facing privacy information
        frontend_path = Path(project_path) / "frontend"
        if frontend_path.exists():
            privacy_components = list(frontend_path.rglob("*privacy*.tsx"))
            privacy_components.extend(list(frontend_path.rglob("*consent*.tsx")))
            
            if not privacy_components:
                issues.append(self._create_issue(
                    "gdpr_transparency_no_ui",
                    "high",
                    "Missing Privacy UI Components",
                    "No privacy or consent UI components found in frontend",
                    "frontend",
                    None,
                    "Implement privacy notice and consent UI components"
                ))
        
        # Check API documentation for privacy information
        docs_path = Path(project_path) / "docs"
        api_docs_found = False
        
        if docs_path.exists():
            for doc_file in docs_path.rglob("*.md"):
                content = doc_file.read_text()
                if "privacy" in content.lower() or "data processing" in content.lower():
                    api_docs_found = True
                    break
        
        if not api_docs_found:
            issues.append(self._create_issue(
                "gdpr_transparency_no_docs",
                "medium",
                "Missing Privacy Documentation",
                "No privacy or data processing documentation found",
                "documentation",
                None,
                "Create comprehensive privacy and data processing documentation"
            ))
        
        return issues
    
    async def _check_individual_rights(self, project_path: str) -> List[Any]:
        """Check implementation of individual rights."""
        issues = []
        
        # Check for data subject rights implementation
        rights_endpoints = [
            "access", "rectification", "erasure", "portability", 
            "restriction", "objection", "withdraw_consent"
        ]
        
        api_files = list(Path(project_path).rglob("*api*.py"))
        api_files.extend(list(Path(project_path).rglob("*router*.py")))
        
        implemented_rights = set()
        
        for api_file in api_files:
            try:
                content = api_file.read_text()
                
                for right in rights_endpoints:
                    if right in content.lower():
                        implemented_rights.add(right)
            
            except Exception as e:
                logger.warning(f"Could not analyze API file {api_file}: {e}")
        
        missing_rights = set(rights_endpoints) - implemented_rights
        
        if missing_rights:
            issues.append(self._create_issue(
                "gdpr_individual_rights_missing",
                "critical",
                "Missing Individual Rights Implementation",
                f"Missing implementation for rights: {', '.join(missing_rights)}",
                "api",
                None,
                "Implement all GDPR individual rights (access, rectification, erasure, etc.)"
            ))
        
        return issues
    
    async def _check_lawful_basis(self, project_path: str) -> List[Any]:
        """Check lawful basis for data processing."""
        issues = []
        
        # Check for lawful basis documentation
        legal_files = [
            "LEGAL_BASIS.md", "legal-basis.md", "docs/legal.md",
            "TERMS_OF_SERVICE.md", "terms.md"
        ]
        
        legal_basis_found = False
        for legal_file in legal_files:
            if (Path(project_path) / legal_file).exists():
                legal_basis_found = True
                break
        
        if not legal_basis_found:
            issues.append(self._create_issue(
                "gdpr_lawful_basis_undocumented",
                "critical",
                "Missing Lawful Basis Documentation",
                "No documentation of lawful basis for data processing found",
                "legal",
                None,
                "Document the lawful basis for all data processing activities"
            ))
        
        # Check consent implementation for consent-based processing
        consent_files = list(Path(project_path).rglob("*consent*.py"))
        consent_files.extend(list(Path(project_path).rglob("*consent*.tsx")))
        
        if not consent_files:
            issues.append(self._create_issue(
                "gdpr_consent_implementation_missing",
                "high",
                "Missing Consent Implementation",
                "No consent management implementation found",
                "consent",
                None,
                "Implement consent management system for consent-based processing"
            ))
        
        return issues
    
    async def _check_privacy_by_design(self, project_path: str) -> List[Any]:
        """Check privacy by design implementation."""
        issues = []
        
        # Check for data anonymization/pseudonymization
        privacy_files = list(Path(project_path).rglob("*anonymiz*.py"))
        privacy_files.extend(list(Path(project_path).rglob("*pseudonym*.py")))
        privacy_files.extend(list(Path(project_path).rglob("*privacy*.py")))
        
        if not privacy_files:
            issues.append(self._create_issue(
                "gdpr_privacy_by_design_missing",
                "high",
                "Missing Privacy by Design Implementation",
                "No data anonymization or pseudonymization implementation found",
                "privacy",
                None,
                "Implement privacy-enhancing technologies (anonymization, pseudonymization)"
            ))
        
        # Check for encryption implementation
        crypto_found = False
        for file_path in Path(project_path).rglob("*.py"):
            try:
                content = file_path.read_text()
                if re.search(r'(encrypt|decrypt|cipher|aes|rsa)', content, re.IGNORECASE):
                    crypto_found = True
                    break
            except Exception:
                continue
        
        if not crypto_found:
            issues.append(self._create_issue(
                "gdpr_encryption_missing",
                "critical",
                "Missing Encryption Implementation",
                "No encryption implementation found for personal data protection",
                "security",
                None,
                "Implement encryption for personal data at rest and in transit"
            ))
        
        return issues
    
    async def _check_data_residency(self, project_path: str) -> List[Any]:
        """Check EU data residency compliance."""
        issues = []
        
        # Check cloud provider configurations
        cloud_configs = list(Path(project_path).rglob("*cloud*.yaml"))
        cloud_configs.extend(list(Path(project_path).rglob("*aws*.yaml")))
        cloud_configs.extend(list(Path(project_path).rglob("*gcp*.yaml")))
        cloud_configs.extend(list(Path(project_path).rglob("*azure*.yaml")))
        
        for config_file in cloud_configs:
            try:
                content = config_file.read_text()
                
                # Check for non-EU regions
                non_eu_regions = [
                    "us-", "ap-", "ca-", "sa-", "af-", "me-", "cn-"
                ]
                
                for region in non_eu_regions:
                    if region in content.lower():
                        issues.append(self._create_issue(
                            "gdpr_data_residency_violation",
                            "critical",
                            "Non-EU Data Residency",
                            f"Configuration references non-EU region: {region}",
                            "infrastructure",
                            str(config_file),
                            "Ensure all data processing occurs within EU/EEA"
                        ))
            
            except Exception as e:
                logger.warning(f"Could not analyze cloud config {config_file}: {e}")
        
        return issues
    
    async def _check_consent_management(self, project_path: str) -> List[Any]:
        """Check consent management implementation."""
        issues = []
        
        # Check frontend consent implementation
        frontend_path = Path(project_path) / "frontend"
        if frontend_path.exists():
            consent_found = False
            
            for tsx_file in frontend_path.rglob("*.tsx"):
                try:
                    content = tsx_file.read_text()
                    if re.search(r'(consent|cookie|opt-in|opt-out)', content, re.IGNORECASE):
                        consent_found = True
                        break
                except Exception:
                    continue
            
            if not consent_found:
                issues.append(self._create_issue(
                    "gdpr_consent_ui_missing",
                    "high",
                    "Missing Consent UI",
                    "No consent management UI found in frontend",
                    "frontend",
                    None,
                    "Implement user consent interface with clear opt-in/opt-out options"
                ))
        
        # Check backend consent storage
        consent_models = False
        for model_file in Path(project_path).rglob("*model*.py"):
            try:
                content = model_file.read_text()
                if "consent" in content.lower():
                    consent_models = True
                    break
            except Exception:
                continue
        
        if not consent_models:
            issues.append(self._create_issue(
                "gdpr_consent_storage_missing",
                "high",
                "Missing Consent Storage",
                "No consent storage model found in backend",
                "backend",
                None,
                "Implement consent storage and management in database models"
            ))
        
        return issues
    
    async def _check_data_security(self, project_path: str) -> List[Any]:
        """Check data security measures."""
        issues = []
        
        # Check for HTTPS enforcement
        security_configs = list(Path(project_path).rglob("*security*.yaml"))
        security_configs.extend(list(Path(project_path).rglob("*tls*.yaml")))
        security_configs.extend(list(Path(project_path).rglob("*ssl*.yaml")))
        
        https_enforced = False
        for config_file in security_configs:
            try:
                content = config_file.read_text()
                if "tls" in content.lower() or "https" in content.lower():
                    https_enforced = True
                    break
            except Exception:
                continue
        
        if not https_enforced:
            issues.append(self._create_issue(
                "gdpr_https_not_enforced",
                "high",
                "HTTPS Not Enforced",
                "No HTTPS/TLS enforcement configuration found",
                "security",
                None,
                "Enforce HTTPS/TLS for all data transmission"
            ))
        
        # Check for access controls
        auth_files = list(Path(project_path).rglob("*auth*.py"))
        auth_files.extend(list(Path(project_path).rglob("*rbac*.py")))
        
        if not auth_files:
            issues.append(self._create_issue(
                "gdpr_access_control_missing",
                "critical",
                "Missing Access Controls",
                "No authentication or authorization implementation found",
                "security",
                None,
                "Implement proper access controls and authentication"
            ))
        
        return issues
    
    async def _analyze_data_processing(self, project_path: str) -> List[Dict[str, Any]]:
        """Analyze data processing activities."""
        activities = []
        
        # Analyze API endpoints for data processing
        api_files = list(Path(project_path).rglob("*router*.py"))
        api_files.extend(list(Path(project_path).rglob("*api*.py")))
        
        for api_file in api_files:
            try:
                content = api_file.read_text()
                
                # Find POST/PUT endpoints (data processing)
                endpoints = re.findall(r'@\w+\.(post|put|patch)\(["\']([^"\']+)', content)
                
                for method, endpoint in endpoints:
                    # Determine data categories processed
                    data_categories = []
                    for pattern in self.personal_data_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            data_categories.append(pattern.strip(r'\b()'))
                    
                    if data_categories:
                        activities.append({
                            "activity": f"{method.upper()} {endpoint}",
                            "file": str(api_file),
                            "data_categories": data_categories,
                            "purpose": "Voice processing and AI assistance",  # Default
                            "lawful_basis": "Consent or Legitimate Interest",  # Default
                            "retention_period": "Unknown",
                            "third_party_sharing": "Unknown"
                        })
            
            except Exception as e:
                logger.warning(f"Could not analyze API file {api_file}: {e}")
        
        return activities
    
    def _generate_gdpr_recommendations(self, issues: List[Any]) -> List[str]:
        """Generate GDPR-specific recommendations."""
        recommendations = []
        
        # Critical issues first
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(
                "Address critical GDPR violations immediately to avoid regulatory penalties"
            )
        
        # Specific recommendations based on issue types
        issue_types = {i.id.split('_')[1] for i in issues if '_' in i.id}
        
        if "data" in issue_types or "minimization" in issue_types:
            recommendations.append(
                "Implement data minimization: collect only necessary personal data"
            )
        
        if "consent" in issue_types:
            recommendations.append(
                "Implement comprehensive consent management with clear opt-in/opt-out"
            )
        
        if "rights" in issue_types:
            recommendations.append(
                "Implement all individual rights: access, rectification, erasure, portability"
            )
        
        if "residency" in issue_types:
            recommendations.append(
                "Ensure all data processing occurs within EU/EEA boundaries"
            )
        
        if "encryption" in issue_types or "security" in issue_types:
            recommendations.append(
                "Implement end-to-end encryption and proper access controls"
            )
        
        return recommendations
    
    def _create_issue(
        self, 
        issue_id: str, 
        severity: str, 
        title: str, 
        description: str, 
        component: str, 
        file_path: Optional[str] = None, 
        recommendation: Optional[str] = None
    ) -> Any:
        """Create a compliance issue object."""
        # Import here to avoid circular imports
        from .compliance_system import ComplianceIssue, ComplianceCategory
        
        return ComplianceIssue(
            id=issue_id,
            category=ComplianceCategory.GDPR,
            severity=severity,
            title=title,
            description=description,
            component=component,
            file_path=file_path,
            recommendation=recommendation,
            auto_fixable=False  # GDPR issues typically require manual review
        )
    
    async def apply_auto_fixes(self, issues: List[Any]) -> List[str]:
        """Apply automatic fixes for GDPR issues."""
        # Most GDPR issues require manual intervention
        # This method is placeholder for future auto-fix capabilities
        fixes_applied = []
        
        for issue in issues:
            if issue.auto_fixable:
                # Implement specific auto-fixes here
                pass
        
        return fixes_applied
    
    async def apply_single_fix(self, issue: Any) -> Optional[str]:
        """Apply a single auto-fix for a GDPR issue."""
        # Placeholder for individual issue fixes
        return None
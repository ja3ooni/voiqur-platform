"""
License Compliance Validator

Validates open-source license compliance for the EUVoice AI Platform
ensuring all dependencies use compatible licenses.
"""

import re
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LicenseCompatibility(str, Enum):
    """License compatibility levels."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REQUIRES_REVIEW = "requires_review"
    UNKNOWN = "unknown"


class LicenseCategory(str, Enum):
    """License categories."""
    PERMISSIVE = "permissive"
    COPYLEFT_WEAK = "copyleft_weak"
    COPYLEFT_STRONG = "copyleft_strong"
    PROPRIETARY = "proprietary"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"


@dataclass
class LicenseDependency:
    """Represents a dependency with license information."""
    name: str
    version: str
    license: str
    license_category: LicenseCategory
    compatibility: LicenseCompatibility
    file_path: Optional[str] = None
    license_text_path: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LicenseValidationResult:
    """License validation result."""
    status: str  # "compliant", "non_compliant", "warning"
    issues: List[Any]  # ComplianceIssue objects
    dependencies: List[LicenseDependency]
    license_summary: Dict[str, int]
    compatibility_summary: Dict[str, int]
    recommendations: List[str]


class LicenseValidator:
    """
    License compliance validator for the EUVoice AI Platform.
    
    Validates compliance with open-source licensing requirements including:
    - Dependency license compatibility
    - License attribution requirements
    - Copyleft compliance
    - License file presence and validity
    - Third-party license aggregation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize license validator."""
        self.config = config
        
        # Compatible licenses for Apache 2.0 project
        self.compatible_licenses = {
            "Apache-2.0": LicenseCategory.PERMISSIVE,
            "MIT": LicenseCategory.PERMISSIVE,
            "BSD-2-Clause": LicenseCategory.PERMISSIVE,
            "BSD-3-Clause": LicenseCategory.PERMISSIVE,
            "ISC": LicenseCategory.PERMISSIVE,
            "CC0-1.0": LicenseCategory.PUBLIC_DOMAIN,
            "Unlicense": LicenseCategory.PUBLIC_DOMAIN,
            "WTFPL": LicenseCategory.PUBLIC_DOMAIN,
            "CC-BY-4.0": LicenseCategory.PERMISSIVE,
            "CC-BY-3.0": LicenseCategory.PERMISSIVE,
            "Python-2.0": LicenseCategory.PERMISSIVE,
            "Zlib": LicenseCategory.PERMISSIVE,
            "libpng": LicenseCategory.PERMISSIVE
        }
        
        # Weak copyleft licenses (compatible with conditions)
        self.weak_copyleft_licenses = {
            "LGPL-2.1": LicenseCategory.COPYLEFT_WEAK,
            "LGPL-3.0": LicenseCategory.COPYLEFT_WEAK,
            "MPL-2.0": LicenseCategory.COPYLEFT_WEAK,
            "EPL-1.0": LicenseCategory.COPYLEFT_WEAK,
            "EPL-2.0": LicenseCategory.COPYLEFT_WEAK,
            "CDDL-1.0": LicenseCategory.COPYLEFT_WEAK,
            "CDDL-1.1": LicenseCategory.COPYLEFT_WEAK
        }
        
        # Strong copyleft licenses (generally incompatible)
        self.strong_copyleft_licenses = {
            "GPL-2.0": LicenseCategory.COPYLEFT_STRONG,
            "GPL-3.0": LicenseCategory.COPYLEFT_STRONG,
            "AGPL-3.0": LicenseCategory.COPYLEFT_STRONG,
            "EUPL-1.1": LicenseCategory.COPYLEFT_STRONG,
            "EUPL-1.2": LicenseCategory.COPYLEFT_STRONG,
            "OSL-3.0": LicenseCategory.COPYLEFT_STRONG
        }
        
        # Proprietary/commercial licenses (incompatible)
        self.proprietary_licenses = {
            "Commercial": LicenseCategory.PROPRIETARY,
            "Proprietary": LicenseCategory.PROPRIETARY,
            "All Rights Reserved": LicenseCategory.PROPRIETARY,
            "Custom": LicenseCategory.PROPRIETARY
        }
        
        # All license mappings
        self.all_licenses = {
            **self.compatible_licenses,
            **self.weak_copyleft_licenses,
            **self.strong_copyleft_licenses,
            **self.proprietary_licenses
        }
        
        logger.info("License Validator initialized")
    
    async def validate_project(self, project_path: str) -> LicenseValidationResult:
        """
        Validate license compliance for the entire project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            License validation result
        """
        logger.info(f"Starting license validation for project: {project_path}")
        
        issues = []
        dependencies = []
        
        # Check project license
        issues.extend(await self._check_project_license(project_path))
        
        # Analyze Python dependencies
        python_deps = await self._analyze_python_dependencies(project_path)
        dependencies.extend(python_deps)
        
        # Analyze JavaScript/Node.js dependencies
        js_deps = await self._analyze_javascript_dependencies(project_path)
        dependencies.extend(js_deps)
        
        # Check for license files
        issues.extend(await self._check_license_files(project_path))
        
        # Check for third-party attributions
        issues.extend(await self._check_third_party_attributions(project_path))
        
        # Validate dependency compatibility
        compatibility_issues = await self._validate_dependency_compatibility(dependencies)
        issues.extend(compatibility_issues)
        
        # Check for missing license information
        missing_license_issues = await self._check_missing_licenses(dependencies)
        issues.extend(missing_license_issues)
        
        # Generate summaries
        license_summary = self._generate_license_summary(dependencies)
        compatibility_summary = self._generate_compatibility_summary(dependencies)
        
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
        recommendations = self._generate_license_recommendations(issues, dependencies)
        
        result = LicenseValidationResult(
            status=status,
            issues=issues,
            dependencies=dependencies,
            license_summary=license_summary,
            compatibility_summary=compatibility_summary,
            recommendations=recommendations
        )
        
        logger.info(f"License validation completed. Status: {status}, Dependencies: {len(dependencies)}")
        return result
    
    async def _check_project_license(self, project_path: str) -> List[Any]:
        """Check project license file and validity."""
        issues = []
        
        # Check for LICENSE file
        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]
        license_file_found = None
        
        for license_file in license_files:
            file_path = Path(project_path) / license_file
            if file_path.exists():
                license_file_found = file_path
                break
        
        if not license_file_found:
            issues.append(self._create_issue(
                "license_project_file_missing",
                "critical",
                "Missing Project License File",
                "No LICENSE file found in project root",
                "licensing",
                None,
                "Add LICENSE file with Apache 2.0 license text"
            ))
        else:
            # Validate license content
            try:
                license_content = license_file_found.read_text()
                
                # Check for Apache 2.0 license
                if "apache" not in license_content.lower() or "2.0" not in license_content:
                    issues.append(self._create_issue(
                        "license_project_not_apache",
                        "high",
                        "Project License Not Apache 2.0",
                        "Project license should be Apache 2.0 for open-source compatibility",
                        "licensing",
                        str(license_file_found),
                        "Update project license to Apache 2.0"
                    ))
                
                # Check for copyright notice
                if "copyright" not in license_content.lower():
                    issues.append(self._create_issue(
                        "license_copyright_missing",
                        "medium",
                        "Missing Copyright Notice",
                        "License file should include copyright notice",
                        "licensing",
                        str(license_file_found),
                        "Add copyright notice to license file"
                    ))
            
            except Exception as e:
                logger.warning(f"Could not read license file {license_file_found}: {e}")
        
        return issues
    
    async def _analyze_python_dependencies(self, project_path: str) -> List[LicenseDependency]:
        """Analyze Python dependencies and their licenses."""
        dependencies = []
        
        # Check requirements files
        req_files = [
            "requirements.txt", "requirements-dev.txt", "requirements-prod.txt",
            "pyproject.toml", "setup.py", "Pipfile"
        ]
        
        for req_file in req_files:
            file_path = Path(project_path) / req_file
            if file_path.exists():
                deps = await self._parse_python_requirements(file_path)
                dependencies.extend(deps)
        
        # Try to get license information using pip-licenses if available
        try:
            result = subprocess.run(
                ["pip-licenses", "--format=json"],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=30
            )
            
            if result.returncode == 0:
                license_data = json.loads(result.stdout)
                dependencies = self._enrich_python_licenses(dependencies, license_data)
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not run pip-licenses to get license information")
        except json.JSONDecodeError:
            logger.warning("Could not parse pip-licenses output")
        
        return dependencies
    
    async def _parse_python_requirements(self, req_file: Path) -> List[LicenseDependency]:
        """Parse Python requirements file."""
        dependencies = []
        
        try:
            if req_file.name == "pyproject.toml":
                # Parse TOML file
                import tomli
                content = tomli.loads(req_file.read_text())
                
                # Extract dependencies from various sections
                deps = []
                if "project" in content and "dependencies" in content["project"]:
                    deps.extend(content["project"]["dependencies"])
                if "tool" in content and "poetry" in content["tool"] and "dependencies" in content["tool"]["poetry"]:
                    deps.extend(content["tool"]["poetry"]["dependencies"].keys())
                
                for dep in deps:
                    name, version = self._parse_dependency_string(dep)
                    if name:
                        dependencies.append(LicenseDependency(
                            name=name,
                            version=version,
                            license="Unknown",
                            license_category=LicenseCategory.UNKNOWN,
                            compatibility=LicenseCompatibility.UNKNOWN,
                            file_path=str(req_file)
                        ))
            
            else:
                # Parse requirements.txt format
                content = req_file.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        name, version = self._parse_dependency_string(line)
                        if name:
                            dependencies.append(LicenseDependency(
                                name=name,
                                version=version,
                                license="Unknown",
                                license_category=LicenseCategory.UNKNOWN,
                                compatibility=LicenseCompatibility.UNKNOWN,
                                file_path=str(req_file)
                            ))
        
        except Exception as e:
            logger.warning(f"Could not parse requirements file {req_file}: {e}")
        
        return dependencies
    
    async def _analyze_javascript_dependencies(self, project_path: str) -> List[LicenseDependency]:
        """Analyze JavaScript/Node.js dependencies and their licenses."""
        dependencies = []
        
        # Check package.json
        package_json = Path(project_path) / "package.json"
        if package_json.exists():
            try:
                package_data = json.loads(package_json.read_text())
                
                # Extract dependencies
                all_deps = {}
                if "dependencies" in package_data:
                    all_deps.update(package_data["dependencies"])
                if "devDependencies" in package_data:
                    all_deps.update(package_data["devDependencies"])
                
                for name, version in all_deps.items():
                    dependencies.append(LicenseDependency(
                        name=name,
                        version=version,
                        license="Unknown",
                        license_category=LicenseCategory.UNKNOWN,
                        compatibility=LicenseCompatibility.UNKNOWN,
                        file_path=str(package_json)
                    ))
            
            except Exception as e:
                logger.warning(f"Could not parse package.json: {e}")
        
        # Try to get license information using license-checker if available
        try:
            result = subprocess.run(
                ["npx", "license-checker", "--json"],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=60
            )
            
            if result.returncode == 0:
                license_data = json.loads(result.stdout)
                dependencies = self._enrich_javascript_licenses(dependencies, license_data)
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not run license-checker to get JavaScript license information")
        except json.JSONDecodeError:
            logger.warning("Could not parse license-checker output")
        
        return dependencies
    
    def _parse_dependency_string(self, dep_string: str) -> Tuple[str, str]:
        """Parse dependency string to extract name and version."""
        # Remove common prefixes and suffixes
        dep_string = dep_string.strip()
        
        # Handle various formats: name==version, name>=version, name~=version, etc.
        match = re.match(r'^([a-zA-Z0-9_-]+)([><=!~]+)(.+)$', dep_string)
        if match:
            return match.group(1), match.group(3)
        
        # Handle simple name without version
        match = re.match(r'^([a-zA-Z0-9_-]+)$', dep_string)
        if match:
            return match.group(1), "latest"
        
        return "", ""
    
    def _enrich_python_licenses(
        self, 
        dependencies: List[LicenseDependency], 
        license_data: List[Dict[str, Any]]
    ) -> List[LicenseDependency]:
        """Enrich Python dependencies with license information."""
        license_map = {item["Name"]: item for item in license_data}
        
        for dep in dependencies:
            if dep.name in license_map:
                license_info = license_map[dep.name]
                dep.license = license_info.get("License", "Unknown")
                dep.version = license_info.get("Version", dep.version)
                dep.homepage = license_info.get("URL", None)
                
                # Classify license
                dep.license_category = self._classify_license(dep.license)
                dep.compatibility = self._assess_compatibility(dep.license, dep.license_category)
        
        return dependencies
    
    def _enrich_javascript_licenses(
        self, 
        dependencies: List[LicenseDependency], 
        license_data: Dict[str, Any]
    ) -> List[LicenseDependency]:
        """Enrich JavaScript dependencies with license information."""
        for dep in dependencies:
            # license-checker uses "name@version" as key
            key_patterns = [
                f"{dep.name}@{dep.version}",
                f"{dep.name}@latest",
                dep.name
            ]
            
            for key in key_patterns:
                if key in license_data:
                    license_info = license_data[key]
                    dep.license = license_info.get("licenses", "Unknown")
                    dep.homepage = license_info.get("repository", None)
                    dep.license_text_path = license_info.get("licenseFile", None)
                    
                    # Classify license
                    dep.license_category = self._classify_license(dep.license)
                    dep.compatibility = self._assess_compatibility(dep.license, dep.license_category)
                    break
        
        return dependencies
    
    def _classify_license(self, license_name: str) -> LicenseCategory:
        """Classify license into category."""
        if not license_name or license_name.lower() in ["unknown", "none", ""]:
            return LicenseCategory.UNKNOWN
        
        # Normalize license name
        license_normalized = license_name.strip().replace(" ", "-")
        
        # Check exact matches first
        if license_normalized in self.all_licenses:
            return self.all_licenses[license_normalized]
        
        # Check partial matches
        license_lower = license_name.lower()
        
        if any(term in license_lower for term in ["apache", "mit", "bsd", "isc"]):
            return LicenseCategory.PERMISSIVE
        
        if any(term in license_lower for term in ["lgpl", "mpl", "epl", "cddl"]):
            return LicenseCategory.COPYLEFT_WEAK
        
        if any(term in license_lower for term in ["gpl", "agpl", "eupl", "osl"]):
            return LicenseCategory.COPYLEFT_STRONG
        
        if any(term in license_lower for term in ["cc0", "unlicense", "public domain"]):
            return LicenseCategory.PUBLIC_DOMAIN
        
        if any(term in license_lower for term in ["commercial", "proprietary", "all rights reserved"]):
            return LicenseCategory.PROPRIETARY
        
        return LicenseCategory.UNKNOWN
    
    def _assess_compatibility(
        self, 
        license_name: str, 
        license_category: LicenseCategory
    ) -> LicenseCompatibility:
        """Assess license compatibility with Apache 2.0."""
        if license_category == LicenseCategory.PERMISSIVE:
            return LicenseCompatibility.COMPATIBLE
        
        if license_category == LicenseCategory.PUBLIC_DOMAIN:
            return LicenseCompatibility.COMPATIBLE
        
        if license_category == LicenseCategory.COPYLEFT_WEAK:
            return LicenseCompatibility.REQUIRES_REVIEW
        
        if license_category == LicenseCategory.COPYLEFT_STRONG:
            return LicenseCompatibility.INCOMPATIBLE
        
        if license_category == LicenseCategory.PROPRIETARY:
            return LicenseCompatibility.INCOMPATIBLE
        
        return LicenseCompatibility.UNKNOWN
    
    async def _check_license_files(self, project_path: str) -> List[Any]:
        """Check for required license files."""
        issues = []
        
        # Check for NOTICE file (required for Apache 2.0)
        notice_files = ["NOTICE", "NOTICE.txt", "NOTICE.md"]
        notice_found = False
        
        for notice_file in notice_files:
            if (Path(project_path) / notice_file).exists():
                notice_found = True
                break
        
        if not notice_found:
            issues.append(self._create_issue(
                "license_notice_file_missing",
                "medium",
                "Missing NOTICE File",
                "Apache 2.0 projects should include a NOTICE file",
                "licensing",
                None,
                "Create NOTICE file with project attribution information"
            ))
        
        return issues
    
    async def _check_third_party_attributions(self, project_path: str) -> List[Any]:
        """Check for third-party license attributions."""
        issues = []
        
        # Check for third-party licenses directory or file
        attribution_paths = [
            "THIRD_PARTY_LICENSES.md",
            "third-party-licenses.md",
            "licenses/",
            "third-party/",
            "attributions.md"
        ]
        
        attribution_found = False
        for attr_path in attribution_paths:
            if (Path(project_path) / attr_path).exists():
                attribution_found = True
                break
        
        if not attribution_found:
            issues.append(self._create_issue(
                "license_attributions_missing",
                "medium",
                "Missing Third-Party Attributions",
                "No third-party license attributions found",
                "licensing",
                None,
                "Create third-party license attributions file"
            ))
        
        return issues
    
    async def _validate_dependency_compatibility(
        self, 
        dependencies: List[LicenseDependency]
    ) -> List[Any]:
        """Validate dependency license compatibility."""
        issues = []
        
        for dep in dependencies:
            if dep.compatibility == LicenseCompatibility.INCOMPATIBLE:
                issues.append(self._create_issue(
                    f"license_incompatible_{dep.name}",
                    "critical",
                    f"Incompatible License: {dep.name}",
                    f"Dependency {dep.name} has incompatible license: {dep.license}",
                    "licensing",
                    dep.file_path,
                    f"Replace {dep.name} with compatible alternative or obtain commercial license"
                ))
            
            elif dep.compatibility == LicenseCompatibility.REQUIRES_REVIEW:
                issues.append(self._create_issue(
                    f"license_review_required_{dep.name}",
                    "high",
                    f"License Requires Review: {dep.name}",
                    f"Dependency {dep.name} license requires legal review: {dep.license}",
                    "licensing",
                    dep.file_path,
                    f"Review {dep.license} license compatibility for {dep.name}"
                ))
        
        return issues
    
    async def _check_missing_licenses(
        self, 
        dependencies: List[LicenseDependency]
    ) -> List[Any]:
        """Check for dependencies with missing license information."""
        issues = []
        
        unknown_licenses = [
            dep for dep in dependencies 
            if dep.license in ["Unknown", "UNKNOWN", "", None] or 
               dep.compatibility == LicenseCompatibility.UNKNOWN
        ]
        
        if unknown_licenses:
            dep_names = [dep.name for dep in unknown_licenses[:5]]  # Limit to first 5
            more_count = len(unknown_licenses) - 5
            
            description = f"Dependencies with unknown licenses: {', '.join(dep_names)}"
            if more_count > 0:
                description += f" and {more_count} more"
            
            issues.append(self._create_issue(
                "license_unknown_dependencies",
                "medium",
                "Dependencies with Unknown Licenses",
                description,
                "licensing",
                None,
                "Investigate and document licenses for all dependencies"
            ))
        
        return issues
    
    def _generate_license_summary(self, dependencies: List[LicenseDependency]) -> Dict[str, int]:
        """Generate license summary statistics."""
        summary = {}
        
        for dep in dependencies:
            license_key = dep.license if dep.license != "Unknown" else "Unknown"
            summary[license_key] = summary.get(license_key, 0) + 1
        
        return summary
    
    def _generate_compatibility_summary(self, dependencies: List[LicenseDependency]) -> Dict[str, int]:
        """Generate compatibility summary statistics."""
        summary = {
            "compatible": 0,
            "incompatible": 0,
            "requires_review": 0,
            "unknown": 0
        }
        
        for dep in dependencies:
            if dep.compatibility == LicenseCompatibility.COMPATIBLE:
                summary["compatible"] += 1
            elif dep.compatibility == LicenseCompatibility.INCOMPATIBLE:
                summary["incompatible"] += 1
            elif dep.compatibility == LicenseCompatibility.REQUIRES_REVIEW:
                summary["requires_review"] += 1
            else:
                summary["unknown"] += 1
        
        return summary
    
    def _generate_license_recommendations(
        self, 
        issues: List[Any], 
        dependencies: List[LicenseDependency]
    ) -> List[str]:
        """Generate license-specific recommendations."""
        recommendations = []
        
        # Critical issues first
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(
                "Address incompatible licenses immediately - replace or obtain commercial licenses"
            )
        
        # High-priority recommendations
        high_issues = [i for i in issues if i.severity == "high"]
        if high_issues:
            recommendations.append(
                "Review licenses that require legal assessment for compatibility"
            )
        
        # Specific recommendations
        incompatible_deps = [
            dep for dep in dependencies 
            if dep.compatibility == LicenseCompatibility.INCOMPATIBLE
        ]
        
        if incompatible_deps:
            recommendations.append(
                f"Replace {len(incompatible_deps)} incompatible dependencies with Apache 2.0 compatible alternatives"
            )
        
        review_deps = [
            dep for dep in dependencies 
            if dep.compatibility == LicenseCompatibility.REQUIRES_REVIEW
        ]
        
        if review_deps:
            recommendations.append(
                f"Conduct legal review for {len(review_deps)} dependencies with weak copyleft licenses"
            )
        
        unknown_deps = [
            dep for dep in dependencies 
            if dep.compatibility == LicenseCompatibility.UNKNOWN
        ]
        
        if unknown_deps:
            recommendations.append(
                f"Investigate and document licenses for {len(unknown_deps)} dependencies with unknown licenses"
            )
        
        # General recommendations
        if not any("NOTICE" in str(i.id) for i in issues):
            recommendations.append(
                "Create comprehensive third-party license attributions and NOTICE file"
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
            category=ComplianceCategory.LICENSING,
            severity=severity,
            title=title,
            description=description,
            component=component,
            file_path=file_path,
            recommendation=recommendation,
            auto_fixable=False  # License issues typically require manual review
        )
    
    async def apply_auto_fixes(self, issues: List[Any]) -> List[str]:
        """Apply automatic fixes for license issues."""
        # Most license issues require manual intervention
        fixes_applied = []
        
        for issue in issues:
            if issue.auto_fixable:
                # Implement specific auto-fixes here
                pass
        
        return fixes_applied
    
    async def apply_single_fix(self, issue: Any) -> Optional[str]:
        """Apply a single auto-fix for a license issue."""
        # Placeholder for individual issue fixes
        return None
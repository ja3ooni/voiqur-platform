"""
Security Scanner

Comprehensive security scanning and vulnerability assessment system
for the EUVoice AI Platform.
"""

import asyncio
import logging
import re
import json
import hashlib
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import ast
import os

logger = logging.getLogger(__name__)


class VulnerabilityType(str, Enum):
    """Types of security vulnerabilities."""
    HARDCODED_SECRETS = "hardcoded_secrets"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    INSECURE_CRYPTO = "insecure_crypto"
    WEAK_AUTHENTICATION = "weak_authentication"
    INSECURE_DEPENDENCIES = "insecure_dependencies"
    DATA_EXPOSURE = "data_exposure"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    INSECURE_COMMUNICATION = "insecure_communication"
    INPUT_VALIDATION = "input_validation"


class SeverityLevel(str, Enum):
    """Security vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityVulnerability:
    """Security vulnerability finding."""
    id: str
    vulnerability_type: VulnerabilityType
    severity: SeverityLevel
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID
    cvss_score: Optional[float] = None
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()


@dataclass
class SecurityScanResult:
    """Security scan result."""
    scan_id: str
    scan_type: str
    started_at: datetime
    completed_at: datetime
    vulnerabilities: List[SecurityVulnerability]
    files_scanned: int
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    scan_duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scan_id": self.scan_id,
            "scan_type": self.scan_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "vulnerabilities": [asdict(vuln) for vuln in self.vulnerabilities],
            "files_scanned": self.files_scanned,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "scan_duration_seconds": self.scan_duration_seconds
        }


class SecurityScanner:
    """
    Comprehensive security scanner for the EUVoice AI Platform.
    
    Performs:
    - Static code analysis for security vulnerabilities
    - Dependency vulnerability scanning
    - Configuration security assessment
    - Data exposure detection
    - Authentication and authorization checks
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security scanner."""
        self.config = config or {}
        
        # Security patterns for different vulnerability types
        self.security_patterns = self._initialize_security_patterns()
        
        # File extensions to scan
        self.scannable_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', 
            '.php', '.rb', '.cs', '.cpp', '.c', '.h', '.sql',
            '.yaml', '.yml', '.json', '.xml', '.env'
        }
        
        # Scan history
        self.scan_history: List[SecurityScanResult] = []
        
        logger.info("Security Scanner initialized")
    
    def _initialize_security_patterns(self) -> Dict[VulnerabilityType, List[Dict[str, Any]]]:
        """Initialize security vulnerability patterns."""
        return {
            VulnerabilityType.HARDCODED_SECRETS: [
                {
                    "pattern": r'(?i)(password|pwd|pass)\s*[=:]\s*["\'][^"\']{8,}["\']',
                    "description": "Hardcoded password detected",
                    "severity": SeverityLevel.CRITICAL,
                    "cwe_id": "CWE-798"
                },
                {
                    "pattern": r'(?i)(api[_-]?key|apikey|access[_-]?key)\s*[=:]\s*["\'][^"\']{16,}["\']',
                    "description": "Hardcoded API key detected",
                    "severity": SeverityLevel.CRITICAL,
                    "cwe_id": "CWE-798"
                },
                {
                    "pattern": r'(?i)(secret|token|auth)\s*[=:]\s*["\'][^"\']{16,}["\']',
                    "description": "Hardcoded secret/token detected",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-798"
                },
                {
                    "pattern": r'(?i)(private[_-]?key|privatekey)\s*[=:]\s*["\'][^"\']{32,}["\']',
                    "description": "Hardcoded private key detected",
                    "severity": SeverityLevel.CRITICAL,
                    "cwe_id": "CWE-798"
                }
            ],
            VulnerabilityType.SQL_INJECTION: [
                {
                    "pattern": r'(?i)execute\s*\(\s*["\'].*%s.*["\']',
                    "description": "Potential SQL injection via string formatting",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-89"
                },
                {
                    "pattern": r'(?i)query\s*\(\s*f["\'].*\{.*\}.*["\']',
                    "description": "Potential SQL injection via f-string",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-89"
                },
                {
                    "pattern": r'(?i)(select|insert|update|delete).*\+.*["\']',
                    "description": "Potential SQL injection via string concatenation",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-89"
                }
            ],
            VulnerabilityType.XSS: [
                {
                    "pattern": r'(?i)innerHTML\s*=\s*.*\+',
                    "description": "Potential XSS via innerHTML manipulation",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-79"
                },
                {
                    "pattern": r'(?i)document\.write\s*\(',
                    "description": "Potential XSS via document.write",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-79"
                },
                {
                    "pattern": r'(?i)dangerouslySetInnerHTML',
                    "description": "Potential XSS via dangerouslySetInnerHTML",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-79"
                }
            ],
            VulnerabilityType.INSECURE_CRYPTO: [
                {
                    "pattern": r'(?i)(md5|sha1)\s*\(',
                    "description": "Use of weak cryptographic hash function",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-327"
                },
                {
                    "pattern": r'(?i)des\s*\(',
                    "description": "Use of weak DES encryption",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-327"
                },
                {
                    "pattern": r'(?i)random\.random\s*\(',
                    "description": "Use of weak random number generator",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-338"
                }
            ],
            VulnerabilityType.INSECURE_COMMUNICATION: [
                {
                    "pattern": r'(?i)http://[^\\s"\']+',
                    "description": "Insecure HTTP URL detected",
                    "severity": SeverityLevel.LOW,
                    "cwe_id": "CWE-319"
                },
                {
                    "pattern": r'(?i)ssl_verify\s*=\s*false',
                    "description": "SSL verification disabled",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-295"
                },
                {
                    "pattern": r'(?i)verify\s*=\s*false',
                    "description": "Certificate verification disabled",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-295"
                }
            ],
            VulnerabilityType.INPUT_VALIDATION: [
                {
                    "pattern": r'(?i)eval\s*\(',
                    "description": "Use of dangerous eval() function",
                    "severity": SeverityLevel.CRITICAL,
                    "cwe_id": "CWE-95"
                },
                {
                    "pattern": r'(?i)exec\s*\(',
                    "description": "Use of dangerous exec() function",
                    "severity": SeverityLevel.CRITICAL,
                    "cwe_id": "CWE-95"
                },
                {
                    "pattern": r'(?i)shell\s*=\s*true',
                    "description": "Shell injection vulnerability",
                    "severity": SeverityLevel.HIGH,
                    "cwe_id": "CWE-78"
                }
            ],
            VulnerabilityType.DATA_EXPOSURE: [
                {
                    "pattern": r'(?i)print\s*\(.*password.*\)',
                    "description": "Potential password exposure in logs",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-532"
                },
                {
                    "pattern": r'(?i)console\.log\s*\(.*token.*\)',
                    "description": "Potential token exposure in console",
                    "severity": SeverityLevel.MEDIUM,
                    "cwe_id": "CWE-532"
                },
                {
                    "pattern": r'(?i)debug\s*=\s*true',
                    "description": "Debug mode enabled in production",
                    "severity": SeverityLevel.LOW,
                    "cwe_id": "CWE-489"
                }
            ]
        }
    
    async def scan_project(self, project_path: str, scan_type: str = "comprehensive") -> SecurityScanResult:
        """
        Perform comprehensive security scan of the project.
        
        Args:
            project_path: Path to the project directory
            scan_type: Type of scan to perform
            
        Returns:
            Security scan result
        """
        logger.info(f"Starting security scan: {scan_type} for {project_path}")
        
        scan_id = f"security_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.utcnow()
        
        vulnerabilities = []
        files_scanned = 0
        
        try:
            # Static code analysis
            if scan_type in ["comprehensive", "static"]:
                static_vulns, static_files = await self._perform_static_analysis(project_path)
                vulnerabilities.extend(static_vulns)
                files_scanned += static_files
            
            # Dependency vulnerability scanning
            if scan_type in ["comprehensive", "dependencies"]:
                dep_vulns = await self._scan_dependencies(project_path)
                vulnerabilities.extend(dep_vulns)
            
            # Configuration security assessment
            if scan_type in ["comprehensive", "config"]:
                config_vulns, config_files = await self._scan_configurations(project_path)
                vulnerabilities.extend(config_vulns)
                files_scanned += config_files
            
            # Infrastructure security checks
            if scan_type in ["comprehensive", "infrastructure"]:
                infra_vulns, infra_files = await self._scan_infrastructure(project_path)
                vulnerabilities.extend(infra_vulns)
                files_scanned += infra_files
            
        except Exception as e:
            logger.error(f"Error during security scan: {e}")
            raise
        
        completed_at = datetime.utcnow()
        scan_duration = (completed_at - started_at).total_seconds()
        
        # Count vulnerabilities by severity
        severity_counts = {
            "critical": len([v for v in vulnerabilities if v.severity == SeverityLevel.CRITICAL]),
            "high": len([v for v in vulnerabilities if v.severity == SeverityLevel.HIGH]),
            "medium": len([v for v in vulnerabilities if v.severity == SeverityLevel.MEDIUM]),
            "low": len([v for v in vulnerabilities if v.severity == SeverityLevel.LOW])
        }
        
        scan_result = SecurityScanResult(
            scan_id=scan_id,
            scan_type=scan_type,
            started_at=started_at,
            completed_at=completed_at,
            vulnerabilities=vulnerabilities,
            files_scanned=files_scanned,
            total_issues=len(vulnerabilities),
            critical_issues=severity_counts["critical"],
            high_issues=severity_counts["high"],
            medium_issues=severity_counts["medium"],
            low_issues=severity_counts["low"],
            scan_duration_seconds=scan_duration
        )
        
        # Store in history
        self.scan_history.append(scan_result)
        
        logger.info(f"Security scan completed: {len(vulnerabilities)} vulnerabilities found")
        return scan_result
    
    async def _perform_static_analysis(self, project_path: str) -> Tuple[List[SecurityVulnerability], int]:
        """Perform static code analysis for security vulnerabilities."""
        vulnerabilities = []
        files_scanned = 0
        
        project_root = Path(project_path)
        
        # Scan all relevant files
        for file_path in project_root.rglob("*"):
            if (file_path.is_file() and 
                file_path.suffix in self.scannable_extensions and
                not self._should_skip_file(file_path)):
                
                try:
                    file_vulns = await self._scan_file_for_vulnerabilities(file_path)
                    vulnerabilities.extend(file_vulns)
                    files_scanned += 1
                except Exception as e:
                    logger.warning(f"Could not scan file {file_path}: {e}")
        
        return vulnerabilities, files_scanned
    
    async def _scan_file_for_vulnerabilities(self, file_path: Path) -> List[SecurityVulnerability]:
        """Scan a single file for security vulnerabilities."""
        vulnerabilities = []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Apply security patterns
            for vuln_type, patterns in self.security_patterns.items():
                for pattern_info in patterns:
                    pattern = pattern_info["pattern"]
                    matches = list(re.finditer(pattern, content, re.MULTILINE))
                    
                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1
                        
                        # Get code snippet
                        start_line = max(0, line_number - 2)
                        end_line = min(len(lines), line_number + 1)
                        code_snippet = '\n'.join(lines[start_line:end_line])
                        
                        vulnerability = SecurityVulnerability(
                            id=f"{vuln_type.value}_{file_path.stem}_{line_number}",
                            vulnerability_type=vuln_type,
                            severity=SeverityLevel(pattern_info["severity"]),
                            title=pattern_info["description"],
                            description=f"{pattern_info['description']} in {file_path.name}",
                            file_path=str(file_path),
                            line_number=line_number,
                            code_snippet=code_snippet,
                            recommendation=self._get_recommendation(vuln_type),
                            cwe_id=pattern_info.get("cwe_id")
                        )
                        vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.warning(f"Error scanning file {file_path}: {e}")
        
        return vulnerabilities
    
    async def _scan_dependencies(self, project_path: str) -> List[SecurityVulnerability]:
        """Scan project dependencies for known vulnerabilities."""
        vulnerabilities = []
        
        # Check Python dependencies
        requirements_file = Path(project_path) / "requirements.txt"
        if requirements_file.exists():
            python_vulns = await self._scan_python_dependencies(requirements_file)
            vulnerabilities.extend(python_vulns)
        
        # Check Node.js dependencies
        package_json = Path(project_path) / "package.json"
        if package_json.exists():
            node_vulns = await self._scan_node_dependencies(package_json)
            vulnerabilities.extend(node_vulns)
        
        return vulnerabilities
    
    async def _scan_python_dependencies(self, requirements_file: Path) -> List[SecurityVulnerability]:
        """Scan Python dependencies for vulnerabilities."""
        vulnerabilities = []
        
        try:
            # Read requirements
            content = requirements_file.read_text()
            
            # Known vulnerable packages (simplified - in production, use a vulnerability database)
            vulnerable_packages = {
                "django": {"versions": ["<3.2.0"], "cve": "CVE-2021-31542"},
                "flask": {"versions": ["<1.1.0"], "cve": "CVE-2019-1010083"},
                "requests": {"versions": ["<2.20.0"], "cve": "CVE-2018-18074"},
                "pyyaml": {"versions": ["<5.1"], "cve": "CVE-2017-18342"}
            }
            
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    package_name = line.split('==')[0].split('>=')[0].split('<=')[0].lower()
                    
                    if package_name in vulnerable_packages:
                        vulnerability = SecurityVulnerability(
                            id=f"dependency_{package_name}_vulnerable",
                            vulnerability_type=VulnerabilityType.INSECURE_DEPENDENCIES,
                            severity=SeverityLevel.HIGH,
                            title=f"Vulnerable dependency: {package_name}",
                            description=f"Package {package_name} has known security vulnerabilities",
                            file_path=str(requirements_file),
                            recommendation=f"Update {package_name} to a secure version",
                            cwe_id="CWE-1104"
                        )
                        vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.warning(f"Error scanning Python dependencies: {e}")
        
        return vulnerabilities
    
    async def _scan_node_dependencies(self, package_json: Path) -> List[SecurityVulnerability]:
        """Scan Node.js dependencies for vulnerabilities."""
        vulnerabilities = []
        
        try:
            # Try to run npm audit if available
            result = await asyncio.create_subprocess_exec(
                "npm", "audit", "--json",
                cwd=package_json.parent,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                audit_data = json.loads(stdout.decode())
                
                for vuln_id, vuln_info in audit_data.get("vulnerabilities", {}).items():
                    severity_map = {
                        "critical": SeverityLevel.CRITICAL,
                        "high": SeverityLevel.HIGH,
                        "moderate": SeverityLevel.MEDIUM,
                        "low": SeverityLevel.LOW
                    }
                    
                    vulnerability = SecurityVulnerability(
                        id=f"npm_audit_{vuln_id}",
                        vulnerability_type=VulnerabilityType.INSECURE_DEPENDENCIES,
                        severity=severity_map.get(vuln_info.get("severity", "low"), SeverityLevel.LOW),
                        title=f"NPM vulnerability: {vuln_info.get('title', 'Unknown')}",
                        description=vuln_info.get("overview", "NPM audit detected vulnerability"),
                        file_path=str(package_json),
                        recommendation=vuln_info.get("recommendation", "Update package to secure version")
                    )
                    vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.warning(f"Error scanning Node.js dependencies: {e}")
        
        return vulnerabilities
    
    async def _scan_configurations(self, project_path: str) -> Tuple[List[SecurityVulnerability], int]:
        """Scan configuration files for security issues."""
        vulnerabilities = []
        files_scanned = 0
        
        config_patterns = {
            ".env": [
                (r"(?i)debug\s*=\s*true", "Debug mode enabled", SeverityLevel.LOW),
                (r"(?i)ssl\s*=\s*false", "SSL disabled", SeverityLevel.HIGH),
            ],
            ".yaml": [
                (r"(?i)allowPrivilegeEscalation:\s*true", "Privilege escalation allowed", SeverityLevel.HIGH),
                (r"(?i)runAsRoot:\s*true", "Running as root", SeverityLevel.MEDIUM),
            ],
            ".yml": [
                (r"(?i)allowPrivilegeEscalation:\s*true", "Privilege escalation allowed", SeverityLevel.HIGH),
                (r"(?i)runAsRoot:\s*true", "Running as root", SeverityLevel.MEDIUM),
            ]
        }
        
        project_root = Path(project_path)
        
        for file_path in project_root.rglob("*"):
            if file_path.is_file():
                for ext, patterns in config_patterns.items():
                    if file_path.name.endswith(ext):
                        try:
                            content = file_path.read_text()
                            
                            for pattern, description, severity in patterns:
                                matches = list(re.finditer(pattern, content, re.MULTILINE))
                                
                                for match in matches:
                                    line_number = content[:match.start()].count('\n') + 1
                                    
                                    vulnerability = SecurityVulnerability(
                                        id=f"config_{file_path.stem}_{line_number}",
                                        vulnerability_type=VulnerabilityType.WEAK_AUTHENTICATION,
                                        severity=severity,
                                        title=f"Configuration issue: {description}",
                                        description=f"{description} in {file_path.name}",
                                        file_path=str(file_path),
                                        line_number=line_number,
                                        recommendation="Review and secure configuration"
                                    )
                                    vulnerabilities.append(vulnerability)
                            
                            files_scanned += 1
                        
                        except Exception as e:
                            logger.warning(f"Error scanning config file {file_path}: {e}")
        
        return vulnerabilities, files_scanned
    
    async def _scan_infrastructure(self, project_path: str) -> Tuple[List[SecurityVulnerability], int]:
        """Scan infrastructure configurations for security issues."""
        vulnerabilities = []
        files_scanned = 0
        
        # Check Kubernetes configurations
        k8s_path = Path(project_path) / "k8s"
        if k8s_path.exists():
            k8s_vulns, k8s_files = await self._scan_kubernetes_configs(k8s_path)
            vulnerabilities.extend(k8s_vulns)
            files_scanned += k8s_files
        
        # Check Docker configurations
        dockerfile_path = Path(project_path) / "Dockerfile"
        if dockerfile_path.exists():
            docker_vulns = await self._scan_dockerfile(dockerfile_path)
            vulnerabilities.extend(docker_vulns)
            files_scanned += 1
        
        return vulnerabilities, files_scanned
    
    async def _scan_kubernetes_configs(self, k8s_path: Path) -> Tuple[List[SecurityVulnerability], int]:
        """Scan Kubernetes configuration files."""
        vulnerabilities = []
        files_scanned = 0
        
        security_checks = [
            (r"(?i)privileged:\s*true", "Privileged container", SeverityLevel.CRITICAL),
            (r"(?i)runAsUser:\s*0", "Running as root user", SeverityLevel.HIGH),
            (r"(?i)allowPrivilegeEscalation:\s*true", "Privilege escalation allowed", SeverityLevel.HIGH),
            (r"(?i)hostNetwork:\s*true", "Host network access", SeverityLevel.MEDIUM),
            (r"(?i)hostPID:\s*true", "Host PID namespace", SeverityLevel.MEDIUM),
        ]
        
        for yaml_file in k8s_path.rglob("*.yaml"):
            try:
                content = yaml_file.read_text()
                
                for pattern, description, severity in security_checks:
                    matches = list(re.finditer(pattern, content, re.MULTILINE))
                    
                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1
                        
                        vulnerability = SecurityVulnerability(
                            id=f"k8s_{yaml_file.stem}_{line_number}",
                            vulnerability_type=VulnerabilityType.PRIVILEGE_ESCALATION,
                            severity=severity,
                            title=f"Kubernetes security issue: {description}",
                            description=f"{description} in {yaml_file.name}",
                            file_path=str(yaml_file),
                            line_number=line_number,
                            recommendation="Follow Kubernetes security best practices"
                        )
                        vulnerabilities.append(vulnerability)
                
                files_scanned += 1
            
            except Exception as e:
                logger.warning(f"Error scanning K8s file {yaml_file}: {e}")
        
        return vulnerabilities, files_scanned
    
    async def _scan_dockerfile(self, dockerfile_path: Path) -> List[SecurityVulnerability]:
        """Scan Dockerfile for security issues."""
        vulnerabilities = []
        
        try:
            content = dockerfile_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for running as root
                if re.match(r'(?i)user\s+root', line):
                    vulnerability = SecurityVulnerability(
                        id=f"dockerfile_root_{i}",
                        vulnerability_type=VulnerabilityType.PRIVILEGE_ESCALATION,
                        severity=SeverityLevel.HIGH,
                        title="Dockerfile runs as root",
                        description="Container configured to run as root user",
                        file_path=str(dockerfile_path),
                        line_number=i,
                        recommendation="Use a non-root user for container execution"
                    )
                    vulnerabilities.append(vulnerability)
                
                # Check for ADD instead of COPY
                if re.match(r'(?i)add\s+', line) and not re.search(r'\.(tar|gz|zip)$', line):
                    vulnerability = SecurityVulnerability(
                        id=f"dockerfile_add_{i}",
                        vulnerability_type=VulnerabilityType.DATA_EXPOSURE,
                        severity=SeverityLevel.LOW,
                        title="Use COPY instead of ADD",
                        description="ADD command has additional features that may be exploited",
                        file_path=str(dockerfile_path),
                        line_number=i,
                        recommendation="Use COPY instead of ADD for simple file copying"
                    )
                    vulnerabilities.append(vulnerability)
        
        except Exception as e:
            logger.warning(f"Error scanning Dockerfile: {e}")
        
        return vulnerabilities
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "node_modules", "__pycache__", ".git", ".venv", "venv",
            "build", "dist", ".pytest_cache", "coverage"
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _get_recommendation(self, vuln_type: VulnerabilityType) -> str:
        """Get security recommendation for vulnerability type."""
        recommendations = {
            VulnerabilityType.HARDCODED_SECRETS: "Use environment variables or secure key management",
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries or ORM",
            VulnerabilityType.XSS: "Sanitize user input and use safe DOM manipulation",
            VulnerabilityType.INSECURE_CRYPTO: "Use strong cryptographic algorithms (SHA-256, AES)",
            VulnerabilityType.WEAK_AUTHENTICATION: "Implement strong authentication mechanisms",
            VulnerabilityType.INSECURE_DEPENDENCIES: "Update to secure package versions",
            VulnerabilityType.DATA_EXPOSURE: "Remove sensitive data from logs and debug output",
            VulnerabilityType.PRIVILEGE_ESCALATION: "Follow principle of least privilege",
            VulnerabilityType.INSECURE_COMMUNICATION: "Use HTTPS and verify SSL certificates",
            VulnerabilityType.INPUT_VALIDATION: "Validate and sanitize all user inputs"
        }
        
        return recommendations.get(vuln_type, "Follow security best practices")
    
    def get_scan_history(self, limit: int = 10) -> List[SecurityScanResult]:
        """Get recent security scan history."""
        return sorted(
            self.scan_history,
            key=lambda scan: scan.started_at,
            reverse=True
        )[:limit]
    
    def get_vulnerability_summary(self) -> Dict[str, Any]:
        """Get summary of all vulnerabilities from recent scans."""
        if not self.scan_history:
            return {"message": "No scan history available"}
        
        latest_scan = self.scan_history[-1]
        
        # Group vulnerabilities by type
        vuln_by_type = {}
        for vuln in latest_scan.vulnerabilities:
            vuln_type = vuln.vulnerability_type.value
            if vuln_type not in vuln_by_type:
                vuln_by_type[vuln_type] = []
            vuln_by_type[vuln_type].append(vuln)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(latest_scan.vulnerabilities)
        
        return {
            "scan_id": latest_scan.scan_id,
            "total_vulnerabilities": latest_scan.total_issues,
            "critical_issues": latest_scan.critical_issues,
            "high_issues": latest_scan.high_issues,
            "medium_issues": latest_scan.medium_issues,
            "low_issues": latest_scan.low_issues,
            "risk_score": risk_score,
            "vulnerabilities_by_type": {
                vuln_type: len(vulns) for vuln_type, vulns in vuln_by_type.items()
            },
            "scan_date": latest_scan.completed_at.isoformat(),
            "files_scanned": latest_scan.files_scanned
        }
    
    def _calculate_risk_score(self, vulnerabilities: List[SecurityVulnerability]) -> float:
        """Calculate overall risk score (0-100)."""
        if not vulnerabilities:
            return 0.0
        
        severity_weights = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 7,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 1
        }
        
        total_score = sum(
            severity_weights.get(vuln.severity, 1) 
            for vuln in vulnerabilities
        )
        
        # Normalize to 0-100 scale
        max_possible_score = len(vulnerabilities) * 10
        risk_score = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0
        
        return round(risk_score, 1)


# Global security scanner instance
_security_scanner: Optional[SecurityScanner] = None


def get_security_scanner() -> SecurityScanner:
    """Get the global security scanner instance."""
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = SecurityScanner()
    return _security_scanner


def set_security_scanner(scanner: SecurityScanner) -> None:
    """Set the global security scanner instance."""
    global _security_scanner
    _security_scanner = scanner
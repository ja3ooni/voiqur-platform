"""
AI Act Compliance Validator

Validates EU AI Act compliance for the EUVoice AI Platform including
risk classification, transparency requirements, and governance measures.
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


class AIRiskCategory(str, Enum):
    """AI Act risk categories."""
    UNACCEPTABLE_RISK = "unacceptable_risk"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"
    MINIMAL_RISK = "minimal_risk"


class AISystemType(str, Enum):
    """AI system types under the AI Act."""
    GENERAL_PURPOSE = "general_purpose"
    FOUNDATION_MODEL = "foundation_model"
    BIOMETRIC_IDENTIFICATION = "biometric_identification"
    EMOTION_RECOGNITION = "emotion_recognition"
    VOICE_ASSISTANT = "voice_assistant"
    CHATBOT = "chatbot"
    RECOMMENDATION_SYSTEM = "recommendation_system"


@dataclass
class AIActValidationResult:
    """AI Act validation result."""
    status: str  # "compliant", "non_compliant", "warning"
    issues: List[Any]  # ComplianceIssue objects
    risk_classification: AIRiskCategory
    system_types: List[AISystemType]
    transparency_requirements: Dict[str, bool]
    governance_measures: Dict[str, bool]
    recommendations: List[str]


class AIActValidator:
    """
    EU AI Act compliance validator for the EUVoice AI Platform.
    
    Validates compliance with AI Act requirements including:
    - Risk classification and assessment
    - Transparency and explainability requirements
    - Human oversight and governance
    - Quality management systems
    - Documentation and record-keeping
    - Conformity assessment procedures
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize AI Act validator."""
        self.config = config
        
        # AI model patterns for detection
        self.ai_model_patterns = [
            r'\b(model|neural|network|transformer|bert|gpt|llm)\b',
            r'\b(tensorflow|pytorch|keras|huggingface|openai)\b',
            r'\b(train|inference|predict|classify|generate)\b',
            r'\b(stt|tts|asr|nlp|nlu|speech|voice)\b'
        ]
        
        # High-risk AI system indicators
        self.high_risk_indicators = [
            r'\b(biometric|facial|recognition|identification)\b',
            r'\b(emotion|sentiment|mood|feeling)\b',
            r'\b(recruitment|hiring|employment|cv|resume)\b',
            r'\b(credit|loan|finance|scoring|rating)\b',
            r'\b(education|exam|assessment|grading)\b',
            r'\b(healthcare|medical|diagnosis|treatment)\b',
            r'\b(law_enforcement|police|security|surveillance)\b',
            r'\b(migration|asylum|border|visa)\b'
        ]
        
        # Prohibited AI practices
        self.prohibited_practices = [
            r'\b(subliminal|manipulation|deception|dark_pattern)\b',
            r'\b(social_scoring|citizen_scoring|behavior_rating)\b',
            r'\b(real_time.*biometric.*public)\b',
            r'\b(exploit.*vulnerability.*age|disability|social)\b'
        ]
        
        logger.info("AI Act Validator initialized")
    
    async def validate_project(self, project_path: str) -> AIActValidationResult:
        """
        Validate AI Act compliance for the entire project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            AI Act validation result
        """
        logger.info(f"Starting AI Act validation for project: {project_path}")
        
        issues = []
        
        # Detect AI system types
        system_types = await self._detect_ai_system_types(project_path)
        
        # Classify risk category
        risk_classification = await self._classify_risk_category(project_path, system_types)
        
        # Check for prohibited practices
        issues.extend(await self._check_prohibited_practices(project_path))
        
        # Check transparency requirements
        transparency_requirements = await self._check_transparency_requirements(project_path)
        transparency_issues = await self._validate_transparency_compliance(
            project_path, transparency_requirements
        )
        issues.extend(transparency_issues)
        
        # Check governance measures
        governance_measures = await self._check_governance_measures(project_path)
        governance_issues = await self._validate_governance_compliance(
            project_path, governance_measures
        )
        issues.extend(governance_issues)
        
        # Check risk-specific requirements
        if risk_classification == AIRiskCategory.HIGH_RISK:
            issues.extend(await self._check_high_risk_requirements(project_path))
        elif risk_classification == AIRiskCategory.LIMITED_RISK:
            issues.extend(await self._check_limited_risk_requirements(project_path))
        
        # Check foundation model requirements (if applicable)
        if AISystemType.FOUNDATION_MODEL in system_types:
            issues.extend(await self._check_foundation_model_requirements(project_path))
        
        # Check documentation requirements
        issues.extend(await self._check_documentation_requirements(project_path))
        
        # Check quality management system
        issues.extend(await self._check_quality_management(project_path))
        
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
        recommendations = self._generate_ai_act_recommendations(
            issues, risk_classification, system_types
        )
        
        result = AIActValidationResult(
            status=status,
            issues=issues,
            risk_classification=risk_classification,
            system_types=system_types,
            transparency_requirements=transparency_requirements,
            governance_measures=governance_measures,
            recommendations=recommendations
        )
        
        logger.info(f"AI Act validation completed. Status: {status}, Risk: {risk_classification.value}")
        return result
    
    async def _detect_ai_system_types(self, project_path: str) -> List[AISystemType]:
        """Detect AI system types present in the project."""
        system_types = []
        
        # Analyze codebase for AI system indicators
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                
                # Voice assistant detection
                if re.search(r'\b(voice|speech|stt|tts|assistant|conversation)\b', content, re.IGNORECASE):
                    if AISystemType.VOICE_ASSISTANT not in system_types:
                        system_types.append(AISystemType.VOICE_ASSISTANT)
                
                # Emotion recognition detection
                if re.search(r'\b(emotion|sentiment|mood|feeling|affect)\b', content, re.IGNORECASE):
                    if AISystemType.EMOTION_RECOGNITION not in system_types:
                        system_types.append(AISystemType.EMOTION_RECOGNITION)
                
                # Biometric identification detection
                if re.search(r'\b(biometric|facial|fingerprint|iris|voice_print)\b', content, re.IGNORECASE):
                    if AISystemType.BIOMETRIC_IDENTIFICATION not in system_types:
                        system_types.append(AISystemType.BIOMETRIC_IDENTIFICATION)
                
                # Foundation model detection
                if re.search(r'\b(foundation|base_model|pretrained|transformer|llm)\b', content, re.IGNORECASE):
                    if AISystemType.FOUNDATION_MODEL not in system_types:
                        system_types.append(AISystemType.FOUNDATION_MODEL)
                
                # Chatbot detection
                if re.search(r'\b(chatbot|chat|dialogue|conversation|bot)\b', content, re.IGNORECASE):
                    if AISystemType.CHATBOT not in system_types:
                        system_types.append(AISystemType.CHATBOT)
            
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
        
        # Default to general purpose if no specific type detected
        if not system_types:
            system_types.append(AISystemType.GENERAL_PURPOSE)
        
        return system_types
    
    async def _classify_risk_category(
        self, 
        project_path: str, 
        system_types: List[AISystemType]
    ) -> AIRiskCategory:
        """Classify the AI system's risk category."""
        
        # Check for prohibited practices (unacceptable risk)
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                for pattern in self.prohibited_practices:
                    if re.search(pattern, content, re.IGNORECASE):
                        return AIRiskCategory.UNACCEPTABLE_RISK
            except Exception:
                continue
        
        # Check for high-risk indicators
        high_risk_found = False
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                for pattern in self.high_risk_indicators:
                    if re.search(pattern, content, re.IGNORECASE):
                        high_risk_found = True
                        break
                if high_risk_found:
                    break
            except Exception:
                continue
        
        if high_risk_found:
            return AIRiskCategory.HIGH_RISK
        
        # Check system types for risk classification
        high_risk_types = {
            AISystemType.BIOMETRIC_IDENTIFICATION,
            AISystemType.EMOTION_RECOGNITION
        }
        
        if any(sys_type in high_risk_types for sys_type in system_types):
            return AIRiskCategory.HIGH_RISK
        
        # Voice assistants and chatbots are typically limited risk
        limited_risk_types = {
            AISystemType.VOICE_ASSISTANT,
            AISystemType.CHATBOT
        }
        
        if any(sys_type in limited_risk_types for sys_type in system_types):
            return AIRiskCategory.LIMITED_RISK
        
        # Default to minimal risk
        return AIRiskCategory.MINIMAL_RISK
    
    async def _check_prohibited_practices(self, project_path: str) -> List[Any]:
        """Check for prohibited AI practices."""
        issues = []
        
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                
                for pattern in self.prohibited_practices:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        issues.append(self._create_issue(
                            "ai_act_prohibited_practice",
                            "critical",
                            "Prohibited AI Practice Detected",
                            f"Potential prohibited practice found: {match.group()}",
                            "ai_system",
                            str(py_file),
                            "Remove or modify prohibited AI practices immediately"
                        ))
            
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
        
        return issues
    
    async def _check_transparency_requirements(self, project_path: str) -> Dict[str, bool]:
        """Check transparency requirements implementation."""
        requirements = {
            "user_notification": False,
            "system_documentation": False,
            "decision_explanation": False,
            "human_oversight": False,
            "accuracy_disclosure": False,
            "limitations_disclosure": False
        }
        
        # Check for user notification
        frontend_path = Path(project_path) / "frontend"
        if frontend_path.exists():
            for tsx_file in frontend_path.rglob("*.tsx"):
                try:
                    content = tsx_file.read_text()
                    if re.search(r'\b(ai|artificial|automated|algorithm)\b.*\b(notice|notification|disclosure)\b', content, re.IGNORECASE):
                        requirements["user_notification"] = True
                        break
                except Exception:
                    continue
        
        # Check for system documentation
        docs_path = Path(project_path) / "docs"
        if docs_path.exists():
            for doc_file in docs_path.rglob("*.md"):
                try:
                    content = doc_file.read_text()
                    if re.search(r'\b(ai|model|algorithm|system)\b.*\b(documentation|description|specification)\b', content, re.IGNORECASE):
                        requirements["system_documentation"] = True
                        break
                except Exception:
                    continue
        
        # Check for decision explanation
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                if re.search(r'\b(explain|explanation|interpret|reasoning|rationale)\b', content, re.IGNORECASE):
                    requirements["decision_explanation"] = True
                    break
            except Exception:
                continue
        
        # Check for human oversight
        for py_file in Path(project_path).rglob("*.py"):
            try:
                content = py_file.read_text()
                if re.search(r'\b(human|manual|override|review|supervision)\b', content, re.IGNORECASE):
                    requirements["human_oversight"] = True
                    break
            except Exception:
                continue
        
        return requirements
    
    async def _validate_transparency_compliance(
        self, 
        project_path: str, 
        requirements: Dict[str, bool]
    ) -> List[Any]:
        """Validate transparency compliance."""
        issues = []
        
        for requirement, implemented in requirements.items():
            if not implemented:
                severity = "high" if requirement in ["user_notification", "human_oversight"] else "medium"
                
                issues.append(self._create_issue(
                    f"ai_act_transparency_{requirement}",
                    severity,
                    f"Missing Transparency Requirement: {requirement.replace('_', ' ').title()}",
                    f"AI Act transparency requirement not implemented: {requirement}",
                    "transparency",
                    None,
                    f"Implement {requirement.replace('_', ' ')} for AI Act compliance"
                ))
        
        return issues
    
    async def _check_governance_measures(self, project_path: str) -> Dict[str, bool]:
        """Check governance measures implementation."""
        measures = {
            "risk_management": False,
            "quality_assurance": False,
            "monitoring_system": False,
            "incident_response": False,
            "audit_trail": False,
            "version_control": False
        }
        
        # Check for risk management
        risk_files = list(Path(project_path).rglob("*risk*.py"))
        risk_files.extend(list(Path(project_path).rglob("*risk*.md")))
        if risk_files:
            measures["risk_management"] = True
        
        # Check for quality assurance (tests)
        test_files = list(Path(project_path).rglob("test_*.py"))
        test_files.extend(list(Path(project_path).rglob("*_test.py")))
        if test_files:
            measures["quality_assurance"] = True
        
        # Check for monitoring
        monitoring_files = list(Path(project_path).rglob("*monitor*.py"))
        monitoring_files.extend(list(Path(project_path).rglob("*metric*.py")))
        if monitoring_files:
            measures["monitoring_system"] = True
        
        # Check for incident response
        incident_files = list(Path(project_path).rglob("*incident*.py"))
        incident_files.extend(list(Path(project_path).rglob("*alert*.py")))
        if incident_files:
            measures["incident_response"] = True
        
        # Check for audit trail
        audit_files = list(Path(project_path).rglob("*audit*.py"))
        audit_files.extend(list(Path(project_path).rglob("*log*.py")))
        if audit_files:
            measures["audit_trail"] = True
        
        # Check for version control (.git directory)
        if (Path(project_path) / ".git").exists():
            measures["version_control"] = True
        
        return measures
    
    async def _validate_governance_compliance(
        self, 
        project_path: str, 
        measures: Dict[str, bool]
    ) -> List[Any]:
        """Validate governance compliance."""
        issues = []
        
        critical_measures = ["risk_management", "quality_assurance", "audit_trail"]
        
        for measure, implemented in measures.items():
            if not implemented:
                severity = "critical" if measure in critical_measures else "high"
                
                issues.append(self._create_issue(
                    f"ai_act_governance_{measure}",
                    severity,
                    f"Missing Governance Measure: {measure.replace('_', ' ').title()}",
                    f"AI Act governance requirement not implemented: {measure}",
                    "governance",
                    None,
                    f"Implement {measure.replace('_', ' ')} for AI Act compliance"
                ))
        
        return issues
    
    async def _check_high_risk_requirements(self, project_path: str) -> List[Any]:
        """Check high-risk AI system specific requirements."""
        issues = []
        
        # Check for conformity assessment
        conformity_files = list(Path(project_path).rglob("*conformity*.md"))
        conformity_files.extend(list(Path(project_path).rglob("*assessment*.md")))
        
        if not conformity_files:
            issues.append(self._create_issue(
                "ai_act_high_risk_conformity",
                "critical",
                "Missing Conformity Assessment",
                "High-risk AI system requires conformity assessment documentation",
                "compliance",
                None,
                "Conduct and document conformity assessment for high-risk AI system"
            ))
        
        # Check for CE marking documentation
        ce_files = list(Path(project_path).rglob("*ce_mark*.md"))
        ce_files.extend(list(Path(project_path).rglob("*declaration*.md")))
        
        if not ce_files:
            issues.append(self._create_issue(
                "ai_act_high_risk_ce_marking",
                "critical",
                "Missing CE Marking Documentation",
                "High-risk AI system requires CE marking and declaration of conformity",
                "compliance",
                None,
                "Prepare CE marking and declaration of conformity documentation"
            ))
        
        # Check for post-market monitoring
        monitoring_files = list(Path(project_path).rglob("*post_market*.py"))
        monitoring_files.extend(list(Path(project_path).rglob("*monitoring*.py")))
        
        if not monitoring_files:
            issues.append(self._create_issue(
                "ai_act_high_risk_monitoring",
                "high",
                "Missing Post-Market Monitoring",
                "High-risk AI system requires post-market monitoring system",
                "monitoring",
                None,
                "Implement post-market monitoring and reporting system"
            ))
        
        return issues
    
    async def _check_limited_risk_requirements(self, project_path: str) -> List[Any]:
        """Check limited-risk AI system specific requirements."""
        issues = []
        
        # Check for transparency obligations
        transparency_found = False
        
        # Check frontend for AI disclosure
        frontend_path = Path(project_path) / "frontend"
        if frontend_path.exists():
            for tsx_file in frontend_path.rglob("*.tsx"):
                try:
                    content = tsx_file.read_text()
                    if re.search(r'\b(ai|artificial|automated)\b.*\b(generated|powered|assisted)\b', content, re.IGNORECASE):
                        transparency_found = True
                        break
                except Exception:
                    continue
        
        if not transparency_found:
            issues.append(self._create_issue(
                "ai_act_limited_risk_transparency",
                "medium",
                "Missing AI Transparency Disclosure",
                "Limited-risk AI system must inform users about AI interaction",
                "transparency",
                None,
                "Add clear disclosure that users are interacting with an AI system"
            ))
        
        return issues
    
    async def _check_foundation_model_requirements(self, project_path: str) -> List[Any]:
        """Check foundation model specific requirements."""
        issues = []
        
        # Check for model documentation
        model_docs = list(Path(project_path).rglob("*model*.md"))
        model_docs.extend(list(Path(project_path).rglob("MODEL_CARD.md")))
        
        if not model_docs:
            issues.append(self._create_issue(
                "ai_act_foundation_model_docs",
                "high",
                "Missing Foundation Model Documentation",
                "Foundation models require comprehensive documentation",
                "documentation",
                None,
                "Create detailed model documentation including capabilities and limitations"
            ))
        
        # Check for training data documentation
        data_docs = list(Path(project_path).rglob("*data*.md"))
        data_docs.extend(list(Path(project_path).rglob("DATASET.md")))
        
        if not data_docs:
            issues.append(self._create_issue(
                "ai_act_foundation_training_data",
                "high",
                "Missing Training Data Documentation",
                "Foundation models require training data documentation",
                "documentation",
                None,
                "Document training data sources, preprocessing, and characteristics"
            ))
        
        return issues
    
    async def _check_documentation_requirements(self, project_path: str) -> List[Any]:
        """Check documentation requirements."""
        issues = []
        
        required_docs = [
            ("README.md", "Project documentation"),
            ("docs/ai_system.md", "AI system description"),
            ("docs/risk_assessment.md", "Risk assessment"),
            ("docs/quality_management.md", "Quality management system")
        ]
        
        for doc_file, description in required_docs:
            if not (Path(project_path) / doc_file).exists():
                issues.append(self._create_issue(
                    f"ai_act_docs_{doc_file.replace('/', '_').replace('.md', '')}",
                    "medium",
                    f"Missing Documentation: {description}",
                    f"Required documentation not found: {doc_file}",
                    "documentation",
                    None,
                    f"Create {description.lower()} documentation"
                ))
        
        return issues
    
    async def _check_quality_management(self, project_path: str) -> List[Any]:
        """Check quality management system."""
        issues = []
        
        # Check for quality management documentation
        qms_files = list(Path(project_path).rglob("*quality*.md"))
        qms_files.extend(list(Path(project_path).rglob("*qms*.md")))
        
        if not qms_files:
            issues.append(self._create_issue(
                "ai_act_quality_management_missing",
                "high",
                "Missing Quality Management System",
                "AI Act requires quality management system documentation",
                "quality",
                None,
                "Implement and document quality management system"
            ))
        
        # Check for testing procedures
        test_procedures = list(Path(project_path).rglob("*test*.md"))
        test_procedures.extend(list(Path(project_path).rglob("TESTING.md")))
        
        if not test_procedures:
            issues.append(self._create_issue(
                "ai_act_testing_procedures",
                "medium",
                "Missing Testing Procedures Documentation",
                "Quality management requires documented testing procedures",
                "testing",
                None,
                "Document testing and validation procedures"
            ))
        
        return issues
    
    def _generate_ai_act_recommendations(
        self, 
        issues: List[Any], 
        risk_classification: AIRiskCategory,
        system_types: List[AISystemType]
    ) -> List[str]:
        """Generate AI Act specific recommendations."""
        recommendations = []
        
        # Risk-specific recommendations
        if risk_classification == AIRiskCategory.UNACCEPTABLE_RISK:
            recommendations.append(
                "CRITICAL: Remove prohibited AI practices immediately to comply with AI Act"
            )
        elif risk_classification == AIRiskCategory.HIGH_RISK:
            recommendations.append(
                "Implement full high-risk AI system requirements: conformity assessment, CE marking, post-market monitoring"
            )
        elif risk_classification == AIRiskCategory.LIMITED_RISK:
            recommendations.append(
                "Implement transparency obligations: inform users about AI interaction"
            )
        
        # System type specific recommendations
        if AISystemType.EMOTION_RECOGNITION in system_types:
            recommendations.append(
                "Emotion recognition systems require special attention to fundamental rights and transparency"
            )
        
        if AISystemType.FOUNDATION_MODEL in system_types:
            recommendations.append(
                "Foundation models require comprehensive documentation and systemic risk assessment"
            )
        
        # General recommendations based on issues
        issue_categories = {i.component for i in issues}
        
        if "transparency" in issue_categories:
            recommendations.append(
                "Implement comprehensive transparency measures including user notifications and system documentation"
            )
        
        if "governance" in issue_categories:
            recommendations.append(
                "Establish robust governance framework with risk management and quality assurance"
            )
        
        if "documentation" in issue_categories:
            recommendations.append(
                "Complete all required documentation for AI Act compliance"
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
            category=ComplianceCategory.AI_ACT,
            severity=severity,
            title=title,
            description=description,
            component=component,
            file_path=file_path,
            recommendation=recommendation,
            auto_fixable=False  # AI Act issues typically require manual review
        )
    
    async def apply_auto_fixes(self, issues: List[Any]) -> List[str]:
        """Apply automatic fixes for AI Act issues."""
        # Most AI Act issues require manual intervention
        fixes_applied = []
        
        for issue in issues:
            if issue.auto_fixable:
                # Implement specific auto-fixes here
                pass
        
        return fixes_applied
    
    async def apply_single_fix(self, issue: Any) -> Optional[str]:
        """Apply a single auto-fix for an AI Act issue."""
        # Placeholder for individual issue fixes
        return None
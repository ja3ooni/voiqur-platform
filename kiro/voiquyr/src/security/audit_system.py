"""
Audit System

Comprehensive audit trail generation and compliance reporting system
for the EUVoice AI Platform.
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    SYSTEM_CONFIGURATION = "system_configuration"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_CHECK = "compliance_check"
    VOICE_PROCESSING = "voice_processing"
    MODEL_INFERENCE = "model_inference"
    ADMIN_ACTION = "admin_action"
    ERROR_EVENT = "error_event"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    outcome: str  # "success", "failure", "error"
    details: Dict[str, Any]
    risk_score: float
    compliance_tags: List[str]
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not isinstance(self.timestamp, datetime):
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
            "risk_score": self.risk_score,
            "compliance_tags": self.compliance_tags
        }


@dataclass
class ComplianceReport:
    """Compliance audit report."""
    report_id: str
    report_type: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_events: int
    critical_events: int
    high_risk_events: int
    compliance_violations: List[Dict[str, Any]]
    gdpr_events: List[AuditEvent]
    security_events: List[AuditEvent]
    data_processing_events: List[AuditEvent]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_events": self.total_events,
            "critical_events": self.critical_events,
            "high_risk_events": self.high_risk_events,
            "compliance_violations": self.compliance_violations,
            "gdpr_events": [event.to_dict() for event in self.gdpr_events],
            "security_events": [event.to_dict() for event in self.security_events],
            "data_processing_events": [event.to_dict() for event in self.data_processing_events],
            "summary": self.summary
        }


class AuditSystem:
    """
    Comprehensive audit system for the EUVoice AI Platform.
    
    Provides:
    - Audit trail generation and storage
    - Compliance reporting (GDPR, AI Act)
    - Security event monitoring
    - Data processing audit logs
    - Risk assessment and alerting
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize audit system."""
        self.config = config or {}
        
        # Audit storage
        self.audit_events: List[AuditEvent] = []
        self.audit_storage_path = Path(self.config.get("audit_storage_path", "audit_logs"))
        self.audit_storage_path.mkdir(exist_ok=True)
        
        # Compliance configuration
        self.gdpr_retention_days = self.config.get("gdpr_retention_days", 2555)  # 7 years
        self.audit_retention_days = self.config.get("audit_retention_days", 2555)  # 7 years
        
        # Risk scoring weights
        self.risk_weights = {
            AuditEventType.DATA_DELETION: 9.0,
            AuditEventType.ADMIN_ACTION: 8.0,
            AuditEventType.SYSTEM_CONFIGURATION: 7.0,
            AuditEventType.SECURITY_EVENT: 8.0,
            AuditEventType.DATA_MODIFICATION: 6.0,
            AuditEventType.DATA_ACCESS: 4.0,
            AuditEventType.API_ACCESS: 3.0,
            AuditEventType.USER_LOGIN: 2.0,
            AuditEventType.VOICE_PROCESSING: 3.0,
            AuditEventType.MODEL_INFERENCE: 3.0
        }
        
        logger.info("Audit System initialized")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        outcome: str = "success",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: Optional[AuditSeverity] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            action: Action performed
            outcome: Outcome of the action
            user_id: User identifier
            session_id: Session identifier
            source_ip: Source IP address
            user_agent: User agent string
            resource: Resource accessed
            details: Additional event details
            severity: Event severity
            
        Returns:
            Created audit event
        """
        # Auto-determine severity if not provided
        if severity is None:
            severity = self._determine_severity(event_type, outcome)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(event_type, outcome, details or {})
        
        # Determine compliance tags
        compliance_tags = self._get_compliance_tags(event_type, details or {})
        
        # Create audit event
        audit_event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            source_ip=source_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details or {},
            risk_score=risk_score,
            compliance_tags=compliance_tags
        )
        
        # Store event
        self.audit_events.append(audit_event)
        
        # Persist to storage
        await self._persist_event(audit_event)
        
        # Check for compliance violations
        await self._check_compliance_violations(audit_event)
        
        logger.debug(f"Audit event logged: {event_type.value} - {action}")
        return audit_event
    
    def _determine_severity(self, event_type: AuditEventType, outcome: str) -> AuditSeverity:
        """Determine event severity based on type and outcome."""
        if outcome == "failure" or outcome == "error":
            if event_type in [AuditEventType.SECURITY_EVENT, AuditEventType.DATA_DELETION]:
                return AuditSeverity.CRITICAL
            elif event_type in [AuditEventType.ADMIN_ACTION, AuditEventType.SYSTEM_CONFIGURATION]:
                return AuditSeverity.HIGH
            else:
                return AuditSeverity.MEDIUM
        
        # Success cases
        if event_type in [AuditEventType.DATA_DELETION, AuditEventType.ADMIN_ACTION]:
            return AuditSeverity.HIGH
        elif event_type in [AuditEventType.DATA_MODIFICATION, AuditEventType.SYSTEM_CONFIGURATION]:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW
    
    def _calculate_risk_score(
        self, 
        event_type: AuditEventType, 
        outcome: str, 
        details: Dict[str, Any]
    ) -> float:
        """Calculate risk score for the event (0-10)."""
        base_score = self.risk_weights.get(event_type, 3.0)
        
        # Adjust for outcome
        if outcome == "failure":
            base_score *= 1.5
        elif outcome == "error":
            base_score *= 1.3
        
        # Adjust for sensitive data
        if details.get("contains_pii", False):
            base_score *= 1.4
        
        if details.get("contains_audio", False):
            base_score *= 1.2
        
        # Adjust for admin actions
        if details.get("admin_action", False):
            base_score *= 1.3
        
        return min(10.0, round(base_score, 1))
    
    def _get_compliance_tags(self, event_type: AuditEventType, details: Dict[str, Any]) -> List[str]:
        """Get compliance tags for the event."""
        tags = []
        
        # GDPR tags
        if event_type in [
            AuditEventType.DATA_ACCESS, 
            AuditEventType.DATA_MODIFICATION, 
            AuditEventType.DATA_DELETION
        ]:
            tags.append("GDPR")
        
        if details.get("contains_pii", False):
            tags.append("GDPR_PII")
        
        if details.get("data_subject_request", False):
            tags.append("GDPR_DSR")
        
        # AI Act tags
        if event_type in [AuditEventType.MODEL_INFERENCE, AuditEventType.VOICE_PROCESSING]:
            tags.append("AI_ACT")
        
        if details.get("high_risk_ai", False):
            tags.append("AI_ACT_HIGH_RISK")
        
        # Security tags
        if event_type == AuditEventType.SECURITY_EVENT:
            tags.append("SECURITY")
        
        if details.get("authentication_failure", False):
            tags.append("AUTH_FAILURE")
        
        return tags
    
    async def _persist_event(self, event: AuditEvent) -> None:
        """Persist audit event to storage."""
        try:
            # Create daily log file
            date_str = event.timestamp.strftime("%Y-%m-%d")
            log_file = self.audit_storage_path / f"audit_{date_str}.jsonl"
            
            # Append event to log file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")
    
    async def _check_compliance_violations(self, event: AuditEvent) -> None:
        """Check for compliance violations."""
        violations = []
        
        # Check GDPR violations
        if "GDPR" in event.compliance_tags:
            # Check for unauthorized data access
            if (event.event_type == AuditEventType.DATA_ACCESS and 
                event.outcome == "success" and 
                not event.details.get("authorized", True)):
                violations.append({
                    "type": "GDPR_UNAUTHORIZED_ACCESS",
                    "description": "Unauthorized access to personal data",
                    "event_id": event.event_id
                })
            
            # Check for data retention violations
            if (event.event_type == AuditEventType.DATA_ACCESS and
                event.details.get("data_age_days", 0) > self.gdpr_retention_days):
                violations.append({
                    "type": "GDPR_RETENTION_VIOLATION",
                    "description": "Access to data beyond retention period",
                    "event_id": event.event_id
                })
        
        # Check AI Act violations
        if "AI_ACT" in event.compliance_tags:
            # Check for high-risk AI system usage without proper safeguards
            if (event.details.get("high_risk_ai", False) and 
                not event.details.get("risk_mitigation_active", False)):
                violations.append({
                    "type": "AI_ACT_HIGH_RISK_VIOLATION",
                    "description": "High-risk AI system used without proper safeguards",
                    "event_id": event.event_id
                })
        
        # Log violations
        for violation in violations:
            await self.log_event(
                AuditEventType.COMPLIANCE_CHECK,
                f"Compliance violation detected: {violation['type']}",
                "failure",
                details=violation,
                severity=AuditSeverity.CRITICAL
            )
    
    async def generate_compliance_report(
        self,
        report_type: str = "comprehensive",
        period_days: int = 30
    ) -> ComplianceReport:
        """
        Generate compliance audit report.
        
        Args:
            report_type: Type of report to generate
            period_days: Number of days to include in report
            
        Returns:
            Compliance report
        """
        logger.info(f"Generating compliance report: {report_type}")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Filter events for the period
        period_events = [
            event for event in self.audit_events
            if start_time <= event.timestamp <= end_time
        ]
        
        # Categorize events
        gdpr_events = [e for e in period_events if "GDPR" in e.compliance_tags]
        security_events = [e for e in period_events if e.event_type == AuditEventType.SECURITY_EVENT]
        data_processing_events = [
            e for e in period_events 
            if e.event_type in [
                AuditEventType.VOICE_PROCESSING,
                AuditEventType.MODEL_INFERENCE,
                AuditEventType.DATA_ACCESS,
                AuditEventType.DATA_MODIFICATION
            ]
        ]
        
        # Find compliance violations
        compliance_violations = []
        for event in period_events:
            if (event.event_type == AuditEventType.COMPLIANCE_CHECK and 
                event.outcome == "failure"):
                compliance_violations.append(event.details)
        
        # Count critical and high-risk events
        critical_events = len([e for e in period_events if e.severity == AuditSeverity.CRITICAL])
        high_risk_events = len([e for e in period_events if e.risk_score >= 7.0])
        
        # Generate summary
        summary = {
            "period_days": period_days,
            "total_events": len(period_events),
            "gdpr_events": len(gdpr_events),
            "security_events": len(security_events),
            "data_processing_events": len(data_processing_events),
            "compliance_violations": len(compliance_violations),
            "average_risk_score": round(
                sum(e.risk_score for e in period_events) / len(period_events)
                if period_events else 0, 2
            ),
            "event_types": self._count_event_types(period_events),
            "outcomes": self._count_outcomes(period_events),
            "top_users": self._get_top_users(period_events),
            "compliance_score": self._calculate_compliance_score(period_events, compliance_violations)
        }
        
        report = ComplianceReport(
            report_id=f"compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            report_type=report_type,
            generated_at=datetime.utcnow(),
            period_start=start_time,
            period_end=end_time,
            total_events=len(period_events),
            critical_events=critical_events,
            high_risk_events=high_risk_events,
            compliance_violations=compliance_violations,
            gdpr_events=gdpr_events[:100],  # Limit for report size
            security_events=security_events[:100],
            data_processing_events=data_processing_events[:100],
            summary=summary
        )
        
        # Persist report
        await self._persist_report(report)
        
        logger.info(f"Compliance report generated: {report.report_id}")
        return report
    
    def _count_event_types(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by type."""
        counts = {}
        for event in events:
            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
    
    def _count_outcomes(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by outcome."""
        counts = {}
        for event in events:
            outcome = event.outcome
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts
    
    def _get_top_users(self, events: List[AuditEvent], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by activity."""
        user_counts = {}
        for event in events:
            if event.user_id:
                if event.user_id not in user_counts:
                    user_counts[event.user_id] = {"count": 0, "risk_score": 0}
                user_counts[event.user_id]["count"] += 1
                user_counts[event.user_id]["risk_score"] += event.risk_score
        
        # Sort by activity count
        sorted_users = sorted(
            user_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [
            {
                "user_id": user_id,
                "event_count": data["count"],
                "total_risk_score": round(data["risk_score"], 1),
                "avg_risk_score": round(data["risk_score"] / data["count"], 1)
            }
            for user_id, data in sorted_users[:limit]
        ]
    
    def _calculate_compliance_score(
        self, 
        events: List[AuditEvent], 
        violations: List[Dict[str, Any]]
    ) -> float:
        """Calculate compliance score (0-100)."""
        if not events:
            return 100.0
        
        # Base score
        score = 100.0
        
        # Deduct for violations
        violation_penalty = len(violations) * 10
        score -= violation_penalty
        
        # Deduct for high-risk events
        high_risk_events = [e for e in events if e.risk_score >= 8.0]
        risk_penalty = len(high_risk_events) * 2
        score -= risk_penalty
        
        # Deduct for failed events
        failed_events = [e for e in events if e.outcome in ["failure", "error"]]
        failure_penalty = len(failed_events) * 1
        score -= failure_penalty
        
        return max(0.0, round(score, 1))
    
    async def _persist_report(self, report: ComplianceReport) -> None:
        """Persist compliance report to storage."""
        try:
            report_file = self.audit_storage_path / f"{report.report_id}.json"
            
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to persist compliance report: {e}")
    
    def get_audit_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get audit events with filtering."""
        events = self.audit_events
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_audit_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get audit statistics for the specified period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        period_events = [
            e for e in self.audit_events
            if start_time <= e.timestamp <= end_time
        ]
        
        if not period_events:
            return {"message": "No audit events in the specified period"}
        
        return {
            "period_days": days,
            "total_events": len(period_events),
            "events_by_type": self._count_event_types(period_events),
            "events_by_severity": {
                severity.value: len([e for e in period_events if e.severity == severity])
                for severity in AuditSeverity
            },
            "events_by_outcome": self._count_outcomes(period_events),
            "average_risk_score": round(
                sum(e.risk_score for e in period_events) / len(period_events), 2
            ),
            "high_risk_events": len([e for e in period_events if e.risk_score >= 7.0]),
            "compliance_events": len([e for e in period_events if e.compliance_tags]),
            "unique_users": len(set(e.user_id for e in period_events if e.user_id)),
            "events_per_day": round(len(period_events) / days, 1)
        }
    
    async def cleanup_old_events(self) -> int:
        """Clean up old audit events based on retention policy."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.audit_retention_days)
        
        initial_count = len(self.audit_events)
        self.audit_events = [
            event for event in self.audit_events
            if event.timestamp > cutoff_date
        ]
        
        cleaned_count = initial_count - len(self.audit_events)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old audit events")
        
        return cleaned_count


# Global audit system instance
_audit_system: Optional[AuditSystem] = None


def get_audit_system() -> AuditSystem:
    """Get the global audit system instance."""
    global _audit_system
    if _audit_system is None:
        _audit_system = AuditSystem()
    return _audit_system


def set_audit_system(system: AuditSystem) -> None:
    """Set the global audit system instance."""
    global _audit_system
    _audit_system = system


# Audit decorator for automatic event logging
def audit_action(
    event_type: AuditEventType,
    action: str,
    resource: Optional[str] = None
):
    """Decorator to automatically audit function calls."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            audit_system = get_audit_system()
            
            try:
                result = await func(*args, **kwargs)
                await audit_system.log_event(
                    event_type=event_type,
                    action=action,
                    outcome="success",
                    resource=resource,
                    details={"function": func.__name__, "args_count": len(args)}
                )
                return result
            except Exception as e:
                await audit_system.log_event(
                    event_type=event_type,
                    action=action,
                    outcome="error",
                    resource=resource,
                    details={
                        "function": func.__name__,
                        "error": str(e),
                        "args_count": len(args)
                    }
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            audit_system = get_audit_system()
            
            try:
                result = func(*args, **kwargs)
                # For sync functions, we'll need to handle audit logging differently
                # This is a simplified version
                return result
            except Exception as e:
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
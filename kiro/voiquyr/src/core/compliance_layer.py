"""
Compliance Layer - Per-jurisdiction data handling enforcement.

Implements GDPR, UAE PDPL, India DPDP, and PDPA compliance rules
with jurisdiction-specific retention and erasure policies.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ComplianceJurisdiction(str, Enum):
    """Compliance jurisdictions."""
    EU = "EU"  # GDPR
    GULF = "Gulf"  # UAE PDPL
    INDIA = "India"  # DPDP
    SEA = "SEA"  # PDPA


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ComplianceRecord:
    """Per-call compliance record."""
    record_id: str
    call_id: str
    jurisdiction: ComplianceJurisdiction
    data_subject_id: str
    lawful_basis: str
    consent_obtained: bool
    retention_days: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ErasureRequest:
    """Data erasure request."""
    request_id: str
    data_subject_id: str
    jurisdiction: ComplianceJurisdiction
    requested_at: datetime = field(default_factory=datetime.utcnow)
    sla_deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0


@dataclass
class ComplianceSummaryReport:
    """Monthly compliance summary."""
    month: str
    jurisdiction: ComplianceJurisdiction
    total_calls: int
    consent_rate: float
    exceptions: int
    erasure_requests: int
    avg_response_time_hours: float


class ComplianceAlert(Exception):
    """Compliance alert exception."""
    def __init__(self, message: str, severity: AlertSeverity):
        self.message = message
        self.severity = severity
        super().__init__(message)


class ComplianceRuleSet:
    """Base class for jurisdiction-specific rules."""
    
    def __init__(self, jurisdiction: ComplianceJurisdiction):
        self.jurisdiction = jurisdiction
    
    def get_retention_days(self) -> int:
        """Get data retention period in days."""
        raise NotImplementedError
    
    def get_erasure_sla_days(self) -> int:
        """Get erasure request SLA in days."""
        raise NotImplementedError
    
    def validate_lawful_basis(self, basis: str) -> bool:
        """Validate lawful basis for processing."""
        raise NotImplementedError


class GDPRRuleSet(ComplianceRuleSet):
    """GDPR compliance rules (EU)."""
    
    def __init__(self):
        super().__init__(ComplianceJurisdiction.EU)
    
    def get_retention_days(self) -> int:
        return 365  # 1 year default
    
    def get_erasure_sla_days(self) -> int:
        return 30  # 30 days
    
    def validate_lawful_basis(self, basis: str) -> bool:
        valid_bases = ["consent", "contract", "legal_obligation", "vital_interests", 
                       "public_task", "legitimate_interests"]
        return basis in valid_bases


class UAEPDPLRuleSet(ComplianceRuleSet):
    """UAE PDPL compliance rules (Gulf)."""
    
    def __init__(self):
        super().__init__(ComplianceJurisdiction.GULF)
    
    def get_retention_days(self) -> int:
        return 365  # 1 year
    
    def get_erasure_sla_days(self) -> int:
        return 30  # 30 days
    
    def validate_lawful_basis(self, basis: str) -> bool:
        valid_bases = ["consent", "contract", "legal_requirement"]
        return basis in valid_bases


class INDIADPDPRuleSet(ComplianceRuleSet):
    """India DPDP compliance rules."""
    
    def __init__(self):
        super().__init__(ComplianceJurisdiction.INDIA)
    
    def get_retention_days(self) -> int:
        return 180  # 6 months
    
    def get_erasure_sla_days(self) -> int:
        return 7  # 7 days (stricter)
    
    def validate_lawful_basis(self, basis: str) -> bool:
        valid_bases = ["consent", "legitimate_use"]
        return basis in valid_bases


class PDPARuleSet(ComplianceRuleSet):
    """PDPA compliance rules (SEA)."""
    
    def __init__(self):
        super().__init__(ComplianceJurisdiction.SEA)
    
    def get_retention_days(self) -> int:
        return 365  # 1 year
    
    def get_erasure_sla_days(self) -> int:
        return 30  # 30 days
    
    def validate_lawful_basis(self, basis: str) -> bool:
        valid_bases = ["consent", "contract", "legal_obligation"]
        return basis in valid_bases


# Jurisdiction to rule-set mapping
JURISDICTION_RULE_MAP = {
    ComplianceJurisdiction.EU: GDPRRuleSet,
    ComplianceJurisdiction.GULF: UAEPDPLRuleSet,
    ComplianceJurisdiction.INDIA: INDIADPDPRuleSet,
    ComplianceJurisdiction.SEA: PDPARuleSet,
}


class ComplianceLayer:
    """Compliance enforcement layer."""
    
    def __init__(self):
        self.records: Dict[str, ComplianceRecord] = {}
        self.erasure_requests: Dict[str, ErasureRequest] = {}
        self.rule_sets: Dict[ComplianceJurisdiction, ComplianceRuleSet] = {
            j: rule_class() for j, rule_class in JURISDICTION_RULE_MAP.items()
        }
    
    def validate_jurisdiction_match(self, 
                                    call_jurisdiction: ComplianceJurisdiction,
                                    expected_jurisdiction: ComplianceJurisdiction) -> bool:
        """Validate jurisdiction match."""
        if call_jurisdiction != expected_jurisdiction:
            raise ComplianceAlert(
                f"Jurisdiction mismatch: call={call_jurisdiction}, expected={expected_jurisdiction}",
                AlertSeverity.CRITICAL
            )
        return True
    
    async def process_call(self,
                          call_id: str,
                          jurisdiction: ComplianceJurisdiction,
                          data_subject_id: str,
                          lawful_basis: str,
                          consent_obtained: bool,
                          metadata: Dict = None) -> ComplianceRecord:
        """Process call and create compliance record."""
        # Get rule set for jurisdiction
        rule_set = self.rule_sets.get(jurisdiction)
        if not rule_set:
            raise ComplianceAlert(
                f"No rule set for jurisdiction: {jurisdiction}",
                AlertSeverity.CRITICAL
            )
        
        # Validate lawful basis
        if not rule_set.validate_lawful_basis(lawful_basis):
            raise ComplianceAlert(
                f"Invalid lawful basis '{lawful_basis}' for {jurisdiction}",
                AlertSeverity.CRITICAL
            )
        
        # Create compliance record
        retention_days = rule_set.get_retention_days()
        record = ComplianceRecord(
            record_id=f"rec-{call_id}",
            call_id=call_id,
            jurisdiction=jurisdiction,
            data_subject_id=data_subject_id,
            lawful_basis=lawful_basis,
            consent_obtained=consent_obtained,
            retention_days=retention_days,
            expires_at=datetime.utcnow() + timedelta(days=retention_days),
            metadata=metadata or {}
        )
        
        # Store record (in production: PostgreSQL with row-level security)
        self.records[record.record_id] = record
        
        logger.info(f"Compliance record created: {record.record_id} ({jurisdiction})")
        return record
    
    async def handle_erasure_request(self,
                                     data_subject_id: str,
                                     jurisdiction: ComplianceJurisdiction) -> ErasureRequest:
        """Handle data erasure request."""
        rule_set = self.rule_sets.get(jurisdiction)
        if not rule_set:
            raise ComplianceAlert(
                f"No rule set for jurisdiction: {jurisdiction}",
                AlertSeverity.CRITICAL
            )
        
        # Create erasure request
        sla_days = rule_set.get_erasure_sla_days()
        request = ErasureRequest(
            request_id=f"erase-{data_subject_id}-{datetime.utcnow().timestamp()}",
            data_subject_id=data_subject_id,
            jurisdiction=jurisdiction,
            sla_deadline=datetime.utcnow() + timedelta(days=sla_days)
        )
        
        self.erasure_requests[request.request_id] = request
        
        # Schedule deletion job with retry
        await self._schedule_erasure(request)
        
        logger.info(f"Erasure request created: {request.request_id} (SLA: {sla_days} days)")
        return request
    
    async def _schedule_erasure(self, request: ErasureRequest, retry: int = 0):
        """Schedule erasure with retry logic."""
        max_retries = 3
        
        try:
            # Delete all records for data subject
            deleted_count = 0
            for record_id, record in list(self.records.items()):
                if record.data_subject_id == request.data_subject_id:
                    del self.records[record_id]
                    deleted_count += 1
            
            # Mark request as completed
            request.completed_at = datetime.utcnow()
            logger.info(f"Erasure completed: {request.request_id} ({deleted_count} records)")
            
        except Exception as e:
            logger.error(f"Erasure failed (attempt {retry + 1}): {e}")
            
            if retry < max_retries:
                request.retry_count = retry + 1
                # Exponential backoff (simplified)
                await self._schedule_erasure(request, retry + 1)
            else:
                raise ComplianceAlert(
                    f"Erasure failed after {max_retries} retries",
                    AlertSeverity.CRITICAL
                )
    
    def generate_monthly_report(self, 
                                month: str,
                                jurisdiction: ComplianceJurisdiction) -> ComplianceSummaryReport:
        """Generate monthly compliance summary report."""
        # Filter records for month and jurisdiction
        records = [
            r for r in self.records.values()
            if r.jurisdiction == jurisdiction and r.created_at.strftime("%Y-%m") == month
        ]
        
        total_calls = len(records)
        consent_count = sum(1 for r in records if r.consent_obtained)
        consent_rate = consent_count / total_calls if total_calls > 0 else 0.0
        
        # Count exceptions (records without consent where required)
        exceptions = sum(1 for r in records if not r.consent_obtained and r.lawful_basis == "consent")
        
        # Count erasure requests
        erasure_count = sum(
            1 for req in self.erasure_requests.values()
            if req.jurisdiction == jurisdiction and req.requested_at.strftime("%Y-%m") == month
        )
        
        # Calculate average response time
        completed_requests = [
            req for req in self.erasure_requests.values()
            if req.jurisdiction == jurisdiction and req.completed_at
        ]
        avg_response_hours = 0.0
        if completed_requests:
            total_hours = sum(
                (req.completed_at - req.requested_at).total_seconds() / 3600
                for req in completed_requests
            )
            avg_response_hours = total_hours / len(completed_requests)
        
        return ComplianceSummaryReport(
            month=month,
            jurisdiction=jurisdiction,
            total_calls=total_calls,
            consent_rate=consent_rate,
            exceptions=exceptions,
            erasure_requests=erasure_count,
            avg_response_time_hours=avg_response_hours
        )


# Global instance
_compliance_layer: Optional[ComplianceLayer] = None


def get_compliance_layer() -> ComplianceLayer:
    """Get global compliance layer instance."""
    global _compliance_layer
    if _compliance_layer is None:
        _compliance_layer = ComplianceLayer()
    return _compliance_layer


def set_compliance_layer(layer: ComplianceLayer) -> None:
    """Set global compliance layer instance."""
    global _compliance_layer
    _compliance_layer = layer

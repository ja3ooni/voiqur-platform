"""
Data Protection System

Data anonymization and privacy protection features for the EUVoice AI Platform
to ensure GDPR compliance and data privacy.
"""

import asyncio
import logging
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import base64

logger = logging.getLogger(__name__)


class DataType(str, Enum):
    """Types of data for protection."""
    PII = "pii"  # Personally Identifiable Information
    AUDIO = "audio"
    TEXT = "text"
    BIOMETRIC = "biometric"
    BEHAVIORAL = "behavioral"
    LOCATION = "location"
    DEVICE = "device"
    SESSION = "session"


class ProtectionLevel(str, Enum):
    """Data protection levels."""
    NONE = "none"
    PSEUDONYMIZATION = "pseudonymization"
    ANONYMIZATION = "anonymization"
    ENCRYPTION = "encryption"
    DELETION = "deletion"


class ConsentStatus(str, Enum):
    """Data processing consent status."""
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


@dataclass
class DataSubject:
    """Data subject information."""
    subject_id: str
    email: Optional[str]
    consent_status: ConsentStatus
    consent_date: Optional[datetime]
    consent_expiry: Optional[datetime]
    data_categories: List[DataType]
    processing_purposes: List[str]
    retention_period_days: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject_id": self.subject_id,
            "email": self.email,
            "consent_status": self.consent_status.value,
            "consent_date": self.consent_date.isoformat() if self.consent_date else None,
            "consent_expiry": self.consent_expiry.isoformat() if self.consent_expiry else None,
            "data_categories": [cat.value for cat in self.data_categories],
            "processing_purposes": self.processing_purposes,
            "retention_period_days": self.retention_period_days,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class DataProcessingRecord:
    """Data processing activity record."""
    record_id: str
    subject_id: str
    data_type: DataType
    processing_purpose: str
    legal_basis: str
    data_source: str
    processing_date: datetime
    retention_date: datetime
    protection_level: ProtectionLevel
    anonymized: bool
    encrypted: bool
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "subject_id": self.subject_id,
            "data_type": self.data_type.value,
            "processing_purpose": self.processing_purpose,
            "legal_basis": self.legal_basis,
            "data_source": self.data_source,
            "processing_date": self.processing_date.isoformat(),
            "retention_date": self.retention_date.isoformat(),
            "protection_level": self.protection_level.value,
            "anonymized": self.anonymized,
            "encrypted": self.encrypted,
            "metadata": self.metadata
        }


class DataProtectionSystem:
    """
    Comprehensive data protection system for GDPR compliance.
    
    Provides:
    - Data anonymization and pseudonymization
    - PII detection and masking
    - Consent management
    - Data retention management
    - Right to be forgotten implementation
    - Data processing records
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data protection system."""
        self.config = config or {}
        
        # Data storage
        self.data_subjects: Dict[str, DataSubject] = {}
        self.processing_records: List[DataProcessingRecord] = []
        
        # Encryption key (in production, use proper key management)
        self.encryption_key = self.config.get("encryption_key", secrets.token_bytes(32))
        
        # PII detection patterns
        self.pii_patterns = self._initialize_pii_patterns()
        
        # Anonymization mappings
        self.anonymization_mappings: Dict[str, str] = {}
        
        # Default retention periods (days)
        self.default_retention_periods = {
            DataType.AUDIO: 365,  # 1 year
            DataType.TEXT: 365,   # 1 year
            DataType.PII: 2555,   # 7 years
            DataType.BIOMETRIC: 90,  # 3 months
            DataType.BEHAVIORAL: 730,  # 2 years
            DataType.LOCATION: 30,   # 1 month
            DataType.DEVICE: 365,    # 1 year
            DataType.SESSION: 30     # 1 month
        }
        
        logger.info("Data Protection System initialized")
    
    def _initialize_pii_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize PII detection patterns."""
        return {
            "email": [
                {
                    "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "replacement": "[EMAIL]"
                }
            ],
            "phone": [
                {
                    "pattern": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
                    "replacement": "[PHONE]"
                },
                {
                    "pattern": r'\b(?:\+33|0)[1-9](?:[0-9]{8})\b',  # French phone
                    "replacement": "[PHONE]"
                }
            ],
            "ssn": [
                {
                    "pattern": r'\b\d{3}-\d{2}-\d{4}\b',  # US SSN
                    "replacement": "[SSN]"
                }
            ],
            "credit_card": [
                {
                    "pattern": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13})\b',
                    "replacement": "[CREDIT_CARD]"
                }
            ],
            "ip_address": [
                {
                    "pattern": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                    "replacement": "[IP_ADDRESS]"
                }
            ],
            "name": [
                {
                    "pattern": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Simple name pattern
                    "replacement": "[NAME]"
                }
            ]
        }
    
    async def register_data_subject(
        self,
        subject_id: str,
        email: Optional[str] = None,
        consent_purposes: Optional[List[str]] = None,
        data_categories: Optional[List[DataType]] = None,
        retention_period_days: Optional[int] = None
    ) -> DataSubject:
        """
        Register a new data subject.
        
        Args:
            subject_id: Unique identifier for the data subject
            email: Email address (optional)
            consent_purposes: List of processing purposes
            data_categories: List of data categories
            retention_period_days: Custom retention period
            
        Returns:
            Created data subject record
        """
        now = datetime.utcnow()
        
        # Default values
        if consent_purposes is None:
            consent_purposes = ["voice_processing", "service_improvement"]
        
        if data_categories is None:
            data_categories = [DataType.AUDIO, DataType.TEXT]
        
        if retention_period_days is None:
            retention_period_days = max(
                self.default_retention_periods.get(cat, 365) 
                for cat in data_categories
            )
        
        # Create data subject
        data_subject = DataSubject(
            subject_id=subject_id,
            email=email,
            consent_status=ConsentStatus.GRANTED,
            consent_date=now,
            consent_expiry=now + timedelta(days=365),  # 1 year consent validity
            data_categories=data_categories,
            processing_purposes=consent_purposes,
            retention_period_days=retention_period_days,
            created_at=now,
            updated_at=now
        )
        
        self.data_subjects[subject_id] = data_subject
        
        logger.info(f"Data subject registered: {subject_id}")
        return data_subject
    
    async def withdraw_consent(self, subject_id: str) -> bool:
        """
        Withdraw consent for a data subject.
        
        Args:
            subject_id: Data subject identifier
            
        Returns:
            True if consent was withdrawn successfully
        """
        if subject_id not in self.data_subjects:
            logger.warning(f"Data subject not found: {subject_id}")
            return False
        
        data_subject = self.data_subjects[subject_id]
        data_subject.consent_status = ConsentStatus.WITHDRAWN
        data_subject.updated_at = datetime.utcnow()
        
        # Log processing record
        await self._log_processing_record(
            subject_id=subject_id,
            data_type=DataType.PII,
            processing_purpose="consent_withdrawal",
            legal_basis="data_subject_request",
            data_source="consent_management"
        )
        
        logger.info(f"Consent withdrawn for subject: {subject_id}")
        return True
    
    async def anonymize_text(self, text: str, protection_level: ProtectionLevel = ProtectionLevel.PSEUDONYMIZATION) -> str:
        """
        Anonymize text by detecting and masking PII.
        
        Args:
            text: Text to anonymize
            protection_level: Level of protection to apply
            
        Returns:
            Anonymized text
        """
        if protection_level == ProtectionLevel.NONE:
            return text
        
        anonymized_text = text
        
        # Apply PII patterns
        for pii_type, patterns in self.pii_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                replacement = pattern_info["replacement"]
                
                if protection_level == ProtectionLevel.PSEUDONYMIZATION:
                    # Use consistent pseudonyms
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        # re.findall returns tuples when pattern has groups; join them
                        if isinstance(match, tuple):
                            match = "".join(match)
                        if match not in self.anonymization_mappings:
                            self.anonymization_mappings[match] = f"{replacement}_{len(self.anonymization_mappings)}"
                        anonymized_text = anonymized_text.replace(match, self.anonymization_mappings[match])
                else:
                    # Full anonymization
                    anonymized_text = re.sub(pattern, replacement, anonymized_text)
        
        return anonymized_text
    
    async def anonymize_audio_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize audio metadata.
        
        Args:
            metadata: Audio metadata dictionary
            
        Returns:
            Anonymized metadata
        """
        anonymized_metadata = metadata.copy()
        
        # Remove or anonymize sensitive fields
        sensitive_fields = [
            "user_id", "session_id", "device_id", "ip_address",
            "location", "timestamp", "user_agent"
        ]
        
        for field in sensitive_fields:
            if field in anonymized_metadata:
                if field == "timestamp":
                    # Round timestamp to hour
                    if isinstance(anonymized_metadata[field], str):
                        dt = datetime.fromisoformat(anonymized_metadata[field].replace('Z', '+00:00'))
                        anonymized_metadata[field] = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                else:
                    # Hash other sensitive fields
                    original_value = str(anonymized_metadata[field])
                    hashed_value = hashlib.sha256(original_value.encode()).hexdigest()[:8]
                    anonymized_metadata[field] = f"anon_{hashed_value}"
        
        return anonymized_metadata
    
    async def encrypt_data(self, data: Union[str, bytes]) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Simple XOR encryption (in production, use proper encryption like AES)
        encrypted = bytes(a ^ b for a, b in zip(data, (self.encryption_key * (len(data) // len(self.encryption_key) + 1))[:len(data)]))
        
        return base64.b64encode(encrypted).decode('utf-8')
    
    async def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        
        # Simple XOR decryption
        decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, (self.encryption_key * (len(encrypted_bytes) // len(self.encryption_key) + 1))[:len(encrypted_bytes)]))
        
        return decrypted.decode('utf-8')
    
    async def process_data_subject_request(
        self,
        subject_id: str,
        request_type: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process data subject rights requests (GDPR Article 15-22).
        
        Args:
            subject_id: Data subject identifier
            request_type: Type of request (access, rectification, erasure, portability, etc.)
            details: Additional request details
            
        Returns:
            Request processing result
        """
        if subject_id not in self.data_subjects:
            return {
                "status": "error",
                "message": "Data subject not found"
            }
        
        data_subject = self.data_subjects[subject_id]
        result = {"status": "success", "request_type": request_type}
        
        if request_type == "access":
            # Right of access (Article 15)
            result["data"] = {
                "subject_info": data_subject.to_dict(),
                "processing_records": [
                    record.to_dict() for record in self.processing_records
                    if record.subject_id == subject_id
                ]
            }
        
        elif request_type == "rectification":
            # Right to rectification (Article 16)
            if details and "updates" in details:
                for field, value in details["updates"].items():
                    if hasattr(data_subject, field):
                        setattr(data_subject, field, value)
                data_subject.updated_at = datetime.utcnow()
                result["message"] = "Data updated successfully"
        
        elif request_type == "erasure":
            # Right to erasure (Article 17)
            await self._erase_subject_data(subject_id)
            result["message"] = "Data erased successfully"
        
        elif request_type == "portability":
            # Right to data portability (Article 20)
            result["data"] = {
                "format": "JSON",
                "subject_data": data_subject.to_dict(),
                "processing_history": [
                    record.to_dict() for record in self.processing_records
                    if record.subject_id == subject_id
                ]
            }
        
        elif request_type == "restriction":
            # Right to restriction of processing (Article 18)
            data_subject.consent_status = ConsentStatus.PENDING
            data_subject.updated_at = datetime.utcnow()
            result["message"] = "Processing restricted"
        
        elif request_type == "objection":
            # Right to object (Article 21)
            await self.withdraw_consent(subject_id)
            result["message"] = "Objection processed, consent withdrawn"
        
        # Log the request
        await self._log_processing_record(
            subject_id=subject_id,
            data_type=DataType.PII,
            processing_purpose=f"data_subject_request_{request_type}",
            legal_basis="data_subject_request",
            data_source="privacy_management",
            metadata={"request_details": details or {}}
        )
        
        logger.info(f"Processed data subject request: {request_type} for {subject_id}")
        return result
    
    async def _erase_subject_data(self, subject_id: str) -> None:
        """Erase all data for a data subject."""
        # Remove data subject record
        if subject_id in self.data_subjects:
            del self.data_subjects[subject_id]
        
        # Remove processing records (or mark as erased)
        self.processing_records = [
            record for record in self.processing_records
            if record.subject_id != subject_id
        ]
        
        # Remove anonymization mappings (if any contain subject data)
        # This is a simplified approach - in practice, you'd need more sophisticated tracking
        
        logger.info(f"Erased all data for subject: {subject_id}")
    
    async def _log_processing_record(
        self,
        subject_id: str,
        data_type: DataType,
        processing_purpose: str,
        legal_basis: str,
        data_source: str,
        protection_level: ProtectionLevel = ProtectionLevel.NONE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataProcessingRecord:
        """Log a data processing activity."""
        now = datetime.utcnow()
        
        # Determine retention date
        retention_days = self.default_retention_periods.get(data_type, 365)
        if subject_id in self.data_subjects:
            retention_days = self.data_subjects[subject_id].retention_period_days
        
        record = DataProcessingRecord(
            record_id=f"proc_{now.strftime('%Y%m%d_%H%M%S')}_{len(self.processing_records)}",
            subject_id=subject_id,
            data_type=data_type,
            processing_purpose=processing_purpose,
            legal_basis=legal_basis,
            data_source=data_source,
            processing_date=now,
            retention_date=now + timedelta(days=retention_days),
            protection_level=protection_level,
            anonymized=protection_level in [ProtectionLevel.ANONYMIZATION, ProtectionLevel.PSEUDONYMIZATION],
            encrypted=protection_level == ProtectionLevel.ENCRYPTION,
            metadata=metadata or {}
        )
        
        self.processing_records.append(record)
        return record
    
    async def check_data_retention(self) -> List[str]:
        """
        Check for data that has exceeded retention periods.
        
        Returns:
            List of subject IDs with expired data
        """
        now = datetime.utcnow()
        expired_subjects = []
        
        for subject_id, data_subject in self.data_subjects.items():
            # Check if consent has expired
            if (data_subject.consent_expiry and 
                data_subject.consent_expiry < now and
                data_subject.consent_status == ConsentStatus.GRANTED):
                data_subject.consent_status = ConsentStatus.EXPIRED
                data_subject.updated_at = now
                expired_subjects.append(subject_id)
        
        # Check processing records for retention expiry
        expired_records = [
            record for record in self.processing_records
            if record.retention_date < now
        ]
        
        if expired_records:
            logger.info(f"Found {len(expired_records)} expired processing records")
            # In practice, you would archive or delete these records
        
        return expired_subjects
    
    def get_privacy_dashboard(self) -> Dict[str, Any]:
        """Get privacy and data protection dashboard data."""
        now = datetime.utcnow()
        
        # Count subjects by consent status
        consent_counts = {}
        for status in ConsentStatus:
            consent_counts[status.value] = len([
                s for s in self.data_subjects.values()
                if s.consent_status == status
            ])
        
        # Count processing records by data type
        processing_counts = {}
        for data_type in DataType:
            processing_counts[data_type.value] = len([
                r for r in self.processing_records
                if r.data_type == data_type
            ])
        
        # Calculate protection statistics
        protected_records = len([
            r for r in self.processing_records
            if r.protection_level != ProtectionLevel.NONE
        ])
        
        protection_rate = (
            (protected_records / len(self.processing_records) * 100)
            if self.processing_records else 0
        )
        
        # Check upcoming expirations
        upcoming_expiry = len([
            s for s in self.data_subjects.values()
            if (s.consent_expiry and 
                s.consent_expiry < now + timedelta(days=30) and
                s.consent_status == ConsentStatus.GRANTED)
        ])
        
        return {
            "total_subjects": len(self.data_subjects),
            "consent_status_breakdown": consent_counts,
            "total_processing_records": len(self.processing_records),
            "processing_by_data_type": processing_counts,
            "protection_statistics": {
                "protected_records": protected_records,
                "protection_rate_percent": round(protection_rate, 1),
                "anonymized_records": len([
                    r for r in self.processing_records if r.anonymized
                ]),
                "encrypted_records": len([
                    r for r in self.processing_records if r.encrypted
                ])
            },
            "compliance_alerts": {
                "upcoming_consent_expiry": upcoming_expiry,
                "expired_consents": consent_counts.get("expired", 0)
            },
            "last_updated": now.isoformat()
        }
    
    def get_subject_data_summary(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Get data summary for a specific subject."""
        if subject_id not in self.data_subjects:
            return None
        
        data_subject = self.data_subjects[subject_id]
        subject_records = [
            r for r in self.processing_records
            if r.subject_id == subject_id
        ]
        
        return {
            "subject_info": data_subject.to_dict(),
            "processing_summary": {
                "total_records": len(subject_records),
                "data_types": list(set(r.data_type.value for r in subject_records)),
                "processing_purposes": list(set(r.processing_purpose for r in subject_records)),
                "protection_levels": list(set(r.protection_level.value for r in subject_records)),
                "latest_processing": max(r.processing_date for r in subject_records).isoformat() if subject_records else None
            },
            "compliance_status": {
                "consent_valid": data_subject.consent_status == ConsentStatus.GRANTED,
                "consent_expiry": data_subject.consent_expiry.isoformat() if data_subject.consent_expiry else None,
                "retention_compliant": all(
                    r.retention_date > datetime.utcnow() for r in subject_records
                )
            }
        }


# Global data protection system instance
_data_protection_system: Optional[DataProtectionSystem] = None


def get_data_protection_system() -> DataProtectionSystem:
    """Get the global data protection system instance."""
    global _data_protection_system
    if _data_protection_system is None:
        _data_protection_system = DataProtectionSystem()
    return _data_protection_system


def set_data_protection_system(system: DataProtectionSystem) -> None:
    """Set the global data protection system instance."""
    global _data_protection_system
    _data_protection_system = system
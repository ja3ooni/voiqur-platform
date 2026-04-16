"""
Refund Engine

Automatic quality-based refund system for failed interactions.
Implements Requirement 13.3 - Automatic refunds for failed interactions.
"""

import logging
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class RefundReason(Enum):
    """Reasons for automatic refunds"""
    LLM_HALLUCINATION = "llm_hallucination"
    LLM_TIMEOUT = "llm_timeout"
    STT_LOW_CONFIDENCE = "stt_low_confidence"
    TTS_GENERATION_FAILED = "tts_generation_failed"
    TELEPHONY_QUALITY = "telephony_quality"
    SYSTEM_ERROR = "system_error"
    LOW_QUALITY_SCORE = "low_quality_score"
    CUSTOMER_COMPLAINT = "customer_complaint"


class RefundStatus(Enum):
    """Status of refund processing"""
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class RefundRecord:
    """Record of a refund transaction"""
    refund_id: str
    session_id: str
    user_id: str
    original_amount: Decimal
    refund_amount: Decimal
    currency: str
    reason: RefundReason
    status: RefundStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['reason'] = self.reason.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.processed_at:
            data['processed_at'] = self.processed_at.isoformat()
        data['original_amount'] = str(self.original_amount)
        data['refund_amount'] = str(self.refund_amount)
        return data


class RefundEngine:
    """
    Automatic refund engine for quality-based refunds
    
    Features:
    - Automatic detection of refund-worthy issues
    - Quality score-based refund calculation
    - 24-hour automatic processing
    - Detailed explanations
    """
    
    # Quality score thresholds for refunds
    QUALITY_THRESHOLDS = {
        "full_refund": 0.3,  # <30% quality = full refund
        "partial_refund": 0.7,  # 30-70% quality = partial refund
        "no_refund": 1.0,  # >70% quality = no refund
    }
    
    # Refund percentages by reason
    REFUND_PERCENTAGES = {
        RefundReason.LLM_HALLUCINATION: Decimal("1.00"),  # 100%
        RefundReason.LLM_TIMEOUT: Decimal("1.00"),  # 100%
        RefundReason.STT_LOW_CONFIDENCE: Decimal("0.50"),  # 50%
        RefundReason.TTS_GENERATION_FAILED: Decimal("1.00"),  # 100%
        RefundReason.TELEPHONY_QUALITY: Decimal("0.50"),  # 50%
        RefundReason.SYSTEM_ERROR: Decimal("1.00"),  # 100%
        RefundReason.LOW_QUALITY_SCORE: Decimal("0.00"),  # Calculated
        RefundReason.CUSTOMER_COMPLAINT: Decimal("1.00"),  # 100%
    }
    
    # Processing time limit (24 hours)
    PROCESSING_TIME_LIMIT = timedelta(hours=24)
    
    def __init__(self):
        """Initialize refund engine"""
        self.refund_queue: List[RefundRecord] = []
        self.processed_refunds: List[RefundRecord] = []
        self.logger = logging.getLogger(__name__)
    
    def should_refund(
        self,
        quality_score: float,
        error_type: Optional[str] = None
    ) -> tuple[bool, Optional[RefundReason]]:
        """
        Determine if a session qualifies for refund
        
        Args:
            quality_score: Quality score (0.0-1.0)
            error_type: Type of error if any
            
        Returns:
            Tuple of (should_refund, reason)
        """
        # Check for specific error types
        if error_type:
            error_mapping = {
                "hallucination": RefundReason.LLM_HALLUCINATION,
                "timeout": RefundReason.LLM_TIMEOUT,
                "low_confidence": RefundReason.STT_LOW_CONFIDENCE,
                "tts_failed": RefundReason.TTS_GENERATION_FAILED,
                "poor_quality": RefundReason.TELEPHONY_QUALITY,
                "system_error": RefundReason.SYSTEM_ERROR,
            }
            
            reason = error_mapping.get(error_type)
            if reason:
                return True, reason
        
        # Check quality score
        if quality_score < self.QUALITY_THRESHOLDS["full_refund"]:
            return True, RefundReason.LOW_QUALITY_SCORE
        elif quality_score < self.QUALITY_THRESHOLDS["partial_refund"]:
            return True, RefundReason.LOW_QUALITY_SCORE
        
        return False, None
    
    def calculate_refund_amount(
        self,
        original_amount: Decimal,
        reason: RefundReason,
        quality_score: float = 1.0
    ) -> Decimal:
        """
        Calculate refund amount based on reason and quality
        
        Args:
            original_amount: Original charge amount
            reason: Reason for refund
            quality_score: Quality score (0.0-1.0)
            
        Returns:
            Refund amount
        """
        if reason == RefundReason.LOW_QUALITY_SCORE:
            # Calculate based on quality score
            if quality_score < self.QUALITY_THRESHOLDS["full_refund"]:
                refund_pct = Decimal("1.00")  # 100%
            else:
                # Partial refund: linear scale from 30-70% quality
                refund_pct = Decimal(str(
                    1.0 - (quality_score - 0.3) / 0.4
                ))
        else:
            refund_pct = self.REFUND_PERCENTAGES.get(
                reason,
                Decimal("0.00")
            )
        
        refund_amount = (original_amount * refund_pct).quantize(
            Decimal("0.01")
        )
        
        return refund_amount
    
    def create_refund(
        self,
        session_id: str,
        user_id: str,
        original_amount: Decimal,
        currency: str,
        reason: RefundReason,
        quality_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RefundRecord:
        """
        Create a refund record
        
        Args:
            session_id: Session ID
            user_id: User ID
            original_amount: Original charge amount
            currency: Currency code
            reason: Refund reason
            quality_score: Quality score
            metadata: Additional metadata
            
        Returns:
            Created refund record
        """
        refund_amount = self.calculate_refund_amount(
            original_amount,
            reason,
            quality_score
        )
        
        explanation = self._generate_explanation(
            reason,
            quality_score,
            refund_amount,
            original_amount
        )
        
        refund = RefundRecord(
            refund_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            original_amount=original_amount,
            refund_amount=refund_amount,
            currency=currency,
            reason=reason,
            status=RefundStatus.PENDING,
            created_at=datetime.utcnow(),
            explanation=explanation,
            metadata=metadata or {}
        )
        
        self.refund_queue.append(refund)
        
        self.logger.info(
            f"Created refund {refund.refund_id} for session {session_id}: "
            f"{refund_amount} {currency} (reason: {reason.value})"
        )
        
        return refund
    
    def _generate_explanation(
        self,
        reason: RefundReason,
        quality_score: float,
        refund_amount: Decimal,
        original_amount: Decimal
    ) -> str:
        """Generate human-readable explanation for refund"""
        explanations = {
            RefundReason.LLM_HALLUCINATION: (
                "The AI assistant provided inaccurate or hallucinated information "
                "during your conversation. We've issued a full refund."
            ),
            RefundReason.LLM_TIMEOUT: (
                "The AI assistant failed to respond in a timely manner. "
                "We've issued a full refund for this interaction."
            ),
            RefundReason.STT_LOW_CONFIDENCE: (
                "Speech recognition quality was below our standards. "
                "We've issued a partial refund."
            ),
            RefundReason.TTS_GENERATION_FAILED: (
                "Voice synthesis failed during your interaction. "
                "We've issued a full refund."
            ),
            RefundReason.TELEPHONY_QUALITY: (
                "Call quality was below acceptable standards. "
                "We've issued a partial refund."
            ),
            RefundReason.SYSTEM_ERROR: (
                "A system error occurred during your interaction. "
                "We've issued a full refund."
            ),
            RefundReason.LOW_QUALITY_SCORE: (
                f"The interaction quality score was {quality_score:.1%}, "
                f"below our standards. We've issued a "
                f"{(refund_amount/original_amount):.0%} refund."
            ),
            RefundReason.CUSTOMER_COMPLAINT: (
                "Based on your feedback, we've issued a full refund "
                "for this interaction."
            ),
        }
        
        return explanations.get(reason, "Refund issued due to quality issues.")
    
    async def process_refund(self, refund: RefundRecord) -> bool:
        """
        Process a refund (integrate with payment gateway)
        
        Args:
            refund: Refund record to process
            
        Returns:
            True if successful
        """
        try:
            refund.status = RefundStatus.PROCESSING
            
            # Process refund via Stripe if transaction ID is available
            transaction_id = refund.metadata.get("original_transaction_id")
            if transaction_id and transaction_id != "tx_mock":
                from .stripe_service import StripeService
                stripe_svc = StripeService()
                success = await stripe_svc.process_refund(
                    transaction_id=transaction_id,
                    amount=refund.refund_amount,
                    reason="quality_issue"
                )
            else:
                # No real transaction to refund — mark as completed (test/dev mode)
                success = True
            
            if success:
                refund.status = RefundStatus.COMPLETED
            refund.processed_at = datetime.utcnow()
            
            self.processed_refunds.append(refund)
            self.refund_queue.remove(refund)
            
            self.logger.info(
                f"Processed refund {refund.refund_id}: "
                f"{refund.refund_amount} {refund.currency}"
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to process refund {refund.refund_id}: {e}")
            refund.status = RefundStatus.FAILED
            return False
    
    async def process_pending_refunds(self) -> Dict[str, int]:
        """
        Process all pending refunds
        
        Returns:
            Statistics on processed refunds
        """
        stats = {
            "processed": 0,
            "failed": 0,
            "total_amount": Decimal("0.00")
        }
        
        # Process refunds older than 24 hours first
        now = datetime.utcnow()
        overdue = [
            r for r in self.refund_queue
            if (now - r.created_at) > self.PROCESSING_TIME_LIMIT
        ]
        
        for refund in overdue:
            success = await self.process_refund(refund)
            if success:
                stats["processed"] += 1
                stats["total_amount"] += refund.refund_amount
            else:
                stats["failed"] += 1
        
        self.logger.info(
            f"Processed {stats['processed']} refunds, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    def get_refund_status(self, refund_id: str) -> Optional[RefundRecord]:
        """
        Get status of a refund
        
        Args:
            refund_id: Refund ID
            
        Returns:
            Refund record or None
        """
        # Check queue
        for refund in self.refund_queue:
            if refund.refund_id == refund_id:
                return refund
        
        # Check processed
        for refund in self.processed_refunds:
            if refund.refund_id == refund_id:
                return refund
        
        return None
    
    def get_user_refunds(
        self,
        user_id: str,
        days: int = 30
    ) -> List[RefundRecord]:
        """
        Get all refunds for a user
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of refund records
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        refunds = []
        
        # Check queue
        refunds.extend([
            r for r in self.refund_queue
            if r.user_id == user_id and r.created_at >= cutoff
        ])
        
        # Check processed
        refunds.extend([
            r for r in self.processed_refunds
            if r.user_id == user_id and r.created_at >= cutoff
        ])
        
        return sorted(refunds, key=lambda x: x.created_at, reverse=True)
    
    def get_refund_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get refund statistics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Statistics dictionary
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_refunds = [
            r for r in self.processed_refunds
            if r.created_at >= cutoff
        ]
        
        total_refunded = sum(r.refund_amount for r in recent_refunds)
        
        # Group by reason
        by_reason = {}
        for refund in recent_refunds:
            reason = refund.reason.value
            if reason not in by_reason:
                by_reason[reason] = {
                    "count": 0,
                    "amount": Decimal("0.00")
                }
            by_reason[reason]["count"] += 1
            by_reason[reason]["amount"] += refund.refund_amount
        
        return {
            "period_days": days,
            "total_refunds": len(recent_refunds),
            "total_amount": str(total_refunded),
            "by_reason": {
                k: {"count": v["count"], "amount": str(v["amount"])}
                for k, v in by_reason.items()
            },
            "pending_refunds": len(self.refund_queue)
        }

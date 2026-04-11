"""
Flash Mode - Speculative LLM inference middleware.

Triggers speculative inference on high-confidence partial transcripts
to reduce TTFT by ~80ms through hit reuse.
"""

from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class SpeculativeStatus(str, Enum):
    """Status of speculative inference."""
    PENDING = "pending"
    HIT = "hit"
    MISS = "miss"
    DISCARDED = "discarded"


@dataclass
class SpeculativeInferenceState:
    """State of speculative inference."""
    call_id: str
    partial_transcript: str
    partial_hash: str
    confidence: float
    llm_response: Optional[str] = None
    status: SpeculativeStatus = SpeculativeStatus.PENDING
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class FlashModeResult:
    """Result of flash mode processing."""
    final_response: str
    was_speculative_hit: bool
    ttft_reduction_ms: float
    speculative_state: Optional[SpeculativeInferenceState] = None


class FlashMode:
    """Speculative LLM inference middleware."""
    
    def __init__(self, 
                 confidence_threshold: float = 0.85,
                 enabled_by_default: bool = True):
        self.confidence_threshold = confidence_threshold
        self.enabled_by_default = enabled_by_default
        self.speculative_states: Dict[str, SpeculativeInferenceState] = {}
        self.tenant_config: Dict[str, bool] = {}
        self.hit_count = 0
        self.miss_count = 0
        self.last_log_date = date.today()
    
    def is_enabled_for_tenant(self, tenant_id: str) -> bool:
        """Check if flash mode is enabled for tenant."""
        return self.tenant_config.get(tenant_id, self.enabled_by_default)
    
    def set_tenant_config(self, tenant_id: str, enabled: bool):
        """Set flash mode configuration for tenant."""
        self.tenant_config[tenant_id] = enabled
        logger.info(f"Flash mode {'enabled' if enabled else 'disabled'} for tenant {tenant_id}")
    
    async def on_partial_transcript(self, 
                                    call_id: str,
                                    partial_transcript: str,
                                    confidence: float,
                                    tenant_id: str,
                                    llm_agent) -> Optional[SpeculativeInferenceState]:
        """Handle partial transcript and trigger speculative inference if confidence high."""
        if not self.is_enabled_for_tenant(tenant_id):
            return None
        
        # Trigger speculative inference if confidence >= threshold
        if confidence >= self.confidence_threshold:
            partial_hash = self._hash_transcript(partial_transcript)
            
            # Check if already processing
            if call_id in self.speculative_states:
                return self.speculative_states[call_id]
            
            # Create speculative state
            state = SpeculativeInferenceState(
                call_id=call_id,
                partial_transcript=partial_transcript,
                partial_hash=partial_hash,
                confidence=confidence
            )
            
            self.speculative_states[call_id] = state
            
            # Trigger speculative LLM inference (non-blocking)
            logger.info(f"Triggering speculative inference for call {call_id} (confidence: {confidence:.2f})")
            
            # Simulate async LLM call
            try:
                response = await llm_agent.infer(partial_transcript)
                state.llm_response = response
                state.completed_at = datetime.utcnow()
                logger.debug(f"Speculative inference completed for call {call_id}")
            except Exception as e:
                logger.error(f"Speculative inference failed: {e}")
                state.status = SpeculativeStatus.DISCARDED
            
            return state
        
        return None
    
    async def on_final_transcript(self,
                                  call_id: str,
                                  final_transcript: str,
                                  llm_agent) -> FlashModeResult:
        """Handle final transcript and reconcile with speculative inference."""
        final_hash = self._hash_transcript(final_transcript)
        
        # Check if we have speculative state
        if call_id not in self.speculative_states:
            # No speculative inference, run normal inference
            response = await llm_agent.infer(final_transcript)
            return FlashModeResult(
                final_response=response,
                was_speculative_hit=False,
                ttft_reduction_ms=0.0
            )
        
        state = self.speculative_states[call_id]
        
        # Compare hashes for hit/miss
        if state.partial_hash == final_hash and state.llm_response:
            # HIT: Reuse speculative result
            state.status = SpeculativeStatus.HIT
            self.hit_count += 1
            
            # Calculate TTFT reduction
            if state.completed_at:
                ttft_reduction = (datetime.utcnow() - state.completed_at).total_seconds() * 1000
            else:
                ttft_reduction = 0.0
            
            logger.info(f"Speculative HIT for call {call_id}, TTFT reduction: {ttft_reduction:.1f}ms")
            
            # Cleanup
            del self.speculative_states[call_id]
            
            return FlashModeResult(
                final_response=state.llm_response,
                was_speculative_hit=True,
                ttft_reduction_ms=ttft_reduction,
                speculative_state=state
            )
        else:
            # MISS: Discard speculative result and run fresh inference
            state.status = SpeculativeStatus.DISCARDED
            self.miss_count += 1
            
            logger.info(f"Speculative MISS for call {call_id}")
            
            response = await llm_agent.infer(final_transcript)
            
            # Cleanup
            del self.speculative_states[call_id]
            
            return FlashModeResult(
                final_response=response,
                was_speculative_hit=False,
                ttft_reduction_ms=0.0,
                speculative_state=state
            )
    
    def get_hit_rate(self) -> float:
        """Calculate current hit rate."""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total
    
    def log_daily_metrics(self):
        """Log daily hit rate metrics to Prometheus."""
        today = date.today()
        
        if today != self.last_log_date:
            hit_rate = self.get_hit_rate()
            logger.info(f"Flash mode daily hit rate: {hit_rate:.2%} (hits: {self.hit_count}, misses: {self.miss_count})")
            
            # Reset counters
            self.hit_count = 0
            self.miss_count = 0
            self.last_log_date = today
    
    def _hash_transcript(self, transcript: str) -> str:
        """Hash transcript for comparison."""
        return hashlib.sha256(transcript.encode()).hexdigest()


# Global instance
_flash_mode: Optional[FlashMode] = None


def get_flash_mode() -> FlashMode:
    """Get global flash mode instance."""
    global _flash_mode
    if _flash_mode is None:
        _flash_mode = FlashMode()
    return _flash_mode


def set_flash_mode(flash_mode: FlashMode) -> None:
    """Set global flash mode instance."""
    global _flash_mode
    _flash_mode = flash_mode

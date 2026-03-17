"""
Call Controller

Orchestrates calls across multiple telephony providers with load balancing
and failover support.
Implements Requirement 14.1 and 14.6 - Unified call control and failover.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from .base import (
    TelephonyProvider,
    CallSession,
    CallStatus,
    CallDirection,
    CallEvent,
    CallEventType,
    CallEventHandler,
    ProviderType,
    HealthStatus
)
from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class LoadBalancingStrategy:
    """Load balancing strategies for call routing"""
    
    @staticmethod
    def round_robin(providers: List[TelephonyProvider]) -> Optional[TelephonyProvider]:
        """Round-robin selection"""
        if not providers:
            return None
        # Simple round-robin (can be enhanced with state)
        return providers[0]
    
    @staticmethod
    def least_loaded(providers: List[TelephonyProvider]) -> Optional[TelephonyProvider]:
        """Select provider with least active calls"""
        if not providers:
            return None
        return min(providers, key=lambda p: len(p.get_active_calls()))
    
    @staticmethod
    def priority_based(providers: List[TelephonyProvider]) -> Optional[TelephonyProvider]:
        """Select provider with highest priority"""
        if not providers:
            return None
        return min(providers, key=lambda p: p.config.priority)
    
    @staticmethod
    def cost_based(providers: List[TelephonyProvider]) -> Optional[TelephonyProvider]:
        """Select provider with lowest cost (based on priority as proxy)"""
        if not providers:
            return None
        return min(providers, key=lambda p: p.config.priority)


class CallController:
    """
    Central call controller
    
    Manages call routing, load balancing, and failover across multiple
    telephony providers.
    """
    
    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        load_balancing_strategy: str = "least_loaded"
    ):
        """
        Initialize call controller
        
        Args:
            registry: Provider registry (creates new if None)
            load_balancing_strategy: Load balancing strategy name
        """
        self.registry = registry or ProviderRegistry()
        self.logger = logging.getLogger(__name__)
        
        # Set load balancing strategy
        strategies = {
            "round_robin": LoadBalancingStrategy.round_robin,
            "least_loaded": LoadBalancingStrategy.least_loaded,
            "priority": LoadBalancingStrategy.priority_based,
            "cost": LoadBalancingStrategy.cost_based
        }
        self.load_balancing_strategy = strategies.get(
            load_balancing_strategy,
            LoadBalancingStrategy.least_loaded
        )
        
        # Event handlers
        self.event_handlers: List[CallEventHandler] = []
        
        # Call tracking
        self.all_calls: Dict[str, CallSession] = {}
        
        # Failover configuration
        self.enable_failover = True
        self.max_failover_attempts = 3
    
    def add_event_handler(self, handler: CallEventHandler) -> None:
        """
        Add a call event handler
        
        Args:
            handler: Event handler to add
        """
        self.event_handlers.append(handler)
        self.logger.info(f"Added event handler: {handler.__class__.__name__}")
    
    async def _emit_event(self, event: CallEvent) -> None:
        """
        Emit a call event to all handlers
        
        Args:
            event: Event to emit
        """
        for handler in self.event_handlers:
            try:
                await handler.handle_event(event)
            except Exception as e:
                self.logger.error(
                    f"Error in event handler {handler.__class__.__name__}: {e}"
                )
    
    def _select_provider(
        self,
        provider_type: Optional[ProviderType] = None
    ) -> Optional[TelephonyProvider]:
        """
        Select a provider for a call
        
        Args:
            provider_type: Specific provider type to use (optional)
            
        Returns:
            Selected provider or None
        """
        # Get healthy providers
        if provider_type:
            providers = [
                p for p in self.registry.get_providers_by_type(provider_type)
                if p.health_status == HealthStatus.HEALTHY and p.config.enabled
            ]
        else:
            providers = [
                p for p in self.registry.get_healthy_providers()
                if p.config.enabled
            ]
        
        if not providers:
            self.logger.error("No healthy providers available")
            return None
        
        # Apply load balancing strategy
        selected = self.load_balancing_strategy(providers)
        
        if selected:
            self.logger.info(
                f"Selected provider: {selected.config.provider_id} "
                f"({selected.config.provider_type.value})"
            )
        
        return selected
    
    async def make_call(
        self,
        from_number: str,
        to_number: str,
        provider_type: Optional[ProviderType] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[CallSession]:
        """
        Make an outbound call
        
        Args:
            from_number: Caller ID
            to_number: Destination number
            provider_type: Specific provider type to use (optional)
            metadata: Additional call metadata
            
        Returns:
            CallSession or None if failed
        """
        attempt = 0
        last_error = None
        
        while attempt < self.max_failover_attempts:
            try:
                # Select provider
                provider = self._select_provider(provider_type)
                if not provider:
                    break
                
                # Make call
                call = await provider.make_call(from_number, to_number, metadata)
                
                # Track call
                self.all_calls[call.call_id] = call
                
                # Emit event
                await self._emit_event(CallEvent(
                    event_type=CallEventType.CALL_INITIATED,
                    call_id=call.call_id,
                    provider_id=provider.config.provider_id,
                    timestamp=datetime.utcnow(),
                    data={
                        "from_number": from_number,
                        "to_number": to_number,
                        "attempt": attempt + 1
                    }
                ))
                
                self.logger.info(
                    f"Call initiated: {call.call_id} via "
                    f"{provider.config.provider_id}"
                )
                
                return call
            
            except Exception as e:
                last_error = e
                attempt += 1
                self.logger.warning(
                    f"Call attempt {attempt} failed: {e}. "
                    f"Retrying..." if attempt < self.max_failover_attempts else "No more retries."
                )
                
                if not self.enable_failover:
                    break
        
        self.logger.error(
            f"Failed to make call after {attempt} attempts. "
            f"Last error: {last_error}"
        )
        return None
    
    async def answer_call(self, call_id: str) -> bool:
        """
        Answer an inbound call
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        call = self.all_calls.get(call_id)
        if not call:
            self.logger.error(f"Call not found: {call_id}")
            return False
        
        provider = self.registry.get_provider(call.provider_id)
        if not provider:
            self.logger.error(f"Provider not found: {call.provider_id}")
            return False
        
        try:
            success = await provider.answer_call(call_id)
            
            if success:
                call.status = CallStatus.ANSWERED
                call.answer_time = datetime.utcnow()
                
                await self._emit_event(CallEvent(
                    event_type=CallEventType.CALL_ANSWERED,
                    call_id=call_id,
                    provider_id=provider.config.provider_id,
                    timestamp=datetime.utcnow()
                ))
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error answering call {call_id}: {e}")
            return False
    
    async def hangup_call(self, call_id: str) -> bool:
        """
        Hang up a call
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if successful
        """
        call = self.all_calls.get(call_id)
        if not call:
            self.logger.error(f"Call not found: {call_id}")
            return False
        
        provider = self.registry.get_provider(call.provider_id)
        if not provider:
            self.logger.error(f"Provider not found: {call.provider_id}")
            return False
        
        try:
            success = await provider.hangup_call(call_id)
            
            if success:
                call.status = CallStatus.COMPLETED
                call.end_time = datetime.utcnow()
                
                await self._emit_event(CallEvent(
                    event_type=CallEventType.CALL_ENDED,
                    call_id=call_id,
                    provider_id=provider.config.provider_id,
                    timestamp=datetime.utcnow(),
                    data={"duration": call.duration}
                ))
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error hanging up call {call_id}: {e}")
            return False
    
    async def transfer_call(
        self,
        call_id: str,
        destination: str
    ) -> bool:
        """
        Transfer a call
        
        Args:
            call_id: Call identifier
            destination: Transfer destination
            
        Returns:
            True if successful
        """
        call = self.all_calls.get(call_id)
        if not call:
            self.logger.error(f"Call not found: {call_id}")
            return False
        
        provider = self.registry.get_provider(call.provider_id)
        if not provider:
            self.logger.error(f"Provider not found: {call.provider_id}")
            return False
        
        try:
            success = await provider.transfer_call(call_id, destination)
            
            if success:
                call.status = CallStatus.TRANSFERRING
                
                await self._emit_event(CallEvent(
                    event_type=CallEventType.CALL_TRANSFERRED,
                    call_id=call_id,
                    provider_id=provider.config.provider_id,
                    timestamp=datetime.utcnow(),
                    data={"destination": destination}
                ))
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error transferring call {call_id}: {e}")
            return False
    
    async def get_call_qos(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get QoS metrics for a call
        
        Args:
            call_id: Call identifier
            
        Returns:
            QoS metrics dictionary or None
        """
        call = self.all_calls.get(call_id)
        if not call:
            return None
        
        provider = self.registry.get_provider(call.provider_id)
        if not provider:
            return None
        
        try:
            qos = await provider.get_qos_metrics(call_id)
            if qos:
                call.qos_metrics = qos
                return qos.to_dict()
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting QoS for call {call_id}: {e}")
            return None
    
    def get_call(self, call_id: str) -> Optional[CallSession]:
        """Get call by ID"""
        return self.all_calls.get(call_id)
    
    def get_active_calls(self) -> List[CallSession]:
        """Get all active calls"""
        return [call for call in self.all_calls.values() if call.is_active]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get call statistics"""
        active_calls = self.get_active_calls()
        
        return {
            "total_calls": len(self.all_calls),
            "active_calls": len(active_calls),
            "completed_calls": len([
                c for c in self.all_calls.values()
                if c.status == CallStatus.COMPLETED
            ]),
            "failed_calls": len([
                c for c in self.all_calls.values()
                if c.status == CallStatus.FAILED
            ]),
            "providers": {
                "total": len(self.registry.get_all_providers()),
                "healthy": len(self.registry.get_healthy_providers()),
                "types": [t.value for t in self.registry.get_registered_types()]
            },
            "load_balancing_strategy": self.load_balancing_strategy.__name__,
            "failover_enabled": self.enable_failover
        }

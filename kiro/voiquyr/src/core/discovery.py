"""
Agent discovery and registration system.
Handles agent lifecycle, health monitoring, and service discovery.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
import json
import aiohttp
from urllib.parse import urljoin

from .models import (
    AgentRegistration, AgentState, AgentCapability, 
    AgentStatus, MessageType, Priority
)
from .messaging import MessageRouter, MessageBus, AgentMessage


logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Central service registry for agent discovery and registration.
    Maintains a registry of all available agents and their capabilities.
    """
    
    def __init__(self, message_router: MessageRouter):
        self.message_router = message_router
        self.message_bus = MessageBus(message_router)
        self.registrations: Dict[str, AgentRegistration] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 10   # seconds
        self.unhealthy_threshold = 3     # failed health checks before marking offline
        self.health_check_task: Optional[asyncio.Task] = None
        self.discovery_callbacks: List[Callable] = []
        self.agent_capabilities_index: Dict[str, Set[str]] = {}  # capability -> agent_ids
        
    async def start(self) -> None:
        """Start the service registry and health monitoring."""
        logger.info("Starting service registry")
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
    async def stop(self) -> None:
        """Stop the service registry."""
        logger.info("Stopping service registry")
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
    
    async def register_agent(self, registration: AgentRegistration) -> bool:
        """Register a new agent."""
        try:
            agent_id = registration.agent_id
            
            # Register with message router first
            success = await self.message_router.register_agent(registration)
            if not success:
                return False
            
            # Store registration
            self.registrations[agent_id] = registration
            
            # Index capabilities
            self._index_agent_capabilities(registration)
            
            # Notify discovery callbacks
            await self._notify_discovery_callbacks("agent_registered", registration)
            
            logger.info(f"Agent {agent_id} registered with capabilities: {[cap.name for cap in registration.capabilities]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {registration.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        try:
            if agent_id not in self.registrations:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False
            
            registration = self.registrations[agent_id]
            
            # Unregister from message router
            await self.message_router.unregister_agent(agent_id)
            
            # Remove from registry
            del self.registrations[agent_id]
            
            # Remove from capability index
            self._remove_agent_from_capability_index(agent_id)
            
            # Notify discovery callbacks
            await self._notify_discovery_callbacks("agent_unregistered", registration)
            
            logger.info(f"Agent {agent_id} unregistered")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    def get_agent_registration(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get registration information for an agent."""
        return self.registrations.get(agent_id)
    
    def get_all_agents(self) -> List[AgentRegistration]:
        """Get all registered agents."""
        return list(self.registrations.values())
    
    def get_agents_by_type(self, agent_type: str) -> List[AgentRegistration]:
        """Get all agents of a specific type."""
        return [reg for reg in self.registrations.values() if reg.agent_type == agent_type]
    
    def get_agents_by_capability(self, capability_name: str) -> List[AgentRegistration]:
        """Get all agents that have a specific capability."""
        agent_ids = self.agent_capabilities_index.get(capability_name, set())
        return [self.registrations[agent_id] for agent_id in agent_ids 
                if agent_id in self.registrations]
    
    def find_best_agent_for_capability(self, capability_name: str, 
                                     criteria: Optional[Dict[str, Any]] = None) -> Optional[AgentRegistration]:
        """Find the best agent for a specific capability based on criteria."""
        candidates = self.get_agents_by_capability(capability_name)
        
        if not candidates:
            return None
        
        if not criteria:
            # Return first available healthy agent
            for candidate in candidates:
                agent_state = self.message_router.get_agent_state(candidate.agent_id)
                if agent_state and agent_state.is_healthy() and agent_state.status == AgentStatus.IDLE:
                    return candidate
            return candidates[0]  # Fallback to first candidate
        
        # Apply selection criteria
        best_candidate = None
        best_score = -1
        
        for candidate in candidates:
            agent_state = self.message_router.get_agent_state(candidate.agent_id)
            if not agent_state or not agent_state.is_healthy():
                continue
            
            score = self._calculate_agent_score(candidate, agent_state, criteria)
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        return best_candidate
    
    def _calculate_agent_score(self, registration: AgentRegistration, 
                              state: AgentState, criteria: Dict[str, Any]) -> float:
        """Calculate a score for agent selection based on criteria."""
        score = 0.0
        
        # Prefer idle agents
        if state.status == AgentStatus.IDLE:
            score += 10.0
        elif state.status == AgentStatus.WORKING:
            score += 5.0
        
        # Consider performance metrics
        if "performance_weight" in criteria:
            weight = criteria["performance_weight"]
            avg_performance = sum(state.performance_metrics.values()) / max(len(state.performance_metrics), 1)
            score += avg_performance * weight
        
        # Consider error rate
        if state.total_tasks_completed > 0:
            error_rate = state.error_count / state.total_tasks_completed
            score -= error_rate * 5.0  # Penalize high error rates
        
        # Consider resource usage
        if "resource_weight" in criteria:
            weight = criteria["resource_weight"]
            avg_resource_usage = sum(state.resource_usage.values()) / max(len(state.resource_usage), 1)
            score -= avg_resource_usage * weight  # Prefer less loaded agents
        
        return score
    
    def _index_agent_capabilities(self, registration: AgentRegistration) -> None:
        """Index agent capabilities for fast lookup."""
        agent_id = registration.agent_id
        for capability in registration.capabilities:
            if capability.name not in self.agent_capabilities_index:
                self.agent_capabilities_index[capability.name] = set()
            self.agent_capabilities_index[capability.name].add(agent_id)
    
    def _remove_agent_from_capability_index(self, agent_id: str) -> None:
        """Remove agent from capability index."""
        for capability_agents in self.agent_capabilities_index.values():
            capability_agents.discard(agent_id)
    
    async def _health_check_loop(self) -> None:
        """Continuous health check loop for all registered agents."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered agents."""
        health_check_tasks = []
        
        for agent_id in list(self.registrations.keys()):
            task = asyncio.create_task(self._check_agent_health(agent_id))
            health_check_tasks.append(task)
        
        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)
    
    async def _check_agent_health(self, agent_id: str) -> None:
        """Check health of a specific agent."""
        try:
            registration = self.registrations.get(agent_id)
            if not registration:
                return
            
            agent_state = self.message_router.get_agent_state(agent_id)
            if not agent_state:
                return
            
            # Send heartbeat request
            heartbeat_message = AgentMessage(
                sender_id="service_registry",
                receiver_id=agent_id,
                message_type=MessageType.HEARTBEAT,
                payload={"timestamp": datetime.utcnow().isoformat()},
                priority=Priority.HIGH,
                expires_at=datetime.utcnow() + timedelta(seconds=self.health_check_timeout)
            )
            
            success = await self.message_router.send_message(heartbeat_message)
            
            if success:
                # Check if agent is responding based on heartbeat timestamp
                if agent_state.is_healthy():
                    # Reset error count on successful health check
                    if agent_state.status == AgentStatus.ERROR:
                        agent_state.status = AgentStatus.IDLE
                else:
                    # Mark as unhealthy if heartbeat is too old
                    await self._handle_unhealthy_agent(agent_id, "Heartbeat timeout")
            else:
                await self._handle_unhealthy_agent(agent_id, "Failed to send heartbeat")
                
        except Exception as e:
            logger.error(f"Error checking health of agent {agent_id}: {e}")
            await self._handle_unhealthy_agent(agent_id, f"Health check error: {e}")
    
    async def _handle_unhealthy_agent(self, agent_id: str, reason: str) -> None:
        """Handle an unhealthy agent."""
        agent_state = self.message_router.get_agent_state(agent_id)
        if not agent_state:
            return
        
        agent_state.error_count += 1
        
        if agent_state.error_count >= self.unhealthy_threshold:
            logger.warning(f"Agent {agent_id} marked as offline: {reason}")
            agent_state.status = AgentStatus.OFFLINE
            
            # Notify other agents about the offline agent
            await self.message_bus.send_notification(
                sender_id="service_registry",
                notification_data={
                    "event": "agent_offline",
                    "agent_id": agent_id,
                    "reason": reason
                }
            )
        else:
            logger.warning(f"Agent {agent_id} health check failed ({agent_state.error_count}/{self.unhealthy_threshold}): {reason}")
            agent_state.status = AgentStatus.ERROR
    
    def add_discovery_callback(self, callback: Callable[[str, AgentRegistration], None]) -> None:
        """Add a callback for agent discovery events."""
        self.discovery_callbacks.append(callback)
    
    async def _notify_discovery_callbacks(self, event: str, registration: AgentRegistration) -> None:
        """Notify all discovery callbacks."""
        for callback in self.discovery_callbacks:
            try:
                await callback(event, registration)
            except Exception as e:
                logger.error(f"Error in discovery callback: {e}")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        agent_types = {}
        capability_counts = {}
        status_counts = {}
        
        for registration in self.registrations.values():
            # Count by agent type
            agent_types[registration.agent_type] = agent_types.get(registration.agent_type, 0) + 1
            
            # Count capabilities
            for capability in registration.capabilities:
                capability_counts[capability.name] = capability_counts.get(capability.name, 0) + 1
            
            # Count by status
            agent_state = self.message_router.get_agent_state(registration.agent_id)
            if agent_state:
                status = agent_state.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_agents": len(self.registrations),
            "agent_types": agent_types,
            "capability_counts": capability_counts,
            "status_counts": status_counts,
            "health_check_interval": self.health_check_interval,
            "unhealthy_threshold": self.unhealthy_threshold
        }


class AgentDiscoveryClient:
    """
    Client-side agent discovery functionality.
    Used by agents to discover and communicate with other agents.
    """
    
    def __init__(self, agent_id: str, service_registry: ServiceRegistry):
        self.agent_id = agent_id
        self.service_registry = service_registry
        self.known_agents: Dict[str, AgentRegistration] = {}
        self.capability_cache: Dict[str, List[str]] = {}  # capability -> agent_ids
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = datetime.min
    
    async def discover_agents_by_type(self, agent_type: str) -> List[AgentRegistration]:
        """Discover agents by type."""
        await self._refresh_cache_if_needed()
        return [reg for reg in self.known_agents.values() if reg.agent_type == agent_type]
    
    async def discover_agents_by_capability(self, capability_name: str) -> List[AgentRegistration]:
        """Discover agents by capability."""
        await self._refresh_cache_if_needed()
        
        if capability_name in self.capability_cache:
            agent_ids = self.capability_cache[capability_name]
            return [self.known_agents[agent_id] for agent_id in agent_ids 
                   if agent_id in self.known_agents]
        
        return []
    
    async def find_best_agent_for_task(self, capability_name: str, 
                                     task_requirements: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Find the best agent ID for a specific task."""
        registration = self.service_registry.find_best_agent_for_capability(
            capability_name, task_requirements
        )
        return registration.agent_id if registration else None
    
    async def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Get capabilities of a specific agent."""
        await self._refresh_cache_if_needed()
        
        if agent_id in self.known_agents:
            return self.known_agents[agent_id].capabilities
        
        return []
    
    async def is_agent_available(self, agent_id: str) -> bool:
        """Check if an agent is available for work."""
        agent_state = self.service_registry.message_router.get_agent_state(agent_id)
        if not agent_state:
            return False
        
        return (agent_state.is_healthy() and 
                agent_state.status in [AgentStatus.IDLE, AgentStatus.WORKING])
    
    async def _refresh_cache_if_needed(self) -> None:
        """Refresh the agent cache if it's stale."""
        now = datetime.utcnow()
        if (now - self.last_cache_update).total_seconds() > self.cache_ttl:
            await self._refresh_cache()
    
    async def _refresh_cache(self) -> None:
        """Refresh the local agent cache."""
        try:
            # Get all registered agents
            all_agents = self.service_registry.get_all_agents()
            
            # Update known agents
            self.known_agents = {reg.agent_id: reg for reg in all_agents}
            
            # Update capability cache
            self.capability_cache.clear()
            for registration in all_agents:
                for capability in registration.capabilities:
                    if capability.name not in self.capability_cache:
                        self.capability_cache[capability.name] = []
                    self.capability_cache[capability.name].append(registration.agent_id)
            
            self.last_cache_update = datetime.utcnow()
            logger.debug(f"Agent cache refreshed for {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to refresh agent cache for {self.agent_id}: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "known_agents": len(self.known_agents),
            "cached_capabilities": len(self.capability_cache),
            "last_update": self.last_cache_update.isoformat(),
            "cache_age_seconds": (datetime.utcnow() - self.last_cache_update).total_seconds()
        }
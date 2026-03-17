"""
System Orchestration

Master orchestration logic for agent coordination, load balancing,
health checking, and automatic failover in the EUVoice AI Platform.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME = "response_time"
    HEALTH_BASED = "health_based"


@dataclass
class AgentInstance:
    """Represents an agent instance."""
    instance_id: str
    agent_type: str
    endpoint: str
    status: AgentStatus
    health_score: float
    active_connections: int
    total_requests: int
    avg_response_time_ms: float
    last_health_check: datetime
    weight: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class HealthCheckResult:
    """Health check result for an agent."""
    instance_id: str
    status: AgentStatus
    health_score: float
    response_time_ms: float
    error_message: Optional[str]
    timestamp: datetime
    metrics: Dict[str, Any]


class HealthChecker:
    """Health checking system for agent instances."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize health checker."""
        self.config = config or {}
        
        # Health check configuration
        self.check_interval_seconds = self.config.get("check_interval", 30)
        self.timeout_seconds = self.config.get("timeout", 5)
        self.failure_threshold = self.config.get("failure_threshold", 3)
        self.recovery_threshold = self.config.get("recovery_threshold", 2)
        
        # Health check history
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.failure_counts: Dict[str, int] = {}
        
        logger.info("Health Checker initialized")
    
    async def check_agent_health(self, agent: AgentInstance) -> HealthCheckResult:
        """Perform health check on an agent instance."""
        start_time = time.time()
        
        try:
            # Simulate health check (replace with actual health check logic)
            await asyncio.sleep(0.01)  # Simulate network call
            
            # Mock health check based on agent status and performance
            if agent.status == AgentStatus.OFFLINE:
                raise Exception("Agent is offline")
            
            # Calculate health score based on various factors
            health_score = 1.0
            
            # Response time factor
            if agent.avg_response_time_ms > 1000:
                health_score *= 0.7
            elif agent.avg_response_time_ms > 500:
                health_score *= 0.9
            
            # Connection load factor
            if agent.active_connections > 100:
                health_score *= 0.8
            elif agent.active_connections > 50:
                health_score *= 0.95
            
            # Determine status based on health score
            if health_score >= 0.9:
                status = AgentStatus.HEALTHY
            elif health_score >= 0.7:
                status = AgentStatus.DEGRADED
            else:
                status = AgentStatus.UNHEALTHY
            
            response_time = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                instance_id=agent.instance_id,
                status=status,
                health_score=health_score,
                response_time_ms=response_time,
                error_message=None,
                timestamp=datetime.utcnow(),
                metrics={
                    "cpu_usage": 45.0 + (hash(agent.instance_id) % 30),
                    "memory_usage": 60.0 + (hash(agent.instance_id) % 25),
                    "active_connections": agent.active_connections,
                    "response_time": agent.avg_response_time_ms
                }
            )
            
            # Reset failure count on successful check
            self.failure_counts[agent.instance_id] = 0
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            # Increment failure count
            self.failure_counts[agent.instance_id] = self.failure_counts.get(agent.instance_id, 0) + 1
            
            result = HealthCheckResult(
                instance_id=agent.instance_id,
                status=AgentStatus.UNHEALTHY,
                health_score=0.0,
                response_time_ms=response_time,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                metrics={}
            )
        
        # Store health check result
        if agent.instance_id not in self.health_history:
            self.health_history[agent.instance_id] = []
        
        self.health_history[agent.instance_id].append(result)
        
        # Keep only recent history
        max_history = self.config.get("max_history", 100)
        if len(self.health_history[agent.instance_id]) > max_history:
            self.health_history[agent.instance_id] = self.health_history[agent.instance_id][-max_history:]
        
        return result
    
    def should_mark_unhealthy(self, instance_id: str) -> bool:
        """Check if an instance should be marked as unhealthy."""
        return self.failure_counts.get(instance_id, 0) >= self.failure_threshold
    
    def should_mark_healthy(self, instance_id: str) -> bool:
        """Check if an instance should be marked as healthy."""
        recent_checks = self.get_recent_health_checks(instance_id, self.recovery_threshold)
        return len(recent_checks) >= self.recovery_threshold and all(
            check.status in [AgentStatus.HEALTHY, AgentStatus.DEGRADED] 
            for check in recent_checks
        )
    
    def get_recent_health_checks(self, instance_id: str, count: int) -> List[HealthCheckResult]:
        """Get recent health check results for an instance."""
        history = self.health_history.get(instance_id, [])
        return history[-count:] if len(history) >= count else history


class LoadBalancer:
    """Load balancer for distributing requests across agent instances."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_BASED):
        """Initialize load balancer."""
        self.strategy = strategy
        self.round_robin_counters: Dict[str, int] = {}
        
        logger.info(f"Load Balancer initialized with strategy: {strategy.value}")
    
    def select_agent(self, agents: List[AgentInstance], agent_type: str) -> Optional[AgentInstance]:
        """Select the best agent instance for a request."""
        # Filter healthy agents
        healthy_agents = [
            agent for agent in agents 
            if agent.agent_type == agent_type and agent.status in [AgentStatus.HEALTHY, AgentStatus.DEGRADED]
        ]
        
        if not healthy_agents:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_agents, agent_type)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_agents)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(healthy_agents, agent_type)
        elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME:
            return self._response_time_selection(healthy_agents)
        elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
            return self._health_based_selection(healthy_agents)
        else:
            return healthy_agents[0]  # Fallback
    
    def _round_robin_selection(self, agents: List[AgentInstance], agent_type: str) -> AgentInstance:
        """Round robin selection."""
        if agent_type not in self.round_robin_counters:
            self.round_robin_counters[agent_type] = 0
        
        selected_agent = agents[self.round_robin_counters[agent_type] % len(agents)]
        self.round_robin_counters[agent_type] += 1
        
        return selected_agent
    
    def _least_connections_selection(self, agents: List[AgentInstance]) -> AgentInstance:
        """Least connections selection."""
        return min(agents, key=lambda agent: agent.active_connections)
    
    def _weighted_round_robin_selection(self, agents: List[AgentInstance], agent_type: str) -> AgentInstance:
        """Weighted round robin selection."""
        # Simple weighted selection based on agent weights
        total_weight = sum(agent.weight for agent in agents)
        
        if agent_type not in self.round_robin_counters:
            self.round_robin_counters[agent_type] = 0
        
        # Calculate weighted position
        position = self.round_robin_counters[agent_type] % int(total_weight * 10)
        self.round_robin_counters[agent_type] += 1
        
        # Select based on weighted position
        cumulative_weight = 0
        for agent in agents:
            cumulative_weight += agent.weight * 10
            if position < cumulative_weight:
                return agent
        
        return agents[0]  # Fallback
    
    def _response_time_selection(self, agents: List[AgentInstance]) -> AgentInstance:
        """Response time based selection."""
        return min(agents, key=lambda agent: agent.avg_response_time_ms)
    
    def _health_based_selection(self, agents: List[AgentInstance]) -> AgentInstance:
        """Health score based selection."""
        # Combine health score and response time
        def score_function(agent):
            return agent.health_score - (agent.avg_response_time_ms / 1000.0)
        
        return max(agents, key=score_function)


class SystemOrchestrator:
    """Master orchestration system for the EUVoice AI Platform."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize system orchestrator."""
        self.config = config or {}
        
        # Agent registry
        self.agent_instances: Dict[str, AgentInstance] = {}
        self.agent_types = ["stt", "llm", "tts", "emotion", "accent", "lip_sync", "arabic"]
        
        # Components
        self.health_checker = HealthChecker(self.config.get("health_check", {}))
        self.load_balancer = LoadBalancer(
            LoadBalancingStrategy(self.config.get("load_balancing_strategy", "health_based"))
        )
        
        # Orchestration state
        self.orchestration_active = False
        self.orchestration_tasks: List[asyncio.Task] = []
        
        # Performance tracking
        self.request_metrics: Dict[str, List[float]] = {agent_type: [] for agent_type in self.agent_types}
        
        # Failover configuration
        self.enable_auto_failover = self.config.get("auto_failover", True)
        self.failover_cooldown_seconds = self.config.get("failover_cooldown", 60)
        self.last_failover: Dict[str, datetime] = {}
        
        logger.info("System Orchestrator initialized")
    
    async def start_orchestration(self) -> None:
        """Start the orchestration system."""
        if self.orchestration_active:
            logger.warning("Orchestration is already active")
            return
        
        self.orchestration_active = True
        
        # Initialize default agent instances
        await self._initialize_default_agents()
        
        # Start orchestration tasks
        self.orchestration_tasks = [
            asyncio.create_task(self._health_monitoring_loop()),
            asyncio.create_task(self._performance_monitoring_loop()),
            asyncio.create_task(self._failover_management_loop())
        ]
        
        logger.info("System orchestration started")
    
    async def stop_orchestration(self) -> None:
        """Stop the orchestration system."""
        self.orchestration_active = False
        
        # Cancel orchestration tasks
        for task in self.orchestration_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.orchestration_tasks:
            await asyncio.gather(*self.orchestration_tasks, return_exceptions=True)
        
        self.orchestration_tasks.clear()
        
        logger.info("System orchestration stopped")
    
    async def _initialize_default_agents(self) -> None:
        """Initialize default agent instances."""
        # Create mock agent instances for each type
        for agent_type in self.agent_types:
            for i in range(2):  # 2 instances per agent type
                instance_id = f"{agent_type}_instance_{i+1}"
                
                agent = AgentInstance(
                    instance_id=instance_id,
                    agent_type=agent_type,
                    endpoint=f"http://localhost:800{i+1}/{agent_type}",
                    status=AgentStatus.HEALTHY,
                    health_score=0.95,
                    active_connections=0,
                    total_requests=0,
                    avg_response_time_ms=100.0 + i * 50,
                    last_health_check=datetime.utcnow(),
                    weight=1.0 if i == 0 else 0.8,  # Primary instance has higher weight
                    metadata={"version": "1.0.0", "region": "eu-west-1"}
                )
                
                self.agent_instances[instance_id] = agent
        
        logger.info(f"Initialized {len(self.agent_instances)} agent instances")
    
    async def _health_monitoring_loop(self) -> None:
        """Health monitoring loop."""
        while self.orchestration_active:
            try:
                # Check health of all agents
                health_tasks = [
                    self.health_checker.check_agent_health(agent)
                    for agent in self.agent_instances.values()
                ]
                
                if health_tasks:
                    health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
                    
                    # Update agent statuses based on health checks
                    for result in health_results:
                        if isinstance(result, HealthCheckResult):
                            await self._update_agent_status(result)
                
                # Sleep until next health check
                await asyncio.sleep(self.health_checker.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _performance_monitoring_loop(self) -> None:
        """Performance monitoring loop."""
        while self.orchestration_active:
            try:
                # Update performance metrics
                await self._update_performance_metrics()
                
                # Sleep for performance monitoring interval
                await asyncio.sleep(self.config.get("performance_interval", 60))
                
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _failover_management_loop(self) -> None:
        """Failover management loop."""
        while self.orchestration_active:
            try:
                if self.enable_auto_failover:
                    await self._check_and_execute_failover()
                
                # Sleep for failover check interval
                await asyncio.sleep(self.config.get("failover_interval", 30))
                
            except Exception as e:
                logger.error(f"Error in failover management loop: {e}")
                await asyncio.sleep(10)
    
    async def _update_agent_status(self, health_result: HealthCheckResult) -> None:
        """Update agent status based on health check result."""
        agent = self.agent_instances.get(health_result.instance_id)
        if not agent:
            return
        
        # Update agent with health check results
        agent.status = health_result.status
        agent.health_score = health_result.health_score
        agent.last_health_check = health_result.timestamp
        
        # Check for status changes that require action
        if health_result.status == AgentStatus.UNHEALTHY:
            logger.warning(f"Agent {agent.instance_id} marked as unhealthy: {health_result.error_message}")
        elif health_result.status == AgentStatus.HEALTHY and agent.status != AgentStatus.HEALTHY:
            logger.info(f"Agent {agent.instance_id} recovered to healthy status")
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics for all agents."""
        for agent in self.agent_instances.values():
            # Simulate performance metric updates
            agent.avg_response_time_ms = max(50, agent.avg_response_time_ms + (hash(agent.instance_id) % 21 - 10))
            agent.active_connections = max(0, agent.active_connections + (hash(str(time.time())) % 11 - 5))
    
    async def _check_and_execute_failover(self) -> None:
        """Check for failover conditions and execute if necessary."""
        for agent_type in self.agent_types:
            type_agents = [a for a in self.agent_instances.values() if a.agent_type == agent_type]
            healthy_agents = [a for a in type_agents if a.status == AgentStatus.HEALTHY]
            
            # Check if we need failover (less than 50% healthy agents)
            if len(healthy_agents) < len(type_agents) * 0.5:
                await self._execute_failover(agent_type, type_agents)
    
    async def _execute_failover(self, agent_type: str, agents: List[AgentInstance]) -> None:
        """Execute failover for an agent type."""
        # Check cooldown
        last_failover = self.last_failover.get(agent_type)
        if last_failover and datetime.utcnow() - last_failover < timedelta(seconds=self.failover_cooldown_seconds):
            return
        
        logger.warning(f"Executing failover for agent type: {agent_type}")
        
        # Simulate failover actions
        unhealthy_agents = [a for a in agents if a.status == AgentStatus.UNHEALTHY]
        
        for agent in unhealthy_agents:
            # Simulate restarting unhealthy agents
            agent.status = AgentStatus.STARTING
            logger.info(f"Restarting agent: {agent.instance_id}")
            
            # Simulate restart delay
            await asyncio.sleep(0.1)
            
            # Mark as healthy after restart
            agent.status = AgentStatus.HEALTHY
            agent.health_score = 0.8  # Slightly lower after restart
            agent.active_connections = 0
            
        self.last_failover[agent_type] = datetime.utcnow()
        logger.info(f"Failover completed for agent type: {agent_type}")
    
    async def route_request(self, agent_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request to the best available agent instance."""
        # Get available agents for the type
        type_agents = [a for a in self.agent_instances.values() if a.agent_type == agent_type]
        
        # Select best agent using load balancer
        selected_agent = self.load_balancer.select_agent(type_agents, agent_type)
        
        if not selected_agent:
            raise Exception(f"No healthy agents available for type: {agent_type}")
        
        # Simulate request processing
        start_time = time.time()
        
        try:
            # Update agent metrics
            selected_agent.active_connections += 1
            selected_agent.total_requests += 1
            
            # Simulate processing time
            processing_time = selected_agent.avg_response_time_ms / 1000.0
            await asyncio.sleep(processing_time)
            
            # Mock successful response
            response = {
                "success": True,
                "agent_id": selected_agent.instance_id,
                "agent_type": agent_type,
                "processing_time_ms": processing_time * 1000,
                "data": f"Processed by {selected_agent.instance_id}"
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Request failed on agent {selected_agent.instance_id}: {e}")
            raise
            
        finally:
            # Update agent metrics
            selected_agent.active_connections = max(0, selected_agent.active_connections - 1)
            
            # Update average response time
            actual_time = (time.time() - start_time) * 1000
            selected_agent.avg_response_time_ms = (
                selected_agent.avg_response_time_ms * 0.9 + actual_time * 0.1
            )
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        # Count agents by status
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = len([
                a for a in self.agent_instances.values() 
                if a.status == status
            ])
        
        # Count agents by type
        type_counts = {}
        for agent_type in self.agent_types:
            type_agents = [a for a in self.agent_instances.values() if a.agent_type == agent_type]
            healthy_count = len([a for a in type_agents if a.status == AgentStatus.HEALTHY])
            type_counts[agent_type] = {
                "total": len(type_agents),
                "healthy": healthy_count,
                "health_percentage": (healthy_count / len(type_agents) * 100) if type_agents else 0
            }
        
        return {
            "orchestration_active": self.orchestration_active,
            "total_agents": len(self.agent_instances),
            "agent_status_counts": status_counts,
            "agent_type_health": type_counts,
            "load_balancing_strategy": self.load_balancer.strategy.value,
            "auto_failover_enabled": self.enable_auto_failover,
            "last_health_check": max(
                (a.last_health_check for a in self.agent_instances.values()),
                default=datetime.utcnow()
            ).isoformat()
        }
    
    def get_agent_details(self, instance_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about agents."""
        if instance_id:
            agent = self.agent_instances.get(instance_id)
            return asdict(agent) if agent else {}
        else:
            return {
                instance_id: asdict(agent) 
                for instance_id, agent in self.agent_instances.items()
            }


# Global orchestrator instance
_system_orchestrator: Optional[SystemOrchestrator] = None


def get_system_orchestrator() -> SystemOrchestrator:
    """Get the global system orchestrator instance."""
    global _system_orchestrator
    if _system_orchestrator is None:
        _system_orchestrator = SystemOrchestrator()
    return _system_orchestrator


def set_system_orchestrator(orchestrator: SystemOrchestrator) -> None:
    """Set the global system orchestrator instance."""
    global _system_orchestrator
    _system_orchestrator = orchestrator
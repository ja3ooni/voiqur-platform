"""
EUVoice AI Multi-Agent Framework.
Main integration class that brings together all core components.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .core import (
    MessageRouter, ServiceRegistry, AgentOrchestrator, 
    CoordinationController, QualityMonitor, SharedKnowledgeBase,
    AgentRegistration, Task, AgentCapability, KnowledgeItem
)


logger = logging.getLogger(__name__)


class MultiAgentFramework:
    """
    Main multi-agent framework that integrates all core components.
    Provides a unified interface for managing the multi-agent system.
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 postgres_url: str = "postgresql://localhost:5432/euvoice"):
        """
        Initialize the multi-agent framework.
        
        Args:
            redis_url: Redis connection URL for caching and messaging
            postgres_url: PostgreSQL connection URL for persistent storage
        """
        # Core components
        self.message_router = MessageRouter()
        self.service_registry = ServiceRegistry(self.message_router)
        self.orchestrator = AgentOrchestrator(self.message_router, self.service_registry)
        self.coordination_controller = CoordinationController(self.message_router)
        self.quality_monitor = QualityMonitor(self.message_router)
        self.knowledge_base = SharedKnowledgeBase(
            self.message_router, redis_url, postgres_url
        )
        
        # Framework state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        # Statistics
        self.stats = {
            "framework_start_time": None,
            "total_agents_registered": 0,
            "total_tasks_processed": 0,
            "total_messages_sent": 0
        }
    
    async def start(self) -> None:
        """Start the multi-agent framework."""
        if self.is_running:
            logger.warning("Framework is already running")
            return
        
        logger.info("Starting EUVoice AI Multi-Agent Framework")
        
        try:
            # Start all core components
            await self.service_registry.start()
            await self.orchestrator.start()
            await self.coordination_controller.start()
            await self.quality_monitor.start()
            await self.knowledge_base.start()
            
            self.is_running = True
            self.start_time = datetime.utcnow()
            self.stats["framework_start_time"] = self.start_time.isoformat()
            
            logger.info("Multi-Agent Framework started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start framework: {e}")
            await self.stop()  # Cleanup on failure
            raise
    
    async def stop(self) -> None:
        """Stop the multi-agent framework."""
        if not self.is_running:
            return
        
        logger.info("Stopping EUVoice AI Multi-Agent Framework")
        
        # Stop all components in reverse order
        await self.knowledge_base.stop()
        await self.quality_monitor.stop()
        await self.coordination_controller.stop()
        await self.orchestrator.stop()
        await self.service_registry.stop()
        
        self.is_running = False
        logger.info("Multi-Agent Framework stopped")
    
    async def register_agent(self, registration: AgentRegistration) -> bool:
        """
        Register a new agent in the framework.
        
        Args:
            registration: Agent registration information
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Register with service registry
            success = await self.service_registry.register_agent(registration)
            
            if success:
                # Register with quality monitor
                await self.quality_monitor.register_agent(registration.agent_id)
                
                self.stats["total_agents_registered"] += 1
                logger.info(f"Agent {registration.agent_id} registered successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to register agent {registration.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the framework.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            # Unregister from all components
            await self.service_registry.unregister_agent(agent_id)
            await self.quality_monitor.unregister_agent(agent_id)
            
            logger.info(f"Agent {agent_id} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def submit_task(self, task: Task) -> bool:
        """
        Submit a task for execution by the framework.
        
        Args:
            task: Task to be executed
            
        Returns:
            True if task submitted successfully, False otherwise
        """
        try:
            success = await self.orchestrator.submit_task(task)
            
            if success:
                self.stats["total_tasks_processed"] += 1
                logger.info(f"Task {task.task_id} submitted successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit task {task.task_id}: {e}")
            return False
    
    async def store_knowledge(self, knowledge: KnowledgeItem) -> bool:
        """
        Store knowledge in the shared knowledge base.
        
        Args:
            knowledge: Knowledge item to store
            
        Returns:
            True if storage successful, False otherwise
        """
        try:
            return await self.knowledge_base.store_knowledge(knowledge)
            
        except Exception as e:
            logger.error(f"Failed to store knowledge {knowledge.knowledge_id}: {e}")
            return False
    
    async def get_knowledge(self, knowledge_id: str, requester_agent_id: str) -> Optional[KnowledgeItem]:
        """
        Retrieve knowledge from the shared knowledge base.
        
        Args:
            knowledge_id: ID of the knowledge item
            requester_agent_id: ID of the requesting agent
            
        Returns:
            Knowledge item if found and accessible, None otherwise
        """
        try:
            return await self.knowledge_base.get_knowledge(knowledge_id, requester_agent_id)
            
        except Exception as e:
            logger.error(f"Failed to get knowledge {knowledge_id}: {e}")
            return None
    
    def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health information for a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Health summary if agent exists, None otherwise
        """
        return self.quality_monitor.get_agent_health_summary(agent_id)
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health information.
        
        Returns:
            System health summary
        """
        return self.quality_monitor.get_system_health_summary()
    
    def get_framework_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive framework statistics.
        
        Returns:
            Dictionary containing framework statistics
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "framework_status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime,
            "stats": self.stats,
            "message_router": self.message_router.get_system_stats(),
            "service_registry": self.service_registry.get_registry_stats(),
            "orchestrator": self.orchestrator.get_orchestrator_stats(),
            "coordination": self.coordination_controller.get_coordination_stats(),
            "quality_monitor": self.quality_monitor.get_system_health_summary(),
            "knowledge_base": self.knowledge_base.get_knowledge_stats()
        }
    
    async def create_workflow(self, workflow_id: str, description: str, 
                            steps: List[Dict[str, Any]]) -> bool:
        """
        Create a multi-agent workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            description: Workflow description
            steps: List of workflow steps
            
        Returns:
            True if workflow created successfully, False otherwise
        """
        try:
            from .core.coordination import Workflow, WorkflowStep
            
            workflow = Workflow(workflow_id, description)
            
            # Add steps to workflow
            for step_data in steps:
                step = WorkflowStep(
                    step_id=step_data["step_id"],
                    agent_id=step_data["agent_id"],
                    task=Task(**step_data["task"]),
                    dependencies=step_data.get("dependencies", []),
                    sync_points=step_data.get("sync_points", [])
                )
                workflow.add_step(step)
            
            return await self.coordination_controller.create_workflow(workflow)
            
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_id}: {e}")
            return False
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """
        Execute a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            True if execution started successfully, False otherwise
        """
        try:
            return await self.coordination_controller.execute_workflow(workflow_id)
            
        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            return False
    
    async def find_agent_for_capability(self, capability_name: str, 
                                      criteria: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Find the best agent for a specific capability.
        
        Args:
            capability_name: Name of the required capability
            criteria: Selection criteria
            
        Returns:
            Agent ID if found, None otherwise
        """
        try:
            registration = self.service_registry.find_best_agent_for_capability(
                capability_name, criteria
            )
            return registration.agent_id if registration else None
            
        except Exception as e:
            logger.error(f"Failed to find agent for capability {capability_name}: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Convenience function for creating and starting the framework
async def create_framework(redis_url: str = "redis://localhost:6379",
                          postgres_url: str = "postgresql://localhost:5432/euvoice") -> MultiAgentFramework:
    """
    Create and start a new multi-agent framework instance.
    
    Args:
        redis_url: Redis connection URL
        postgres_url: PostgreSQL connection URL
        
    Returns:
        Started MultiAgentFramework instance
    """
    framework = MultiAgentFramework(redis_url, postgres_url)
    await framework.start()
    return framework
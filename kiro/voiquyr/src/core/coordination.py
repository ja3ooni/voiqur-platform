"""
Coordination Controller for managing agent dependencies and synchronization.
Handles complex multi-agent workflows and coordination patterns.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import json

from .models import (
    Task, AgentState, AgentMessage, TaskStatus, AgentStatus, 
    Priority, MessageType, AgentCapability
)
from .messaging import MessageRouter, MessageBus
from .orchestration import CoordinationEvent


logger = logging.getLogger(__name__)


class SynchronizationPoint:
    """Represents a synchronization point where multiple agents must coordinate."""
    
    def __init__(self, sync_id: str, required_agents: List[str], 
                 completion_criteria: Dict[str, Any], timeout: timedelta):
        self.sync_id = sync_id
        self.required_agents = set(required_agents)
        self.completion_criteria = completion_criteria
        self.timeout = timeout
        self.created_at = datetime.utcnow()
        self.completed_agents: Set[str] = set()
        self.is_completed = False
        self.is_timed_out = False
        self.result_data: Dict[str, Any] = {}
    
    def add_agent_completion(self, agent_id: str, data: Dict[str, Any]) -> bool:
        """Mark an agent as completed for this sync point."""
        if agent_id not in self.required_agents:
            return False
        
        self.completed_agents.add(agent_id)
        self.result_data[agent_id] = data
        
        # Check if all agents have completed
        if self.completed_agents == self.required_agents:
            self.is_completed = True
        
        return True
    
    def is_expired(self) -> bool:
        """Check if the synchronization point has expired."""
        if self.is_timed_out:
            return True
        
        elapsed = datetime.utcnow() - self.created_at
        if elapsed > self.timeout:
            self.is_timed_out = True
            return True
        
        return False
    
    def get_waiting_agents(self) -> Set[str]:
        """Get agents that haven't completed this sync point."""
        return self.required_agents - self.completed_agents


class WorkflowStep:
    """Represents a step in a multi-agent workflow."""
    
    def __init__(self, step_id: str, agent_id: str, task: Task, 
                 dependencies: List[str] = None, sync_points: List[str] = None):
        self.step_id = step_id
        self.agent_id = agent_id
        self.task = task
        self.dependencies = dependencies or []
        self.sync_points = sync_points or []
        self.status = TaskStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None


class Workflow:
    """Represents a multi-agent workflow with dependencies and synchronization."""
    
    def __init__(self, workflow_id: str, description: str):
        self.workflow_id = workflow_id
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.sync_points: Dict[str, SynchronizationPoint] = {}
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
    
    def add_sync_point(self, sync_point: SynchronizationPoint) -> None:
        """Add a synchronization point to the workflow."""
        self.sync_points[sync_point.sync_id] = sync_point
    
    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (dependencies satisfied)."""
        ready_steps = []
        
        for step in self.steps.values():
            if step.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_satisfied = True
            for dep_step_id in step.dependencies:
                if dep_step_id in self.steps:
                    dep_step = self.steps[dep_step_id]
                    if dep_step.status != TaskStatus.COMPLETED:
                        dependencies_satisfied = False
                        break
            
            # Check if all required sync points are completed
            sync_points_satisfied = True
            for sync_id in step.sync_points:
                if sync_id in self.sync_points:
                    sync_point = self.sync_points[sync_id]
                    if not sync_point.is_completed:
                        sync_points_satisfied = False
                        break
            
            if dependencies_satisfied and sync_points_satisfied:
                ready_steps.append(step)
        
        return ready_steps
    
    def is_completed(self) -> bool:
        """Check if the workflow is completed."""
        return all(step.status == TaskStatus.COMPLETED for step in self.steps.values())
    
    def has_failed_steps(self) -> bool:
        """Check if any steps have failed."""
        return any(step.status == TaskStatus.FAILED for step in self.steps.values())


class ConflictResolution:
    """Handles conflict resolution for concurrent agent operations."""
    
    def __init__(self):
        self.resolution_strategies: Dict[str, Callable] = {
            "timestamp_priority": self._timestamp_priority_resolution,
            "agent_priority": self._agent_priority_resolution,
            "task_priority": self._task_priority_resolution,
            "merge_strategy": self._merge_strategy_resolution
        }
        self.agent_priorities: Dict[str, int] = {}
    
    async def resolve_conflict(self, conflict_type: str, conflicting_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve a conflict between multiple operations."""
        strategy = conflict_type.split("_")[-1] if "_" in conflict_type else "timestamp_priority"
        
        if strategy in self.resolution_strategies:
            return await self.resolution_strategies[strategy](conflicting_operations)
        else:
            return await self._timestamp_priority_resolution(conflicting_operations)
    
    async def _timestamp_priority_resolution(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflict by timestamp (first wins)."""
        if not operations:
            return {}
        
        earliest_op = min(operations, key=lambda op: op.get("timestamp", datetime.max))
        return {"winner": earliest_op, "strategy": "timestamp_priority"}
    
    async def _agent_priority_resolution(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflict by agent priority."""
        if not operations:
            return {}
        
        highest_priority_op = None
        highest_priority = -1
        
        for op in operations:
            agent_id = op.get("agent_id")
            priority = self.agent_priorities.get(agent_id, 0)
            if priority > highest_priority:
                highest_priority = priority
                highest_priority_op = op
        
        return {"winner": highest_priority_op or operations[0], "strategy": "agent_priority"}
    
    async def _task_priority_resolution(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflict by task priority."""
        if not operations:
            return {}
        
        highest_priority_op = max(operations, key=lambda op: op.get("task_priority", 0))
        return {"winner": highest_priority_op, "strategy": "task_priority"}
    
    async def _merge_strategy_resolution(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflict by merging compatible operations."""
        if not operations:
            return {}
        
        # Simple merge strategy - combine data from all operations
        merged_data = {}
        for op in operations:
            if "data" in op:
                merged_data.update(op["data"])
        
        return {"winner": {"merged_data": merged_data}, "strategy": "merge_strategy"}
    
    def set_agent_priority(self, agent_id: str, priority: int) -> None:
        """Set priority for an agent in conflict resolution."""
        self.agent_priorities[agent_id] = priority


class CoordinationController:
    """
    Central coordination controller for managing agent dependencies and synchronization.
    Handles complex multi-agent workflows, synchronization points, and conflict resolution.
    """
    
    def __init__(self, message_router: MessageRouter):
        self.message_router = message_router
        self.message_bus = MessageBus(message_router)
        
        # Workflow management
        self.workflows: Dict[str, Workflow] = {}
        self.active_sync_points: Dict[str, SynchronizationPoint] = {}
        
        # Coordination state
        self.agent_dependencies: Dict[str, Set[str]] = defaultdict(set)  # agent -> dependencies
        self.blocked_agents: Set[str] = set()
        self.coordination_events: deque = deque(maxlen=1000)  # Event history
        
        # Conflict resolution
        self.conflict_resolver = ConflictResolution()
        self.pending_conflicts: Dict[str, List[Dict[str, Any]]] = {}
        
        # Configuration
        self.sync_point_timeout = timedelta(minutes=10)
        self.coordination_interval = 2.0  # seconds
        
        # Runtime state
        self.coordination_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Event callbacks
        self.event_callbacks: Dict[CoordinationEvent, List[Callable]] = defaultdict(list)
    
    async def start(self) -> None:
        """Start the coordination controller."""
        if self.is_running:
            return
        
        logger.info("Starting Coordination Controller")
        self.is_running = True
        self.coordination_task = asyncio.create_task(self._coordination_loop())
    
    async def stop(self) -> None:
        """Stop the coordination controller."""
        if not self.is_running:
            return
        
        logger.info("Stopping Coordination Controller")
        self.is_running = False
        
        if self.coordination_task:
            self.coordination_task.cancel()
            try:
                await self.coordination_task
            except asyncio.CancelledError:
                pass
    
    async def create_workflow(self, workflow: Workflow) -> bool:
        """Create a new multi-agent workflow."""
        try:
            self.workflows[workflow.workflow_id] = workflow
            
            # Register sync points
            for sync_point in workflow.sync_points.values():
                self.active_sync_points[sync_point.sync_id] = sync_point
            
            logger.info(f"Workflow {workflow.workflow_id} created with {len(workflow.steps)} steps")
            await self._emit_coordination_event(CoordinationEvent.TASK_ASSIGNED, {
                "workflow_id": workflow.workflow_id,
                "steps_count": len(workflow.steps)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow.workflow_id}: {e}")
            return False
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            logger.error(f"Workflow {workflow_id} not found")
            return False
        
        workflow = self.workflows[workflow_id]
        workflow.status = TaskStatus.IN_PROGRESS
        workflow.started_at = datetime.utcnow()
        
        logger.info(f"Starting execution of workflow {workflow_id}")
        return True
    
    async def add_agent_dependency(self, agent_id: str, depends_on: str) -> None:
        """Add a dependency between agents."""
        self.agent_dependencies[agent_id].add(depends_on)
        
        # Check if this creates a circular dependency
        if self._has_circular_dependency(agent_id):
            logger.error(f"Circular dependency detected involving agent {agent_id}")
            self.agent_dependencies[agent_id].discard(depends_on)
            return
        
        logger.info(f"Added dependency: {agent_id} depends on {depends_on}")
    
    async def remove_agent_dependency(self, agent_id: str, depends_on: str) -> None:
        """Remove a dependency between agents."""
        self.agent_dependencies[agent_id].discard(depends_on)
        
        # Check if agent can be unblocked
        if agent_id in self.blocked_agents and not self.agent_dependencies[agent_id]:
            await self._unblock_agent(agent_id)
        
        logger.info(f"Removed dependency: {agent_id} no longer depends on {depends_on}")
    
    async def create_sync_point(self, sync_id: str, required_agents: List[str], 
                              completion_criteria: Dict[str, Any], 
                              timeout: Optional[timedelta] = None) -> bool:
        """Create a synchronization point."""
        try:
            timeout = timeout or self.sync_point_timeout
            sync_point = SynchronizationPoint(sync_id, required_agents, completion_criteria, timeout)
            self.active_sync_points[sync_id] = sync_point
            
            # Notify required agents about the sync point
            await self.message_bus.send_notification(
                sender_id="coordination_controller",
                notification_data={
                    "event": "sync_point_created",
                    "sync_id": sync_id,
                    "completion_criteria": completion_criteria,
                    "timeout": timeout.total_seconds()
                },
                recipients=required_agents
            )
            
            logger.info(f"Sync point {sync_id} created for agents: {required_agents}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create sync point {sync_id}: {e}")
            return False
    
    async def agent_sync_completion(self, sync_id: str, agent_id: str, data: Dict[str, Any]) -> bool:
        """Mark an agent as completed for a sync point."""
        if sync_id not in self.active_sync_points:
            logger.error(f"Sync point {sync_id} not found")
            return False
        
        sync_point = self.active_sync_points[sync_id]
        success = sync_point.add_agent_completion(agent_id, data)
        
        if success:
            logger.info(f"Agent {agent_id} completed sync point {sync_id}")
            
            # Check if sync point is now complete
            if sync_point.is_completed:
                await self._handle_sync_point_completion(sync_point)
        
        return success
    
    async def report_conflict(self, conflict_id: str, conflict_type: str, 
                            conflicting_operations: List[Dict[str, Any]]) -> None:
        """Report a conflict that needs resolution."""
        self.pending_conflicts[conflict_id] = conflicting_operations
        
        logger.warning(f"Conflict reported: {conflict_id} ({conflict_type})")
        
        # Attempt to resolve immediately
        resolution = await self.conflict_resolver.resolve_conflict(conflict_type, conflicting_operations)
        
        # Notify involved agents about the resolution
        involved_agents = set()
        for op in conflicting_operations:
            if "agent_id" in op:
                involved_agents.add(op["agent_id"])
        
        await self.message_bus.send_notification(
            sender_id="coordination_controller",
            notification_data={
                "event": "conflict_resolved",
                "conflict_id": conflict_id,
                "resolution": resolution
            },
            recipients=list(involved_agents)
        )
        
        # Remove from pending conflicts
        if conflict_id in self.pending_conflicts:
            del self.pending_conflicts[conflict_id]
    
    async def _coordination_loop(self) -> None:
        """Main coordination loop."""
        while self.is_running:
            try:
                await self._process_workflows()
                await self._check_sync_point_timeouts()
                await self._check_blocked_agents()
                await asyncio.sleep(self.coordination_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(self.coordination_interval)
    
    async def _process_workflows(self) -> None:
        """Process active workflows."""
        for workflow in self.workflows.values():
            if workflow.status != TaskStatus.IN_PROGRESS:
                continue
            
            # Get ready steps
            ready_steps = workflow.get_ready_steps()
            
            # Execute ready steps
            for step in ready_steps:
                await self._execute_workflow_step(workflow, step)
            
            # Check if workflow is completed
            if workflow.is_completed():
                workflow.status = TaskStatus.COMPLETED
                workflow.completed_at = datetime.utcnow()
                logger.info(f"Workflow {workflow.workflow_id} completed")
                
                await self._emit_coordination_event(CoordinationEvent.TASK_COMPLETED, {
                    "workflow_id": workflow.workflow_id
                })
            
            # Check if workflow has failed
            elif workflow.has_failed_steps():
                workflow.status = TaskStatus.FAILED
                workflow.completed_at = datetime.utcnow()
                logger.error(f"Workflow {workflow.workflow_id} failed")
                
                await self._emit_coordination_event(CoordinationEvent.TASK_FAILED, {
                    "workflow_id": workflow.workflow_id
                })
    
    async def _execute_workflow_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a workflow step."""
        try:
            step.status = TaskStatus.IN_PROGRESS
            step.started_at = datetime.utcnow()
            
            # Send task to agent
            task_message = AgentMessage(
                sender_id="coordination_controller",
                receiver_id=step.agent_id,
                message_type=MessageType.REQUEST,
                payload={
                    "action": "execute_workflow_step",
                    "workflow_id": workflow.workflow_id,
                    "step_id": step.step_id,
                    "task": step.task.dict()
                },
                priority=step.task.priority,
                correlation_id=f"workflow_{workflow.workflow_id}_step_{step.step_id}"
            )
            
            await self.message_router.send_message(task_message)
            
            logger.info(f"Workflow step {step.step_id} sent to agent {step.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute workflow step {step.step_id}: {e}")
            step.status = TaskStatus.FAILED
            step.error_message = str(e)
    
    async def _check_sync_point_timeouts(self) -> None:
        """Check for timed out synchronization points."""
        expired_sync_points = []
        
        for sync_id, sync_point in self.active_sync_points.items():
            if sync_point.is_expired() and not sync_point.is_completed:
                expired_sync_points.append(sync_id)
        
        # Handle expired sync points
        for sync_id in expired_sync_points:
            await self._handle_sync_point_timeout(sync_id)
    
    async def _handle_sync_point_timeout(self, sync_id: str) -> None:
        """Handle a timed out sync point."""
        sync_point = self.active_sync_points[sync_id]
        waiting_agents = sync_point.get_waiting_agents()
        
        logger.warning(f"Sync point {sync_id} timed out. Waiting agents: {waiting_agents}")
        
        # Notify all agents about the timeout
        all_agents = list(sync_point.required_agents)
        await self.message_bus.send_notification(
            sender_id="coordination_controller",
            notification_data={
                "event": "sync_point_timeout",
                "sync_id": sync_id,
                "waiting_agents": list(waiting_agents)
            },
            recipients=all_agents
        )
        
        # Remove from active sync points
        del self.active_sync_points[sync_id]
    
    async def _handle_sync_point_completion(self, sync_point: SynchronizationPoint) -> None:
        """Handle completion of a sync point."""
        logger.info(f"Sync point {sync_point.sync_id} completed")
        
        # Notify all agents about completion
        all_agents = list(sync_point.required_agents)
        await self.message_bus.send_notification(
            sender_id="coordination_controller",
            notification_data={
                "event": "sync_point_completed",
                "sync_id": sync_point.sync_id,
                "result_data": sync_point.result_data
            },
            recipients=all_agents
        )
        
        # Remove from active sync points
        if sync_point.sync_id in self.active_sync_points:
            del self.active_sync_points[sync_point.sync_id]
        
        await self._emit_coordination_event(CoordinationEvent.DEPENDENCY_RESOLVED, {
            "sync_id": sync_point.sync_id
        })
    
    async def _check_blocked_agents(self) -> None:
        """Check if any blocked agents can be unblocked."""
        agents_to_unblock = []
        
        for agent_id in self.blocked_agents:
            # Check if all dependencies are resolved
            dependencies_resolved = True
            for dep_agent_id in self.agent_dependencies[agent_id]:
                dep_agent_state = self.message_router.get_agent_state(dep_agent_id)
                if not dep_agent_state or dep_agent_state.status == AgentStatus.BLOCKED:
                    dependencies_resolved = False
                    break
            
            if dependencies_resolved:
                agents_to_unblock.append(agent_id)
        
        # Unblock agents
        for agent_id in agents_to_unblock:
            await self._unblock_agent(agent_id)
    
    async def _unblock_agent(self, agent_id: str) -> None:
        """Unblock an agent."""
        self.blocked_agents.discard(agent_id)
        
        # Update agent state
        agent_state = self.message_router.get_agent_state(agent_id)
        if agent_state:
            agent_state.status = AgentStatus.IDLE
        
        # Notify agent
        await self.message_bus.send_notification(
            sender_id="coordination_controller",
            notification_data={
                "event": "agent_unblocked"
            },
            recipients=[agent_id]
        )
        
        logger.info(f"Agent {agent_id} unblocked")
        await self._emit_coordination_event(CoordinationEvent.AGENT_UNBLOCKED, {
            "agent_id": agent_id
        })
    
    def _has_circular_dependency(self, agent_id: str) -> bool:
        """Check if adding a dependency would create a circular dependency."""
        visited = set()
        rec_stack = set()
        
        def dfs(current_agent: str) -> bool:
            visited.add(current_agent)
            rec_stack.add(current_agent)
            
            for dep_agent in self.agent_dependencies[current_agent]:
                if dep_agent not in visited:
                    if dfs(dep_agent):
                        return True
                elif dep_agent in rec_stack:
                    return True
            
            rec_stack.remove(current_agent)
            return False
        
        return dfs(agent_id)
    
    async def _emit_coordination_event(self, event: CoordinationEvent, data: Dict[str, Any]) -> None:
        """Emit a coordination event."""
        event_data = {
            "event": event.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        self.coordination_events.append(event_data)
        
        # Call event callbacks
        for callback in self.event_callbacks[event]:
            try:
                await callback(event_data)
            except Exception as e:
                logger.error(f"Error in coordination event callback: {e}")
    
    def add_event_callback(self, event: CoordinationEvent, callback: Callable) -> None:
        """Add a callback for coordination events."""
        self.event_callbacks[event].append(callback)
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        return {
            "active_workflows": len([w for w in self.workflows.values() if w.status == TaskStatus.IN_PROGRESS]),
            "completed_workflows": len([w for w in self.workflows.values() if w.status == TaskStatus.COMPLETED]),
            "failed_workflows": len([w for w in self.workflows.values() if w.status == TaskStatus.FAILED]),
            "active_sync_points": len(self.active_sync_points),
            "blocked_agents": len(self.blocked_agents),
            "pending_conflicts": len(self.pending_conflicts),
            "total_events": len(self.coordination_events)
        }
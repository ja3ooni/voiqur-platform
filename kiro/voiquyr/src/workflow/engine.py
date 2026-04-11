"""
Workflow Execution Engine — distributed execution, event triggers,
scheduled tasks, retry logic, and execution logging.
Implements Requirements 18.4, 18.5.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .builder import NodeType, Workflow, WorkflowNode


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TriggerType(Enum):
    MANUAL = "manual"
    EVENT = "event"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"


@dataclass
class NodeExecutionLog:
    node_id: str
    node_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    output: Optional[Any] = None
    error: Optional[str] = None
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status.value,
            "error": self.error,
            "attempt": self.attempt,
        }


@dataclass
class WorkflowExecution:
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    trigger_type: TriggerType = TriggerType.MANUAL
    status: ExecutionStatus = ExecutionStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    node_logs: List[NodeExecutionLog] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "node_logs": [l.to_dict() for l in self.node_logs],
        }


# ---------------------------------------------------------------------------
# Action registry — maps node action names to async callables
# ---------------------------------------------------------------------------

ActionFn = Callable[[Dict[str, Any], Dict[str, Any]], Any]


class ActionRegistry:
    def __init__(self):
        self._actions: Dict[str, ActionFn] = {}

    def register(self, name: str, fn: ActionFn) -> None:
        self._actions[name] = fn

    def get(self, name: str) -> Optional[ActionFn]:
        return self._actions.get(name)

    def list_actions(self) -> List[str]:
        return list(self._actions.keys())


# ---------------------------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """
    Executes workflows node-by-node with retry, error handling, and logging.
    Supports event-driven and scheduled triggers.
    """

    def __init__(
        self,
        action_registry: Optional[ActionRegistry] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.registry = action_registry or ActionRegistry()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._executions: Dict[str, WorkflowExecution] = {}
        self._event_handlers: Dict[str, List[str]] = {}   # event_name → [workflow_id]
        self._workflows: Dict[str, Workflow] = {}
        self._scheduled: List[Dict[str, Any]] = []
        self._scheduler_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

    def register_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow

    def subscribe_to_event(self, event_name: str, workflow_id: str) -> None:
        self._event_handlers.setdefault(event_name, []).append(workflow_id)

    def schedule(self, workflow_id: str, cron_expr: str, context: Optional[Dict] = None) -> None:
        """Register a workflow for scheduled execution (simplified cron)."""
        self._scheduled.append({
            "workflow_id": workflow_id,
            "cron": cron_expr,
            "context": context or {},
        })

    async def fire_event(self, event_name: str, payload: Dict[str, Any]) -> List[WorkflowExecution]:
        """Trigger all workflows subscribed to an event."""
        executions = []
        for wf_id in self._event_handlers.get(event_name, []):
            wf = self._workflows.get(wf_id)
            if wf:
                ex = await self.execute(wf, {**payload, "_event": event_name},
                                        trigger=TriggerType.EVENT)
                executions.append(ex)
        return executions

    async def execute(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None,
        trigger: TriggerType = TriggerType.MANUAL,
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow.workflow_id,
            trigger_type=trigger,
            status=ExecutionStatus.RUNNING,
            context=dict(context or {}),
        )
        self._executions[execution.execution_id] = execution
        self.logger.info(f"Executing workflow {workflow.workflow_id} [{execution.execution_id}]")

        try:
            errors = workflow.validate()
            if errors:
                raise ValueError(f"Invalid workflow: {errors}")

            current_id = workflow.entry_node_id
            while current_id:
                node = workflow.nodes.get(current_id)
                if not node:
                    break
                current_id = await self._execute_node(node, execution)

            execution.status = ExecutionStatus.COMPLETED
        except asyncio.CancelledError:
            execution.status = ExecutionStatus.CANCELLED
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            self.logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
        finally:
            execution.finished_at = datetime.utcnow()

        return execution

    async def _execute_node(
        self, node: WorkflowNode, execution: WorkflowExecution
    ) -> Optional[str]:
        """Execute a single node. Returns the ID of the next node to execute."""
        log = NodeExecutionLog(
            node_id=node.node_id,
            node_name=node.name,
            started_at=datetime.utcnow(),
        )
        execution.node_logs.append(log)

        try:
            if node.node_type == NodeType.TRIGGER:
                log.status = ExecutionStatus.COMPLETED
                log.finished_at = datetime.utcnow()
                return node.next_node_id
            elif node.node_type == NodeType.CONDITION:
                return await self._exec_condition(node, execution, log)
            elif node.node_type == NodeType.LOOP:
                return await self._exec_loop(node, execution, log)
            elif node.node_type == NodeType.PARALLEL:
                return await self._exec_parallel(node, execution, log)
            elif node.node_type == NodeType.DELAY:
                delay = node.config.get("seconds", 0)
                await asyncio.sleep(delay)
                log.output = f"Delayed {delay}s"
            elif node.node_type == NodeType.TRANSFORM:
                output = self._exec_transform(node, execution.context)
                execution.context.update(output)
                log.output = output
            elif node.node_type == NodeType.END:
                log.status = ExecutionStatus.COMPLETED
                log.finished_at = datetime.utcnow()
                return None
            else:
                output = await self._exec_action_with_retry(node, execution)
                if output is not None:
                    execution.context[f"_output_{node.node_id}"] = output
                log.output = output

            log.status = ExecutionStatus.COMPLETED
        except Exception as e:
            log.status = ExecutionStatus.FAILED
            log.error = str(e)
            raise
        finally:
            log.finished_at = datetime.utcnow()

        return node.next_node_id

    async def _exec_action_with_retry(
        self, node: WorkflowNode, execution: WorkflowExecution
    ) -> Any:
        action_name = node.config.get("action", "")
        fn = self.registry.get(action_name)
        if not fn:
            raise ValueError(f"Unknown action: {action_name}")

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = fn(node.config, execution.context)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as e:
                last_err = e
                self.logger.warning(f"Action {action_name} attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
        raise last_err

    async def _exec_condition(
        self, node: WorkflowNode, execution: WorkflowExecution, log: NodeExecutionLog
    ) -> Optional[str]:
        from .builder import ConditionGroup, Condition, ConditionOperator
        cg_data = node.config.get("condition_group")
        if cg_data:
            conditions = [
                Condition(
                    field=c["field"],
                    operator=ConditionOperator(c["operator"]),
                    value=c.get("value"),
                )
                for c in cg_data.get("conditions", [])
            ]
            cg = ConditionGroup(conditions=conditions, logic=cg_data.get("logic", "AND"))
            result = cg.evaluate(execution.context)
        else:
            result = bool(execution.context.get(node.config.get("field", ""), False))

        log.output = {"condition_result": result}
        return node.true_branch_id if result else node.false_branch_id

    async def _exec_loop(
        self, node: WorkflowNode, execution: WorkflowExecution, log: NodeExecutionLog
    ) -> Optional[str]:
        items = execution.context.get(node.config.get("items_field", "items"), [])
        iterations = 0
        for item in items:
            execution.context["_loop_item"] = item
            execution.context["_loop_index"] = iterations
            body_id = node.loop_body_id
            while body_id:
                body_node = execution.context.get("_workflow_nodes", {}).get(body_id)
                if not body_node:
                    break
                body_id = await self._execute_node(body_node, execution)
            iterations += 1
        log.output = {"iterations": iterations}
        return node.next_node_id

    async def _exec_parallel(
        self, node: WorkflowNode, execution: WorkflowExecution, log: NodeExecutionLog
    ) -> Optional[str]:
        # Execute all branches concurrently
        tasks = []
        for branch_id in node.parallel_branch_ids:
            branch_node = execution.context.get("_workflow_nodes", {}).get(branch_id)
            if branch_node:
                tasks.append(self._execute_node(branch_node, execution))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.output = {"branches": len(tasks)}
        return node.next_node_id

    def _exec_transform(self, node: WorkflowNode, context: Dict) -> Dict:
        from .connectors import DataTransformer
        ops = node.config.get("operations", [])
        field = node.config.get("input_field", "")
        data = context.get(field, context)
        return DataTransformer().transform(data, ops)

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def get_executions(self, workflow_id: Optional[str] = None) -> List[WorkflowExecution]:
        execs = list(self._executions.values())
        if workflow_id:
            execs = [e for e in execs if e.workflow_id == workflow_id]
        return execs

    async def cancel(self, execution_id: str) -> bool:
        ex = self._executions.get(execution_id)
        if ex and ex.status == ExecutionStatus.RUNNING:
            ex.status = ExecutionStatus.CANCELLED
            ex.finished_at = datetime.utcnow()
            return True
        return False

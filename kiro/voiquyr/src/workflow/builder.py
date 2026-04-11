"""
Workflow Builder — node model, condition builder, version control.
Implements Requirement 18.1.
"""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(Enum):
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    DELAY = "delay"
    TRANSFORM = "transform"
    END = "end"


class ConditionOperator(Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass
class Condition:
    field: str
    operator: ConditionOperator
    value: Any = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        actual = context.get(self.field)
        op = self.operator
        if op == ConditionOperator.EQ:
            return actual == self.value
        if op == ConditionOperator.NEQ:
            return actual != self.value
        if op == ConditionOperator.GT:
            return actual is not None and actual > self.value
        if op == ConditionOperator.GTE:
            return actual is not None and actual >= self.value
        if op == ConditionOperator.LT:
            return actual is not None and actual < self.value
        if op == ConditionOperator.LTE:
            return actual is not None and actual <= self.value
        if op == ConditionOperator.CONTAINS:
            return self.value in (actual or "")
        if op == ConditionOperator.NOT_CONTAINS:
            return self.value not in (actual or "")
        if op == ConditionOperator.IS_EMPTY:
            return not actual
        if op == ConditionOperator.IS_NOT_EMPTY:
            return bool(actual)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "operator": self.operator.value, "value": self.value}


@dataclass
class ConditionGroup:
    """AND/OR group of conditions."""
    conditions: List[Condition] = field(default_factory=list)
    logic: str = "AND"  # "AND" | "OR"

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if not self.conditions:
            return True
        results = [c.evaluate(context) for c in self.conditions]
        return all(results) if self.logic == "AND" else any(results)


@dataclass
class WorkflowNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.ACTION
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    # Outgoing edges: default next, true/false branches for conditions
    next_node_id: Optional[str] = None
    true_branch_id: Optional[str] = None
    false_branch_id: Optional[str] = None
    # For loops
    loop_body_id: Optional[str] = None
    loop_condition: Optional[ConditionGroup] = None
    # For parallel
    parallel_branch_ids: List[str] = field(default_factory=list)
    # Position on canvas (for visual builder)
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "config": self.config,
            "next_node_id": self.next_node_id,
            "true_branch_id": self.true_branch_id,
            "false_branch_id": self.false_branch_id,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class WorkflowVersion:
    version: int
    nodes: Dict[str, WorkflowNode]
    entry_node_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    comment: str = ""


class Workflow:
    """
    A workflow definition with nodes, version history, and canvas metadata.
    """

    def __init__(self, workflow_id: Optional[str] = None, name: str = ""):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.name = name
        self.nodes: Dict[str, WorkflowNode] = {}
        self.entry_node_id: Optional[str] = None
        self._versions: List[WorkflowVersion] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.tags: List[str] = []

    # ------------------------------------------------------------------
    # Node management (drag-and-drop canvas operations)
    # ------------------------------------------------------------------

    def add_node(self, node: WorkflowNode) -> WorkflowNode:
        self.nodes[node.node_id] = node
        if not self.entry_node_id and node.node_type == NodeType.TRIGGER:
            self.entry_node_id = node.node_id
        self.updated_at = datetime.utcnow()
        return node

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        # Clean up dangling references
        for n in self.nodes.values():
            if n.next_node_id == node_id:
                n.next_node_id = None
            if n.true_branch_id == node_id:
                n.true_branch_id = None
            if n.false_branch_id == node_id:
                n.false_branch_id = None
        self.updated_at = datetime.utcnow()
        return True

    def connect(self, from_id: str, to_id: str, branch: str = "next") -> None:
        """Connect two nodes. branch: 'next' | 'true' | 'false'."""
        node = self.nodes[from_id]
        if branch == "true":
            node.true_branch_id = to_id
        elif branch == "false":
            node.false_branch_id = to_id
        else:
            node.next_node_id = to_id
        self.updated_at = datetime.utcnow()

    def move_node(self, node_id: str, x: float, y: float) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].x = x
            self.nodes[node_id].y = y

    # ------------------------------------------------------------------
    # Version control
    # ------------------------------------------------------------------

    def commit(self, comment: str = "", created_by: str = "system") -> WorkflowVersion:
        version_num = len(self._versions) + 1
        snapshot = copy.deepcopy(self.nodes)
        v = WorkflowVersion(
            version=version_num,
            nodes=snapshot,
            entry_node_id=self.entry_node_id or "",
            comment=comment,
            created_by=created_by,
        )
        self._versions.append(v)
        return v

    def rollback(self, version: int) -> bool:
        target = next((v for v in self._versions if v.version == version), None)
        if not target:
            return False
        self.nodes = copy.deepcopy(target.nodes)
        self.entry_node_id = target.entry_node_id
        self.updated_at = datetime.utcnow()
        return True

    def get_versions(self) -> List[Dict[str, Any]]:
        return [
            {"version": v.version, "comment": v.comment,
             "created_by": v.created_by, "created_at": v.created_at.isoformat()}
            for v in self._versions
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        errors = []
        if not self.entry_node_id:
            errors.append("No trigger node defined")
        if self.entry_node_id and self.entry_node_id not in self.nodes:
            errors.append("Entry node not found in nodes")
        for nid, node in self.nodes.items():
            if node.next_node_id and node.next_node_id not in self.nodes:
                errors.append(f"Node {nid} references missing next_node {node.next_node_id}")
            if node.node_type == NodeType.CONDITION:
                if not node.true_branch_id and not node.false_branch_id:
                    errors.append(f"Condition node {nid} has no branches")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "entry_node_id": self.entry_node_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "node_count": len(self.nodes),
            "versions": len(self._versions),
            "tags": self.tags,
        }

"""
Conversation Canvas — node model, connection management, property editor,
canvas navigation, version control, and collaboration.
Implements Requirements 21.1, 21.4, 21.7.
"""

import copy
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

class ConvNodeType(Enum):
    START = "start"
    INTENT = "intent"
    ENTITY = "entity"
    RESPONSE = "response"
    CONDITION = "condition"
    ACTION = "action"
    SLOT_FILLING = "slot_filling"
    FALLBACK = "fallback"
    HANDOFF = "handoff"
    END = "end"


# ---------------------------------------------------------------------------
# Condition model (21.2)
# ---------------------------------------------------------------------------

class CondOp(Enum):
    EQ = "eq"; NEQ = "neq"; GT = "gt"; GTE = "gte"
    LT = "lt"; LTE = "lte"; CONTAINS = "contains"
    MATCHES = "matches"; IS_SET = "is_set"; IS_EMPTY = "is_empty"


@dataclass
class ConvCondition:
    variable: str
    operator: CondOp
    value: Any = None
    custom_fn: Optional[str] = None   # Python expression string

    def evaluate(self, ctx: Dict[str, Any]) -> bool:
        val = ctx.get(self.variable)
        op = self.operator
        if op == CondOp.EQ:      return val == self.value
        if op == CondOp.NEQ:     return val != self.value
        if op == CondOp.GT:      return val is not None and val > self.value
        if op == CondOp.GTE:     return val is not None and val >= self.value
        if op == CondOp.LT:      return val is not None and val < self.value
        if op == CondOp.LTE:     return val is not None and val <= self.value
        if op == CondOp.CONTAINS: return self.value in (val or "")
        if op == CondOp.MATCHES:
            return bool(re.search(str(self.value), str(val or "")))
        if op == CondOp.IS_SET:  return val is not None and val != ""
        if op == CondOp.IS_EMPTY: return not val
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {"variable": self.variable, "operator": self.operator.value,
                "value": self.value}


@dataclass
class ConditionGroup:
    conditions: List[ConvCondition] = field(default_factory=list)
    logic: str = "AND"

    def evaluate(self, ctx: Dict[str, Any]) -> bool:
        if not self.conditions:
            return True
        results = [c.evaluate(ctx) for c in self.conditions]
        return all(results) if self.logic == "AND" else any(results)


# ---------------------------------------------------------------------------
# Canvas node
# ---------------------------------------------------------------------------

@dataclass
class ConvNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: ConvNodeType = ConvNodeType.RESPONSE
    name: str = ""
    # Type-specific config
    intents: List[str] = field(default_factory=list)       # for INTENT nodes
    entities: List[str] = field(default_factory=list)      # for ENTITY nodes
    response_text: Optional[str] = None                    # for RESPONSE nodes
    response_variants: List[str] = field(default_factory=list)  # random variants
    condition_group: Optional[ConditionGroup] = None       # for CONDITION nodes
    action_name: Optional[str] = None                      # for ACTION nodes
    slots: List[str] = field(default_factory=list)         # for SLOT_FILLING
    # Routing
    next_node_id: Optional[str] = None
    true_branch_id: Optional[str] = None
    false_branch_id: Optional[str] = None
    # Canvas position
    x: float = 0.0
    y: float = 0.0
    # Metadata
    tags: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "x": self.x, "y": self.y,
            "next_node_id": self.next_node_id,
            "true_branch_id": self.true_branch_id,
            "false_branch_id": self.false_branch_id,
        }


# ---------------------------------------------------------------------------
# Version control
# ---------------------------------------------------------------------------

@dataclass
class FlowVersion:
    version: int
    nodes: Dict[str, ConvNode]
    entry_node_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    author: str = "system"
    comment: str = ""
    diff_summary: str = ""


# ---------------------------------------------------------------------------
# Collaboration
# ---------------------------------------------------------------------------

@dataclass
class Annotation:
    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    author: str = ""
    text: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False


@dataclass
class EditSession:
    user_id: str
    joined_at: datetime = field(default_factory=datetime.utcnow)
    cursor_node_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversation Flow (canvas)
# ---------------------------------------------------------------------------

class ConversationFlow:
    """
    A conversation flow with nodes, version history, and collaboration support.
    """

    def __init__(self, flow_id: Optional[str] = None, name: str = ""):
        self.flow_id = flow_id or str(uuid.uuid4())
        self.name = name
        self.nodes: Dict[str, ConvNode] = {}
        self.entry_node_id: Optional[str] = None
        self._versions: List[FlowVersion] = []
        self._annotations: List[Annotation] = []
        self._active_editors: Dict[str, EditSession] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.tags: List[str] = []

    # ------------------------------------------------------------------
    # Canvas operations
    # ------------------------------------------------------------------

    def add_node(self, node: ConvNode) -> ConvNode:
        self.nodes[node.node_id] = node
        if not self.entry_node_id and node.node_type == ConvNodeType.START:
            self.entry_node_id = node.node_id
        self.updated_at = datetime.utcnow()
        return node

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
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

    def commit(self, comment: str = "", author: str = "system") -> FlowVersion:
        prev = self._versions[-1] if self._versions else None
        diff = self._compute_diff(prev)
        v = FlowVersion(
            version=len(self._versions) + 1,
            nodes=copy.deepcopy(self.nodes),
            entry_node_id=self.entry_node_id or "",
            comment=comment,
            author=author,
            diff_summary=diff,
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

    def _compute_diff(self, prev: Optional[FlowVersion]) -> str:
        if not prev:
            return f"Initial commit: {len(self.nodes)} nodes"
        added = set(self.nodes) - set(prev.nodes)
        removed = set(prev.nodes) - set(self.nodes)
        return f"+{len(added)} nodes, -{len(removed)} nodes"

    def get_versions(self) -> List[Dict[str, Any]]:
        return [{"version": v.version, "comment": v.comment,
                 "author": v.author, "diff": v.diff_summary,
                 "created_at": v.created_at.isoformat()}
                for v in self._versions]

    # ------------------------------------------------------------------
    # Collaboration
    # ------------------------------------------------------------------

    def join_editing(self, user_id: str) -> EditSession:
        session = EditSession(user_id=user_id)
        self._active_editors[user_id] = session
        return session

    def leave_editing(self, user_id: str) -> None:
        self._active_editors.pop(user_id, None)

    def update_cursor(self, user_id: str, node_id: str) -> None:
        if user_id in self._active_editors:
            self._active_editors[user_id].cursor_node_id = node_id

    def add_annotation(self, node_id: str, author: str, text: str) -> Annotation:
        ann = Annotation(node_id=node_id, author=author, text=text)
        self._annotations.append(ann)
        return ann

    def resolve_annotation(self, annotation_id: str) -> bool:
        for a in self._annotations:
            if a.annotation_id == annotation_id:
                a.resolved = True
                return True
        return False

    def get_annotations(self, node_id: Optional[str] = None) -> List[Annotation]:
        if node_id:
            return [a for a in self._annotations if a.node_id == node_id]
        return list(self._annotations)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        errors = []
        if not self.entry_node_id:
            errors.append("No START node defined")
        for nid, node in self.nodes.items():
            if node.next_node_id and node.next_node_id not in self.nodes:
                errors.append(f"Node {nid} references missing node {node.next_node_id}")
            if node.node_type == ConvNodeType.CONDITION and not node.condition_group:
                errors.append(f"Condition node {nid} has no condition group")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "name": self.name,
            "entry_node_id": self.entry_node_id,
            "node_count": len(self.nodes),
            "versions": len(self._versions),
            "active_editors": list(self._active_editors.keys()),
        }

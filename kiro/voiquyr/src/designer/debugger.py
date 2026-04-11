"""
Conversation Debugger — real-time preview, variable inspection,
step-by-step debugging, simulation, and test case management.
Implements Requirement 21.3.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .canvas import ConvNode, ConvNodeType, ConversationFlow


class DebugStepStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DebugStep:
    step_num: int
    node_id: str
    node_name: str
    node_type: str
    context_snapshot: Dict[str, Any]
    output: Optional[Any] = None
    status: DebugStepStatus = DebugStepStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_num,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "status": self.status.value,
            "context": self.context_snapshot,
            "output": self.output,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SimulationTurn:
    user_input: str
    bot_response: Optional[str] = None
    matched_intent: Optional[str] = None
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    node_path: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_input": self.user_input,
            "bot_response": self.bot_response,
            "matched_intent": self.matched_intent,
            "extracted_entities": self.extracted_entities,
            "node_path": self.node_path,
        }


@dataclass
class TestCase:
    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    turns: List[Dict[str, str]] = field(default_factory=list)  # [{user, expected_response}]
    initial_context: Dict[str, Any] = field(default_factory=dict)
    passed: Optional[bool] = None
    failure_reason: Optional[str] = None
    run_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "turns": len(self.turns),
            "passed": self.passed,
            "failure_reason": self.failure_reason,
        }


class ConversationDebugger:
    """
    Step-by-step debugger and simulator for conversation flows.
    """

    def __init__(self, flow: ConversationFlow):
        self.flow = flow
        self._steps: List[DebugStep] = []
        self._test_cases: Dict[str, TestCase] = {}
        self._breakpoints: set = set()

    def set_breakpoint(self, node_id: str) -> None:
        self._breakpoints.add(node_id)

    def clear_breakpoint(self, node_id: str) -> None:
        self._breakpoints.discard(node_id)

    def inspect_variables(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return typed variable inspection snapshot."""
        return {
            k: {"value": v, "type": type(v).__name__}
            for k, v in context.items()
        }

    def simulate(
        self,
        user_inputs: List[str],
        initial_context: Optional[Dict[str, Any]] = None,
        intent_resolver: Optional[Any] = None,
    ) -> List[SimulationTurn]:
        """
        Simulate a conversation given a list of user inputs.
        intent_resolver: optional callable(text) -> (intent, entities)
        """
        context = dict(initial_context or {})
        current_node_id = self.flow.entry_node_id
        turns = []

        for user_input in user_inputs:
            turn = SimulationTurn(user_input=user_input, context=dict(context))
            context["_last_user_input"] = user_input

            # Resolve intent
            if intent_resolver:
                intent, entities = intent_resolver(user_input)
                turn.matched_intent = intent
                turn.extracted_entities = entities
                context["_intent"] = intent
                context.update(entities)

            # Walk the flow
            node_id = current_node_id
            while node_id:
                node = self.flow.nodes.get(node_id)
                if not node:
                    break
                turn.node_path.append(node_id)

                if node.node_type == ConvNodeType.RESPONSE:
                    import random
                    variants = node.response_variants or ([node.response_text] if node.response_text else [])
                    turn.bot_response = random.choice(variants) if variants else ""
                    node_id = node.next_node_id
                    break

                elif node.node_type == ConvNodeType.CONDITION:
                    result = node.condition_group.evaluate(context) if node.condition_group else False
                    node_id = node.true_branch_id if result else node.false_branch_id

                elif node.node_type == ConvNodeType.INTENT:
                    matched = context.get("_intent") in (node.intents or [])
                    node_id = node.next_node_id if matched else None

                elif node.node_type in (ConvNodeType.START, ConvNodeType.ACTION):
                    node_id = node.next_node_id

                elif node.node_type == ConvNodeType.END:
                    node_id = None
                    break
                else:
                    node_id = node.next_node_id

            current_node_id = node_id or self.flow.entry_node_id
            turns.append(turn)

        return turns

    def step_through(
        self, context: Dict[str, Any]
    ) -> List[DebugStep]:
        """Execute flow step-by-step, recording each node visit."""
        self._steps = []
        step_num = 0
        node_id = self.flow.entry_node_id
        visited = set()

        while node_id and node_id not in visited:
            node = self.flow.nodes.get(node_id)
            if not node:
                break
            visited.add(node_id)
            step = DebugStep(
                step_num=step_num,
                node_id=node_id,
                node_name=node.name,
                node_type=node.node_type.value,
                context_snapshot=dict(context),
            )
            step.status = DebugStepStatus.ACTIVE
            self._steps.append(step)

            if node_id in self._breakpoints:
                step.status = DebugStepStatus.COMPLETED
                step.output = "BREAKPOINT"
                break

            if node.node_type == ConvNodeType.CONDITION and node.condition_group:
                result = node.condition_group.evaluate(context)
                step.output = {"condition": result}
                node_id = node.true_branch_id if result else node.false_branch_id
            elif node.node_type == ConvNodeType.END:
                step.output = "END"
                step.status = DebugStepStatus.COMPLETED
                break
            else:
                node_id = node.next_node_id

            step.status = DebugStepStatus.COMPLETED
            step_num += 1

        return self._steps

    # ------------------------------------------------------------------
    # Test case management
    # ------------------------------------------------------------------

    def add_test_case(self, test_case: TestCase) -> None:
        self._test_cases[test_case.test_id] = test_case

    def run_test_case(
        self,
        test_id: str,
        intent_resolver: Optional[Any] = None,
    ) -> TestCase:
        tc = self._test_cases[test_id]
        tc.run_at = datetime.utcnow()
        user_inputs = [t["user"] for t in tc.turns]
        expected = [t.get("expected_response", "") for t in tc.turns]

        turns = self.simulate(user_inputs, tc.initial_context, intent_resolver)

        for i, (turn, exp) in enumerate(zip(turns, expected)):
            if exp and turn.bot_response != exp:
                tc.passed = False
                tc.failure_reason = (
                    f"Turn {i+1}: expected '{exp}', got '{turn.bot_response}'"
                )
                return tc

        tc.passed = True
        return tc

    def run_all_tests(self, intent_resolver: Optional[Any] = None) -> Dict[str, Any]:
        results = [self.run_test_case(tid, intent_resolver) for tid in self._test_cases]
        passed = sum(1 for r in results if r.passed)
        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": [r.to_dict() for r in results],
        }

    def get_steps(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._steps]

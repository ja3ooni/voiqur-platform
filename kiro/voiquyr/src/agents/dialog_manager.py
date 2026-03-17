"""
Advanced Dialog Management System
Implements conversation state tracking, session management, and context switching
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid

from ..core.models import AgentMessage, Task


class DialogState(Enum):
    """Dialog states for conversation flow"""
    INITIAL = "initial"
    ACTIVE = "active"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING = "processing"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    COMPLETING_TASK = "completing_task"
    INTERRUPTED = "interrupted"
    ENDED = "ended"
    ERROR = "error"


class TurnType(Enum):
    """Types of conversation turns"""
    USER_UTTERANCE = "user_utterance"
    SYSTEM_RESPONSE = "system_response"
    SYSTEM_QUESTION = "system_question"
    USER_CONFIRMATION = "user_confirmation"
    INTERRUPTION = "interruption"
    CLARIFICATION = "clarification"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"


@dataclass
class DialogTurn:
    """Represents a single turn in the conversation"""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turn_type: TurnType = TurnType.USER_UTTERANCE
    speaker: str = "user"  # "user", "assistant", "system", "tool"
    content: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "turn_id": self.turn_id,
            "turn_type": self.turn_type.value,
            "speaker": self.speaker,
            "content": self.content,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class DialogFrame:
    """Represents a dialog frame for task-oriented conversations"""
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    required_slots: Set[str] = field(default_factory=set)
    optional_slots: Set[str] = field(default_factory=set)
    filled_slots: Dict[str, Any] = field(default_factory=dict)
    confirmed_slots: Set[str] = field(default_factory=set)
    is_complete: bool = False
    confidence_threshold: float = 0.8
    
    def add_slot_value(self, slot: str, value: Any, confidence: float = 1.0):
        """Add or update a slot value"""
        self.filled_slots[slot] = {
            "value": value,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if confidence >= self.confidence_threshold:
            self.confirmed_slots.add(slot)
    
    def is_slot_filled(self, slot: str) -> bool:
        """Check if a slot is filled"""
        return slot in self.filled_slots
    
    def is_slot_confirmed(self, slot: str) -> bool:
        """Check if a slot is confirmed"""
        return slot in self.confirmed_slots
    
    def get_missing_required_slots(self) -> Set[str]:
        """Get missing required slots"""
        return self.required_slots - set(self.filled_slots.keys())
    
    def get_unconfirmed_slots(self) -> Set[str]:
        """Get filled but unconfirmed slots"""
        return set(self.filled_slots.keys()) - self.confirmed_slots
    
    def update_completion_status(self):
        """Update completion status based on filled slots"""
        missing_required = self.get_missing_required_slots()
        unconfirmed = self.get_unconfirmed_slots()
        
        self.is_complete = len(missing_required) == 0 and len(unconfirmed) == 0


@dataclass
class ConversationSession:
    """Enhanced conversation session with dialog management"""
    session_id: str
    user_id: Optional[str] = None
    dialog_state: DialogState = DialogState.INITIAL
    turns: List[DialogTurn] = field(default_factory=list)
    current_frame: Optional[DialogFrame] = None
    frame_stack: List[DialogFrame] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    session_timeout: timedelta = field(default_factory=lambda: timedelta(hours=1))
    
    def add_turn(self, turn: DialogTurn):
        """Add a turn to the conversation"""
        self.turns.append(turn)
        self.last_updated = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def get_recent_turns(self, count: int = 5) -> List[DialogTurn]:
        """Get recent turns"""
        return self.turns[-count:] if len(self.turns) >= count else self.turns
    
    def get_turns_by_type(self, turn_type: TurnType) -> List[DialogTurn]:
        """Get turns by type"""
        return [turn for turn in self.turns if turn.turn_type == turn_type]
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() - self.last_activity > self.session_timeout
    
    def push_frame(self, frame: DialogFrame):
        """Push a new dialog frame onto the stack"""
        if self.current_frame:
            self.frame_stack.append(self.current_frame)
        self.current_frame = frame
    
    def pop_frame(self) -> Optional[DialogFrame]:
        """Pop the current frame and return to previous"""
        completed_frame = self.current_frame
        if self.frame_stack:
            self.current_frame = self.frame_stack.pop()
        else:
            self.current_frame = None
        return completed_frame
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation context"""
        return {
            "session_id": self.session_id,
            "dialog_state": self.dialog_state.value,
            "turn_count": len(self.turns),
            "current_frame": self.current_frame.task_type if self.current_frame else None,
            "frame_stack_depth": len(self.frame_stack),
            "language": self.language,
            "last_intent": self.turns[-1].intent if self.turns else None,
            "context_variables": self.context_variables
        }


class DialogPolicy:
    """Dialog policy for determining next actions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define dialog policies for different scenarios
        self.policies = {
            "greeting": self._handle_greeting,
            "question": self._handle_question,
            "request": self._handle_request,
            "booking": self._handle_booking,
            "information": self._handle_information,
            "clarification": self._handle_clarification,
            "confirmation": self._handle_confirmation,
            "interruption": self._handle_interruption,
            "goodbye": self._handle_goodbye
        }
        
        # Frame templates for task-oriented dialogs
        self.frame_templates = {
            "booking": DialogFrame(
                task_type="booking",
                required_slots={"service", "date", "time"},
                optional_slots={"location", "duration", "notes"}
            ),
            "weather_query": DialogFrame(
                task_type="weather_query",
                required_slots={"location"},
                optional_slots={"date", "time_period"}
            ),
            "information_request": DialogFrame(
                task_type="information_request",
                required_slots={"topic"},
                optional_slots={"detail_level", "format"}
            )
        }
    
    async def determine_next_action(self, session: ConversationSession, 
                                  current_turn: DialogTurn) -> Dict[str, Any]:
        """Determine the next action based on current state and turn"""
        try:
            intent = current_turn.intent or "general"
            
            # Get appropriate policy handler
            policy_handler = self.policies.get(intent, self._handle_general)
            
            # Execute policy
            action = await policy_handler(session, current_turn)
            
            return action
            
        except Exception as e:
            self.logger.error(f"Policy determination failed: {e}")
            return {
                "action": "error_response",
                "message": "I encountered an error while processing your request.",
                "next_state": DialogState.ERROR
            }
    
    async def _handle_greeting(self, session: ConversationSession, 
                             turn: DialogTurn) -> Dict[str, Any]:
        """Handle greeting intent"""
        if session.dialog_state == DialogState.INITIAL:
            return {
                "action": "greeting_response",
                "message": "Hello! How can I help you today?",
                "next_state": DialogState.ACTIVE
            }
        else:
            return {
                "action": "acknowledgment",
                "message": "Hello again! What can I do for you?",
                "next_state": DialogState.ACTIVE
            }
    
    async def _handle_question(self, session: ConversationSession, 
                              turn: DialogTurn) -> Dict[str, Any]:
        """Handle question intent"""
        # Check if we need to create an information request frame
        if not session.current_frame or session.current_frame.task_type != "information_request":
            frame = self.frame_templates["information_request"].copy()
            frame.frame_id = str(uuid.uuid4())
            session.push_frame(frame)
        
        # Extract topic from entities or content
        topic = turn.entities.get("topic", [turn.content])[0] if turn.entities.get("topic") else turn.content
        session.current_frame.add_slot_value("topic", topic, turn.confidence)
        
        return {
            "action": "provide_information",
            "topic": topic,
            "next_state": DialogState.PROCESSING
        }
    
    async def _handle_request(self, session: ConversationSession, 
                             turn: DialogTurn) -> Dict[str, Any]:
        """Handle request intent"""
        return {
            "action": "process_request",
            "request_type": turn.entities.get("request_type", "general"),
            "next_state": DialogState.PROCESSING
        }
    
    async def _handle_booking(self, session: ConversationSession, 
                             turn: DialogTurn) -> Dict[str, Any]:
        """Handle booking intent"""
        # Create or update booking frame
        if not session.current_frame or session.current_frame.task_type != "booking":
            frame = self.frame_templates["booking"].copy()
            frame.frame_id = str(uuid.uuid4())
            session.push_frame(frame)
        
        # Fill slots from entities
        for slot in ["service", "date", "time", "location"]:
            if slot in turn.entities:
                value = turn.entities[slot][0] if isinstance(turn.entities[slot], list) else turn.entities[slot]
                session.current_frame.add_slot_value(slot, value, turn.confidence)
        
        session.current_frame.update_completion_status()
        
        # Check if we need more information
        missing_slots = session.current_frame.get_missing_required_slots()
        if missing_slots:
            return {
                "action": "request_slot_filling",
                "missing_slots": list(missing_slots),
                "next_state": DialogState.WAITING_FOR_INPUT
            }
        
        # Check if we need confirmation
        unconfirmed_slots = session.current_frame.get_unconfirmed_slots()
        if unconfirmed_slots:
            return {
                "action": "request_confirmation",
                "slots_to_confirm": {slot: session.current_frame.filled_slots[slot] 
                                   for slot in unconfirmed_slots},
                "next_state": DialogState.WAITING_FOR_CLARIFICATION
            }
        
        # All slots filled and confirmed
        return {
            "action": "complete_booking",
            "booking_details": session.current_frame.filled_slots,
            "next_state": DialogState.COMPLETING_TASK
        }
    
    async def _handle_information(self, session: ConversationSession, 
                                 turn: DialogTurn) -> Dict[str, Any]:
        """Handle information request"""
        return await self._handle_question(session, turn)
    
    async def _handle_clarification(self, session: ConversationSession, 
                                   turn: DialogTurn) -> Dict[str, Any]:
        """Handle clarification request"""
        if session.current_frame:
            # Try to fill missing slots with clarification
            missing_slots = session.current_frame.get_missing_required_slots()
            for slot in missing_slots:
                if slot in turn.entities:
                    value = turn.entities[slot][0] if isinstance(turn.entities[slot], list) else turn.entities[slot]
                    session.current_frame.add_slot_value(slot, value, turn.confidence)
            
            session.current_frame.update_completion_status()
            
            # Continue with the current task
            return await self.determine_next_action(session, turn)
        
        return {
            "action": "provide_clarification",
            "message": "I understand. Let me help clarify that for you.",
            "next_state": DialogState.ACTIVE
        }
    
    async def _handle_confirmation(self, session: ConversationSession, 
                                  turn: DialogTurn) -> Dict[str, Any]:
        """Handle confirmation"""
        if session.current_frame:
            # Confirm unconfirmed slots
            unconfirmed_slots = session.current_frame.get_unconfirmed_slots()
            for slot in unconfirmed_slots:
                session.current_frame.confirmed_slots.add(slot)
            
            session.current_frame.update_completion_status()
            
            if session.current_frame.is_complete:
                return {
                    "action": "complete_task",
                    "task_type": session.current_frame.task_type,
                    "next_state": DialogState.COMPLETING_TASK
                }
        
        return {
            "action": "acknowledge_confirmation",
            "message": "Thank you for confirming. How else can I help?",
            "next_state": DialogState.ACTIVE
        }
    
    async def _handle_interruption(self, session: ConversationSession, 
                                  turn: DialogTurn) -> Dict[str, Any]:
        """Handle conversation interruption"""
        # Save current state
        session.context_variables["interrupted_state"] = session.dialog_state.value
        session.context_variables["interrupted_frame"] = session.current_frame.frame_id if session.current_frame else None
        
        return {
            "action": "handle_interruption",
            "message": "I understand you have a new request. Let me help with that.",
            "next_state": DialogState.INTERRUPTED
        }
    
    async def _handle_goodbye(self, session: ConversationSession, 
                             turn: DialogTurn) -> Dict[str, Any]:
        """Handle goodbye intent"""
        return {
            "action": "farewell",
            "message": "Goodbye! Feel free to reach out if you need anything else.",
            "next_state": DialogState.ENDED
        }
    
    async def _handle_general(self, session: ConversationSession, 
                             turn: DialogTurn) -> Dict[str, Any]:
        """Handle general/unknown intent"""
        return {
            "action": "general_response",
            "message": "I understand. How can I help you with that?",
            "next_state": DialogState.ACTIVE
        }


class DialogManager:
    """Advanced dialog management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, ConversationSession] = {}
        self.dialog_policy = DialogPolicy()
        
        # Dialog management settings
        self.max_turns_per_session = 100
        self.session_cleanup_interval = timedelta(minutes=30)
        self.last_cleanup = datetime.utcnow()
    
    def create_session(self, user_id: Optional[str] = None, 
                      language: str = "en") -> ConversationSession:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            language=language
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"Created dialog session {session_id} for user {user_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get existing session"""
        session = self.sessions.get(session_id)
        
        if session and session.is_expired():
            self.logger.info(f"Session {session_id} expired, removing")
            del self.sessions[session_id]
            return None
        
        return session
    
    async def process_turn(self, session_id: str, content: str, 
                          intent: Optional[str] = None, 
                          entities: Optional[Dict[str, Any]] = None,
                          confidence: float = 1.0) -> Dict[str, Any]:
        """Process a conversation turn"""
        try:
            session = self.get_session(session_id)
            if not session:
                return {"error": "Session not found or expired"}
            
            # Create turn
            turn = DialogTurn(
                turn_type=TurnType.USER_UTTERANCE,
                speaker="user",
                content=content,
                intent=intent,
                entities=entities or {},
                confidence=confidence
            )
            
            # Add turn to session
            session.add_turn(turn)
            
            # Determine next action using dialog policy
            action = await self.dialog_policy.determine_next_action(session, turn)
            
            # Update dialog state
            if "next_state" in action:
                session.dialog_state = action["next_state"]
            
            # Create system response turn
            if "message" in action:
                response_turn = DialogTurn(
                    turn_type=TurnType.SYSTEM_RESPONSE,
                    speaker="assistant",
                    content=action["message"],
                    metadata={"action": action["action"]}
                )
                session.add_turn(response_turn)
            
            # Cleanup if needed
            await self._cleanup_if_needed()
            
            return {
                "session_id": session_id,
                "action": action,
                "dialog_state": session.dialog_state.value,
                "context_summary": session.get_context_summary()
            }
            
        except Exception as e:
            self.logger.error(f"Turn processing failed: {e}")
            return {"error": str(e)}
    
    async def handle_interruption(self, session_id: str, new_content: str,
                                 new_intent: Optional[str] = None) -> Dict[str, Any]:
        """Handle conversation interruption"""
        try:
            session = self.get_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            # Mark as interrupted
            session.dialog_state = DialogState.INTERRUPTED
            
            # Create interruption turn
            interruption_turn = DialogTurn(
                turn_type=TurnType.INTERRUPTION,
                speaker="user",
                content=new_content,
                intent=new_intent or "interruption"
            )
            
            session.add_turn(interruption_turn)
            
            # Process the interruption
            result = await self.process_turn(session_id, new_content, new_intent)
            
            return {
                **result,
                "interruption_handled": True,
                "previous_state": session.context_variables.get("interrupted_state")
            }
            
        except Exception as e:
            self.logger.error(f"Interruption handling failed: {e}")
            return {"error": str(e)}
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context information"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_summary": session.get_context_summary(),
            "recent_turns": [turn.to_dict() for turn in session.get_recent_turns()],
            "current_frame": {
                "task_type": session.current_frame.task_type,
                "filled_slots": session.current_frame.filled_slots,
                "missing_slots": list(session.current_frame.get_missing_required_slots()),
                "is_complete": session.current_frame.is_complete
            } if session.current_frame else None,
            "frame_stack_depth": len(session.frame_stack)
        }
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Deleted session {session_id}")
            return True
        return False
    
    async def _cleanup_if_needed(self):
        """Clean up expired sessions if needed"""
        if datetime.utcnow() - self.last_cleanup > self.session_cleanup_interval:
            await self.cleanup_expired_sessions()
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        self.last_cleanup = current_time
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_dialog_stats(self) -> Dict[str, Any]:
        """Get dialog management statistics"""
        active_sessions = len([s for s in self.sessions.values() 
                              if not s.is_expired()])
        
        total_turns = sum(len(s.turns) for s in self.sessions.values())
        
        state_distribution = {}
        for session in self.sessions.values():
            state = session.dialog_state.value
            state_distribution[state] = state_distribution.get(state, 0) + 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "total_turns": total_turns,
            "average_turns_per_session": total_turns / len(self.sessions) if self.sessions else 0,
            "state_distribution": state_distribution
        }
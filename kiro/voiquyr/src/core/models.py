"""
Core data models for the EUVoice AI multi-agent system.
Implements AgentMessage, AgentState, and Task models with proper serialization.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid


class MessageType(str, Enum):
    """Types of messages that can be sent between agents."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class AgentStatus(str, Enum):
    """Status of an agent in the system."""
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    ERROR = "error"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    """Status of a task in the system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(int, Enum):
    """Priority levels for messages and tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentMessage(BaseModel):
    """
    Standardized message format for inter-agent communication.
    Based on OpenAI function calling patterns.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = Field(..., description="ID of the sending agent")
    receiver_id: Optional[str] = Field(None, description="ID of the receiving agent (None for broadcast)")
    message_type: MessageType = Field(..., description="Type of message")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent task/message IDs")
    priority: Priority = Field(default=Priority.NORMAL, description="Message priority")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Message expiration time")
    correlation_id: Optional[str] = Field(None, description="For tracking request-response pairs")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def is_expired(self) -> bool:
        """Check if the message has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def can_retry(self) -> bool:
        """Check if the message can be retried."""
        return self.retry_count < self.max_retries


class Task(BaseModel):
    """
    Task model for agent work coordination.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str = Field(..., description="Task description")
    requirements: List[str] = Field(default_factory=list, description="Requirements this task addresses")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent task IDs")
    assigned_agent: Optional[str] = Field(None, description="ID of assigned agent")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: Priority = Field(default=Priority.NORMAL)
    estimated_duration: Optional[timedelta] = Field(None, description="Estimated completion time")
    actual_duration: Optional[timedelta] = Field(None, description="Actual completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    context: Dict[str, Any] = Field(default_factory=dict, description="Task-specific context data")
    result: Optional[Dict[str, Any]] = Field(None, description="Task execution result")
    error_message: Optional[str] = Field(None, description="Error message if task failed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds()
        }

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def complete(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at

    def fail(self, error_message: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at


class AgentCapability(BaseModel):
    """Represents a capability that an agent can perform."""
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for inputs")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for outputs")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")


class AgentState(BaseModel):
    """
    State information for an agent in the system.
    """
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(..., description="Type of agent (STT, LLM, TTS, etc.)")
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    current_task: Optional[Task] = Field(None, description="Currently executing task")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="Agent capabilities")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent agent IDs")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata")
    resource_usage: Dict[str, float] = Field(default_factory=dict, description="Resource usage metrics")
    error_count: int = Field(default=0, description="Number of errors encountered")
    total_tasks_completed: int = Field(default=0, description="Total tasks completed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        """Check if agent is healthy based on heartbeat."""
        if self.status == AgentStatus.OFFLINE:
            return False
        time_since_heartbeat = datetime.utcnow() - self.last_heartbeat
        return time_since_heartbeat.total_seconds() < timeout_seconds

    def assign_task(self, task: Task) -> None:
        """Assign a task to this agent."""
        self.current_task = task
        self.status = AgentStatus.WORKING
        self.last_updated = datetime.utcnow()

    def complete_task(self) -> None:
        """Mark current task as completed."""
        if self.current_task:
            self.total_tasks_completed += 1
        self.current_task = None
        self.status = AgentStatus.IDLE
        self.last_updated = datetime.utcnow()

    def report_error(self, error_message: str) -> None:
        """Report an error for this agent."""
        self.error_count += 1
        self.status = AgentStatus.ERROR
        self.last_updated = datetime.utcnow()
        if self.current_task:
            self.current_task.fail(error_message)


class AgentRegistration(BaseModel):
    """Agent registration information."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(..., description="Type of agent")
    capabilities: List[AgentCapability] = Field(..., description="Agent capabilities")
    endpoint: str = Field(..., description="Agent communication endpoint")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    registered_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageQueue(BaseModel):
    """Message queue for agent communication."""
    queue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(..., description="Owner agent ID")
    messages: List[AgentMessage] = Field(default_factory=list)
    max_size: int = Field(default=1000, description="Maximum queue size")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, message: AgentMessage) -> bool:
        """Add a message to the queue."""
        if len(self.messages) >= self.max_size:
            # Remove oldest low-priority message to make room
            for i, msg in enumerate(self.messages):
                if msg.priority == Priority.LOW:
                    self.messages.pop(i)
                    break
            else:
                # If no low-priority messages, reject the new message
                return False
        
        # Insert message based on priority
        inserted = False
        for i, existing_msg in enumerate(self.messages):
            if message.priority.value > existing_msg.priority.value:
                self.messages.insert(i, message)
                inserted = True
                break
        
        if not inserted:
            self.messages.append(message)
        
        return True

    def get_next_message(self) -> Optional[AgentMessage]:
        """Get the next message from the queue."""
        # Remove expired messages first
        self.messages = [msg for msg in self.messages if not msg.is_expired()]
        
        if not self.messages:
            return None
        
        return self.messages.pop(0)

    def peek_next_message(self) -> Optional[AgentMessage]:
        """Peek at the next message without removing it."""
        # Remove expired messages first
        self.messages = [msg for msg in self.messages if not msg.is_expired()]
        
        if not self.messages:
            return None
        
        return self.messages[0]

    def size(self) -> int:
        """Get the current queue size."""
        return len(self.messages)
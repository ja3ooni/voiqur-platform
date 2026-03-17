"""
Message routing and delivery system for multi-agent communication.
Implements priority queuing, routing, and delivery mechanisms.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import json
from collections import defaultdict

from .models import (
    AgentMessage, AgentState, MessageQueue, MessageType, 
    Priority, AgentStatus, AgentRegistration
)


logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Central message routing system for agent communication.
    Handles message delivery, priority queuing, and routing logic.
    """
    
    def __init__(self):
        self.agent_queues: Dict[str, MessageQueue] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.agent_registrations: Dict[str, AgentRegistration] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.broadcast_subscribers: Dict[MessageType, List[str]] = defaultdict(list)
        self.routing_rules: List[Callable] = []
        self.delivery_callbacks: List[Callable] = []
        self.failed_messages: List[AgentMessage] = []
        self.message_history: List[AgentMessage] = []
        self.max_history_size = 10000
        
    async def register_agent(self, registration: AgentRegistration) -> bool:
        """Register a new agent in the system."""
        try:
            agent_id = registration.agent_id
            
            # Create message queue for the agent
            self.agent_queues[agent_id] = MessageQueue(agent_id=agent_id)
            
            # Create initial agent state
            agent_state = AgentState(
                agent_id=agent_id,
                agent_type=registration.agent_type,
                capabilities=registration.capabilities,
                status=AgentStatus.IDLE
            )
            self.agent_states[agent_id] = agent_state
            
            # Store registration info
            self.agent_registrations[agent_id] = registration
            
            logger.info(f"Agent {agent_id} registered successfully")
            
            # Notify other agents about new registration
            await self._broadcast_agent_registration(registration)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {registration.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system."""
        try:
            if agent_id not in self.agent_states:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False
            
            # Update agent status
            if agent_id in self.agent_states:
                self.agent_states[agent_id].status = AgentStatus.OFFLINE
            
            # Clean up queues and subscriptions
            if agent_id in self.agent_queues:
                del self.agent_queues[agent_id]
            
            # Remove from broadcast subscriptions
            for message_type, subscribers in self.broadcast_subscribers.items():
                if agent_id in subscribers:
                    subscribers.remove(agent_id)
            
            logger.info(f"Agent {agent_id} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message to the specified recipient(s)."""
        try:
            # Add to message history
            self._add_to_history(message)
            
            # Handle broadcast messages
            if message.receiver_id is None:
                return await self._broadcast_message(message)
            
            # Handle direct messages
            return await self._deliver_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send message {message.message_id}: {e}")
            return False
    
    async def _deliver_message(self, message: AgentMessage) -> bool:
        """Deliver a message to a specific agent."""
        receiver_id = message.receiver_id
        
        if receiver_id not in self.agent_queues:
            logger.error(f"Receiver {receiver_id} not found")
            self.failed_messages.append(message)
            return False
        
        # Check if receiver is available
        if receiver_id in self.agent_states:
            agent_state = self.agent_states[receiver_id]
            if not agent_state.is_healthy():
                logger.warning(f"Receiver {receiver_id} is not healthy, queuing message")
        
        # Apply routing rules
        if not await self._apply_routing_rules(message):
            logger.warning(f"Message {message.message_id} rejected by routing rules")
            return False
        
        # Add message to recipient's queue
        queue = self.agent_queues[receiver_id]
        success = queue.add_message(message)
        
        if success:
            logger.debug(f"Message {message.message_id} delivered to {receiver_id}")
            await self._notify_delivery_callbacks(message, receiver_id)
        else:
            logger.error(f"Failed to add message to queue for {receiver_id}")
            self.failed_messages.append(message)
        
        return success
    
    async def _broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast a message to all subscribed agents."""
        message_type = message.message_type
        subscribers = self.broadcast_subscribers.get(message_type, [])
        
        if not subscribers:
            # If no specific subscribers, broadcast to all active agents
            subscribers = [
                agent_id for agent_id, state in self.agent_states.items()
                if state.status != AgentStatus.OFFLINE and agent_id != message.sender_id
            ]
        
        success_count = 0
        for subscriber_id in subscribers:
            # Create a copy of the message for each subscriber
            subscriber_message = message.copy()
            subscriber_message.receiver_id = subscriber_id
            
            if await self._deliver_message(subscriber_message):
                success_count += 1
        
        logger.info(f"Broadcast message {message.message_id} delivered to {success_count}/{len(subscribers)} subscribers")
        return success_count > 0
    
    async def get_messages(self, agent_id: str, max_messages: int = 10) -> List[AgentMessage]:
        """Get messages for a specific agent."""
        if agent_id not in self.agent_queues:
            logger.error(f"Agent {agent_id} not found")
            return []
        
        queue = self.agent_queues[agent_id]
        messages = []
        
        for _ in range(min(max_messages, queue.size())):
            message = queue.get_next_message()
            if message is None:
                break
            messages.append(message)
        
        return messages
    
    async def peek_messages(self, agent_id: str, max_messages: int = 10) -> List[AgentMessage]:
        """Peek at messages for a specific agent without removing them."""
        if agent_id not in self.agent_queues:
            logger.error(f"Agent {agent_id} not found")
            return []
        
        queue = self.agent_queues[agent_id]
        messages = []
        
        # Get a copy of messages without removing them
        for i in range(min(max_messages, len(queue.messages))):
            if i < len(queue.messages):
                messages.append(queue.messages[i])
        
        return messages
    
    def subscribe_to_broadcast(self, agent_id: str, message_type: MessageType) -> bool:
        """Subscribe an agent to broadcast messages of a specific type."""
        if agent_id not in self.agent_states:
            logger.error(f"Agent {agent_id} not found")
            return False
        
        if agent_id not in self.broadcast_subscribers[message_type]:
            self.broadcast_subscribers[message_type].append(agent_id)
            logger.info(f"Agent {agent_id} subscribed to {message_type} broadcasts")
        
        return True
    
    def unsubscribe_from_broadcast(self, agent_id: str, message_type: MessageType) -> bool:
        """Unsubscribe an agent from broadcast messages of a specific type."""
        if agent_id in self.broadcast_subscribers[message_type]:
            self.broadcast_subscribers[message_type].remove(agent_id)
            logger.info(f"Agent {agent_id} unsubscribed from {message_type} broadcasts")
            return True
        
        return False
    
    def add_routing_rule(self, rule: Callable[[AgentMessage], bool]) -> None:
        """Add a custom routing rule."""
        self.routing_rules.append(rule)
    
    def add_delivery_callback(self, callback: Callable[[AgentMessage, str], None]) -> None:
        """Add a callback to be called when a message is delivered."""
        self.delivery_callbacks.append(callback)
    
    async def _apply_routing_rules(self, message: AgentMessage) -> bool:
        """Apply all routing rules to a message."""
        for rule in self.routing_rules:
            try:
                if not rule(message):
                    return False
            except Exception as e:
                logger.error(f"Error applying routing rule: {e}")
                return False
        
        return True
    
    async def _notify_delivery_callbacks(self, message: AgentMessage, receiver_id: str) -> None:
        """Notify all delivery callbacks."""
        for callback in self.delivery_callbacks:
            try:
                await callback(message, receiver_id)
            except Exception as e:
                logger.error(f"Error in delivery callback: {e}")
    
    async def _broadcast_agent_registration(self, registration: AgentRegistration) -> None:
        """Broadcast agent registration to other agents."""
        message = AgentMessage(
            sender_id="system",
            message_type=MessageType.NOTIFICATION,
            payload={
                "event": "agent_registered",
                "agent_id": registration.agent_id,
                "agent_type": registration.agent_type,
                "capabilities": [cap.dict() for cap in registration.capabilities]
            },
            priority=Priority.NORMAL
        )
        
        await self._broadcast_message(message)
    
    def _add_to_history(self, message: AgentMessage) -> None:
        """Add message to history with size limit."""
        self.message_history.append(message)
        
        # Maintain history size limit
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get the current state of an agent."""
        return self.agent_states.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, AgentState]:
        """Get all agent states."""
        return self.agent_states.copy()
    
    def get_queue_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get queue status for an agent."""
        if agent_id not in self.agent_queues:
            return None
        
        queue = self.agent_queues[agent_id]
        return {
            "queue_id": queue.queue_id,
            "size": queue.size(),
            "max_size": queue.max_size,
            "oldest_message": queue.messages[0].timestamp.isoformat() if queue.messages else None
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        total_messages = len(self.message_history)
        failed_messages = len(self.failed_messages)
        active_agents = sum(1 for state in self.agent_states.values() 
                          if state.status != AgentStatus.OFFLINE)
        
        queue_sizes = {agent_id: queue.size() 
                      for agent_id, queue in self.agent_queues.items()}
        
        return {
            "total_agents": len(self.agent_states),
            "active_agents": active_agents,
            "total_messages_processed": total_messages,
            "failed_messages": failed_messages,
            "queue_sizes": queue_sizes,
            "broadcast_subscribers": dict(self.broadcast_subscribers)
        }
    
    async def cleanup_expired_messages(self) -> int:
        """Clean up expired messages from all queues."""
        cleaned_count = 0
        
        for queue in self.agent_queues.values():
            original_size = queue.size()
            queue.messages = [msg for msg in queue.messages if not msg.is_expired()]
            cleaned_count += original_size - queue.size()
        
        # Clean up failed messages
        original_failed = len(self.failed_messages)
        self.failed_messages = [msg for msg in self.failed_messages if not msg.is_expired()]
        cleaned_count += original_failed - len(self.failed_messages)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired messages")
        
        return cleaned_count


class MessageBus:
    """
    High-level message bus interface for agent communication.
    Provides simplified API for common messaging patterns.
    """
    
    def __init__(self, router: MessageRouter):
        self.router = router
    
    async def send_request(self, sender_id: str, receiver_id: str, 
                          request_data: Dict[str, Any], 
                          priority: Priority = Priority.NORMAL,
                          timeout_seconds: int = 30) -> AgentMessage:
        """Send a request message and return the message object."""
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.REQUEST,
            payload=request_data,
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
            correlation_id=f"req_{sender_id}_{datetime.utcnow().timestamp()}"
        )
        
        await self.router.send_message(message)
        return message
    
    async def send_response(self, original_request: AgentMessage, 
                           response_data: Dict[str, Any]) -> bool:
        """Send a response to a request message."""
        response = AgentMessage(
            sender_id=original_request.receiver_id,
            receiver_id=original_request.sender_id,
            message_type=MessageType.RESPONSE,
            payload=response_data,
            priority=original_request.priority,
            correlation_id=original_request.correlation_id
        )
        
        return await self.router.send_message(response)
    
    async def send_notification(self, sender_id: str, 
                               notification_data: Dict[str, Any],
                               recipients: Optional[List[str]] = None) -> bool:
        """Send a notification message."""
        if recipients:
            # Send to specific recipients
            success_count = 0
            for recipient in recipients:
                message = AgentMessage(
                    sender_id=sender_id,
                    receiver_id=recipient,
                    message_type=MessageType.NOTIFICATION,
                    payload=notification_data,
                    priority=Priority.NORMAL
                )
                if await self.router.send_message(message):
                    success_count += 1
            return success_count == len(recipients)
        else:
            # Broadcast notification
            message = AgentMessage(
                sender_id=sender_id,
                receiver_id=None,  # Broadcast
                message_type=MessageType.NOTIFICATION,
                payload=notification_data,
                priority=Priority.NORMAL
            )
            return await self.router.send_message(message)
    
    async def send_error(self, sender_id: str, receiver_id: str, 
                        error_data: Dict[str, Any],
                        original_message: Optional[AgentMessage] = None) -> bool:
        """Send an error message."""
        correlation_id = None
        if original_message:
            correlation_id = original_message.correlation_id or original_message.message_id
        
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.ERROR,
            payload=error_data,
            priority=Priority.HIGH,
            correlation_id=correlation_id
        )
        
        return await self.router.send_message(message)
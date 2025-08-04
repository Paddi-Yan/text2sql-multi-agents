"""
Inter-agent communication protocols and state management.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from utils.models import ChatMessage, AgentResponse


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class CommunicationState(Enum):
    """Communication session states."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CommunicationSession:
    """Represents a communication session between agents."""
    session_id: str
    initiator: str
    participants: List[str]
    state: CommunicationState = CommunicationState.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 300  # 5 minutes default timeout
    message_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session has expired.
        
        Returns:
            True if session has timed out
        """
        return datetime.now() - self.updated_at > timedelta(seconds=self.timeout_seconds)
    
    def update_state(self, new_state: CommunicationState):
        """Update session state.
        
        Args:
            new_state: New state to set
        """
        self.state = new_state
        self.updated_at = datetime.now()


class MessageQueue:
    """Priority-based message queue for agent communication."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queues: Dict[int, List[ChatMessage]] = {
            MessagePriority.URGENT.value: [],
            MessagePriority.HIGH.value: [],
            MessagePriority.NORMAL.value: [],
            MessagePriority.LOW.value: []
        }
        self.total_size = 0
        self._lock = asyncio.Lock()
    
    async def enqueue(self, message: ChatMessage) -> bool:
        """Add message to queue.
        
        Args:
            message: Message to enqueue
            
        Returns:
            True if message was enqueued successfully
        """
        async with self._lock:
            if self.total_size >= self.max_size:
                # Remove lowest priority message to make space
                if not self._remove_lowest_priority():
                    return False
            
            priority = message.priority
            self.queues[priority].append(message)
            self.total_size += 1
            return True
    
    async def dequeue(self) -> Optional[ChatMessage]:
        """Get next message from queue (highest priority first).
        
        Returns:
            Next message or None if queue is empty
        """
        async with self._lock:
            # Check queues in priority order
            for priority in [MessagePriority.URGENT.value, MessagePriority.HIGH.value, 
                           MessagePriority.NORMAL.value, MessagePriority.LOW.value]:
                if self.queues[priority]:
                    message = self.queues[priority].pop(0)
                    self.total_size -= 1
                    return message
            return None
    
    def _remove_lowest_priority(self) -> bool:
        """Remove lowest priority message to make space.
        
        Returns:
            True if a message was removed
        """
        for priority in [MessagePriority.LOW.value, MessagePriority.NORMAL.value,
                        MessagePriority.HIGH.value, MessagePriority.URGENT.value]:
            if self.queues[priority]:
                self.queues[priority].pop(0)
                self.total_size -= 1
                return True
        return False
    
    def size(self) -> int:
        """Get total queue size.
        
        Returns:
            Number of messages in queue
        """
        return self.total_size
    
    def is_empty(self) -> bool:
        """Check if queue is empty.
        
        Returns:
            True if queue has no messages
        """
        return self.total_size == 0


class CommunicationProtocol:
    """Protocol for managing inter-agent communication."""
    
    def __init__(self):
        self.sessions: Dict[str, CommunicationSession] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        self.logger = logging.getLogger("CommunicationProtocol")
    
    def create_session(self, initiator: str, participants: List[str], 
                      timeout_seconds: int = 300) -> str:
        """Create a new communication session.
        
        Args:
            initiator: Agent that initiated the session
            participants: List of participating agents
            timeout_seconds: Session timeout in seconds
            
        Returns:
            Session ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.sessions)}"
        
        session = CommunicationSession(
            session_id=session_id,
            initiator=initiator,
            participants=participants,
            timeout_seconds=timeout_seconds
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"Created communication session {session_id} with participants: {participants}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[CommunicationSession]:
        """Get communication session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        return self.sessions.get(session_id)
    
    def close_session(self, session_id: str, final_state: CommunicationState = CommunicationState.COMPLETED):
        """Close a communication session.
        
        Args:
            session_id: Session to close
            final_state: Final state to set
        """
        if session_id in self.sessions:
            self.sessions[session_id].update_state(final_state)
            self.logger.info(f"Closed session {session_id} with state {final_state.value}")
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            self.sessions[session_id].update_state(CommunicationState.TIMEOUT)
            self.logger.warning(f"Session {session_id} expired and marked as timeout")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a message handler for specific message types.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type] = handler
        self.logger.info(f"Registered handler for message type: {message_type}")
    
    def add_middleware(self, middleware: Callable):
        """Add middleware for message processing.
        
        Args:
            middleware: Middleware function
        """
        self.middleware.append(middleware)
        self.logger.info("Added communication middleware")
    
    async def process_message(self, message: ChatMessage, session_id: Optional[str] = None) -> AgentResponse:
        """Process message through the communication protocol.
        
        Args:
            message: Message to process
            session_id: Optional session ID
            
        Returns:
            Processing response
        """
        # Apply middleware
        for middleware in self.middleware:
            message = await middleware(message)
        
        # Update session if provided
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.message_count += 1
            session.update_state(CommunicationState.ACTIVE)
        
        # Handle message based on type
        message_type = message.get_context("message_type", "default")
        if message_type in self.message_handlers:
            handler = self.message_handlers[message_type]
            return await handler(message)
        
        # Default processing
        return AgentResponse(
            success=True,
            message=message,
            metadata={"processed_by": "CommunicationProtocol"}
        )
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get communication session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s.state == CommunicationState.ACTIVE)
        completed_sessions = sum(1 for s in self.sessions.values() if s.state == CommunicationState.COMPLETED)
        failed_sessions = sum(1 for s in self.sessions.values() if s.state == CommunicationState.FAILED)
        expired_sessions = sum(1 for s in self.sessions.values() if s.is_expired())
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "expired_sessions": expired_sessions,
            "success_rate": completed_sessions / total_sessions if total_sessions > 0 else 0.0
        }


class AgentCommunicationManager:
    """High-level manager for agent communication."""
    
    def __init__(self):
        self.protocol = CommunicationProtocol()
        self.message_queue = MessageQueue()
        self.agents: Dict[str, Any] = {}  # Will be populated with actual agent instances
        self.logger = logging.getLogger("AgentCommunicationManager")
        self._running = False
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """Register an agent with the communication manager.
        
        Args:
            agent_name: Name of the agent
            agent_instance: Agent instance
        """
        self.agents[agent_name] = agent_instance
        self.logger.info(f"Registered agent: {agent_name}")
    
    async def send_message(self, message: ChatMessage, session_id: Optional[str] = None) -> bool:
        """Send message through the communication system.
        
        Args:
            message: Message to send
            session_id: Optional session ID
            
        Returns:
            True if message was queued successfully
        """
        # Add session context if provided
        if session_id:
            message.add_context("session_id", session_id)
        
        return await self.message_queue.enqueue(message)
    
    async def start_processing(self):
        """Start the message processing loop."""
        self._running = True
        self.logger.info("Started message processing")
        
        while self._running:
            try:
                message = await self.message_queue.dequeue()
                if message:
                    await self._process_message(message)
                else:
                    # No messages, wait a bit
                    await asyncio.sleep(0.1)
                    
                # Cleanup expired sessions periodically
                self.protocol.cleanup_expired_sessions()
                
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    def stop_processing(self):
        """Stop the message processing loop."""
        self._running = False
        self.logger.info("Stopped message processing")
    
    async def _process_message(self, message: ChatMessage):
        """Process a single message.
        
        Args:
            message: Message to process
        """
        try:
            session_id = message.get_context("session_id")
            response = await self.protocol.process_message(message, session_id)
            
            # Route to target agent if specified
            if message.send_to != "System" and message.send_to in self.agents:
                target_agent = self.agents[message.send_to]
                if hasattr(target_agent, 'process_message'):
                    await target_agent.process_message(message)
                elif hasattr(target_agent, 'talk'):
                    target_agent.talk(message)
            
        except Exception as e:
            self.logger.error(f"Error processing message {message.message_id}: {e}")
    
    def create_communication_session(self, initiator: str, participants: List[str]) -> str:
        """Create a new communication session.
        
        Args:
            initiator: Initiating agent
            participants: Participating agents
            
        Returns:
            Session ID
        """
        return self.protocol.create_session(initiator, participants)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "queue_size": self.message_queue.size(),
            "registered_agents": len(self.agents),
            "session_stats": self.protocol.get_session_stats(),
            "is_processing": self._running
        }
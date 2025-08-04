"""
Base agent interface for Text2SQL multi-agent system.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from utils.models import ChatMessage, AgentResponse


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class MessageRouter:
    """Message routing system for inter-agent communication."""
    
    def __init__(self):
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.message_history: List[Dict[str, Any]] = []
        self.routing_rules: Dict[str, str] = {}
    
    def register_agent(self, agent: 'BaseAgent'):
        """Register an agent with the router.
        
        Args:
            agent: Agent instance to register
        """
        self.agents[agent.agent_name] = agent
        logging.info(f"Registered agent: {agent.agent_name}")
    
    def route_message(self, message: ChatMessage, from_agent: str = "System") -> Optional[AgentResponse]:
        """Route message to appropriate agent.
        
        Args:
            message: Message to route
            from_agent: Name of sending agent
            
        Returns:
            Response from target agent or None if routing fails
        """
        target_agent = message.send_to
        
        # Log message routing
        self.message_history.append({
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": target_agent,
            "message_id": id(message),
            "query": message.query[:100] + "..." if len(message.query) > 100 else message.query
        })
        
        if target_agent == "System":
            logging.info(f"Message completed processing chain")
            return None
        
        if target_agent not in self.agents:
            logging.error(f"Target agent '{target_agent}' not found")
            return None
        
        target_agent_instance = self.agents[target_agent]
        logging.info(f"Routing message from {from_agent} to {target_agent}")
        
        try:
            response = target_agent_instance.talk(message)
            return response
        except Exception as e:
            logging.error(f"Error routing message to {target_agent}: {e}")
            return None
    
    def get_routing_history(self) -> List[Dict[str, Any]]:
        """Get message routing history.
        
        Returns:
            List of routing events
        """
        return self.message_history.copy()
    
    def clear_history(self):
        """Clear message routing history."""
        self.message_history.clear()


class BaseAgent(ABC):
    """Abstract base class for all intelligent agents."""
    
    def __init__(self, agent_name: str, router: Optional[MessageRouter] = None):
        """Initialize base agent.
        
        Args:
            agent_name: Name identifier for this agent
            router: Message router for inter-agent communication
        """
        self.agent_name = agent_name
        self.router = router
        self.state = AgentState.IDLE
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = 0.0
        self.last_error: Optional[str] = None
        self.context_memory: Dict[str, Any] = {}
        
        # Register with router if provided
        if self.router:
            self.router.register_agent(self)
        
        # Setup logging
        self.logger = logging.getLogger(f"Agent.{agent_name}")
    
    @abstractmethod
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process a message and return response.
        
        Args:
            message: Input message to process
            
        Returns:
            AgentResponse containing processed message and metadata
        """
        pass
    
    def process_message(self, message: ChatMessage) -> AgentResponse:
        """Process message with state management and error handling.
        
        Args:
            message: Input message to process
            
        Returns:
            AgentResponse with processing results
        """
        start_time = time.time()
        self.state = AgentState.PROCESSING
        
        try:
            self.logger.info(f"Processing message: {message.query[:100]}...")
            
            # Call the abstract talk method
            response = self.talk(message)
            
            # Update statistics
            execution_time = time.time() - start_time
            self.last_execution_time = execution_time
            self.total_execution_time += execution_time
            self._update_stats(response.success)
            
            # Update state
            self.state = AgentState.COMPLETED if response.success else AgentState.ERROR
            
            # Store execution time in response
            response.execution_time = execution_time
            
            # Route message to next agent if specified
            if response.message.send_to != "System" and self.router:
                next_response = self.router.route_message(response.message, self.agent_name)
                if next_response:
                    # Chain responses if needed
                    response.metadata["next_response"] = next_response
            
            self.logger.info(f"Message processed successfully in {execution_time:.3f}s")
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.last_execution_time = execution_time
            self.total_execution_time += execution_time
            self.last_error = str(e)
            self.state = AgentState.ERROR
            self._update_stats(False)
            
            self.logger.error(f"Error processing message: {e}")
            
            return AgentResponse(
                success=False,
                message=message,
                error=str(e),
                execution_time=execution_time
            )
    
    def send_message(self, message: ChatMessage) -> Optional[AgentResponse]:
        """Send message to another agent via router.
        
        Args:
            message: Message to send
            
        Returns:
            Response from target agent or None
        """
        if not self.router:
            self.logger.warning("No router available for message sending")
            return None
        
        return self.router.route_message(message, self.agent_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        success_rate = self.success_count / self.execution_count if self.execution_count > 0 else 0.0
        error_rate = self.error_count / self.execution_count if self.execution_count > 0 else 0.0
        avg_execution_time = self.total_execution_time / self.execution_count if self.execution_count > 0 else 0.0
        
        return {
            "agent_name": self.agent_name,
            "state": self.state.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "last_execution_time": self.last_execution_time,
            "last_error": self.last_error
        }
    
    def reset_stats(self):
        """Reset agent statistics."""
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = 0.0
        self.last_error = None
        self.state = AgentState.IDLE
        self.logger.info("Agent statistics reset")
    
    def set_context(self, key: str, value: Any):
        """Set context memory for the agent.
        
        Args:
            key: Context key
            value: Context value
        """
        self.context_memory[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context memory value.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self.context_memory.get(key, default)
    
    def clear_context(self):
        """Clear agent context memory."""
        self.context_memory.clear()
        self.logger.info("Agent context memory cleared")
    
    def _update_stats(self, success: bool):
        """Update agent statistics.
        
        Args:
            success: Whether the operation was successful
        """
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def _validate_message(self, message: ChatMessage) -> bool:
        """Validate incoming message format.
        
        Args:
            message: Message to validate
            
        Returns:
            True if message is valid
        """
        if not message.db_id:
            self.logger.error("Message missing db_id")
            return False
        
        if not message.query:
            self.logger.error("Message missing query")
            return False
        
        return True
    
    def _prepare_response(self, message: ChatMessage, success: bool = True, 
                         error: Optional[str] = None, **kwargs) -> AgentResponse:
        """Prepare standardized agent response.
        
        Args:
            message: Original message
            success: Whether processing was successful
            error: Error message if any
            **kwargs: Additional metadata
            
        Returns:
            Formatted agent response
        """
        metadata = {
            "agent_name": self.agent_name,
            "processing_time": self.last_execution_time,
            **kwargs
        }
        
        return AgentResponse(
            success=success,
            message=message,
            error=error,
            execution_time=self.last_execution_time,
            metadata=metadata
        )
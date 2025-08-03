"""
Base agent interface for Text2SQL multi-agent system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from utils.models import ChatMessage, AgentResponse


class BaseAgent(ABC):
    """Abstract base class for all intelligent agents."""
    
    def __init__(self, agent_name: str):
        """Initialize base agent.
        
        Args:
            agent_name: Name identifier for this agent
        """
        self.agent_name = agent_name
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
    
    @abstractmethod
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process a message and return response.
        
        Args:
            message: Input message to process
            
        Returns:
            AgentResponse containing processed message and metadata
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        success_rate = self.success_count / self.execution_count if self.execution_count > 0 else 0.0
        error_rate = self.error_count / self.execution_count if self.execution_count > 0 else 0.0
        
        return {
            "agent_name": self.agent_name,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "error_rate": error_rate
        }
    
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
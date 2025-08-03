"""
Unit tests for BaseAgent.
"""
import pytest
from agents.base_agent import BaseAgent
from utils.models import ChatMessage, AgentResponse


class TestAgent(BaseAgent):
    """Test implementation of BaseAgent."""
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Test implementation of talk method."""
        self._update_stats(True)
        return AgentResponse(
            success=True,
            message=message,
            execution_time=0.1
        )


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized."""
        agent = TestAgent("test_agent")
        
        assert agent.agent_name == "test_agent"
        assert agent.execution_count == 0
        assert agent.success_count == 0
        assert agent.error_count == 0
    
    def test_agent_stats_initial(self):
        """Test initial agent statistics."""
        agent = TestAgent("test_agent")
        stats = agent.get_stats()
        
        assert stats["agent_name"] == "test_agent"
        assert stats["execution_count"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["error_rate"] == 0.0
    
    def test_agent_talk_updates_stats(self):
        """Test that talk method updates statistics."""
        agent = TestAgent("test_agent")
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        response = agent.talk(message)
        
        assert response.success is True
        assert agent.execution_count == 1
        assert agent.success_count == 1
        assert agent.error_count == 0
    
    def test_agent_stats_after_execution(self):
        """Test agent statistics after execution."""
        agent = TestAgent("test_agent")
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        # Execute multiple times
        agent.talk(message)
        agent.talk(message)
        agent._update_stats(False)  # Simulate one failure
        
        stats = agent.get_stats()
        assert stats["execution_count"] == 3
        assert stats["success_count"] == 2
        assert stats["error_count"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["error_rate"] == 1/3
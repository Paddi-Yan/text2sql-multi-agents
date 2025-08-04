"""
Unit tests for BaseAgent and communication system.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from agents.base_agent import BaseAgent, MessageRouter, AgentState
from agents.communication import (
    MessageQueue, CommunicationProtocol, AgentCommunicationManager,
    CommunicationState, MessagePriority
)
from utils.models import ChatMessage, AgentResponse


class MockTestAgent(BaseAgent):
    """Test implementation of BaseAgent."""
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Test implementation of talk method."""
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        # Simulate some processing
        if message.query == "error":
            raise ValueError("Test error")
        
        # Update message for next agent
        message.final_sql = f"SELECT * FROM {message.db_id}"
        message.send_to = "NextAgent" if message.send_to == "MockTestAgent" else "System"
        
        return self._prepare_response(message, success=True)


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized."""
        agent = MockTestAgent("test_agent")
        
        assert agent.agent_name == "test_agent"
        assert agent.execution_count == 0
        assert agent.success_count == 0
        assert agent.error_count == 0
        assert agent.state == AgentState.IDLE
    
    def test_agent_initialization_with_router(self):
        """Test agent initialization with message router."""
        router = MessageRouter()
        agent = MockTestAgent("test_agent", router)
        
        assert agent.router == router
        assert "test_agent" in router.agents
    
    def test_agent_stats_initial(self):
        """Test initial agent statistics."""
        agent = MockTestAgent("test_agent")
        stats = agent.get_stats()
        
        assert stats["agent_name"] == "test_agent"
        assert stats["state"] == "idle"
        assert stats["execution_count"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["error_rate"] == 0.0
        assert stats["total_execution_time"] == 0.0
    
    def test_agent_process_message_success(self):
        """Test successful message processing."""
        agent = MockTestAgent("test_agent")
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        response = agent.process_message(message)
        
        assert response.success is True
        assert agent.execution_count == 1
        assert agent.success_count == 1
        assert agent.error_count == 0
        assert agent.state == AgentState.COMPLETED
        assert response.execution_time >= 0
    
    def test_agent_process_message_error(self):
        """Test message processing with error."""
        agent = MockTestAgent("test_agent")
        message = ChatMessage(db_id="test", query="error")
        
        response = agent.process_message(message)
        
        assert response.success is False
        assert agent.execution_count == 1
        assert agent.success_count == 0
        assert agent.error_count == 1
        assert agent.state == AgentState.ERROR
        assert "Test error" in response.error
    
    def test_agent_context_management(self):
        """Test agent context memory management."""
        agent = MockTestAgent("test_agent")
        
        agent.set_context("key1", "value1")
        agent.set_context("key2", {"nested": "value"})
        
        assert agent.get_context("key1") == "value1"
        assert agent.get_context("key2")["nested"] == "value"
        assert agent.get_context("nonexistent", "default") == "default"
        
        agent.clear_context()
        assert agent.get_context("key1") is None
    
    def test_agent_stats_reset(self):
        """Test agent statistics reset."""
        agent = MockTestAgent("test_agent")
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        # Execute some operations
        agent.process_message(message)
        agent.process_message(message)
        
        assert agent.execution_count == 2
        
        agent.reset_stats()
        
        assert agent.execution_count == 0
        assert agent.success_count == 0
        assert agent.error_count == 0
        assert agent.state == AgentState.IDLE
    
    def test_message_validation(self):
        """Test message validation."""
        agent = MockTestAgent("test_agent")
        
        # Valid message
        valid_message = ChatMessage(db_id="test", query="SELECT 1")
        assert agent._validate_message(valid_message) is True
        
        # Invalid messages
        invalid_message1 = ChatMessage(db_id="", query="SELECT 1")
        assert agent._validate_message(invalid_message1) is False
        
        invalid_message2 = ChatMessage(db_id="test", query="")
        assert agent._validate_message(invalid_message2) is False


class TestMessageRouter:
    """Test MessageRouter functionality."""
    
    def test_router_initialization(self):
        """Test router initialization."""
        router = MessageRouter()
        
        assert len(router.agents) == 0
        assert len(router.message_history) == 0
    
    def test_agent_registration(self):
        """Test agent registration."""
        router = MessageRouter()
        agent = MockTestAgent("test_agent")
        
        router.register_agent(agent)
        
        assert "test_agent" in router.agents
        assert router.agents["test_agent"] == agent
    
    def test_message_routing_success(self):
        """Test successful message routing."""
        router = MessageRouter()
        agent = MockTestAgent("test_agent")
        router.register_agent(agent)
        
        message = ChatMessage(db_id="test", query="SELECT 1", send_to="test_agent")
        
        response = router.route_message(message, "System")
        
        assert response is not None
        assert response.success is True
        assert len(router.message_history) == 1
    
    def test_message_routing_to_system(self):
        """Test message routing to System (end of chain)."""
        router = MessageRouter()
        message = ChatMessage(db_id="test", query="SELECT 1", send_to="System")
        
        response = router.route_message(message, "TestAgent")
        
        assert response is None
        assert len(router.message_history) == 1
    
    def test_message_routing_agent_not_found(self):
        """Test message routing to non-existent agent."""
        router = MessageRouter()
        message = ChatMessage(db_id="test", query="SELECT 1", send_to="NonExistentAgent")
        
        response = router.route_message(message, "System")
        
        assert response is None
    
    def test_routing_history(self):
        """Test routing history tracking."""
        router = MessageRouter()
        agent = MockTestAgent("test_agent")
        router.register_agent(agent)
        
        message = ChatMessage(db_id="test", query="SELECT 1", send_to="test_agent")
        router.route_message(message, "System")
        
        history = router.get_routing_history()
        assert len(history) == 1
        assert history[0]["from"] == "System"
        assert history[0]["to"] == "test_agent"
        
        router.clear_history()
        assert len(router.get_routing_history()) == 0


class TestChatMessage:
    """Test ChatMessage functionality."""
    
    def test_message_initialization(self):
        """Test message initialization."""
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        assert message.db_id == "test"
        assert message.query == "SELECT 1"
        assert message.send_to == "System"
        assert message.priority == 1
        assert message.retry_count == 0
        assert isinstance(message.context, dict)
    
    def test_message_copy(self):
        """Test message copying."""
        original = ChatMessage(db_id="test", query="SELECT 1")
        original.add_context("key", "value")
        
        copy = original.copy()
        
        assert copy.db_id == original.db_id
        assert copy.query == original.query
        assert copy.get_context("key") == "value"
        assert copy is not original
    
    def test_message_routing(self):
        """Test message routing functionality."""
        message = ChatMessage(db_id="test", query="SELECT 1", send_to="Agent1")
        
        routed = message.route_to("Agent2")
        
        assert routed.send_to == "Agent2"
        assert routed.sender == "Agent1"
        assert routed is not message
    
    def test_message_context(self):
        """Test message context management."""
        message = ChatMessage(db_id="test", query="SELECT 1")
        
        message.add_context("key1", "value1")
        message.add_context("key2", {"nested": "value"})
        
        assert message.get_context("key1") == "value1"
        assert message.get_context("key2")["nested"] == "value"
        assert message.get_context("nonexistent", "default") == "default"
    
    def test_message_retry_logic(self):
        """Test message retry functionality."""
        message = ChatMessage(db_id="test", query="SELECT 1", max_retries=2)
        
        assert message.increment_retry() is True  # retry_count = 1
        assert message.increment_retry() is True  # retry_count = 2
        assert message.increment_retry() is False  # retry_count = 3, exceeds max
    
    def test_message_priority(self):
        """Test message priority functionality."""
        low_priority = ChatMessage(db_id="test", query="SELECT 1", priority=1)
        high_priority = ChatMessage(db_id="test", query="SELECT 1", priority=3)
        
        assert not low_priority.is_high_priority()
        assert high_priority.is_high_priority()
    
    def test_message_to_dict(self):
        """Test message dictionary conversion."""
        message = ChatMessage(db_id="test", query="SELECT 1")
        message.add_context("key", "value")
        
        message_dict = message.to_dict()
        
        assert message_dict["db_id"] == "test"
        assert message_dict["query"] == "SELECT 1"
        assert message_dict["context"]["key"] == "value"
        assert "timestamp" in message_dict


class TestMessageQueue:
    """Test MessageQueue functionality."""
    
    @pytest.mark.asyncio
    async def test_queue_enqueue_dequeue(self):
        """Test basic enqueue and dequeue operations."""
        queue = MessageQueue(max_size=10)
        
        message = ChatMessage(db_id="test", query="SELECT 1", priority=2)
        
        success = await queue.enqueue(message)
        assert success is True
        assert queue.size() == 1
        
        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert dequeued.query == "SELECT 1"
        assert queue.size() == 0
    
    @pytest.mark.asyncio
    async def test_queue_priority_ordering(self):
        """Test priority-based message ordering."""
        queue = MessageQueue(max_size=10)
        
        # Add messages with different priorities
        low_msg = ChatMessage(db_id="test", query="low", priority=1)
        high_msg = ChatMessage(db_id="test", query="high", priority=3)
        normal_msg = ChatMessage(db_id="test", query="normal", priority=2)
        
        await queue.enqueue(low_msg)
        await queue.enqueue(high_msg)
        await queue.enqueue(normal_msg)
        
        # Should dequeue in priority order
        first = await queue.dequeue()
        assert first.query == "high"  # Priority 3
        
        second = await queue.dequeue()
        assert second.query == "normal"  # Priority 2
        
        third = await queue.dequeue()
        assert third.query == "low"  # Priority 1
    
    @pytest.mark.asyncio
    async def test_queue_max_size_handling(self):
        """Test queue behavior when max size is reached."""
        queue = MessageQueue(max_size=2)
        
        msg1 = ChatMessage(db_id="test", query="1", priority=1)
        msg2 = ChatMessage(db_id="test", query="2", priority=2)
        msg3 = ChatMessage(db_id="test", query="3", priority=3)
        
        await queue.enqueue(msg1)
        await queue.enqueue(msg2)
        
        # Queue is full, adding high priority should remove low priority
        success = await queue.enqueue(msg3)
        assert success is True
        assert queue.size() == 2
        
        # Should get high priority message first
        first = await queue.dequeue()
        assert first.query == "3"


class TestCommunicationProtocol:
    """Test CommunicationProtocol functionality."""
    
    def test_protocol_initialization(self):
        """Test protocol initialization."""
        protocol = CommunicationProtocol()
        
        assert len(protocol.sessions) == 0
        assert len(protocol.message_handlers) == 0
        assert len(protocol.middleware) == 0
    
    def test_session_creation(self):
        """Test communication session creation."""
        protocol = CommunicationProtocol()
        
        session_id = protocol.create_session("Agent1", ["Agent2", "Agent3"])
        
        assert session_id in protocol.sessions
        session = protocol.get_session(session_id)
        assert session.initiator == "Agent1"
        assert "Agent2" in session.participants
        assert session.state == CommunicationState.IDLE
    
    def test_session_management(self):
        """Test session lifecycle management."""
        protocol = CommunicationProtocol()
        
        session_id = protocol.create_session("Agent1", ["Agent2"])
        session = protocol.get_session(session_id)
        
        assert session.state == CommunicationState.IDLE
        
        protocol.close_session(session_id, CommunicationState.COMPLETED)
        assert session.state == CommunicationState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_message_processing(self):
        """Test message processing through protocol."""
        protocol = CommunicationProtocol()
        
        message = ChatMessage(db_id="test", query="SELECT 1")
        response = await protocol.process_message(message)
        
        assert response.success is True
        assert response.message == message
    
    def test_message_handler_registration(self):
        """Test message handler registration."""
        protocol = CommunicationProtocol()
        
        async def test_handler(message):
            return AgentResponse(success=True, message=message)
        
        protocol.register_message_handler("test_type", test_handler)
        
        assert "test_type" in protocol.message_handlers
    
    def test_session_statistics(self):
        """Test session statistics."""
        protocol = CommunicationProtocol()
        
        # Create some sessions
        protocol.create_session("Agent1", ["Agent2"])
        protocol.create_session("Agent2", ["Agent3"])
        
        stats = protocol.get_session_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 0
        assert stats["completed_sessions"] == 0
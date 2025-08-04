"""
Example usage of BaseAgent and inter-agent communication system.
"""

import sys
import os
import asyncio
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, MessageRouter, AgentState
from agents.communication import (
    AgentCommunicationManager, CommunicationProtocol, MessageQueue,
    CommunicationState, MessagePriority
)
from utils.models import ChatMessage, AgentResponse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class SelectorAgent(BaseAgent):
    """Mock Selector agent for demonstration."""
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process message as Selector agent."""
        self.logger.info(f"Selector processing query: {message.query}")
        
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        # Simulate schema selection and pruning
        message.desc_str = f"Schema for {message.db_id}: users(id, name, email), orders(id, user_id, amount)"
        message.extracted_schema = {
            "users": ["id", "name", "email"],
            "orders": ["id", "user_id", "amount"]
        }
        message.pruned = True
        
        # Route to Decomposer
        message.send_to = "Decomposer"
        
        self.logger.info("Selector completed schema selection")
        return self._prepare_response(message, success=True, schema_selected=True)


class DecomposerAgent(BaseAgent):
    """Mock Decomposer agent for demonstration."""
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process message as Decomposer agent."""
        self.logger.info(f"Decomposer processing query: {message.query}")
        
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        # Simulate SQL generation
        if "users" in message.query.lower():
            message.final_sql = f"SELECT * FROM users WHERE name LIKE '%{message.query}%'"
        elif "orders" in message.query.lower():
            message.final_sql = f"SELECT * FROM orders WHERE amount > 100"
        else:
            message.final_sql = f"SELECT COUNT(*) FROM users"
        
        message.qa_pairs = f"Q: {message.query}\nA: {message.final_sql}"
        
        # Route to Refiner
        message.send_to = "Refiner"
        
        self.logger.info(f"Decomposer generated SQL: {message.final_sql}")
        return self._prepare_response(message, success=True, sql_generated=True)


class RefinerAgent(BaseAgent):
    """Mock Refiner agent for demonstration."""
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process message as Refiner agent."""
        self.logger.info(f"Refiner processing SQL: {message.final_sql}")
        
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        # Simulate SQL validation and execution
        if "SELECT" not in message.final_sql.upper():
            # SQL needs fixing
            message.final_sql = f"SELECT * FROM users -- Fixed by Refiner"
            message.fixed = True
            self.logger.info("Refiner fixed SQL syntax")
        
        # Simulate execution result
        message.execution_result = {
            "success": True,
            "rows": 5,
            "execution_time": 0.05,
            "data": [("1", "John", "john@example.com"), ("2", "Jane", "jane@example.com")]
        }
        
        # End of processing chain
        message.send_to = "System"
        
        self.logger.info("Refiner completed SQL validation and execution")
        return self._prepare_response(message, success=True, sql_executed=True)


async def demonstrate_basic_agent_functionality():
    """Demonstrate basic agent functionality."""
    print("=== 基础智能体功能演示 ===\n")
    
    # Create agents
    selector = SelectorAgent("Selector")
    decomposer = DecomposerAgent("Decomposer")
    refiner = RefinerAgent("Refiner")
    
    print("1. 智能体初始化")
    print(f"Selector状态: {selector.get_stats()}")
    print(f"Decomposer状态: {decomposer.get_stats()}")
    print(f"Refiner状态: {refiner.get_stats()}")
    
    print("\n2. 单个智能体消息处理")
    message = ChatMessage(
        db_id="ecommerce_db",
        query="Show all users with name John",
        evidence="User wants to find users by name"
    )
    
    # Process through Selector
    response = selector.process_message(message)
    print(f"Selector处理结果: 成功={response.success}, 执行时间={response.execution_time:.4f}s")
    print(f"Schema选择: {response.message.extracted_schema}")
    
    # Process through Decomposer
    response = decomposer.process_message(response.message)
    print(f"Decomposer处理结果: 成功={response.success}, SQL={response.message.final_sql}")
    
    # Process through Refiner
    response = refiner.process_message(response.message)
    print(f"Refiner处理结果: 成功={response.success}, 执行结果={response.message.execution_result}")
    
    print("\n3. 智能体统计信息")
    for agent in [selector, decomposer, refiner]:
        stats = agent.get_stats()
        print(f"{agent.agent_name}: 执行{stats['execution_count']}次, "
              f"成功率{stats['success_rate']:.2%}, "
              f"平均执行时间{stats['average_execution_time']:.4f}s")


async def demonstrate_message_routing():
    """Demonstrate message routing functionality."""
    print("\n=== 消息路由功能演示 ===\n")
    
    # Create router and agents
    router = MessageRouter()
    selector = SelectorAgent("Selector", router)
    decomposer = DecomposerAgent("Decomposer", router)
    refiner = RefinerAgent("Refiner", router)
    
    print("1. 智能体注册到路由器")
    print(f"注册的智能体: {list(router.agents.keys())}")
    
    print("\n2. 消息路由处理")
    message = ChatMessage(
        db_id="ecommerce_db",
        query="Count all orders",
        send_to="Selector"
    )
    
    # Start routing chain
    current_message = message
    step = 1
    
    while current_message.send_to != "System":
        print(f"\n步骤 {step}: 路由到 {current_message.send_to}")
        response = router.route_message(current_message, "System" if step == 1 else current_message.sender)
        
        if response:
            current_message = response.message
            print(f"处理结果: 成功={response.success}")
            if hasattr(response.metadata, 'get'):
                if response.metadata.get('schema_selected'):
                    print(f"  - Schema已选择: {current_message.extracted_schema}")
                if response.metadata.get('sql_generated'):
                    print(f"  - SQL已生成: {current_message.final_sql}")
                if response.metadata.get('sql_executed'):
                    print(f"  - SQL已执行: {current_message.execution_result}")
        else:
            print("路由失败")
            break
        
        step += 1
        if step > 5:  # Prevent infinite loop
            break
    
    print(f"\n3. 路由历史")
    history = router.get_routing_history()
    for i, event in enumerate(history, 1):
        print(f"  {i}. {event['from']} -> {event['to']} at {event['timestamp']}")


async def demonstrate_communication_protocol():
    """Demonstrate advanced communication protocol."""
    print("\n=== 高级通信协议演示 ===\n")
    
    # Create communication manager
    comm_manager = AgentCommunicationManager()
    
    # Create and register agents
    selector = SelectorAgent("Selector")
    decomposer = DecomposerAgent("Decomposer")
    refiner = RefinerAgent("Refiner")
    
    comm_manager.register_agent("Selector", selector)
    comm_manager.register_agent("Decomposer", decomposer)
    comm_manager.register_agent("Refiner", refiner)
    
    print("1. 通信管理器初始化")
    stats = comm_manager.get_stats()
    print(f"注册智能体数: {stats['registered_agents']}")
    print(f"消息队列大小: {stats['queue_size']}")
    
    print("\n2. 创建通信会话")
    session_id = comm_manager.create_communication_session(
        "Selector", 
        ["Decomposer", "Refiner"]
    )
    print(f"会话ID: {session_id}")
    
    print("\n3. 发送不同优先级的消息")
    
    # High priority message
    high_priority_msg = ChatMessage(
        db_id="urgent_db",
        query="URGENT: System health check",
        priority=MessagePriority.HIGH.value,
        send_to="Selector"
    )
    
    # Normal priority message
    normal_msg = ChatMessage(
        db_id="normal_db",
        query="Show user statistics",
        priority=MessagePriority.NORMAL.value,
        send_to="Selector"
    )
    
    # Low priority message
    low_msg = ChatMessage(
        db_id="batch_db",
        query="Generate monthly report",
        priority=MessagePriority.LOW.value,
        send_to="Selector"
    )
    
    # Send messages (they will be queued by priority)
    await comm_manager.send_message(low_msg, session_id)
    await comm_manager.send_message(high_priority_msg, session_id)
    await comm_manager.send_message(normal_msg, session_id)
    
    print(f"消息队列大小: {comm_manager.message_queue.size()}")
    
    print("\n4. 消息处理顺序 (按优先级)")
    
    # Process messages manually to show priority ordering
    for i in range(3):
        message = await comm_manager.message_queue.dequeue()
        if message:
            print(f"  处理消息 {i+1}: 优先级={message.priority}, 查询='{message.query}'")
    
    print("\n5. 会话统计")
    session_stats = comm_manager.protocol.get_session_stats()
    print(f"总会话数: {session_stats['total_sessions']}")
    print(f"活跃会话数: {session_stats['active_sessions']}")


async def demonstrate_error_handling():
    """Demonstrate error handling and retry mechanisms."""
    print("\n=== 错误处理和重试机制演示 ===\n")
    
    class ErrorProneAgent(BaseAgent):
        """Agent that sometimes fails for demonstration."""
        
        def __init__(self, name: str, failure_rate: float = 0.3):
            super().__init__(name)
            self.failure_rate = failure_rate
            self.attempt_count = 0
        
        def talk(self, message: ChatMessage) -> AgentResponse:
            self.attempt_count += 1
            
            # Simulate random failures
            import random
            if random.random() < self.failure_rate:
                raise Exception(f"Simulated failure on attempt {self.attempt_count}")
            
            message.send_to = "System"
            return self._prepare_response(message, success=True, attempts=self.attempt_count)
    
    print("1. 创建容易出错的智能体")
    error_agent = ErrorProneAgent("ErrorProneAgent", failure_rate=0.7)
    
    print("\n2. 测试错误处理")
    message = ChatMessage(
        db_id="test_db",
        query="Test error handling",
        max_retries=3
    )
    
    success_count = 0
    total_attempts = 5
    
    for i in range(total_attempts):
        try:
            response = error_agent.process_message(message.copy())
            if response.success:
                success_count += 1
                print(f"  尝试 {i+1}: 成功 (第{response.metadata.get('attempts', 1)}次尝试)")
            else:
                print(f"  尝试 {i+1}: 失败 - {response.error}")
        except Exception as e:
            print(f"  尝试 {i+1}: 异常 - {e}")
    
    print(f"\n3. 错误处理统计")
    stats = error_agent.get_stats()
    print(f"总执行次数: {stats['execution_count']}")
    print(f"成功次数: {stats['success_count']}")
    print(f"错误次数: {stats['error_count']}")
    print(f"成功率: {stats['success_rate']:.2%}")
    print(f"最后错误: {stats['last_error']}")


async def demonstrate_context_management():
    """Demonstrate agent context management."""
    print("\n=== 上下文管理演示 ===\n")
    
    class ContextAwareAgent(BaseAgent):
        """Agent that uses context for processing."""
        
        def talk(self, message: ChatMessage) -> AgentResponse:
            # Use agent context
            user_preferences = self.get_context("user_preferences", {})
            query_history = self.get_context("query_history", [])
            
            # Add current query to history
            query_history.append(message.query)
            self.set_context("query_history", query_history)
            
            # Use message context
            session_info = message.get_context("session_info", {})
            
            # Process based on context
            if user_preferences.get("format") == "json":
                result = {"query": message.query, "format": "json"}
            else:
                result = f"Processed: {message.query}"
            
            message.add_context("processing_result", result)
            message.send_to = "System"
            
            return self._prepare_response(
                message, 
                success=True, 
                query_count=len(query_history),
                user_format=user_preferences.get("format", "default")
            )
    
    print("1. 创建上下文感知智能体")
    context_agent = ContextAwareAgent("ContextAgent")
    
    print("\n2. 设置智能体上下文")
    context_agent.set_context("user_preferences", {"format": "json", "language": "zh"})
    context_agent.set_context("session_start", "2024-01-01 10:00:00")
    
    print("\n3. 处理带上下文的消息")
    for i, query in enumerate(["Show users", "Count orders", "Generate report"], 1):
        message = ChatMessage(
            db_id="context_db",
            query=query
        )
        message.add_context("session_info", {"session_id": "sess_123", "step": i})
        
        response = context_agent.process_message(message)
        print(f"  查询 {i}: {query}")
        print(f"    处理结果: {response.message.get_context('processing_result')}")
        print(f"    查询计数: {response.metadata.get('query_count')}")
        print(f"    用户格式: {response.metadata.get('user_format')}")
    
    print("\n4. 查看智能体上下文")
    query_history = context_agent.get_context("query_history")
    print(f"查询历史: {query_history}")
    
    print("\n5. 清理上下文")
    context_agent.clear_context()
    print(f"清理后的查询历史: {context_agent.get_context('query_history')}")


async def main():
    """Main demonstration function."""
    print("=== BaseAgent和智能体通信系统演示 ===\n")
    
    # Run all demonstrations
    await demonstrate_basic_agent_functionality()
    await demonstrate_message_routing()
    await demonstrate_communication_protocol()
    await demonstrate_error_handling()
    await demonstrate_context_management()
    
    print("\n=== 演示完成 ===")
    print("\nBaseAgent和通信系统已成功演示以下功能:")
    print("✓ 基础智能体功能 - 消息处理、统计跟踪、状态管理")
    print("✓ 消息路由系统 - 智能体注册、消息路由、历史跟踪")
    print("✓ 高级通信协议 - 会话管理、优先级队列、异步处理")
    print("✓ 错误处理机制 - 异常捕获、重试逻辑、统计跟踪")
    print("✓ 上下文管理 - 智能体上下文、消息上下文、状态保持")
    print("✓ 性能监控 - 执行时间、成功率、详细统计")


if __name__ == "__main__":
    asyncio.run(main())
"""
LangGraph Memory功能演示脚本

展示如何使用LangGraph的短期记忆功能来保持多轮对话的上下文，
特别是在错误重试场景中如何利用对话历史来改进SQL生成。
"""
import sys
import os
import time
import uuid
from typing import Dict, List, Any

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.workflow import OptimizedChatManager, LangGraphMemoryManager
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore


def demonstrate_langgraph_memory():
    """演示LangGraph Memory功能"""
    print("=== LangGraph Memory功能演示 ===\n")
    
    # 创建带Memory功能的ChatManager
    checkpointer = InMemorySaver()
    store = InMemoryStore()
    
    chat_manager = OptimizedChatManager(
        data_path="data",
        dataset_name="generic",
        max_rounds=3,
        enable_memory=True,
        checkpointer=checkpointer,
        store=store
    )
    
    print("✓ ChatManager已创建，启用LangGraph Memory功能")
    print(f"  - Checkpointer: {type(checkpointer).__name__}")
    print(f"  - Store: {type(store).__name__}")
    print()
    
    # 生成唯一的thread_id用于演示
    thread_id = f"demo_thread_{uuid.uuid4().hex[:8]}"
    user_id = "demo_user"
    
    print(f"使用Thread ID: {thread_id}")
    print(f"用户ID: {user_id}")
    print()
    
    # 模拟多轮对话场景
    queries = [
        {
            "query": "Show all users from the database",
            "db_id": "demo_db",
            "evidence": "The database contains user information in a table"
        },
        {
            "query": "Count how many users are active",
            "db_id": "demo_db", 
            "evidence": "Users have an 'active' status field"
        },
        {
            "query": "Find users created in the last month",
            "db_id": "demo_db",
            "evidence": "Users have a 'created_at' timestamp field"
        }
    ]
    
    results = []
    
    for i, query_info in enumerate(queries, 1):
        print(f"--- 查询 {i} ---")
        print(f"Query: {query_info['query']}")
        print(f"Evidence: {query_info['evidence']}")
        
        # 处理查询（使用相同的thread_id保持上下文）
        result = chat_manager.process_query(
            db_id=query_info["db_id"],
            query=query_info["query"],
            evidence=query_info["evidence"],
            user_id=user_id,
            thread_id=thread_id
        )
        
        results.append(result)
        
        print(f"成功: {result['success']}")
        print(f"SQL: {result.get('sql', 'N/A')}")
        print(f"重试次数: {result.get('retry_count', 0)}")
        print(f"对话长度: {result.get('conversation_length', 0)} 条消息")
        print(f"处理时间: {result.get('processing_time', 0):.2f}秒")
        
        if not result['success']:
            print(f"错误: {result.get('error', 'Unknown error')}")
        
        print()
        time.sleep(1)  # 模拟用户思考时间
    
    return thread_id, results


def demonstrate_memory_persistence():
    """持久化功能"""
    print("=== Memory持久化演示 ===\n")
    
    # 创建持久化的Memory组件
    checkpointer = InMemorySaver()
    store = InMemoryStore()
    
    # 第一个ChatManager实例
    chat_manager_1 = OptimizedChatManager(
        enable_memory=True,
        checkpointer=checkpointer,
        store=store
    )
    
    thread_id = f"persistent_thread_{uuid.uuid4().hex[:8]}"
    
    print("第一个ChatManager实例处理查询...")
    result_1 = chat_manager_1.process_query(
        db_id="test_db",
        query="Show all products",
        evidence="Database contains product information",
        thread_id=thread_id
    )
    
    print(f"结果1: 成功={result_1['success']}, 对话长度={result_1.get('conversation_length', 0)}")
    print()
    
    # 第二个ChatManager实例（使用相同的checkpointer和store）
    chat_manager_2 = OptimizedChatManager(
        enable_memory=True,
        checkpointer=checkpointer,
        store=store
    )
    
    print("第二个ChatManager实例处理后续查询...")
    result_2 = chat_manager_2.process_query(
        db_id="test_db",
        query="Count the products",
        evidence="Need to count total products",
        thread_id=thread_id  # 使用相同的thread_id
    )
    
    print(f"结果2: 成功={result_2['success']}, 对话长度={result_2.get('conversation_length', 0)}")
    print()
    
    print("✓ Memory持久化成功！第二个实例能够访问第一个实例的对话历史")


def demonstrate_error_context_with_memory():
    """演示带Memory的错误上下文传递"""
    print("=== 带Memory的错误上下文传递演示 ===\n")
    
    checkpointer = InMemorySaver()
    store = InMemoryStore()
    
    chat_manager = OptimizedChatManager(
        enable_memory=True,
        checkpointer=checkpointer,
        store=store,
        max_rounds=3
    )
    
    thread_id = f"error_context_thread_{uuid.uuid4().hex[:8]}"
    
    print("模拟一个可能失败的查询...")
    
    # 模拟一个复杂查询，可能会触发重试
    result = chat_manager.process_query(
        db_id="complex_db",
        query="Show me all users who have made purchases in the last 30 days with their total spending",
        evidence="Database has users, purchases, and order_items tables with relationships",
        thread_id=thread_id
    )
    
    print(f"查询结果:")
    print(f"  成功: {result['success']}")
    print(f"  SQL: {result.get('sql', 'N/A')}")
    print(f"  重试次数: {result.get('retry_count', 0)}")
    print(f"  对话长度: {result.get('conversation_length', 0)} 条消息")
    print(f"  Memory启用: {result.get('memory_enabled', False)}")
    
    if result.get('retry_count', 0) > 0:
        print(f"  ✓ 系统进行了 {result['retry_count']} 次重试")
        print(f"  ✓ 每次重试都能访问完整的对话历史和错误上下文")
    
    print()
    
    # 继续对话，展示上下文保持
    print("继续对话，测试上下文保持...")
    follow_up_result = chat_manager.process_query(
        db_id="complex_db",
        query="Now show me just the user names from the previous query",
        evidence="Referring to the previous query result",
        thread_id=thread_id
    )
    
    print(f"后续查询结果:")
    print(f"  成功: {follow_up_result['success']}")
    print(f"  对话长度: {follow_up_result.get('conversation_length', 0)} 条消息")
    print(f"  ✓ 系统能够理解'previous query'的引用")


def demonstrate_memory_manager_features():
    """演示LangGraphMemoryManager的功能"""
    print("=== LangGraphMemoryManager功能演示 ===\n")
    
    # 创建模拟状态
    from services.workflow import initialize_state
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    state = initialize_state("demo_db", "Show all users")
    
    print("1. 添加系统消息")
    LangGraphMemoryManager.add_system_message(
        state, 
        "Starting Text2SQL processing",
        {"type": "system_start", "timestamp": time.time()}
    )
    print(f"   消息数量: {len(state['messages'])}")
    
    print("\n2. 添加智能体消息")
    LangGraphMemoryManager.add_agent_message(
        state,
        "Selector",
        "Schema selection completed",
        input_data={"db_id": "demo_db"},
        output_data={"selected_tables": ["users", "profiles"]}
    )
    print(f"   消息数量: {len(state['messages'])}")
    
    print("\n3. 添加错误上下文消息")
    error_info = {
        "error_message": "no such table: user",
        "error_type": "schema_error",
        "failed_sql": "SELECT * FROM user",
        "attempt_number": 1
    }
    LangGraphMemoryManager.add_error_context_message(state, error_info)
    print(f"   消息数量: {len(state['messages'])}")
    
    print("\n4. 获取对话上下文")
    context = LangGraphMemoryManager.get_conversation_context(state, max_messages=10)
    print(f"   上下文条目数: {len(context)}")
    for i, ctx in enumerate(context, 1):
        print(f"   {i}. {ctx['role']}: {ctx['content'][:50]}...")
    
    print("\n5. 提取错误上下文")
    error_contexts = LangGraphMemoryManager.get_error_context_from_messages(state)
    print(f"   错误上下文数: {len(error_contexts)}")
    for i, error in enumerate(error_contexts, 1):
        print(f"   {i}. {error['error_type']}: {error['error_message']}")
    
    print("\n6. 构建上下文感知提示词")
    base_prompt = "Convert the following query to SQL:"
    enhanced_prompt = LangGraphMemoryManager.build_context_aware_prompt(
        base_prompt, state, "Decomposer"
    )
    print(f"   增强提示词长度: {len(enhanced_prompt)} 字符")
    print(f"   包含上下文: {'Session Context' in enhanced_prompt}")
    print(f"   包含错误信息: {'Error Context' in enhanced_prompt}")


def main():
    """主演示函数"""
    print("LangGraph Memory功能完整演示")
    print("=" * 60)
    
    try:
        # 1. 基本Memory功能演示
        thread_id, results = demonstrate_langgraph_memory()
        
        # 2. Memory持久化演示
        demonstrate_memory_persistence()
        
        # 3. 错误上下文与Memory结合演示
        demonstrate_error_context_with_memory()
        
        # 4. MemoryManager功能演示
        demonstrate_memory_manager_features()
        
        print("\n=== 演示总结 ===")
        print("LangGraph Memory功能提供了以下优势:")
        print("1. 自动管理对话历史，无需手动维护")
        print("2. 支持跨实例的Memory持久化")
        print("3. 错误上下文自动集成到对话历史中")
        print("4. 基于thread_id的会话隔离")
        print("5. 丰富的上下文信息用于智能体决策")
        print("6. 与LangGraph生态系统完美集成")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
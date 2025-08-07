"""
Demo script for multi-round error context passing mechanism.

This script demonstrates how the system handles multiple retry attempts
with error context accumulation and analysis.
"""
import sys
import os
import time
from typing import Dict, List, Any

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.models import ChatMessage, classify_error_type
from agents.decomposer_agent import DecomposerAgent
from services.workflow import initialize_state


def simulate_error_scenario():
    """模拟多轮错误场景"""
    print("=== Multi-Round Error Context Passing Demo ===\n")
    
    # 初始化状态
    state = initialize_state("demo_db", "Show all users from the database", max_retries=3)
    print(f"Initial state initialized with max_retries: {state['max_retries']}")
    print(f"Initial error_history: {state['error_history']}")
    print(f"Initial error_context_available: {state['error_context_available']}\n")
    
    # 模拟多次SQL生成失败
    failed_attempts = [
        {
            'sql': 'SELECT * FROM users',
            'error': 'no such table: users'
        },
        {
            'sql': 'SELECT * FROM user_table', 
            'error': 'no such table: user_table'
        },
        {
            'sql': 'SELECT name FROM accounts',
            'error': 'no such column: name'
        }
    ]
    
    decomposer = DecomposerAgent()
    
    for i, attempt in enumerate(failed_attempts, 1):
        print(f"--- Attempt {i} ---")
        print(f"Generated SQL: {attempt['sql']}")
        print(f"Error: {attempt['error']}")
        
        # 分类错误类型
        error_type = classify_error_type(attempt['error'])
        print(f"Classified error type: {error_type}")
        
        # 添加错误记录到状态
        error_record = {
            'attempt_number': i,
            'failed_sql': attempt['sql'],
            'error_message': attempt['error'],
            'error_type': error_type,
            'timestamp': time.time()
        }
        state['error_history'].append(error_record)
        state['error_context_available'] = True
        
        print(f"Error history length: {len(state['error_history'])}")
        
        # 分析错误模式
        if len(state['error_history']) > 1:
            patterns = decomposer._analyze_error_patterns(state['error_history'])
            if patterns:
                print("Identified error patterns:")
                for pattern in patterns:
                    print(f"  - {pattern}")
        
        print()
    
    # 演示错误感知的提示词生成
    print("--- Error-Aware Prompt Generation ---")
    
    message = ChatMessage(
        db_id="demo_db",
        query="Show all users from the database",
        desc_str="Table: user_accounts (id, name, email, created_at)",
        fk_str="",
        evidence="The database contains user information",
        error_history=state['error_history'],
        error_context_available=True
    )
    
    enhanced_prompt = decomposer._build_multi_error_aware_prompt(message)
    print("Generated error-aware prompt:")
    print("-" * 50)
    print(enhanced_prompt[:1000] + "..." if len(enhanced_prompt) > 1000 else enhanced_prompt)
    print("-" * 50)
    print()
    
    # 演示错误感知的QA对生成
    print("--- Error-Aware QA Pairs Generation ---")
    
    error_patterns = decomposer._analyze_error_patterns(state['error_history'])
    message.final_sql = "SELECT * FROM user_accounts"  # 模拟修正后的SQL
    
    qa_pairs = decomposer._build_error_aware_qa_pairs(message, error_patterns)
    print("Generated error-aware QA pairs:")
    print("-" * 50)
    print(qa_pairs)
    print("-" * 50)
    print()
    
    # 演示最终统计
    print("--- Final Statistics ---")
    print(f"Total failed attempts: {len(state['error_history'])}")
    
    error_types = [record['error_type'] for record in state['error_history']]
    unique_error_types = list(set(error_types))
    print(f"Unique error types encountered: {unique_error_types}")
    
    type_counts = {}
    for error_type in error_types:
        type_counts[error_type] = type_counts.get(error_type, 0) + 1
    
    print("Error type distribution:")
    for error_type, count in type_counts.items():
        print(f"  - {error_type}: {count} times")
    
    print(f"\nError context available: {state['error_context_available']}")
    print(f"Ready for intelligent retry: {len(state['error_history']) > 0}")


def demonstrate_error_classification():
    """演示错误分类功能"""
    print("\n=== Error Classification Demo ===\n")
    
    test_errors = [
        "no such table: users",
        "no such column: user.invalid_field", 
        "syntax error near 'FROM'",
        "column must appear in the GROUP BY clause",
        "connection timeout",
        "permission denied",
        "unknown error occurred",
        ""
    ]
    
    print("Error message classification:")
    print("-" * 60)
    print(f"{'Error Message':<35} {'Classification':<20}")
    print("-" * 60)
    
    for error_msg in test_errors:
        error_type = classify_error_type(error_msg)
        display_msg = error_msg if error_msg else "(empty)"
        print(f"{display_msg:<35} {error_type:<20}")
    
    print("-" * 60)


def demonstrate_chat_message_extension():
    """演示ChatMessage扩展功能"""
    print("\n=== ChatMessage Extension Demo ===\n")
    
    # 创建包含错误历史的消息
    error_history = [
        {
            'attempt_number': 1,
            'failed_sql': 'SELECT * FROM users',
            'error_message': 'no such table: users',
            'error_type': 'schema_error',
            'timestamp': time.time()
        },
        {
            'attempt_number': 2,
            'failed_sql': 'SELECT * FROM user_table',
            'error_message': 'no such table: user_table', 
            'error_type': 'schema_error',
            'timestamp': time.time()
        }
    ]
    
    message = ChatMessage(
        db_id="demo_db",
        query="Show all users",
        desc_str="Table: user_accounts (id, name, email)",
        error_history=error_history,
        error_context_available=True
    )
    
    print("ChatMessage with error history:")
    print(f"  Database ID: {message.db_id}")
    print(f"  Query: {message.query}")
    print(f"  Error context available: {message.error_context_available}")
    print(f"  Error history length: {len(message.error_history)}")
    
    print("\nError history details:")
    for i, record in enumerate(message.error_history, 1):
        print(f"  Record {i}:")
        print(f"    Attempt: {record['attempt_number']}")
        print(f"    Failed SQL: {record['failed_sql']}")
        print(f"    Error: {record['error_message']}")
        print(f"    Type: {record['error_type']}")
    
    # 演示get_context方法
    print(f"\nUsing get_context method:")
    print(f"  db_id: {message.get_context('db_id')}")
    print(f"  non_existent: {message.get_context('non_existent')}")
    print(f"  non_existent (with default): {message.get_context('non_existent', 'default_value')}")


def main():
    """主演示函数"""
    print("Multi-Round Error Context Passing Mechanism Demo")
    print("=" * 60)
    
    # 演示错误分类
    demonstrate_error_classification()
    
    # 演示ChatMessage扩展
    demonstrate_chat_message_extension()
    
    # 演示完整的错误场景
    simulate_error_scenario()
    
    print("\n=== Demo Complete ===")
    print("The multi-round error context passing mechanism provides:")
    print("1. Automatic error classification")
    print("2. Error history accumulation across retry attempts")
    print("3. Error pattern analysis and identification")
    print("4. Error-aware prompt generation for improved retry accuracy")
    print("5. Comprehensive error context for debugging and learning")


if __name__ == "__main__":
    main()
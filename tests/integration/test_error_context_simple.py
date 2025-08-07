"""
Simplified integration tests for error context passing mechanism.
"""
import unittest
import time
from unittest.mock import Mock, patch

from utils.models import ChatMessage, classify_error_type
from agents.decomposer_agent import DecomposerAgent
from services.workflow import initialize_state


class TestErrorContextSimple(unittest.TestCase):
    """简化的错误上下文测试"""
    
    def test_error_classification(self):
        """测试错误分类功能"""
        test_cases = [
            ("no such table: users", "schema_error"),
            ("syntax error near FROM", "syntax_error"),
            ("column must appear in GROUP BY", "logic_error"),
            ("connection timeout", "execution_error"),
            ("", "unknown_error")
        ]
        
        for error_msg, expected_type in test_cases:
            result = classify_error_type(error_msg)
            self.assertEqual(result, expected_type, f"Failed for: {error_msg}")
    
    def test_chat_message_error_history(self):
        """测试ChatMessage的错误历史功能"""
        error_history = [
            {
                'attempt_number': 1,
                'failed_sql': 'SELECT * FROM users',
                'error_message': 'no such table: users',
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            error_history=error_history,
            error_context_available=True
        )
        
        self.assertTrue(message.error_context_available)
        self.assertEqual(len(message.error_history), 1)
        self.assertEqual(message.error_history[0]['error_type'], 'schema_error')
    
    def test_workflow_state_initialization(self):
        """测试工作流状态初始化"""
        state = initialize_state("test_db", "Show all users")
        
        self.assertIn('error_history', state)
        self.assertIn('error_context_available', state)
        self.assertEqual(state['error_history'], [])
        self.assertFalse(state['error_context_available'])
    
    def test_decomposer_error_pattern_analysis(self):
        """测试Decomposer的错误模式分析"""
        decomposer = DecomposerAgent()
        
        # 测试空历史
        patterns = decomposer._analyze_error_patterns([])
        self.assertEqual(patterns, [])
        
        # 测试重复错误类型
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
        
        patterns = decomposer._analyze_error_patterns(error_history)
        self.assertTrue(any('Repeated schema_error errors' in pattern for pattern in patterns))
    
    def test_decomposer_error_aware_prompt(self):
        """测试Decomposer的错误感知提示词生成"""
        decomposer = DecomposerAgent()
        
        error_history = [
            {
                'attempt_number': 1,
                'failed_sql': 'SELECT * FROM users',
                'error_message': 'no such table: users',
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="Table: user_accounts (id, name, email)",
            fk_str="",
            evidence="",
            error_history=error_history,
            error_context_available=True
        )
        
        prompt = decomposer._build_multi_error_aware_prompt(message)
        
        # 验证提示词包含关键信息
        self.assertIn("Previous Attempts Analysis", prompt)
        self.assertIn("Attempt 1", prompt)
        self.assertIn("no such table: users", prompt)
        self.assertIn("schema_error", prompt)
        self.assertIn("Instructions for Next Attempt", prompt)
    
    def test_decomposer_handles_malformed_error_records(self):
        """测试Decomposer处理格式错误的错误记录"""
        decomposer = DecomposerAgent()
        
        # 创建格式不完整的错误记录
        malformed_history = [
            {
                'attempt_number': 1,
                'failed_sql': 'SELECT * FROM users',
                # 缺少error_message和error_type
                'timestamp': time.time()
            },
            {
                'attempt_number': 2,
                # 缺少failed_sql
                'error_message': 'some error',
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        # 应该能够处理而不崩溃
        patterns = decomposer._analyze_error_patterns(malformed_history)
        self.assertIsInstance(patterns, list)
    
    def test_decomposer_error_context_detection(self):
        """测试Decomposer的错误上下文检测"""
        decomposer = DecomposerAgent()
        
        # 测试有错误上下文的消息
        message_with_error = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="Table: users (id, name)",
            error_history=[{'attempt_number': 1, 'error_type': 'schema_error'}],
            error_context_available=True
        )
        
        # 测试无错误上下文的消息
        message_without_error = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="Table: users (id, name)",
            error_history=[],
            error_context_available=False
        )
        
        # 模拟处理方法
        with patch.object(decomposer, '_handle_retry_with_error_context') as mock_retry, \
             patch.object(decomposer, '_handle_normal_processing') as mock_normal:
            
            mock_retry.return_value = Mock(success=True)
            mock_normal.return_value = Mock(success=True)
            
            # 有错误上下文应该调用重试处理
            decomposer.talk(message_with_error)
            mock_retry.assert_called_once()
            
            # 无错误上下文应该调用正常处理
            decomposer.talk(message_without_error)
            mock_normal.assert_called_once()
    
    def test_error_context_qa_pairs_generation(self):
        """测试错误上下文QA对生成"""
        decomposer = DecomposerAgent()
        
        error_patterns = ["Repeated schema_error errors (2 times)"]
        error_history = [
            {
                'attempt_number': 1,
                'failed_sql': 'SELECT * FROM users',
                'error_message': 'no such table: users',
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            final_sql="SELECT * FROM user_accounts",
            error_history=error_history,
            error_context_available=True
        )
        
        qa_pairs = decomposer._build_error_aware_qa_pairs(message, error_patterns)
        
        # 验证QA对包含必要信息
        self.assertIn("Error-Aware Query Processing", qa_pairs)
        self.assertIn("Identified Error Patterns", qa_pairs)
        self.assertIn("Previous Attempts Summary", qa_pairs)
        self.assertIn("Total failed attempts: 1", qa_pairs)
    
    def test_state_error_history_accumulation(self):
        """测试状态中错误历史的累积"""
        state = initialize_state("test_db", "Show all users", max_retries=3)
        
        # 模拟多次错误
        errors = [
            ('SELECT * FROM users', 'no such table: users'),
            ('SELECT * FROM user_table', 'no such table: user_table'),
            ('SELECT name FROM accounts', 'no such column: name')
        ]
        
        for i, (sql, error_msg) in enumerate(errors):
            error_record = {
                'attempt_number': i + 1,
                'failed_sql': sql,
                'error_message': error_msg,
                'error_type': classify_error_type(error_msg),
                'timestamp': time.time()
            }
            state['error_history'].append(error_record)
        
        # 验证累积结果
        self.assertEqual(len(state['error_history']), 3)
        
        # 验证错误类型分类正确
        error_types = [record['error_type'] for record in state['error_history']]
        self.assertEqual(error_types.count('schema_error'), 3)
        
        # 验证尝试次数正确
        attempt_numbers = [record['attempt_number'] for record in state['error_history']]
        self.assertEqual(attempt_numbers, [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
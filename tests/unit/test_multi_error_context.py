"""
Unit tests for multi-round error context passing mechanism.
"""
import unittest
import time
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from utils.models import ChatMessage, ErrorRecord, classify_error_type
from agents.decomposer_agent import DecomposerAgent
from services.workflow import Text2SQLState, initialize_state


class TestErrorRecord(unittest.TestCase):
    """测试ErrorRecord数据结构"""
    
    def test_error_record_creation(self):
        """测试ErrorRecord创建"""
        error_record = ErrorRecord(
            attempt_number=1,
            failed_sql="SELECT * FROM non_existent_table",
            error_message="no such table: non_existent_table",
            error_type="schema_error",
            timestamp=time.time()
        )
        
        self.assertEqual(error_record.attempt_number, 1)
        self.assertEqual(error_record.failed_sql, "SELECT * FROM non_existent_table")
        self.assertEqual(error_record.error_message, "no such table: non_existent_table")
        self.assertEqual(error_record.error_type, "schema_error")
        self.assertIsInstance(error_record.timestamp, float)


class TestErrorClassification(unittest.TestCase):
    """测试错误类型分类功能"""
    
    def test_classify_syntax_error(self):
        """测试语法错误分类"""
        error_msg = "syntax error near 'FROM'"
        result = classify_error_type(error_msg)
        self.assertEqual(result, "syntax_error")
    
    def test_classify_schema_error(self):
        """测试模式错误分类"""
        error_msg = "no such table: users"
        result = classify_error_type(error_msg)
        self.assertEqual(result, "schema_error")
        
        error_msg2 = "no such column: user.invalid_column"
        result2 = classify_error_type(error_msg2)
        self.assertEqual(result2, "schema_error")
    
    def test_classify_logic_error(self):
        """测试逻辑错误分类"""
        error_msg = "column must appear in the GROUP BY clause"
        result = classify_error_type(error_msg)
        self.assertEqual(result, "logic_error")
    
    def test_classify_execution_error(self):
        """测试执行错误分类"""
        error_msg = "connection timeout"
        result = classify_error_type(error_msg)
        self.assertEqual(result, "execution_error")
    
    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        error_msg = "some unknown error"
        result = classify_error_type(error_msg)
        self.assertEqual(result, "execution_error")  # 默认为执行错误
    
    def test_classify_empty_error(self):
        """测试空错误消息"""
        result = classify_error_type("")
        self.assertEqual(result, "unknown_error")


class TestChatMessageExtension(unittest.TestCase):
    """测试ChatMessage扩展功能"""
    
    def test_chat_message_with_error_history(self):
        """测试带错误历史的ChatMessage"""
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
        
        self.assertEqual(message.db_id, "test_db")
        self.assertEqual(message.query, "Show all users")
        self.assertEqual(len(message.error_history), 1)
        self.assertTrue(message.error_context_available)
        self.assertEqual(message.error_history[0]['error_type'], 'schema_error')
    
    def test_chat_message_get_context(self):
        """测试ChatMessage的get_context方法"""
        message = ChatMessage(
            db_id="test_db",
            query="Show all users"
        )
        
        # 测试获取存在的属性
        self.assertEqual(message.get_context('db_id'), "test_db")
        
        # 测试获取不存在的属性
        self.assertIsNone(message.get_context('non_existent'))
        
        # 测试获取不存在的属性并提供默认值
        self.assertEqual(message.get_context('non_existent', 'default'), 'default')


class TestWorkflowStateExtension(unittest.TestCase):
    """测试工作流状态扩展"""
    
    def test_initialize_state_with_error_fields(self):
        """测试初始化状态包含错误字段"""
        state = initialize_state(
            db_id="test_db",
            query="Show all users",
            evidence="",
            max_retries=3
        )
        
        self.assertIn('error_history', state)
        self.assertIn('error_context_available', state)
        self.assertEqual(state['error_history'], [])
        self.assertFalse(state['error_context_available'])
    
    def test_state_error_history_update(self):
        """测试状态错误历史更新"""
        state = initialize_state("test_db", "Show all users")
        
        # 模拟添加错误记录
        error_record = {
            'attempt_number': 1,
            'failed_sql': 'SELECT * FROM users',
            'error_message': 'no such table: users',
            'error_type': 'schema_error',
            'timestamp': time.time()
        }
        
        state['error_history'].append(error_record)
        state['error_context_available'] = True
        
        self.assertEqual(len(state['error_history']), 1)
        self.assertTrue(state['error_context_available'])
        self.assertEqual(state['error_history'][0]['error_type'], 'schema_error')


class TestDecomposerErrorHandling(unittest.TestCase):
    """测试Decomposer智能体错误处理"""
    
    def setUp(self):
        """设置测试环境"""
        self.decomposer = DecomposerAgent(
            agent_name="TestDecomposer",
            dataset_name="generic"
        )
    
    def test_analyze_error_patterns_empty_history(self):
        """测试分析空错误历史"""
        patterns = self.decomposer._analyze_error_patterns([])
        self.assertEqual(patterns, [])
    
    def test_analyze_error_patterns_repeated_types(self):
        """测试分析重复错误类型"""
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
        
        patterns = self.decomposer._analyze_error_patterns(error_history)
        
        # 应该识别出重复的schema_error
        self.assertTrue(any('Repeated schema_error errors' in pattern for pattern in patterns))
    
    def test_analyze_error_patterns_identical_messages(self):
        """测试分析相同错误消息"""
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
                'failed_sql': 'SELECT name FROM users',
                'error_message': 'no such table: users',
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        patterns = self.decomposer._analyze_error_patterns(error_history)
        
        # 应该识别出相同的错误消息
        self.assertTrue(any('identical error messages' in pattern for pattern in patterns))
    
    def test_build_multi_error_aware_prompt(self):
        """测试构建多轮错误感知提示词"""
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
        
        prompt = self.decomposer._build_multi_error_aware_prompt(message)
        
        # 检查提示词包含错误信息
        self.assertIn("Previous Attempts Analysis", prompt)
        self.assertIn("Attempt 1", prompt)
        self.assertIn("no such table: users", prompt)
        self.assertIn("schema_error", prompt)
        self.assertIn("Instructions for Next Attempt", prompt)
    
    def test_build_error_aware_qa_pairs(self):
        """测试构建错误感知QA对"""
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
        
        qa_pairs = self.decomposer._build_error_aware_qa_pairs(message, error_patterns)
        
        # 检查QA对包含错误分析信息
        self.assertIn("Error-Aware Query Processing", qa_pairs)
        self.assertIn("Identified Error Patterns", qa_pairs)
        self.assertIn("Repeated schema_error errors", qa_pairs)
        self.assertIn("Previous Attempts Summary", qa_pairs)
        self.assertIn("Total failed attempts: 1", qa_pairs)
    
    @patch('agents.decomposer_agent.llm_service')
    def test_handle_retry_with_error_context(self, mock_llm_service):
        """测试处理带错误上下文的重试"""
        # 模拟LLM服务响应
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "SELECT * FROM user_accounts"
        mock_llm_service.generate_completion.return_value = mock_response
        mock_llm_service.extract_sql_from_response.return_value = "SELECT * FROM user_accounts"
        
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
        
        response = self.decomposer._handle_retry_with_error_context(message)
        
        # 检查响应
        self.assertTrue(response.success)
        self.assertEqual(message.final_sql, "SELECT * FROM user_accounts")
        self.assertEqual(message.send_to, "Refiner")
        self.assertTrue(response.metadata.get('retry_with_error_context', False))


class TestIntegrationWorkflow(unittest.TestCase):
    """测试集成工作流"""
    
    def test_error_context_flow(self):
        """测试错误上下文传递流程"""
        # 初始化状态
        state = initialize_state("test_db", "Show all users", max_retries=2)
        
        # 模拟第一次失败
        state['final_sql'] = 'SELECT * FROM users'
        state['retry_count'] = 0
        
        # 模拟refiner_node添加错误记录
        error_record = {
            'attempt_number': 1,
            'failed_sql': state['final_sql'],
            'error_message': 'no such table: users',
            'error_type': classify_error_type('no such table: users'),
            'timestamp': time.time()
        }
        
        state['error_history'].append(error_record)
        state['error_context_available'] = True
        state['current_agent'] = 'Decomposer'
        state['retry_count'] = 1
        
        # 验证状态更新
        self.assertEqual(len(state['error_history']), 1)
        self.assertTrue(state['error_context_available'])
        self.assertEqual(state['error_history'][0]['error_type'], 'schema_error')
        self.assertEqual(state['current_agent'], 'Decomposer')
        
        # 模拟第二次失败
        error_record_2 = {
            'attempt_number': 2,
            'failed_sql': 'SELECT * FROM user_table',
            'error_message': 'no such table: user_table',
            'error_type': classify_error_type('no such table: user_table'),
            'timestamp': time.time()
        }
        
        state['error_history'].append(error_record_2)
        state['retry_count'] = 2
        
        # 验证多轮错误记录
        self.assertEqual(len(state['error_history']), 2)
        self.assertEqual(state['error_history'][1]['error_type'], 'schema_error')
        
        # 验证错误模式分析
        decomposer = DecomposerAgent()
        patterns = decomposer._analyze_error_patterns(state['error_history'])
        
        # 应该识别出重复的schema_error
        self.assertTrue(any('Repeated schema_error errors' in pattern for pattern in patterns))


if __name__ == '__main__':
    unittest.main()
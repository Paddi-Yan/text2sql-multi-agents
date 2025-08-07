"""
Integration tests for error context passing in the complete workflow.
"""
import unittest
import time
from unittest.mock import Mock, patch, MagicMock

from services.workflow import (
    OptimizedChatManager, 
    create_text2sql_workflow,
    initialize_state,
    refiner_node,
    decomposer_node
)
from utils.models import ChatMessage, classify_error_type
from agents.decomposer_agent import DecomposerAgent
from agents.refiner_agent import RefinerAgent


class TestErrorContextWorkflowIntegration(unittest.TestCase):
    """测试错误上下文在完整工作流中的传递"""
    
    def setUp(self):
        """设置测试环境"""
        self.chat_manager = OptimizedChatManager(
            data_path="test_data",
            tables_json_path="test_data/tables.json",
            dataset_name="generic",
            max_rounds=3,
            enable_memory=False  # 禁用Memory以避免thread_id要求
        )
    
    @patch('agents.refiner_agent.RefinerAgent')
    @patch('agents.decomposer_agent.DecomposerAgent')
    def test_single_retry_with_error_context(self, mock_decomposer_class, mock_refiner_class):
        """测试单次重试的错误上下文传递"""
        
        # 模拟Decomposer智能体
        mock_decomposer = Mock()
        mock_decomposer_response = Mock()
        mock_decomposer_response.success = True
        mock_decomposer_message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            final_sql="SELECT * FROM user_accounts",
            send_to="Refiner"
        )
        mock_decomposer_response.message = mock_decomposer_message
        mock_decomposer.talk.return_value = mock_decomposer_response
        mock_decomposer_class.return_value = mock_decomposer
        
        # 模拟Refiner智能体 - 第一次失败，第二次成功
        mock_refiner = Mock()
        
        # 第一次调用：失败
        mock_refiner_response_1 = Mock()
        mock_refiner_response_1.success = False
        mock_refiner_message_1 = ChatMessage(
            db_id="test_db",
            query="Show all users",
            final_sql="SELECT * FROM users",
            execution_result={
                'is_successful': False,
                'sqlite_error': 'no such table: users'
            },
            send_to="System"
        )
        mock_refiner_response_1.message = mock_refiner_message_1
        
        # 第二次调用：成功
        mock_refiner_response_2 = Mock()
        mock_refiner_response_2.success = True
        mock_refiner_message_2 = ChatMessage(
            db_id="test_db",
            query="Show all users",
            final_sql="SELECT * FROM user_accounts",
            execution_result={
                'is_successful': True,
                'data': [('1', 'John'), ('2', 'Jane')]
            },
            send_to="System"
        )
        mock_refiner_response_2.message = mock_refiner_message_2
        
        mock_refiner.talk.side_effect = [mock_refiner_response_1, mock_refiner_response_2]
        mock_refiner_class.return_value = mock_refiner
        
        # 执行查询处理
        result = self.chat_manager.process_query(
            db_id="test_db",
            query="Show all users",
            evidence=""
        )
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["retry_count"], 1)  # 应该有一次重试
        
        # 验证Decomposer被调用了两次（初始 + 重试）
        self.assertEqual(mock_decomposer.talk.call_count, 2)
        
        # 验证第二次调用Decomposer时传递了错误上下文
        second_call_args = mock_decomposer.talk.call_args_list[1][0][0]
        self.assertTrue(second_call_args.error_context_available)
        self.assertEqual(len(second_call_args.error_history), 1)
        self.assertEqual(second_call_args.error_history[0]['error_type'], 'schema_error')
    
    @patch('agents.refiner_agent.RefinerAgent')
    @patch('agents.decomposer_agent.DecomposerAgent')
    def test_multiple_retries_with_error_accumulation(self, mock_decomposer_class, mock_refiner_class):
        """测试多次重试的错误累积"""
        
        # 模拟Decomposer智能体
        mock_decomposer = Mock()
        mock_decomposer_response = Mock()
        mock_decomposer_response.success = True
        mock_decomposer_message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            final_sql="SELECT * FROM some_table",
            send_to="Refiner"
        )
        mock_decomposer_response.message = mock_decomposer_message
        mock_decomposer.talk.return_value = mock_decomposer_response
        mock_decomposer_class.return_value = mock_decomposer
        
        # 模拟Refiner智能体 - 连续失败
        mock_refiner = Mock()
        
        # 创建多个失败响应
        failure_responses = []
        error_messages = [
            'no such table: users',
            'no such table: user_table', 
            'syntax error near FROM'
        ]
        
        for i, error_msg in enumerate(error_messages):
            mock_response = Mock()
            mock_response.success = False
            mock_message = ChatMessage(
                db_id="test_db",
                query="Show all users",
                final_sql=f"SELECT * FROM table_{i}",
                execution_result={
                    'is_successful': False,
                    'sqlite_error': error_msg
                },
                send_to="System"
            )
            mock_response.message = mock_message
            failure_responses.append(mock_response)
        
        mock_refiner.talk.side_effect = failure_responses
        mock_refiner_class.return_value = mock_refiner
        
        # 执行查询处理
        result = self.chat_manager.process_query(
            db_id="test_db",
            query="Show all users",
            evidence=""
        )
        
        # 验证结果
        self.assertFalse(result["success"])  # 最终应该失败
        self.assertEqual(result["retry_count"], 3)  # 应该达到最大重试次数
        
        # 验证Decomposer被调用了3次（初始 + 2次重试）
        self.assertEqual(mock_decomposer.talk.call_count, 3)
        
        # 验证最后一次调用Decomposer时有完整的错误历史
        last_call_args = mock_decomposer.talk.call_args_list[2][0][0]
        self.assertTrue(last_call_args.error_context_available)
        self.assertEqual(len(last_call_args.error_history), 2)  # 前两次的错误
        
        # 验证错误类型分类正确
        error_types = [record['error_type'] for record in last_call_args.error_history]
        self.assertIn('schema_error', error_types)
    
    def test_error_pattern_analysis(self):
        """测试错误模式分析功能"""
        decomposer = DecomposerAgent()
        
        # 创建包含重复错误模式的历史
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
            },
            {
                'attempt_number': 3,
                'failed_sql': 'SELECT name FROM users',
                'error_message': 'no such table: users',  # 重复的错误消息
                'error_type': 'schema_error',
                'timestamp': time.time()
            }
        ]
        
        patterns = decomposer._analyze_error_patterns(error_history)
        
        # 验证识别出的模式
        self.assertTrue(any('Repeated schema_error errors' in pattern for pattern in patterns))
        self.assertTrue(any('identical error messages' in pattern for pattern in patterns))
        self.assertTrue(any('table_not_found' in pattern for pattern in patterns))
    
    def test_error_aware_prompt_generation(self):
        """测试错误感知提示词生成"""
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
        
        # 验证提示词内容
        self.assertIn("Previous Attempts Analysis", prompt)
        self.assertIn("Attempt 1", prompt)
        self.assertIn("no such table: users", prompt)
        self.assertIn("schema_error", prompt)
        self.assertIn("Instructions for Next Attempt", prompt)
        self.assertIn("double-check the schema information", prompt)
    
    def test_workflow_state_error_history_management(self):
        """测试工作流状态中的错误历史管理"""
        # 初始化状态
        state = initialize_state("test_db", "Show all users", max_retries=3)
        
        # 模拟多次错误添加
        errors = [
            ('SELECT * FROM users', 'no such table: users'),
            ('SELECT * FROM user_table', 'no such table: user_table'),
            ('SELECT name FROM accounts', 'no such column: name')
        ]
        
        for i, (sql, error_msg) in enumerate(errors):
            state['final_sql'] = sql
            state['retry_count'] = i
            
            # 添加错误记录
            error_record = {
                'attempt_number': i + 1,
                'failed_sql': sql,
                'error_message': error_msg,
                'error_type': classify_error_type(error_msg),
                'timestamp': time.time()
            }
            state['error_history'].append(error_record)
            state['error_context_available'] = True
        
        # 验证错误历史
        self.assertEqual(len(state['error_history']), 3)
        self.assertTrue(state['error_context_available'])
        
        # 验证错误类型分类
        error_types = [record['error_type'] for record in state['error_history']]
        self.assertEqual(error_types.count('schema_error'), 3)
        
        # 验证尝试次数递增
        attempt_numbers = [record['attempt_number'] for record in state['error_history']]
        self.assertEqual(attempt_numbers, [1, 2, 3])
    
    def test_chat_manager_error_statistics(self):
        """测试ChatManager的错误统计功能"""
        # 重置统计
        self.chat_manager.reset_stats()
        
        # 模拟一些查询（包括成功和失败的）
        with patch('services.workflow.create_text2sql_workflow') as mock_workflow:
            # 模拟工作流返回失败结果
            mock_workflow_instance = Mock()
            mock_final_state = {
                'success': False,
                'retry_count': 2,
                'error_history': [
                    {'error_type': 'schema_error', 'attempt_number': 1},
                    {'error_type': 'syntax_error', 'attempt_number': 2}
                ]
            }
            mock_workflow_instance.invoke.return_value = mock_final_state
            mock_workflow.return_value = mock_workflow_instance
            
            # 执行查询
            result = self.chat_manager.process_query("test_db", "Show all users")
            
            # 验证统计信息
            stats = self.chat_manager.get_stats()
            self.assertEqual(stats['total_queries'], 1)
            self.assertEqual(stats['failed_queries'], 1)
            self.assertEqual(stats['successful_queries'], 0)


class TestErrorContextEdgeCases(unittest.TestCase):
    """测试错误上下文的边界情况"""
    
    def test_empty_error_history(self):
        """测试空错误历史的处理"""
        decomposer = DecomposerAgent()
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="Table: users (id, name)",  # 添加必要的schema信息
            error_history=[],
            error_context_available=False
        )
        
        # 应该使用正常处理流程
        with patch.object(decomposer, '_handle_normal_processing') as mock_normal:
            mock_response = Mock()
            mock_response.success = True
            mock_normal.return_value = mock_response
            
            result = decomposer.talk(message)
            mock_normal.assert_called_once()
    
    def test_malformed_error_record(self):
        """测试格式错误的错误记录"""
        decomposer = DecomposerAgent()
        
        # 创建格式不完整的错误记录
        malformed_history = [
            {
                'attempt_number': 1,
                'failed_sql': 'SELECT * FROM users',
                # 缺少error_message和error_type
                'timestamp': time.time()
            }
        ]
        
        # 应该能够处理而不崩溃
        patterns = decomposer._analyze_error_patterns(malformed_history)
        self.assertIsInstance(patterns, list)
    
    def test_very_long_error_history(self):
        """测试很长的错误历史"""
        decomposer = DecomposerAgent()
        
        # 创建很长的错误历史
        long_history = []
        for i in range(50):
            long_history.append({
                'attempt_number': i + 1,
                'failed_sql': f'SELECT * FROM table_{i}',
                'error_message': f'no such table: table_{i}',
                'error_type': 'schema_error',
                'timestamp': time.time()
            })
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="Table: user_accounts (id, name, email)",
            error_history=long_history,
            error_context_available=True
        )
        
        # 应该能够处理长历史而不出现性能问题
        prompt = decomposer._build_multi_error_aware_prompt(message)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)


if __name__ == '__main__':
    unittest.main()
"""
LangGraph工作流系统单元测试

测试Text2SQL工作流的状态定义、节点函数和条件路由逻辑。
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from typing import Dict, Any

from services.workflow import (
    Text2SQLState,
    selector_node,
    decomposer_node,
    refiner_node,
    should_continue,
    initialize_state,
    finalize_state
)


class TestText2SQLWorkflow(unittest.TestCase):
    """Text2SQL工作流测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.test_db_id = "test_db"
        self.test_query = "Show me all customers from New York"
        self.test_evidence = "Customer table contains location information"
        
    def test_initialize_state(self):
        """测试状态初始化"""
        state = initialize_state(
            db_id=self.test_db_id,
            query=self.test_query,
            evidence=self.test_evidence,
            user_id="test_user",
            max_retries=3
        )
        
        # 验证基本字段
        self.assertEqual(state['db_id'], self.test_db_id)
        self.assertEqual(state['query'], self.test_query)
        self.assertEqual(state['evidence'], self.test_evidence)
        self.assertEqual(state['user_id'], "test_user")
        self.assertEqual(state['max_retries'], 3)
        
        # 验证初始状态
        self.assertEqual(state['current_agent'], 'Selector')
        self.assertEqual(state['retry_count'], 0)
        self.assertEqual(state['processing_stage'], 'initialized')
        self.assertFalse(state['finished'])
        self.assertFalse(state['success'])
        
        # 验证时间戳
        self.assertIsNotNone(state['start_time'])
        self.assertIsNone(state['end_time'])
    
    def test_finalize_state(self):
        """测试状态完成处理"""
        state = initialize_state(self.test_db_id, self.test_query)
        time.sleep(0.1)  # 模拟处理时间
        
        finalized_state = finalize_state(state)
        
        self.assertIsNotNone(finalized_state['end_time'])
        self.assertGreater(finalized_state['end_time'], finalized_state['start_time'])
    
    @patch('services.workflow.SelectorAgent')
    def test_selector_node_success(self, mock_selector_class):
        """测试Selector节点成功执行"""
        # 模拟Selector智能体
        mock_selector = Mock()
        mock_selector.talk.return_value = {
            'extracted_schema': {'table1': ['col1', 'col2']},
            'desc_str': 'Test description',
            'fk_str': 'Test foreign keys',
            'pruned': True,
            'chosen_db_schema_dict': {'table1': 'keep_all'}
        }
        mock_selector_class.return_value = mock_selector
        
        # 初始化状态
        state = initialize_state(self.test_db_id, self.test_query)
        
        # 执行Selector节点
        result_state = selector_node(state)
        
        # 验证结果
        self.assertEqual(result_state['current_agent'], 'Decomposer')
        self.assertEqual(result_state['processing_stage'], 'schema_selection_completed')
        self.assertTrue(result_state['pruned'])
        self.assertEqual(result_state['desc_str'], 'Test description')
        self.assertIn('selector', result_state['agent_execution_times'])
        
        # 验证Selector被正确调用
        mock_selector.talk.assert_called_once()
        call_args = mock_selector.talk.call_args[0][0]
        self.assertEqual(call_args['db_id'], self.test_db_id)
        self.assertEqual(call_args['query'], self.test_query)
    
    @patch('services.workflow.SelectorAgent')
    def test_selector_node_failure(self, mock_selector_class):
        """测试Selector节点执行失败"""
        # 模拟Selector抛出异常
        mock_selector = Mock()
        mock_selector.talk.side_effect = Exception("Selector failed")
        mock_selector_class.return_value = mock_selector
        
        state = initialize_state(self.test_db_id, self.test_query)
        result_state = selector_node(state)
        
        # 验证错误处理
        self.assertEqual(result_state['current_agent'], 'Error')
        self.assertEqual(result_state['processing_stage'], 'selector_failed')
        self.assertIn('Selector执行失败', result_state['error_message'])
    
    @patch('services.workflow.DecomposerAgent')
    def test_decomposer_node_success(self, mock_decomposer_class):
        """测试Decomposer节点成功执行"""
        # 模拟Decomposer智能体
        mock_decomposer = Mock()
        mock_decomposer.talk.return_value = {
            'final_sql': 'SELECT * FROM customers WHERE city = "New York"',
            'qa_pairs': 'Q: Show customers A: SELECT...',
            'sub_questions': ['Find customers', 'Filter by city'],
            'decomposition_strategy': 'complex'
        }
        mock_decomposer_class.return_value = mock_decomposer
        
        # 准备状态（模拟Selector已完成）
        state = initialize_state(self.test_db_id, self.test_query)
        state.update({
            'current_agent': 'Decomposer',
            'desc_str': 'Test description',
            'fk_str': 'Test FK',
            'extracted_schema': {'table1': ['col1']}
        })
        
        # 执行Decomposer节点
        result_state = decomposer_node(state)
        
        # 验证结果
        self.assertEqual(result_state['current_agent'], 'Refiner')
        self.assertEqual(result_state['processing_stage'], 'sql_generation_completed')
        self.assertIn('SELECT', result_state['final_sql'])
        self.assertEqual(len(result_state['sub_questions']), 2)
        self.assertIn('decomposer', result_state['agent_execution_times'])
    
    @patch('services.workflow.RefinerAgent')
    def test_refiner_node_success(self, mock_refiner_class):
        """测试Refiner节点成功执行"""
        # 模拟Refiner智能体
        mock_refiner = Mock()
        mock_refiner.talk.return_value = {
            'execution_result': {
                'is_successful': True,
                'data': [('Customer1', 'New York'), ('Customer2', 'New York')],
                'execution_time': 0.1
            },
            'fixed': False
        }
        mock_refiner_class.return_value = mock_refiner
        
        # 准备状态（模拟Decomposer已完成）
        state = initialize_state(self.test_db_id, self.test_query)
        state.update({
            'current_agent': 'Refiner',
            'final_sql': 'SELECT * FROM customers WHERE city = "New York"',
            'desc_str': 'Test description',
            'fk_str': 'Test FK'
        })
        
        # 执行Refiner节点
        result_state = refiner_node(state)
        
        # 验证结果
        self.assertTrue(result_state['finished'])
        self.assertTrue(result_state['success'])
        self.assertTrue(result_state['is_correct'])
        self.assertEqual(result_state['current_agent'], 'Completed')
        self.assertIsNotNone(result_state['result'])
        self.assertIn('refiner', result_state['agent_execution_times'])
    
    @patch('services.workflow.RefinerAgent')
    def test_refiner_node_failure_with_retry(self, mock_refiner_class):
        """测试Refiner节点失败并触发重试"""
        # 模拟Refiner智能体返回执行失败
        mock_refiner = Mock()
        mock_refiner.talk.return_value = {
            'execution_result': {
                'is_successful': False,
                'sqlite_error': 'Syntax error in SQL',
                'execution_time': 0.1
            },
            'fixed': False
        }
        mock_refiner_class.return_value = mock_refiner
        
        # 准备状态
        state = initialize_state(self.test_db_id, self.test_query, max_retries=2)
        state.update({
            'current_agent': 'Refiner',
            'final_sql': 'INVALID SQL',
            'desc_str': 'Test description',
            'fk_str': 'Test FK'
        })
        
        # 执行Refiner节点
        result_state = refiner_node(state)
        
        # 验证重试逻辑
        self.assertFalse(result_state['finished'])
        self.assertFalse(result_state['is_correct'])
        self.assertEqual(result_state['refinement_attempts'], 1)
        self.assertIn('Syntax error', result_state['error_message'])
    
    def test_should_continue_routing(self):
        """测试条件路由逻辑"""
        # 测试Selector -> Decomposer
        state = initialize_state(self.test_db_id, self.test_query)
        state['current_agent'] = 'Selector'
        self.assertEqual(should_continue(state), "decomposer")
        
        # 测试Decomposer -> Refiner
        state['current_agent'] = 'Decomposer'
        self.assertEqual(should_continue(state), "refiner")
        
        # 测试Refiner成功 -> end
        state['current_agent'] = 'Completed'
        state['finished'] = True
        self.assertEqual(should_continue(state), "end")
        
        # 测试Refiner失败但可重试 -> decomposer
        state = initialize_state(self.test_db_id, self.test_query, max_retries=2)
        state.update({
            'current_agent': 'Refiner',
            'is_correct': False,
            'retry_count': 0,
            'finished': False
        })
        self.assertEqual(should_continue(state), "decomposer")
        
        # 测试达到最大重试次数 -> end
        state['retry_count'] = 2
        self.assertEqual(should_continue(state), "end")
    
    def test_state_type_validation(self):
        """测试状态类型验证"""
        state = initialize_state(self.test_db_id, self.test_query)
        
        # 验证必需字段类型
        self.assertIsInstance(state['db_id'], str)
        self.assertIsInstance(state['query'], str)
        self.assertIsInstance(state['evidence'], str)
        self.assertIsInstance(state['retry_count'], int)
        self.assertIsInstance(state['max_retries'], int)
        self.assertIsInstance(state['finished'], bool)
        self.assertIsInstance(state['success'], bool)
        self.assertIsInstance(state['agent_execution_times'], dict)
    
    def test_error_handling_in_routing(self):
        """测试路由中的错误处理"""
        state = initialize_state(self.test_db_id, self.test_query)
        
        # 测试未知智能体状态
        state['current_agent'] = 'UnknownAgent'
        result = should_continue(state)
        self.assertEqual(result, "end")
        
        # 测试错误状态
        state['current_agent'] = 'Error'
        result = should_continue(state)
        self.assertEqual(result, "end")


if __name__ == '__main__':
    unittest.main()
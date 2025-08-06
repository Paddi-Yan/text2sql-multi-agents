"""
LangGraph工作流集成测试

测试完整的Text2SQL工作流集成，包括智能体协作、错误处理和重试机制。
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import tempfile
import os
from typing import Dict, Any

from services.workflow import (
    OptimizedChatManager,
    create_text2sql_workflow,
    initialize_state,
    Text2SQLState
)


class TestWorkflowIntegration(unittest.TestCase):
    """工作流集成测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_path = os.path.join(self.temp_dir, "data")
        self.test_tables_path = os.path.join(self.temp_dir, "tables.json")
        
        # 创建测试目录
        os.makedirs(self.test_data_path, exist_ok=True)
        
        # 创建测试表结构文件
        import json
        test_tables = {
            "california_schools": {
                "tables": ["schools", "districts"],
                "schema": {
                    "schools": ["school_id", "school_name", "district_id", "sat_score"],
                    "districts": ["district_id", "district_name", "city"]
                }
            }
        }
        with open(self.test_tables_path, 'w') as f:
            json.dump(test_tables, f)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_chat_manager_initialization(self):
        """测试ChatManager初始化"""
        chat_manager = OptimizedChatManager(
            data_path=self.test_data_path,
            tables_json_path=self.test_tables_path,
            dataset_name="bird",
            max_rounds=3
        )
        
        self.assertIsNotNone(chat_manager.workflow)
        self.assertEqual(chat_manager.max_rounds, 3)
        self.assertEqual(chat_manager.dataset_name, "bird")
        self.assertIsInstance(chat_manager.stats, dict)
    
    def test_workflow_creation(self):
        """测试工作流创建"""
        workflow = create_text2sql_workflow()
        
        self.assertIsNotNone(workflow)
        # 验证工作流可以被调用（虽然可能会因为缺少实际智能体而失败）
        self.assertTrue(hasattr(workflow, 'invoke'))
    
    @patch('services.workflow.SelectorAgent')
    @patch('services.workflow.DecomposerAgent')
    @patch('services.workflow.RefinerAgent')
    def test_successful_workflow_execution(self, mock_refiner, mock_decomposer, mock_selector):
        """测试成功的工作流执行"""
        # 模拟Selector
        mock_selector_instance = Mock()
        mock_selector_instance.talk.return_value = {
            'extracted_schema': {'schools': ['school_id', 'school_name', 'sat_score']},
            'desc_str': 'Schools table with SAT scores',
            'fk_str': 'No foreign keys',
            'pruned': False,
            'chosen_db_schema_dict': {'schools': 'keep_all'}
        }
        mock_selector.return_value = mock_selector_instance
        
        # 模拟Decomposer
        mock_decomposer_instance = Mock()
        mock_decomposer_instance.talk.return_value = {
            'final_sql': 'SELECT school_name FROM schools WHERE sat_score > 1400',
            'qa_pairs': 'Q: High SAT schools A: SELECT...',
            'sub_questions': ['Find schools', 'Filter by SAT score'],
            'decomposition_strategy': 'simple'
        }
        mock_decomposer.return_value = mock_decomposer_instance
        
        # 模拟Refiner
        mock_refiner_instance = Mock()
        mock_refiner_instance.talk.return_value = {
            'execution_result': {
                'is_successful': True,
                'data': [('School A',), ('School B',)],
                'execution_time': 0.1,
                'sqlite_error': ''
            },
            'fixed': False
        }
        mock_refiner.return_value = mock_refiner_instance
        
        # 创建ChatManager并执行查询
        chat_manager = OptimizedChatManager(
            data_path=self.test_data_path,
            tables_json_path=self.test_tables_path,
            max_rounds=3
        )
        
        result = chat_manager.process_query(
            db_id="california_schools",
            query="List schools with SAT scores above 1400",
            evidence="Schools table contains SAT score information"
        )
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertIn('SELECT', result['sql'])
        self.assertIsNotNone(result['execution_result'])
        self.assertEqual(result['retry_count'], 0)
        self.assertGreater(result['processing_time'], 0)
        
        # 验证统计信息更新
        stats = chat_manager.get_stats()
        self.assertEqual(stats['total_queries'], 1)
        self.assertEqual(stats['successful_queries'], 1)
        self.assertEqual(stats['failed_queries'], 0)
    
    @patch('services.workflow.SelectorAgent')
    @patch('services.workflow.DecomposerAgent')
    @patch('services.workflow.RefinerAgent')
    def test_workflow_with_retry(self, mock_refiner, mock_decomposer, mock_selector):
        """测试带重试的工作流执行"""
        # 模拟Selector
        mock_selector_instance = Mock()
        mock_selector_instance.talk.return_value = {
            'extracted_schema': {'schools': ['school_id', 'school_name']},
            'desc_str': 'Schools table',
            'fk_str': '',
            'pruned': False,
            'chosen_db_schema_dict': {'schools': 'keep_all'}
        }
        mock_selector.return_value = mock_selector_instance
        
        # 模拟Decomposer（每次调用返回不同SQL）
        mock_decomposer_instance = Mock()
        sql_attempts = [
            'INVALID SQL SYNTAX',  # 第一次失败
            'SELECT school_name FROM schools'  # 第二次成功
        ]
        mock_decomposer_instance.talk.side_effect = [
            {
                'final_sql': sql_attempts[0],
                'qa_pairs': 'Q: Schools A: INVALID...',
                'sub_questions': ['Find schools'],
                'decomposition_strategy': 'simple'
            },
            {
                'final_sql': sql_attempts[1],
                'qa_pairs': 'Q: Schools A: SELECT...',
                'sub_questions': ['Find schools'],
                'decomposition_strategy': 'simple'
            }
        ]
        mock_decomposer.return_value = mock_decomposer_instance
        
        # 模拟Refiner（第一次失败，第二次成功）
        mock_refiner_instance = Mock()
        mock_refiner_instance.talk.side_effect = [
            {
                'execution_result': {
                    'is_successful': False,
                    'sqlite_error': 'Syntax error in SQL',
                    'execution_time': 0.1
                },
                'fixed': False
            },
            {
                'execution_result': {
                    'is_successful': True,
                    'data': [('School A',), ('School B',)],
                    'execution_time': 0.1,
                    'sqlite_error': ''
                },
                'fixed': True
            }
        ]
        mock_refiner.return_value = mock_refiner_instance
        
        # 执行查询
        chat_manager = OptimizedChatManager(max_rounds=3)
        result = chat_manager.process_query(
            db_id="test_db",
            query="List all schools",
            evidence=""
        )
        
        # 验证重试逻辑
        self.assertTrue(result['success'])
        self.assertEqual(result['retry_count'], 1)  # 一次重试
        self.assertEqual(result['sql'], sql_attempts[1])  # 使用第二次的SQL
        
        # 验证智能体调用次数
        self.assertEqual(mock_selector_instance.talk.call_count, 1)  # Selector只调用一次
        self.assertEqual(mock_decomposer_instance.talk.call_count, 2)  # Decomposer调用两次
        self.assertEqual(mock_refiner_instance.talk.call_count, 2)  # Refiner调用两次
    
    @patch('services.workflow.SelectorAgent')
    def test_workflow_failure_handling(self, mock_selector):
        """测试工作流失败处理"""
        # 模拟Selector抛出异常
        mock_selector_instance = Mock()
        mock_selector_instance.talk.side_effect = Exception("Database connection failed")
        mock_selector.return_value = mock_selector_instance
        
        chat_manager = OptimizedChatManager(max_rounds=3)
        result = chat_manager.process_query(
            db_id="test_db",
            query="Test query",
            evidence=""
        )
        
        # 验证错误处理
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIsNone(result['sql'])
        self.assertIsNone(result['execution_result'])
        
        # 验证统计信息
        stats = chat_manager.get_stats()
        self.assertEqual(stats['failed_queries'], 1)
    
    @patch('services.workflow.SelectorAgent')
    @patch('services.workflow.DecomposerAgent')
    @patch('services.workflow.RefinerAgent')
    def test_max_retry_limit(self, mock_refiner, mock_decomposer, mock_selector):
        """测试最大重试次数限制"""
        # 模拟Selector
        mock_selector_instance = Mock()
        mock_selector_instance.talk.return_value = {
            'extracted_schema': {'test': ['id']},
            'desc_str': 'Test table',
            'fk_str': '',
            'pruned': False,
            'chosen_db_schema_dict': {'test': 'keep_all'}
        }
        mock_selector.return_value = mock_selector_instance
        
        # 模拟Decomposer（总是返回无效SQL）
        mock_decomposer_instance = Mock()
        mock_decomposer_instance.talk.return_value = {
            'final_sql': 'ALWAYS INVALID SQL',
            'qa_pairs': '',
            'sub_questions': [],
            'decomposition_strategy': 'simple'
        }
        mock_decomposer.return_value = mock_decomposer_instance
        
        # 模拟Refiner（总是失败）
        mock_refiner_instance = Mock()
        mock_refiner_instance.talk.return_value = {
            'execution_result': {
                'is_successful': False,
                'sqlite_error': 'Persistent syntax error',
                'execution_time': 0.1
            },
            'fixed': False
        }
        mock_refiner.return_value = mock_refiner_instance
        
        # 执行查询（最大重试2次）
        chat_manager = OptimizedChatManager(max_rounds=2)
        result = chat_manager.process_query(
            db_id="test_db",
            query="Test query",
            evidence=""
        )
        
        # 验证达到最大重试次数后失败
        self.assertFalse(result['success'])
        self.assertEqual(result['retry_count'], 2)  # 达到最大重试次数
        self.assertIn('error', result)
        
        # 验证调用次数：Selector 1次，Decomposer 3次（初始+2次重试），Refiner 3次
        self.assertEqual(mock_selector_instance.talk.call_count, 1)
        self.assertEqual(mock_decomposer_instance.talk.call_count, 3)
        self.assertEqual(mock_refiner_instance.talk.call_count, 3)
    
    def test_health_check(self):
        """测试健康检查功能"""
        chat_manager = OptimizedChatManager()
        
        health = chat_manager.health_check()
        
        self.assertIn('status', health)
        self.assertIn('network', health)
        self.assertIn('workflow', health)
        self.assertIn('stats', health)
        self.assertIn('timestamp', health)
        
        # 工作流应该是健康的
        self.assertTrue(health['workflow'])
    
    def test_stats_tracking(self):
        """测试统计信息跟踪"""
        chat_manager = OptimizedChatManager()
        
        # 初始统计
        initial_stats = chat_manager.get_stats()
        self.assertEqual(initial_stats['total_queries'], 0)
        self.assertEqual(initial_stats['successful_queries'], 0)
        self.assertEqual(initial_stats['failed_queries'], 0)
        
        # 模拟一些查询（会失败，因为没有实际智能体）
        for i in range(3):
            chat_manager.process_query(f"test_db_{i}", f"query {i}")
        
        # 检查统计更新
        updated_stats = chat_manager.get_stats()
        self.assertEqual(updated_stats['total_queries'], 3)
        self.assertEqual(updated_stats['failed_queries'], 3)  # 都会失败
        
        # 重置统计
        chat_manager.reset_stats()
        reset_stats = chat_manager.get_stats()
        self.assertEqual(reset_stats['total_queries'], 0)
    
    def test_state_initialization_and_finalization(self):
        """测试状态初始化和完成处理"""
        # 测试状态初始化
        state = initialize_state(
            db_id="test_db",
            query="test query",
            evidence="test evidence",
            user_id="test_user",
            max_retries=5
        )
        
        # 验证初始化字段
        self.assertEqual(state['db_id'], "test_db")
        self.assertEqual(state['query'], "test query")
        self.assertEqual(state['evidence'], "test evidence")
        self.assertEqual(state['user_id'], "test_user")
        self.assertEqual(state['max_retries'], 5)
        self.assertEqual(state['current_agent'], 'Selector')
        self.assertFalse(state['finished'])
        self.assertIsNotNone(state['start_time'])
        
        # 模拟处理时间
        time.sleep(0.1)
        
        # 测试状态完成处理
        from services.workflow import finalize_state
        final_state = finalize_state(state)
        
        self.assertIsNotNone(final_state['end_time'])
        self.assertGreater(final_state['end_time'], final_state['start_time'])
    
    def test_concurrent_query_processing(self):
        """测试并发查询处理"""
        import threading
        import queue
        
        chat_manager = OptimizedChatManager()
        results_queue = queue.Queue()
        
        def process_query_thread(query_id):
            try:
                result = chat_manager.process_query(
                    db_id=f"test_db_{query_id}",
                    query=f"test query {query_id}",
                    evidence=f"test evidence {query_id}"
                )
                results_queue.put((query_id, result))
            except Exception as e:
                results_queue.put((query_id, {"error": str(e)}))
        
        # 启动多个并发查询
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_query_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10)  # 10秒超时
        
        # 收集结果
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # 验证所有查询都被处理
        self.assertEqual(len(results), 5)
        
        # 验证统计信息反映了并发查询
        stats = chat_manager.get_stats()
        self.assertEqual(stats['total_queries'], 5)


class TestWorkflowStateManagement(unittest.TestCase):
    """工作流状态管理测试"""
    
    def test_state_transitions(self):
        """测试状态转换"""
        from services.workflow import should_continue
        
        state = initialize_state("test_db", "test query", max_retries=2)
        
        # 测试正常流程转换
        transitions = [
            ('Selector', False, "decomposer"),
            ('Decomposer', False, "refiner"),
            ('Completed', True, "end"),
            ('Failed', True, "end"),
            ('Error', True, "end")
        ]
        
        for agent, finished, expected in transitions:
            state['current_agent'] = agent
            state['finished'] = finished
            result = should_continue(state)
            self.assertEqual(result, expected, 
                           f"状态转换错误: {agent} -> {result}, 期望: {expected}")
    
    def test_retry_logic(self):
        """测试重试逻辑"""
        from services.workflow import should_continue
        
        state = initialize_state("test_db", "test query", max_retries=3)
        state.update({
            'current_agent': 'Refiner',
            'is_correct': False,
            'finished': False
        })
        
        # 测试重试次数递增
        for retry_count in range(4):
            state['retry_count'] = retry_count
            result = should_continue(state)
            
            if retry_count < 3:
                self.assertEqual(result, "decomposer", 
                               f"重试 {retry_count} 应该继续到decomposer")
                # 验证重试计数递增
                self.assertEqual(state['retry_count'], retry_count + 1)
            else:
                self.assertEqual(result, "end", 
                               f"重试 {retry_count} 应该结束")
    
    def test_error_state_handling(self):
        """测试错误状态处理"""
        from services.workflow import should_continue
        
        error_states = ['Error', 'Failed', 'UnknownAgent']
        
        for error_state in error_states:
            state = initialize_state("test_db", "test query")
            state['current_agent'] = error_state
            
            result = should_continue(state)
            self.assertEqual(result, "end", 
                           f"错误状态 {error_state} 应该结束工作流")


if __name__ == '__main__':
    unittest.main()
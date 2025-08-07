"""
LangGraph Memory集成测试

测试LangGraph Memory功能在Text2SQL工作流中的集成和使用。
"""
import unittest
import time
import uuid
from unittest.mock import Mock, patch

from services.workflow import (
    OptimizedChatManager, 
    LangGraphMemoryManager,
    initialize_state
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class TestLangGraphMemoryIntegration(unittest.TestCase):
    """测试LangGraph Memory集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        
        self.chat_manager = OptimizedChatManager(
            data_path="test_data",
            dataset_name="generic",
            max_rounds=3,
            enable_memory=True,
            checkpointer=self.checkpointer,
            store=self.store
        )
    
    def test_memory_enabled_initialization(self):
        """测试启用Memory的初始化"""
        self.assertTrue(self.chat_manager.enable_memory)
        self.assertIsNotNone(self.chat_manager.checkpointer)
        self.assertIsNotNone(self.chat_manager.store)
        self.assertIsNotNone(self.chat_manager.workflow)
    
    def test_memory_disabled_initialization(self):
        """测试禁用Memory的初始化"""
        chat_manager = OptimizedChatManager(
            enable_memory=False
        )
        
        self.assertFalse(chat_manager.enable_memory)
        self.assertIsNone(chat_manager.checkpointer)
        self.assertIsNone(chat_manager.store)
    
    def test_thread_id_in_process_query(self):
        """测试process_query中的thread_id处理"""
        thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        
        with patch.object(self.chat_manager.workflow, 'invoke') as mock_invoke:
            # 模拟工作流返回
            mock_final_state = {
                'success': True,
                'final_sql': 'SELECT * FROM users',
                'messages': [HumanMessage(content="test")],
                'retry_count': 0,
                'agent_execution_times': {'selector': 1.0},
                'db_id': 'test_db',
                'query': 'Show all users'
            }
            mock_invoke.return_value = mock_final_state
            
            result = self.chat_manager.process_query(
                db_id="test_db",
                query="Show all users",
                thread_id=thread_id
            )
            
            # 验证thread_id被正确传递
            self.assertEqual(result['thread_id'], thread_id)
            self.assertTrue(result['memory_enabled'])
            self.assertEqual(result['conversation_length'], 1)
            
            # 验证config参数
            mock_invoke.assert_called_once()
            call_args = mock_invoke.call_args
            self.assertIn('config', call_args.kwargs)
            self.assertEqual(call_args.kwargs['config']['configurable']['thread_id'], thread_id)


class TestLangGraphMemoryManager(unittest.TestCase):
    """测试LangGraphMemoryManager功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.state = initialize_state("test_db", "Show all users")
    
    def test_add_system_message(self):
        """测试添加系统消息"""
        initial_count = len(self.state['messages'])
        
        LangGraphMemoryManager.add_system_message(
            self.state,
            "System initialized",
            {"type": "system_start"}
        )
        
        self.assertEqual(len(self.state['messages']), initial_count + 1)
        
        last_message = self.state['messages'][-1]
        self.assertIsInstance(last_message, SystemMessage)
        self.assertEqual(last_message.content, "System initialized")
        self.assertEqual(last_message.additional_kwargs['type'], "system_start")
    
    def test_add_agent_message(self):
        """测试添加智能体消息"""
        initial_count = len(self.state['messages'])
        
        LangGraphMemoryManager.add_agent_message(
            self.state,
            "Selector",
            "Schema selection completed",
            input_data={"db_id": "test_db"},
            output_data={"selected_tables": ["users"]}
        )
        
        self.assertEqual(len(self.state['messages']), initial_count + 1)
        
        last_message = self.state['messages'][-1]
        self.assertIsInstance(last_message, AIMessage)
        self.assertEqual(last_message.content, "Schema selection completed")
        self.assertEqual(last_message.additional_kwargs['agent'], "Selector")
        self.assertEqual(last_message.additional_kwargs['input_data']['db_id'], "test_db")
    
    def test_add_error_context_message(self):
        """测试添加错误上下文消息"""
        initial_count = len(self.state['messages'])
        
        error_info = {
            'error_message': 'no such table: users',
            'error_type': 'schema_error',
            'failed_sql': 'SELECT * FROM users',
            'attempt_number': 1
        }
        
        LangGraphMemoryManager.add_error_context_message(self.state, error_info)
        
        self.assertEqual(len(self.state['messages']), initial_count + 1)
        
        last_message = self.state['messages'][-1]
        self.assertIsInstance(last_message, SystemMessage)
        self.assertIn("no such table: users", last_message.content)
        self.assertEqual(last_message.additional_kwargs['type'], "error_context")
        self.assertEqual(last_message.additional_kwargs['error_type'], "schema_error")
    
    def test_get_conversation_context(self):
        """测试获取对话上下文"""
        # 添加多种类型的消息
        LangGraphMemoryManager.add_system_message(self.state, "System start")
        LangGraphMemoryManager.add_agent_message(self.state, "Selector", "Processing")
        LangGraphMemoryManager.add_error_context_message(self.state, {
            'error_message': 'test error',
            'error_type': 'test_error',
            'failed_sql': 'SELECT * FROM test',
            'attempt_number': 1
        })
        
        # 获取所有上下文
        context = LangGraphMemoryManager.get_conversation_context(self.state)
        
        self.assertGreater(len(context), 0)
        
        # 验证上下文结构
        for ctx in context:
            self.assertIn('role', ctx)
            self.assertIn('content', ctx)
            self.assertIn('metadata', ctx)
        
        # 获取特定智能体的上下文
        selector_context = LangGraphMemoryManager.get_conversation_context(
            self.state, agent_name="Selector"
        )
        
        self.assertEqual(len(selector_context), 1)
        self.assertEqual(selector_context[0]['metadata']['agent'], "Selector")
    
    def test_get_error_context_from_messages(self):
        """测试从消息中提取错误上下文"""
        # 添加错误消息
        error_info_1 = {
            'error_message': 'error 1',
            'error_type': 'type_1',
            'failed_sql': 'SQL 1',
            'attempt_number': 1
        }
        error_info_2 = {
            'error_message': 'error 2',
            'error_type': 'type_2',
            'failed_sql': 'SQL 2',
            'attempt_number': 2
        }
        
        LangGraphMemoryManager.add_error_context_message(self.state, error_info_1)
        LangGraphMemoryManager.add_error_context_message(self.state, error_info_2)
        
        # 提取错误上下文
        error_contexts = LangGraphMemoryManager.get_error_context_from_messages(self.state)
        
        self.assertEqual(len(error_contexts), 2)
        
        # 验证错误上下文内容
        self.assertEqual(error_contexts[0]['error_message'], 'error 1')
        self.assertEqual(error_contexts[0]['error_type'], 'type_1')
        self.assertEqual(error_contexts[1]['error_message'], 'error 2')
        self.assertEqual(error_contexts[1]['error_type'], 'type_2')
    
    def test_build_context_aware_prompt(self):
        """测试构建上下文感知提示词"""
        # 添加各种上下文信息
        self.state['retry_count'] = 1
        
        LangGraphMemoryManager.add_agent_message(
            self.state, "Decomposer", "Previous attempt",
            input_data={"query": "test"}, output_data={"sql": "SELECT 1"}
        )
        
        LangGraphMemoryManager.add_error_context_message(self.state, {
            'error_message': 'syntax error',
            'error_type': 'syntax_error',
            'failed_sql': 'SELECT * FROM',
            'attempt_number': 1
        })
        
        # 添加第二个相同类型的错误来触发重复模式检测
        LangGraphMemoryManager.add_error_context_message(self.state, {
            'error_message': 'another syntax error',
            'error_type': 'syntax_error',
            'failed_sql': 'SELECT FROM users',
            'attempt_number': 2
        })
        
        base_prompt = "Convert query to SQL:"
        enhanced_prompt = LangGraphMemoryManager.build_context_aware_prompt(
            base_prompt, self.state, "Decomposer"
        )
        
        # 验证增强提示词包含必要信息
        self.assertIn("Convert query to SQL:", enhanced_prompt)
        self.assertIn("Session Context", enhanced_prompt)
        self.assertIn("retry attempt #1", enhanced_prompt)
        self.assertIn("Decomposer Agent History", enhanced_prompt)
        self.assertIn("Error Context", enhanced_prompt)
        self.assertIn("syntax error", enhanced_prompt)
        self.assertIn("Repeated syntax_error errors", enhanced_prompt)
    
    def test_message_limit_handling(self):
        """测试消息数量限制处理"""
        # 添加大量消息
        for i in range(25):
            LangGraphMemoryManager.add_system_message(
                self.state, f"Message {i}", {"index": i}
            )
        
        # 获取有限数量的上下文
        context = LangGraphMemoryManager.get_conversation_context(
            self.state, max_messages=10
        )
        
        # 应该只返回最近的10条消息（加上初始消息）
        self.assertLessEqual(len(context), 11)  # 10 + 初始消息
        
        # 验证返回的是最新的消息
        if len(context) > 1:
            last_system_msg = [ctx for ctx in context 
                             if ctx['metadata'].get('index') is not None][-1]
            self.assertEqual(last_system_msg['metadata']['index'], 24)


class TestMemoryPersistence(unittest.TestCase):
    """测试Memory持久化功能"""
    
    def test_cross_instance_memory_sharing(self):
        """测试跨实例的Memory共享"""
        checkpointer = InMemorySaver()
        store = InMemoryStore()
        
        # 第一个实例
        chat_manager_1 = OptimizedChatManager(
            enable_memory=True,
            checkpointer=checkpointer,
            store=store
        )
        
        # 第二个实例（共享相同的checkpointer和store）
        chat_manager_2 = OptimizedChatManager(
            enable_memory=True,
            checkpointer=checkpointer,
            store=store
        )
        
        thread_id = f"shared_thread_{uuid.uuid4().hex[:8]}"
        
        # 第一个实例处理查询
        with patch.object(chat_manager_1.workflow, 'invoke') as mock_invoke_1:
            mock_final_state_1 = {
                'success': True,
                'final_sql': 'SELECT * FROM users',
                'messages': [
                    HumanMessage(content="Show users"),
                    AIMessage(content="Generated SQL")
                ],
                'retry_count': 0,
                'agent_execution_times': {},
                'db_id': 'test_db',
                'query': 'Show users'
            }
            mock_invoke_1.return_value = mock_final_state_1
            
            result_1 = chat_manager_1.process_query(
                db_id="test_db",
                query="Show users",
                thread_id=thread_id
            )
        
        # 第二个实例处理后续查询
        with patch.object(chat_manager_2.workflow, 'invoke') as mock_invoke_2:
            mock_final_state_2 = {
                'success': True,
                'final_sql': 'SELECT COUNT(*) FROM users',
                'messages': [
                    HumanMessage(content="Show users"),
                    AIMessage(content="Generated SQL"),
                    HumanMessage(content="Count users"),
                    AIMessage(content="Generated count SQL")
                ],
                'retry_count': 0,
                'agent_execution_times': {},
                'db_id': 'test_db',
                'query': 'Count users'
            }
            mock_invoke_2.return_value = mock_final_state_2
            
            result_2 = chat_manager_2.process_query(
                db_id="test_db",
                query="Count users",
                thread_id=thread_id  # 相同的thread_id
            )
        
        # 验证两个实例都能正常工作
        self.assertTrue(result_1['success'])
        self.assertTrue(result_2['success'])
        self.assertEqual(result_1['thread_id'], thread_id)
        self.assertEqual(result_2['thread_id'], thread_id)
        
        # 验证第二个实例的对话长度更长（包含了第一个实例的历史）
        self.assertGreater(result_2['conversation_length'], result_1['conversation_length'])


if __name__ == '__main__':
    unittest.main()
"""
LangGraph工作流编排系统

实现Text2SQL多智能体协作的LangGraph工作流，包括状态定义、节点函数和条件路由逻辑。
"""

from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# 导入智能体
from agents.selector_agent import SelectorAgent
from agents.decomposer_agent import DecomposerAgent  
from agents.refiner_agent import RefinerAgent

logger = logging.getLogger(__name__)


class Text2SQLState(TypedDict):
    """
    LangGraph状态定义
    
    包含Text2SQL工作流中所有必要的状态信息，支持智能体间的数据传递和状态管理。
    """
    # 输入信息
    db_id: str                          # 数据库标识符
    query: str                          # 用户自然语言查询
    evidence: str                       # 查询证据和上下文信息
    user_id: Optional[str]              # 用户标识符
    
    # 处理状态
    current_agent: str                  # 当前处理的智能体
    retry_count: int                    # 重试计数
    max_retries: int                    # 最大重试次数
    processing_stage: str               # 处理阶段标识
    
    # Selector智能体输出
    extracted_schema: Optional[Dict[str, Any]]  # 提取的数据库模式
    desc_str: str                       # 数据库描述字符串
    fk_str: str                         # 外键关系字符串
    pruned: bool                        # 是否进行了模式裁剪
    chosen_db_schema_dict: Optional[Dict[str, Any]]  # 选择的数据库模式字典
    
    # Decomposer智能体输出
    final_sql: str                      # 生成的SQL语句
    qa_pairs: str                       # 问答对信息
    sub_questions: Optional[List[str]]  # 分解的子问题列表
    decomposition_strategy: str         # 分解策略
    
    # Refiner智能体输出
    execution_result: Optional[Dict[str, Any]]  # SQL执行结果
    is_correct: bool                    # SQL是否正确
    error_message: str                  # 错误信息
    fixed: bool                         # 是否已修正
    refinement_attempts: int            # 修正尝试次数
    
    # 最终结果
    result: Optional[Dict[str, Any]]    # 最终处理结果
    finished: bool                      # 是否完成处理
    success: bool                       # 是否成功
    
    # 元数据和监控
    start_time: Optional[float]         # 开始处理时间
    end_time: Optional[float]           # 结束处理时间
    agent_execution_times: Dict[str, float]  # 各智能体执行时间
    total_tokens_used: int              # 总token使用量


def selector_node(state: Text2SQLState) -> Text2SQLState:
    """
    Selector智能体节点函数
    
    处理数据库模式理解和动态裁剪，选择查询相关的表和列。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的工作流状态
    """
    logger.info(f"执行Selector节点，处理查询: {state['query'][:50]}...")
    
    try:
        import time
        start_time = time.time()
        
        # 创建Selector智能体实例
        selector = SelectorAgent(
            agent_name="Selector",
            tables_json_path="data/tables.json"  # 从配置中获取
        )
        
        # 构建消息
        message = {
            'db_id': state['db_id'],
            'query': state['query'],
            'evidence': state['evidence'],
            'send_to': 'Selector'
        }
        
        # 调用Selector智能体
        result = selector.talk(message)
        
        # 更新状态
        execution_time = time.time() - start_time
        state.update({
            'extracted_schema': result.get('extracted_schema', {}),
            'desc_str': result.get('desc_str', ''),
            'fk_str': result.get('fk_str', ''),
            'pruned': result.get('pruned', False),
            'chosen_db_schema_dict': result.get('chosen_db_schema_dict', {}),
            'current_agent': 'Decomposer',
            'processing_stage': 'schema_selection_completed',
            'agent_execution_times': {
                **state.get('agent_execution_times', {}),
                'selector': execution_time
            }
        })
        
        logger.info(f"Selector节点执行完成，耗时: {execution_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"Selector节点执行失败: {str(e)}")
        state.update({
            'error_message': f"Selector执行失败: {str(e)}",
            'current_agent': 'Error',
            'processing_stage': 'selector_failed'
        })
    
    return state


def decomposer_node(state: Text2SQLState) -> Text2SQLState:
    """
    Decomposer智能体节点函数
    
    处理查询分解和SQL生成，将复杂查询分解为子问题并生成SQL语句。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的工作流状态
    """
    logger.info(f"执行Decomposer节点，处理查询分解和SQL生成...")
    
    try:
        import time
        start_time = time.time()
        
        # 创建Decomposer智能体实例
        decomposer = DecomposerAgent(
            agent_name="Decomposer",
            dataset_name="bird"  # 从配置中获取
        )
        
        # 构建消息
        message = {
            'db_id': state['db_id'],
            'query': state['query'],
            'evidence': state['evidence'],
            'desc_str': state['desc_str'],
            'fk_str': state['fk_str'],
            'extracted_schema': state.get('extracted_schema', {}),
            'send_to': 'Decomposer'
        }
        
        # 调用Decomposer智能体
        result = decomposer.talk(message)
        
        # 更新状态
        execution_time = time.time() - start_time
        state.update({
            'final_sql': result.get('final_sql', ''),
            'qa_pairs': result.get('qa_pairs', ''),
            'sub_questions': result.get('sub_questions', []),
            'decomposition_strategy': result.get('decomposition_strategy', 'simple'),
            'current_agent': 'Refiner',
            'processing_stage': 'sql_generation_completed',
            'agent_execution_times': {
                **state.get('agent_execution_times', {}),
                'decomposer': execution_time
            }
        })
        
        logger.info(f"Decomposer节点执行完成，耗时: {execution_time:.2f}秒")
        logger.info(f"生成的SQL: {result.get('final_sql', '')[:100]}...")
        
    except Exception as e:
        logger.error(f"Decomposer节点执行失败: {str(e)}")
        state.update({
            'error_message': f"Decomposer执行失败: {str(e)}",
            'current_agent': 'Error',
            'processing_stage': 'decomposer_failed'
        })
    
    return state


def refiner_node(state: Text2SQLState) -> Text2SQLState:
    """
    Refiner智能体节点函数
    
    处理SQL执行验证和错误修正，确保生成的SQL正确可执行。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的工作流状态
    """
    logger.info(f"执行Refiner节点，进行SQL验证和修正...")
    
    try:
        import time
        start_time = time.time()
        
        # 创建Refiner智能体实例
        refiner = RefinerAgent(
            data_path="data",  # 从配置中获取
            dataset_name="bird"  # 从配置中获取
        )
        
        # 构建消息
        message = {
            'db_id': state['db_id'],
            'query': state['query'],
            'final_sql': state['final_sql'],
            'desc_str': state['desc_str'],
            'fk_str': state['fk_str'],
            'send_to': 'Refiner'
        }
        
        # 调用Refiner智能体
        result = refiner.talk(message)
        
        # 更新状态
        execution_time = time.time() - start_time
        execution_result = result.get('execution_result', {})
        is_successful = execution_result.get('is_successful', False)
        
        state.update({
            'execution_result': execution_result,
            'is_correct': is_successful,
            'error_message': execution_result.get('sqlite_error', ''),
            'fixed': result.get('fixed', False),
            'refinement_attempts': state.get('refinement_attempts', 0) + 1,
            'processing_stage': 'sql_validation_completed',
            'agent_execution_times': {
                **state.get('agent_execution_times', {}),
                'refiner': execution_time
            }
        })
        
        # 如果SQL执行成功，标记为完成
        if is_successful:
            state.update({
                'finished': True,
                'success': True,
                'current_agent': 'Completed',
                'result': {
                    'sql': state['final_sql'],
                    'execution_result': execution_result,
                    'processing_time': sum(state['agent_execution_times'].values())
                }
            })
            logger.info(f"Refiner节点执行成功，SQL验证通过")
        else:
            # 如果需要重试且未超过最大重试次数
            if state['retry_count'] < state['max_retries']:
                state.update({
                    'current_agent': 'Decomposer',
                    'processing_stage': 'retry_sql_generation'
                })
                logger.warning(f"SQL执行失败，准备重试 ({state['retry_count'] + 1}/{state['max_retries']})")
            else:
                state.update({
                    'finished': True,
                    'success': False,
                    'current_agent': 'Failed',
                    'result': {
                        'error': state['error_message'],
                        'failed_sql': state['final_sql'],
                        'processing_time': sum(state['agent_execution_times'].values())
                    }
                })
                logger.error(f"SQL执行失败，已达到最大重试次数")
        
        logger.info(f"Refiner节点执行完成，耗时: {execution_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"Refiner节点执行失败: {str(e)}")
        state.update({
            'error_message': f"Refiner执行失败: {str(e)}",
            'current_agent': 'Error',
            'processing_stage': 'refiner_failed',
            'finished': True,
            'success': False
        })
    
    return state


def should_continue(state: Text2SQLState) -> str:
    """
    条件路由逻辑函数
    
    根据当前状态决定工作流的下一步执行路径，支持智能重试和错误处理。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个节点的名称或结束标识
    """
    logger.debug(f"路由决策: 当前智能体={state['current_agent']}, 完成状态={state['finished']}")
    
    # 如果已完成或出错，结束工作流
    if state['finished'] or state['current_agent'] in ['Completed', 'Failed', 'Error']:
        logger.info(f"工作流结束: {state['current_agent']}")
        return "end"
    
    # 根据当前智能体决定下一步
    if state['current_agent'] == 'Selector':
        return "decomposer"
    elif state['current_agent'] == 'Decomposer':
        return "refiner"
    elif state['current_agent'] == 'Refiner':
        # Refiner执行后的路由逻辑在refiner_node中已处理
        if not state['is_correct'] and state['retry_count'] < state['max_retries']:
            # 增加重试计数
            state['retry_count'] += 1
            logger.info(f"准备重试，重试次数: {state['retry_count']}/{state['max_retries']}")
            return "decomposer"
        else:
            return "end"
    
    # 默认结束
    logger.warning(f"未知的智能体状态: {state['current_agent']}")
    return "end"


def initialize_state(db_id: str, query: str, evidence: str = "", 
                    user_id: Optional[str] = None, max_retries: int = 3) -> Text2SQLState:
    """
    初始化工作流状态
    
    Args:
        db_id: 数据库标识符
        query: 用户查询
        evidence: 查询证据
        user_id: 用户标识符
        max_retries: 最大重试次数
        
    Returns:
        初始化的工作流状态
    """
    import time
    
    return Text2SQLState(
        # 输入信息
        db_id=db_id,
        query=query,
        evidence=evidence,
        user_id=user_id,
        
        # 处理状态
        current_agent='Selector',
        retry_count=0,
        max_retries=max_retries,
        processing_stage='initialized',
        
        # 智能体输出（初始化为空值）
        extracted_schema=None,
        desc_str='',
        fk_str='',
        pruned=False,
        chosen_db_schema_dict=None,
        
        final_sql='',
        qa_pairs='',
        sub_questions=None,
        decomposition_strategy='',
        
        execution_result=None,
        is_correct=False,
        error_message='',
        fixed=False,
        refinement_attempts=0,
        
        # 最终结果
        result=None,
        finished=False,
        success=False,
        
        # 元数据
        start_time=time.time(),
        end_time=None,
        agent_execution_times={},
        total_tokens_used=0
    )


def finalize_state(state: Text2SQLState) -> Text2SQLState:
    """
    完成工作流状态处理
    
    Args:
        state: 当前工作流状态
        
    Returns:
        最终处理完成的状态
    """
    import time
    
    if not state.get('end_time'):
        state['end_time'] = time.time()
    
    # 计算总处理时间
    if state.get('start_time') and state.get('end_time'):
        total_time = state['end_time'] - state['start_time']
        if state.get('result'):
            state['result']['total_processing_time'] = total_time
    
    logger.info(f"工作流完成: 成功={state['success']}, 总耗时={total_time:.2f}秒")
    
    return state
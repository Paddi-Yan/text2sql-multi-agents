"""
LangGraph工作流系统使用示例

演示如何使用Text2SQL工作流的状态定义、节点函数和条件路由逻辑，
以及新的OptimizedChatManager的使用方法。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.workflow import (
    Text2SQLState,
    selector_node,
    decomposer_node,
    refiner_node,
    should_continue,
    initialize_state,
    finalize_state,
    create_text2sql_workflow,
    OptimizedChatManager
)
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def simulate_workflow_execution():
    """模拟完整的工作流执行过程"""
    logger.info("开始模拟Text2SQL工作流执行")
    
    # 1. 初始化状态
    state = initialize_state(
        db_id="california_schools",
        query="List all schools in Los Angeles with SAT scores above 1400",
        evidence="The database contains school information including location and test scores",
        user_id="demo_user",
        max_retries=3
    )
    
    logger.info(f"初始状态: {state['current_agent']}, 查询: {state['query']}")
    
    # 2. 模拟工作流执行循环
    max_iterations = 10  # 防止无限循环
    iteration = 0
    
    while not state['finished'] and iteration < max_iterations:
        iteration += 1
        logger.info(f"=== 迭代 {iteration}: 当前智能体 {state['current_agent']} ===")
        
        # 根据当前智能体执行相应节点
        if state['current_agent'] == 'Selector':
            try:
                state = selector_node(state)
                logger.info(f"Selector完成: 裁剪={state['pruned']}, 下一步={state['current_agent']}")
            except Exception as e:
                logger.error(f"Selector执行失败: {e}")
                break
                
        elif state['current_agent'] == 'Decomposer':
            try:
                state = decomposer_node(state)
                logger.info(f"Decomposer完成: SQL长度={len(state['final_sql'])}, 下一步={state['current_agent']}")
            except Exception as e:
                logger.error(f"Decomposer执行失败: {e}")
                break
                
        elif state['current_agent'] == 'Refiner':
            try:
                state = refiner_node(state)
                logger.info(f"Refiner完成: 成功={state['is_correct']}, 完成={state['finished']}")
            except Exception as e:
                logger.error(f"Refiner执行失败: {e}")
                break
        
        # 检查是否需要继续
        next_step = should_continue(state)
        if next_step == "end":
            logger.info("工作流路由决定结束")
            break
        elif next_step == "decomposer" and state['current_agent'] != 'Decomposer':
            state['current_agent'] = 'Decomposer'
            logger.info("路由到Decomposer进行重试")
    
    # 3. 完成状态处理
    final_state = finalize_state(state)
    
    # 4. 输出结果
    logger.info("=== 工作流执行完成 ===")
    logger.info(f"成功: {final_state['success']}")
    logger.info(f"总迭代次数: {iteration}")
    logger.info(f"重试次数: {final_state['retry_count']}")
    
    if final_state.get('result'):
        result = final_state['result']
        logger.info(f"最终SQL: {result.get('sql', 'N/A')}")
        logger.info(f"处理时间: {result.get('total_processing_time', 0):.2f}秒")
    
    if final_state.get('agent_execution_times'):
        logger.info("各智能体执行时间:")
        for agent, time_spent in final_state['agent_execution_times'].items():
            logger.info(f"  {agent}: {time_spent:.2f}秒")
    
    return final_state


def demonstrate_state_structure():
    """演示状态结构和字段"""
    logger.info("=== 演示状态结构 ===")
    
    state = initialize_state(
        db_id="demo_db",
        query="Show me the data",
        evidence="Some evidence"
    )
    
    logger.info("状态字段结构:")
    for key, value in state.items():
        logger.info(f"  {key}: {type(value).__name__} = {value}")


def demonstrate_routing_logic():
    """演示条件路由逻辑"""
    logger.info("=== 演示路由逻辑 ===")
    
    state = initialize_state("test_db", "test query")
    
    # 测试各种路由场景
    scenarios = [
        ("Selector", "decomposer"),
        ("Decomposer", "refiner"),
        ("Completed", "end"),
        ("Error", "end"),
        ("Failed", "end")
    ]
    
    for current_agent, expected_route in scenarios:
        state['current_agent'] = current_agent
        if current_agent in ['Completed', 'Error', 'Failed']:
            state['finished'] = True
        else:
            state['finished'] = False
            
        route = should_continue(state)
        logger.info(f"{current_agent} -> {route} (期望: {expected_route})")
        assert route == expected_route, f"路由错误: {current_agent} -> {route}, 期望: {expected_route}"
    
    # 测试重试逻辑
    logger.info("测试重试逻辑:")
    state = initialize_state("test_db", "test query", max_retries=2)
    state.update({
        'current_agent': 'Refiner',
        'is_correct': False,
        'finished': False
    })
    
    for retry_count in range(3):
        state['retry_count'] = retry_count
        route = should_continue(state)
        expected = "decomposer" if retry_count < 2 else "end"
        logger.info(f"重试 {retry_count}/2 -> {route} (期望: {expected})")


def demonstrate_workflow_creation():
    """演示工作流创建"""
    logger.info("=== 演示工作流创建 ===")
    
    try:
        workflow = create_text2sql_workflow()
        logger.info(f"工作流创建成功: {type(workflow)}")
        logger.info("工作流节点和边已配置完成")
        return workflow
    except Exception as e:
        logger.error(f"工作流创建失败: {e}")
        return None


def demonstrate_chat_manager():
    """演示OptimizedChatManager的使用"""
    logger.info("=== 演示OptimizedChatManager ===")
    
    try:
        # 创建ChatManager实例
        chat_manager = OptimizedChatManager(
            data_path="data",
            tables_json_path="data/tables.json",
            dataset_name="bird",
            max_rounds=3
        )
        
        logger.info("ChatManager创建成功")
        
        # 健康检查
        health = chat_manager.health_check()
        logger.info(f"健康检查结果: {health['status']}")
        
        # 演示查询处理（注意：需要实际的智能体实现才能完整运行）
        logger.info("演示查询处理接口（模拟）")
        
        sample_queries = [
            {
                "db_id": "california_schools",
                "query": "List all schools in Los Angeles with SAT scores above 1400",
                "evidence": "The database contains school information including location and test scores"
            },
            {
                "db_id": "company_db",
                "query": "Show me the top 5 employees by salary",
                "evidence": "Employee table contains salary information"
            }
        ]
        
        for i, query_data in enumerate(sample_queries, 1):
            logger.info(f"示例查询 {i}: {query_data['query'][:30]}...")
            
            # 注意：实际调用需要智能体实现
            # result = chat_manager.process_query(**query_data)
            # logger.info(f"处理结果: 成功={result['success']}")
        
        # 显示统计信息
        stats = chat_manager.get_stats()
        logger.info(f"当前统计: {stats}")
        
        return chat_manager
        
    except Exception as e:
        logger.error(f"ChatManager演示失败: {e}")
        return None


def demonstrate_integration_workflow():
    """演示完整的集成工作流"""
    logger.info("=== 演示完整集成工作流 ===")
    
    try:
        # 1. 创建工作流
        workflow = create_text2sql_workflow()
        if not workflow:
            logger.error("工作流创建失败")
            return
        
        # 2. 创建ChatManager
        chat_manager = OptimizedChatManager()
        if not chat_manager:
            logger.error("ChatManager创建失败")
            return
        
        # 3. 演示状态监控
        logger.info("工作流状态监控演示:")
        initial_state = initialize_state(
            db_id="demo_db",
            query="SELECT * FROM users WHERE age > 25",
            evidence="User table contains age information"
        )
        
        logger.info(f"初始状态: {initial_state['current_agent']}")
        logger.info(f"最大重试次数: {initial_state['max_retries']}")
        logger.info(f"处理阶段: {initial_state['processing_stage']}")
        
        # 4. 演示错误处理
        logger.info("错误处理机制演示:")
        error_state = initial_state.copy()
        error_state.update({
            'current_agent': 'Error',
            'error_message': '模拟错误',
            'finished': True,
            'success': False
        })
        
        route = should_continue(error_state)
        logger.info(f"错误状态路由: {route}")
        
        logger.info("集成工作流演示完成")
        
    except Exception as e:
        logger.error(f"集成工作流演示失败: {e}")


def main():
    """主函数"""
    logger.info("LangGraph工作流系统完整示例")
    
    try:
        # 1. 演示状态结构
        demonstrate_state_structure()
        
        print("\n" + "="*50 + "\n")
        
        # 2. 演示路由逻辑
        demonstrate_routing_logic()
        
        print("\n" + "="*50 + "\n")
        
        # 3. 演示工作流创建
        demonstrate_workflow_creation()
        
        print("\n" + "="*50 + "\n")
        
        # 4. 演示ChatManager
        demonstrate_chat_manager()
        
        print("\n" + "="*50 + "\n")
        
        # 5. 演示完整集成
        demonstrate_integration_workflow()
        
        print("\n" + "="*50 + "\n")
        
        logger.info("注意: 完整功能需要实际的智能体实现")
        logger.info("当前演示了工作流框架和ChatManager的结构")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
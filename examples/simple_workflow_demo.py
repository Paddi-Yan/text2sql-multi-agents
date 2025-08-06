"""
简单的工作流演示

演示OptimizedChatManager的基本使用，不依赖实际的智能体实现。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.workflow import (
    OptimizedChatManager,
    create_text2sql_workflow,
    initialize_state,
    finalize_state
)
import logging
import tempfile
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_environment():
    """创建测试环境"""
    temp_dir = tempfile.mkdtemp()
    data_path = os.path.join(temp_dir, "data")
    tables_path = os.path.join(temp_dir, "tables.json")
    
    # 创建数据目录
    os.makedirs(data_path, exist_ok=True)
    
    # 创建测试表结构
    test_tables = {
        "california_schools": {
            "tables": ["schools", "districts"],
            "schema": {
                "schools": ["school_id", "school_name", "district_id", "sat_score"],
                "districts": ["district_id", "district_name", "city"]
            }
        }
    }
    
    with open(tables_path, 'w') as f:
        json.dump(test_tables, f)
    
    return temp_dir, data_path, tables_path


def demo_workflow_creation():
    """演示工作流创建"""
    logger.info("=== 演示工作流创建 ===")
    
    try:
        workflow = create_text2sql_workflow()
        logger.info(f"工作流创建成功: {type(workflow)}")
        logger.info("工作流包含节点: selector, decomposer, refiner")
        return workflow
    except Exception as e:
        logger.error(f"工作流创建失败: {e}")
        return None


def demo_state_management():
    """演示状态管理"""
    logger.info("=== 演示状态管理 ===")
    
    # 初始化状态
    state = initialize_state(
        db_id="california_schools",
        query="List schools with SAT scores above 1400",
        evidence="Schools table contains SAT score information",
        user_id="demo_user",
        max_retries=3
    )
    
    logger.info(f"初始状态创建: 当前智能体={state['current_agent']}")
    logger.info(f"查询: {state['query']}")
    logger.info(f"最大重试次数: {state['max_retries']}")
    
    # 模拟状态更新
    import time
    time.sleep(0.1)
    
    # 完成状态
    final_state = finalize_state(state)
    logger.info(f"状态完成处理: 开始时间={final_state['start_time']}, 结束时间={final_state['end_time']}")
    
    return final_state


def demo_chat_manager():
    """演示ChatManager功能"""
    logger.info("=== 演示ChatManager功能 ===")
    
    try:
        # 创建测试环境
        temp_dir, data_path, tables_path = create_test_environment()
        
        # 创建ChatManager
        chat_manager = OptimizedChatManager(
            data_path=data_path,
            tables_json_path=tables_path,
            dataset_name="bird",
            max_rounds=3
        )
        
        logger.info("ChatManager创建成功")
        
        # 健康检查
        health = chat_manager.health_check()
        logger.info(f"健康检查: 状态={health['status']}, 工作流={health['workflow']}")
        
        # 获取初始统计
        stats = chat_manager.get_stats()
        logger.info(f"初始统计: 总查询={stats['total_queries']}, 成功={stats['successful_queries']}")
        
        # 演示查询处理（会失败，因为没有实际智能体）
        logger.info("演示查询处理（预期会失败，因为没有实际智能体实现）")
        
        result = chat_manager.process_query(
            db_id="california_schools",
            query="List schools with SAT scores above 1400",
            evidence="Schools table contains SAT score information"
        )
        
        logger.info(f"查询结果: 成功={result['success']}")
        if not result['success']:
            logger.info(f"失败原因: {result.get('error', 'Unknown error')}")
        
        # 更新后的统计
        updated_stats = chat_manager.get_stats()
        logger.info(f"更新统计: 总查询={updated_stats['total_queries']}, 失败={updated_stats['failed_queries']}")
        
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return chat_manager
        
    except Exception as e:
        logger.error(f"ChatManager演示失败: {e}")
        return None


def demo_error_handling():
    """演示错误处理"""
    logger.info("=== 演示错误处理 ===")
    
    from services.workflow import should_continue
    
    # 测试各种错误状态
    error_scenarios = [
        {"current_agent": "Error", "finished": True, "expected": "end"},
        {"current_agent": "Failed", "finished": True, "expected": "end"},
        {"current_agent": "UnknownAgent", "finished": False, "expected": "end"}
    ]
    
    for scenario in error_scenarios:
        state = initialize_state("test_db", "test query")
        state.update(scenario)
        
        route = should_continue(state)
        logger.info(f"错误场景: {scenario['current_agent']} -> {route}")
        assert route == scenario["expected"], f"路由错误: 期望{scenario['expected']}, 实际{route}"
    
    logger.info("错误处理测试通过")


def demo_retry_logic():
    """演示重试逻辑"""
    logger.info("=== 演示重试逻辑 ===")
    
    from services.workflow import should_continue
    
    # 创建重试场景
    state = initialize_state("test_db", "test query", max_retries=3)
    state.update({
        'current_agent': 'Refiner',
        'is_correct': False,
        'finished': False
    })
    
    # 测试重试逻辑
    for retry_count in range(5):
        state['retry_count'] = retry_count
        route = should_continue(state)
        
        if retry_count < 3:
            expected = "decomposer"
            logger.info(f"重试 {retry_count}/3: {route} (继续重试)")
        else:
            expected = "end"
            logger.info(f"重试 {retry_count}/3: {route} (达到最大重试次数)")
        
        assert route == expected, f"重试逻辑错误: 期望{expected}, 实际{route}"
    
    logger.info("重试逻辑测试通过")


def main():
    """主演示函数"""
    logger.info("开始Text2SQL工作流系统演示")
    
    try:
        # 1. 工作流创建演示
        workflow = demo_workflow_creation()
        if not workflow:
            logger.error("工作流创建失败，停止演示")
            return
        
        print("\n" + "="*60 + "\n")
        
        # 2. 状态管理演示
        demo_state_management()
        
        print("\n" + "="*60 + "\n")
        
        # 3. ChatManager演示
        demo_chat_manager()
        
        print("\n" + "="*60 + "\n")
        
        # 4. 错误处理演示
        demo_error_handling()
        
        print("\n" + "="*60 + "\n")
        
        # 5. 重试逻辑演示
        demo_retry_logic()
        
        print("\n" + "="*60 + "\n")
        
        logger.info("演示完成！")
        logger.info("注意: 完整功能需要实际的智能体实现（Selector、Decomposer、Refiner）")
        logger.info("当前演示展示了工作流框架的核心功能和架构")
        
    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
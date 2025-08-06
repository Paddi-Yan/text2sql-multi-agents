"""
简化的工作流测试

使用正确的配置测试工作流系统。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.workflow import OptimizedChatManager
import logging
import tempfile
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_workflow_with_existing_data():
    """使用现有数据测试工作流"""
    logger.info("=== 使用现有数据测试工作流 ===")
    
    try:
        # 使用项目中现有的数据配置
        chat_manager = OptimizedChatManager(
            data_path="data",
            tables_json_path="data/tables.json",
            dataset_name="bird",
            max_rounds=3
        )
        
        # 测试简单查询
        result = chat_manager.process_query(
            db_id="california_schools",
            query="List all schools",
            evidence="Show me information about schools"
        )
        
        # 输出结果
        logger.info(f"查询结果:")
        logger.info(f"  成功: {result['success']}")
        logger.info(f"  SQL: {result.get('sql', 'N/A')}")
        logger.info(f"  处理时间: {result.get('processing_time', 0):.2f}秒")
        logger.info(f"  重试次数: {result.get('retry_count', 0)}")
        
        if result['success']:
            exec_result = result.get('execution_result', {})
            if exec_result.get('data'):
                logger.info(f"  查询结果行数: {len(exec_result['data'])}")
                logger.info(f"  前3行数据: {exec_result['data'][:3]}")
            
            # 显示智能体执行时间
            agent_times = result.get('agent_execution_times', {})
            if agent_times:
                logger.info("  智能体执行时间:")
                for agent, time_spent in agent_times.items():
                    logger.info(f"    {agent}: {time_spent:.2f}秒")
        else:
            logger.error(f"  错误: {result.get('error', 'Unknown error')}")
            logger.error(f"  失败的SQL: {result.get('failed_sql', 'N/A')}")
            logger.error(f"  处理阶段: {result.get('processing_stage', 'N/A')}")
        
        # 获取统计信息
        stats = chat_manager.get_stats()
        logger.info(f"统计信息:")
        logger.info(f"  总查询数: {stats['total_queries']}")
        logger.info(f"  成功查询数: {stats['successful_queries']}")
        logger.info(f"  失败查询数: {stats['failed_queries']}")
        
        # 健康检查
        health = chat_manager.health_check()
        logger.info(f"系统健康状态: {health['status']}")
        
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_multiple_queries():
    """测试多个查询"""
    logger.info("=== 测试多个查询 ===")
    
    try:
        chat_manager = OptimizedChatManager(
            data_path="data",
            tables_json_path="data/tables.json",
            dataset_name="bird",
            max_rounds=2
        )
        
        queries = [
            ("Show me all schools", "Simple query"),
            ("List schools with high SAT scores", "Filter query"),
            ("What is the average enrollment?", "Aggregation query")
        ]
        
        results = []
        for i, (query, description) in enumerate(queries, 1):
            logger.info(f"执行查询 {i}: {query}")
            
            result = chat_manager.process_query(
                db_id="california_schools",
                query=query,
                evidence=description
            )
            
            results.append(result)
            logger.info(f"  结果: {'成功' if result['success'] else '失败'}")
            if not result['success']:
                logger.info(f"  错误: {result.get('error', 'Unknown')}")
        
        # 最终统计
        stats = chat_manager.get_stats()
        logger.info(f"批量测试统计:")
        logger.info(f"  总查询数: {stats['total_queries']}")
        logger.info(f"  成功查询数: {stats['successful_queries']}")
        logger.info(f"  成功率: {stats['successful_queries']/stats['total_queries']*100:.1f}%")
        
        return results
        
    except Exception as e:
        logger.error(f"批量测试失败: {str(e)}")
        return []


def main():
    """主测试函数"""
    logger.info("开始简化的工作流测试")
    
    try:
        # 1. 单个查询测试
        logger.info("\n" + "="*50)
        single_result = test_workflow_with_existing_data()
        
        # 2. 多个查询测试
        logger.info("\n" + "="*50)
        batch_results = test_multiple_queries()
        
        # 总结
        logger.info("\n" + "="*50)
        logger.info("测试总结:")
        
        single_success = single_result.get('success', False)
        batch_success = len([r for r in batch_results if r.get('success', False)])
        total_batch = len(batch_results)
        
        logger.info(f"  单个查询测试: {'✅ 通过' if single_success else '❌ 失败'}")
        logger.info(f"  批量查询测试: {batch_success}/{total_batch} 成功")
        
        if single_success or batch_success > 0:
            logger.info("🎉 工作流系统基本功能正常！")
        else:
            logger.warning("⚠️ 工作流系统需要进一步调试")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
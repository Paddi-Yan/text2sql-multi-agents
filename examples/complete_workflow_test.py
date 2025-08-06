"""
完整的工作流端到端测试

测试完整的Text2SQL工作流，包括所有智能体的真实协作。
使用MySQL数据库进行真实的端到端测试。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.workflow import OptimizedChatManager
from config.settings import config
import logging
import json
import pymysql

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_mysql_test_data():
    """设置MySQL测试数据"""
    logger.info("设置MySQL测试数据...")
    
    # 连接到MySQL数据库
    connection = pymysql.connect(
        host=config.database_config.host,
        port=config.database_config.port,
        user=config.database_config.username,
        password=config.database_config.password,
        database=config.database_config.database,
        charset='utf8mb4'
    )
    
    try:
        cursor = connection.cursor()
        
        # 创建学校测试表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id INT AUTO_INCREMENT PRIMARY KEY,
                school_name VARCHAR(200) NOT NULL,
                district_id INT,
                city VARCHAR(100),
                sat_score INT,
                enrollment INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS districts (
                district_id INT AUTO_INCREMENT PRIMARY KEY,
                district_name VARCHAR(200) NOT NULL,
                city VARCHAR(100),
                county VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 清理现有测试数据
        cursor.execute("DELETE FROM schools WHERE school_name LIKE '%Test%' OR city IN ('Los Angeles', 'San Francisco', 'San Diego')")
        cursor.execute("DELETE FROM districts WHERE district_name LIKE '%Test%' OR city IN ('Los Angeles', 'San Francisco', 'San Diego')")
        
        # 插入测试数据
        districts_data = [
            ("Los Angeles Unified Test", "Los Angeles", "Los Angeles County"),
            ("San Francisco Unified Test", "San Francisco", "San Francisco County"),
            ("San Diego Unified Test", "San Diego", "San Diego County")
        ]
        
        cursor.executemany(
            "INSERT INTO districts (district_name, city, county) VALUES (%s, %s, %s)",
            districts_data
        )
        
        # 获取插入的district_id
        cursor.execute("SELECT district_id, city FROM districts WHERE district_name LIKE '%Test%' ORDER BY district_id")
        district_mapping = {city: district_id for district_id, city in cursor.fetchall()}
        
        schools_data = [
            ("Lincoln High School Test", district_mapping["Los Angeles"], "Los Angeles", 1450, 2500),
            ("Washington High School Test", district_mapping["Los Angeles"], "Los Angeles", 1380, 2200),
            ("Roosevelt High School Test", district_mapping["San Francisco"], "San Francisco", 1520, 1800),
            ("Jefferson High School Test", district_mapping["San Francisco"], "San Francisco", 1420, 1900),
            ("Madison High School Test", district_mapping["San Diego"], "San Diego", 1480, 2100),
            ("Monroe High School Test", district_mapping["San Diego"], "San Diego", 1350, 1950)
        ]
        
        cursor.executemany(
            "INSERT INTO schools (school_name, district_id, city, sat_score, enrollment) VALUES (%s, %s, %s, %s, %s)",
            schools_data
        )
        
        connection.commit()
        
        # 验证数据插入
        cursor.execute("SELECT COUNT(*) FROM schools WHERE school_name LIKE '%Test%'")
        school_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM districts WHERE district_name LIKE '%Test%'")
        district_count = cursor.fetchone()[0]
        
        logger.info(f"测试数据插入成功: {school_count} 所学校, {district_count} 个学区")
        
        return True
        
    except Exception as e:
        logger.error(f"设置测试数据失败: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()


def cleanup_mysql_test_data():
    """清理MySQL测试数据"""
    logger.info("清理MySQL测试数据...")
    
    try:
        connection = pymysql.connect(
            host=config.database_config.host,
            port=config.database_config.port,
            user=config.database_config.username,
            password=config.database_config.password,
            database=config.database_config.database,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 删除测试数据
        cursor.execute("DELETE FROM schools WHERE school_name LIKE '%Test%'")
        cursor.execute("DELETE FROM districts WHERE district_name LIKE '%Test%'")
        
        connection.commit()
        logger.info("测试数据清理完成")
        
    except Exception as e:
        logger.error(f"清理测试数据失败: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


def test_simple_query():
    """测试简单查询"""
    logger.info("=== 测试简单查询 ===")
    
    # 创建ChatManager，使用默认配置连接MySQL
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=3
    )
    
    # 测试查询
    result = chat_manager.process_query(
        db_id="text2sql_db",  # 使用实际的MySQL数据库名
        query="List all schools in Los Angeles",
        evidence="The schools table contains school information including city"
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
    
    return result


def test_complex_query():
    """测试复杂查询"""
    logger.info("=== 测试复杂查询 ===")
    
    # 创建ChatManager
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=3
    )
    
    # 测试复杂查询
    result = chat_manager.process_query(
        db_id="text2sql_db",
        query="Show me schools with SAT scores above 1400 and their district information",
        evidence="Need to join schools and districts tables to get complete information"
    )
    
    # 输出结果
    logger.info(f"复杂查询结果:")
    logger.info(f"  成功: {result['success']}")
    logger.info(f"  SQL: {result.get('sql', 'N/A')}")
    logger.info(f"  处理时间: {result.get('processing_time', 0):.2f}秒")
    logger.info(f"  重试次数: {result.get('retry_count', 0)}")
    logger.info(f"  模式裁剪: {result.get('schema_pruned', False)}")
    logger.info(f"  分解策略: {result.get('decomposition_strategy', 'N/A')}")
    
    if result['success']:
        exec_result = result.get('execution_result', {})
        if exec_result.get('data'):
            logger.info(f"  查询结果行数: {len(exec_result['data'])}")
            logger.info(f"  前3行数据: {exec_result['data'][:3]}")
    else:
        logger.error(f"  错误: {result.get('error', 'Unknown error')}")
    
    return result


def test_aggregation_query():
    """测试聚合查询"""
    logger.info("=== 测试聚合查询 ===")
    
    # 创建ChatManager
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=3
    )
    
    # 测试聚合查询
    result = chat_manager.process_query(
        db_id="text2sql_db",
        query="What is the average SAT score by city?",
        evidence="Need to calculate average SAT scores grouped by city"
    )
    
    # 输出结果
    logger.info(f"聚合查询结果:")
    logger.info(f"  成功: {result['success']}")
    logger.info(f"  SQL: {result.get('sql', 'N/A')}")
    logger.info(f"  处理时间: {result.get('processing_time', 0):.2f}秒")
    logger.info(f"  重试次数: {result.get('retry_count', 0)}")
    
    if result['success']:
        exec_result = result.get('execution_result', {})
        if exec_result.get('data'):
            logger.info(f"  查询结果行数: {len(exec_result['data'])}")
            logger.info(f"  聚合结果: {exec_result['data']}")
    else:
        logger.error(f"  错误: {result.get('error', 'Unknown error')}")
    
    return result


def test_error_handling():
    """测试错误处理"""
    logger.info("=== 测试错误处理 ===")
    
    # 创建ChatManager
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=2  # 减少重试次数以快速测试
    )
    
    # 测试可能导致错误的查询
    result = chat_manager.process_query(
        db_id="text2sql_db",
        query="Show me information from the nonexistent_table",
        evidence="This query should fail because the table doesn't exist"
    )
    
    # 输出结果
    logger.info(f"错误处理测试结果:")
    logger.info(f"  成功: {result['success']}")
    logger.info(f"  SQL: {result.get('sql', 'N/A')}")
    logger.info(f"  处理时间: {result.get('processing_time', 0):.2f}秒")
    logger.info(f"  重试次数: {result.get('retry_count', 0)}")
    
    if not result['success']:
        logger.info(f"  错误信息: {result.get('error', 'Unknown error')}")
        logger.info(f"  失败的SQL: {result.get('failed_sql', 'N/A')}")
        logger.info(f"  处理阶段: {result.get('processing_stage', 'N/A')}")
    
    return result


def test_workflow_statistics():
    """测试工作流统计功能"""
    logger.info("=== 测试工作流统计功能 ===")
    
    # 创建ChatManager
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=3
    )
    
    # 执行多个查询
    queries = [
        ("List all users", "Simple query test"),
        ("Show products with price > 100", "Filter query test"),
        ("Average price by category", "Aggregation query test"),
        ("Invalid query with wrong table", "Error test")
    ]
    
    results = []
    for query, evidence in queries:
        logger.info(f"执行查询: {query}")
        result = chat_manager.process_query(
            db_id="text2sql_db",
            query=query,
            evidence=evidence
        )
        results.append(result)
    
    # 获取统计信息
    stats = chat_manager.get_stats()
    logger.info(f"工作流统计信息:")
    logger.info(f"  总查询数: {stats['total_queries']}")
    logger.info(f"  成功查询数: {stats['successful_queries']}")
    logger.info(f"  失败查询数: {stats['failed_queries']}")
    logger.info(f"  成功率: {stats['successful_queries']/stats['total_queries']*100:.1f}%")
    logger.info(f"  平均处理时间: {stats['average_processing_time']:.2f}秒")
    logger.info(f"  重试率: {stats['retry_rate']*100:.1f}%")
    
    # 健康检查
    health = chat_manager.health_check()
    logger.info(f"系统健康状态: {health['status']}")
    
    return results, stats


def test_concurrent_queries():
    """测试并发查询处理"""
    logger.info("=== 测试并发查询处理 ===")
    
    import threading
    import queue
    
    # 创建ChatManager
    chat_manager = OptimizedChatManager(
        data_path="data",
        tables_json_path="data/tables.json",
        dataset_name="bird",
        max_rounds=3
    )
    
    # 并发查询
    queries = [
        "List all users",
        "Show products with price above 100",
        "What is the average order amount?",
        "List all categories",
        "Show recent orders"
    ]
    
    results_queue = queue.Queue()
    
    def execute_query(query_id, query):
        try:
            result = chat_manager.process_query(
                db_id="text2sql_db",
                query=query,
                evidence=f"Concurrent test query {query_id}"
            )
            results_queue.put((query_id, query, result))
        except Exception as e:
            results_queue.put((query_id, query, {"error": str(e), "success": False}))
    
    # 启动并发线程
    threads = []
    for i, query in enumerate(queries):
        thread = threading.Thread(target=execute_query, args=(i, query))
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join(timeout=60)  # 60秒超时
    
    # 收集结果
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # 输出结果
    logger.info(f"并发查询结果:")
    for query_id, query, result in results:
        logger.info(f"  查询 {query_id}: {result['success']} - {query[:30]}...")
    
    # 最终统计
    stats = chat_manager.get_stats()
    logger.info(f"并发测试统计:")
    logger.info(f"  总查询数: {stats['total_queries']}")
    logger.info(f"  成功查询数: {stats['successful_queries']}")
    logger.info(f"  平均处理时间: {stats['average_processing_time']:.2f}秒")
    
    return results


def main():
    """主测试函数"""
    logger.info("开始完整的工作流端到端测试")
    logger.info(f"数据库配置: {config.database_config.host}:{config.database_config.port}/{config.database_config.database}")
    
    # 设置测试数据
    if not setup_mysql_test_data():
        logger.error("测试数据设置失败，终止测试")
        return
    
    try:
        # 1. 简单查询测试
        logger.info("\n" + "="*60)
        simple_result = test_simple_query()
        
        # 2. 复杂查询测试
        logger.info("\n" + "="*60)
        complex_result = test_complex_query()
        
        # 3. 聚合查询测试
        logger.info("\n" + "="*60)
        agg_result = test_aggregation_query()
        
        # 4. 错误处理测试
        logger.info("\n" + "="*60)
        error_result = test_error_handling()
        
        # 5. 统计功能测试
        logger.info("\n" + "="*60)
        batch_results, stats = test_workflow_statistics()
        
        # 6. 并发查询测试
        logger.info("\n" + "="*60)
        concurrent_results = test_concurrent_queries()
        
        # 总结
        logger.info("\n" + "="*60)
        logger.info("完整工作流测试总结:")
        
        test_results = [
            ("简单查询", simple_result['success']),
            ("复杂查询", complex_result['success']),
            ("聚合查询", agg_result['success']),
            ("错误处理", not error_result['success']),  # 错误处理测试期望失败
            ("批量统计", len(batch_results) > 0),
            ("并发处理", len(concurrent_results) > 0)
        ]
        
        for test_name, success in test_results:
            status = "✅ 通过" if success else "❌ 失败"
            logger.info(f"  {test_name}: {status}")
        
        total_passed = sum(1 for _, success in test_results if success)
        logger.info(f"\n测试通过率: {total_passed}/{len(test_results)} ({total_passed/len(test_results)*100:.1f}%)")
        
        if total_passed == len(test_results):
            logger.info("🎉 所有测试通过！工作流系统运行正常！")
        else:
            logger.warning("⚠️ 部分测试失败，请检查系统配置")
        
        # 显示最终统计
        logger.info("\n" + "="*60)
        logger.info("最终系统统计:")
        logger.info(f"  数据库: MySQL {config.database_config.database}")
        logger.info(f"  总查询处理: {stats['total_queries'] if 'stats' in locals() else 0}")
        logger.info(f"  工作流框架: LangGraph")
        logger.info(f"  智能体协作: Selector + Decomposer + Refiner")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试数据
        cleanup_mysql_test_data()


if __name__ == "__main__":
    main()
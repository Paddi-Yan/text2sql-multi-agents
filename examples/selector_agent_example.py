"""
Example usage of Selector Agent for MySQL database schema understanding and pruning.
"""

import sys
import os
import json
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.selector_agent import SelectorAgent, SchemaPruningConfig
from utils.models import ChatMessage


def get_sample_databases():
    """Get list of available sample MySQL databases."""
    return [
        "text2sql_db",  # Main test database with users, products, orders, etc.
    ]


def create_sample_json_schema():
    """Create a sample JSON schema file for demonstration."""
    schema_data = {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "description": "Customer ID"},
                    {"name": "name", "type": "TEXT", "description": "Customer name"},
                    {"name": "email", "type": "TEXT", "description": "Customer email"},
                    {"name": "phone", "type": "TEXT", "description": "Customer phone"},
                    {"name": "address", "type": "TEXT", "description": "Customer address"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "sample_values": {
                    "id": "1, 2, 3",
                    "name": "John Doe, Jane Smith, Bob Johnson",
                    "email": "john@example.com, jane@example.com, bob@example.com"
                }
            },
            "sales": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "description": "Sale ID"},
                    {"name": "customer_id", "type": "INTEGER", "description": "Customer ID"},
                    {"name": "amount", "type": "REAL", "description": "Sale amount"},
                    {"name": "date", "type": "TEXT", "description": "Sale date"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [
                    {"from": "customer_id", "to_table": "customers", "to_column": "id"}
                ],
                "sample_values": {
                    "id": "1, 2, 3",
                    "amount": "100.50, 250.00, 75.25",
                    "date": "2024-01-01, 2024-01-02, 2024-01-03"
                }
            }
        }
    }
    
    json_fd, json_path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(json_fd, 'w') as f:
        json.dump(schema_data, f, indent=2)
    
    return json_path


def main():
    """Main demonstration function."""
    print("=== Selector智能体演示 (MySQL版本) ===\n")
    
    # Get sample databases and JSON schema
    sample_databases = get_sample_databases()
    json_path = create_sample_json_schema()
    
    try:
        # 1. 基础功能演示
        print("1. 基础Selector智能体功能")
        
        # Create Selector agent
        selector = SelectorAgent(
            agent_name="DemoSelector",
            tables_json_path=os.path.dirname(json_path)
        )
        
        print(f"智能体名称: {selector.agent_name}")
        print(f"可用的示例数据库: {', '.join(sample_databases)}")
        print(f"初始统计: {selector.get_stats()}")
        
        # 2. MySQL数据库模式扫描演示
        print("\n2. MySQL数据库模式扫描")
        
        # Use the first sample database
        db_id = sample_databases[0]  # ecommerce_db
        
        try:
            # Scan database schema
            db_info = selector.schema_manager.scan_mysql_database_schema(db_id, db_id)
            db_stats = selector.schema_manager.get_database_stats(db_id)
        except Exception as e:
            print(f"❌ 无法连接到MySQL数据库: {e}")
            print("请确保:")
            print("1. MySQL服务正在运行")
            print("2. .env文件中的数据库配置正确")
            print("3. 已运行 python scripts/init_mysql_db.py 创建示例数据")
            return
        
        print(f"扫描的数据库: {db_id}")
        print(f"表数量: {db_stats.table_count}")
        print(f"总列数: {db_stats.total_column_count}")
        print(f"平均列数: {db_stats.avg_column_count:.1f}")
        print(f"最大列数: {db_stats.max_column_count}")
        
        print("\n表结构:")
        for table_name, columns in db_info.desc_dict.items():
            print(f"  {table_name}: {len(columns)} 列")
            for col_name, col_type, _ in columns[:3]:  # Show first 3 columns
                print(f"    - {col_name} ({col_type})")
            if len(columns) > 3:
                print(f"    ... 还有 {len(columns) - 3} 列")
        
        # 3. 模式描述生成演示
        print("\n3. 数据库模式描述生成")
        
        desc_str, fk_str = selector._get_db_desc_str(db_id, None)
        
        print("完整模式描述 (前500字符):")
        print(desc_str[:500] + "..." if len(desc_str) > 500 else desc_str)
        
        print(f"\n外键关系:")
        if fk_str:
            for fk_line in fk_str.split('\n')[:5]:  # Show first 5 FK relationships
                print(f"  {fk_line}")
        else:
            print("  无外键关系")
        
        # 4. 查询处理演示
        print("\n4. 简单查询处理")
        
        simple_message = ChatMessage(
            db_id=db_id,
            query="Show all user names and emails"
        )
        
        response = selector.talk(simple_message)
        
        print(f"处理结果: {'成功' if response.success else '失败'}")
        if response.success:
            print(f"是否裁剪: {response.message.pruned}")
            print(f"路由到: {response.message.send_to}")
            print(f"执行时间: {response.execution_time:.4f}s")
        else:
            print(f"错误信息: {response.error}")
        
        # 5. 复杂查询处理演示（需要裁剪）
        print("\n5. 复杂查询处理（可能需要裁剪）")
        
        # Update pruning config to make pruning more likely
        selector.update_pruning_config(
            avg_column_threshold=5,
            total_column_threshold=20,
            token_limit=2000
        )
        
        complex_message = ChatMessage(
            db_id=db_id,
            query="Show user purchase history with product details and reviews"
        )
        
        response = selector.talk(complex_message)
        
        print(f"处理结果: {'成功' if response.success else '失败'}")
        print(f"是否裁剪: {response.message.pruned}")
        print(f"路由到: {response.message.send_to}")
        
        if response.message.pruned and response.message.chosen_db_schema_dict:
            print("裁剪决策:")
            for table, decision in response.message.chosen_db_schema_dict.items():
                if decision == "keep_all":
                    print(f"  {table}: 保留所有列")
                elif decision == "drop_all":
                    print(f"  {table}: 删除整个表")
                elif isinstance(decision, list):
                    print(f"  {table}: 保留列 {decision}")
        
        # 6. JSON模式加载演示
        print("\n6. JSON模式文件加载")
        
        json_db_id = os.path.basename(json_path).replace('.json', '')
        
        # Load schema from JSON
        json_db_info = selector._load_schema_from_json(json_path, json_db_id)
        json_db_stats = selector.schema_manager.get_database_stats(json_db_id)
        
        print(f"JSON数据库: {json_db_id}")
        print(f"表数量: {json_db_stats.table_count}")
        print(f"总列数: {json_db_stats.total_column_count}")
        
        # Process query with JSON schema
        json_message = ChatMessage(
            db_id=json_db_id,
            query="Find customers with high sales amounts"
        )
        
        response = selector.talk(json_message)
        print(f"JSON模式处理结果: {'成功' if response.success else '失败'}")
        
        # 7. 不同查询类型的裁剪演示
        print("\n7. 不同查询类型的裁剪策略")
        
        test_queries = [
            ("用户查询", "Show all users with their basic information"),
            ("订单查询", "List all orders with customer details"),
            ("产品查询", "Find products in electronics category"),
            ("复杂关联查询", "Show user purchase history with product reviews and ratings"),
            ("统计查询", "Calculate total sales by category and month")
        ]
        
        for query_type, query_text in test_queries:
            message = ChatMessage(db_id=db_id, query=query_text)
            response = selector.talk(message)
            
            if response.success:
                print(f"  {query_type}: {'裁剪' if response.message.pruned else '无裁剪'}")
            else:
                print(f"  {query_type}: 处理失败")
        
        # 8. 性能统计演示
        print("\n8. 性能统计信息")
        
        pruning_stats = selector.get_pruning_stats()
        agent_stats = selector.get_stats()
        
        print("裁剪统计:")
        print(f"  总查询数: {pruning_stats['total_queries']}")
        print(f"  裁剪查询数: {pruning_stats['pruned_queries']}")
        print(f"  裁剪比例: {pruning_stats['avg_pruning_ratio']:.2%}")
        
        print("智能体统计:")
        print(f"  执行次数: {agent_stats['execution_count']}")
        print(f"  成功率: {agent_stats['success_rate']:.2%}")
        print(f"  平均执行时间: {agent_stats['average_execution_time']:.4f}s")
        
        # 9. 配置调整演示
        print("\n9. 动态配置调整")
        
        print("原始配置:")
        print(f"  Token限制: {selector.pruning_config.token_limit}")
        print(f"  平均列阈值: {selector.pruning_config.avg_column_threshold}")
        print(f"  总列阈值: {selector.pruning_config.total_column_threshold}")
        
        # Update configuration
        selector.update_pruning_config(
            token_limit=50000,
            avg_column_threshold=10,
            total_column_threshold=50
        )
        
        print("更新后配置:")
        print(f"  Token限制: {selector.pruning_config.token_limit}")
        print(f"  平均列阈值: {selector.pruning_config.avg_column_threshold}")
        print(f"  总列阈值: {selector.pruning_config.total_column_threshold}")
        
        # Test with new configuration
        test_message = ChatMessage(db_id=db_id, query="Show comprehensive user data")
        response = selector.talk(test_message)
        print(f"新配置下的裁剪结果: {'裁剪' if response.message.pruned else '无裁剪'}")
        
        # 10. 错误处理演示
        print("\n10. 错误处理演示")
        
        # Test with non-existent database
        error_message = ChatMessage(
            db_id="non_existent_db",
            query="This should fail"
        )
        
        response = selector.talk(error_message)
        print(f"不存在数据库的处理: {'成功' if response.success else '失败'}")
        if not response.success:
            print(f"错误信息: {response.error}")
        
        # Test with invalid message
        invalid_message = ChatMessage(db_id="", query="")
        response = selector.talk(invalid_message)
        print(f"无效消息的处理: {'成功' if response.success else '失败'}")
        if not response.success:
            print(f"错误信息: {response.error}")
        
        print("\n=== 演示完成 ===")
        print("\nSelector智能体已成功演示以下功能:")
        print("✓ MySQL数据库模式自动扫描和理解")
        print("✓ 基于MAC-SQL策略的动态模式裁剪")
        print("✓ Token限制和复杂度评估")
        print("✓ 数据库描述字符串和外键关系生成")
        print("✓ JSON模式文件加载支持")
        print("✓ 查询相关性分析和表/列选择")
        print("✓ 性能统计和监控")
        print("✓ 动态配置调整")
        print("✓ 完善的错误处理机制")
        
    finally:
        # Clean up temporary files
        if os.path.exists(json_path):
            os.unlink(json_path)


if __name__ == "__main__":
    main()
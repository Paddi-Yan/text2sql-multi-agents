"""
MySQL Selector Agent Example - 演示MySQL数据库模式理解和裁剪功能
"""

import sys
import os
import json
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.selector_agent import SelectorAgent, SchemaPruningConfig
from utils.models import ChatMessage


def get_sample_databases():
    """获取可用的示例MySQL数据库列表"""
    return [
        "text2sql_db",  # 主要测试数据库：用户、产品、订单等
    ]


def create_sample_json_schema():
    """创建示例JSON模式文件用于演示"""
    schema_data = {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "INT", "description": "客户ID"},
                    {"name": "name", "type": "VARCHAR", "description": "客户姓名"},
                    {"name": "email", "type": "VARCHAR", "description": "客户邮箱"},
                    {"name": "phone", "type": "VARCHAR", "description": "客户电话"},
                    {"name": "address", "type": "TEXT", "description": "客户地址"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "sample_values": {
                    "id": "1, 2, 3",
                    "name": "张三, 李四, 王五",
                    "email": "zhang@example.com, li@example.com, wang@example.com"
                }
            },
            "sales": {
                "columns": [
                    {"name": "id", "type": "INT", "description": "销售ID"},
                    {"name": "customer_id", "type": "INT", "description": "客户ID"},
                    {"name": "amount", "type": "DECIMAL", "description": "销售金额"},
                    {"name": "date", "type": "DATE", "description": "销售日期"}
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
    with os.fdopen(json_fd, 'w', encoding='utf-8') as f:
        json.dump(schema_data, f, indent=2, ensure_ascii=False)
    
    return json_path


def main():
    """主演示函数"""
    print("=== MySQL Selector智能体演示 ===\n")
    
    # 获取示例数据库和JSON模式
    sample_databases = get_sample_databases()
    json_path = create_sample_json_schema()
    
    try:
        # 1. 基础功能演示
        print("1. 基础Selector智能体功能")
        
        # 创建Selector智能体
        selector = SelectorAgent(
            agent_name="MySQLDemoSelector",
            tables_json_path=os.path.dirname(json_path)
        )
        
        print(f"智能体名称: {selector.agent_name}")
        print(f"可用的示例数据库: {', '.join(sample_databases)}")
        print(f"初始统计: {selector.get_stats()}")
        
        # 2. MySQL数据库模式扫描演示
        print("\n2. MySQL数据库模式扫描")
        
        # 使用第一个示例数据库
        db_id = sample_databases[0]  # ecommerce_db
        
        try:
            # 扫描数据库模式
            db_info = selector.schema_manager.scan_mysql_database_schema(db_id, db_id)
            db_stats = selector.schema_manager.get_database_stats(db_id)
            
            print(f"扫描的数据库: {db_id}")
            print(f"表数量: {db_stats.table_count}")
            print(f"总列数: {db_stats.total_column_count}")
            print(f"平均列数: {db_stats.avg_column_count:.1f}")
            print(f"最大列数: {db_stats.max_column_count}")
            
            print("\n表结构:")
            for table_name, columns in db_info.desc_dict.items():
                print(f"  {table_name}: {len(columns)} 列")
                for col_name, col_type, col_desc in columns[:3]:  # 显示前3列
                    desc_text = f" - {col_desc}" if col_desc else ""
                    print(f"    - {col_name} ({col_type}){desc_text}")
                if len(columns) > 3:
                    print(f"    ... 还有 {len(columns) - 3} 列")
            
        except Exception as e:
            print(f"❌ 无法连接到MySQL数据库: {e}")
            print("请确保:")
            print("1. MySQL服务正在运行")
            print("2. .env文件中的数据库配置正确")
            print("3. 已运行 python scripts/init_mysql_db.py 创建示例数据")
            print("\n继续使用JSON模式演示...")
            
            # 使用JSON模式作为备选
            db_id = "json_demo"
            db_info = selector._load_schema_from_json(json_path, db_id)
            db_stats = selector.schema_manager.get_database_stats(db_id)
            
            print(f"\n使用JSON模式: {db_id}")
            print(f"表数量: {db_stats.table_count}")
            print(f"总列数: {db_stats.total_column_count}")
        
        # 3. 模式描述生成演示
        print("\n3. 数据库模式描述生成")
        
        desc_str, fk_str = selector._get_db_desc_str(db_id, None)
        
        print("完整模式描述 (前500字符):")
        print(desc_str[:500] + "..." if len(desc_str) > 500 else desc_str)
        
        print(f"\n外键关系:")
        if fk_str:
            for fk_line in fk_str.split('\n')[:5]:  # 显示前5个外键关系
                if fk_line.strip():
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
        
        # 5. 复杂查询处理演示（可能需要裁剪）
        print("\n5. 复杂查询处理（可能需要裁剪）")
        
        # 更新裁剪配置以使裁剪更容易触发
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
        if response.success:
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
        
        # 6. 不同查询类型的裁剪演示
        print("\n6. 不同查询类型的裁剪策略")
        
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
        
        # 7. 性能统计演示
        print("\n7. 性能统计信息")
        
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
        
        # 8. 配置调整演示
        print("\n8. 动态配置调整")
        
        print("原始配置:")
        print(f"  Token限制: {selector.pruning_config.token_limit}")
        print(f"  平均列阈值: {selector.pruning_config.avg_column_threshold}")
        print(f"  总列阈值: {selector.pruning_config.total_column_threshold}")
        
        # 更新配置
        selector.update_pruning_config(
            token_limit=50000,
            avg_column_threshold=10,
            total_column_threshold=50
        )
        
        print("更新后配置:")
        print(f"  Token限制: {selector.pruning_config.token_limit}")
        print(f"  平均列阈值: {selector.pruning_config.avg_column_threshold}")
        print(f"  总列阈值: {selector.pruning_config.total_column_threshold}")
        
        # 使用新配置测试
        test_message = ChatMessage(db_id=db_id, query="Show comprehensive user data")
        response = selector.talk(test_message)
        if response.success:
            print(f"新配置下的裁剪结果: {'裁剪' if response.message.pruned else '无裁剪'}")
        
        # 9. 错误处理演示
        print("\n9. 错误处理演示")
        
        # 测试不存在的数据库
        error_message = ChatMessage(
            db_id="non_existent_db",
            query="This should fail"
        )
        
        response = selector.talk(error_message)
        print(f"不存在数据库的处理: {'成功' if response.success else '失败'}")
        if not response.success:
            print(f"错误信息: {response.error}")
        
        # 测试无效消息
        invalid_message = ChatMessage(db_id="", query="")
        response = selector.talk(invalid_message)
        print(f"无效消息的处理: {'成功' if response.success else '失败'}")
        if not response.success:
            print(f"错误信息: {response.error}")
        
        # 10. 多数据库演示
        print("\n10. 多数据库支持演示")
        
        for db_name in sample_databases:
            try:
                print(f"\n尝试连接数据库: {db_name}")
                db_info = selector.schema_manager.scan_mysql_database_schema(db_name, db_name)
                db_stats = selector.schema_manager.get_database_stats(db_name)
                
                print(f"  ✅ 成功连接 {db_name}")
                print(f"  表数量: {db_stats.table_count}")
                print(f"  总列数: {db_stats.total_column_count}")
                
                # 测试一个简单查询
                test_msg = ChatMessage(db_id=db_name, query="Show basic information")
                response = selector.talk(test_msg)
                print(f"  查询测试: {'成功' if response.success else '失败'}")
                
            except Exception as e:
                print(f"  ❌ 连接失败: {e}")
        
        print("\n=== 演示完成 ===")
        print("\nMySQL Selector智能体已成功演示以下功能:")
        print("✅ MySQL数据库模式自动扫描和理解")
        print("✅ 基于MAC-SQL策略的动态模式裁剪")
        print("✅ Token限制和复杂度评估")
        print("✅ 数据库描述字符串和外键关系生成")
        print("✅ JSON模式文件加载支持（备选方案）")
        print("✅ 查询相关性分析和表/列选择")
        print("✅ 性能统计和监控")
        print("✅ 动态配置调整")
        print("✅ 完善的错误处理机制")
        print("✅ 多数据库支持")
        
        print("\n💡 提示:")
        print("- 确保MySQL服务正在运行")
        print("- 运行 python scripts/init_mysql_db.py 创建示例数据")
        print("- 检查 .env 文件中的数据库配置")
        
    finally:
        # 清理临时文件
        if os.path.exists(json_path):
            os.unlink(json_path)


if __name__ == "__main__":
    main()
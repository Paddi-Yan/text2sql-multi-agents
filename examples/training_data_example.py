"""
Example usage of the training data management system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.training_models import TrainingData, TrainingDataType
from utils.training_data_manager import TrainingDataManager
from utils.vectorization import MetadataManager


def main():
    """演示训练数据管理系统的使用"""
    
    # 创建训练数据管理器
    manager = TrainingDataManager()
    
    print("=== 训练数据管理系统演示 ===\n")
    
    # 1. 添加DDL语句训练数据
    print("1. 添加DDL语句训练数据")
    ddl_content = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    ddl_data = TrainingData(
        id=manager.generate_id(ddl_content, TrainingDataType.DDL_STATEMENT),
        data_type=TrainingDataType.DDL_STATEMENT,
        content=ddl_content.strip(),
        metadata=MetadataManager.create_metadata("ddl", "manual"),
        db_id="ecommerce_db",
        table_names=MetadataManager.extract_table_names_from_ddl(ddl_content),
        tags=MetadataManager.extract_tags_from_content(ddl_content, "ddl")
    )
    
    manager.add_training_data(ddl_data)
    print(f"添加DDL数据: {ddl_data.id}")
    
    # 2. 添加业务文档训练数据
    print("\n2. 添加业务文档训练数据")
    doc_content = """
    用户表(users)存储系统中所有注册用户的基本信息。
    - id: 用户唯一标识符
    - name: 用户姓名，不能为空
    - email: 用户邮箱，必须唯一
    - created_at: 用户注册时间
    """
    
    doc_data = TrainingData(
        id=manager.generate_id(doc_content, TrainingDataType.DOCUMENTATION),
        data_type=TrainingDataType.DOCUMENTATION,
        content=doc_content.strip(),
        metadata=MetadataManager.create_metadata("doc", "manual", {"category": "schema_documentation"}),
        db_id="ecommerce_db",
        table_names=["users"],
        tags=["documentation", "users", "schema"]
    )
    
    manager.add_training_data(doc_data)
    print(f"添加文档数据: {doc_data.id}")
    
    # 3. 添加SQL查询示例
    print("\n3. 添加SQL查询示例")
    sql_content = "SELECT id, name, email FROM users WHERE created_at >= '2024-01-01' ORDER BY created_at DESC;"
    
    sql_data = TrainingData(
        id=manager.generate_id(sql_content, TrainingDataType.SQL_QUERY),
        data_type=TrainingDataType.SQL_QUERY,
        content=sql_content,
        metadata=MetadataManager.create_metadata("sql", "manual"),
        db_id="ecommerce_db",
        sql=sql_content,
        table_names=MetadataManager.extract_table_names_from_sql(sql_content),
        tags=MetadataManager.extract_tags_from_content(sql_content, "sql")
    )
    
    manager.add_training_data(sql_data)
    print(f"添加SQL数据: {sql_data.id}")
    
    # 4. 添加问题-SQL对
    print("\n4. 添加问题-SQL对")
    question = "显示所有在2024年注册的用户，按注册时间倒序排列"
    sql_answer = "SELECT id, name, email FROM users WHERE created_at >= '2024-01-01' ORDER BY created_at DESC;"
    qa_content = f"Q: {question}\nA: {sql_answer}"
    
    qa_data = TrainingData(
        id=manager.generate_id(qa_content, TrainingDataType.QUESTION_SQL_PAIR),
        data_type=TrainingDataType.QUESTION_SQL_PAIR,
        content=qa_content,
        metadata=MetadataManager.create_metadata("qa_pair", "manual"),
        db_id="ecommerce_db",
        question=question,
        sql=sql_answer,
        table_names=MetadataManager.extract_table_names_from_sql(sql_answer),
        tags=["query", "filtering", "sorting", "users", "date_range"]
    )
    
    manager.add_training_data(qa_data)
    print(f"添加QA对数据: {qa_data.id}")
    
    # 5. 显示统计信息
    print("\n5. 统计信息")
    stats = manager.get_stats()
    print(f"总数据量: {stats.total_count}")
    print(f"DDL语句: {stats.ddl_count}")
    print(f"文档: {stats.doc_count}")
    print(f"SQL查询: {stats.sql_count}")
    print(f"问题-SQL对: {stats.qa_pair_count}")
    print(f"数据库覆盖: {stats.db_coverage}")
    print(f"标签分布: {dict(list(stats.tag_distribution.items())[:5])}")  # 显示前5个标签
    
    # 6. 按类型查询数据
    print("\n6. 按类型查询数据")
    qa_pairs = manager.get_by_type(TrainingDataType.QUESTION_SQL_PAIR)
    print(f"找到 {len(qa_pairs)} 个问题-SQL对:")
    for qa in qa_pairs:
        print(f"  - 问题: {qa.question}")
        print(f"    SQL: {qa.sql}")
    
    # 7. 内容搜索
    print("\n7. 内容搜索")
    search_results = manager.search_by_content("用户")
    print(f"搜索'用户'找到 {len(search_results)} 条记录:")
    for result in search_results:
        print(f"  - 类型: {result.data_type.value}, ID: {result.id}")
    
    # 8. 按标签查询
    print("\n8. 按标签查询")
    tag_results = manager.get_by_tags(["users", "query"])
    print(f"标签'users'和'query'找到 {len(tag_results)} 条记录:")
    for result in tag_results:
        print(f"  - 类型: {result.data_type.value}, 标签: {result.tags}")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    main()
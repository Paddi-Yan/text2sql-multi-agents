"""
Example usage of VannaTrainingService and EnhancedRAGRetriever.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.training_service import VannaTrainingService, EnhancedRAGRetriever
from storage.vector_store import VectorStore
from utils.vectorization import VectorizationService
from config.settings import config
import random


class MockEmbeddingService:
    """Mock embedding service for demonstration purposes."""
    
    def generate_embedding(self, text: str) -> list:
        """Generate a mock embedding vector."""
        # Generate a consistent but pseudo-random embedding based on text hash
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        random.seed(text_hash)
        return [random.random() for _ in range(1536)]


def main():
    """演示Vanna.ai式训练服务的使用"""
    
    print("=== Vanna.ai式训练服务演示 ===\n")
    
    # 初始化服务
    vector_store = VectorStore(config.vector_store_config)
    # Use mock embedding service for demonstration
    embedding_service = MockEmbeddingService()
    
    # 创建训练服务
    training_service = VannaTrainingService(
        vector_store=vector_store,
        embedding_service=embedding_service
    )
    
    # 创建RAG检索器
    rag_retriever = EnhancedRAGRetriever(
        vector_store=vector_store,
        embedding_service=embedding_service
    )
    
    db_id = "ecommerce_db"
    
    # 1. 训练DDL语句
    print("1. 训练DDL语句")
    ddl_statements = [
        """CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            age INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE orders (
            id INT PRIMARY KEY,
            user_id INT,
            product_name VARCHAR(200),
            quantity INT,
            price DECIMAL(10,2),
            order_date TIMESTAMP,
            status VARCHAR(50),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );""",
        """CREATE TABLE products (
            id INT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            price DECIMAL(10,2),
            stock_quantity INT,
            created_at TIMESTAMP
        );"""
    ]
    
    success = training_service.train_ddl(ddl_statements, db_id)
    print(f"DDL训练结果: {'成功' if success else '失败'}")
    
    # 2. 训练业务文档
    print("\n2. 训练业务文档")
    documentation = [
        {
            "title": "用户表说明",
            "content": "用户表存储所有注册用户信息。age字段表示用户年龄，可以为空。活跃用户定义为最近30天内有订单的用户。",
            "category": "schema_doc"
        },
        {
            "title": "订单状态说明", 
            "content": "订单状态包括：pending(待处理)、processing(处理中)、shipped(已发货)、delivered(已送达)、cancelled(已取消)。",
            "category": "business_rules"
        },
        {
            "title": "产品分类",
            "content": "产品分类包括：electronics(电子产品)、clothing(服装)、books(图书)、home(家居用品)、sports(体育用品)。",
            "category": "data_definitions"
        }
    ]
    
    success = training_service.train_documentation(documentation, db_id)
    print(f"文档训练结果: {'成功' if success else '失败'}")
    
    # 3. 训练SQL查询示例
    print("\n3. 训练SQL查询示例")
    sql_examples = [
        "SELECT COUNT(*) FROM users WHERE age >= 18;",
        "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name;",
        "SELECT * FROM orders WHERE status = 'delivered' AND order_date >= '2024-01-01';",
        "SELECT p.name, p.price FROM products p WHERE p.category = 'electronics' ORDER BY p.price DESC;",
        "SELECT AVG(price) as avg_price FROM orders WHERE status = 'delivered';"
    ]
    
    success = training_service.train_sql(sql_examples, db_id)
    print(f"SQL示例训练结果: {'成功' if success else '失败'}")
    
    # 4. 训练问题-SQL对（最重要的训练数据）
    print("\n4. 训练问题-SQL对")
    qa_pairs = [
        {
            "question": "有多少个成年用户？",
            "sql": "SELECT COUNT(*) FROM users WHERE age >= 18;"
        },
        {
            "question": "显示每个用户的订单数量",
            "sql": "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name;"
        },
        {
            "question": "查找所有已送达的订单",
            "sql": "SELECT * FROM orders WHERE status = 'delivered';"
        },
        {
            "question": "按价格降序显示电子产品",
            "sql": "SELECT p.name, p.price FROM products p WHERE p.category = 'electronics' ORDER BY p.price DESC;"
        },
        {
            "question": "计算已送达订单的平均价格",
            "sql": "SELECT AVG(price) as avg_price FROM orders WHERE status = 'delivered';"
        },
        {
            "question": "找出购买次数最多的用户",
            "sql": "SELECT u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name ORDER BY order_count DESC LIMIT 1;"
        }
    ]
    
    success = training_service.train_qa_pairs(qa_pairs, db_id)
    print(f"问题-SQL对训练结果: {'成功' if success else '失败'}")
    
    # 5. 训练领域知识
    print("\n5. 训练领域知识")
    domain_knowledge = [
        {
            "content": "在电商系统中，用户留存率通常通过计算在特定时间段内重复购买的用户比例来衡量。",
            "category": "business_metrics",
            "tags": ["retention", "metrics", "ecommerce"]
        },
        {
            "content": "订单金额计算公式：总金额 = 数量 × 单价。对于批量订单，可能有折扣优惠。",
            "category": "calculation_rules",
            "tags": ["pricing", "calculation", "orders"]
        },
        {
            "content": "库存预警：当产品库存数量低于10时，系统应该发出补货提醒。",
            "category": "business_rules",
            "tags": ["inventory", "alert", "stock"]
        }
    ]
    
    success = training_service.train_domain_knowledge(domain_knowledge, db_id)
    print(f"领域知识训练结果: {'成功' if success else '失败'}")
    
    # 6. 获取训练统计
    print("\n6. 训练统计信息")
    stats = training_service.get_training_stats(db_id)
    print(f"数据库 {db_id} 的训练统计:")
    print(f"  总训练样本数: {stats['total_training_examples']}")
    print(f"  按类型分布: {stats['by_type']}")
    
    # 7. 演示RAG检索功能
    print("\n7. RAG检索演示")
    test_queries = [
        "显示所有成年用户",
        "计算用户的平均订单金额", 
        "查找库存不足的产品",
        "统计每个产品分类的销售情况"
    ]
    
    schema_info = """
    Tables:
    - users (id, name, email, age, created_at)
    - orders (id, user_id, product_name, quantity, price, order_date, status)
    - products (id, name, category, price, stock_quantity, created_at)
    """
    
    for query in test_queries:
        print(f"\n查询: {query}")
        
        # 检索相关上下文
        context = rag_retriever.retrieve_context(query, db_id, top_k=3)
        
        print("检索到的上下文:")
        if context["qa_pairs"]:
            print(f"  相似问题-SQL对: {len(context['qa_pairs'])} 个")
            for i, pair in enumerate(context["qa_pairs"][:2]):
                print(f"    {i+1}. Q: {pair['question']}")
                print(f"       A: {pair['sql']}")
        
        if context["sql_examples"]:
            print(f"  相似SQL示例: {len(context['sql_examples'])} 个")
            for i, sql in enumerate(context["sql_examples"][:2]):
                print(f"    {i+1}. {sql}")
        
        if context["documentation"]:
            print(f"  相关文档: {len(context['documentation'])} 个")
        
        if context["domain_knowledge"]:
            print(f"  领域知识: {len(context['domain_knowledge'])} 个")
        
        # 构建增强提示词
        enhanced_prompt = rag_retriever.build_enhanced_prompt(query, context, schema_info)
        print(f"  增强提示词长度: {len(enhanced_prompt)} 字符")
    
    # 8. 演示自动学习功能
    print("\n8. 自动学习演示")
    successful_query = "显示所有用户的邮箱"
    successful_sql = "SELECT name, email FROM users;"
    
    auto_train_result = training_service.auto_train_from_successful_query(
        successful_query, successful_sql, db_id
    )
    print(f"自动学习结果: {'成功' if auto_train_result else '失败'}")
    
    # 更新统计
    final_stats = training_service.get_training_stats(db_id)
    print(f"最终训练样本数: {final_stats['total_training_examples']}")
    
    print("\n=== 演示完成 ===")
    print("\n训练服务已成功演示以下功能:")
    print("✓ DDL语句训练 - 让系统理解数据库结构")
    print("✓ 业务文档训练 - 提供业务上下文")
    print("✓ SQL示例训练 - 学习查询模式")
    print("✓ 问题-SQL对训练 - 最直接的训练方式")
    print("✓ 领域知识训练 - 业务规则和计算逻辑")
    print("✓ RAG检索 - 智能上下文检索")
    print("✓ 增强提示词生成 - 结合检索上下文")
    print("✓ 自动学习 - 从成功查询中学习")


if __name__ == "__main__":
    main()
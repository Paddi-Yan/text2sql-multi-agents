"""
Example usage of Enhanced RAG Retriever with advanced features.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.enhanced_rag_retriever import (
    EnhancedRAGRetriever, RetrievalConfig, RetrievalStrategy
)
from services.training_service import VannaTrainingService
from storage.vector_store import VectorStore
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
    """演示增强型RAG检索系统的高级功能"""
    
    print("=== 增强型RAG检索系统演示 ===\n")
    
    # 初始化服务
    vector_store = VectorStore(config.vector_store_config)
    embedding_service = MockEmbeddingService()
    
    # 创建训练服务并添加训练数据
    training_service = VannaTrainingService(
        vector_store=vector_store,
        embedding_service=embedding_service
    )
    
    db_id = "ecommerce_db"
    
    # 1. 准备训练数据
    print("1. 准备训练数据")
    
    # DDL语句
    ddl_statements = [
        """CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            age INT,
            status VARCHAR(20) DEFAULT 'active',
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
            is_active BOOLEAN DEFAULT TRUE
        );"""
    ]
    
    # 问题-SQL对（包含不同质量的示例）
    qa_pairs = [
        # 高质量示例
        {
            "question": "显示所有活跃用户的信息",
            "sql": "SELECT id, name, email, age FROM users WHERE status = 'active';"
        },
        {
            "question": "统计每个用户的订单总数",
            "sql": "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name ORDER BY order_count DESC;"
        },
        {
            "question": "查找价格超过100元的产品",
            "sql": "SELECT name, price, category FROM products WHERE price > 100 AND is_active = TRUE ORDER BY price DESC;"
        },
        # 中等质量示例
        {
            "question": "显示用户邮箱",
            "sql": "SELECT email FROM users;"
        },
        # 低质量示例（包含错误）
        {
            "question": "错误的查询示例",
            "sql": "SELECT * FROM nonexistent_table WHERE syntax error;"
        }
    ]
    
    # SQL示例
    sql_examples = [
        "SELECT COUNT(*) FROM users WHERE age >= 18;",
        "SELECT AVG(price) FROM orders WHERE status = 'completed';",
        "SELECT p.name, p.stock_quantity FROM products p WHERE p.stock_quantity < 10;",
        "SELECT u.name, o.order_date FROM users u JOIN orders o ON u.id = o.user_id WHERE o.order_date >= '2024-01-01';"
    ]
    
    # 业务文档
    documentation = [
        {
            "title": "用户状态说明",
            "content": "用户状态包括：active(活跃)、inactive(非活跃)、suspended(暂停)。只有活跃用户可以下订单。",
            "category": "business_rules"
        },
        {
            "title": "订单状态定义",
            "content": "订单状态：pending(待处理)、processing(处理中)、shipped(已发货)、delivered(已送达)、cancelled(已取消)。",
            "category": "data_definitions"
        }
    ]
    
    # 领域知识
    domain_knowledge = [
        {
            "content": "库存预警：当产品库存数量低于10时，需要及时补货。",
            "category": "inventory_management",
            "tags": ["inventory", "alert"]
        },
        {
            "content": "用户活跃度定义：最近30天内有登录或下单行为的用户被认为是活跃用户。",
            "category": "user_metrics",
            "tags": ["user", "activity"]
        }
    ]
    
    # 添加训练数据
    training_service.train_ddl(ddl_statements, db_id)
    training_service.train_qa_pairs(qa_pairs, db_id)
    training_service.train_sql(sql_examples, db_id)
    training_service.train_documentation(documentation, db_id)
    training_service.train_domain_knowledge(domain_knowledge, db_id)
    
    print("训练数据添加完成")
    
    # 2. 创建不同配置的检索器
    print("\n2. 创建不同配置的检索器")
    
    # 标准配置
    standard_config = RetrievalConfig(
        similarity_threshold=0.7,
        max_examples_per_type=3,
        enable_quality_filter=True,
        enable_diversity_filter=True,
        strategy=RetrievalStrategy.BALANCED
    )
    
    # QA重点配置
    qa_focused_config = RetrievalConfig(
        similarity_threshold=0.6,
        max_examples_per_type=2,
        enable_quality_filter=True,
        enable_diversity_filter=True,
        strategy=RetrievalStrategy.QA_FOCUSED
    )
    
    # 高质量配置
    high_quality_config = RetrievalConfig(
        similarity_threshold=0.8,
        max_examples_per_type=2,
        enable_quality_filter=True,
        enable_diversity_filter=True,
        strategy=RetrievalStrategy.BALANCED
    )
    
    # 无过滤配置
    no_filter_config = RetrievalConfig(
        similarity_threshold=0.3,
        max_examples_per_type=5,
        enable_quality_filter=False,
        enable_diversity_filter=False,
        strategy=RetrievalStrategy.BALANCED
    )
    
    retrievers = {
        "标准检索器": EnhancedRAGRetriever(vector_store, embedding_service, standard_config),
        "QA重点检索器": EnhancedRAGRetriever(vector_store, embedding_service, qa_focused_config),
        "高质量检索器": EnhancedRAGRetriever(vector_store, embedding_service, high_quality_config),
        "无过滤检索器": EnhancedRAGRetriever(vector_store, embedding_service, no_filter_config)
    }
    
    # 3. 测试查询
    print("\n3. 测试不同类型的查询")
    
    test_queries = [
        "显示所有活跃用户的详细信息",
        "统计每个产品分类的平均价格",
        "查找库存不足的产品",
        "显示最近一个月的订单统计"
    ]
    
    schema_info = """
    数据库模式:
    - users (id, name, email, age, status, created_at)
    - orders (id, user_id, product_name, quantity, price, order_date, status)
    - products (id, name, category, price, stock_quantity, is_active)
    """
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 60)
        
        for retriever_name, retriever in retrievers.items():
            print(f"\n{retriever_name}:")
            
            # 获取检索统计
            stats = retriever.get_retrieval_stats(query, db_id)
            print(f"  检索统计: {stats['retrieved_counts']}")
            print(f"  总检索数: {stats['total_retrieved']}")
            print(f"  高质量QA对: {stats['high_quality_qa_pairs']}")
            print(f"  相似度阈值: {stats['similarity_threshold']}")
            print(f"  检索策略: {stats['strategy']}")
            
            # 检索上下文
            context = retriever.retrieve_context(query, db_id)
            
            # 显示检索到的内容摘要
            if context.get("qa_pairs"):
                print(f"  相关QA对: {len(context['qa_pairs'])} 个")
                for i, pair in enumerate(context["qa_pairs"][:2], 1):
                    score = pair.get("score", 0)
                    print(f"    {i}. Q: {pair['question'][:50]}... (分数: {score:.2f})")
            
            if context.get("sql_examples"):
                print(f"  SQL示例: {len(context['sql_examples'])} 个")
            
            if context.get("documentation"):
                print(f"  相关文档: {len(context['documentation'])} 个")
            
            if context.get("domain_knowledge"):
                print(f"  领域知识: {len(context['domain_knowledge'])} 个")
    
    # 4. 演示高级提示词生成
    print("\n\n4. 演示高级提示词生成")
    
    query = "显示所有活跃用户的详细信息"
    retriever = retrievers["标准检索器"]
    
    context = retriever.retrieve_context(query, db_id)
    
    # 生成标准提示词
    standard_prompt = retriever.build_enhanced_prompt(query, context, schema_info)
    
    # 生成带额外指令的提示词
    enhanced_prompt = retriever.build_enhanced_prompt(
        query, 
        context, 
        schema_info,
        "请确保查询性能优化，使用适当的索引，并限制返回结果数量。"
    )
    
    print(f"标准提示词长度: {len(standard_prompt)} 字符")
    print(f"增强提示词长度: {len(enhanced_prompt)} 字符")
    
    print("\n标准提示词预览:")
    print(standard_prompt[:500] + "..." if len(standard_prompt) > 500 else standard_prompt)
    
    # 5. 演示配置动态更新
    print("\n\n5. 演示配置动态更新")
    
    retriever = retrievers["标准检索器"]
    
    print("原始配置:")
    print(f"  相似度阈值: {retriever.config.similarity_threshold}")
    print(f"  每类型最大示例数: {retriever.config.max_examples_per_type}")
    print(f"  启用质量过滤: {retriever.config.enable_quality_filter}")
    
    # 动态更新配置
    retriever.update_config(
        similarity_threshold=0.9,
        max_examples_per_type=1,
        enable_quality_filter=False
    )
    
    print("\n更新后配置:")
    print(f"  相似度阈值: {retriever.config.similarity_threshold}")
    print(f"  每类型最大示例数: {retriever.config.max_examples_per_type}")
    print(f"  启用质量过滤: {retriever.config.enable_quality_filter}")
    
    # 测试更新后的检索效果
    updated_stats = retriever.get_retrieval_stats(query, db_id)
    print(f"\n更新后检索统计: {updated_stats['retrieved_counts']}")
    print(f"总检索数: {updated_stats['total_retrieved']}")
    
    # 6. 演示自定义过滤器
    print("\n\n6. 演示自定义过滤器")
    
    # 使用自定义过滤器检索特定类别的内容
    custom_filters = {"category": "business_rules"}
    
    context_with_filter = retriever.retrieve_context(
        "用户状态相关的业务规则",
        db_id,
        custom_filters=custom_filters
    )
    
    print("使用自定义过滤器 (category: business_rules):")
    print(f"  检索到的文档: {len(context_with_filter.get('documentation', []))}")
    print(f"  检索到的领域知识: {len(context_with_filter.get('domain_knowledge', []))}")
    
    # 7. 性能对比
    print("\n\n7. 不同策略的性能对比")
    
    strategies = [
        RetrievalStrategy.BALANCED,
        RetrievalStrategy.QA_FOCUSED,
        RetrievalStrategy.SQL_FOCUSED,
        RetrievalStrategy.CONTEXT_FOCUSED
    ]
    
    test_query = "统计活跃用户的订单情况"
    
    for strategy in strategies:
        retriever.config.strategy = strategy
        retriever.context_builder = retriever.context_builder.__class__(retriever.config)
        
        stats = retriever.get_retrieval_stats(test_query, db_id)
        
        print(f"\n策略: {strategy.value}")
        print(f"  检索分布: {stats['retrieved_counts']}")
        print(f"  总数: {stats['total_retrieved']}")
        print(f"  高质量QA对: {stats['high_quality_qa_pairs']}")
    
    print("\n=== 演示完成 ===")
    print("\n增强型RAG检索系统已成功演示以下高级功能:")
    print("✓ 质量过滤 - 基于相似度和内容质量的智能过滤")
    print("✓ 多样性过滤 - 避免过于相似的检索结果")
    print("✓ 多种检索策略 - 平衡、QA重点、SQL重点、上下文重点")
    print("✓ 动态配置更新 - 运行时调整检索参数")
    print("✓ 自定义过滤器 - 基于元数据的精确过滤")
    print("✓ 高级提示词生成 - 结构化、分层的提示词构建")
    print("✓ 检索统计分析 - 详细的检索性能指标")
    print("✓ 上下文长度控制 - 智能截断和优化")


if __name__ == "__main__":
    main()
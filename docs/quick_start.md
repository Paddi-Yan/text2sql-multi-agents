# 快速开始指南

## 环境准备

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境变量配置
```bash
export OPENAI_API_KEY="your-api-key"
export DB_HOST="localhost"
export REDIS_HOST="localhost"
export MILVUS_HOST="localhost"
```

## 基本使用

### 1. Selector智能体使用

```python
from agents.selector_agent import SelectorAgent
from utils.models import ChatMessage

# 创建Selector智能体
selector = SelectorAgent(
    agent_name="MySelector",
    data_path="/path/to/databases",  # SQLite数据库文件路径
    tables_json_path="/path/to/schemas"  # JSON模式文件路径
)

# 创建查询消息
message = ChatMessage(
    db_id="ecommerce_db",
    query="显示所有活跃用户的订单信息"
)

# 处理查询
response = selector.talk(message)

if response.success:
    print(f"模式选择成功")
    print(f"是否裁剪: {response.message.pruned}")
    print(f"数据库描述: {response.message.desc_str[:200]}...")
    print(f"下一个智能体: {response.message.send_to}")
else:
    print(f"处理失败: {response.error}")
```

### 2. 训练服务使用

```python
from services.training_service import VannaTrainingService
from storage.vector_store import VectorStore
from config.settings import config

# 初始化服务
vector_store = VectorStore(config.vector_store_config)
embedding_service = MockEmbeddingService()  # 替换为实际的嵌入服务

training_service = VannaTrainingService(
    vector_store=vector_store,
    embedding_service=embedding_service
)

# 训练DDL语句
ddl_statements = [
    "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(255))",
    "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, amount DECIMAL(10,2))"
]
training_service.train_ddl(ddl_statements, "ecommerce_db")

# 训练问答对
qa_pairs = [
    {"question": "显示所有用户", "sql": "SELECT * FROM users"},
    {"question": "统计订单总数", "sql": "SELECT COUNT(*) FROM orders"}
]
training_service.train_qa_pairs(qa_pairs, "ecommerce_db")
```

### 3. 增强型RAG检索使用

```python
from services.enhanced_rag_retriever import EnhancedRAGRetriever, RetrievalConfig, RetrievalStrategy

# 创建检索器配置
config = RetrievalConfig(
    similarity_threshold=0.7,
    max_examples_per_type=3,
    enable_quality_filter=True,
    strategy=RetrievalStrategy.BALANCED
)

# 创建检索器
retriever = EnhancedRAGRetriever(vector_store, embedding_service, config)

# 检索相关上下文
context = retriever.retrieve_context("显示所有用户", "ecommerce_db")

# 生成增强提示词
schema_info = "Table: users (id, name, email)"
prompt = retriever.build_enhanced_prompt("显示所有用户", context, schema_info)
```

### 4. LLM服务使用

```python
from services.llm_service import llm_service

# 查询分解
response = llm_service.decompose_query(
    query="显示每个分类中销量最高的产品",
    schema_info="# Table: products\n[id, name, category, price]\n# Table: sales\n[id, product_id, quantity]",
    evidence="需要关联产品表和销售表"
)

if response.success:
    json_result = llm_service.extract_json_from_response(response.content)
    sub_questions = json_result.get("sub_questions", [])
    print(f"分解的子问题: {sub_questions}")

# SQL生成
sql_response = llm_service.generate_sql(
    query="显示所有活跃用户",
    sub_questions=["显示所有活跃用户"],
    schema_info="# Table: users\n[id, name, email, status]",
    use_cot=False
)

if sql_response.success:
    sql = llm_service.extract_sql_from_response(sql_response.content)
    print(f"生成的SQL: {sql}")
```

### 5. Decomposer智能体使用

```python
from agents.decomposer_agent import DecomposerAgent
from utils.models import ChatMessage

# 创建Decomposer智能体
decomposer = DecomposerAgent(
    agent_name="MyDecomposer",
    dataset_name="generic"  # 支持 "bird", "spider", "generic"
)

# 创建查询消息
message = ChatMessage(
    db_id="ecommerce_db",
    query="显示每个分类中销量最高的产品及其详细信息",
    desc_str="# Table: products\n[id, name, category, price]\n# Table: sales\n[id, product_id, quantity]",
    fk_str="products.id = sales.product_id",
    evidence="需要关联产品表和销售表进行统计分析"
)

# 处理查询
response = decomposer.talk(message)

if response.success:
    print(f"生成的SQL: {response.message.final_sql}")
    print(f"子问题数量: {response.metadata['sub_questions_count']}")
    print(f"RAG增强: {response.metadata['rag_enhanced']}")
    print(f"下一个智能体: {response.message.send_to}")
else:
    print(f"处理失败: {response.error}")

# 获取统计信息
stats = decomposer.get_decomposition_stats()
print(f"总查询数: {stats['total_queries']}")
print(f"复杂查询比例: {stats['complex_queries'] / stats['total_queries']:.2%}")
print(f"RAG增强率: {stats['rag_enhancement_rate']:.2%}")
```

### 6. Refiner智能体使用

```python
from agents.refiner_agent import RefinerAgent
from utils.models import ChatMessage
from services.llm_service import LLMService
from storage.mysql_adapter import MySQLAdapter

# 创建Refiner智能体
llm_service = LLMService()
mysql_adapter = MySQLAdapter()  # 可选，用于MySQL数据库

refiner = RefinerAgent(
    data_path="/path/to/databases",
    dataset_name="production",
    llm_service=llm_service,
    mysql_adapter=mysql_adapter
)

# 创建包含SQL的消息
message = ChatMessage(
    db_id="ecommerce_db",
    query="显示所有活跃用户及其订单数量",
    final_sql="SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.status = 'active' GROUP BY u.id",
    desc_str="users(id, name, status), orders(id, user_id, amount)",
    fk_str="users.id = orders.user_id"
)

# 处理SQL验证和执行
response = refiner.talk(message)

if response.success:
    print(f"SQL执行成功")
    print(f"执行时间: {response.message.execution_result['execution_time']:.3f}s")
    print(f"结果行数: {len(response.message.execution_result['data'])}")
    if response.message.fixed:
        print(f"SQL已修正: {response.message.final_sql}")
else:
    print(f"执行失败: {response.error}")

# 获取统计信息
stats = refiner.get_stats()
print(f"验证次数: {stats['validation_count']}")
print(f"修正率: {stats['refinement_rate']:.2%}")
print(f"安全违规率: {stats['security_violation_rate']:.2%}")
```

### 7. 提示词管理系统使用

```python
from utils.prompts import (
    prompt_manager,
    get_selector_schema_analysis_prompt,
    get_decomposer_query_decomposition_prompt,
    get_refiner_validation_prompt
)

# 基本使用
template = prompt_manager.get_prompt("selector", "schema_analysis")
system_prompt, user_prompt = prompt_manager.format_prompt(
    "selector", "schema_analysis",
    db_id="ecommerce_db",
    schema_info="CREATE TABLE users...",
    table_count=5,
    total_columns=25,
    avg_columns=5.0
)

# 便捷函数使用
system_prompt, user_prompt = get_decomposer_query_decomposition_prompt(
    query="显示所有活跃用户的订单信息",
    schema_info="database schema",
    evidence="additional context"
)

# 在智能体中集成
class CustomAgent:
    def process_query(self, query: str, schema_info: str):
        system_prompt, user_prompt = get_selector_schema_analysis_prompt(
            db_id="test_db",
            schema_info=schema_info,
            table_count=10,
            total_columns=50,
            avg_columns=5.0
        )
        
        # 调用LLM服务
        response = llm_service.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        return response
```

## 完整示例

### 端到端查询处理

```python
import asyncio
from agents.selector_agent import SelectorAgent
from agents.decomposer_agent import DecomposerAgent
from agents.refiner_agent import RefinerAgent
from agents.base_agent import MessageRouter
from utils.models import ChatMessage
from services.llm_service import LLMService

async def process_query():
    # 创建消息路由器
    router = MessageRouter()
    
    # 创建智能体
    selector = SelectorAgent("Selector", router=router)
    decomposer = DecomposerAgent("Decomposer", dataset_name="generic", router=router)
    refiner = RefinerAgent(
        data_path="/path/to/databases",
        dataset_name="production",
        llm_service=LLMService()
    )
    
    # 创建查询消息
    message = ChatMessage(
        db_id="ecommerce_db",
        query="显示每个分类中销量最高的产品及其详细信息",
        send_to="Selector"
    )
    
    # 步骤1: Selector处理
    response = selector.process_message(message)
    
    if response.success:
        print("✅ Selector处理成功")
        print(f"模式是否裁剪: {response.message.pruned}")
        
        # 步骤2: Decomposer处理
        decomposer_response = decomposer.process_message(response.message)
        
        if decomposer_response.success:
            print("✅ Decomposer处理成功")
            print(f"生成的SQL: {decomposer_response.message.final_sql}")
            print(f"子问题数量: {decomposer_response.metadata.get('sub_questions_count', 0)}")
            print(f"RAG增强: {decomposer_response.metadata.get('rag_enhanced', False)}")
            
            # 步骤3: Refiner处理
            refiner_response = refiner.process_message(decomposer_response.message)
            
            if refiner_response.success:
                print("✅ Refiner处理成功")
                print(f"SQL执行成功: {refiner_response.message.execution_result['is_successful']}")
                print(f"执行时间: {refiner_response.message.execution_result['execution_time']:.3f}s")
                if refiner_response.message.fixed:
                    print(f"SQL已修正: {refiner_response.message.final_sql}")
                print(f"处理完成: {refiner_response.message.send_to}")
            else:
                print(f"❌ Refiner处理失败: {refiner_response.error}")
        else:
            print(f"❌ Decomposer处理失败: {decomposer_response.error}")
        
    else:
        print(f"❌ Selector处理失败: {response.error}")

# 运行示例
asyncio.run(process_query())
```

## 配置调优

### 1. Selector智能体配置

```python
# 更新裁剪配置
selector.update_pruning_config(
    token_limit=50000,           # 增加token限制
    avg_column_threshold=10,     # 提高列数阈值
    total_column_threshold=50,   # 提高总列数阈值
    enable_foreign_key_analysis=True,  # 启用外键分析
    enable_semantic_pruning=True       # 启用语义裁剪
)
```

### 2. Decomposer智能体配置

```python
# 更新分解配置
decomposer.update_config(
    max_sub_questions=3,         # 限制子问题数量
    enable_cot_reasoning=True,   # 启用CoT推理
    enable_rag_enhancement=True, # 启用RAG增强
    temperature=0.2              # 调整LLM温度
)

# 切换数据集类型
decomposer.switch_dataset("bird")  # 或 "spider", "generic"

# 设置RAG检索器
from services.enhanced_rag_retriever import EnhancedRAGRetriever
rag_retriever = EnhancedRAGRetriever(vector_store, embedding_service)
decomposer.set_rag_retriever(rag_retriever)
```

### 3. RAG检索器配置

```python
# 动态更新检索配置
retriever.update_config(
    similarity_threshold=0.8,    # 提高相似度要求
    max_examples_per_type=5,     # 增加示例数量
    strategy=RetrievalStrategy.QA_FOCUSED  # 切换到QA重点策略
)
```

## 监控和调试

### 1. 启用详细日志

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 或者只为特定组件启用调试
logging.getLogger("Agent.Selector").setLevel(logging.DEBUG)
```

### 2. 性能监控

```python
# 获取智能体性能统计
stats = selector.get_stats()
print(f"平均执行时间: {stats['average_execution_time']:.3f}s")
print(f"成功率: {stats['success_rate']:.2%}")

# 获取裁剪效果统计
pruning_stats = selector.get_pruning_stats()
print(f"裁剪比例: {pruning_stats['avg_pruning_ratio']:.2%}")
```

### 3. 错误处理

```python
try:
    response = selector.talk(message)
    if not response.success:
        print(f"处理失败: {response.error}")
        # 实施重试或降级策略
except Exception as e:
    print(f"系统异常: {e}")
    # 记录错误日志，触发告警
```

## 测试验证

### 1. 运行单元测试

```bash
# 运行所有测试
pytest tests/unit/ -v

# 运行特定组件测试
pytest tests/unit/test_selector_agent.py -v

# 运行测试并生成覆盖率报告
pytest tests/unit/ --cov=. --cov-report=html
```

### 2. 运行示例脚本

```bash
# 运行Selector智能体示例
python examples/selector_agent_example.py

# 运行训练服务示例
python examples/vanna_training_service_example.py

# 运行RAG检索示例
python examples/enhanced_rag_retriever_example.py
```

## 常见问题

### Q: 如何处理大型数据库的模式裁剪？
A: 调整`token_limit`和列数阈值，启用语义裁剪功能，使用更严格的相似度过滤。

### Q: 如何提高查询处理的准确性？
A: 增加训练数据，特别是高质量的问答对；调整检索策略；优化相似度阈值。

### Q: 如何处理多数据库环境？
A: 为每个数据库配置独立的`db_id`，使用统一的智能体实例处理不同数据库的查询。

### Q: 如何监控系统性能？
A: 使用内置的统计功能，定期检查智能体和裁剪统计；集成外部监控系统收集指标。

## 下一步

1. **扩展功能**: 尝试添加新的数据源支持或裁剪策略
2. **性能优化**: 根据实际使用情况调整配置参数
3. **集成测试**: 在真实数据库环境中验证系统功能
4. **生产部署**: 配置监控、日志和告警系统

更多详细信息请参考：
- [Selector智能体详细文档](selector_agent.md)
- [提示词管理系统文档](prompts_system.md)
- [测试和质量保证](testing_and_quality.md)
- [项目示例代码](../examples/)
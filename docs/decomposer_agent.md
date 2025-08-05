# Decomposer智能体详细文档

## 概述

Decomposer智能体是Text2SQL多智能体系统中的核心组件，负责查询分解和SQL生成。基于MAC-SQL策略和Chain of Thought (CoT) 方法，它能够智能地将复杂的自然语言查询分解为逻辑子问题，并生成高质量的SQL语句。

## 核心功能

### 1. 智能查询分解

#### 复杂度分析
- **自动复杂度评估**: 基于8个维度的复杂度指标分析查询难度
- **智能分解决策**: 简单查询直接处理，复杂查询进行分解
- **多层次分析**: 聚合、分组、过滤、排序、连接、比较、时间、多实体分析

#### 分解策略
- **LLM驱动分解**: 使用大语言模型进行智能查询分解
- **结构化输出**: 生成JSON格式的子问题列表和推理过程
- **后备机制**: LLM失败时自动降级到原始查询处理

### 2. Chain of Thought (CoT) SQL生成

#### 生成模式
- **简单模式**: 单一子问题直接生成SQL
- **CoT模式**: 多子问题渐进式SQL构建
- **上下文感知**: 结合数据库模式和外键关系信息

#### 智能优化
- **模板驱动**: 使用集中化的提示词模板系统
- **参数化配置**: 支持温度、最大token等参数调整
- **错误恢复**: 生成失败时提供基础SQL后备方案

### 3. 多数据集适配

#### 支持的数据集
- **BIRD**: 业务导向的复杂查询数据集，注重上下文理解
- **Spider**: 学术研究导向的跨域查询数据集，注重SQL模式
- **Generic**: 通用查询处理，平衡各种查询类型

#### 自适应策略
- **动态配置**: 根据数据集类型自动调整处理策略
- **检索策略**: 不同数据集使用不同的RAG检索策略
- **提示词优化**: 针对数据集特点优化提示词模板

### 4. RAG增强机制

#### 检索策略
- **BIRD数据集**: 使用CONTEXT_FOCUSED策略，重点检索业务上下文
- **Spider数据集**: 使用SQL_FOCUSED策略，重点检索SQL模式
- **Generic数据集**: 使用BALANCED策略，平衡各类信息

#### 上下文利用
- **历史示例**: 利用相似的问题-SQL对提高生成准确性
- **SQL模式**: 参考相关的SQL查询模式
- **业务知识**: 整合领域知识和文档信息

## 技术实现

### 核心类结构

```python
class DecomposerAgent(BaseAgent):
    """Decomposer智能体主类"""
    
    def __init__(self, agent_name: str = "Decomposer", 
                 dataset_name: str = "generic",
                 rag_retriever: Optional[EnhancedRAGRetriever] = None):
        # 初始化智能体
        
    def talk(self, message: ChatMessage) -> AgentResponse:
        # 处理查询分解和SQL生成的主要接口
```

### 组件架构

#### QueryDecomposer (查询分解器)
```python
class QueryDecomposer:
    def decompose_query(self, query: str, schema_info: str, evidence: str = "") -> List[str]:
        # 查询分解主方法
        
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        # 复杂度分析
```

#### SQLGenerator (SQL生成器)
```python
class SQLGenerator:
    def generate_sql_steps(self, sub_questions: List[str], schema_info: str, 
                          fk_info: str, context: Dict[str, List]) -> str:
        # SQL生成主方法
        
    def _generate_simple_sql(self, question: str, ...) -> str:
        # 简单SQL生成
        
    def _generate_cot_sql(self, sub_questions: List[str], ...) -> str:
        # CoT SQL生成
```

### 配置系统

```python
@dataclass
class DecompositionConfig:
    """查询分解配置"""
    max_sub_questions: int = 5              # 最大子问题数量
    enable_cot_reasoning: bool = True       # 启用CoT推理
    enable_rag_enhancement: bool = True     # 启用RAG增强
    dataset_type: DatasetType = DatasetType.GENERIC
    temperature: float = 0.1                # LLM温度参数
    max_tokens: int = 2000                  # 最大token数
```

## 复杂度分析算法

### 分析维度

1. **聚合分析** (`has_aggregation`): 检测count, sum, avg等聚合函数
2. **分组分析** (`has_grouping`): 检测group by, each, per等分组关键词
3. **过滤分析** (`has_filtering`): 检测where, filter, only等过滤条件
4. **排序分析** (`has_sorting`): 检测order, sort, top等排序关键词
5. **连接分析** (`has_joining`): 检测多表关联的关键词
6. **比较分析** (`has_comparison`): 检测比较操作符和关键词
7. **时间分析** (`has_temporal`): 检测时间相关的查询条件
8. **多实体分析** (`has_multiple_entities`): 检测涉及多个数据实体

### 复杂度评分

- **简单查询**: 复杂度分数 ≤ 2，直接生成SQL
- **复杂查询**: 复杂度分数 ≥ 4，进行查询分解
- **中等查询**: 复杂度分数 3，根据具体情况处理

## 使用示例

### 基本使用

```python
from agents.decomposer_agent import DecomposerAgent
from utils.models import ChatMessage

# 创建Decomposer智能体
decomposer = DecomposerAgent(
    agent_name="MyDecomposer",
    dataset_name="generic"
)

# 创建查询消息
message = ChatMessage(
    db_id="ecommerce_db",
    query="显示每个分类中销量最高的产品及其详细信息",
    desc_str="# Table: products\n[id, name, category, price]\n# Table: sales\n[id, product_id, quantity]",
    fk_str="products.id = sales.product_id"
)

# 处理查询
response = decomposer.talk(message)

if response.success:
    print(f"生成的SQL: {response.message.final_sql}")
    print(f"子问题数量: {response.metadata['sub_questions_count']}")
    print(f"RAG增强: {response.metadata['rag_enhanced']}")
```

### 高级配置

```python
# 更新配置
decomposer.update_config(
    max_sub_questions=3,
    enable_cot_reasoning=True,
    temperature=0.2
)

# 切换数据集
decomposer.switch_dataset("bird")

# 设置RAG检索器
from services.enhanced_rag_retriever import EnhancedRAGRetriever
rag_retriever = EnhancedRAGRetriever(vector_store, embedding_service)
decomposer.set_rag_retriever(rag_retriever)
```

### 统计监控

```python
# 获取分解统计
stats = decomposer.get_decomposition_stats()
print(f"总查询数: {stats['total_queries']}")
print(f"复杂查询比例: {stats['complex_queries'] / stats['total_queries']:.2%}")
print(f"平均子问题数: {stats['avg_sub_questions']:.1f}")
print(f"RAG增强率: {stats['rag_enhancement_rate']:.2%}")

# 重置统计
decomposer.reset_decomposition_stats()
```

## 性能特性

### 查询处理效率

- **智能分解**: 只对复杂查询进行分解，简单查询直接处理
- **并行优化**: 支持多个子问题的并行处理
- **缓存机制**: 利用LLM服务的缓存机制提高响应速度

### 生成质量

- **上下文感知**: 充分利用数据库模式和外键关系信息
- **历史学习**: 通过RAG检索利用历史成功案例
- **错误恢复**: 多层次的后备机制确保始终有输出

### 适应性

- **数据集特化**: 针对不同数据集优化处理策略
- **动态配置**: 支持运行时参数调整
- **扩展性**: 易于添加新的数据集支持和处理策略

## 集成接口

### 与Selector智能体集成

```python
# 接收Selector处理后的消息
message.desc_str  # 数据库模式描述
message.fk_str    # 外键关系信息
message.pruned    # 是否经过模式裁剪
```

### 与Refiner智能体集成

```python
# 发送给Refiner的信息
message.final_sql    # 生成的SQL语句
message.qa_pairs     # QA对信息
message.send_to = "Refiner"  # 路由到Refiner
```

### 与LLM服务集成

```python
# 使用统一的LLM服务接口
from services.llm_service import llm_service

# 查询分解
llm_response = llm_service.generate_completion(
    prompt=user_prompt,
    system_prompt=system_prompt,
    temperature=self.config.temperature
)

# SQL生成
sql_response = llm_service.generate_completion(
    prompt=sql_prompt,
    system_prompt=sql_system_prompt,
    max_tokens=self.config.max_tokens
)
```

## 测试覆盖

### 单元测试 (tests/unit/test_decomposer_agent.py)

- **QueryDecomposer测试**: 复杂度分析、查询分解、LLM集成
- **SQLGenerator测试**: 简单SQL生成、CoT SQL生成、后备机制
- **DecomposerAgent测试**: 完整流程、配置管理、统计跟踪

### 集成测试

- **端到端测试**: 完整的查询处理流程
- **多数据集测试**: BIRD、Spider、Generic数据集兼容性
- **RAG集成测试**: 与增强型RAG检索器的协作

## 最佳实践

### 配置优化

- **数据集选择**: 根据实际查询类型选择合适的数据集配置
- **参数调优**: 根据LLM性能调整温度和token限制
- **RAG策略**: 根据业务需求选择合适的检索策略

### 性能调优

- **批量处理**: 对于相似查询，复用分解结果
- **缓存利用**: 充分利用LLM服务的缓存机制
- **监控指标**: 定期检查分解统计，优化处理策略

### 错误处理

- **降级策略**: 当分解失败时，使用原始查询
- **日志记录**: 详细记录分解过程，便于问题诊断
- **重试机制**: 对于临时性LLM错误实施重试

## 扩展性

### 新数据集支持

- **枚举扩展**: 在DatasetType中添加新的数据集类型
- **策略配置**: 为新数据集配置专门的处理策略
- **提示词优化**: 针对新数据集特点优化提示词模板

### 新分解算法

- **算法插件**: 支持添加新的查询分解算法
- **策略模式**: 使用策略模式支持多种分解方法
- **A/B测试**: 支持不同算法的效果对比

## 故障排除

### 常见问题

1. **分解失败**: 检查LLM服务连接和提示词格式
2. **SQL生成错误**: 验证数据库模式信息和外键关系
3. **RAG检索异常**: 确保向量数据库连接正常
4. **配置不生效**: 检查配置更新后是否重新初始化组件

### 调试技巧

- **启用详细日志**: 设置日志级别为DEBUG
- **统计信息分析**: 使用get_decomposition_stats()分析处理效果
- **手动测试**: 使用示例脚本验证各个组件功能
- **性能分析**: 监控处理时间和成功率

## 未来发展

### 计划功能

- **多模态支持**: 支持图表和表格的查询理解
- **增量学习**: 基于用户反馈持续优化分解策略
- **并行处理**: 支持子问题的并行SQL生成
- **可视化界面**: 提供查询分解过程的可视化展示

### 性能提升

- **模型微调**: 针对特定领域微调查询分解模型
- **缓存优化**: 实现分解结果的智能缓存
- **批处理**: 支持批量查询的高效处理
- **分布式处理**: 支持分布式环境下的查询分解
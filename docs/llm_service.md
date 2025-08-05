# LLM服务详细文档

## 概述

LLM服务（`services/llm_service.py`）是Text2SQL多智能体系统的核心语言模型调用服务，提供统一的LLM接口，支持查询分解、SQL生成和上下文增强功能。该服务与OpenAI API深度集成，为Decomposer智能体提供强大的自然语言处理能力。

## 核心功能

### 1. LLMService 主要服务类

#### 核心特性
- **统一接口**: 标准化的LLM调用接口，支持多种OpenAI模型
- **灵活配置**: 支持自定义模型名称、API密钥和基础URL
- **查询分解**: 智能将复杂自然语言查询分解为子问题
- **SQL生成**: 支持简单SQL生成和基于CoT的复杂SQL生成
- **上下文集成**: 与RAG检索器深度集成，利用检索上下文增强生成质量
- **错误处理**: 完善的异常处理和响应包装机制

#### 关键方法
```python
class LLMService:
    def generate_completion(self, prompt: str, temperature: float = 0.1, 
                          max_tokens: int = 2000, system_prompt: Optional[str] = None) -> LLMResponse
    def decompose_query(self, query: str, schema_info: str, evidence: str = "", 
                       complexity_info: Optional[Dict] = None) -> LLMResponse
    def generate_sql(self, query: str, sub_questions: List[str], schema_info: str, 
                    fk_info: str = "", context: Optional[Dict[str, List]] = None,
                    use_cot: bool = True) -> LLMResponse
    def extract_json_from_response(self, response_content: str) -> Optional[Dict]
    def extract_sql_from_response(self, response_content: str) -> str
```

### 2. LLMResponse 响应包装器

#### 数据结构
```python
@dataclass
class LLMResponse:
    content: str                        # 生成的内容
    success: bool                       # 是否成功
    error: Optional[str] = None         # 错误信息
    usage: Optional[Dict[str, Any]] = None  # Token使用统计
    model: Optional[str] = None         # 使用的模型名称
```

## 技术特性

### 1. 查询分解功能

#### 智能分解策略
- **复杂度感知**: 基于查询复杂度信息进行智能分解
- **结构化输出**: 返回JSON格式的子问题列表和推理过程
- **上下文理解**: 结合数据库模式和证据信息进行分解
- **逻辑流程**: 确保子问题的逻辑顺序和完整性

#### 分解提示词模板
```python
system_prompt = """You are an expert at analyzing natural language database queries and breaking them down into logical sub-steps.

Guidelines:
1. Break the question into logical sub-steps
2. Each sub-question should be answerable with a single SQL query
3. Maintain the logical flow from simple to complex
4. Ensure all sub-questions contribute to answering the original question
5. For simple queries, you may return just the original question

Output format: JSON object with sub_questions and reasoning"""
```

### 2. SQL生成功能

#### 双模式生成
- **简单SQL生成**: 直接从自然语言生成SQL查询
- **CoT SQL生成**: 基于Chain of Thought方法的分步SQL构建
- **上下文增强**: 利用RAG检索的SQL示例和QA对
- **模式感知**: 基于数据库模式信息生成准确的SQL

#### 生成策略选择
```python
def generate_sql(self, query: str, sub_questions: List[str], schema_info: str, 
                fk_info: str = "", context: Optional[Dict[str, List]] = None,
                use_cot: bool = True) -> LLMResponse:
    if use_cot and len(sub_questions) > 1:
        return self._generate_cot_sql(query, sub_questions, schema_info, fk_info, context)
    else:
        return self._generate_simple_sql(query, schema_info, fk_info, context)
```

### 3. 上下文集成

#### RAG上下文利用
- **SQL示例集成**: 将相似的SQL示例嵌入到提示词中
- **QA对增强**: 优先使用高质量的问题-SQL对（分数≥0.8）
- **模式信息**: 充分利用数据库模式和外键关系信息
- **智能过滤**: 自动选择最相关的上下文信息

#### 上下文构建示例
```python
# 添加RAG上下文
if context:
    if context.get("sql_examples"):
        prompt_parts.extend([
            "**Similar SQL Examples:**",
            ""
        ])
        for i, sql in enumerate(context["sql_examples"][:2], 1):
            prompt_parts.extend([
                f"Example {i}:",
                f"```sql",
                sql.strip(),
                f"```",
                ""
            ])
```

### 4. 响应处理

#### JSON提取
- **智能解析**: 从LLM响应中提取JSON对象
- **容错处理**: 支持部分JSON和格式化问题的处理
- **错误恢复**: 解析失败时返回None而不是抛出异常

#### SQL清理
- **格式清理**: 移除Markdown代码块标记
- **注释过滤**: 过滤SQL注释和说明文字
- **空行处理**: 清理多余的空行和空格

## 配置和初始化

### 环境变量配置
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL_NAME="gpt-4"  # 可选，默认为gpt-4
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
```

### 服务初始化
```python
# 使用默认配置
llm_service = LLMService()

# 自定义配置
llm_service = LLMService(
    model_name="gpt-3.5-turbo",
    api_key="custom-api-key",
    base_url="https://custom-endpoint.com/v1"
)
```

## 使用示例

### 基本查询分解
```python
from services.llm_service import llm_service

# 查询分解
response = llm_service.decompose_query(
    query="显示每个分类中销量最高的产品及其详细信息",
    schema_info="# Table: products\n[id, name, category, price]\n# Table: sales\n[id, product_id, quantity]",
    evidence="需要关联产品表和销售表",
    complexity_info={
        "score": 6,
        "indicators": {
            "has_aggregation": True,
            "has_grouping": True,
            "has_joining": True
        }
    }
)

if response.success:
    json_result = llm_service.extract_json_from_response(response.content)
    sub_questions = json_result.get("sub_questions", [])
    print(f"分解的子问题: {sub_questions}")
```

### SQL生成
```python
# 简单SQL生成
response = llm_service.generate_sql(
    query="显示所有活跃用户",
    sub_questions=["显示所有活跃用户"],
    schema_info="# Table: users\n[id, name, email, status]",
    fk_info="",
    context={
        "sql_examples": ["SELECT * FROM users WHERE active = 1"],
        "qa_pairs": [
            {"question": "显示用户", "sql": "SELECT * FROM users", "score": 0.9}
        ]
    },
    use_cot=False
)

if response.success:
    sql = llm_service.extract_sql_from_response(response.content)
    print(f"生成的SQL: {sql}")
```

### CoT SQL生成
```python
# 复杂查询的CoT生成
sub_questions = [
    "找到每个产品分类",
    "计算每个分类的销量",
    "找到每个分类中销量最高的产品",
    "获取产品详细信息"
]

response = llm_service.generate_sql(
    query="显示每个分类中销量最高的产品及其详细信息",
    sub_questions=sub_questions,
    schema_info="# Table: products\n[id, name, category, price]\n# Table: sales\n[id, product_id, quantity]",
    fk_info="products.id = sales.product_id",
    context=context,
    use_cot=True
)
```

## 与Decomposer智能体的集成

### 集成方式
```python
# 在Decomposer智能体中使用
from services.llm_service import llm_service

class DecomposerAgent(BaseAgent):
    def _decompose_query(self, query: str, schema_info: str, evidence: str = "") -> List[str]:
        # 分析查询复杂度
        complexity = self._analyze_query_complexity(query)
        
        # 调用LLM服务进行分解
        response = llm_service.decompose_query(query, schema_info, evidence, complexity)
        
        if response.success:
            json_result = llm_service.extract_json_from_response(response.content)
            if json_result and "sub_questions" in json_result:
                return json_result["sub_questions"]
        
        # 降级到规则分解
        return self._rule_based_decompose(query, complexity)
    
    def _generate_sql_steps(self, sub_questions: List[str], schema_info: str, 
                          fk_info: str, context: Dict[str, List]) -> str:
        # 调用LLM服务生成SQL
        response = llm_service.generate_sql(
            query=self.current_query,
            sub_questions=sub_questions,
            schema_info=schema_info,
            fk_info=fk_info,
            context=context,
            use_cot=self.config.enable_cot_reasoning
        )
        
        if response.success:
            return llm_service.extract_sql_from_response(response.content)
        
        # 降级到模板生成
        return self._template_based_sql_generation(sub_questions, schema_info)
```

## 性能特性

### 1. 响应时间优化
- **温度控制**: 默认使用0.1的低温度确保输出稳定性
- **Token限制**: 合理的token限制平衡质量和速度
- **超时控制**: 30秒的API调用超时防止长时间等待

### 2. 错误处理
- **异常捕获**: 完整的异常处理机制
- **降级策略**: LLM调用失败时的降级处理
- **日志记录**: 详细的调用日志和错误信息

### 3. 资源管理
- **连接复用**: OpenAI客户端的连接复用
- **内存效率**: 合理的响应数据结构设计
- **配置缓存**: 服务配置的高效缓存

## 测试覆盖

### 单元测试（预期）
- **LLMService初始化测试**: 验证服务正确初始化
- **查询分解测试**: 测试各种复杂度的查询分解
- **SQL生成测试**: 测试简单和CoT SQL生成
- **响应处理测试**: 测试JSON和SQL提取功能
- **错误处理测试**: 测试异常情况的处理

### 集成测试
- **与Decomposer集成**: 验证与智能体的集成效果
- **RAG上下文集成**: 测试上下文信息的有效利用
- **端到端测试**: 完整的查询处理流程测试

## 最佳实践

### 1. 配置优化
- **模型选择**: 根据需求选择合适的OpenAI模型
- **温度设置**: 对于SQL生成建议使用较低温度（0.1-0.2）
- **Token限制**: 根据查询复杂度调整最大token数

### 2. 错误处理
- **重试机制**: 对于临时性错误实施重试
- **降级策略**: 准备基于规则的后备方案
- **日志监控**: 监控API调用成功率和响应时间

### 3. 成本控制
- **Token优化**: 优化提示词长度减少token消耗
- **缓存策略**: 对相似查询实施缓存
- **批量处理**: 合理批量处理减少API调用次数

## 扩展性

### 1. 多模型支持
- **模型切换**: 支持动态切换不同的LLM模型
- **提供商扩展**: 可扩展支持其他LLM提供商
- **本地模型**: 支持本地部署的开源模型

### 2. 功能扩展
- **新任务类型**: 支持添加新的NLP任务
- **自定义提示词**: 支持用户自定义提示词模板
- **多语言支持**: 扩展支持多种自然语言

## 故障排除

### 常见问题
1. **API密钥错误**: 检查OPENAI_API_KEY环境变量
2. **网络连接问题**: 验证网络连接和API端点
3. **Token限制**: 调整max_tokens参数
4. **响应解析失败**: 检查LLM响应格式

### 调试技巧
- **启用详细日志**: 设置日志级别为DEBUG
- **响应检查**: 检查原始LLM响应内容
- **提示词优化**: 调整提示词模板提高成功率
- **参数调优**: 调整温度和token限制参数

## 未来发展

### 计划功能
- **流式响应**: 支持流式API调用减少延迟
- **批量处理**: 支持批量查询处理
- **模型微调**: 支持针对特定领域的模型微调
- **性能监控**: 集成详细的性能监控和分析

### 技术改进
- **提示词优化**: 基于使用数据优化提示词模板
- **缓存策略**: 实现智能的响应缓存机制
- **负载均衡**: 支持多个API端点的负载均衡
- **成本优化**: 实现更精细的成本控制和优化
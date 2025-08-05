# 提示词管理系统文档

## 概述

提示词管理系统 (`utils/prompts.py`) 是Text2SQL多智能体服务的核心组件，提供集中化、结构化的提示词模板管理。该系统确保所有智能体使用一致、高质量的提示词，并支持动态参数化和模板格式化。

## 核心特性

### 1. 集中化管理
- **统一存储**: 所有提示词模板集中存储在一个文件中
- **分类组织**: 按智能体类型（Selector、Decomposer、Refiner）和功能分类
- **版本控制**: 便于跟踪提示词的变更历史
- **维护性**: 统一的修改入口，避免重复和不一致

### 2. 结构化模板
- **系统提示**: 定义智能体的角色和基本行为准则
- **用户提示模板**: 包含参数占位符的用户输入模板
- **参数验证**: 自动检查必需参数是否提供
- **格式化支持**: 支持Python字符串格式化语法

### 3. 智能体专用提示词
- **Selector智能体**: 模式分析和裁剪相关提示词
- **Decomposer智能体**: 查询分解和SQL生成提示词
- **Refiner智能体**: SQL验证和修正提示词
- **通用提示词**: 跨智能体共享的通用模板

## 架构设计

### 核心类结构

```python
@dataclass
class PromptTemplate:
    """提示词模板数据结构"""
    system_prompt: str          # 系统提示词
    user_prompt_template: str   # 用户提示词模板
    description: str            # 模板描述
    parameters: List[str]       # 必需参数列表

class PromptManager:
    """提示词管理器"""
    def get_prompt(self, agent: str, prompt_type: str) -> PromptTemplate
    def format_prompt(self, agent: str, prompt_type: str, **kwargs) -> tuple[str, str]
```

### 模板组织结构

```
prompts/
├── selector/
│   ├── schema_analysis      # 模式分析提示词
│   └── schema_pruning       # 模式裁剪提示词
├── decomposer/
│   ├── query_decomposition  # 查询分解提示词
│   ├── simple_sql_generation # 简单SQL生成提示词
│   └── cot_sql_generation   # CoT SQL生成提示词
├── refiner/
│   ├── sql_validation       # SQL验证提示词
│   └── sql_refinement       # SQL修正提示词
└── common/
    └── context_builder      # 通用上下文构建提示词
```

## 使用方法

### 1. 基本使用

```python
from utils.prompts import prompt_manager

# 获取提示词模板
template = prompt_manager.get_prompt("selector", "schema_analysis")

# 格式化提示词
system_prompt, user_prompt = prompt_manager.format_prompt(
    "selector", "schema_analysis",
    db_id="ecommerce_db",
    schema_info="CREATE TABLE users...",
    table_count=5,
    total_columns=25,
    avg_columns=5.0
)
```

### 2. 便捷函数使用

```python
from utils.prompts import (
    get_selector_schema_analysis_prompt,
    get_decomposer_query_decomposition_prompt,
    get_refiner_validation_prompt
)

# Selector模式分析
system_prompt, user_prompt = get_selector_schema_analysis_prompt(
    db_id="test_db",
    schema_info="schema information",
    table_count=10,
    total_columns=50,
    avg_columns=5.0
)

# Decomposer查询分解
system_prompt, user_prompt = get_decomposer_query_decomposition_prompt(
    query="显示所有活跃用户的订单信息",
    schema_info="database schema",
    evidence="additional context"
)

# Refiner SQL验证
system_prompt, user_prompt = get_refiner_validation_prompt(
    sql_query="SELECT * FROM users",
    schema_info="schema info",
    original_query="show all users"
)
```

### 3. 在智能体中集成

```python
from utils.prompts import get_decomposer_simple_sql_prompt
from services.llm_service import llm_service

class DecomposerAgent:
    def generate_sql(self, query: str, schema_info: str, context: Dict):
        # 获取格式化的提示词
        system_prompt, user_prompt = get_decomposer_simple_sql_prompt(
            query=query,
            schema_info=schema_info,
            context=context
        )
        
        # 调用LLM服务
        response = llm_service.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        return response
```

## 提示词模板详解

### 1. Selector智能体提示词

#### 模式分析提示词 (schema_analysis)
- **用途**: 分析数据库模式复杂度，判断是否需要裁剪
- **输入参数**: `db_id`, `schema_info`, `table_count`, `total_columns`, `avg_columns`
- **输出格式**: JSON格式的分析结果
- **特点**: 结构化分析，包含复杂度评分和裁剪建议

#### 模式裁剪提示词 (schema_pruning)
- **用途**: 基于查询相关性进行智能模式裁剪
- **输入参数**: `query`, `schema_info`, `fk_info`, `evidence`
- **输出格式**: JSON格式的裁剪决策
- **特点**: 保持外键关系，智能选择相关表和列

### 2. Decomposer智能体提示词

#### 查询分解提示词 (query_decomposition)
- **用途**: 将复杂查询分解为简单子问题
- **输入参数**: `query`, `schema_info`, `evidence_section`, `complexity_section`
- **输出格式**: JSON格式的子问题列表
- **特点**: 支持复杂度信息集成，逐步分解策略

#### 简单SQL生成提示词 (simple_sql_generation)
- **用途**: 生成简单的SQL查询
- **输入参数**: `query`, `schema_info`, `fk_section`, `context_section`
- **输出格式**: 纯SQL语句
- **特点**: 集成RAG上下文，遵循SQL最佳实践

#### CoT SQL生成提示词 (cot_sql_generation)
- **用途**: 使用链式思维生成复杂SQL
- **输入参数**: `original_query`, `sub_questions_list`, `schema_info`, `fk_section`, `context_section`
- **输出格式**: 复杂SQL语句
- **特点**: 步骤化推理，支持CTE和复杂连接

### 3. Refiner智能体提示词

#### SQL验证提示词 (sql_validation)
- **用途**: 验证SQL语法和逻辑正确性
- **输入参数**: `sql_query`, `schema_info`, `original_query`
- **输出格式**: JSON格式的验证结果
- **特点**: 多维度验证，包含安全性检查

#### SQL修正提示词 (sql_refinement)
- **用途**: 基于错误信息修正SQL查询
- **输入参数**: `original_sql`, `error_info`, `schema_info`, `original_query`, `context`
- **输出格式**: 修正后的SQL语句
- **特点**: 错误驱动修正，保持原始意图

## 上下文构建

### RAG上下文集成
系统自动将RAG检索到的上下文信息格式化为提示词的一部分：

```python
def _build_context_section(context: Optional[Dict[str, List]]) -> str:
    """构建上下文部分"""
    sections = []
    
    # SQL示例
    if context.get("sql_examples"):
        sections.append("**Similar SQL Examples:**")
        # 格式化SQL示例
    
    # 高质量QA对
    if context.get("qa_pairs"):
        high_quality_pairs = [p for p in context["qa_pairs"] if p.get("score", 0) >= 0.8]
        sections.append("**Similar Question-SQL Pairs:**")
        # 格式化QA对
    
    # 业务文档
    if context.get("documentation"):
        sections.append("**Business Context:**")
        # 格式化文档内容
    
    return "\n".join(sections)
```

### 动态参数处理
- **条件性内容**: 根据参数是否提供动态包含内容部分
- **格式化控制**: 自动处理空值和格式化问题
- **长度限制**: 自动截断过长的上下文内容

## 最佳实践

### 1. 提示词设计原则
- **清晰性**: 使用明确、具体的指令
- **结构化**: 采用一致的格式和结构
- **参数化**: 支持动态内容替换
- **可测试**: 便于验证和调试

### 2. 模板维护
- **版本控制**: 记录重要变更
- **测试验证**: 确保模板修改不影响功能
- **性能监控**: 跟踪提示词效果
- **文档同步**: 保持文档与代码同步

### 3. 扩展指南
- **新增智能体**: 在相应分类下添加新模板
- **新增功能**: 创建新的提示词类型
- **参数扩展**: 谨慎添加新参数，保持向后兼容
- **便捷函数**: 为常用模板提供便捷访问函数

## 性能优化

### 1. 模板缓存
- **内存缓存**: 模板在首次加载后缓存在内存中
- **延迟加载**: 按需加载特定智能体的模板
- **版本检查**: 支持模板热更新机制

### 2. 格式化优化
- **参数验证**: 提前验证必需参数
- **字符串优化**: 使用高效的字符串格式化方法
- **内存管理**: 避免不必要的字符串复制

### 3. 长度控制
- **智能截断**: 根据LLM上下文窗口限制截断内容
- **优先级排序**: 保留最重要的上下文信息
- **压缩策略**: 使用简洁的表达方式

## 错误处理

### 1. 参数验证
```python
# 检查必需参数
missing_params = [param for param in template.parameters if param not in kwargs]
if missing_params:
    raise ValueError(f"Missing required parameters: {missing_params}")
```

### 2. 模板验证
- **语法检查**: 验证模板语法正确性
- **参数匹配**: 确保所有占位符都有对应参数
- **格式验证**: 检查输出格式的一致性

### 3. 降级策略
- **默认模板**: 提供基础的默认模板
- **简化版本**: 在复杂模板失败时使用简化版本
- **错误记录**: 详细记录模板使用错误

## 监控和调试

### 1. 使用统计
- **调用频率**: 跟踪各模板的使用频率
- **成功率**: 监控模板格式化成功率
- **性能指标**: 测量格式化耗时

### 2. 效果评估
- **输出质量**: 评估生成内容的质量
- **一致性检查**: 确保输出格式一致
- **用户反馈**: 收集智能体使用反馈

### 3. 调试工具
- **模板预览**: 提供模板内容预览功能
- **参数检查**: 验证参数完整性
- **格式化测试**: 测试模板格式化结果

## 未来发展

### 1. 智能化增强
- **自适应模板**: 根据使用效果自动调整模板
- **A/B测试**: 支持多版本模板对比测试
- **机器学习优化**: 使用ML技术优化提示词效果

### 2. 多语言支持
- **国际化**: 支持多语言提示词模板
- **本地化**: 适配不同地区的表达习惯
- **动态切换**: 根据用户偏好切换语言

### 3. 可视化管理
- **Web界面**: 提供可视化的模板管理界面
- **在线编辑**: 支持在线编辑和预览
- **版本管理**: 可视化的版本控制和回滚

## 总结

提示词管理系统是Text2SQL多智能体服务的重要基础设施，通过集中化、结构化的管理方式，确保了系统的一致性、可维护性和扩展性。该系统不仅提高了开发效率，还为系统的持续优化和改进提供了坚实的基础。

通过合理使用提示词管理系统，开发者可以：
- 快速创建和修改智能体提示词
- 确保提示词的一致性和质量
- 便于进行A/B测试和效果优化
- 简化新智能体的开发过程
- 提高系统的整体可维护性

随着系统的不断发展，提示词管理系统将继续演进，为Text2SQL服务提供更强大、更智能的提示词支持。
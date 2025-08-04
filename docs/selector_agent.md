# Selector智能体详细文档 (MySQL版本)

## 概述

Selector智能体是Text2SQL多智能体系统中的核心组件，负责MySQL数据库模式理解和智能裁剪。基于MAC-SQL策略，它能够自动分析MySQL数据库结构，并根据查询相关性和token限制进行动态模式优化。

## 核心功能

### 1. MySQL数据库模式扫描与理解

#### 自动模式发现
- **MySQL数据库扫描**: 自动连接MySQL数据库，提取完整的表结构信息
- **元数据提取**: 获取表名、列名、数据类型、主键、外键、注释等完整元数据
- **样本数据收集**: 自动采集每个表的前3行样本数据，用于上下文理解
- **统计信息计算**: 计算表数量、列数量、平均复杂度等统计指标

#### 多数据源支持
- **MySQL数据库**: 直接连接MySQL服务器扫描数据库模式
- **JSON模式文件**: 从预定义的JSON文件加载模式信息（备选方案）
- **统一接口**: 透明的数据源切换，统一的访问接口

### 2. 智能模式裁剪

#### 复杂度评估
- **Token计数**: 使用tiktoken进行精确的token数量计算
- **列数阈值**: 基于平均列数（默认6列）和总列数（默认30列）的双重阈值
- **Token限制**: 支持25000 token的上限控制
- **智能判断**: 综合考虑多个维度决定是否需要裁剪

#### 查询相关性分析
- **关键词提取**: 从自然语言查询中提取实体、属性、操作等关键词
- **表相关性评分**: 基于表名匹配、列名匹配、外键关系的综合评分
- **列重要性排序**: 优先保留ID列、匹配列和常见重要列
- **智能选择**: 基于相关性分数选择最重要的表和列

### 3. 高性能缓存系统

#### 三级缓存架构
- **db2infos**: 缓存完整的数据库模式信息（DatabaseInfo对象）
- **db2dbjsons**: 缓存JSON格式的模式表示，便于序列化
- **db2stats**: 缓存数据库统计信息（DatabaseStats对象）

#### 缓存优化

- **一次扫描，多次使用**: 避免重复的数据库扫描操作
- **内存效率**: 合理的缓存大小和生命周期管理
- **快速访问**: 毫秒级的缓存命中响应时间
- **JSON表示缓存**: 为数据库模式创建JSON表示，便于序列化和传输

## 技术实现

### 核心类结构

```python
class SelectorAgent(BaseAgent):
    """Selector智能体主类"""
    
    def __init__(self, agent_name: str = "Selector", 
                 tables_json_path: str = "", 
                 router=None):
        # 初始化智能体
        
    def talk(self, message: ChatMessage) -> AgentResponse:
        # 处理消息的主要接口
```

### 代码质量特性

- **格式规范**: 遵循Python PEP 8代码风格规范
- **紧凑结构**: 优化的列表推导式和简洁的代码布局
- **清晰注释**: 详细的代码注释和文档字符串
- **维护性**: 良好的代码组织和模块化设计

### 配置系统

```python
@dataclass
class SchemaPruningConfig:
    """模式裁剪配置"""
    token_limit: int = 25000                    # Token限制
    avg_column_threshold: int = 6               # 平均列数阈值
    total_column_threshold: int = 30            # 总列数阈值
    max_tables_per_query: int = 10              # 每查询最大表数
    enable_foreign_key_analysis: bool = True   # 启用外键分析
    enable_semantic_pruning: bool = True       # 启用语义裁剪
```

### 裁剪算法

#### 1. 复杂度判断
```python
def is_need_prune(self, db_stats: DatabaseStats, schema_text: str) -> bool:
    # 检查列数阈值
    if (db_stats.avg_column_count > self.config.avg_column_threshold or 
        db_stats.total_column_count > self.config.total_column_threshold):
        return True
    
    # 检查token数量
    token_count = schema_manager.count_tokens(schema_text)
    return token_count >= self.config.token_limit
```

#### 2. 查询关键词提取
```python
def _extract_query_keywords(self, query: str) -> Dict[str, List[str]]:
    keywords = {
        "entities": [],     # 潜在表名
        "attributes": [],   # 潜在列名
        "operations": [],   # 操作类型
        "conditions": []    # 过滤条件
    }
    # 使用正则表达式提取各类关键词
```

#### 3. 表相关性计算
```python
def _calculate_table_relevance(self, table_name: str, columns: List[Tuple], 
                             query_keywords: Dict[str, List[str]], 
                             foreign_keys: List[Tuple]) -> Dict[str, Any]:
    relevance_score = 0
    
    # 表名匹配（权重：10分）
    # 列名匹配（权重：5分）
    # 外键关系（权重：3分）
    
    return {
        "score": relevance_score,
        "column_matches": column_matches,
        "is_irrelevant": is_irrelevant
    }
```

## 使用示例

### 基本使用
```python
# 创建Selector智能体
selector = SelectorAgent(
    agent_name="MySelector",
    tables_json_path="/path/to/json/schemas"  # 可选的JSON备选方案
)

# 处理查询
message = ChatMessage(
    db_id="ecommerce_db",  # MySQL数据库名
    query="Show all users with their order history"
)

response = selector.talk(message)

if response.success:
    print(f"Schema selected: {response.message.desc_str}")
    print(f"Pruned: {response.message.pruned}")
    print(f"Next agent: {response.message.send_to}")
```

### 配置调整
```python
# 更新裁剪配置
selector.update_pruning_config(
    token_limit=50000,
    avg_column_threshold=10,
    enable_semantic_pruning=True
)

# 获取统计信息
stats = selector.get_pruning_stats()
print(f"Pruning ratio: {stats['avg_pruning_ratio']:.2%}")
```

### 手动模式扫描
```python
# 扫描MySQL数据库模式
db_info = selector.schema_manager.scan_mysql_database_schema(
    "my_database",  # MySQL数据库名
    "my_db"         # 内部标识符
)

# 获取模式描述
desc_str, fk_str = selector._get_db_desc_str("my_db", None)
```

## 性能特性

### 裁剪效率
- **智能判断**: 只在必要时进行裁剪，避免不必要的计算开销
- **快速匹配**: 基于关键词的快速相关性匹配算法
- **渐进式处理**: 优先处理最相关的表和列，提高处理效率

### Token优化
- **精确计算**: 使用tiktoken库进行精确的token计数
- **长度控制**: 确保生成的模式描述不超过LLM的token限制
- **性能提升**: 减少不必要的token消耗，提高LLM处理效率

### 内存管理
- **缓存优化**: 三级缓存系统避免重复计算
- **内存控制**: 合理的缓存大小限制，防止内存溢出
- **生命周期管理**: 智能的缓存清理和更新机制

## 测试覆盖

### 单元测试（21个测试用例）
- **DatabaseSchemaManager测试**: 模式扫描、缓存、token计数
- **SchemaPruner测试**: 裁剪判断、关键词提取、相关性计算
- **SelectorAgent测试**: 消息处理、配置管理、统计跟踪

### 集成测试
- **端到端测试**: 完整的查询处理流程
- **多数据源测试**: MySQL和JSON数据源的兼容性
- **性能测试**: 大型MySQL数据库的处理能力验证

## 最佳实践

### 配置优化
- **Token限制**: 根据目标LLM的上下文窗口调整token_limit
- **阈值设置**: 根据数据库复杂度调整列数阈值
- **外键分析**: 对于关系复杂的数据库启用外键分析

### 性能调优
- **缓存预热**: 在系统启动时预先扫描常用数据库
- **批量处理**: 对于多个相似查询，复用模式信息
- **监控指标**: 定期检查裁剪统计，优化裁剪策略

### 错误处理
- **降级策略**: 当裁剪失败时，使用完整模式
- **日志记录**: 详细记录裁剪过程，便于问题诊断
- **重试机制**: 对于临时性错误实施重试策略

## 扩展性

### 新数据源支持
- **插件架构**: 通过继承DatabaseSchemaManager添加新数据源
- **统一接口**: 保持一致的API接口，便于扩展
- **配置驱动**: 通过配置文件支持新的数据源类型

### 裁剪策略扩展
- **策略模式**: 支持添加新的裁剪算法
- **可配置权重**: 支持调整不同因素的权重
- **机器学习**: 未来可集成ML模型进行更智能的裁剪

## 故障排除

### 常见问题
1. **MySQL连接失败**: 检查数据库连接配置、服务状态和权限
2. **JSON解析错误**: 验证JSON文件格式和编码
3. **Token计数异常**: 确保tiktoken库正确安装
4. **裁剪过度**: 调整相关性阈值和列数限制

### 调试技巧
- **启用详细日志**: 设置日志级别为DEBUG
- **统计信息分析**: 使用get_pruning_stats()分析裁剪效果
- **手动测试**: 使用示例脚本验证各个组件功能
- **性能分析**: 监控处理时间和内存使用情况

## 未来发展

### 计划功能
- **机器学习优化**: 基于历史查询优化裁剪策略
- **多数据库支持**: 扩展到PostgreSQL、Oracle等其他数据库
- **实时更新**: 支持MySQL数据库模式的实时变更检测
- **可视化界面**: 提供模式裁剪的可视化管理界面

### 性能提升
- **并行处理**: 支持多表并行扫描和裁剪
- **增量更新**: 只更新变更的模式部分
- **智能预测**: 基于查询模式预测需要的模式信息
- **分布式缓存**: 支持分布式环境下的缓存共享
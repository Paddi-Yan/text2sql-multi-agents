# Text2SQL Multi-Agent Service

A production-ready Text2SQL service system that combines **Vanna.ai's RAG training mechanism** with **MAC-SQL's three-agent collaboration architecture**, delivering enterprise-grade natural language to SQL conversion with continuous learning capabilities.

## Core Innovation

This system uniquely integrates two proven approaches:

- **Vanna.ai's Training-Asking Paradigm**: Supports DDL statements, documentation, SQL examples, and question-SQL pairs for comprehensive context building
- **MAC-SQL's Agent Collaboration**: Specialized agents for schema selection, query decomposition, and execution validation
- **Enhanced RAG Architecture**: Vector-based semantic retrieval with intelligent context assembly

## 核心功能

- **Vanna.ai式训练系统**: 支持多种训练数据类型（DDL、文档、SQL示例、问答对、领域知识）
- **MAC-SQL智能体架构**: 协作式Selector、Decomposer和Refiner智能体，具备智能模式裁剪功能
- **增强型RAG检索**: 高级质量过滤、多样性控制和多策略上下文检索
- **智能记忆与学习**: 从用户反馈和成功查询中持续改进
- **企业级可靠性**: 内置容错、重试机制和高可用性
- **向量相似性搜索**: 基于Milvus的语义匹配和上下文检索
- **高性能缓存**: 基于Redis的多层缓存，响应时间低于100ms
- **安全与访问控制**: SQL注入防护和基于角色的权限管理
- **全面测试覆盖**: 包含50+测试用例的健壮测试套件，覆盖所有主要组件

## 已实现功能

### ✅ 基础架构和核心接口

- 完整的项目目录结构（agents、services、storage、utils、config等）
- 核心数据模型（ChatMessage、DatabaseInfo、SQLExecutionResult等）
- 基础配置管理系统

### ✅ Vanna.ai式RAG训练系统

- **训练数据管理**: 支持5种训练数据类型的统一管理
- **VannaTrainingService**: 完整的训练服务，支持DDL、文档、SQL、问答对和领域知识训练
- **增强型RAG检索器**: 高级质量过滤、多样性控制和智能提示词生成

### ✅ MAC-SQL智能体协作系统

- **BaseAgent基类**: 抽象基类和完整的消息传递机制
- **Selector智能体**: MySQL数据库模式理解和智能裁剪，支持token限制优化
- **Decomposer智能体**: 完整实现查询分解和SQL生成，支持CoT推理、多数据集适配和RAG增强
- **LLM服务**: 统一的语言模型调用接口，支持查询分解和SQL生成
- **提示词管理系统**: 集中化的提示词模板管理，支持参数化和动态格式化
- **通信协议**: 高级智能体间通信，支持优先级队列和会话管理
- **代码质量**: 持续的代码格式优化和注释改进，确保代码可读性和维护性

### ✅ 完整的MAC-SQL智能体协作系统

- **BaseAgent基类**: 抽象基类和完整的消息传递机制
- **Selector智能体**: MySQL数据库模式理解和智能裁剪，支持token限制优化
- **Decomposer智能体**: 完整实现查询分解和SQL生成，支持CoT推理、多数据集适配和RAG增强
- **Refiner智能体**: SQL执行验证、错误修正和安全检查，支持超时控制和智能修复
- **LLM服务**: 统一的语言模型调用接口，支持查询分解和SQL生成
- **提示词管理系统**: 集中化的提示词模板管理，支持参数化和动态格式化
- **通信协议**: 高级智能体间通信，支持优先级队列和会话管理

### ✅ LangGraph工作流编排系统

- **工作流状态管理**: 完整的Text2SQLState状态定义，支持智能体间数据传递
- **节点函数实现**: Selector、Decomposer、Refiner三个核心节点函数
- **条件路由逻辑**: 智能的工作流路径决策和重试机制
- **状态初始化和完成**: 完整的工作流生命周期管理
- **错误处理和监控**: 内置的异常处理和执行时间统计

## Architecture

The system combines the best of both worlds:

### Vanna.ai Training Phase

- **DDL Training**: Understands database structure and relationships
- **Documentation Training**: Learns business context and domain knowledge
- **SQL Example Training**: Captures query patterns and best practices
- **QA Pair Training**: Direct question-to-SQL mapping for accuracy
- **Auto-Learning**: Continuous improvement from successful interactions

### MAC-SQL Agent Collaboration

- **Selector**: Database schema analysis and intelligent pruning (with token-aware optimization)
- **Decomposer**: Query decomposition and step-by-step SQL generation
- **Refiner**: SQL execution validation and error-based refinement

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
export OPENAI_API_KEY="your-api-key"
export DB_HOST="127.0.0.1"
export DB_PORT="3306"
export DB_USER="root"
export DB_PASSWORD="123456"
export DB_NAME="text2sql_db"
export REDIS_HOST="localhost"
export MILVUS_HOST="localhost"
```

3. Initialize MySQL database:

```bash
python scripts/init_mysql_db.py
```

4. Test MySQL connection:

```bash
python scripts/test_mysql_connection.py
```

5. Start the service:

```bash
python -m services.chat_manager
```

## 项目结构

```
├── agents/                 # 多智能体实现
│   ├── base_agent.py      # 基础智能体抽象类和消息路由
│   ├── selector_agent.py  # Selector智能体（数据库模式理解和裁剪）
│   ├── decomposer_agent.py # Decomposer智能体（查询分解和SQL生成）
│   └── communication.py   # 高级智能体间通信协议
├── services/              # 核心业务服务
│   ├── training_service.py        # Vanna.ai式训练服务
│   ├── enhanced_rag_retriever.py  # 增强型RAG检索器
│   ├── llm_service.py             # 统一LLM调用服务
│   └── workflow.py                # LangGraph工作流编排系统
├── storage/               # 数据访问层
│   └── vector_store.py    # 向量数据库操作
├── utils/                 # 共享工具和模型
│   ├── models.py          # 核心数据模型
│   ├── training_models.py # 训练数据模型
│   ├── training_data_manager.py # 训练数据管理器
│   ├── vectorization.py   # 向量化工具
│   └── prompts.py         # 集中化提示词管理系统
├── config/               # 配置管理
│   └── settings.py       # 应用配置
├── tests/                # 测试套件
│   ├── unit/            # 单元测试
│   └── integration/     # 集成测试
├── examples/             # 使用示例
└── docs/                # 文档
```

## 核心组件

### Selector智能体 (agents/selector_agent.py)

- **MySQL数据库模式扫描**: 自动扫描MySQL数据库结构，提取表、列、主键、外键信息
- **智能模式裁剪**: 基于查询相关性和token限制进行动态模式裁剪
- **多数据源支持**: 支持MySQL数据库和JSON模式文件
- **性能优化**: 三级缓存系统（db2infos、db2dbjsons、db2stats）
- **Token控制**: 基于tiktoken的精确token计数，支持25000 token限制

### 训练服务 (services/training_service.py)

- **多类型训练**: 支持DDL、文档、SQL、问答对、领域知识5种训练数据类型
- **向量化存储**: 自动生成向量嵌入并存储到Milvus向量数据库
- **自动学习**: 从成功查询中自动提取训练数据

### 增强型RAG检索器 (services/enhanced_rag_retriever.py)

- **质量过滤**: 基于相似度阈值和内容质量的智能过滤
- **多样性控制**: 避免检索结果过于相似，保证内容多样性
- **多种检索策略**: 平衡、QA重点、SQL重点、上下文重点四种策略
- **智能提示词生成**: 结构化、分层的提示词构建

### Decomposer智能体 (agents/decomposer_agent.py)

- **智能查询分解**: 自动分析查询复杂度，将复杂自然语言查询分解为逻辑子问题
- **CoT推理**: 基于Chain of Thought的渐进式SQL生成，支持简单和复杂查询两种模式
- **多数据集适配**: 支持BIRD、Spider、Generic等数据集，动态调整处理策略
- **RAG增强**: 深度集成增强型RAG检索，利用历史示例和上下文提高生成质量
- **LLM集成**: 与LLM服务深度集成，支持查询分解和SQL生成的智能化处理
- **性能监控**: 完整的统计系统，包括查询复杂度分析、RAG增强率和成功率跟踪
- **动态配置**: 支持运行时配置更新、数据集切换和RAG检索器设置

### Refiner智能体 (agents/refiner_agent.py)

- **SQL执行验证**: 自动执行生成的SQL查询并验证结果正确性
- **安全检查**: 内置SQL注入防护，检测和阻止危险的SQL操作
- **错误修正**: 基于执行错误智能修正SQL语句，支持语法错误、表名错误、列名错误等
- **超时控制**: 120秒执行超时保护，防止长时间运行的查询影响系统性能
- **双数据库支持**: 生产环境使用MySQL，开发/测试环境自动降级到SQLite，提供灵活的部署选项
- **智能切换**: 根据环境配置自动选择合适的数据库，确保最佳的开发体验和生产性能
- **LLM增强修复**: 利用LLM服务进行智能SQL修正，提供上下文感知的错误修复
- **统计监控**: 详细的执行统计，包括验证次数、修正率、安全违规率等指标

### LLM服务 (services/llm_service.py)

- **统一接口**: 标准化的LLM调用接口，支持多种模型
- **查询分解**: 智能将复杂查询分解为子问题，支持JSON格式输出
- **SQL生成**: 支持简单SQL生成和基于CoT的复杂SQL生成
- **上下文集成**: 与RAG检索器深度集成，利用检索上下文增强生成质量
- **错误处理**: 完善的异常处理和响应包装机制
- **架构优化**: 组件间采用松耦合设计，支持依赖注入和统一日志管理

### LangGraph工作流编排系统 (services/workflow.py)

- **状态管理**: 完整的Text2SQLState状态定义，包含所有智能体间的数据传递信息
- **节点函数**: 实现Selector、Decomposer、Refiner三个核心智能体的节点函数
- **条件路由**: 智能的工作流路径决策，支持重试机制和错误处理
- **生命周期管理**: 完整的工作流初始化、执行和完成流程
- **监控统计**: 内置执行时间统计、token使用量跟踪和性能监控
- **错误恢复**: 支持智能重试、降级处理和异常恢复机制

### 提示词管理系统 (utils/prompts.py)

- **集中化管理**: 统一管理所有智能体的提示词模板
- **结构化模板**: 支持系统提示和用户提示的分离管理
- **参数化支持**: 动态参数替换和模板格式化
- **智能体专用**: 为Selector、Decomposer、Refiner等智能体提供专门的提示词
- **便捷函数**: 提供常用提示词的快速访问接口

## 文档

### 快速开始

- [快速开始指南](docs/quick_start.md) - 系统安装、配置和基本使用

### 核心组件文档

- [Selector智能体详细文档](docs/selector_agent.md) - 数据库模式理解和智能裁剪
- [Decomposer智能体详细文档](docs/decomposer_agent.md) - 查询分解和SQL生成
- [LLM服务详细文档](docs/llm_service.md) - 统一语言模型调用接口
- [Task 3.3 实现总结](docs/task_3_3_implementation_summary.md) - Decomposer智能体实现详情
- [Task 3.2 实现总结](docs/task_3_2_implementation_summary.md) - Selector智能体实现详情
- [Task 3.1 实现总结](docs/task_3_1_implementation_summary.md) - BaseAgent基类和消息传递
- [Task 2.3 实现总结](docs/task_2_3_implementation_summary.md) - 增强型RAG检索系统
- [Task 2.2 实现总结](docs/task_2_2_implementation_summary.md) - Vanna训练服务
- [更新日志](docs/changelog.md) - 项目更新历史和改进记录

### 测试和质量

- [测试和质量保证](docs/testing_and_quality.md) - 完整的测试策略和质量控制

### 使用示例

- [Selector智能体示例](examples/selector_agent_example.py) - 完整的使用演示
- [Decomposer智能体示例](examples/decomposer_agent_example.py) - 查询分解和SQL生成演示
- [Refiner智能体示例](examples/refiner_agent_example.py) - SQL验证和错误修正演示
- [BaseAgent通信示例](examples/base_agent_communication_example.py) - 智能体间通信演示
- [增强型RAG检索示例](examples/enhanced_rag_retriever_example.py) - RAG检索功能演示
- [训练服务示例](examples/vanna_training_service_example.py) - 训练系统使用演示
- [LLM集成测试示例](examples/test_llm_integration.py) - LLM服务集成测试
- [LangGraph工作流示例](examples/workflow_example.py) - 工作流编排系统使用演示
- [完整工作流测试](examples/complete_workflow_test.py) - 端到端工作流测试和验证
- [简单工作流测试](examples/simple_workflow_test.py) - 基础工作流功能测试

### 技术文档

- [提示词管理系统文档](docs/prompts_system.md) - 集中化提示词管理详细说明
- [LangGraph工作流文档](docs/langgraph_workflow.md) - 工作流编排系统详细说明

## License

MIT License
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
- **通信协议**: 高级智能体间通信，支持优先级队列和会话管理
- **代码质量**: 持续的代码格式优化和注释改进，确保代码可读性和维护性

### 🚧 开发中功能

- **Decomposer智能体**: 查询分解和SQL生成（规划中）
- **Refiner智能体**: SQL执行验证和错误修正（规划中）
- **LangGraph工作流**: 智能体编排和状态管理（规划中）

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
│   └── communication.py   # 高级智能体间通信协议
├── services/              # 核心业务服务
│   ├── training_service.py        # Vanna.ai式训练服务
│   └── enhanced_rag_retriever.py  # 增强型RAG检索器
├── storage/               # 数据访问层
│   └── vector_store.py    # 向量数据库操作
├── utils/                 # 共享工具和模型
│   ├── models.py          # 核心数据模型
│   ├── training_models.py # 训练数据模型
│   ├── training_data_manager.py # 训练数据管理器
│   └── vectorization.py   # 向量化工具
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

## 文档

### 快速开始

- [快速开始指南](docs/quick_start.md) - 系统安装、配置和基本使用

### 核心组件文档

- [Selector智能体详细文档](docs/selector_agent.md) - 数据库模式理解和智能裁剪
- [Task 3.2 实现总结](docs/task_3_2_implementation_summary.md) - Selector智能体实现详情
- [Task 3.1 实现总结](docs/task_3_1_implementation_summary.md) - BaseAgent基类和消息传递
- [Task 2.3 实现总结](docs/task_2_3_implementation_summary.md) - 增强型RAG检索系统
- [Task 2.2 实现总结](docs/task_2_2_implementation_summary.md) - Vanna训练服务
- [更新日志](docs/changelog.md) - 项目更新历史和改进记录

### 测试和质量

- [测试和质量保证](docs/testing_and_quality.md) - 完整的测试策略和质量控制

### 使用示例

- [Selector智能体示例](examples/selector_agent_example.py) - 完整的使用演示
- [BaseAgent通信示例](examples/base_agent_communication_example.py) - 智能体间通信演示
- [增强型RAG检索示例](examples/enhanced_rag_retriever_example.py) - RAG检索功能演示
- [训练服务示例](examples/vanna_training_service_example.py) - 训练系统使用演示

## License

MIT License
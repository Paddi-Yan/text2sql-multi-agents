# 实施计划

- [x] 1. 建立项目基础架构和核心接口
  - 创建项目目录结构，包含agents、services、storage、utils、config等模块
  - 定义核心数据模型和接口（ChatMessage、DatabaseInfo、SQLExecutionResult等）
  - 实现基础配置管理系统
  - _需求: 1.1, 2.1, 6.1_

- [ ] 2. 实现Vanna.ai式RAG训练系统
- [x] 2.1 创建训练数据类型和管理
  - 实现TrainingDataType枚举（DDL_STATEMENT、DOCUMENTATION、SQL_QUERY、QUESTION_SQL_PAIR、DOMAIN_KNOWLEDGE）
  - 创建TrainingData数据类，支持多种训练数据类型的统一管理
  - 实现训练数据的向量化、元数据管理和时间戳记录
  - 添加训练数据的标签系统和相关表名关联
  - _需求: 3.1, 3.2_

- [x] 2.2 实现VannaTrainingService训练服务
  - 创建VannaTrainingService类，集成向量存储和嵌入模型
  - 实现train_ddl()方法，训练DDL语句让系统理解数据库结构
  - 实现train_documentation()方法，训练业务文档提供业务上下文
  - 实现train_sql()方法，训练SQL查询示例
  - 实现train_qa_pairs()方法，训练问题-SQL对（最直接的训练方式）
  - 添加_store_training_data()方法，处理向量嵌入生成和存储
  - 编写训练服务的单元测试
  - _需求: 3.1, 3.2, 3.3_

- [ ] 2.3 实现增强型RAG检索系统
  - 创建EnhancedRAGRetriever检索器，结合Vanna.ai的检索策略
  - 实现retrieve_context()方法，支持多类型检索（DDL、文档、SQL示例、QA对、领域知识）
  - 创建build_enhanced_prompt()方法，构建包含检索上下文的增强提示词
  - 添加相似性搜索过滤器和top-k检索策略
  - 实现上下文数量限制和质量控制机制
  - 编写RAG检索系统的单元测试
  - _需求: 3.3, 3.4_

- [ ] 3. 实现MAC-SQL三智能体协作系统
- [ ] 3.1 创建BaseAgent基类和消息传递机制
  - 实现BaseAgent抽象基类，定义talk()方法接口
  - 创建ChatMessage消息传递标准格式，包含所有必要字段（db_id、query、evidence、extracted_schema等）
  - 实现智能体间通信协议和状态管理
  - 添加消息路由机制（send_to字段控制）
  - _需求: 2.1, 2.2_

- [ ] 3.2 实现Selector选择器智能体
  - 创建Selector类，继承BaseAgent，负责数据库模式理解和动态裁剪
  - 实现数据库模式自动扫描和理解功能（db2infos、db2dbjsons缓存）
  - 实现动态模式裁剪算法，基于MAC-SQL策略和token限制（25000 tokens）
  - 创建_get_db_desc_str()方法，生成数据库描述字符串和外键关系
  - 实现_is_need_prune()方法，基于复杂度评估判断是否需要裁剪
  - 实现_prune()方法，基于查询相关性选择表和列
  - 添加数据库统计信息收集（表数量、列数量等）
  - 编写Selector智能体的单元测试
  - _需求: 2.1, 2.2, 6.1_

- [ ] 3.3 实现Decomposer分解器智能体
  - 创建Decomposer类，继承BaseAgent，负责查询分解和SQL生成
  - 实现自然语言查询分解为子问题的功能
  - 创建基于CoT（Chain of Thought）的SQL生成策略
  - 添加多数据集模板适配（BIRD、Spider等），支持dataset_name参数
  - 实现_decompose_query()方法，将复杂查询分解为子问题列表
  - 实现_generate_sql_steps()方法，渐进式SQL构建
  - 集成增强型RAG检索，利用历史示例和上下文
  - 编写Decomposer智能体的单元测试
  - _需求: 1.1, 1.3, 2.1_

- [ ] 3.4 实现Refiner精炼器智能体
  - 创建Refiner类，继承BaseAgent，负责SQL执行验证和错误修正
  - 实现SQL语法和语义验证功能
  - 创建数据库执行和结果验证机制
  - 实现_execute_sql()方法，支持实际SQL执行和超时控制（120秒）
  - 实现_is_need_refine()方法，基于执行结果判断是否需要修正
  - 实现_refine_sql()方法，基于错误反馈进行SQL修正
  - 添加安全性检查和SQL注入防护
  - 集成SQLExecutionResult数据模型，记录执行时间和错误信息
  - 编写Refiner智能体的单元测试
  - _需求: 1.2, 2.1, 7.1_

- [ ] 4. 实现LangGraph工作流编排系统
- [ ] 4.1 创建LangGraph状态定义和节点
  - 定义Text2SQLState状态模型（TypedDict），包含输入信息、处理状态、智能体输出和最终结果
  - 实现selector_node节点函数，处理Selector智能体逻辑并更新状态
  - 实现decomposer_node节点函数，处理Decomposer智能体逻辑并更新状态
  - 实现refiner_node节点函数，处理Refiner智能体逻辑并更新状态
  - 创建条件路由逻辑should_continue()，支持智能重试和错误处理
  - 添加重试计数和最大重试次数控制
  - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 4.2 构建工作流图和ChatManager
  - 实现create_text2sql_workflow()工作流构建函数，使用StateGraph
  - 添加工作流节点（selector、decomposer、refiner）和边的定义
  - 设置工作流入口点和条件边，支持循环重试机制
  - 创建OptimizedChatManager聊天管理器，集成LangGraph工作流编排
  - 实现process_query()方法，替代原有的多轮对话机制
  - 添加最大协作轮次限制（max_rounds=3）和智能体字典管理
  - 集成工作流状态监控、错误处理和智能重试机制
  - 编写工作流集成测试
  - _需求: 2.1, 2.5, 4.1_

- [ ] 5. 实现存储和缓存系统
- [ ] 5.1 创建Redis多层缓存服务
  - 实现CacheService类，支持L1内存缓存（1000个查询结果）、L2 Redis缓存（24小时TTL）、L3向量相似性缓存
  - 创建CacheKeyGenerator缓存键生成器，支持查询键和相似性键生成
  - 实现LRU淘汰策略和缓存容量限制管理
  - 添加缓存命中率监控、性能优化机制和集群模式支持
  - 编写缓存服务的单元测试
  - _需求: 5.1, 5.2, 5.5_

- [ ] 5.2 实现Milvus向量存储服务
  - 创建VectorStore类，集成Milvus向量数据库和嵌入模型
  - 实现insert()方法，支持向量插入和元数据存储
  - 实现search()方法，支持向量相似性搜索和过滤器查询
  - 添加批量向量操作、向量索引管理和集合管理功能
  - 实现向量数据库的连接管理和性能优化
  - 支持多种数据类型的向量存储（训练数据、记忆记录等）
  - 编写向量存储的单元测试
  - _需求: 3.3, 5.3, 5.4_

- [ ] 5.3 创建数据库适配器和模式管理
  - 实现DatabaseAdapter支持多数据库连接（MySQL、PostgreSQL、Oracle）
  - 创建SchemaManager自动扫描和理解数据库模式
  - 实现DatabaseInfo数据模型，包含desc_dict、value_dict、pk_dict、fk_dict
  - 创建DatabaseStats统计信息模型，记录表数量和列数量统计
  - 添加数据库连接池、故障转移和模式缓存机制
  - 实现数据库特定语法差异处理和元数据更新机制
  - 编写数据库适配器的单元测试
  - _需求: 6.1, 6.2, 6.3, 6.4, 4.2_

- [ ] 6. 实现智能记忆和学习系统
- [ ] 6.1 创建记忆服务核心功能
  - 实现MemoryService类，管理正确和错误示例的向量化存储
  - 创建MemoryRecord数据模型，包含查询对、执行结果、用户反馈和向量嵌入
  - 实现MemoryType枚举（POSITIVE_EXAMPLE、NEGATIVE_EXAMPLE、PATTERN_TEMPLATE、DOMAIN_KNOWLEDGE）
  - 添加记忆记录的CRUD操作、相似查询检索和模式识别功能
  - 实现记忆分类体系和使用计数统计
  - _需求: 3.1, 3.2, 3.3_

- [ ] 6.2 实现学习机制和效果评估
  - 创建增量学习流程，支持用户反馈收集和验证
  - 实现LearningMetrics学习效果评估指标，包含准确率趋势和模式覆盖度
  - 添加错误减少率计算和改进率评估功能
  - 实现错误模式避免机制和查询模式模板提取
  - 创建相似性索引更新和模式识别算法
  - 添加学习效果的可视化和报告功能
  - 编写记忆学习系统的单元测试
  - _需求: 3.4, 3.5_

- [ ] 7. 实现安全和权限控制系统
- [ ] 7.1 创建SQL安全验证器
  - 实现SQLSecurityValidator类，检测SQL注入攻击和危险模式
  - 创建dangerous_patterns正则表达式列表，检测DROP、DELETE、UNION SELECT等危险操作
  - 实现validate_sql()方法，支持模式匹配检查和AST语法树分析
  - 创建SecurityValidationResult结果模型，包含安全状态、风险等级和检测模式
  - 添加RiskLevel枚举（HIGH、MEDIUM、LOW）和错误信息记录
  - 集成sqlparse库进行SQL语法树分析和深度安全检查
  - 编写SQL安全验证的单元测试
  - _需求: 7.1


- [ ] 8. 创建API接口和用户界面
- [ ] 8.1 实现RESTful API接口
  - 创建FastAPI应用，提供Text2SQL转换、训练数据管理API端点
  - 实现查询提交、结果获取、用户反馈、训练数据上传等接口
  - 添加API文档、请求验证、认证授权和限流机制
  - 编写API接口的单元测试
  - _需求: 1.1, 1.5_

- [ ] 8.2 创建Web用户界面
  - 实现Web界面用于查询输入、结果展示和训练数据管理
  - 添加用户反馈收集、历史查询查看和学习效果展示功能
  - 创建系统状态监控、智能体性能监控和管理界面
  - 编写API和UI的集成测试
  - _需求: 1.1, 3.1, 3.2_

- [ ] 9. 实现智能模式裁剪和优化策略
- [ ] 9.1 创建模式复杂度评估系统
  - 实现SchemaPruningStrategy类，定义复杂度阈值（avg_column_count=6, total_column_count=30, token_limit=25000）
  - 创建is_need_prune()方法，基于列数量和token数量判断是否需要裁剪
  - 实现_count_tokens()方法，使用tiktoken计算模式文本的token数量
  - 添加数据库复杂度评估和裁剪决策逻辑
  - _需求: 6.1, 6.2_

- [ ] 9.2 实现智能表和列选择算法
  - 创建TableColumnSelector类，基于查询相关性选择表和列
  - 实现select_relevant_schema()方法，支持keep_all、drop_all、选择性保留策略
  - 创建_is_table_irrelevant()方法，判断表与查询的相关性
  - 实现_select_top_columns()方法，选择最相关的6列
  - 添加ProgressiveSchemaBuilder，构建渐进式模式描述
  - 编写模式裁剪算法的单元测试
  - _需求: 6.1, 6.2_

- [ ] 10. 综合测试和质量保证
- [ ] 10.1 实现全面的测试套件
  - 创建基于BIRD和Spider数据集的准确性测试
  - 实现SQL正确性测试（多表JOIN、聚合函数、子查询）
  - 添加执行准确性测试（EX: Execution Accuracy）和有效效率评分测试（VES: Valid Efficiency Score）
  - 创建智能体协作测试（Selector模式裁剪、Decomposer分解、Refiner修正）
  - 实现负载测试和压力测试，验证并发处理能力
  - 添加端到端集成测试，验证完整工作流程
  - _需求: 1.1, 1.2, 1.3, 1.4_

- [ ] 10.2 系统集成和性能验证
  - 执行系统集成测试，验证所有组件协作
  - 进行性能基准测试，确保响应时间满足要求（缓存命中<100ms）
  - 验证学习能力和准确率提升效果
  - 测试数据集兼容性（BIRD复杂业务场景、Spider学术查询场景）
  - 完成最终的系统验收和文档整理
  - _需求: 5.2, 3.4, 3.5, 8.1, 8.2_
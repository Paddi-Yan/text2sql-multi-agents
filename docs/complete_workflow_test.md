# 完整工作流端到端测试文档

## 概述

`examples/complete_workflow_test.py` 是一个全面的端到端测试套件，用于验证Text2SQL多智能体系统的完整工作流程。该测试使用**真实的MySQL数据库**进行端到端验证，涵盖了从简单查询到复杂聚合查询的各种场景，以及错误处理、并发处理和系统统计等功能。

## 重要更新 (2024-01-08)

### 🔄 架构升级：从SQLite到MySQL

测试系统已完全迁移到MySQL数据库，提供更真实的生产环境测试：

- **真实MySQL环境**: 使用生产级MySQL数据库进行测试
- **企业级特性**: 支持事务、外键约束、并发控制等MySQL特性
- **配置驱动**: 通过 `config.settings` 统一管理数据库连接
- **生产对等**: 测试环境与生产环境完全一致

## 测试功能

### 1. MySQL测试数据管理

测试系统提供完整的MySQL测试数据生命周期管理：

#### 1.1 自动测试数据创建 (`setup_mysql_test_data`)

- **MySQL连接**: 使用 `pymysql` 连接到配置的MySQL数据库
- **表结构创建**: 自动创建 `schools` 和 `districts` 表（如果不存在）
- **测试数据插入**: 插入6所学校和3个学区的真实测试数据
- **数据验证**: 确认测试数据正确插入

#### 1.2 自动测试数据清理 (`cleanup_mysql_test_data`)

- **数据清理**: 测试完成后自动删除测试数据
- **环境隔离**: 确保测试不影响其他数据
- **错误处理**: 优雅处理清理过程中的异常

#### MySQL测试数据结构

```sql
-- 学校表 (MySQL版本)
CREATE TABLE IF NOT EXISTS schools (
    school_id INT AUTO_INCREMENT PRIMARY KEY,
    school_name VARCHAR(200) NOT NULL,
    district_id INT,
    city VARCHAR(100),
    sat_score INT,
    enrollment INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 学区表 (MySQL版本)
CREATE TABLE IF NOT EXISTS districts (
    district_id INT AUTO_INCREMENT PRIMARY KEY,
    district_name VARCHAR(200) NOT NULL,
    city VARCHAR(100),
    county VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 测试数据内容

**学区数据**:
- Los Angeles Unified Test (Los Angeles County)
- San Francisco Unified Test (San Francisco County)  
- San Diego Unified Test (San Diego County)

**学校数据**:
- Lincoln High School Test (Los Angeles, SAT: 1450, 学生: 2500)
- Washington High School Test (Los Angeles, SAT: 1380, 学生: 2200)
- Roosevelt High School Test (San Francisco, SAT: 1520, 学生: 1800)
- Jefferson High School Test (San Francisco, SAT: 1420, 学生: 1900)
- Madison High School Test (San Diego, SAT: 1480, 学生: 2100)
- Monroe High School Test (San Diego, SAT: 1350, 学生: 1950)

### 2. 测试场景覆盖

#### 2.1 简单查询测试 (`test_simple_query`)

- **目标**: 验证基础查询处理能力
- **查询示例**: "List all schools in Los Angeles"
- **验证点**:
  - SQL生成正确性
  - 查询执行成功
  - 结果数据准确性
  - 处理时间统计

#### 2.2 复杂查询测试 (`test_complex_query`)

- **目标**: 验证多表关联查询处理
- **查询示例**: "Show me schools with SAT scores above 1400 and their district information"
- **验证点**:
  - JOIN查询生成
  - 模式裁剪功能
  - 分解策略应用
  - 复杂逻辑处理

#### 2.3 聚合查询测试 (`test_aggregation_query`)

- **目标**: 验证聚合函数和分组查询
- **查询示例**: "What is the average SAT score by city?"
- **验证点**:
  - GROUP BY语句生成
  - 聚合函数使用
  - 统计计算准确性

#### 2.4 错误处理测试 (`test_error_handling`)

- **目标**: 验证系统错误处理和恢复能力
- **查询示例**: "Show me information from the nonexistent_table"
- **验证点**:
  - 错误检测机制
  - 重试逻辑
  - 错误信息记录
  - 优雅降级处理

#### 2.5 工作流统计测试 (`test_workflow_statistics`)

- **目标**: 验证系统监控和统计功能
- **测试内容**:
  - 执行多个不同类型的查询
  - 收集系统性能指标
  - 验证统计数据准确性
  - 健康检查功能

#### 2.6 并发查询测试 (`test_concurrent_queries`)

- **目标**: 验证系统并发处理能力
- **测试方法**:
  - 同时启动5个查询线程
  - 验证并发安全性
  - 检查资源竞争问题
  - 统计并发性能

## 环境要求

### MySQL数据库配置

在运行测试之前，确保MySQL数据库已正确配置：

#### 1. 环境变量设置

```bash
# MySQL数据库连接配置
export DB_HOST="127.0.0.1"
export DB_PORT="3306"
export DB_USER="root"
export DB_PASSWORD="your_password"
export DB_NAME="text2sql_db"

# LLM服务配置
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL_NAME="gpt-4"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

#### 2. MySQL数据库初始化

```bash
# 初始化MySQL数据库和基础表结构
python scripts/init_mysql_db.py

# 测试MySQL连接
python scripts/test_mysql_connection.py
```

#### 3. 依赖安装

```bash
# 安装MySQL客户端依赖
pip install pymysql

# 安装完整依赖
pip install -r requirements.txt
```

## 使用方法

### 基本运行

```bash
# 直接运行完整的MySQL端到端测试套件
python examples/complete_workflow_test.py
```

### 测试前检查

```bash
# 1. 验证MySQL连接
python scripts/test_mysql_connection.py

# 2. 检查配置
python -c "from config.settings import config; print(f'MySQL: {config.database_config.host}:{config.database_config.port}')"

# 3. 运行测试
python examples/complete_workflow_test.py
```

### 单独测试函数

```python
from examples.complete_workflow_test import (
    test_simple_query,
    test_complex_query,
    test_aggregation_query,
    test_error_handling,
    test_workflow_statistics,
    test_concurrent_queries
)

# 运行特定测试
result = test_simple_query()
print(f"简单查询测试结果: {result['success']}")
```

### 自定义测试数据

```python
def create_custom_test_data():
    """创建自定义测试数据"""
    # 可以修改 create_test_data() 函数来使用自定义数据
    pass
```

## 测试输出解析

### 成功测试输出示例

```
2024-01-08 10:30:15,123 - INFO - === 测试简单查询 ===
2024-01-08 10:30:15,456 - INFO - 测试数据创建完成: /tmp/tmpxyz123
2024-01-08 10:30:17,789 - INFO - 查询结果:
2024-01-08 10:30:17,789 - INFO -   成功: True
2024-01-08 10:30:17,789 - INFO -   SQL: SELECT * FROM schools WHERE city = 'Los Angeles'
2024-01-08 10:30:17,789 - INFO -   处理时间: 2.33秒
2024-01-08 10:30:17,789 - INFO -   重试次数: 0
2024-01-08 10:30:17,789 - INFO -   查询结果行数: 2
```

### 错误测试输出示例

```
2024-01-08 10:30:20,123 - INFO - === 测试错误处理 ===
2024-01-08 10:30:22,456 - INFO - 错误处理测试结果:
2024-01-08 10:30:22,456 - INFO -   成功: False
2024-01-08 10:30:22,456 - INFO -   SQL: SELECT * FROM nonexistent_table
2024-01-08 10:30:22,456 - INFO -   处理时间: 2.33秒
2024-01-08 10:30:22,456 - INFO -   重试次数: 2
2024-01-08 10:30:22,456 - INFO -   错误信息: no such table: nonexistent_table
```

### 统计信息输出示例

```
2024-01-08 10:30:25,123 - INFO - 工作流统计信息:
2024-01-08 10:30:25,123 - INFO -   总查询数: 4
2024-01-08 10:30:25,123 - INFO -   成功查询数: 3
2024-01-08 10:30:25,123 - INFO -   失败查询数: 1
2024-01-08 10:30:25,123 - INFO -   成功率: 75.0%
2024-01-08 10:30:25,123 - INFO -   平均处理时间: 2.15秒
2024-01-08 10:30:25,123 - INFO -   重试率: 25.0%
2024-01-08 10:30:25,123 - INFO - 系统健康状态: healthy
```

## 测试结果分析

### 成功指标

- **查询成功率**: 应该 > 90%
- **平均处理时间**: 应该 < 5秒
- **重试率**: 应该 < 20%
- **并发安全性**: 无数据竞争或死锁
- **内存泄漏**: 测试后内存正常释放

### 性能基准

| 测试类型 | 期望处理时间 | 期望成功率 | 备注 |
|---------|-------------|-----------|------|
| 简单查询 | < 3秒 | 100% | 基础功能验证 |
| 复杂查询 | < 5秒 | > 95% | 多表关联查询 |
| 聚合查询 | < 4秒 | > 95% | 统计计算查询 |
| 错误处理 | < 3秒 | 0% (期望失败) | 错误恢复能力 |
| 并发查询 | < 10秒 | > 90% | 并发处理能力 |

## 故障排除

### 常见问题

#### 1. 测试数据创建失败

```
错误: sqlite3.OperationalError: database is locked
解决: 确保没有其他进程占用SQLite文件，重启测试
```

#### 2. LLM服务连接失败

```
错误: OpenAI API connection failed
解决: 检查 OPENAI_API_KEY 环境变量设置
```

#### 3. 并发测试超时

```
错误: Thread join timeout after 30 seconds
解决: 增加超时时间或检查系统资源使用情况
```

#### 4. 临时文件清理失败

```
警告: Failed to remove temporary directory
解决: 手动清理 /tmp 目录下的测试文件
```

### 调试技巧

#### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 保留测试数据

```python
# 在测试函数中注释掉清理代码
# shutil.rmtree(temp_dir, ignore_errors=True)
```

#### 单步调试

```python
# 在关键位置添加断点
import pdb; pdb.set_trace()
```

## 扩展测试

### 添加新测试场景

```python
def test_custom_scenario():
    """自定义测试场景"""
    temp_dir, data_dir, tables_json_path, db_path = create_test_data()
    
    try:
        chat_manager = OptimizedChatManager(
            data_path=data_dir,
            tables_json_path=tables_json_path,
            dataset_name="bird",
            max_rounds=3
        )
        
        # 自定义测试逻辑
        result = chat_manager.process_query(
            db_id="california_schools",
            query="Your custom query here",
            evidence="Custom test evidence"
        )
        
        # 验证结果
        assert result['success'], f"Test failed: {result.get('error')}"
        
        return result
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### 性能压力测试

```python
def test_performance_stress():
    """性能压力测试"""
    import time
    
    # 创建大量并发查询
    num_queries = 100
    start_time = time.time()
    
    # 执行压力测试逻辑
    # ...
    
    end_time = time.time()
    avg_time = (end_time - start_time) / num_queries
    
    assert avg_time < 1.0, f"Average query time too high: {avg_time:.2f}s"
```

## 集成到CI/CD

### GitHub Actions 配置

```yaml
name: Complete Workflow Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run complete workflow test
      run: python examples/complete_workflow_test.py
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### 测试报告生成

```python
def generate_test_report(results):
    """生成测试报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed_tests": sum(1 for r in results if r['success']),
        "failed_tests": sum(1 for r in results if not r['success']),
        "average_time": sum(r.get('processing_time', 0) for r in results) / len(results),
        "details": results
    }
    
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return report
```

## 最佳实践

### 1. 测试隔离

- 每个测试使用独立的临时环境
- 测试完成后自动清理资源
- 避免测试间的相互影响

### 2. 数据一致性

- 使用固定的测试数据集
- 确保测试结果可重现
- 验证数据完整性

### 3. 错误处理

- 捕获并记录所有异常
- 提供详细的错误信息
- 实现优雅的失败处理

### 4. 性能监控

- 记录每个测试的执行时间
- 监控系统资源使用情况
- 设置性能基准和告警

### 5. 可维护性

- 使用清晰的测试命名
- 添加详细的注释和文档
- 保持测试代码的简洁性

## 总结

完整工作流端到端测试为Text2SQL多智能体系统提供了全面的质量保证：

✅ **功能完整性**: 覆盖所有主要使用场景  
✅ **性能验证**: 确保系统满足性能要求  
✅ **错误处理**: 验证系统的健壮性和恢复能力  
✅ **并发安全**: 确保多用户环境下的稳定性  
✅ **监控统计**: 提供系统运行状态的全面视图  
✅ **自动化**: 支持CI/CD集成和自动化测试  

通过定期运行这些测试，可以确保系统在生产环境中的稳定性和可靠性。
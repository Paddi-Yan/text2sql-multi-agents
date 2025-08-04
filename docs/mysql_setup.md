# MySQL数据库配置指南

## 概述

本项目已更新为使用MySQL数据库作为主要数据存储，替代了原来的SQLite。这提供了更好的性能、并发支持和企业级功能。

## 环境配置

### 1. 环境变量设置

项目根目录下的`.env`文件包含了数据库配置信息：

```env
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=text2sql_db
```

### 2. 依赖安装

确保安装了MySQL相关的Python依赖：

```bash
pip install PyMySQL python-dotenv
```

或者安装完整的依赖：

```bash
pip install -r requirements.txt
```

## MySQL服务器设置

### 1. 安装MySQL

**Windows:**
- 下载并安装MySQL Community Server
- 或使用XAMPP/WAMP等集成环境

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

### 2. 配置MySQL用户

连接到MySQL并创建用户（如果需要）：

```sql
-- 连接到MySQL
mysql -u root -p

-- 创建数据库用户（可选）
CREATE USER 'text2sql_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON text2sql_db.* TO 'text2sql_user'@'localhost';
FLUSH PRIVILEGES;
```

## 数据库初始化

### 1. 测试连接

首先测试数据库连接是否正常：

```bash
python scripts/test_mysql_connection.py
```

### 2. 初始化数据库

运行初始化脚本创建数据库和示例数据：

```bash
python scripts/init_mysql_db.py
```

这个脚本会：
- 创建`text2sql_db`数据库
- 创建示例表（users, products, orders, categories等）
- 插入示例数据用于测试

### 3. 验证安装

运行MySQL Selector示例来验证一切正常工作：

```bash
python examples/mysql_selector_example.py
```

## 数据库架构

初始化脚本会创建以下表结构：

### 用户表 (users)
- 用户基本信息：用户名、邮箱、姓名、年龄等
- 包含15个字段，支持用户画像和个人信息管理

### 产品表 (products)
- 产品信息：名称、描述、价格、分类等
- 包含17个字段，支持完整的产品管理

### 订单表 (orders)
- 订单信息：订单号、状态、金额、地址等
- 包含17个字段，支持完整的订单生命周期

### 订单项表 (order_items)
- 订单详情：产品、数量、价格等
- 支持多产品订单管理

### 分类表 (categories)
- 产品分类：支持层级分类结构
- 包含父子关系的分类管理

### 评价表 (reviews)
- 产品评价：评分、评论、验证状态等
- 支持用户反馈和产品质量评估

## 技术特性

### 1. 数据库适配器

`storage/mysql_adapter.py`提供了完整的MySQL数据库操作接口：

- **模式扫描**: 自动扫描数据库结构
- **元数据提取**: 获取表、列、主键、外键信息
- **样本数据**: 提取样本数据用于模式理解
- **查询执行**: 支持SQL查询执行
- **连接管理**: 自动连接管理和错误处理

### 2. Selector智能体增强

Selector智能体已更新以支持MySQL：

- **优先MySQL**: 优先尝试MySQL连接，SQLite作为备选
- **模式缓存**: 高效的模式信息缓存机制
- **智能裁剪**: 基于MySQL元数据的智能模式裁剪
- **外键分析**: 完整的外键关系识别和处理

### 3. 配置管理

通过`config/settings.py`统一管理数据库配置：

- **环境变量**: 支持从.env文件加载配置
- **连接字符串**: 自动生成MySQL连接字符串
- **多环境支持**: 支持开发、测试、生产环境配置

## 使用示例

### 基本使用

```python
from agents.selector_agent import SelectorAgent
from utils.models import ChatMessage

# 创建Selector智能体
selector = SelectorAgent(agent_name="MySQLSelector")

# 处理查询
message = ChatMessage(
    db_id="text2sql_db",
    query="Show all users with their order history"
)

response = selector.talk(message)

if response.success:
    print(f"Schema: {response.message.desc_str}")
    print(f"Pruned: {response.message.pruned}")
```

### 直接数据库操作

```python
from storage.mysql_adapter import MySQLAdapter

# 创建MySQL适配器
adapter = MySQLAdapter()

# 获取表列表
tables = adapter.get_table_names("text2sql_db")

# 执行查询
results = adapter.execute_query("SELECT * FROM users LIMIT 5")

# 扫描模式
db_info, db_stats = adapter.scan_database_schema("text2sql_db")
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查MySQL服务是否运行
   - 验证主机和端口配置
   - 确认防火墙设置

2. **认证失败**
   - 检查用户名和密码
   - 验证用户权限
   - 确认用户可以从指定主机连接

3. **数据库不存在**
   - 运行`python scripts/init_mysql_db.py`创建数据库
   - 检查数据库名称配置

4. **权限不足**
   - 确保用户有CREATE、SELECT、INSERT等权限
   - 检查数据库级别的权限设置

### 调试步骤

1. 测试基本连接：
   ```bash
   python scripts/test_mysql_connection.py
   ```

2. 检查MySQL服务状态：
   ```bash
   # Windows
   net start mysql
   
   # macOS/Linux
   sudo systemctl status mysql
   ```

3. 手动连接测试：
   ```bash
   mysql -h 127.0.0.1 -P 3306 -u root -p
   ```

4. 查看错误日志：
   - Windows: `C:\ProgramData\MySQL\MySQL Server 8.0\Data\*.err`
   - Linux: `/var/log/mysql/error.log`
   - macOS: `/usr/local/var/mysql/*.err`

## 性能优化

### 1. 索引优化

为常用查询字段添加索引：

```sql
-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- 订单表索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- 产品表索引
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_name ON products(name);
```

### 2. 连接池配置

在生产环境中配置连接池：

```python
# 在config/settings.py中添加
@dataclass
class DatabaseConfig:
    # ... 其他配置
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
```

### 3. 查询优化

- 使用EXPLAIN分析查询计划
- 避免SELECT *，只选择需要的列
- 合理使用LIMIT限制结果集大小
- 优化JOIN查询的顺序和条件

## 安全考虑

### 1. 连接安全

- 使用强密码
- 限制数据库用户权限
- 启用SSL连接（生产环境）
- 配置防火墙规则

### 2. SQL注入防护

- 使用参数化查询
- 验证和清理用户输入
- 实施最小权限原则
- 定期安全审计

### 3. 数据保护

- 定期备份数据库
- 加密敏感数据
- 实施访问控制
- 监控异常访问

## 迁移指南

### 从SQLite迁移

如果你之前使用SQLite，可以通过以下步骤迁移：

1. 导出SQLite数据：
   ```bash
   sqlite3 your_database.db .dump > data.sql
   ```

2. 转换SQL语法（如需要）
3. 导入到MySQL：
   ```bash
   mysql -u root -p text2sql_db < data.sql
   ```

### 数据同步

对于持续的数据同步，可以考虑：
- 使用ETL工具
- 编写数据迁移脚本
- 实施增量同步机制

## 监控和维护

### 1. 性能监控

- 监控查询执行时间
- 跟踪连接数和资源使用
- 分析慢查询日志

### 2. 定期维护

- 更新表统计信息
- 优化表结构
- 清理过期数据
- 检查和修复表

### 3. 备份策略

```bash
# 每日备份
mysqldump -u root -p text2sql_db > backup_$(date +%Y%m%d).sql

# 自动化备份脚本
0 2 * * * /usr/bin/mysqldump -u root -p text2sql_db > /backup/text2sql_$(date +\%Y\%m\%d).sql
```

通过以上配置和优化，你的Text2SQL多智能体系统将能够充分利用MySQL的强大功能，提供更好的性能和可靠性。
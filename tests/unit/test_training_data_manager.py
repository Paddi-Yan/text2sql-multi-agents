"""
Unit tests for training data management system.
"""

import unittest
import tempfile
import os
from datetime import datetime

from utils.training_models import TrainingData, TrainingDataType, TrainingDataStats
from utils.training_data_manager import TrainingDataManager
from utils.vectorization import VectorizationService, MetadataManager


class TestTrainingDataModels(unittest.TestCase):
    """测试训练数据模型"""
    
    def test_training_data_creation(self):
        """测试训练数据创建"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.DDL_STATEMENT,
            content="CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        self.assertEqual(training_data.id, "test_001")
        self.assertEqual(training_data.data_type, TrainingDataType.DDL_STATEMENT)
        self.assertIsInstance(training_data.created_at, datetime)
    
    def test_training_data_to_dict(self):
        """测试训练数据转换为字典"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.QUESTION_SQL_PAIR,
            content="Q: Show all users\nA: SELECT * FROM users;",
            metadata={"source": "test"},
            db_id="test_db",
            question="Show all users",
            sql="SELECT * FROM users;",
            tags=["query", "select"]
        )
        
        data_dict = training_data.to_dict()
        self.assertEqual(data_dict["id"], "test_001")
        self.assertEqual(data_dict["data_type"], "qa_pair")
        self.assertEqual(data_dict["question"], "Show all users")
        self.assertEqual(data_dict["sql"], "SELECT * FROM users;")
        self.assertEqual(data_dict["tags"], ["query", "select"])
    
    def test_training_data_from_dict(self):
        """测试从字典创建训练数据"""
        data_dict = {
            "id": "test_001",
            "data_type": "qa_pair",
            "content": "Q: Show all users\nA: SELECT * FROM users;",
            "metadata": {"source": "test"},
            "db_id": "test_db",
            "created_at": datetime.now().isoformat(),
            "question": "Show all users",
            "sql": "SELECT * FROM users;",
            "table_names": ["users"],
            "tags": ["query", "select"]
        }
        
        training_data = TrainingData.from_dict(data_dict)
        self.assertEqual(training_data.id, "test_001")
        self.assertEqual(training_data.data_type, TrainingDataType.QUESTION_SQL_PAIR)
        self.assertEqual(training_data.question, "Show all users")
        self.assertEqual(training_data.sql, "SELECT * FROM users;")


class TestTrainingDataManager(unittest.TestCase):
    """测试训练数据管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = TrainingDataManager()
    
    def test_add_training_data(self):
        """测试添加训练数据"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.DDL_STATEMENT,
            content="CREATE TABLE users (id INT PRIMARY KEY);",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        result = self.manager.add_training_data(training_data)
        self.assertTrue(result)
        self.assertEqual(len(self.manager.data_store), 1)
        self.assertEqual(self.manager.stats.total_count, 1)
        self.assertEqual(self.manager.stats.ddl_count, 1)
    
    def test_get_training_data(self):
        """测试获取训练数据"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.SQL_QUERY,
            content="SELECT * FROM users;",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        self.manager.add_training_data(training_data)
        retrieved_data = self.manager.get_training_data("test_001")
        
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data.id, "test_001")
        self.assertEqual(retrieved_data.content, "SELECT * FROM users;")
    
    def test_update_training_data(self):
        """测试更新训练数据"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.QUESTION_SQL_PAIR,
            content="Q: Show users\nA: SELECT * FROM users;",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        self.manager.add_training_data(training_data)
        
        updates = {
            "question": "Show all users",
            "tags": ["query", "select", "users"]
        }
        
        result = self.manager.update_training_data("test_001", updates)
        self.assertTrue(result)
        
        updated_data = self.manager.get_training_data("test_001")
        self.assertEqual(updated_data.question, "Show all users")
        self.assertEqual(updated_data.tags, ["query", "select", "users"])
    
    def test_delete_training_data(self):
        """测试删除训练数据"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.DOCUMENTATION,
            content="User table documentation",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        self.manager.add_training_data(training_data)
        self.assertEqual(len(self.manager.data_store), 1)
        
        result = self.manager.delete_training_data("test_001")
        self.assertTrue(result)
        self.assertEqual(len(self.manager.data_store), 0)
    
    def test_get_by_type(self):
        """测试按类型获取数据"""
        # 添加不同类型的数据
        ddl_data = TrainingData(
            id="ddl_001",
            data_type=TrainingDataType.DDL_STATEMENT,
            content="CREATE TABLE users (id INT);",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        sql_data = TrainingData(
            id="sql_001",
            data_type=TrainingDataType.SQL_QUERY,
            content="SELECT * FROM users;",
            metadata={"source": "test"},
            db_id="test_db"
        )
        
        self.manager.add_training_data(ddl_data)
        self.manager.add_training_data(sql_data)
        
        ddl_results = self.manager.get_by_type(TrainingDataType.DDL_STATEMENT)
        sql_results = self.manager.get_by_type(TrainingDataType.SQL_QUERY)
        
        self.assertEqual(len(ddl_results), 1)
        self.assertEqual(len(sql_results), 1)
        self.assertEqual(ddl_results[0].id, "ddl_001")
        self.assertEqual(sql_results[0].id, "sql_001")
    
    def test_search_by_content(self):
        """测试按内容搜索"""
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.QUESTION_SQL_PAIR,
            content="Q: Show all active users\nA: SELECT * FROM users WHERE active = 1;",
            metadata={"source": "test"},
            db_id="test_db",
            question="Show all active users",
            sql="SELECT * FROM users WHERE active = 1;"
        )
        
        self.manager.add_training_data(training_data)
        
        # 搜索内容
        results = self.manager.search_by_content("active users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "test_001")
        
        # 搜索SQL
        results = self.manager.search_by_content("WHERE active")
        self.assertEqual(len(results), 1)
    
    def test_export_import_data(self):
        """测试数据导出和导入"""
        # 添加测试数据
        training_data = TrainingData(
            id="test_001",
            data_type=TrainingDataType.QUESTION_SQL_PAIR,
            content="Q: Count users\nA: SELECT COUNT(*) FROM users;",
            metadata={"source": "test"},
            db_id="test_db",
            question="Count users",
            sql="SELECT COUNT(*) FROM users;",
            tags=["count", "aggregation"]
        )
        
        self.manager.add_training_data(training_data)
        
        # 导出数据
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            result = self.manager.export_data(temp_file)
            self.assertTrue(result)
            
            # 创建新的管理器并导入数据
            new_manager = TrainingDataManager()
            result = new_manager.import_data(temp_file)
            self.assertTrue(result)
            
            # 验证导入的数据
            self.assertEqual(len(new_manager.data_store), 1)
            imported_data = new_manager.get_training_data("test_001")
            self.assertIsNotNone(imported_data)
            self.assertEqual(imported_data.question, "Count users")
            self.assertEqual(imported_data.tags, ["count", "aggregation"])
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestMetadataManager(unittest.TestCase):
    """测试元数据管理器"""
    
    def test_extract_table_names_from_ddl(self):
        """测试从DDL提取表名"""
        ddl = """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        );
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            user_id INT
        );
        """
        
        table_names = MetadataManager.extract_table_names_from_ddl(ddl)
        self.assertIn("users", table_names)
        self.assertIn("orders", table_names)
    
    def test_extract_table_names_from_sql(self):
        """测试从SQL提取表名"""
        sql = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name"
        
        table_names = MetadataManager.extract_table_names_from_sql(sql)
        self.assertIn("users", table_names)
        self.assertIn("orders", table_names)
    
    def test_extract_tags_from_content(self):
        """测试从内容提取标签"""
        sql_content = "SELECT * FROM users WHERE active = 1 ORDER BY name"
        
        tags = MetadataManager.extract_tags_from_content(sql_content, "sql")
        self.assertIn("sql", tags)
        self.assertIn("query", tags)
        self.assertIn("filtering", tags)
        self.assertIn("sorting", tags)


if __name__ == '__main__':
    unittest.main()
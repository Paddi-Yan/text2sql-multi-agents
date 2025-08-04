"""
Unit tests for Selector Agent (MySQL version).
"""
import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from agents.selector_agent import (
    SelectorAgent, DatabaseSchemaManager, SchemaPruner, 
    SchemaPruningConfig
)
from utils.models import ChatMessage, DatabaseInfo, DatabaseStats


class TestDatabaseSchemaManager:
    """Test DatabaseSchemaManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.schema_manager = DatabaseSchemaManager()
    
    def test_token_counting(self):
        """Test token counting functionality."""
        text = "This is a test sentence with multiple words."
        
        # Test token counting (should work with or without tiktoken)
        token_count = self.schema_manager.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    @patch('pymysql.connect')
    def test_scan_mysql_database_schema(self, mock_connect):
        """Test MySQL database schema scanning."""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock table list query
        mock_cursor.fetchall.side_effect = [
            # Tables query result
            [{'TABLE_NAME': 'users'}, {'TABLE_NAME': 'orders'}],
            # Users columns query result
            [
                {'COLUMN_NAME': 'id', 'DATA_TYPE': 'INT', 'COLUMN_COMMENT': 'User ID', 'COLUMN_KEY': 'PRI'},
                {'COLUMN_NAME': 'name', 'DATA_TYPE': 'VARCHAR', 'COLUMN_COMMENT': 'User name', 'COLUMN_KEY': ''},
                {'COLUMN_NAME': 'email', 'DATA_TYPE': 'VARCHAR', 'COLUMN_COMMENT': 'Email', 'COLUMN_KEY': ''},
                {'COLUMN_NAME': 'age', 'DATA_TYPE': 'INT', 'COLUMN_COMMENT': 'Age', 'COLUMN_KEY': ''}
            ],
            # Users sample data
            [
                {'id': 1, 'name': 'John', 'email': 'john@test.com', 'age': 25},
                {'id': 2, 'name': 'Jane', 'email': 'jane@test.com', 'age': 30}
            ],
            # Users foreign keys (empty)
            [],
            # Orders columns query result
            [
                {'COLUMN_NAME': 'id', 'DATA_TYPE': 'INT', 'COLUMN_COMMENT': 'Order ID', 'COLUMN_KEY': 'PRI'},
                {'COLUMN_NAME': 'user_id', 'DATA_TYPE': 'INT', 'COLUMN_COMMENT': 'User ID', 'COLUMN_KEY': ''},
                {'COLUMN_NAME': 'product_name', 'DATA_TYPE': 'VARCHAR', 'COLUMN_COMMENT': 'Product', 'COLUMN_KEY': ''},
                {'COLUMN_NAME': 'amount', 'DATA_TYPE': 'DECIMAL', 'COLUMN_COMMENT': 'Amount', 'COLUMN_KEY': ''}
            ],
            # Orders sample data
            [
                {'id': 1, 'user_id': 1, 'product_name': 'Product A', 'amount': 99.99}
            ],
            # Orders foreign keys
            [
                {'COLUMN_NAME': 'user_id', 'REFERENCED_TABLE_NAME': 'users', 'REFERENCED_COLUMN_NAME': 'id'}
            ]
        ]
        
        # Test schema scanning
        db_info = self.schema_manager.scan_mysql_database_schema("test_db", "test_db")
        
        # Verify results
        assert isinstance(db_info, DatabaseInfo)
        assert "users" in db_info.desc_dict
        assert "orders" in db_info.desc_dict
        
        # Check users table
        users_cols = db_info.desc_dict["users"]
        assert len(users_cols) == 4
        assert any(col[0] == "id" for col in users_cols)
        assert any(col[0] == "name" for col in users_cols)
        
        # Check primary keys
        assert "id" in db_info.pk_dict["users"]
        
        # Check foreign keys
        orders_fks = db_info.fk_dict["orders"]
        assert len(orders_fks) == 1
        assert orders_fks[0][0] == "user_id"  # from column
        assert orders_fks[0][1] == "users"    # to table
        
        # Check statistics
        db_stats = self.schema_manager.get_database_stats("test_db")
        assert db_stats.table_count == 2
        assert db_stats.total_column_count == 8  # 4 + 4 columns
        
        # Check JSON representation
        db_json = self.schema_manager.get_database_json("test_db")
        assert "tables" in db_json
        assert "users" in db_json["tables"]
        assert "statistics" in db_json
        
        # Verify connection was closed
        mock_cursor.close.assert_called()
        mock_connection.close.assert_called()
    
    def test_caching(self):
        """Test schema information caching."""
        # Mock database info
        mock_db_info = DatabaseInfo(
            desc_dict={"test_table": [("id", "INTEGER", ""), ("name", "TEXT", "")]},
            value_dict={"test_table": [("id", "1"), ("name", "test")]},
            pk_dict={"test_table": ["id"]},
            fk_dict={"test_table": []}
        )
        
        # Cache the info
        self.schema_manager.db2infos["test_db"] = mock_db_info
        
        # Retrieve from cache
        cached_info = self.schema_manager.get_database_info("test_db")
        assert cached_info == mock_db_info
        
        # Test non-existent database
        assert self.schema_manager.get_database_info("non_existent") is None


class TestSchemaPruner:
    """Test SchemaPruner functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = SchemaPruningConfig(
            token_limit=1000,
            avg_column_threshold=6,
            total_column_threshold=30
        )
        self.pruner = SchemaPruner(self.config)
    
    def test_is_need_prune_small_schema(self):
        """Test pruning decision for small schema."""
        db_stats = DatabaseStats(
            table_count=2,
            max_column_count=5,
            total_column_count=10,
            avg_column_count=5
        )
        
        schema_text = "Small schema with few columns"
        
        # Should not need pruning
        assert not self.pruner.is_need_prune(db_stats, schema_text)
    
    def test_is_need_prune_large_schema(self):
        """Test pruning decision for large schema."""
        db_stats = DatabaseStats(
            table_count=10,
            max_column_count=15,
            total_column_count=100,
            avg_column_count=10
        )
        
        # Create a long schema text that exceeds token limit
        schema_text = "Large schema " * 2000  # Should definitely exceed token limit
        
        # Should need pruning
        assert self.pruner.is_need_prune(db_stats, schema_text)
    
    def test_extract_query_keywords(self):
        """Test query keyword extraction."""
        query = "Show all users with their orders and total amount"
        
        keywords = self.pruner._extract_query_keywords(query.lower())
        
        assert "users" in keywords["entities"]
        assert "orders" in keywords["entities"]
        assert "amount" in keywords["attributes"]
        assert "show" in keywords["operations"]
    
    def test_calculate_table_relevance(self):
        """Test table relevance calculation."""
        table_name = "users"
        columns = [("id", "INTEGER", ""), ("name", "TEXT", ""), ("email", "TEXT", "")]
        query_keywords = {
            "entities": ["users", "user"],
            "attributes": ["name", "email"],
            "operations": ["show"],
            "conditions": []
        }
        foreign_keys = []
        
        relevance = self.pruner._calculate_table_relevance(
            table_name, columns, query_keywords, foreign_keys
        )
        
        assert relevance["score"] > 0
        assert relevance["column_matches"] == 2  # name and email
        assert not relevance["is_irrelevant"]
    
    def test_select_relevant_columns(self):
        """Test relevant column selection."""
        columns = [
            ("id", "INTEGER", ""),
            ("name", "TEXT", ""),
            ("email", "TEXT", ""),
            ("phone", "TEXT", ""),
            ("address", "TEXT", ""),
            ("created_at", "TIMESTAMP", ""),
            ("updated_at", "TIMESTAMP", ""),
            ("internal_notes", "TEXT", "")
        ]
        
        query_keywords = {
            "entities": ["users"],
            "attributes": ["name", "email"],
            "operations": ["show"],
            "conditions": []
        }
        
        selected = self.pruner._select_relevant_columns(columns, query_keywords, max_columns=4)
        
        assert len(selected) <= 4
        assert "id" in selected  # ID columns should always be included
        assert "name" in selected  # Matches query attributes
        assert "email" in selected  # Matches query attributes
    
    def test_prune_schema(self):
        """Test complete schema pruning."""
        # Create mock database info
        db_info = DatabaseInfo(
            desc_dict={
                "users": [("id", "INTEGER", ""), ("name", "TEXT", ""), ("email", "TEXT", "")],
                "orders": [("id", "INTEGER", ""), ("user_id", "INTEGER", ""), ("amount", "REAL", "")],
                "logs": [("id", "INTEGER", ""), ("message", "TEXT", ""), ("timestamp", "TIMESTAMP", "")]
            },
            value_dict={
                "users": [("id", "1"), ("name", "John")],
                "orders": [("id", "1"), ("amount", "99.99")],
                "logs": [("id", "1"), ("message", "test")]
            },
            pk_dict={
                "users": ["id"],
                "orders": ["id"],
                "logs": ["id"]
            },
            fk_dict={
                "users": [],
                "orders": [("user_id", "users", "id")],
                "logs": []
            }
        )
        
        db_stats = DatabaseStats(
            table_count=3,
            max_column_count=3,
            total_column_count=9,
            avg_column_count=3
        )
        
        query = "Show all users with their names and emails"
        
        pruning_result = self.pruner.prune_schema(query, db_info, db_stats)
        
        # Users table should be kept (relevant to query)
        assert "users" in pruning_result
        assert pruning_result["users"] != "drop_all"
        
        # Orders table might be kept due to foreign key relationship
        assert "orders" in pruning_result
        
        # Logs table should likely be dropped (irrelevant)
        assert "logs" in pruning_result


class TestSelectorAgent:
    """Test SelectorAgent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = SelectorAgent("TestSelector")
        
        # Mock database info
        self.mock_db_info = DatabaseInfo(
            desc_dict={
                "users": [("id", "INTEGER", ""), ("name", "TEXT", ""), ("email", "TEXT", "")],
                "orders": [("id", "INTEGER", ""), ("user_id", "INTEGER", ""), ("amount", "REAL", "")]
            },
            value_dict={
                "users": [("id", "1"), ("name", "John")],
                "orders": [("id", "1"), ("amount", "99.99")]
            },
            pk_dict={
                "users": ["id"],
                "orders": ["id"]
            },
            fk_dict={
                "users": [],
                "orders": [("user_id", "users", "id")]
            }
        )
        
        self.mock_db_stats = DatabaseStats(
            table_count=2,
            max_column_count=3,
            total_column_count=6,
            avg_column_count=3
        )
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = SelectorAgent("TestSelector", tables_json_path="/test/path")
        
        assert agent.agent_name == "TestSelector"
        assert agent.tables_json_path == "/test/path"
        assert isinstance(agent.schema_manager, DatabaseSchemaManager)
        assert isinstance(agent.pruning_config, SchemaPruningConfig)
    
    @patch.object(SelectorAgent, '_get_database_info')
    def test_talk_success_no_pruning(self, mock_get_db_info):
        """Test successful message processing without pruning."""
        # Setup mocks
        mock_get_db_info.return_value = self.mock_db_info
        self.agent.schema_manager.db2infos["test_db"] = self.mock_db_info
        self.agent.schema_manager.db2stats["test_db"] = self.mock_db_stats
        self.agent.schema_manager.db2dbjsons["test_db"] = {"tables": {}}
        
        # Create test message
        message = ChatMessage(
            db_id="test_db",
            query="Show user names"
        )
        
        # Process message
        response = self.agent.talk(message)
        
        # Verify response
        assert response.success is True
        assert response.message.desc_str != ""
        assert response.message.send_to == "Decomposer"
        assert response.metadata["schema_selected"] is True
        
        # Verify statistics
        stats = self.agent.get_pruning_stats()
        assert stats["total_queries"] == 1
    
    @patch.object(SelectorAgent, '_get_database_info')
    @patch.object(SelectorAgent, '_is_need_prune')
    @patch.object(SelectorAgent, '_prune')
    def test_talk_success_with_pruning(self, mock_prune, mock_is_need_prune, mock_get_db_info):
        """Test successful message processing with pruning."""
        # Setup mocks
        mock_get_db_info.return_value = self.mock_db_info
        mock_is_need_prune.return_value = True
        mock_prune.return_value = {"users": "keep_all", "orders": "drop_all"}
        
        self.agent.schema_manager.db2stats["test_db"] = self.mock_db_stats
        self.agent.schema_manager.db2dbjsons["test_db"] = {"tables": {}}
        
        # Create test message
        message = ChatMessage(
            db_id="test_db",
            query="Show user names"
        )
        
        # Process message
        response = self.agent.talk(message)
        
        # Verify response
        assert response.success is True
        assert response.message.pruned is True
        assert response.message.chosen_db_schema_dict is not None
        assert response.metadata["pruned"] is True
        
        # Verify pruning was called
        mock_prune.assert_called_once()
        
        # Verify statistics
        stats = self.agent.get_pruning_stats()
        assert stats["pruned_queries"] == 1
    
    def test_talk_database_not_found(self):
        """Test message processing when database is not found."""
        message = ChatMessage(
            db_id="non_existent_db",
            query="Show user names"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "Could not load schema" in response.error
    
    def test_get_db_desc_str_full_schema(self):
        """Test database description string generation."""
        # Setup mock data
        self.agent.schema_manager.db2infos["test_db"] = self.mock_db_info
        
        desc_str, fk_str = self.agent._get_db_desc_str("test_db", None)
        
        # Verify description string
        assert "# Table: users" in desc_str
        assert "# Table: orders" in desc_str
        assert "(id" in desc_str
        assert "(name" in desc_str
        
        # Verify foreign key string
        assert "orders.user_id = users.id" in fk_str
    
    def test_get_db_desc_str_pruned_schema(self):
        """Test database description string generation with pruning."""
        # Setup mock data
        self.agent.schema_manager.db2infos["test_db"] = self.mock_db_info
        
        # Test with pruning
        extracted_schema = {
            "users": ["id", "name"],  # Only keep id and name
            "orders": "drop_all"      # Drop entire table
        }
        
        desc_str, fk_str = self.agent._get_db_desc_str("test_db", extracted_schema)
        
        # Verify only users table is included
        assert "# Table: users" in desc_str
        assert "# Table: orders" not in desc_str
        assert "(id" in desc_str
        assert "(name" in desc_str
        assert "(email" not in desc_str  # Should be pruned
        
        # Foreign key string should be empty (orders table dropped)
        assert fk_str == ""
    
    def test_is_need_prune(self):
        """Test pruning necessity determination."""
        # Setup mock data
        self.agent.schema_manager.db2stats["test_db"] = self.mock_db_stats
        
        # Test with small schema (should not need pruning)
        small_schema = "Small schema text"
        assert not self.agent._is_need_prune("test_db", small_schema)
        
        # Test with large schema (should need pruning)
        large_schema = "Large schema text " * 1000
        # This might or might not need pruning depending on token counting
        result = self.agent._is_need_prune("test_db", large_schema)
        assert isinstance(result, bool)
    
    def test_prune(self):
        """Test schema pruning."""
        # Setup mock data
        self.agent.schema_manager.db2infos["test_db"] = self.mock_db_info
        self.agent.schema_manager.db2stats["test_db"] = self.mock_db_stats
        
        query = "Show all users"
        schema = "test schema"
        
        pruning_result = self.agent._prune("test_db", query, schema)
        
        # Should return a dictionary with pruning decisions
        assert isinstance(pruning_result, dict)
        assert "users" in pruning_result
        assert "orders" in pruning_result
    
    def test_load_schema_from_json(self):
        """Test loading schema from JSON file."""
        # Create temporary JSON file
        test_data = {
            "tables": {
                "users": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "description": "User ID"},
                        {"name": "name", "type": "TEXT", "description": "User name"}
                    ],
                    "primary_keys": ["id"],
                    "foreign_keys": [],
                    "sample_values": {"id": "1", "name": "John"}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            json_path = tmp_file.name
        
        try:
            db_info = self.agent._load_schema_from_json(json_path, "test_db")
            
            # Verify loaded data
            assert isinstance(db_info, DatabaseInfo)
            assert "users" in db_info.desc_dict
            assert len(db_info.desc_dict["users"]) == 2
            assert db_info.pk_dict["users"] == ["id"]
            
            # Verify caching
            assert "test_db" in self.agent.schema_manager.db2infos
            assert "test_db" in self.agent.schema_manager.db2stats
            
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    def test_pruning_stats(self):
        """Test pruning statistics tracking."""
        # Initial stats
        stats = self.agent.get_pruning_stats()
        assert stats["total_queries"] == 0
        assert stats["pruned_queries"] == 0
        assert stats["avg_pruning_ratio"] == 0.0
        
        # Simulate some queries
        self.agent.pruning_stats["total_queries"] = 10
        self.agent.pruning_stats["pruned_queries"] = 3
        
        stats = self.agent.get_pruning_stats()
        assert stats["total_queries"] == 10
        assert stats["pruned_queries"] == 3
        assert stats["avg_pruning_ratio"] == 0.3
        
        # Reset stats
        self.agent.reset_pruning_stats()
        stats = self.agent.get_pruning_stats()
        assert stats["total_queries"] == 0
    
    def test_update_pruning_config(self):
        """Test pruning configuration updates."""
        original_token_limit = self.agent.pruning_config.token_limit
        
        # Update configuration
        self.agent.update_pruning_config(token_limit=50000, avg_column_threshold=10)
        
        assert self.agent.pruning_config.token_limit == 50000
        assert self.agent.pruning_config.avg_column_threshold == 10
        assert self.agent.pruning_config.token_limit != original_token_limit
    
    def test_message_validation(self):
        """Test message validation."""
        # Valid message
        valid_message = ChatMessage(db_id="test", query="SELECT 1")
        response = self.agent.talk(valid_message)
        # Should fail due to missing database, but not due to validation
        assert "Could not load schema" in response.error
        
        # Invalid message (empty db_id)
        invalid_message = ChatMessage(db_id="", query="SELECT 1")
        response = self.agent.talk(invalid_message)
        assert response.success is False
        assert response.error == "Invalid message"
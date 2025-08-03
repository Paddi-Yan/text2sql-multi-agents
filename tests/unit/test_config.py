"""
Unit tests for configuration management.
"""
import os
import pytest
from config.settings import SystemConfig, LLMConfig, DatabaseConfig


class TestSystemConfig:
    """Test system configuration."""
    
    def test_system_config_initialization(self):
        """Test system config can be initialized."""
        config = SystemConfig()
        
        assert config.llm_config is not None
        assert config.database_config is not None
        assert config.cache_config is not None
        assert config.vector_store_config is not None
        assert config.security_config is not None
        assert config.monitoring_config is not None
    
    def test_llm_config_defaults(self):
        """Test LLM config default values."""
        config = LLMConfig()
        
        assert config.model_name == "gpt-4"
        assert config.max_tokens == 2000
        assert config.temperature == 0.1
        assert config.timeout == 30
    
    def test_database_config_env_vars(self):
        """Test database config reads environment variables."""
        # Set environment variables
        os.environ["DB_HOST"] = "test-host"
        os.environ["DB_PORT"] = "5433"
        os.environ["DB_USER"] = "test-user"
        
        config = DatabaseConfig()
        
        assert config.host == "test-host"
        assert config.port == 5433
        assert config.username == "test-user"
        
        # Clean up
        del os.environ["DB_HOST"]
        del os.environ["DB_PORT"]
        del os.environ["DB_USER"]
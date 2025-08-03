# Project Structure

## Organization Principles

- **Agent-Based Architecture**: Separate modules for each intelligent agent
- **Service Layer Pattern**: Clear separation between business logic and infrastructure
- **Configuration Management**: Centralized configuration for different environments
- **Modular Design**: Independent components for easy testing and maintenance

## Recommended Directory Structure

```
/
├── agents/                 # Multi-agent implementations
│   ├── intent_agent.py    # Natural language intent understanding
│   ├── sql_agent.py       # SQL generation logic
│   ├── validation_agent.py # SQL validation and security checks
│   └── optimization_agent.py # Query optimization
├── services/              # Core business services
│   ├── text2sql_service.py # Main service orchestration
│   ├── memory_service.py   # Learning and memory management
│   └── cache_service.py    # Redis caching operations
├── storage/               # Data access layer
│   ├── vector_store.py    # Milvus vector database operations
│   ├── database_adapter.py # Multi-database connectivity
│   └── schema_manager.py   # Database schema discovery
├── utils/                 # Shared utilities
│   ├── security.py        # SQL injection prevention
│   ├── retry.py          # Fault tolerance mechanisms
│   └── monitoring.py     # Logging and metrics
├── config/               # Configuration files
│   ├── settings.py       # Application settings
│   └── database.yaml     # Database configurations
├── tests/                # Test suites
│   ├── unit/            # Unit tests for individual components
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test data and mocks
└── docs/                # Documentation
    ├── api.md           # API documentation
    └── deployment.md    # Deployment guide
```

## Key Conventions

- **Agent Naming**: All agent files end with `_agent.py`
- **Service Layer**: Business logic in `services/` directory
- **Storage Abstraction**: Database operations isolated in `storage/` layer
- **Configuration**: Environment-specific configs in `config/` directory
- **Testing**: Comprehensive test coverage with clear separation of test types

## File Naming Patterns

- Snake_case for Python files and directories
- Descriptive names that indicate component purpose
- Agent files clearly identified with `_agent` suffix
- Service files use `_service` suffix for business logic components
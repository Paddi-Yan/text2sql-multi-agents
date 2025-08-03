# Text2SQL Multi-Agent Service

A production-ready Text2SQL service system that combines **Vanna.ai's RAG training mechanism** with **MAC-SQL's three-agent collaboration architecture**, delivering enterprise-grade natural language to SQL conversion with continuous learning capabilities.

## Core Innovation

This system uniquely integrates two proven approaches:

- **Vanna.ai's Training-Asking Paradigm**: Supports DDL statements, documentation, SQL examples, and question-SQL pairs for comprehensive context building
- **MAC-SQL's Agent Collaboration**: Specialized agents for schema selection, query decomposition, and execution validation
- **Enhanced RAG Architecture**: Vector-based semantic retrieval with intelligent context assembly

## Features

- **Vanna.ai-Style Training System**: Multi-type training data support (DDL, docs, SQL, QA pairs, domain knowledge)
- **MAC-SQL Agent Architecture**: Collaborative Selector, Decomposer, and Refiner agents
- **Intelligent Memory & Learning**: Continuous improvement from user feedback and successful queries
- **Enterprise-Grade Reliability**: Built with fault tolerance, retry mechanisms, and high availability
- **Vector Similarity Search**: Milvus-powered semantic matching and context retrieval
- **High-Performance Caching**: Redis-based multi-layer caching with sub-100ms response times
- **Security & Access Control**: SQL injection prevention and role-based permissions

## Architecture

The system combines the best of both worlds:

### Vanna.ai Training Phase
- **DDL Training**: Understands database structure and relationships
- **Documentation Training**: Learns business context and domain knowledge
- **SQL Example Training**: Captures query patterns and best practices
- **QA Pair Training**: Direct question-to-SQL mapping for accuracy
- **Auto-Learning**: Continuous improvement from successful interactions

### MAC-SQL Agent Collaboration
- **Selector**: Database schema analysis and intelligent pruning
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
export DB_HOST="localhost"
export REDIS_HOST="localhost"
export MILVUS_HOST="localhost"
```

3. Start the service:
```bash
python -m services.chat_manager
```

## Project Structure

```
├── agents/                 # Multi-agent implementations
├── services/              # Core business services
├── storage/               # Data access layer
├── utils/                 # Shared utilities and models
├── config/               # Configuration management
└── tests/                # Test suites
```

## Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Architecture Overview](docs/architecture.md)

## License

MIT License
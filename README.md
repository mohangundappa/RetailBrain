# Staples Brain

An advanced multi-agent AI orchestration platform for intelligent system management, featuring a modular architecture and comprehensive developer tooling.

## Overview

Staples Brain is an AI super-brain agent system specifically designed for Staples Customer Engagement. It focuses on Sales and Services, serving as an integration hub for specialized agents (Order Tracking, Reset Password, Store Locator, and others). 

## Architecture

The system has a simplified architecture with two main components:

1. **Backend**: Pure FastAPI implementation with no Flask/WSGI compatibility layers
2. **Frontend**: React-based UI for user interactions

All services are consolidated within the backend component, maintaining a clear separation through a standardized API gateway serving as the primary entry point for all interactions.

### Application Flow

1. **API Gateway**: All requests enter through `api_gateway.py`, which routes them to the appropriate endpoints.
2. **Services Layer**: The `services` module contains business logic for handling requests.
3. **Brain Orchestration**: The optimized brain service manages agent selection and execution.
4. **Agent Framework**: Specialized agents provide domain-specific handling of user requests.
5. **State Persistence**: Conversation state is maintained for context-aware interactions.

For technical details on the backend architecture, see [backend/README.md](backend/README.md).

## Key Technologies

- **Python 3.12+**: For backend and agent logic
- **FastAPI**: Main API framework (replacing older Flask implementation)
- **PostgreSQL with PgVec**: For database storage including vector embeddings
- **LangChain/LangGraph**: For contextual intelligence
- **OpenAI GPT-4o**: Core language model integration
- **LangSmith**: For telemetry and observability

## Project Structure

```
staples-brain/
├── backend/               # Backend services and components
│   ├── agents/            # Agent implementations
│   │   ├── framework/     # Base agent framework implementations
│   │   └── base_agent.py  # Core agent interface
│   ├── api/               # API endpoints for specific services
│   │   ├── optimized_chat.py  # Chat endpoints
│   │   └── state_management.py # State management endpoints
│   ├── brain/             # Core brain logic
│   │   └── optimized/     # Optimized brain implementation
│   │       ├── embedding_service.py # Embedding service
│   │       ├── factory.py # Agent factory
│   │       ├── router.py  # Agent router
│   │       └── vector_store.py # Vector database 
│   ├── config/            # Configuration management
│   ├── database/          # Database schemas and connections
│   ├── repositories/      # Data access layer
│   ├── services/          # Business logic services
│   │   ├── chat_service.py # Chat processing
│   │   ├── optimized_brain_service.py # Brain orchestration
│   │   └── telemetry_service.py # Logging and metrics
│   ├── utils/             # Utility functions
│   ├── api_gateway.py     # Main FastAPI application
│   └── main.py            # Backend initialization
├── docs/                  # Documentation
│   ├── api/               # API documentation
│   ├── development/       # Development guidelines
│   ├── installation/      # Installation guides
│   └── user-guides/       # End-user documentation
├── frontend/              # React frontend application
├── .env                   # Environment variables (local development)
├── .env.example           # Example environment variables
├── main.py                # ASGI application entry point 
├── run.py                 # Application runner with error handling
└── run_tests.py           # Test runner script
```

## Running the Application

```bash
# Start the application
python run.py

# Run tests
python run_tests.py
```

## Environment Variables

The application requires several environment variables to be set. See `.env.example` for required variables.

## API Reference

API documentation is available at `/static/documentation` when the server is running.

## Contributing

See the development guidelines in the [docs/development](docs/development) directory for more information on contributing to the project.

## License

Proprietary - All rights reserved
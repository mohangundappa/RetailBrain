# Staples Brain Backend Architecture

## Directory Structure

The backend is organized into several folders, each with specific responsibilities:

### Core Components

- `agents/` - Agent definitions and frameworks
  - `framework/` - Base implementations for different agent types
  - `base_agent.py` - Core agent interface used by the system

- `api/` - API endpoint definitions
  - `optimized_chat.py` - Optimized chat API endpoints
  - `state_management.py` - State persistence and session management

- `brain/` - Brain service components
  - `optimized/` - Optimized brain implementation
    - `agent_definition.py` - Agent definition model
    - `embedding_service.py` - Text embedding service
    - `factory.py` - Agent creation factory
    - `router.py` - Agent routing and selection
    - `state_persistence.py` - Conversation state management
    - `vector_store.py` - Vector database for agent selection

- `config/` - Configuration management
  - `settings.py` - Application settings

- `database/` - Database connections and schema
  - `db.py` - Database connection management
  - `init_agent_db.py` - Agent schema initialization
  - `init_state_db.py` - State persistence schema
  - `initialize_db.py` - Main database initialization

- `repositories/` - Data access layer
  - `agent_repository.py` - Agent data access

- `services/` - Business logic services
  - `chat_service.py` - Chat processing service
  - `llm_service.py` - LLM integration
  - `optimized_brain_service.py` - Main brain orchestration service
  - `optimized_dependencies.py` - Dependency injection for services
  - `telemetry_service.py` - Usage metrics and logging

- `utils/` - Utility functions
  - `api_utils.py` - API helper functions

### Entry Points

- `api_gateway.py` - FastAPI application definition and middleware
- `main.py` - Application initialization and runner functions

## Naming Conventions

- Files are named using snake_case
- Classes are named using PascalCase
- Functions and variables are named using snake_case
- Constants are named using UPPER_SNAKE_CASE

## Architecture Overview

1. The application is structured around a FastAPI application in `api_gateway.py`
2. Core initialization happens in `main.py`
3. The primary workflow is:
   - API requests flow through routers in the `api/` directory
   - Service layer processes business logic
   - Brain services manage agent selection and orchestration
   - Agent framework handles specialized responses
   - State persistence maintains conversation context

## Key Design Patterns

1. **Dependency Injection** - Used throughout for services and repositories
2. **Repository Pattern** - Data access abstracted behind repositories
3. **Factory Pattern** - Used for creating agent instances
4. **Strategy Pattern** - Used for agent selection and routing
5. **Observer Pattern** - Used for telemetry and monitoring

## Future Improvements

1. Rename folders to better reflect their functional domains:
   - `brain/optimized/` → `orchestration/`
   - `agents/framework/` → `agents/models/`
   - `api/` → `endpoints/`

2. Restructure files for better cohesion:
   - Move embedding service to its own folder
   - Group state management components together
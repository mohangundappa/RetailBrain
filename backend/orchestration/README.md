# Orchestration Module

This module is responsible for the orchestration of agents within the Staples Brain system. It provides mechanisms for:

1. **Agent Selection & Routing**: Determining which specialized agent should handle a user request
2. **State Management**: Persisting conversation state across interactions
3. **Agent Definitions**: Structured definitions of agent capabilities and configurations
4. **Agent Factory**: Creating and managing agent instances from definitions

## Structure

The orchestration module is organized into several key components:

- **`__init__.py`**: Bridge module that re-exports components from their legacy locations
- **`agent_definition.py`**: Defines agent capabilities and structure (future)
- **`factory.py`**: Creates and manages agent definitions (future)
- **`router.py`**: Router with keyword pre-filtering (future)
- **`state_persistence.py`**: Manages conversation state persistence (future)

## Migration Strategy

This module is part of a gradual refactoring process to improve code organization:

1. Create backward-compatible bridge modules (current phase)
2. Gradually migrate functionality from `backend/brain/optimized/` to `backend/orchestration/`
3. Update imports throughout the codebase to point to new locations
4. Once all references are updated, remove legacy code paths

## Usage

The module's components can be imported directly from `backend.orchestration`, which will
automatically resolve to the correct implementation regardless of whether it is in the
new location or still in the legacy location:

```python
from backend.orchestration import (
    AgentDefinition,
    AgentRouter,
    create_db_tables
)
```

This approach ensures backward compatibility during the migration process.
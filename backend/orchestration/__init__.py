"""
Orchestration module for Staples Brain.

This module provides the components for agent orchestration, routing, and state management.
It is the replacement for the optimized brain functionality.

This module re-exports all the components from the optimized brain to allow for a
gradual migration from backend.brain.optimized to backend.orchestration.
"""

# Re-export all components from optimized brain for backward compatibility
from backend.brain.optimized.agent_definition import (
    AgentDefinition,
    PatternCapability,
    AgentTool,
    EntityDefinition
)
from backend.brain.optimized.embedding_service import (
    EmbeddingService,
)
from backend.brain.optimized.factory import (
    OptimizedAgentFactory,
)
from backend.brain.optimized.router import (
    OptimizedAgentRouter,
)
from backend.brain.optimized.state_persistence import (
    create_db_tables,
    StatePersistenceManager,
    resilient_persist_state,
    resilient_create_checkpoint,
    resilient_recover_state,
    resilient_rollback_to_checkpoint,
    get_most_recent_state,
    check_db_connection,
    process_pending_operations
)
# Import from state_recovery module
from backend.brain.optimized.state_persistence import (
    resilient_recover_state as recover_agent_state,
    get_most_recent_state as get_all_state_entries
)
from backend.brain.optimized.vector_store import (
    AgentVectorStore,
)
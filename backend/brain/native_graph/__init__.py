"""
Native LangGraph implementation for Staples Brain.

This package contains the LangGraph native implementation of the Staples Brain
orchestration system, designed to replace the custom orchestrator with a more
declarative, graph-based approach.
"""

from backend.brain.native_graph.state_definitions import OrchestrationState
from backend.brain.native_graph.graph_orchestrator import GraphOrchestrator
from backend.brain.native_graph.node_functions import (
    classify_intent,
    select_agent,
    process_with_agent,
    update_memory,
    handle_special_cases
)

__all__ = [
    "GraphOrchestrator",
    "OrchestrationState",
    "classify_intent",
    "select_agent",
    "process_with_agent",
    "update_memory",
    "handle_special_cases"
]
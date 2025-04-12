"""
Type definitions for LangGraph state objects.

This module provides TypedDict definitions for the various state objects used in
the LangGraph orchestration system, enabling better type checking and documentation.
"""

from typing import Dict, List, Any, Optional, TypedDict, Union

# Basic state components
class ConversationState(TypedDict, total=False):
    """Conversation state including messages and metadata."""
    session_id: str
    messages: List[Dict[str, Any]]
    last_user_message: str
    last_assistant_message: str
    context: Dict[str, Any]
    user_info: Dict[str, Any]


class MemoryState(TypedDict, total=False):
    """Memory state for conversation history and context."""
    memory_last_updated: str
    working_memory: Dict[str, Any]
    episodic_memory: List[Dict[str, Any]]
    entity_memory: Dict[str, Any]
    memory_ids: Dict[str, str]


class AgentState(TypedDict, total=False):
    """State related to agent selection and execution."""
    selected_agent: str
    available_agents: List[str]
    special_case_detected: bool
    special_case_type: str
    special_case_response: str
    confidence_scores: Dict[str, float]
    last_agent_response: Dict[str, Any]
    execution_id: str


class ErrorState(TypedDict, total=False):
    """Error tracking information."""
    node: str
    error: str
    error_type: str
    timestamp: str
    traceback: str
    additional_info: Dict[str, Any]


class ExecutionState(TypedDict, total=False):
    """Execution metadata and tracking."""
    current_step: str
    execution_path: List[str]
    start_time: str
    last_updated: str
    errors: List[ErrorState]
    performance: Dict[str, float]
    last_persisted_state_id: str
    last_persisted_at: str
    checkpoints: Dict[str, Dict[str, Any]]


# Main orchestration state
class OrchestrationState(TypedDict, total=False):
    """
    Complete orchestration state for the LangGraph system.
    
    This represents the full state object passed between node functions.
    """
    conversation: ConversationState
    memory: MemoryState
    agent: AgentState
    execution: ExecutionState
    
    # Catch-all for additional keys
    __extra__: Dict[str, Any]
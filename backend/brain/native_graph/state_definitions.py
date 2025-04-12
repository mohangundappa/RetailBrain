"""
State definitions for the LangGraph-based orchestration system.

This module defines the TypedDict classes that represent the state used in the LangGraph
orchestration flow. These state definitions provide a structured way to manage information
throughout the graph execution.
"""

from typing import TypedDict, List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the message")
    agent: Optional[str] = Field(None, description="Agent that generated the message (for assistant messages)")
    
    class Config:
        arbitrary_types_allowed = True


class EntityInfo(BaseModel):
    """Information about an extracted entity."""
    name: str = Field(..., description="Name of the entity")
    value: Any = Field(..., description="Value of the entity")
    confidence: float = Field(1.0, description="Confidence score for the entity extraction")
    source: str = Field("direct", description="Source of the entity (direct, inferred, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the entity was extracted")


class AgentSelectionInfo(BaseModel):
    """Information about an agent selection decision."""
    agent_id: str = Field(..., description="ID of the selected agent")
    agent_name: str = Field(..., description="Name of the selected agent")
    confidence: float = Field(..., description="Confidence score for the selection")
    reason: str = Field(..., description="Reason for selecting this agent")


class ConversationState(TypedDict, total=False):
    """State tracking for a conversation."""
    session_id: str
    messages: List[Dict[str, Any]]  # List of Message objects as dicts
    last_user_message: str
    last_assistant_message: Optional[str]
    last_agent: Optional[str]


class EntityState(TypedDict, total=False):
    """State tracking for entities."""
    entities: Dict[str, Any]  # EntityInfo objects by entity name
    extracted_this_turn: List[str]  # Entity names extracted in current turn
    validated: Dict[str, bool]  # Validation status by entity name


class AgentState(TypedDict, total=False):
    """State tracking for agent selection and execution."""
    available_agents: List[str]  # List of available agent IDs
    selected_agent: Optional[str]  # Currently selected agent ID
    selection_info: Optional[Dict[str, Any]]  # AgentSelectionInfo as dict
    confidence: float  # Confidence in the current selection
    continue_with_same_agent: bool  # Whether to continue with the same agent
    special_case_detected: bool  # Whether a special case was detected
    special_case_type: Optional[str]  # Type of special case
    special_case_response: Optional[str]  # Response for special case
    agent_configs: Dict[str, Dict[str, Any]]  # Configuration for each agent


class MemoryState(TypedDict, total=False):
    """State tracking for memory operations."""
    working_memory_ids: List[str]  # IDs of items in working memory
    episodic_memory_ids: List[str]  # IDs of items in episodic memory
    relevant_memory_ids: List[str]  # IDs of relevant memories for current turn
    agent_memory_ids: Dict[str, List[str]]  # IDs of memories by agent
    memory_last_updated: datetime  # When memory was last updated


class ExecutionState(TypedDict, total=False):
    """State tracking for graph execution."""
    current_node: str  # Name of the current node
    previous_node: Optional[str]  # Name of the previous node
    execution_path: List[str]  # Names of nodes visited in order
    errors: List[Dict[str, Any]]  # Errors encountered during execution
    request_start_time: datetime  # When request processing started
    latencies: Dict[str, float]  # Latency by node name
    tools_used: List[str]  # Tools used during processing


class OrchestrationState(TypedDict, total=False):
    """Complete state for orchestration."""
    conversation: ConversationState
    entities: EntityState
    agent: AgentState
    memory: MemoryState
    execution: ExecutionState
    metadata: Dict[str, Any]  # Additional metadata
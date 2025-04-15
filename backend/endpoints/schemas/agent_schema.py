"""
Pydantic models for Agent Builder API.

This module defines the API schemas for agent configuration endpoints,
including request and response models for agent management, persona configuration,
tool management, and entity mapping.
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class AgentResponseTemplateModel(BaseModel):
    """Model for agent response templates."""
    id: Optional[str] = Field(None, description="Template ID")
    template_key: str = Field(..., description="Unique key for this template")
    template_content: str = Field(..., description="Template content with placeholders")
    template_type: str = Field(..., description="Template type (text, rich_text, etc.)")
    language: str = Field(..., description="Template language code")
    tone: Optional[str] = Field(None, description="Template tone")
    version: int = Field(1, description="Template version")


class AgentPatternModel(BaseModel):
    """Model for agent detection patterns."""
    id: Optional[str] = Field(None, description="Pattern ID")
    pattern_type: str = Field(..., description="Pattern type (keyword, semantic, regex)")
    pattern_value: str = Field(..., description="The pattern value")
    confidence_boost: float = Field(0.1, description="Confidence boost when pattern matches")
    priority: int = Field(1, description="Pattern priority (higher is more important)")


class EntityMappingModel(BaseModel):
    """Model for entity mappings to agents."""
    id: Optional[str] = Field(None, description="Entity mapping ID")
    entity_id: str = Field(..., description="Entity definition ID")
    entity_name: str = Field(..., description="Entity name")
    display_name: str = Field(..., description="Display name for the entity")
    extraction_strategy: str = Field("llm", description="Strategy for extracting this entity")
    confidence_threshold: float = Field(0.7, description="Confidence threshold for extraction")
    is_required: bool = Field(False, description="Whether this entity is required")
    persistence_scope: str = Field("session", description="Scope for entity persistence (session, conversation, etc.)")
    validation_regex: Optional[str] = Field(None, description="Regex for validating extracted values")
    default_value: Optional[str] = Field(None, description="Default value if not found")


class AgentToolModel(BaseModel):
    """Model for agent tools."""
    id: Optional[str] = Field(None, description="Tool ID")
    tool_name: str = Field(..., description="Name of the tool")
    tool_description: str = Field(..., description="Description of what the tool does")
    tool_class_path: str = Field(..., description="Python path to tool implementation")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    is_enabled: bool = Field(True, description="Whether the tool is enabled")
    requires_confirmation: bool = Field(False, description="Whether user confirmation is required")
    usage_threshold: float = Field(0.7, description="Threshold for when to use this tool")


class AgentPersonaModel(BaseModel):
    """Model for agent persona configuration."""
    system_prompt: str = Field(..., description="System prompt defining the agent's persona")
    tone: str = Field("professional", description="Tone of the agent's responses")
    verbosity: str = Field("balanced", description="Verbosity level (concise, balanced, detailed)")
    formality: str = Field("formal", description="Formality level (casual, balanced, formal)")
    persona_traits: List[str] = Field([], description="Persona traits (empathetic, authoritative, etc.)")
    language_style: Optional[str] = Field(None, description="Language style guidelines")
    
    @validator('verbosity')
    def validate_verbosity(cls, v):
        allowed_values = ["concise", "balanced", "detailed"]
        if v not in allowed_values:
            raise ValueError(f"verbosity must be one of {allowed_values}")
        return v
    
    @validator('formality')
    def validate_formality(cls, v):
        allowed_values = ["casual", "balanced", "formal"]
        if v not in allowed_values:
            raise ValueError(f"formality must be one of {allowed_values}")
        return v


class AgentLlmConfigModel(BaseModel):
    """Model for LLM agent configuration."""
    model_name: str = Field(..., description="LLM model name")
    temperature: float = Field(0.7, description="Temperature setting")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    timeout_seconds: int = Field(30, description="Timeout in seconds")
    confidence_threshold: float = Field(0.7, description="Confidence threshold")
    few_shot_examples: Optional[List[Dict[str, Any]]] = Field(None, description="Few-shot examples")
    output_parser: Optional[str] = Field(None, description="Output parser configuration")


class AgentDetailModel(BaseModel):
    """Detailed model for agent information."""
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    agent_type: str = Field(..., description="Agent type")
    version: int = Field(1, description="Agent version")
    status: str = Field("draft", description="Agent status (draft, active, deprecated)")
    is_system: bool = Field(False, description="Whether this is a system agent")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator username")
    
    # Configuration components
    persona: Optional[AgentPersonaModel] = Field(None, description="Agent persona configuration")
    llm_config: Optional[AgentLlmConfigModel] = Field(None, description="LLM configuration")
    patterns: Optional[List[AgentPatternModel]] = Field(None, description="Detection patterns")
    tools: Optional[List[AgentToolModel]] = Field(None, description="Available tools")
    response_templates: Optional[List[AgentResponseTemplateModel]] = Field(None, description="Response templates")
    entities: Optional[List[EntityMappingModel]] = Field(None, description="Entity mappings")


class AgentCreateRequest(BaseModel):
    """Request model for creating a new agent."""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    agent_type: str = Field(..., description="Agent type")
    is_system: bool = Field(False, description="Whether this is a system agent")
    
    # Optional configuration components
    template_id: Optional[str] = Field(None, description="Template ID to base the agent on")
    persona: Optional[AgentPersonaModel] = Field(None, description="Agent persona configuration")
    llm_config: Optional[AgentLlmConfigModel] = Field(None, description="LLM configuration")
    patterns: Optional[List[AgentPatternModel]] = Field(None, description="Detection patterns")
    tools: Optional[List[AgentToolModel]] = Field(None, description="Available tools")
    response_templates: Optional[List[AgentResponseTemplateModel]] = Field(None, description="Response templates")
    entities: Optional[List[EntityMappingModel]] = Field(None, description="Entity mappings")


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    agent_type: Optional[str] = Field(None, description="Agent type")
    
    # Optional configuration components
    persona: Optional[AgentPersonaModel] = Field(None, description="Agent persona configuration")
    llm_config: Optional[AgentLlmConfigModel] = Field(None, description="LLM configuration")
    patterns: Optional[List[AgentPatternModel]] = Field(None, description="Detection patterns")
    response_templates: Optional[List[AgentResponseTemplateModel]] = Field(None, description="Response templates")


class AgentListResponse(BaseModel):
    """Response model for listing agents."""
    success: bool = Field(..., description="Whether the request was successful")
    agents: List[Union[str, AgentDetailModel]] = Field(..., description="List of agents")
    error: Optional[str] = Field(None, description="Error message if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class AgentTestRequest(BaseModel):
    """Request model for testing an agent."""
    message: str = Field(..., description="Sample message to test the agent with")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for the test")
    include_debug: bool = Field(False, description="Whether to include debug information in the response")


class AgentTestResponse(BaseModel):
    """Response model for agent testing."""
    success: bool = Field(..., description="Whether the test was successful")
    agent_id: str = Field(..., description="ID of the agent tested")
    agent_name: str = Field(..., description="Name of the agent tested")
    message: str = Field(..., description="Original test message")
    response: str = Field(..., description="Agent's response")
    confidence: float = Field(..., description="Agent's confidence score")
    processing_time: float = Field(..., description="Processing time in milliseconds")
    extracted_entities: Optional[Dict[str, Any]] = Field(None, description="Entities extracted from the message")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Debug information if requested")
    error: Optional[str] = Field(None, description="Error message if applicable")
"""
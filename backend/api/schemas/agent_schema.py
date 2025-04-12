"""
API schemas for agent-related operations.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from pydantic import BaseModel, Field, constr


class AgentBase(BaseModel):
    """Base model for agent data."""
    name: constr(min_length=1, max_length=255) = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    agent_type: constr(min_length=1, max_length=50) = Field(..., description="Agent type (LLM, RULE, RETRIEVAL, etc.)")
    is_system: bool = Field(False, description="Whether this is a system agent")


class AgentCreate(AgentBase):
    """Model for creating a new agent."""
    pass


class AgentUpdate(BaseModel):
    """Model for updating an agent."""
    name: Optional[constr(min_length=1, max_length=255)] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    status: Optional[str] = Field(None, description="Agent status (draft, active, archived)")


class AgentResponse(AgentBase):
    """Model for returning agent data."""
    id: uuid.UUID = Field(..., description="Agent ID")
    status: str = Field(..., description="Agent status (draft, active, archived)")
    version: int = Field(..., description="Agent version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator of the agent")
    
    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Model for returning a list of agents."""
    items: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total number of agents")


class DeploymentCreate(BaseModel):
    """Model for creating a new deployment."""
    environment: constr(min_length=1, max_length=50) = Field(..., description="Deployment environment (dev, staging, production)")
    deployment_notes: Optional[str] = Field(None, description="Notes about this deployment")


class DeploymentResponse(BaseModel):
    """Model for returning deployment data."""
    id: uuid.UUID = Field(..., description="Deployment ID")
    agent_id: uuid.UUID = Field(..., description="Agent ID")
    environment: str = Field(..., description="Deployment environment")
    is_active: bool = Field(..., description="Whether this deployment is active")
    deployed_at: datetime = Field(..., description="Deployment timestamp")
    deployed_by: Optional[str] = Field(None, description="User who created the deployment")
    deployment_notes: Optional[str] = Field(None, description="Deployment notes")
    
    class Config:
        from_attributes = True


class PatternCreate(BaseModel):
    """Model for creating a new pattern."""
    pattern_type: constr(min_length=1, max_length=50) = Field(..., description="Pattern type (regex, keyword, semantic)")
    pattern_value: str = Field(..., description="The pattern value")
    priority: int = Field(0, description="Pattern priority (higher number = higher priority)")
    confidence_boost: float = Field(0.1, description="Confidence boost when pattern matches (0.0-1.0)")


class PatternResponse(PatternCreate):
    """Model for returning pattern data."""
    id: uuid.UUID = Field(..., description="Pattern ID")
    agent_id: uuid.UUID = Field(..., description="Agent ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class ResponseTemplateCreate(BaseModel):
    """Model for creating a new response template."""
    template_key: constr(min_length=1, max_length=100) = Field(..., description="Template identifier")
    template_content: str = Field(..., description="The template content")
    language: str = Field("en", description="Language code")
    template_type: str = Field("text", description="Template type (text, markdown, html)")
    scenario: Optional[str] = Field(None, description="Scenario classification")
    tone: str = Field("neutral", description="Template tone (friendly, formal, etc.)")
    is_fallback: bool = Field(False, description="Whether this is a fallback template")


class ResponseTemplateResponse(ResponseTemplateCreate):
    """Model for returning response template data."""
    id: uuid.UUID = Field(..., description="Template ID")
    agent_id: uuid.UUID = Field(..., description="Agent ID")
    version: int = Field(..., description="Template version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


# Type-specific configuration models

class LlmAgentConfig(BaseModel):
    """Configuration for LLM-based agents."""
    model_name: str = Field(..., description="LLM model to use")
    temperature: float = Field(0.7, description="Temperature parameter (0.0-1.0)")
    max_tokens: Optional[int] = Field(None, description="Maximum number of tokens")
    timeout_seconds: int = Field(30, description="Timeout in seconds")
    confidence_threshold: float = Field(0.7, description="Confidence threshold (0.0-1.0)")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    few_shot_examples: Optional[List[Dict[str, str]]] = Field(None, description="Few-shot examples")
    output_parser: Optional[str] = Field(None, description="Output parser to use")


class RuleAgentConfig(BaseModel):
    """Configuration for rule-based agents."""
    rules: Dict[str, Any] = Field(..., description="Rules configuration")
    default_confidence: float = Field(0.5, description="Default confidence score (0.0-1.0)")
    fallback_message: Optional[str] = Field(None, description="Fallback message when no rules match")


class RetrievalAgentConfig(BaseModel):
    """Configuration for retrieval-based agents."""
    vector_store_id: Optional[uuid.UUID] = Field(None, description="Vector store ID")
    search_type: str = Field("similarity", description="Search type (similarity, hybrid)")
    top_k: int = Field(3, description="Number of results to retrieve")
    similarity_threshold: float = Field(0.7, description="Similarity threshold (0.0-1.0)")
    reranker_config: Optional[Dict[str, Any]] = Field(None, description="Reranker configuration")


class AgentConfigCreate(BaseModel):
    """Model for creating agent-specific configuration."""
    llm_config: Optional[LlmAgentConfig] = Field(None, description="LLM agent configuration")
    rule_config: Optional[RuleAgentConfig] = Field(None, description="Rule agent configuration")
    retrieval_config: Optional[RetrievalAgentConfig] = Field(None, description="Retrieval agent configuration")


class AgentDetailResponse(AgentResponse):
    """Detailed agent information including configurations."""
    llm_config: Optional[LlmAgentConfig] = Field(None, description="LLM agent configuration")
    rule_config: Optional[RuleAgentConfig] = Field(None, description="Rule agent configuration")
    retrieval_config: Optional[RetrievalAgentConfig] = Field(None, description="Retrieval agent configuration")
    patterns: List[PatternResponse] = Field([], description="Agent patterns")
    response_templates: List[ResponseTemplateResponse] = Field([], description="Response templates")
    
    class Config:
        from_attributes = True
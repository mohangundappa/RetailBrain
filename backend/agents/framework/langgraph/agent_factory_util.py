"""
Utility functions for agent factory.

This module provides utility functions for agent factory to help with agent creation
and loading based on agent types.
"""
import logging
from typing import Dict, Any, Optional, List

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.agents.framework.langgraph.database_agent import DatabaseAgent
from backend.agents.framework.langgraph.workflow_database_agent import WorkflowDatabaseAgent, create_workflow_database_agent_from_definition
from backend.config.agent_constants import (
    RESET_PASSWORD_AGENT,
    PACKAGE_TRACKING_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT,
    RETURNS_PROCESSING_AGENT
)
from backend.database.agent_schema import AgentDefinition

logger = logging.getLogger(__name__)


async def create_agent_from_definition(agent_def: Dict[str, Any]) -> Optional[LangGraphAgent]:
    """
    Create the appropriate agent type based on agent definition.
    
    This function determines the correct agent implementation to use based on
    the agent type and name in the definition.
    
    Args:
        agent_def: Agent definition dictionary
        
    Returns:
        LangGraphAgent instance or None if creation fails
    """
    try:
        # Check for required fields
        required_fields = ["id", "name", "agent_type"]
        for field in required_fields:
            if field not in agent_def:
                logger.error(f"Missing required field in agent definition: {field}")
                return None
        
        # Use workflow-aware agent for Reset Password Agent
        if agent_def.get("agent_type") == RESET_PASSWORD_AGENT or "Reset Password" in agent_def.get("name", ""):
            logger.info(f"Creating workflow-enabled agent for {agent_def.get('name')}")
            return await create_workflow_database_agent_from_definition(agent_def)
        
        # Standard database agent for all other types
        from backend.agents.framework.langgraph.database_agent import create_database_agent_from_definition
        return await create_database_agent_from_definition(agent_def)
    
    except Exception as e:
        logger.error(f"Error creating agent from definition: {str(e)}", exc_info=True)
        return None


async def create_agent_from_model(agent_model: AgentDefinition) -> Optional[LangGraphAgent]:
    """
    Create the appropriate agent type based on database model.
    
    Args:
        agent_model: AgentDefinition database model
        
    Returns:
        LangGraphAgent instance or None if creation fails
    """
    try:
        # Convert model to dictionary
        agent_def = {
            "id": str(agent_model.id),
            "name": agent_model.name,
            "description": agent_model.description,
            "agent_type": agent_model.agent_type,
            "status": agent_model.status,
            "is_system": agent_model.is_system,
            "created_at": agent_model.created_at.isoformat() if agent_model.created_at else None,
            "updated_at": agent_model.updated_at.isoformat() if agent_model.updated_at else None,
            "version": agent_model.version
        }
        
        # Add LLM configuration
        if hasattr(agent_model, 'llm_configuration') and agent_model.llm_configuration:
            llm_config = agent_model.llm_configuration[0] if isinstance(agent_model.llm_configuration, list) else agent_model.llm_configuration
            if llm_config:
                agent_def["llm_config"] = {
                    "model_name": llm_config.model_name,
                    "temperature": llm_config.temperature,
                    "max_tokens": llm_config.max_tokens,
                    "timeout_seconds": llm_config.timeout_seconds,
                    "system_prompt": llm_config.system_prompt
                }
                # Add individual fields for easier access
                agent_def["model_name"] = llm_config.model_name
                agent_def["temperature"] = llm_config.temperature
                agent_def["system_prompt"] = llm_config.system_prompt
        
        # Add patterns
        if hasattr(agent_model, 'patterns') and agent_model.patterns:
            agent_def["patterns"] = [
                {
                    "pattern_type": pattern.pattern_type,
                    "pattern_value": pattern.pattern_value,
                    "confidence_boost": pattern.confidence_boost
                }
                for pattern in agent_model.patterns
            ]
        
        # Add tools
        if hasattr(agent_model, 'tools') and agent_model.tools:
            agent_def["tools"] = [
                {
                    "tool_name": tool.tool_name,
                    "tool_description": tool.tool_description,
                    "parameters": tool.parameters,
                    "enabled": tool.enabled
                }
                for tool in agent_model.tools
            ]
        
        # Add response templates
        if hasattr(agent_model, 'response_templates') and agent_model.response_templates:
            agent_def["response_templates"] = {
                template.template_key: template.template_content
                for template in agent_model.response_templates
            }
        
        # Create the agent using the helper function
        return await create_agent_from_definition(agent_def)
    
    except Exception as e:
        logger.error(f"Error creating agent from model: {str(e)}", exc_info=True)
        return None
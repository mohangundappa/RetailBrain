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
        # Begin by extracting all the data we need while the model is attached to the session
        agent_id = str(agent_model.id)
        agent_name = agent_model.name
        agent_description = agent_model.description
        agent_type = agent_model.agent_type
        agent_status = agent_model.status
        agent_is_system = agent_model.is_system
        agent_created_at = agent_model.created_at.isoformat() if agent_model.created_at else None
        agent_updated_at = agent_model.updated_at.isoformat() if agent_model.updated_at else None
        agent_version = agent_model.version
        
        # Convert model to dictionary with basic fields
        agent_def = {
            "id": agent_id,
            "name": agent_name,
            "description": agent_description,
            "agent_type": agent_type,
            "status": agent_status,
            "is_system": agent_is_system,
            "created_at": agent_created_at,
            "updated_at": agent_updated_at,
            "version": agent_version
        }
        
        # Extract LLM configuration safely
        llm_configurations = getattr(agent_model, 'llm_configuration', None)
        if llm_configurations:
            # Make sure to extract all configuration values while the model is attached
            if isinstance(llm_configurations, list) and llm_configurations:
                llm_config = llm_configurations[0]
                
                # Extract all values from the configuration
                model_name = getattr(llm_config, 'model_name', 'gpt-4o')
                temperature = getattr(llm_config, 'temperature', 0.2)
                max_tokens = getattr(llm_config, 'max_tokens', 800)
                timeout_seconds = getattr(llm_config, 'timeout_seconds', 30)
                system_prompt = getattr(llm_config, 'system_prompt', '')
                
                agent_def["llm_config"] = {
                    "model_name": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout_seconds": timeout_seconds,
                    "system_prompt": system_prompt
                }
                
                # Add individual fields for easier access
                agent_def["model_name"] = model_name
                agent_def["temperature"] = temperature
                agent_def["system_prompt"] = system_prompt
        
        # Extract patterns safely
        patterns = getattr(agent_model, 'patterns', None)
        if patterns:
            agent_def["patterns"] = [
                {
                    "pattern_type": pattern.pattern_type,
                    "pattern_value": pattern.pattern_value,
                    "confidence_boost": pattern.confidence_boost
                }
                for pattern in patterns
            ]
        
        # Extract tools safely
        tools = getattr(agent_model, 'tools', None)
        if tools:
            agent_def["tools"] = [
                {
                    "tool_name": tool.tool_name,
                    "tool_description": tool.tool_description,
                    "parameters": tool.parameters,
                    "enabled": tool.enabled
                }
                for tool in tools
            ]
        
        # Extract response templates safely
        templates = getattr(agent_model, 'response_templates', None)
        if templates:
            agent_def["response_templates"] = {
                template.template_key: template.template_content
                for template in templates
            }
        
        # Log the created agent definition
        logger.info(f"Creating agent from definition: {agent_name} (ID: {agent_id}, Type: {agent_type})")
        
        # Create the agent using the helper function
        return await create_agent_from_definition(agent_def)
    
    except Exception as e:
        logger.error(f"Error creating agent from model: {str(e)}", exc_info=True)
        return None
"""
Agent Builder API endpoints for Staples Brain.

This module provides API endpoints for managing agent configurations through the Agent Builder
interface, allowing dynamic creation, editing, and deployment of agents.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path, status
from pydantic import BaseModel, Field

from backend.endpoints.schemas.agent_schema import (
    AgentDetailModel, AgentCreateRequest, AgentUpdateRequest, 
    AgentListResponse, AgentTestRequest, AgentTestResponse,
    AgentPersonaModel, AgentToolModel, EntityMappingModel
)
from backend.services.agent_builder_service import AgentBuilderService
from backend.dependencies import get_agent_builder_service, get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Create API router
agent_builder_router = APIRouter(prefix="/agent-builder", tags=["agent-builder"])


@agent_builder_router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    agent_type: Optional[str] = None,
    is_system: Optional[bool] = None,
    status: Optional[str] = None,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    List all agents with optional filtering.
    
    Args:
        agent_type: Optional filter by agent type
        is_system: Optional filter by system agent flag
        status: Optional filter by agent status
    
    Returns:
        List of agent details
    """
    try:
        agents = await agent_builder_service.list_agents(
            agent_type=agent_type,
            is_system=is_system,
            status=status
        )
        return {
            "success": True,
            "agents": agents,
            "metadata": {
                "count": len(agents),
                "filters": {
                    "agent_type": agent_type,
                    "is_system": is_system,
                    "status": status
                }
            }
        }
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return {
            "success": False,
            "agents": [],
            "error": f"Failed to retrieve agents: {str(e)}",
            "metadata": {}
        }


@agent_builder_router.get("/agents/{agent_id}", response_model=AgentDetailModel)
async def get_agent(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_id: ID of the agent to retrieve
    
    Returns:
        Detailed agent information
    """
    try:
        agent = await agent_builder_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent: {str(e)}"
        )


@agent_builder_router.post("/agents", response_model=AgentDetailModel, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreateRequest,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Create a new agent configuration.
    
    Args:
        agent_data: Agent configuration data
    
    Returns:
        Created agent details
    """
    try:
        agent = await agent_builder_service.create_agent(agent_data)
        return agent
    except ValueError as e:
        logger.error(f"Validation error creating agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@agent_builder_router.put("/agents/{agent_id}", response_model=AgentDetailModel)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdateRequest,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Update an existing agent configuration.
    
    Args:
        agent_id: ID of the agent to update
        agent_data: Updated agent configuration data
    
    Returns:
        Updated agent details
    """
    try:
        agent = await agent_builder_service.update_agent(agent_id, agent_data)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        return agent
    except ValueError as e:
        logger.error(f"Validation error updating agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@agent_builder_router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Delete an agent configuration.
    
    Args:
        agent_id: ID of the agent to delete
    """
    try:
        success = await agent_builder_service.delete_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@agent_builder_router.get("/agents/{agent_id}/persona", response_model=AgentPersonaModel)
async def get_agent_persona(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Get the persona configuration for an agent.
    
    Args:
        agent_id: ID of the agent
    
    Returns:
        Agent persona configuration
    """
    try:
        persona = await agent_builder_service.get_agent_persona(agent_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona for agent with ID {agent_id} not found"
            )
        return persona
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent persona: {str(e)}"
        )


@agent_builder_router.put("/agents/{agent_id}/persona", response_model=AgentPersonaModel)
async def update_agent_persona(
    agent_id: str,
    persona_data: AgentPersonaModel,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Update the persona configuration for an agent.
    
    Args:
        agent_id: ID of the agent
        persona_data: Updated persona configuration
    
    Returns:
        Updated agent persona
    """
    try:
        persona = await agent_builder_service.update_agent_persona(agent_id, persona_data)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        return persona
    except ValueError as e:
        logger.error(f"Validation error updating persona for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent persona: {str(e)}"
        )


@agent_builder_router.get("/agents/{agent_id}/tools", response_model=List[AgentToolModel])
async def list_agent_tools(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    List all tools available to an agent.
    
    Args:
        agent_id: ID of the agent
    
    Returns:
        List of agent tools
    """
    try:
        tools = await agent_builder_service.list_agent_tools(agent_id)
        return tools
    except Exception as e:
        logger.error(f"Error listing tools for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent tools: {str(e)}"
        )


@agent_builder_router.post("/agents/{agent_id}/tools", response_model=AgentToolModel, status_code=status.HTTP_201_CREATED)
async def add_agent_tool(
    agent_id: str,
    tool_data: AgentToolModel,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Add a tool to an agent.
    
    Args:
        agent_id: ID of the agent
        tool_data: Tool configuration data
    
    Returns:
        Added tool details
    """
    try:
        tool = await agent_builder_service.add_agent_tool(agent_id, tool_data)
        return tool
    except ValueError as e:
        logger.error(f"Validation error adding tool to agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding tool to agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add tool to agent: {str(e)}"
        )


@agent_builder_router.put("/agents/{agent_id}/tools/{tool_id}", response_model=AgentToolModel)
async def update_agent_tool(
    agent_id: str,
    tool_id: str,
    tool_data: AgentToolModel,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Update a tool configuration for an agent.
    
    Args:
        agent_id: ID of the agent
        tool_id: ID of the tool to update
        tool_data: Updated tool configuration
    
    Returns:
        Updated tool details
    """
    try:
        tool = await agent_builder_service.update_agent_tool(agent_id, tool_id, tool_data)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool with ID {tool_id} for agent {agent_id} not found"
            )
        return tool
    except ValueError as e:
        logger.error(f"Validation error updating tool {tool_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tool {tool_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}"
        )


@agent_builder_router.delete("/agents/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_tool(
    agent_id: str,
    tool_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Delete a tool from an agent.
    
    Args:
        agent_id: ID of the agent
        tool_id: ID of the tool to delete
    """
    try:
        success = await agent_builder_service.delete_agent_tool(agent_id, tool_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool with ID {tool_id} for agent {agent_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tool {tool_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}"
        )


@agent_builder_router.get("/entities", response_model=List[EntityMappingModel])
async def list_entities(
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    List all available entity definitions.
    
    Returns:
        List of entity definitions
    """
    try:
        entities = await agent_builder_service.list_entities()
        return entities
    except Exception as e:
        logger.error(f"Error listing entities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entities: {str(e)}"
        )


@agent_builder_router.get("/agents/{agent_id}/entities", response_model=List[EntityMappingModel])
async def list_agent_entities(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    List all entities configured for an agent.
    
    Args:
        agent_id: ID of the agent
    
    Returns:
        List of entity mappings for the agent
    """
    try:
        entities = await agent_builder_service.list_agent_entities(agent_id)
        return entities
    except Exception as e:
        logger.error(f"Error listing entities for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent entities: {str(e)}"
        )


@agent_builder_router.post("/agents/{agent_id}/entities", response_model=EntityMappingModel, status_code=status.HTTP_201_CREATED)
async def add_agent_entity(
    agent_id: str,
    entity_data: EntityMappingModel,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Add an entity mapping to an agent.
    
    Args:
        agent_id: ID of the agent
        entity_data: Entity mapping configuration
    
    Returns:
        Added entity mapping
    """
    try:
        entity = await agent_builder_service.add_agent_entity(agent_id, entity_data)
        return entity
    except ValueError as e:
        logger.error(f"Validation error adding entity to agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding entity to agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add entity to agent: {str(e)}"
        )


@agent_builder_router.put("/agents/{agent_id}/entities/{entity_id}", response_model=EntityMappingModel)
async def update_agent_entity(
    agent_id: str,
    entity_id: str,
    entity_data: EntityMappingModel,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Update an entity mapping for an agent.
    
    Args:
        agent_id: ID of the agent
        entity_id: ID of the entity mapping to update
        entity_data: Updated entity mapping configuration
    
    Returns:
        Updated entity mapping
    """
    try:
        entity = await agent_builder_service.update_agent_entity(agent_id, entity_id, entity_data)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity mapping with ID {entity_id} for agent {agent_id} not found"
            )
        return entity
    except ValueError as e:
        logger.error(f"Validation error updating entity {entity_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating entity {entity_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity: {str(e)}"
        )


@agent_builder_router.delete("/agents/{agent_id}/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_entity(
    agent_id: str,
    entity_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Delete an entity mapping from an agent.
    
    Args:
        agent_id: ID of the agent
        entity_id: ID of the entity mapping to delete
    """
    try:
        success = await agent_builder_service.delete_agent_entity(agent_id, entity_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity mapping with ID {entity_id} for agent {agent_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting entity {entity_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity: {str(e)}"
        )


@agent_builder_router.post("/agents/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(
    agent_id: str,
    test_data: AgentTestRequest,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Test an agent with a sample message.
    
    Args:
        agent_id: ID of the agent to test
        test_data: Test configuration with sample message
    
    Returns:
        Test results including agent response
    """
    try:
        test_result = await agent_builder_service.test_agent(agent_id, test_data)
        return test_result
    except ValueError as e:
        logger.error(f"Validation error testing agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error testing agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test agent: {str(e)}"
        )


@agent_builder_router.post("/agents/{agent_id}/publish", response_model=AgentDetailModel)
async def publish_agent(
    agent_id: str,
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    Publish an agent from draft to active status.
    
    Args:
        agent_id: ID of the agent to publish
    
    Returns:
        Published agent details
    """
    try:
        agent = await agent_builder_service.publish_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        return agent
    except ValueError as e:
        logger.error(f"Validation error publishing agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error publishing agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish agent: {str(e)}"
        )


@agent_builder_router.get("/templates", response_model=List[AgentDetailModel])
async def list_agent_templates(
    agent_builder_service: AgentBuilderService = Depends(get_agent_builder_service)
):
    """
    List available agent templates.
    
    Returns:
        List of agent templates
    """
    try:
        templates = await agent_builder_service.list_agent_templates()
        return templates
    except Exception as e:
        logger.error(f"Error listing agent templates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent templates: {str(e)}"
        )
"""
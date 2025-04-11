"""
Agent Builder API Routes

This module provides the API endpoints for creating, managing, and testing custom agents
through the drag-and-drop agent builder interface.

FastAPI version - migrated from Flask
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.database.db import get_db
from backend.database.models import CustomAgent, AgentComponent, ComponentConnection, ComponentTemplate, AgentTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

# Configure logging
logger = logging.getLogger(__name__)

# Create router
agent_builder_router = APIRouter(prefix="/agents", tags=["agent-builder"])

# Pydantic models for request/response
class AgentBase(BaseModel):
    name: str
    description: Optional[str] = ""
    creator: Optional[str] = "UI Builder"
    is_active: Optional[bool] = True
    
class ComponentBase(BaseModel):
    id: str
    component_type: str
    name: str
    position_x: float
    position_y: float
    template: Optional[str] = None
    configuration: Dict[str, Any] = {}
    
class ConnectionBase(BaseModel):
    id: Optional[str] = None
    source_id: str
    target_id: str
    connection_type: Optional[str] = "default"
    
class AgentCreate(AgentBase):
    components: List[ComponentBase] = []
    connections: List[ConnectionBase] = []
    
class AgentResponse(AgentBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    components: List[ComponentBase] = []
    connections: List[ConnectionBase] = []
    
class AgentListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_active: bool = True
    creator: str
    component_count: int = 0
    is_custom: bool
    can_edit: bool

class AgentCreateResponse(BaseModel):
    id: int
    name: str
    message: str = "Agent created successfully"

@agent_builder_router.get("/", response_model=List[AgentListItem])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """
    Get a list of all agents, both custom and built-in.
    
    Returns:
        JSON list of agents with their basic information
    """
    try:
        # Get custom agents from database
        result = await db.execute(select(CustomAgent))
        custom_agents = result.scalars().all()
        
        response = []
        for agent in custom_agents:
            response.append(AgentListItem(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                created_at=agent.created_at.isoformat() if agent.created_at else None,
                updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
                is_active=agent.is_active,
                creator=agent.creator,
                component_count=len(agent.components),
                is_custom=True,  # Flag to indicate this is a custom agent
                can_edit=True    # Custom agents can be edited
            ))
        
        # Get built-in agents from the brain
        from brain.staples_brain import initialize_staples_brain
        try:
            brain = initialize_staples_brain()
            builtin_agents = brain.agents
            
            # Add built-in agents to the result
            for idx, agent in enumerate(builtin_agents):
                # Use negative IDs to distinguish built-in agents
                agent_id = -(idx + 1)
                response.append(AgentListItem(
                    id=agent_id,
                    name=agent.name,
                    description=getattr(agent, 'description', f"Built-in agent for {agent.name.lower()} functionality"),
                    created_at=None,
                    updated_at=None,
                    is_active=True,
                    creator='System',
                    component_count=0,  # Built-in agents don't have components in the same way
                    is_custom=False,    # Flag to indicate this is a built-in agent
                    can_edit=False      # Built-in agents cannot be edited
                ))
        except Exception as e:
            logger.warning(f"Error loading built-in agents: {str(e)}")
            # Continue with just the custom agents if we can't load built-in ones
        
        return response
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@agent_builder_router.post("/", response_model=AgentCreateResponse, status_code=201)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new custom agent.
    
    The request body should contain the agent configuration.
    
    Returns:
        JSON with the created agent information
    """
    try:
        logger.debug("Received request to create new agent")
        
        # Check if name already exists
        result = await db.execute(select(CustomAgent).filter(CustomAgent.name == agent_data.name))
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Agent with name '{agent_data.name}' already exists")
            raise HTTPException(status_code=409, detail=f"Agent with name '{agent_data.name}' already exists")
            
        # Create agent
        agent = CustomAgent(
            name=agent_data.name,
            description=agent_data.description,
            creator=agent_data.creator,
            is_active=True
        )
        
        db.add(agent)
        await db.flush()  # Get the agent ID
        
        # Validate required fields for component handling
        for idx, component in enumerate(agent_data.components):
            if not component.template:
                logger.warning(f"Component {idx} missing template field, adding default")
                component_type = component.component_type
                if component_type == 'prompt':
                    component.template = 'custom_prompt'
                elif component_type == 'llm':
                    component.template = 'openai_gpt4'
                elif component_type == 'output':
                    component.template = 'json_formatter'
                else:
                    component.template = f"{component_type}_default"
        
        # Add components
        component_id_map = {}
        for comp_data in agent_data.components:
            # Build additional metadata for component storage
            metadata = {
                'template': comp_data.template
            }
            
            # Create configuration by combining explicit config with metadata
            config = comp_data.configuration
            config['_metadata'] = metadata
            
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data.component_type,
                name=comp_data.name,
                position_x=comp_data.position_x,
                position_y=comp_data.position_y,
                configuration=json.dumps(config)
            )
            
            db.add(component)
            await db.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data.id] = component.id
            logger.debug(f"Added component: {comp_data.name} (ID: {component.id})")
        
        # Add connections
        for conn_data in agent_data.connections:
            # Map frontend IDs to database IDs
            try:
                source_id = component_id_map[conn_data.source_id]
                target_id = component_id_map[conn_data.target_id]
            except KeyError as e:
                logger.warning(f"Invalid component reference in connection: {e}")
                continue
                
            connection = ComponentConnection(
                agent_id=agent.id,
                source_id=source_id,
                target_id=target_id,
                connection_type=conn_data.connection_type
            )
            
            db.add(connection)
            logger.debug(f"Added connection from {conn_data.source_id} to {conn_data.target_id}")
        
        # Store the original configuration as JSON
        agent.configuration = json.dumps(agent_data.dict())
        
        await db.commit()
        logger.info(f"Agent {agent.name} (ID: {agent.id}) created successfully")
        
        return AgentCreateResponse(
            id=agent.id,
            name=agent.name,
            message="Agent created successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions for proper error handling
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@agent_builder_router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific agent with all its components and connections.
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        JSON with the complete agent configuration
    """
    try:
        logger.debug(f"Getting agent with ID: {agent_id}")
        result = await db.execute(select(CustomAgent).filter(CustomAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.warning(f"Agent not found with ID: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        logger.debug(f"Agent found: {agent.name}, has configuration: {bool(agent.configuration)}")
        
        # Check if this is a wizard-created agent with wizard_completed=True 
        # but no components or connections (wizard agents have a different structure)
        is_wizard_agent = agent.wizard_completed and len(agent.components) == 0 and len(agent.connections) == 0
        
        # If we have stored configuration and it's not a wizard agent, use that as the base
        if agent.configuration and not is_wizard_agent:
            try:
                config = json.loads(agent.configuration)
                logger.debug(f"Loaded configuration JSON successfully")
                
                # Check if the configuration has components and connections arrays
                # This helps us identify wizard-created agents that might lack these
                if not config.get('components') or not config.get('connections'):
                    logger.debug("Configuration missing components or connections arrays, falling back to building from relationships")
                    # Fall through to the component builder code
                else:
                    # Update basic properties
                    response = AgentResponse(
                        id=agent.id,
                        name=agent.name,
                        description=agent.description,
                        is_active=agent.is_active,
                        created_at=agent.created_at.isoformat() if agent.created_at else None,
                        updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
                        components=[],
                        connections=[]
                    )
                    
                    # Add components
                    for component in config.get('components', []):
                        # Validate required fields for component rendering
                        if 'template' not in component:
                            logger.warning(f"Component missing template field, adding default")
                            component_type = component.get('component_type', 'unknown')
                            if component_type == 'prompt':
                                component['template'] = 'custom_prompt'
                            elif component_type == 'llm':
                                component['template'] = 'openai_gpt4'
                            elif component_type == 'output':
                                component['template'] = 'json_formatter'
                            else:
                                component['template'] = f"{component_type}_default"
                        
                        # Add component to response
                        response.components.append(ComponentBase(**component))
                    
                    # Add connections
                    for connection in config.get('connections', []):
                        response.connections.append(ConnectionBase(**connection))
                    
                    return response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent configuration JSON: {str(e)}")
                # If JSON parsing fails, fall back to building config from components
        
        # For wizard-created agents or if the above conditions aren't met,
        # build the configuration from components and connections
        logger.debug(f"Building configuration from components: {len(agent.components)} and connections: {len(agent.connections)}")
        components = []
        for comp in agent.components:
            # Determine template from component type if not available
            template = 'custom_prompt'
            if comp.component_type == 'llm':
                template = 'openai_gpt4'
            elif comp.component_type == 'output':
                template = 'json_formatter'
                
            configuration = json.loads(comp.configuration) if comp.configuration else {}
            
            component_data = ComponentBase(
                id=f"component-{comp.id}",
                component_type=comp.component_type,
                name=comp.name,
                template=template,  # Add template field which is required by the frontend
                position_x=comp.position_x,
                position_y=comp.position_y,
                configuration=configuration
            )
            components.append(component_data)
            
        connections = []
        for conn in agent.connections:
            connection_data = ConnectionBase(
                id=f"connection-{conn.id}",
                source_id=f"component-{conn.source_id}",
                target_id=f"component-{conn.target_id}",
                connection_type=conn.connection_type
            )
            connections.append(connection_data)
            
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            is_active=agent.is_active,
            creator=agent.creator,
            created_at=agent.created_at.isoformat() if agent.created_at else None,
            updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
            components=components,
            connections=connections
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions for proper error handling
        raise
    except Exception as e:
        logger.error(f"Error retrieving agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@agent_builder_router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing agent.
    
    Args:
        agent_id: The ID of the agent to update
        
    Returns:
        JSON with the updated agent information
    """
    try:
        logger.debug(f"Updating agent with ID: {agent_id}")
        result = await db.execute(select(CustomAgent).filter(CustomAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.warning(f"Agent not found with ID: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        logger.debug(f"Received update data for agent: {agent.name}")
        
        # Check if name already exists (if changed)
        if agent_data.name != agent.name:
            result = await db.execute(select(CustomAgent).filter(CustomAgent.name == agent_data.name))
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.warning(f"Agent with name '{agent_data.name}' already exists")
                raise HTTPException(status_code=409, detail=f"Agent with name '{agent_data.name}' already exists")
        
        # Delete existing components and connections
        await db.execute(delete(ComponentConnection).where(ComponentConnection.agent_id == agent.id))
        await db.execute(delete(AgentComponent).where(AgentComponent.agent_id == agent.id))
        
        # Update agent
        agent.name = agent_data.name
        agent.description = agent_data.description
        agent.updated_at = datetime.utcnow()
        
        # Validate required fields for component handling
        for idx, component in enumerate(agent_data.components):
            if not component.template:
                logger.warning(f"Component {idx} missing template field, adding default")
                component_type = component.component_type
                if component_type == 'prompt':
                    component.template = 'custom_prompt'
                elif component_type == 'llm':
                    component.template = 'openai_gpt4'
                elif component_type == 'output':
                    component.template = 'json_formatter'
                else:
                    component.template = f"{component_type}_default"
        
        # Add new components
        component_id_map = {}
        for comp_data in agent_data.components:
            # Build additional metadata for component storage
            metadata = {
                'template': comp_data.template
            }
            
            # Create configuration by combining explicit config with metadata
            config = comp_data.configuration
            config['_metadata'] = metadata
            
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data.component_type,
                name=comp_data.name,
                position_x=comp_data.position_x,
                position_y=comp_data.position_y,
                configuration=json.dumps(config)
            )
            
            db.add(component)
            await db.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data.id] = component.id
            logger.debug(f"Added component: {comp_data.name} (ID: {component.id})")
        
        # Add connections
        for conn_data in agent_data.connections:
            # Map frontend IDs to database IDs
            try:
                source_id = component_id_map[conn_data.source_id]
                target_id = component_id_map[conn_data.target_id]
            except KeyError as e:
                logger.warning(f"Invalid component reference in connection: {e}")
                continue
                
            connection = ComponentConnection(
                agent_id=agent.id,
                source_id=source_id,
                target_id=target_id,
                connection_type=conn_data.connection_type
            )
            
            db.add(connection)
            logger.debug(f"Added connection from {conn_data.source_id} to {conn_data.target_id}")
        
        # Store the updated configuration as JSON
        agent.configuration = json.dumps(agent_data.dict())
        
        await db.commit()
        logger.info(f"Agent {agent.name} (ID: {agent.id}) updated successfully")
        
        # Return the updated agent
        result = await db.execute(select(CustomAgent).filter(CustomAgent.id == agent_id))
        updated_agent = result.scalar_one()
        
        # Build response
        components = []
        for comp in updated_agent.components:
            template = 'custom_prompt'
            if comp.component_type == 'llm':
                template = 'openai_gpt4'
            elif comp.component_type == 'output':
                template = 'json_formatter'
                
            configuration = json.loads(comp.configuration) if comp.configuration else {}
            
            component_data = ComponentBase(
                id=f"component-{comp.id}",
                component_type=comp.component_type,
                name=comp.name,
                template=template,
                position_x=comp.position_x,
                position_y=comp.position_y,
                configuration=configuration
            )
            components.append(component_data)
            
        connections = []
        for conn in updated_agent.connections:
            connection_data = ConnectionBase(
                id=f"connection-{conn.id}",
                source_id=f"component-{conn.source_id}",
                target_id=f"component-{conn.target_id}",
                connection_type=conn.connection_type
            )
            connections.append(connection_data)
        
        return AgentResponse(
            id=updated_agent.id,
            name=updated_agent.name,
            description=updated_agent.description,
            is_active=updated_agent.is_active,
            creator=updated_agent.creator,
            created_at=updated_agent.created_at.isoformat() if updated_agent.created_at else None,
            updated_at=updated_agent.updated_at.isoformat() if updated_agent.updated_at else None,
            components=components,
            connections=connections
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions for proper error handling
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@agent_builder_router.delete("/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an agent and all its components and connections.
    
    Args:
        agent_id: The ID of the agent to delete
        
    Returns:
        JSON with success message
    """
    try:
        logger.debug(f"Deleting agent with ID: {agent_id}")
        result = await db.execute(select(CustomAgent).filter(CustomAgent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.warning(f"Agent not found with ID: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Delete agent (cascade will delete components and connections)
        await db.delete(agent)
        await db.commit()
        
        logger.info(f"Agent {agent_id} deleted successfully")
        return {"message": f"Agent {agent_id} deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions for proper error handling
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
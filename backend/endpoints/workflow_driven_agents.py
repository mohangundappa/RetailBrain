"""
Workflow-Driven Agents API endpoints for Staples Brain.

This module provides API endpoints for interacting with workflow-driven agents,
allowing dynamic execution of database-defined workflows.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path, status
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.services.workflow_service import WorkflowService
from backend.services.agent_builder_extensions import AgentBuilderExtensions
from backend.services.agent_builder_service import AgentBuilderService
from backend.database.db import get_db
from backend.config.config import get_config

logger = logging.getLogger(__name__)

# Define request/response models
class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow-driven agent."""
    message: str = Field(..., description="User message to process")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    session_id: Optional[str] = Field(None, description="Session ID for user tracking")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")

class WorkflowExecuteResponse(BaseModel):
    """Response model for workflow execution results."""
    agent_id: str = Field(..., description="ID of the agent that processed the request")
    agent_name: Optional[str] = Field(None, description="Name of the agent")
    response: str = Field(..., description="Agent response")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    status: str = Field(..., description="Execution status (success/error)")
    error: Optional[str] = Field(None, description="Error message if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class WorkflowInfoResponse(BaseModel):
    """Response model for workflow information."""
    id: str = Field(..., description="Workflow ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: int = Field(..., description="Number of nodes in the workflow")
    edges: int = Field(..., description="Number of edges in the workflow")
    entry_node: Optional[str] = Field(None, description="Entry node ID")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

# Create a local dependency function
async def get_workflow_service(
    db: AsyncSession = Depends(get_db)
) -> WorkflowService:
    """
    Get a workflow service instance.
    
    Args:
        db: Database session
        
    Returns:
        WorkflowService instance
    """
    return WorkflowService(db_session=db)

async def get_agent_builder_extensions(
    db: AsyncSession = Depends(get_db)
) -> AgentBuilderExtensions:
    """
    Get agent builder extensions instance.
    
    Args:
        db: Database session
        
    Returns:
        AgentBuilderExtensions instance
    """
    # First get agent builder service
    config = get_config()
    agent_builder = AgentBuilderService(db_session=db, brain_service=None)
    
    # Return extensions
    return AgentBuilderExtensions(agent_builder_service=agent_builder, db_session=db)

# Create API router
workflow_router = APIRouter(prefix="/workflow-agents", tags=["workflow-agents"])


@workflow_router.post("/execute/{agent_id}", response_model=WorkflowExecuteResponse)
async def execute_workflow_agent(
    agent_id: str = Path(..., description="Agent ID to execute"),
    request: WorkflowExecuteRequest = Body(...),
    extensions: AgentBuilderExtensions = Depends(get_agent_builder_extensions),
    workflow_service: WorkflowService = Depends(get_workflow_service)
):
    """
    Execute a workflow-driven agent with the given input.
    
    Args:
        agent_id: ID of the agent to execute
        request: Execution request with message and context
        
    Returns:
        Agent response and execution metadata
    """
    try:
        # Get agent with workflow data
        agent_data = await extensions.get_agent_with_workflow_data(agent_id)
        if not agent_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        
        if not agent_data.get('workflow_id'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent {agent_id} does not have a workflow configuration"
            )
        
        # Get agent's workflow ID
        workflow_id = agent_data.get('workflow_id')
        
        # Execute workflow
        result = await workflow_service.execute_workflow(
            workflow_id=workflow_id,
            input_message=request.message,
            context=request.context or {},
            llm_provider=None  # Use default
        )
        
        # Build response
        response = WorkflowExecuteResponse(
            agent_id=agent_id,
            agent_name=agent_data.get('name'),
            response=result.get('response', ''),
            execution_time=result.get('execution_time'),
            status='success',
            metadata={
                'conversation_id': request.conversation_id,
                'session_id': request.session_id,
                'history': result.get('history', []),
                'iterations': result.get('iterations', 0)
            }
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute agent: {str(e)}"
        )


@workflow_router.get("/info/{agent_id}", response_model=WorkflowInfoResponse)
async def get_workflow_info(
    agent_id: str = Path(..., description="Agent ID"),
    extensions: AgentBuilderExtensions = Depends(get_agent_builder_extensions)
):
    """
    Get information about an agent's workflow.
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Workflow information
    """
    try:
        # Get agent with workflow data
        agent_data = await extensions.get_agent_with_workflow_data(agent_id)
        if not agent_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        
        if not agent_data.get('workflow_id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} does not have a workflow configuration"
            )
        
        workflow_data = agent_data.get('workflow', {})
        if not workflow_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow data not found for agent {agent_id}"
            )
        
        # Build response
        return WorkflowInfoResponse(
            id=agent_data.get('workflow_id'),
            agent_id=agent_id,
            name=workflow_data.get('name', 'Unnamed Workflow'),
            description=workflow_data.get('description'),
            nodes=len(workflow_data.get('nodes', {})),
            edges=len(workflow_data.get('edges', {})),
            entry_node=str(workflow_data.get('entry_node', '')),
            created_at=workflow_data.get('created_at'),
            updated_at=workflow_data.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow info for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow info: {str(e)}"
        )
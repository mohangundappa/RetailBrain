"""
Agent Workflow API endpoints for Staples Brain.

This module provides API endpoints for accessing workflow information for agents,
allowing the frontend to display workflow configurations, prompts, and related data.
"""
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Path, status
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.workflow_service import WorkflowService
from backend.database.db import get_db
from backend.config.config import get_config

logger = logging.getLogger(__name__)

# Define response models
class WorkflowNodeModel(BaseModel):
    """Model for a workflow node"""
    type: str = Field(..., description="Node type (prompt, tool, etc.)")
    prompt: Optional[str] = Field(None, description="Prompt content if applicable")
    output_key: Optional[str] = Field(None, description="Output key for storing results")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional node configuration")

class WorkflowResponseModel(BaseModel):
    """Response model for workflow information"""
    id: str = Field(..., description="Workflow ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: Dict[str, WorkflowNodeModel] = Field(default_factory=dict, description="Workflow nodes")
    entry_node: str = Field(..., description="Entry node ID")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

# Create workflow service dependency
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
    return WorkflowService(db)

# Create router
agent_workflow_router = APIRouter(
    prefix="/agent-workflows", 
    tags=["agent-workflows"]
)

@agent_workflow_router.get("/{agent_id}", response_model=WorkflowResponseModel)
async def get_agent_workflow(
    agent_id: str = Path(..., description="Agent ID"),
    workflow_service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get workflow information for an agent.
    
    Args:
        agent_id: Agent ID
        workflow_service: Workflow service instance
        
    Returns:
        Workflow information
    """
    try:
        # Get workflow data
        workflow_data = await workflow_service.get_workflow_data_for_agent(agent_id)
        
        if not workflow_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No workflow found for agent {agent_id}"
            )
        
        # Convert nodes data to the expected format
        nodes_dict = {}
        if workflow_data.get('nodes'):
            for node_id, node_data in workflow_data['nodes'].items():
                nodes_dict[node_id] = WorkflowNodeModel(
                    type=node_data.get('type', 'unknown'),
                    prompt=node_data.get('prompt'),
                    output_key=node_data.get('output_key'),
                    config=node_data.get('config')
                )
        
        # Build response
        return WorkflowResponseModel(
            id=workflow_data['id'],
            agent_id=workflow_data['agent_id'],
            name=workflow_data.get('name', 'Unnamed Workflow'),
            description=workflow_data.get('description'),
            nodes=nodes_dict,
            entry_node=workflow_data.get('entry_node', ''),
            created_at=workflow_data.get('created_at'),
            updated_at=workflow_data.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}"
        )
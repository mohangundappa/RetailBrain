"""
Agent Builder Service Extensions for Staples Brain.

This module extends the existing AgentBuilderService with database-driven workflow
capabilities, providing a seamless integration between the current agent implementation
and the new workflow-based approach.
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.agent_builder_service import AgentBuilderService
from backend.services.workflow_service import WorkflowService
from backend.endpoints.schemas.agent_schema import AgentDetailModel

logger = logging.getLogger(__name__)

class AgentBuilderExtensions:
    """
    Extensions for the AgentBuilderService class.
    
    This class adds database-driven workflow capabilities to the existing
    AgentBuilderService implementation.
    """
    
    def __init__(self, agent_builder_service: AgentBuilderService, db_session: AsyncSession):
        """
        Initialize the agent builder extensions.
        
        Args:
            agent_builder_service: The agent builder service to extend
            db_session: Async database session
        """
        self.agent_builder = agent_builder_service
        self.db_session = db_session
        self.workflow_service = WorkflowService(db_session)
        
        logger.info("Initialized Agent Builder Extensions")
    
    async def add_workflow_to_agent(self, agent_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a workflow to an existing agent.
        
        Args:
            agent_id: ID of the agent
            workflow_data: Workflow configuration data
            
        Returns:
            Created workflow data
        """
        try:
            # Create workflow
            workflow = await self.workflow_service.create_workflow(agent_id, workflow_data)
            
            # Update agent detail data with workflow
            agent = await self.agent_builder.get_agent(agent_id)
            if agent:
                agent.workflow_id = workflow.get('id')
                
            return workflow
        except Exception as e:
            logger.error(f"Error adding workflow to agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def convert_hardcoded_to_dynamic(self, agent_id: str, template_data: Dict[str, Any]) -> bool:
        """
        Convert a hardcoded agent to use a database-driven workflow.
        
        Args:
            agent_id: ID of the agent to convert
            template_data: Template data for the new workflow
            
        Returns:
            True if conversion was successful
        """
        try:
            # Create workflow for agent
            await self.workflow_service.create_workflow(agent_id, template_data)
            
            # Mark agent as converted
            await self.db_session.execute(
                """
                UPDATE agent_definitions
                SET is_system = true, 
                    updated_at = $1
                WHERE id = $2
                """,
                datetime.now(),
                agent_id
            )
            
            return True
        except Exception as e:
            logger.error(f"Error converting agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def get_agent_with_workflow_data(self, agent_id: str) -> Dict[str, Any]:
        """
        Get an agent with its workflow data.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent data with workflow details
        """
        try:
            agent = await self.agent_builder.get_agent(agent_id)
            if not agent:
                return None
                
            # Convert to dict
            agent_data = agent.dict()
            
            # Get workflow data if available
            if agent.workflow_id:
                try:
                    workflow_data = await self.workflow_service.get_workflow(agent.workflow_id)
                    agent_data['workflow'] = workflow_data
                except Exception as workflow_err:
                    logger.warning(f"Error loading workflow for agent {agent_id}: {str(workflow_err)}")
                    agent_data['workflow'] = None
                    
            return agent_data
        except Exception as e:
            logger.error(f"Error getting agent with workflow {agent_id}: {str(e)}", exc_info=True)
            raise
            
    async def update_agent_workflow(self, agent_id: str, workflow_id: str, 
                                  workflow_updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an agent's workflow.
        
        Args:
            agent_id: ID of the agent
            workflow_id: ID of the workflow to update
            workflow_updates: Updated workflow data
            
        Returns:
            Updated workflow data
        """
        try:
            # This is a placeholder - in a real implementation, 
            # you'd update the workflow in the database
            logger.info(f"Would update workflow {workflow_id} for agent {agent_id}")
            
            return {
                "id": workflow_id,
                "agent_id": agent_id,
                "updated": True
            }
        except Exception as e:
            logger.error(f"Error updating workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
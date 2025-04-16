"""
Workflow Service for Staples Brain.

This service provides functionality for creating, managing, and executing workflow-based agents.
It connects to the database-driven agent architecture and executes workflows defined in the database.
"""
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend.interpreters.prompt_interpreter import PromptInterpreter
from backend.interpreters.workflow_interpreter import WorkflowInterpreter

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Service for managing and executing database-driven workflows.
    
    This service provides operations for creating, updating, and executing
    workflow-driven agents that are defined in the database.
    """
    
    def __init__(self, db_session: AsyncSession, llm_provider=None):
        """
        Initialize the workflow service.
        
        Args:
            db_session: Async database session
            llm_provider: LLM provider to use for workflow execution
        """
        self.db_session = db_session
        self.llm_provider = llm_provider
        
        # Initialize interpreters
        self.prompt_interpreter = PromptInterpreter(db_session)
        self.workflow_interpreter = WorkflowInterpreter(db_session)
        
        logger.info("Initialized Workflow Service")
    
    async def create_workflow(self, agent_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow for an agent.
        
        Args:
            agent_id: ID of the agent
            workflow_data: Workflow configuration data
            
        Returns:
            Created workflow data
        """
        try:
            # Create workflow
            workflow_id = str(uuid.uuid4())
            workflow_name = workflow_data.get('name', f"Workflow for {agent_id}")
            workflow_description = workflow_data.get('description', '')
            
            workflow_query = """
                INSERT INTO workflows 
                (id, agent_id, name, description, version, is_active, created_by)
                VALUES ($1, $2, $3, $4, 1, true, 'system')
                RETURNING id
            """
            workflow_result = await self.db_session.fetchrow(
                workflow_query,
                workflow_id,
                agent_id,
                workflow_name,
                workflow_description
            )
            
            # Create nodes
            node_id_map = {}
            for node_data in workflow_data.get('nodes', []):
                node_id = str(uuid.uuid4())
                node_name = node_data.get('name')
                node_type = node_data.get('node_type')
                function_name = node_data.get('function_name')
                response_template = node_data.get('response_template')
                config = node_data.get('config', {})
                
                # Create prompt if needed
                prompt_id = None
                if 'prompt_type' in node_data and node_data['prompt_type']:
                    prompt_type = node_data['prompt_type']
                    prompt_content = workflow_data.get('prompts', {}).get(prompt_type, {}).get('content', '')
                    
                    if prompt_content:
                        prompt_description = workflow_data.get('prompts', {}).get(prompt_type, {}).get('description', '')
                        prompt_variables = workflow_data.get('prompts', {}).get(prompt_type, {}).get('variables')
                        
                        prompt_query = """
                            INSERT INTO system_prompts 
                            (id, agent_id, prompt_type, content, description, 
                             version, is_active, created_by, variables)
                            VALUES ($1, $2, $3, $4, $5, 1, true, 'system', $6)
                            RETURNING id
                        """
                        prompt_id = str(uuid.uuid4())
                        await self.db_session.fetchrow(
                            prompt_query,
                            prompt_id,
                            agent_id,
                            prompt_type,
                            prompt_content,
                            prompt_description,
                            json.dumps(prompt_variables) if prompt_variables else None
                        )
                
                # Create node
                node_query = """
                    INSERT INTO workflow_nodes 
                    (id, workflow_id, name, node_type, function_name, 
                     system_prompt_id, response_template, config)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                """
                await self.db_session.fetchrow(
                    node_query,
                    node_id,
                    workflow_id,
                    node_name,
                    node_type,
                    function_name,
                    prompt_id,
                    response_template,
                    json.dumps(config) if config else None
                )
                
                node_id_map[node_name] = node_id
            
            # Create edges
            for edge_data in workflow_data.get('edges', []):
                edge_id = str(uuid.uuid4())
                source_name = edge_data.get('source')
                target_name = edge_data.get('target')
                condition_type = edge_data.get('condition_type', 'direct')
                condition_value = edge_data.get('condition_value')
                priority = edge_data.get('priority', 0)
                
                source_id = node_id_map.get(source_name)
                target_id = node_id_map.get(target_name) if target_name else None
                
                if source_id:
                    edge_query = """
                        INSERT INTO workflow_edges 
                        (id, workflow_id, source_node_id, target_node_id, 
                         condition_type, condition_value, priority)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                    """
                    await self.db_session.fetchrow(
                        edge_query,
                        edge_id,
                        workflow_id,
                        source_id,
                        target_id,
                        condition_type,
                        condition_value,
                        priority
                    )
            
            # Set entry node
            if workflow_data.get('nodes') and len(workflow_data['nodes']) > 0:
                first_node_name = workflow_data['nodes'][0]['name']
                first_node_id = node_id_map.get(first_node_name)
                
                if first_node_id:
                    await self.db_session.execute(
                        """
                        UPDATE workflows
                        SET entry_node = $1
                        WHERE id = $2
                        """,
                        first_node_id,
                        workflow_id
                    )
            
            # Update agent with workflow reference
            await self.db_session.execute(
                """
                UPDATE agent_definitions
                SET workflow_id = $1, 
                    updated_at = $2
                WHERE id = $3
                """,
                workflow_id,
                datetime.now(),
                agent_id
            )
            
            return {
                "id": workflow_id,
                "agent_id": agent_id,
                "name": workflow_name,
                "description": workflow_description,
                "nodes": len(workflow_data.get('nodes', [])),
                "edges": len(workflow_data.get('edges', [])),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating workflow for agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get a workflow by ID.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow data
        """
        try:
            # Use the workflow interpreter to load the complete workflow
            workflow_data = await self.workflow_interpreter.load_workflow(workflow_id)
            return workflow_data
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_message: str,
        context: Optional[Dict[str, Any]] = None,
        llm_provider = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            input_message: Input message from the user
            context: Optional additional context
            llm_provider: Optional LLM provider to use for execution
            
        Returns:
            Execution results
        """
        try:
            # Load workflow
            workflow_data = await self.get_workflow(workflow_id)
            
            # Use provided or default LLM provider
            llm = llm_provider or self.llm_provider
            if not llm:
                raise ValueError("No LLM provider available for workflow execution")
            
            # Set up interpreters
            interpreters = {
                'prompt': self.prompt_interpreter,
                'workflow': self.workflow_interpreter
            }
            
            # Set up execution context
            exec_context = {
                'input': input_message,
                'context': context or {}
            }
            
            # Execute workflow
            result = await self.workflow_interpreter.execute_workflow(
                workflow_data=workflow_data,
                context=exec_context,
                interpreters=interpreters,
                llm=llm
            )
            
            return result
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
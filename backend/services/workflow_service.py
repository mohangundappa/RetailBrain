"""
Workflow Service for Staples Brain.

This module provides a service layer for managing workflow-based agents,
including creating, updating, retrieving, and executing workflows.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class WorkflowService:
    """
    Service for managing workflow-based agents.
    
    This service provides methods for creating, updating, retrieving, and
    executing workflows for database-driven agents.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the workflow service.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session
        logger.info("Initialized WorkflowService")
    
    async def create_workflow(self, agent_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow for an agent.
        
        Args:
            agent_id: ID of the agent
            workflow_data: Workflow configuration data
            
        Returns:
            Created workflow data with ID
        """
        try:
            workflow_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Prepare nodes and edges for storage
            nodes = workflow_data.get('nodes', {})
            edges = workflow_data.get('edges', {})
            entry_node = workflow_data.get('entry_node', '')
            
            # Store workflow in database
            await self.db.execute(
                """
                INSERT INTO workflows (id, agent_id, name, description, 
                                      nodes, edges, entry_node, 
                                      created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                workflow_id,
                agent_id,
                workflow_data.get('name', 'Unnamed Workflow'),
                workflow_data.get('description', ''),
                json.dumps(nodes),
                json.dumps(edges),
                entry_node,
                now,
                now
            )
            
            # Update agent with workflow ID
            await self.db.execute(
                """
                UPDATE agent_definitions
                SET workflow_id = $1,
                    updated_at = $2
                WHERE id = $3
                """,
                workflow_id,
                now,
                agent_id
            )
            
            # Commit the transaction
            await self.db.commit()
            
            # Return created workflow
            return {
                'id': workflow_id,
                'agent_id': agent_id,
                'name': workflow_data.get('name', 'Unnamed Workflow'),
                'description': workflow_data.get('description', ''),
                'nodes': nodes,
                'edges': edges,
                'entry_node': entry_node,
                'created_at': now,
                'updated_at': now
            }
        except Exception as e:
            # Rollback transaction
            await self.db.rollback()
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
            # Get workflow from database
            result = await self.db.execute(
                """
                SELECT id, agent_id, name, description, 
                       nodes, edges, entry_node, 
                       created_at, updated_at
                FROM workflows
                WHERE id = $1
                """,
                workflow_id
            )
            
            row = result.fetchone()
            if not row:
                return None
                
            # Parse JSON data
            nodes = json.loads(row[4]) if row[4] else {}
            edges = json.loads(row[5]) if row[5] else {}
            
            # Return workflow data
            return {
                'id': row[0],
                'agent_id': row[1],
                'name': row[2],
                'description': row[3],
                'nodes': nodes,
                'edges': edges,
                'entry_node': row[6],
                'created_at': row[7].isoformat() if row[7] else None,
                'updated_at': row[8].isoformat() if row[8] else None
            }
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
    
    async def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a workflow.
        
        Args:
            workflow_id: ID of the workflow
            updates: Updated workflow data
            
        Returns:
            Updated workflow data
        """
        try:
            now = datetime.utcnow().isoformat()
            
            # Prepare nodes and edges for storage if provided
            nodes = json.dumps(updates.get('nodes')) if 'nodes' in updates else None
            edges = json.dumps(updates.get('edges')) if 'edges' in updates else None
            
            # Build dynamic update query
            query_parts = []
            params = [workflow_id]  # Start with workflow_id
            param_idx = 2  # PostgreSQL uses $1, $2, etc. for parameters
            
            if 'name' in updates:
                query_parts.append(f"name = ${param_idx}")
                params.append(updates['name'])
                param_idx += 1
                
            if 'description' in updates:
                query_parts.append(f"description = ${param_idx}")
                params.append(updates['description'])
                param_idx += 1
                
            if nodes is not None:
                query_parts.append(f"nodes = ${param_idx}")
                params.append(nodes)
                param_idx += 1
                
            if edges is not None:
                query_parts.append(f"edges = ${param_idx}")
                params.append(edges)
                param_idx += 1
                
            if 'entry_node' in updates:
                query_parts.append(f"entry_node = ${param_idx}")
                params.append(updates['entry_node'])
                param_idx += 1
                
            # Always update the updated_at timestamp
            query_parts.append(f"updated_at = ${param_idx}")
            params.append(now)
            
            # Execute update if we have fields to update
            if query_parts:
                query = f"""
                UPDATE workflows
                SET {', '.join(query_parts)}
                WHERE id = $1
                """
                await self.db.execute(query, *params)
                
                # Commit the transaction
                await self.db.commit()
            
            # Get updated workflow
            return await self.get_workflow(workflow_id)
        except Exception as e:
            # Rollback transaction
            await self.db.rollback()
            logger.error(f"Error updating workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            True if workflow was deleted
        """
        try:
            # Get agent ID first for updating agent
            result = await self.db.execute(
                "SELECT agent_id FROM workflows WHERE id = $1",
                workflow_id
            )
            row = result.fetchone()
            if not row:
                return False
                
            agent_id = row[0]
            
            # Clear workflow ID from agent
            if agent_id:
                await self.db.execute(
                    """
                    UPDATE agent_definitions
                    SET workflow_id = NULL,
                        updated_at = $1
                    WHERE id = $2
                    """,
                    datetime.utcnow().isoformat(),
                    agent_id
                )
            
            # Delete workflow
            await self.db.execute(
                "DELETE FROM workflows WHERE id = $1",
                workflow_id
            )
            
            # Commit the transaction
            await self.db.commit()
            
            return True
        except Exception as e:
            # Rollback transaction
            await self.db.rollback()
            logger.error(f"Error deleting workflow {workflow_id}: {str(e)}", exc_info=True)
            raise
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_message: str,
        context: Dict[str, Any] = None,
        llm_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow.
        
        Args:
            workflow_id: ID of the workflow
            input_message: User input message to process
            context: Additional context data
            llm_provider: Optional LLM provider to use
            
        Returns:
            Execution result
        """
        from backend.interpreters.agent_runner import AgentRunner
        import time
        
        try:
            # Start timing execution
            start_time = time.time()
            
            # Get workflow data
            workflow_data = await self.get_workflow(workflow_id)
            if not workflow_data:
                raise ValueError(f"Workflow with ID {workflow_id} not found")
            
            # Create agent runner
            runner = AgentRunner(
                db_session=self.db,
                workflow_data=workflow_data,
                llm_provider=llm_provider
            )
            
            # Initialize context
            ctx = context or {}
            
            # Execute workflow
            result = await runner.execute(
                input_message=input_message,
                context=ctx
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Return execution result
            return {
                'response': result.get('response', ''),
                'execution_time': execution_time,
                'history': result.get('history', []),
                'iterations': result.get('iterations', 0),
                'state': result.get('state', {})
            }
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow execution failed: {str(e)}")
    
    async def get_workflows_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all workflows for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of workflow data
        """
        try:
            # Get workflows from database
            result = await self.db.execute(
                """
                SELECT id, name, description, entry_node, created_at, updated_at
                FROM workflows
                WHERE agent_id = $1
                ORDER BY created_at DESC
                """,
                agent_id
            )
            
            workflows = []
            rows = result.fetchall()
            
            for row in rows:
                workflows.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'entry_node': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'updated_at': row[5].isoformat() if row[5] else None
                })
                
            return workflows
        except Exception as e:
            logger.error(f"Error getting workflows for agent {agent_id}: {str(e)}", exc_info=True)
            raise
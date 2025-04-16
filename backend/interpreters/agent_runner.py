"""
Agent Runner for Staples Brain.

This module provides a service for executing database-defined agents using workflows.
It coordinates between workflow interpreters, LLM services, and memory.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.interpreters.workflow_interpreter import WorkflowInterpreter

logger = logging.getLogger(__name__)

class AgentRunner:
    """
    Runner for executing database-defined agents.
    
    This class handles the execution of agents based on workflow configurations,
    coordinating between interpreters, LLM services, and memory.
    """
    
    def __init__(
        self, 
        db_session: AsyncSession, 
        workflow_data: Dict[str, Any] = None,
        llm_provider: Optional[str] = None,
        llm_service = None
    ):
        """
        Initialize the agent runner.
        
        Args:
            db_session: Async database session
            workflow_data: Workflow configuration data
            llm_provider: Name of the LLM provider to use
            llm_service: Service for LLM interactions
        """
        self.db = db_session
        self.workflow_data = workflow_data
        self.llm_provider = llm_provider
        self.llm_service = llm_service
        self.workflow_interpreter = WorkflowInterpreter(db_session, llm_service)
        logger.info("Initialized AgentRunner")
    
    async def execute(
        self, 
        agent_id: Optional[str] = None,
        input_message: str = '',
        context: Dict[str, Any] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an agent with the given input.
        
        Args:
            agent_id: ID of the agent to execute
            input_message: User input message
            context: Additional context data
            conversation_id: ID of the conversation
            session_id: ID of the user session
            
        Returns:
            Execution result
        """
        try:
            start_time = time.time()
            
            # Initialize context
            ctx = context or {}
            
            # Add conversation and session IDs to context
            if conversation_id:
                ctx['conversation_id'] = conversation_id
            if session_id:
                ctx['session_id'] = session_id
            
            # Execute the workflow
            if self.workflow_data:
                # Execute the provided workflow
                result = await self.workflow_interpreter.execute_workflow(
                    self.workflow_data,
                    input_message,
                    ctx
                )
            else:
                # Get workflow data from database
                raise ValueError("No workflow data provided and agent ID lookup not implemented yet")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Add execution metadata
            result['execution_time'] = execution_time
            result['agent_id'] = agent_id
            
            return result
        except Exception as e:
            logger.error(f"Error executing agent: {str(e)}", exc_info=True)
            # Return error result
            return {
                'error': str(e),
                'response': f"Error: {str(e)}",
                'execution_time': time.time() - start_time,
                'agent_id': agent_id
            }
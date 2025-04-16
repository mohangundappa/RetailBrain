"""
Agent Runner Service for Staples Brain.

This service provides a way to execute database-driven agent workflows using the
interpreter framework. It serves as a bridge between the existing codebase and
the new database-driven agent architecture.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.interpreters.agent_runner import AgentRunner
from backend.services.llm_service import LlmService
from backend.services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


class AgentRunnerService:
    """
    Service for running database-driven agent workflows.
    
    This service provides a layer between the API endpoints and the agent runner
    framework, handling the execution of database-defined agent workflows.
    """
    
    def __init__(
        self, 
        db_session: AsyncSession, 
        llm_service: LlmService,
        telemetry_service: Optional[TelemetryService] = None
    ):
        """
        Initialize the agent runner service.
        
        Args:
            db_session: Async database session
            llm_service: LLM service for agent execution
            telemetry_service: Optional telemetry service for logging
        """
        self.db_session = db_session
        self.llm_service = llm_service
        self.telemetry_service = telemetry_service
        
        # Initialize runner
        self.runner = AgentRunner(db_session, llm_service, telemetry_service)
        
        logger.info("Initialized Agent Runner Service")
    
    async def execute_agent(
        self, 
        agent_id: str, 
        input_message: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an agent with the given input message.
        
        Args:
            agent_id: UUID of the agent to execute
            input_message: Input message from the user
            conversation_id: Optional conversation ID
            session_id: Optional session ID
            context: Optional additional context
            
        Returns:
            Dict containing execution results
        """
        try:
            # Execute the agent
            result = await self.runner.execute(
                agent_id=agent_id,
                input_message=input_message,
                conversation_id=conversation_id,
                session_id=session_id,
                context=context or {}
            )
            
            return result
        except Exception as e:
            logger.error(f"Error executing agent {agent_id}: {str(e)}", exc_info=True)
            # Return error response
            return {
                "agent_id": agent_id,
                "response": f"I encountered an issue processing your request: {str(e)}",
                "status": "error",
                "error": str(e)
            }
"""
Workflow-aware Database Agent implementation for LangGraph.

This module extends the DatabaseAgent class to support workflow-based agents
with structured conversation handling using LangGraph StateGraph.
"""
import logging
import time
import json
from typing import Dict, List, Optional, Any, Union

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph

from backend.agents.framework.langgraph.database_agent import DatabaseAgent
from backend.memory.factory import get_mem0
from backend.agents.workflows import (
    create_reset_password_workflow,
    execute_reset_password_workflow
)

logger = logging.getLogger(__name__)


class WorkflowDatabaseAgent(DatabaseAgent):
    """
    Database agent with workflow support.
    
    This agent extends the standard DatabaseAgent with support for
    structured conversation workflows using LangGraph.
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str] = None,
        agent_type: str = "LLM",
        config: Optional[Dict[str, Any]] = None,
        status: str = "active",
        is_system: bool = False,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        version: int = 1
    ):
        """
        Initialize a workflow-enabled database agent.
        
        Args:
            id: Unique identifier
            name: Agent name
            description: Agent description
            agent_type: Type of agent (LLM, RULE, RETRIEVAL)
            config: Configuration dictionary
            status: Agent status
            is_system: Whether this is a system agent
            created_at: Creation timestamp
            updated_at: Last update timestamp
            version: Agent version
        """
        super().__init__(
            id, name, description, agent_type, config, status, is_system, created_at, updated_at, version
        )
        
        # Workflow initialization
        self.workflow = None
        
        # Initialize workflow based on agent type
        self._initialize_workflow()
        
    def _initialize_workflow(self) -> None:
        """Initialize the appropriate workflow based on agent type."""
        try:
            if "Reset Password Agent" in self.name:
                # Get model and temperature from config if available
                model_name = self.config.get("model_name", "gpt-4o")
                temperature = self.config.get("temperature", 0.2)
                
                # Initialize the workflow
                self.workflow = create_reset_password_workflow(model_name, temperature)
                logger.info(f"Initialized Reset Password workflow for agent {self.name}")
            
            # Add other agent-specific workflows here as needed
            
        except Exception as e:
            logger.error(f"Error initializing workflow for agent {self.name}: {str(e)}", exc_info=True)
    
    async def process_message(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a message using the appropriate workflow.
        
        Args:
            message: User message
            context: Optional context
            conversation_id: Conversation identifier
            session_id: Session identifier
            
        Returns:
            Processing result
        """
        start_time = time.time()
        
        try:
            # Check for specific workflow handling
            if "Reset Password Agent" in self.name and self.workflow:
                logger.info(f"Using Reset Password workflow for message: {message[:50]}...")
                
                # Execute the workflow
                result = await execute_reset_password_workflow(
                    workflow=self.workflow,
                    message=message,
                    conversation_id=conversation_id or "default",
                    session_id=session_id or "default",
                    context=context
                )
                
                # Build final response
                processing_time = time.time() - start_time
                assistant_response = result.get("response", "I encountered an issue processing your request.")
                logger.info(f"Workflow result keys: {result.keys()}")
                logger.info(f"Extracted response from workflow: {assistant_response[:100]}...")
                
                response = {
                    "id": self.id,
                    "agent_name": self.name,
                    "response": assistant_response,
                    "confidence": 1.0,  # High confidence for workflow-based responses
                    "processing_time": processing_time,
                    "metadata": {
                        "workflow": "reset_password",
                        "current_step": result.get("current_step"),
                        "intent": result.get("reset_intent"),
                        "email_collected": bool(result.get("user_email")),
                        "workflow_succeeded": not bool(result.get("error"))
                    }
                }
                
                return response
            
            # If no specific workflow is available, fall back to standard processing
            logger.info(f"No specific workflow for {self.name}, using standard processing")
            return await super().process_message(message, context, conversation_id, session_id)
            
        except Exception as e:
            logger.error(f"Error in workflow-based processing: {str(e)}", exc_info=True)
            
            # Return error response
            return {
                "id": self.id,
                "agent_name": self.name,
                "response": "I encountered an error processing your request. Please try again later.",
                "confidence": 0.5,
                "processing_time": time.time() - start_time,
                "error": str(e)
            }


async def create_workflow_database_agent_from_definition(agent_def: Dict[str, Any]) -> Optional[WorkflowDatabaseAgent]:
    """
    Create a WorkflowDatabaseAgent instance from an agent definition dictionary.
    
    Args:
        agent_def: Agent definition dictionary
        
    Returns:
        WorkflowDatabaseAgent instance or None if creation fails
    """
    try:
        required_fields = ["id", "name", "agent_type"]
        for field in required_fields:
            if field not in agent_def:
                logger.error(f"Missing required field in agent definition: {field}")
                return None
        
        # Extract configuration based on agent type
        config = {}
        
        # Add base configuration
        if "system_prompt" in agent_def:
            config["system_prompt"] = agent_def["system_prompt"]
        if "few_shot_examples" in agent_def:
            config["few_shot_examples"] = agent_def["few_shot_examples"]
        if "model_name" in agent_def:
            config["model_name"] = agent_def["model_name"]
        if "temperature" in agent_def:
            config["temperature"] = agent_def["temperature"]
            
        # Add type-specific configuration
        agent_type = agent_def["agent_type"].upper()
        
        if agent_type == "LLM" and "llm_config" in agent_def:
            config.update(agent_def["llm_config"])
            
        elif agent_type == "RULE" and "rule_config" in agent_def:
            config.update(agent_def["rule_config"])
            
        elif agent_type == "RETRIEVAL" and "retrieval_config" in agent_def:
            config.update(agent_def["retrieval_config"])
        
        # Add patterns, tools, and response templates
        if "patterns" in agent_def:
            config["patterns"] = agent_def["patterns"]
        if "tools" in agent_def:
            config["tools"] = agent_def["tools"]
        if "response_templates" in agent_def:
            config["response_templates"] = agent_def["response_templates"]
        
        # Create the workflow-enabled agent
        agent = WorkflowDatabaseAgent(
            id=agent_def["id"],
            name=agent_def["name"],
            description=agent_def.get("description"),
            agent_type=agent_def["agent_type"],
            config=config,
            status=agent_def.get("status", "active"),
            is_system=agent_def.get("is_system", False),
            created_at=agent_def.get("created_at"),
            updated_at=agent_def.get("updated_at"),
            version=agent_def.get("version", 1)
        )
        
        return agent
    except Exception as e:
        logger.error(f"Error creating WorkflowDatabaseAgent: {str(e)}", exc_info=True)
        return None
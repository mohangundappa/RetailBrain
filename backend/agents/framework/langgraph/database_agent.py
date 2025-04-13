"""
Database-driven LangGraph Agent implementation.

This module provides a LangGraph agent implementation that derives its configuration
from the database, supporting dynamic agent creation and modification.
"""
import logging
import time
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, Tuple

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.database.agent_schema import AgentDefinition

logger = logging.getLogger(__name__)


class DatabaseAgent(LangGraphAgent):
    """
    LangGraph agent implementation that sources its configuration from the database.
    
    This agent provides dynamic behavior based on configuration stored in the database
    rather than hardcoded behavior. It supports:
    - LLM-based processing
    - Rule-based processing
    - Retrieval-based processing
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
        Initialize a database-driven agent.
        
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
        super().__init__(id, name, description, config)
        
        # Standardize agent type (convert to uppercase for internal processing)
        self.agent_type = agent_type.upper() if agent_type else "LLM"
        self.raw_agent_type = agent_type  # Keep the original agent type for reference
        self.status = status
        self.is_system = is_system
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version
        
        # LLM for agent processing
        self.llm = None
        
        # Agent-specific configurations
        self.system_prompt = config.get("system_prompt", f"You are {name}, an AI assistant.")
        self.few_shot_examples = config.get("few_shot_examples", [])
        self.model_name = config.get("model_name", "gpt-4o")
        self.temperature = config.get("temperature", 0.2)
        
        self.rules = config.get("rules", [])
        self.default_response = config.get("default_response", "I don't have a specific answer for that query.")
        
        self.datasource_id = config.get("datasource_id")
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.max_results = config.get("max_results", 5)
        
        self.response_templates = config.get("response_templates", {})
        self.tools = config.get("tools", [])
        self.patterns = config.get("patterns", [])
        
        # Initialize tooling based on agent type
        self._init_agent_components()
        
        logger.info(f"Initialized DatabaseAgent: {name} (Type: {agent_type})")
    
    def _init_agent_components(self):
        """Initialize the components specific to this agent type."""
        # All LLM-based agents need the OpenAI model
        if self.agent_type in ["LLM", "LLM-DRIVEN", "PACKAGE_TRACKING", "RESET_PASSWORD", 
                              "STORE_LOCATOR", "PRODUCT_INFO", "RETURNS_PROCESSING", 
                              "POLICY-ENFORCER"]:
            # Initialize LLM
            try:
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature
                )
            except Exception as e:
                logger.error(f"Error initializing LLM for agent {self.name}: {str(e)}")
    
    async def process_message(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message asynchronously and generate an appropriate response.
        
        Args:
            message: User input message
            session_id: Session identifier (optional)
            context: Additional context information
            
        Returns:
            Response dictionary
        """
        start_time = time.time()
        self.request_count += 1
        self.last_request_time = start_time
        
        context = context or {}
        
        try:
            result = await self._route_to_processing_method(message, session_id, context)
            
            processing_time = time.time() - start_time
            self.success_count += 1
            
            # Add metadata to the response
            result.update({
                "agent": self.name,
                "agent_id": self.id,
                "agent_type": self.agent_type,
                "processing_time": processing_time
            })
            
            logger.info(f"Agent {self.name} processed message in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.error_count += 1
            processing_time = time.time() - start_time
            logger.error(f"Error processing message with agent {self.name}: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "response": f"I encountered an error while processing your request. {str(e)}",
                "error": str(e),
                "agent": self.name,
                "agent_id": self.id,
                "agent_type": self.agent_type,
                "processing_time": processing_time
            }
    
    async def _route_to_processing_method(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Route the message to the appropriate processing method based on agent type.
        
        Args:
            message: User message
            session_id: Session identifier (optional)
            context: Additional context
            
        Returns:
            Response dictionary
        """
        context = context or {}
        
        # Check for core processing types first
        if self.agent_type == "LLM":
            return await self._process_with_llm(message, session_id, context)
        elif self.agent_type == "RULE":
            return await self._process_with_rules(message, context)
        elif self.agent_type == "RETRIEVAL":
            return await self._process_with_retrieval(message, context)
        
        # Check for specialized agent types - all these use the LLM handler
        # but could have specialized configuration, prompts, etc.
        elif self.agent_type in ["LLM-DRIVEN", "PACKAGE_TRACKING", "RESET_PASSWORD", 
                                "STORE_LOCATOR", "PRODUCT_INFO", "RETURNS_PROCESSING", 
                                "POLICY-ENFORCER"]:
            return await self._process_with_llm(message, session_id, context)
        else:
            logger.warning(f"Unknown agent type: {self.agent_type}, defaulting to LLM")
            return await self._process_with_llm(message, session_id, context)
    
    async def _process_with_llm(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message using the LLM-based approach.
        
        Args:
            message: User message
            session_id: Session identifier (optional)
            context: Additional context
            
        Returns:
            Response dictionary
        """
        context = context or {}
        if not self.llm:
            # Initialize LLM if not already done
            self._init_agent_components()
            
            if not self.llm:
                raise ValueError("LLM initialization failed")
        
        # Get conversation history from context if available
        conversation_history = context.get("conversation_history", [])
        
        # Convert conversation history to message format
        messages: List[BaseMessage] = []
        
        # Add history if available
        if conversation_history:
            for entry in conversation_history:
                role = entry.get("role", "")
                content = entry.get("content", "")
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                elif role == "system":
                    messages.append(SystemMessage(content=content))
        
        # Create prompt with system message, history placeholder, and user message
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}")
        ])
        
        # Create LLM chain
        chain = prompt | self.llm | StrOutputParser()
        
        # Invoke the chain
        response_text = await chain.ainvoke({
            "history": messages,
            "input": message
        })
        
        return {
            "success": True,
            "response": response_text,
            "message": response_text,
            "processed_with": "llm"
        }
    
    async def _process_with_rules(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a message using rule-based approach.
        
        Args:
            message: User message
            context: Additional context
            
        Returns:
            Response dictionary
        """
        # If no rules are defined, return default response
        if not self.rules:
            return {
                "success": True,
                "response": self.default_response,
                "message": self.default_response,
                "processed_with": "rules_default"
            }
        
        # Check each rule against the message
        for rule in self.rules:
            pattern = rule.get("pattern", "")
            response_template = rule.get("response", "")
            
            if not pattern or not response_template:
                continue
                
            try:
                # Check if the rule pattern matches
                import re
                if re.search(pattern, message, re.IGNORECASE):
                    # Replace placeholders in the response template
                    response = response_template
                    
                    # Apply any dynamic substitutions from context or message
                    variables = re.findall(r'\{([^}]+)\}', response)
                    for var in variables:
                        if var in context:
                            response = response.replace(f"{{{var}}}", str(context[var]))
                    
                    return {
                        "success": True,
                        "response": response,
                        "message": response,
                        "processed_with": "rules_match",
                        "matched_pattern": pattern
                    }
            except Exception as e:
                logger.error(f"Error processing rule: {str(e)}")
        
        # If no rules matched, return default response
        return {
            "success": True,
            "response": self.default_response,
            "message": self.default_response,
            "processed_with": "rules_no_match"
        }
    
    async def _process_with_retrieval(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a message using retrieval-based approach.
        
        Args:
            message: User message
            context: Additional context
            
        Returns:
            Response dictionary
        """
        # Check if we have a datasource ID
        if not self.datasource_id:
            # Fall back to LLM processing if no datasource
            logger.warning(f"No datasource configured for retrieval agent {self.name}")
            return await self._process_with_llm(message, context.get("session_id", ""), context)
        
        # TODO: Implement retrieval logic with configured datasource
        # This would typically involve:
        # 1. Generating embeddings for the user query
        # 2. Searching for similar content in the datasource
        # 3. Retrieving relevant information
        # 4. Generating a response based on the retrieved information
        
        # For now, fall back to LLM processing
        return await self._process_with_llm(message, context.get("session_id", ""), context)
    
    async def process(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message and generate an appropriate response.
        
        Args:
            message: User input message
            context: Additional context information
            
        Returns:
            Response dictionary
        """
        session_id = context.get("session_id", "") if context else ""
        context = context or {}
        return await self.process_message(message, session_id, context)


async def create_database_agent_from_definition(agent_def: Dict[str, Any]) -> Optional[DatabaseAgent]:
    """
    Create a DatabaseAgent instance from an agent definition dictionary.
    
    Args:
        agent_def: Agent definition dictionary
        
    Returns:
        DatabaseAgent instance or None if creation fails
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
        
        # Create the agent
        agent = DatabaseAgent(
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
        logger.error(f"Error creating DatabaseAgent: {str(e)}", exc_info=True)
        return None


async def create_database_agent_from_model(agent_model: AgentDefinition) -> Optional[DatabaseAgent]:
    """
    Create a DatabaseAgent instance from a database model instance.
    
    Args:
        agent_model: AgentDefinition database model
        
    Returns:
        DatabaseAgent instance or None if creation fails
    """
    try:
        # Convert model to dictionary
        agent_def = {
            "id": str(agent_model.id),
            "name": agent_model.name,
            "description": agent_model.description,
            "agent_type": agent_model.agent_type,
            "status": agent_model.status,
            "is_system": agent_model.is_system,
            "created_at": agent_model.created_at.isoformat() if agent_model.created_at else None,
            "updated_at": agent_model.updated_at.isoformat() if agent_model.updated_at else None,
            "version": agent_model.version
        }
        
        # Add patterns
        if hasattr(agent_model, 'patterns') and agent_model.patterns:
            agent_def["patterns"] = [
                {
                    "pattern_type": pattern.pattern_type,
                    "pattern_value": pattern.pattern_value,
                    "confidence_boost": pattern.confidence_boost
                }
                for pattern in agent_model.patterns
            ]
        
        # Add tools
        if hasattr(agent_model, 'tools') and agent_model.tools:
            agent_def["tools"] = [
                {
                    "tool_name": tool.tool_name,
                    "tool_description": tool.tool_description,
                    "parameters": tool.parameters,
                    "enabled": tool.enabled
                }
                for tool in agent_model.tools
            ]
        
        # Add response templates
        if hasattr(agent_model, 'response_templates') and agent_model.response_templates:
            agent_def["response_templates"] = {
                template.template_key: template.template_content
                for template in agent_model.response_templates
            }
        
        # Create the agent using the helper function
        return await create_database_agent_from_definition(agent_def)
    
    except Exception as e:
        logger.error(f"Error creating DatabaseAgent from model: {str(e)}", exc_info=True)
        return None
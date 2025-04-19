"""
Base agent class for all Staples Brain agents.

This module provides the BaseAgent abstract base class that defines
the core interface and shared functionality for all agents in the system.
"""
from abc import ABC, abstractmethod
import logging
import re
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set, Type, Union

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSequence, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Import constants for agent names
from backend.config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT
)

# Import other framework components
from backend.agents.framework.guardrails import GuardrailViolation, Guardrails
from backend.agents.framework.entity_definition import EntityDefinition
from backend.agents.framework.entity_collection_state import EntityCollectionState

# Setup logging
logger = logging.getLogger(__name__)

# Tool service will be implemented in a future update
# For now, we'll use a simple placeholder
tool_service = None

class BaseAgent(ABC):
    """
    Base class for all Staples Brain agents.
    
    This class defines the interface that all agents must implement.
    It includes common functionality shared across agents.
    """
    
    def __init__(self, name: str, description: str, llm):
        """
        Initialize a base agent.
        
        Args:
            name: The name of the agent
            description: A short description of what the agent does
            llm: The language model to use for this agent
        """
        self.name = name
        self.description = description
        self.llm = llm
        self.guardrails = Guardrails()
        self.entity_collection_state = EntityCollectionState()
        self.is_in_entity_collection_mode = False
        self.response_history: List[Dict[str, Any]] = []
        self.max_history_length = 10  # Maximum number of interactions to keep in history
        
        # Initialize agent-specific prompt templates
        self.system_prompt_template = self._get_system_prompt_template()
        self.user_prompt_template = self._get_user_prompt_template()
        self.entity_collection_prompt_template = self._get_entity_collection_prompt_template()
        
        # Define required entities for this agent
        self.setup_required_entities()
        
    @abstractmethod
    def setup_required_entities(self) -> None:
        """
        Define the entities that this agent requires.
        
        This method should be implemented by subclasses to define what information
        this agent needs to collect from the user.
        """
        pass
        
    @abstractmethod
    async def get_response(self, message: str, session_id: str, memory_service=None, **kwargs) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            message: The user's message
            session_id: The unique session identifier
            memory_service: Optional memory service for context persistence
            
        Returns:
            A dict containing the response and metadata
        """
        pass
        
    @abstractmethod
    def _get_system_prompt_template(self) -> str:
        """
        Get the system prompt template for this agent.
        
        Returns:
            The system prompt template
        """
        pass
        
    @abstractmethod
    def _get_user_prompt_template(self) -> str:
        """
        Get the user prompt template for this agent.
        
        Returns:
            The user prompt template
        """
        pass
        
    def _get_entity_collection_prompt_template(self) -> str:
        """
        Get the entity collection prompt template.
        
        Returns:
            The entity collection prompt template
        """
        return """
        You are collecting information for a {task_type} request.
        
        You need to collect the following information:
        {entity_requirements}
        
        The customer has provided the following information so far:
        {collected_entities}
        
        You still need to collect:
        {missing_entities}
        
        Current message from the customer:
        {user_message}
        
        Only ask for ONE missing piece of information at a time.
        Be polite and professional in your requests.
        Do not make up information.
        Do not reveal the internal names of the entities (use user-friendly language).
        """
        
    def create_chain(self, prompt_template: str, messages: List[Dict[str, str]]) -> RunnableSequence:
        """
        Create a langchain chain for inference with the agent's LLM.
        
        Args:
            prompt_template: The prompt template to use
            messages: List of message history dicts to include
            
        Returns:
            A RunnableSequence chain
        """
        # Create prompt with message history
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template),
            *[(msg["role"], msg["content"]) for msg in messages]
        ])
        
        # Create the chain
        chain = prompt | self.llm | StrOutputParser()
        
        return chain
        
    def add_entity(self, 
                  name: str, 
                  required: bool = True, 
                  validation_pattern: Optional[str] = None,
                  error_message: Optional[str] = None,
                  description: Optional[str] = None,
                  examples: Optional[List[str]] = None,
                  alternate_names: Optional[List[str]] = None) -> None:
        """
        Add an entity definition to this agent.
        
        Args:
            name: The name of the entity
            required: Whether this entity is required
            validation_pattern: Optional regex pattern for validation
            error_message: Custom error message for invalid values
            description: Description of the entity
            examples: Example values
            alternate_names: Other names for this entity
        """
        entity = EntityDefinition(
            name=name,
            required=required,
            validation_pattern=validation_pattern,
            error_message=error_message,
            description=description,
            examples=examples,
            alternate_names=alternate_names
        )
        self.entity_collection_state.add_entity(entity)
        
    def format_entity_requirements(self) -> str:
        """
        Format entity requirements for inclusion in prompts.
        
        Returns:
            A formatted string describing entity requirements
        """
        result = []
        for entity in self.entity_collection_state.entity_definitions:
            req_str = f"- {entity.description}"
            if entity.examples:
                req_str += f" Example(s): {', '.join(entity.examples)}"
            if not entity.required:
                req_str += " (optional)"
            result.append(req_str)
        return "\n".join(result)
        
    def format_collected_entities(self) -> str:
        """
        Format collected entities for inclusion in prompts.
        
        Returns:
            A formatted string describing collected entities
        """
        collected = self.entity_collection_state.get_collected_entities()
        if not collected:
            return "None yet."
            
        result = []
        for name, value in collected.items():
            # Get the description from the entity definition
            description = self.entity_collection_state.entities[name].description
            result.append(f"- {description}: {value}")
        return "\n".join(result)
        
    def format_missing_entities(self) -> str:
        """
        Format missing entities for inclusion in prompts.
        
        Returns:
            A formatted string describing missing entities
        """
        missing = self.entity_collection_state.get_missing_entities()
        if not missing:
            return "No missing information!"
            
        result = []
        for name in missing:
            # Get the description from the entity definition
            description = self.entity_collection_state.entities[name].description
            result.append(f"- {description}")
        return "\n".join(result)
        
    async def collect_entities(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Process a message for entity collection.
        
        Args:
            message: The user's message
            
        Returns:
            Tuple of (collection_complete, response_message)
            - collection_complete: True if all required entities are collected
            - response_message: The next message to send to the user, or None if collection is complete
        """
        # Set collection mode
        self.is_in_entity_collection_mode = True
        
        # Increment the collection turn counter
        self.entity_collection_state.increment_turn()
        
        # TODO: In the future, use LLM to extract entity values from messages
        # For now, use a simple rule-based approach
        
        # Check if we should exit the collection process
        if self.entity_collection_state.should_exit_collection():
            self.is_in_entity_collection_mode = False
            return True, None
            
        # Get the next entity to collect
        next_entity = self.entity_collection_state.get_next_missing_entity()
        if not next_entity:
            # All required entities are collected
            self.is_in_entity_collection_mode = False
            return True, None
            
        # Set as the current entity
        self.entity_collection_state.current_entity = next_entity
        
        # Create a prompt to collect the entity
        prompt = self.entity_collection_prompt_template.format(
            task_type=self.name,
            entity_requirements=self.format_entity_requirements(),
            collected_entities=self.format_collected_entities(),
            missing_entities=self.format_missing_entities(),
            user_message=message
        )
        
        # Run the LLM to generate a collection message
        messages = [{"role": "system", "content": prompt}]
        chain = self.create_chain(prompt, messages)
        collection_message = await chain.ainvoke({})
        
        return False, collection_message
        
    async def extract_entities_from_message(self, message: str) -> Dict[str, Any]:
        """
        Extract entity values from a user message.
        
        Args:
            message: The user's message
            
        Returns:
            A dictionary of entity names and extracted values
        """
        # TODO: Use LLM to extract entities
        # For now, use simple pattern matching for common entities
        
        extracted = {}
        
        # Extract order numbers - simple pattern for now
        order_pattern = r'\b[A-Z0-9]{8,12}\b'
        order_matches = re.findall(order_pattern, message)
        if order_matches and "order_number" in self.entity_collection_state.entities:
            extracted["order_number"] = order_matches[0]
            
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, message)
        if email_matches and "email" in self.entity_collection_state.entities:
            extracted["email"] = email_matches[0]
            
        # Extract zip codes
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
        zip_matches = re.findall(zip_pattern, message)
        if zip_matches and "zip_code" in self.entity_collection_state.entities:
            extracted["zip_code"] = zip_matches[0]
            
        return extracted
        
    async def detect_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect and extract tool calls from text.
        
        Args:
            text: Text that may contain tool calls
            
        Returns:
            List of extracted tool calls, each a dict with tool_name and tool_args
        """
        # Pattern for tool calls in JSON format
        tool_calls = []
        
        # Simple pattern matching for JSON tool calls
        # Format: {"tool_name": "some_tool", "tool_args": {"arg1": "value1"}}
        json_pattern = r'({(?:[^{}]|(?R))*})'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                # Try to parse as JSON
                tool_call = json.loads(match)
                
                # Check if it's a valid tool call
                if "tool_name" in tool_call and "tool_args" in tool_call:
                    tool_name = tool_call["tool_name"]
                    tool_args = tool_call["tool_args"]
                    
                    # Validate that tool exists
                    if tool_service and tool_service.has_tool(tool_name):
                        tool_calls.append({
                            "tool_name": tool_name,
                            "tool_args": tool_args
                        })
            except json.JSONDecodeError:
                # Not valid JSON
                pass
        
        return tool_calls
            
    async def execute_detected_tool_calls(self, text: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Execute tool calls detected in text.
        
        Args:
            text: Text that may contain tool calls
            
        Returns:
            Tuple of (tool_results, updated_text)
            where updated_text has tool calls replaced with their results
        """
        # Detect tool calls in the text
        tool_calls = await self.detect_tool_calls(text)
        
        if not tool_calls:
            return [], text
            
        # Execute detected tool calls
        tool_results = []
        updated_text = text
        
        for tool_call in tool_calls:
            tool_name = tool_call["tool_name"]
            tool_args = tool_call["tool_args"]
            
            # Execute the tool call
            result = await self.call_tool(tool_name, **tool_args)
            tool_results.append(result)
            
            # Update text to include tool results
            # This replaces the tool call JSON with the result, if it exists
            json_str = json.dumps(tool_call)
            if json_str in updated_text:
                result_str = json.dumps(result, indent=2)
                updated_text = updated_text.replace(json_str, f"TOOL RESULT: {result_str}")
        
        return tool_results, updated_text
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool by name with arguments.
        
        Args:
            tool_name: The name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of calling the tool
        """
        if tool_service and tool_service.has_tool(tool_name):
            try:
                return await tool_service.call_tool(tool_name, **kwargs)
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {str(e)}")
                return {"error": f"Tool {tool_name} failed: {str(e)}"}
        else:
            logger.warning(f"Tool {tool_name} not found")
            return {"error": f"Tool {tool_name} not found"}
            
    def add_to_response_history(self, user_message: str, agent_response: str) -> None:
        """
        Add an interaction to the response history.
        
        Args:
            user_message: The user's message
            agent_response: The agent's response
        """
        self.response_history.append({
            "user": user_message,
            "agent": agent_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if it exceeds max length
        if len(self.response_history) > self.max_history_length:
            self.response_history = self.response_history[-self.max_history_length:]
            
    def get_formatted_history(self) -> str:
        """
        Get the response history formatted for inclusion in prompts.
        
        Returns:
            Formatted conversation history
        """
        if not self.response_history:
            return "No previous conversation."
            
        formatted = []
        for interaction in self.response_history:
            formatted.append(f"User: {interaction['user']}")
            formatted.append(f"Agent: {interaction['agent']}")
            formatted.append("")  # Empty line between interactions
            
        return "\n".join(formatted)
        
    def is_out_of_scope(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a message is out of scope for this agent.
        
        Args:
            message: The user's message
            
        Returns:
            Tuple of (is_out_of_scope, reason)
        """
        # Delegate to the guardrails
        return self.guardrails.is_out_of_scope(message)
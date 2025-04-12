"""
Base Agent module for Staples Brain.

This module provides the base class for all agents in the system,
as well as utility functions for agent management.
"""
import logging
import uuid
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable

# For maintaining LangGraph compatibility
try:
    import langchain.chains as chains
    import langchain.prompts as prompts
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
    from langchain_core.runnables import RunnableConfig
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)


class BaseEntity:
    """Base class for entity definitions."""
    
    def __init__(
        self, 
        name: str, 
        entity_type: str,
        description: str,
        required: bool = False,
        validation_regex: Optional[str] = None,
        validation_message: Optional[str] = None,
        examples: Optional[List[str]] = None,
        enum_values: Optional[List[str]] = None
    ):
        self.name = name
        self.entity_type = entity_type
        self.description = description
        self.required = required
        self.validation_regex = validation_regex
        self.validation_message = validation_message or f"Please provide a valid {name}"
        self.examples = examples or []
        self.enum_values = enum_values or []
        
    def is_valid(self, value: str) -> bool:
        """Validate an entity value against the defined constraints."""
        if not value and self.required:
            return False
            
        if self.validation_regex and value:
            return bool(re.match(self.validation_regex, value))
            
        if self.enum_values and value and value not in self.enum_values:
            return False
            
        return True


class BaseAgent:
    """
    Base class for all agents in the system.
    Provides common functionality for agent definition, pattern registration,
    entity management, and message processing.
    """
    
    def __init__(self, agent_id: str, name: str, description: Optional[str] = None):
        """
        Initialize the agent with basic metadata.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Descriptive name of the agent
            description: Optional description of the agent's functionality
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.description = description or f"{name} Agent"
        self.patterns = []
        self.entity_definitions = {}
        self.response_templates = {}
        self.agent_type = "base"
        self._tools = {}
        
    @property
    def id(self) -> str:
        """Get the agent ID."""
        return self.agent_id
        
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message. Base implementation returns a simple response.
        
        Args:
            message: User message
            context: Optional message context
            
        Returns:
            Response dictionary with success flag, response text, and metadata
        """
        # Default implementation - should be overridden by subclasses
        return {
            "success": True,
            "agent": self.name,
            "agent_id": self.id,
            "response": f"I'm the {self.name} agent and I processed: '{message}'",
            "confidence": 1.0
        }
        
    def register_pattern(self, pattern: str, weight: float = 1.0) -> None:
        """
        Register a pattern for agent selection.
        
        Args:
            pattern: Pattern string (regex)
            weight: Pattern weight for scoring
        """
        self.patterns.append({"pattern": pattern, "weight": weight})
        
    def add_entity_definition(self, entity: Union[BaseEntity, Dict[str, Any]]) -> None:
        """
        Add an entity definition for extraction during processing.
        
        Args:
            entity: Entity definition (BaseEntity instance or dictionary)
        """
        if isinstance(entity, BaseEntity):
            self.entity_definitions[entity.name] = {
                "type": entity.entity_type,
                "description": entity.description,
                "validation_regex": entity.validation_regex,
                "required": entity.required,
                "examples": entity.examples,
                "enum_values": entity.enum_values
            }
        elif isinstance(entity, dict):
            self.entity_definitions[entity.get("name", f"entity_{len(self.entity_definitions)}")] = entity
        
    def add_response_template(self, name: str, template: str) -> None:
        """
        Add a response template for generating responses.
        
        Args:
            name: Template name
            template: Template string with placeholders
        """
        self.response_templates[name] = template
        
    def add_tool(self, name: str, tool_callback: Callable, description: str) -> None:
        """
        Add a tool that this agent can use during processing.
        
        Args:
            name: Tool name
            tool_callback: Function to call when tool is invoked
            description: Description of tool functionality
        """
        self.add_tool_with_schema(name, tool_callback, description, {})
            
    def add_tool_with_schema(self, name: str, tool_callback: Callable, 
                           description: str, schema: Dict[str, Any]) -> None:
        """
        Add a tool with a parameter schema that this agent can use.
        
        Args:
            name: Tool name
            tool_callback: Function to call when tool is invoked
            description: Description of tool functionality
            schema: JSON schema for tool parameters
        """
        self._tools[name] = {
            "callback": tool_callback,
            "description": description,
            "schema": schema
        }
        
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name with parameters.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found for agent {self.name}")
            
        tool = self._tools[tool_name]
        return tool["callback"](**kwargs)
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get information about tools available to this agent.
        
        Returns:
            List of tool definitions (name, description, schema)
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "schema": tool["schema"]
            }
            for name, tool in self._tools.items()
        ]
        
    def extract_entities(self, message: str) -> Dict[str, Any]:
        """
        Extract entities from a message using the agent's entity definitions.
        Base implementation uses simple regex extraction.
        
        Args:
            message: User message
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        for entity_name, entity_def in self.entity_definitions.items():
            # Simple extraction based on regex if available
            if entity_def.get("validation_regex"):
                matches = re.findall(entity_def["validation_regex"], message)
                if matches:
                    entities[entity_name] = matches[0]
                    
        return entities
            

class RuleBasedAgent(BaseAgent):
    """
    Agent that uses rule-based pattern matching for responses.
    """
    
    def __init__(self, agent_id: str, name: str, description: Optional[str] = None):
        super().__init__(agent_id, name, description)
        self.agent_type = "rule_based"
        self.rules = []
        
    def add_rule(self, pattern: str, response: str, priority: int = 1) -> None:
        """
        Add a rule for response generation.
        
        Args:
            pattern: Regex pattern to match
            response: Response template to use
            priority: Rule priority (higher=higher precedence)
        """
        self.rules.append({
            "pattern": pattern,
            "response": response,
            "priority": priority
        })
        
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process message using rule-based matching.
        
        Args:
            message: User message
            context: Optional message context
            
        Returns:
            Response dictionary
        """
        context = context or {}
        entities = self.extract_entities(message)
        
        # Add extracted entities to context
        context.update({"entities": entities})
        
        # Sort rules by priority (descending)
        sorted_rules = sorted(self.rules, key=lambda r: r["priority"], reverse=True)
        
        # Find the first matching rule
        for rule in sorted_rules:
            if re.search(rule["pattern"], message, re.IGNORECASE):
                # Process response template
                response = rule["response"]
                
                # Replace entity placeholders
                for entity_name, entity_value in entities.items():
                    placeholder = f"{{{{{entity_name}}}}}"
                    if placeholder in response:
                        response = response.replace(placeholder, str(entity_value))
                        
                return {
                    "success": True,
                    "agent": self.name,
                    "agent_id": self.id,
                    "response": response,
                    "confidence": 1.0,
                    "entities": entities
                }
                
        # Default response if no rule matches
        return {
            "success": True,
            "agent": self.name,
            "agent_id": self.id,
            "response": f"I'm the {self.name} agent but I don't have a rule that matches your request.",
            "confidence": 0.5,
            "entities": entities
        }


# Compatibility with LangGraph-based implementation
class LangGraphAgent(BaseAgent):
    """
    Agent that uses LangChain/LangGraph for processing.
    """
    
    def __init__(self, agent_id: str, name: str, description: Optional[str] = None):
        super().__init__(agent_id, name, description)
        self.agent_type = "langgraph"
        
        # Check if LangChain is available
        if not LANGCHAIN_AVAILABLE:
            logger.warning(f"LangChain not available for {name} agent. Functionality will be limited.")
            
        self.system_prompt = f"You are {name}, an AI assistant."
        self.llm = None
        
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt for this agent.
        
        Args:
            prompt: System prompt
        """
        self.system_prompt = prompt
            
    def setup_langchain(self, model_name: str = "gpt-4") -> None:
        """
        Set up LangChain components for this agent.
        
        Args:
            model_name: Name of the LLM model to use
        """
        if not LANGCHAIN_AVAILABLE:
            logger.error("Cannot setup LangChain - package not available")
            return
            
        try:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(model=model_name, temperature=0.1)
        except ImportError:
            logger.error("langchain_openai not available")
            
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message using LangChain.
        
        Args:
            message: User message
            context: Optional message context
            
        Returns:
            Response dictionary
        """
        if not LANGCHAIN_AVAILABLE or not self.llm:
            # Fall back to base implementation
            return super().process_message(message, context)
            
        context = context or {}
        entities = self.extract_entities(message)
        
        try:
            # Create a simple chain
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", message)
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({})
            
            return {
                "success": True,
                "agent": self.name,
                "agent_id": self.id,
                "response": response,
                "confidence": 1.0,
                "entities": entities
            }
        except Exception as e:
            logger.error(f"Error in LangGraphAgent.process_message: {str(e)}")
            return {
                "success": False,
                "agent": self.name,
                "agent_id": self.id,
                "response": f"I encountered an error while processing your request: {str(e)}",
                "confidence": 0.0,
                "entities": entities,
                "error": str(e)
            }


# Agent registry for compatibility
_AGENT_REGISTRY: Dict[str, BaseAgent] = {}

# Agent factory functions for compatibility
def initialize_agent(agent_id: str, name: str, **kwargs) -> BaseAgent:
    """
    Initialize a BaseAgent instance.
    
    Args:
        agent_id: Agent ID
        name: Agent name
        **kwargs: Additional parameters
        
    Returns:
        BaseAgent instance
    """
    agent_type = kwargs.get("agent_type", "base")
    
    if agent_type == "rule_based":
        agent = RuleBasedAgent(agent_id, name, kwargs.get("description"))
    elif agent_type == "langgraph" and LANGCHAIN_AVAILABLE:
        agent = LangGraphAgent(agent_id, name, kwargs.get("description"))
    else:
        agent = BaseAgent(agent_id, name, kwargs.get("description"))
        
    # Register agent
    register_agent(agent)
    
    return agent
    
def register_agent(agent: BaseAgent) -> None:
    """
    Register an agent in the global registry.
    
    Args:
        agent: Agent to register
    """
    _AGENT_REGISTRY[agent.id] = agent
    logger.info(f"Registered agent {agent.name} with ID {agent.id}")
    
def get_agent_by_id(agent_id: str) -> Optional[BaseAgent]:
    """
    Get an agent by ID from the registry.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        BaseAgent instance or None if not found
    """
    return _AGENT_REGISTRY.get(agent_id)
    
def get_all_agents() -> List[BaseAgent]:
    """
    Get all registered agents.
    
    Returns:
        List of all registered agents
    """
    return list(_AGENT_REGISTRY.values())
    
def get_agent_names() -> List[str]:
    """
    Get names of all registered agents.
    
    Returns:
        List of agent names
    """
    return [agent.name for agent in _AGENT_REGISTRY.values()]
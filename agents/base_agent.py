from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, List, Optional
from langchain.schema import BaseMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

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
        self.memory = []  # Simple memory for demo purposes
        logger.info(f"Initialized agent: {name}")
        
    @abstractmethod
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user input and return a response.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A dictionary containing the agent's response and any metadata
        """
        pass
    
    @abstractmethod
    def can_handle(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given user input.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A confidence score between 0 and 1 indicating how well this agent can handle the input
        """
        pass
    
    def _create_chain(self, template: str, input_variables: List[str]) -> LLMChain:
        """
        Create a simple LLM chain with the given template.
        
        Args:
            template: The prompt template
            input_variables: The variables required by the template
            
        Returns:
            An LLMChain that can be invoked
        """
        prompt = ChatPromptTemplate.from_template(template)
        return LLMChain(llm=self.llm, prompt=prompt)
    
    def add_to_memory(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the agent's memory.
        
        Args:
            message: The message to add
        """
        self.memory.append(message)
        # Limit memory size
        if len(self.memory) > 10:
            self.memory.pop(0)
            
    def get_memory(self) -> List[Dict[str, Any]]:
        """
        Get the agent's memory.
        
        Returns:
            The agent's memory as a list of messages
        """
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear the agent's memory."""
        self.memory = []

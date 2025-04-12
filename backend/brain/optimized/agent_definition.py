"""
Agent definition models for the optimized brain.
This module provides models for defining agents in the optimized brain.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class EntityDefinition:
    """Entity definition for the agent."""
    
    def __init__(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        validation_regex: Optional[str] = None
    ):
        """
        Initialize an entity definition.
        
        Args:
            name: Entity name
            entity_type: Type of entity (e.g., "email", "order_number")
            description: Optional description
            validation_regex: Optional regex for validation
        """
        self.name = name
        self.entity_type = entity_type
        self.description = description
        self.validation_regex = validation_regex
        self.enum_values: List[Dict[str, str]] = []
        
    def add_enum_value(self, value: str, description: Optional[str] = None):
        """
        Add an enum value for this entity.
        
        Args:
            value: Value of the enum
            description: Optional description
        """
        self.enum_values.append({
            "value": value,
            "description": description
        })


class AgentTool:
    """Tool that an agent can use."""
    
    def __init__(
        self,
        name: str,
        description: str,
        schema: Dict[str, Any],
        function: str,
        auth_required: bool = False
    ):
        """
        Initialize an agent tool.
        
        Args:
            name: Tool name
            description: Tool description
            schema: JSON schema for the tool
            function: Function name to call
            auth_required: Whether authentication is required
        """
        self.name = name
        self.description = description
        self.schema = schema
        self.function = function
        self.auth_required = auth_required


class PatternCapability:
    """Capability for matching patterns."""
    
    def __init__(self):
        """Initialize a pattern capability."""
        self.patterns: List[Dict[str, Any]] = []
        
    def add_pattern(
        self,
        pattern_type: str,
        pattern_value: str,
        confidence_boost: float = 0.0
    ):
        """
        Add a pattern to the capability.
        
        Args:
            pattern_type: Type of pattern (e.g., "regex", "keyword")
            pattern_value: Pattern value
            confidence_boost: Confidence boost when this pattern matches
        """
        self.patterns.append({
            "type": pattern_type,
            "value": pattern_value,
            "confidence_boost": confidence_boost
        })
        
    def get_all_text(self) -> str:
        """
        Get all pattern text for embedding generation.
        
        Returns:
            Combined pattern text
        """
        # Combine all patterns into a single string for embedding
        text_parts = []
        
        for pattern in self.patterns:
            if pattern["type"] == "regex":
                # For regex patterns, extract keywords that might be in the regex
                regex_keywords = re.findall(r'\b[a-zA-Z]+\b', pattern["value"])
                if regex_keywords:
                    text_parts.append(" ".join(regex_keywords))
            else:
                # For other pattern types, use the pattern value directly
                text_parts.append(pattern["value"])
                
        return " ".join(text_parts)
        
    def matches(self, text: str) -> float:
        """
        Check if the text matches any patterns.
        
        Args:
            text: Text to check
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        max_confidence = 0.0
        
        for pattern in self.patterns:
            pattern_type = pattern["type"]
            pattern_value = pattern["value"]
            boost = pattern.get("confidence_boost", 0.0)
            
            if pattern_type == "regex":
                # Regex pattern
                try:
                    if re.search(pattern_value, text, re.IGNORECASE):
                        confidence = 0.7 + boost  # Base confidence for regex match
                        max_confidence = max(max_confidence, confidence)
                except Exception as e:
                    logger.error(f"Error in regex pattern: {str(e)}")
            elif pattern_type == "keyword":
                # Keyword pattern
                if pattern_value.lower() in text.lower():
                    # Higher confidence for exact matches
                    if re.search(r'\b' + re.escape(pattern_value) + r'\b', text, re.IGNORECASE):
                        confidence = 0.8 + boost
                    else:
                        confidence = 0.5 + boost
                    max_confidence = max(max_confidence, confidence)
            elif pattern_type == "prefix":
                # Prefix pattern
                if text.lower().startswith(pattern_value.lower()):
                    confidence = 0.9 + boost  # High confidence for prefix match
                    max_confidence = max(max_confidence, confidence)
            # Add more pattern types as needed
            
        return min(max_confidence, 1.0)  # Cap at 1.0


class AgentDefinition:
    """Definition of an agent in the optimized brain."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        version: int = 1
    ):
        """
        Initialize an agent definition.
        
        Args:
            id: Agent ID
            name: Agent name
            description: Agent description
            version: Agent version
        """
        self.id = id
        self.name = name
        self.description = description
        self.version = version
        
        # Additional properties
        self.status = "active"
        self.is_system = False
        self.capabilities: List[Any] = []
        self.tools: List[AgentTool] = []
        self.entity_definitions: List[EntityDefinition] = []
        self.domain_examples: List[str] = []
        self.llm_configuration: Dict[str, Any] = {}
        self.response_templates: Dict[str, str] = {}
        
    def add_capability(self, capability: Any):
        """
        Add a capability to the agent.
        
        Args:
            capability: Capability to add
        """
        self.capabilities.append(capability)
        
    def add_tool(self, tool: AgentTool):
        """
        Add a tool to the agent.
        
        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        
    def add_entity_definition(self, entity_definition: EntityDefinition):
        """
        Add an entity definition to the agent.
        
        Args:
            entity_definition: Entity definition to add
        """
        self.entity_definitions.append(entity_definition)
        
    def add_domain_example(self, example: str):
        """
        Add a domain example to the agent.
        
        Args:
            example: Example to add
        """
        self.domain_examples.append(example)
        
    def set_llm_configuration(self, config: Dict[str, Any]):
        """
        Set the LLM configuration for the agent.
        
        Args:
            config: LLM configuration
        """
        self.llm_configuration = config
        
    def add_response_template(self, name: str, template: str):
        """
        Add a response template to the agent.
        
        Args:
            name: Template name
            template: Template text
        """
        self.response_templates[name] = template
        
    def get_embedding_text(self) -> str:
        """
        Get the text to use for embedding this agent.
        
        Returns:
            Text for embedding
        """
        parts = []
        
        # Add name and description
        parts.append(f"Agent: {self.name}")
        parts.append(f"Description: {self.description}")
        
        # Add domain examples
        if self.domain_examples:
            parts.append("Examples:")
            parts.extend(self.domain_examples)
            
        # Add pattern texts from capabilities
        for capability in self.capabilities:
            if hasattr(capability, 'get_all_text'):
                pattern_text = capability.get_all_text()
                if pattern_text:
                    parts.append(pattern_text)
                    
        # Add entity descriptions
        if self.entity_definitions:
            entity_texts = []
            for entity in self.entity_definitions:
                if entity.description:
                    entity_texts.append(f"{entity.name}: {entity.description}")
            if entity_texts:
                parts.append("Entities: " + " ".join(entity_texts))
                
        # Join all parts
        return " ".join(parts)
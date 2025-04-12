"""
Optimized Agent Definition models.
These models support the optimized agent selection process.
"""
import uuid
from typing import Dict, List, Optional, Union, Any


class EntityDefinition:
    """Definition of an entity that can be extracted from user input."""
    
    def __init__(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        example_values: Optional[List[str]] = None,
        validation_regex: Optional[str] = None
    ):
        """
        Initialize an entity definition.
        
        Args:
            name: Name of the entity
            entity_type: Type of entity (string, email, number, enum, etc.)
            description: Description of what this entity represents
            example_values: Example values for this entity
            validation_regex: Regex pattern for validation
        """
        self.name = name
        self.entity_type = entity_type
        self.description = description
        self.example_values = example_values or []
        self.validation_regex = validation_regex
        self.enum_values: List[Dict[str, str]] = []
        
    def add_enum_value(self, value: str, description: Optional[str] = None) -> 'EntityDefinition':
        """
        Add a valid enum value.
        
        Args:
            value: The enum value
            description: Description of this value
            
        Returns:
            Self for chaining
        """
        self.enum_values.append({
            "value": value,
            "description": description
        })
        return self
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "example_values": self.example_values,
            "validation_regex": self.validation_regex,
            "enum_values": self.enum_values
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityDefinition':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            EntityDefinition instance
        """
        entity = cls(
            name=data.get("name", ""),
            entity_type=data.get("entity_type", "string"),
            description=data.get("description"),
            example_values=data.get("example_values"),
            validation_regex=data.get("validation_regex")
        )
        
        # Add enum values if they exist
        for enum_value in data.get("enum_values", []):
            entity.add_enum_value(
                enum_value.get("value", ""),
                enum_value.get("description")
            )
            
        return entity


class AgentTool:
    """Definition of a tool that an agent can use."""
    
    def __init__(
        self,
        name: str,
        description: str,
        schema: Optional[Dict[str, Any]] = None,
        function: Optional[str] = None,
        auth_required: bool = False
    ):
        """
        Initialize a tool definition.
        
        Args:
            name: Name of the tool
            description: Description of what this tool does
            schema: JSON Schema for tool inputs
            function: Function reference or name
            auth_required: Whether this tool requires authentication
        """
        self.name = name
        self.description = description
        self.schema = schema or {}
        self.function = function
        self.auth_required = auth_required
        self.is_system = False
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "function": self.function if isinstance(self.function, str) else None,
            "auth_required": self.auth_required,
            "is_system": self.is_system
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTool':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            AgentTool instance
        """
        tool = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            schema=data.get("schema"),
            function=data.get("function"),
            auth_required=data.get("auth_required", False)
        )
        tool.is_system = data.get("is_system", False)
        return tool


class PatternCapability:
    """Capability for matching patterns in user input."""
    
    def __init__(self, patterns: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize a pattern matching capability.
        
        Args:
            patterns: List of pattern dictionaries
        """
        self.type = "pattern_matching"
        self.patterns = patterns or []
        
    def add_pattern(
        self,
        pattern_type: str,
        pattern_value: str,
        confidence_boost: float = 0.1
    ) -> 'PatternCapability':
        """
        Add a pattern for this capability.
        
        Args:
            pattern_type: Type of pattern (regex, keyword, semantic)
            pattern_value: Value of the pattern
            confidence_boost: Confidence boost when pattern matches
            
        Returns:
            Self for chaining
        """
        self.patterns.append({
            "type": pattern_type,
            "value": pattern_value,
            "confidence_boost": confidence_boost
        })
        return self
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "type": self.type,
            "patterns": self.patterns
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternCapability':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            PatternCapability instance
        """
        capability = cls()
        for pattern in data.get("patterns", []):
            capability.add_pattern(
                pattern_type=pattern.get("type", "keyword"),
                pattern_value=pattern.get("value", ""),
                confidence_boost=pattern.get("confidence_boost", 0.1)
            )
        return capability


class AgentDefinition:
    """
    Complete definition of an agent with all components.
    This is used by the optimized agent selection system.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        id: Optional[str] = None,
        version: int = 1
    ):
        """
        Initialize an agent definition.
        
        Args:
            name: Name of the agent
            description: Description of what this agent does
            id: Unique ID for this agent
            version: Version number
        """
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.version = version
        self.status = "active"
        self.is_system = False
        
        # Components
        self.capabilities: List[PatternCapability] = []
        self.tools: List[AgentTool] = []
        self.entity_definitions: List[EntityDefinition] = []
        self.domain_examples: List[str] = []
        self.response_templates: Dict[str, str] = {}
        self.llm_configuration: Dict[str, Any] = {}
        self.state_schema: Dict[str, Any] = {}
        
        # Cached representation for embedding
        self._text_representation: Optional[str] = None
        
    def add_capability(self, capability: PatternCapability) -> 'AgentDefinition':
        """
        Add a capability to this agent.
        
        Args:
            capability: Capability to add
            
        Returns:
            Self for chaining
        """
        self.capabilities.append(capability)
        self._text_representation = None  # Reset cached representation
        return self
        
    def add_tool(self, tool: AgentTool) -> 'AgentDefinition':
        """
        Add a tool to this agent.
        
        Args:
            tool: Tool to add
            
        Returns:
            Self for chaining
        """
        self.tools.append(tool)
        self._text_representation = None
        return self
        
    def add_entity_definition(self, entity: EntityDefinition) -> 'AgentDefinition':
        """
        Add an entity definition to this agent.
        
        Args:
            entity: Entity definition to add
            
        Returns:
            Self for chaining
        """
        self.entity_definitions.append(entity)
        self._text_representation = None
        return self
        
    def add_domain_example(self, example: str) -> 'AgentDefinition':
        """
        Add an example query this agent can handle.
        
        Args:
            example: Example query
            
        Returns:
            Self for chaining
        """
        self.domain_examples.append(example)
        self._text_representation = None
        return self
        
    def add_response_template(self, name: str, template: str) -> 'AgentDefinition':
        """
        Add a response template for this agent.
        
        Args:
            name: Name of the template
            template: Template string
            
        Returns:
            Self for chaining
        """
        self.response_templates[name] = template
        self._text_representation = None
        return self
        
    def set_llm_configuration(self, config: Dict[str, Any]) -> 'AgentDefinition':
        """
        Set LLM configuration for this agent.
        
        Args:
            config: LLM configuration dictionary
            
        Returns:
            Self for chaining
        """
        self.llm_configuration = config
        return self
        
    def get_text_representation(self) -> str:
        """
        Get a comprehensive text representation of this agent.
        This is used for embedding generation.
        
        Returns:
            Text representation
        """
        if self._text_representation:
            return self._text_representation
            
        sections = []
        
        # Basic information
        sections.append(f"Agent: {self.name}")
        sections.append(f"Description: {self.description}")
        
        # Domain examples
        if self.domain_examples:
            examples = "\n".join([f"- {example}" for example in self.domain_examples])
            sections.append(f"Examples of queries this agent can handle:\n{examples}")
        
        # Entity extraction
        if self.entity_definitions:
            entities = "\n".join([
                f"- {entity.name}: {entity.description or ''} (Type: {entity.entity_type})"
                for entity in self.entity_definitions
            ])
            sections.append(f"Entities this agent can extract:\n{entities}")
        
        # Tools
        if self.tools:
            tools = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in self.tools
            ])
            sections.append(f"Tools this agent can use:\n{tools}")
        
        # Patterns (from capabilities)
        patterns = []
        for cap in self.capabilities:
            if isinstance(cap, PatternCapability):
                for pattern in cap.patterns:
                    if pattern.get("type") == "semantic":
                        patterns.append(pattern.get("value", ""))
        
        if patterns:
            patterns_text = "\n".join([f"- {pattern}" for pattern in patterns])
            sections.append(f"Patterns this agent recognizes:\n{patterns_text}")
        
        # Join all sections
        self._text_representation = "\n\n".join(sections)
        return self._text_representation
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "is_system": self.is_system,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "tools": [tool.to_dict() for tool in self.tools],
            "entity_definitions": [entity.to_dict() for entity in self.entity_definitions],
            "domain_examples": self.domain_examples,
            "response_templates": self.response_templates,
            "llm_configuration": self.llm_configuration,
            "state_schema": self.state_schema
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentDefinition':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            AgentDefinition instance
        """
        agent = cls(
            id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", 1)
        )
        
        agent.status = data.get("status", "active")
        agent.is_system = data.get("is_system", False)
        
        # Load capabilities
        for cap_data in data.get("capabilities", []):
            if cap_data.get("type") == "pattern_matching":
                capability = PatternCapability.from_dict(cap_data)
                agent.add_capability(capability)
            
        # Load tools
        for tool_data in data.get("tools", []):
            tool = AgentTool.from_dict(tool_data)
            agent.add_tool(tool)
            
        # Load entity definitions
        for entity_data in data.get("entity_definitions", []):
            entity = EntityDefinition.from_dict(entity_data)
            agent.add_entity_definition(entity)
            
        # Load examples and templates
        agent.domain_examples = data.get("domain_examples", [])
        agent.response_templates = data.get("response_templates", {})
        agent.llm_configuration = data.get("llm_configuration", {})
        agent.state_schema = data.get("state_schema", {})
        
        return agent
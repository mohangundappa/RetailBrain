from abc import ABC, abstractmethod
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set, Type, Union

from langchain.schema import BaseMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate

# Import constants for agent names
from config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT
)

logger = logging.getLogger(__name__)

# Guardrail utility classes
class GuardrailViolation:
    """Represents a violation of agent guardrails"""
    
    def __init__(self, rule_name: str, severity: str, description: str):
        self.rule_name = rule_name
        self.severity = severity  # 'high', 'medium', 'low'
        self.description = description
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "description": self.description,
            "timestamp": self.timestamp
        }

class Guardrails:
    """Implements guardrails for agent responses"""
    
    def __init__(self):
        # Banned phrases that should never be in responses
        self.banned_phrases = [
            "I don't actually work for Staples",
            "I'm just an AI",
            "I'm not a real customer service representative",
            "I'm an AI language model",
            "I'm an assistant",
            "I'm not a human",
            "As an AI",
            "I cannot access"
        ]
        
        # Sensitive information patterns
        self.sensitive_patterns = {
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            "full_password": r'\b(password is|password:|password =)\s*\w+',
        }
        
        # Topic boundaries - topics the agent should not discuss
        self.prohibited_topics = {
            "political": ["election", "democrat", "republican", "politics", "Biden", "Trump", "vote", "political party"],
            "religious": ["religion", "Christianity", "Islam", "Judaism", "Buddhist", "Hindu", "atheist", "God"],
            "adult": ["porn", "sex", "nude", "explicit", "adult content"],
            "illegal": ["hack", "steal", "illegal download", "pirate software", "crack password"],
            "competitors": ["Office Depot", "Amazon", "Walmart", "Target", "Best Buy", "OfficeMax"]
        }
        
        # Service boundaries - what services the agent can and cannot offer
        self.service_boundaries = {
            "allowed": ["track order", "reset password", "account help", "order status", "store locator", "find store", "product information", "product details"],
            "not_allowed": ["refund processing", "cancel subscription", "create new account", "delete account", "file complaint"]
        }
    
    def check_response(self, response_text: str) -> List[GuardrailViolation]:
        """
        Check a response against all guardrails.
        
        Args:
            response_text: The text to check
            
        Returns:
            List of violations, empty if no violations found
        """
        violations = []
        
        # Check for banned phrases
        for phrase in self.banned_phrases:
            if phrase.lower() in response_text.lower():
                violations.append(GuardrailViolation(
                    "banned_phrase", 
                    "high",
                    f"Response contains banned phrase: '{phrase}'"
                ))
        
        # Check for sensitive information
        for pattern_name, pattern in self.sensitive_patterns.items():
            if re.search(pattern, response_text):
                violations.append(GuardrailViolation(
                    "sensitive_information", 
                    "high",
                    f"Response contains sensitive information pattern: {pattern_name}"
                ))
        
        # Check for prohibited topics
        for topic, keywords in self.prohibited_topics.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', response_text.lower()):
                    violations.append(GuardrailViolation(
                        "prohibited_topic", 
                        "medium",
                        f"Response discusses prohibited topic: {topic} (keyword: {keyword})"
                    ))
        
        # Check for service boundary violations
        for service in self.service_boundaries["not_allowed"]:
            if re.search(r'\b' + re.escape(service.lower()) + r'\b', response_text.lower()):
                if service.lower() not in " ".join(self.service_boundaries["allowed"]).lower():
                    violations.append(GuardrailViolation(
                        "service_boundary", 
                        "medium",
                        f"Response offers disallowed service: {service}"
                    ))
        
        return violations
    
    def apply_guardrails(self, response_text: str) -> Tuple[str, List[GuardrailViolation]]:
        """
        Apply guardrails to a response, correcting issues when possible.
        
        Args:
            response_text: The text to check and modify
            
        Returns:
            Tuple of (corrected_text, list_of_violations)
        """
        violations = self.check_response(response_text)
        corrected_text = response_text
        
        # Apply fixes where possible
        for violation in violations:
            if violation.rule_name == "banned_phrase":
                phrase = violation.description.split("'")[1]
                # Replace banned phrases with appropriate Staples representative language
                corrected_text = corrected_text.replace(
                    phrase, 
                    "As a Staples customer service representative"
                )
        
        return corrected_text, violations

class EntityDefinition:
    """
    Define entity requirements for agent data collection.
    """
    
    def __init__(self, 
                 name: str, 
                 required: bool = True, 
                 validation_pattern: Optional[str] = None,
                 error_message: Optional[str] = None,
                 description: Optional[str] = None,
                 examples: Optional[List[str]] = None,
                 alternate_names: Optional[List[str]] = None):
        """
        Initialize an entity definition.
        
        Args:
            name: The name of the entity (e.g., 'order_number', 'zip_code')
            required: Whether this entity is required for the agent to proceed
            validation_pattern: A regex pattern to validate the entity value
            error_message: Custom error message when validation fails
            description: A description of the entity for the user
            examples: Example values for this entity
            alternate_names: Other names this entity might be called in user input
        """
        self.name = name
        self.required = required
        self.validation_pattern = validation_pattern
        self.error_message = error_message or f"Please provide a valid {name.replace('_', ' ')}."
        self.description = description or f"The {name.replace('_', ' ')} for this request."
        self.examples = examples or []
        self.alternate_names = alternate_names or []
        self.collected = False
        self.value = None
        self.attempts = 0
        self.max_attempts = 3  # Maximum attempts to collect this entity

    def is_valid(self, value: str) -> bool:
        """
        Validate the entity value against the pattern if provided.
        
        Args:
            value: The value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not value:
            return False
            
        if not self.validation_pattern:
            return True
            
        return bool(re.match(self.validation_pattern, value))
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entity definition to a dictionary.
        
        Returns:
            A dictionary representation of the entity
        """
        return {
            "name": self.name,
            "required": self.required,
            "description": self.description,
            "examples": self.examples,
            "collected": self.collected,
            "value": self.value,
            "attempts": self.attempts
        }


class EntityCollectionState:
    """
    Track the state of entity collection for an agent conversation.
    """
    
    def __init__(self):
        """Initialize the entity collection state."""
        self.entities: Dict[str, EntityDefinition] = {}
        self.current_entity: Optional[str] = None
        self.is_collecting = False
        self.max_collection_turns = 5  # Maximum conversation turns for entity collection
        self.collection_turns = 0
        self.exit_condition_met = False
        self.exit_reason = None
        
    def add_entity(self, entity: EntityDefinition) -> None:
        """
        Add an entity to collect.
        
        Args:
            entity: The entity definition
        """
        self.entities[entity.name] = entity
        
    def set_value(self, entity_name: str, value: str) -> bool:
        """
        Set a value for an entity and validate it.
        
        Args:
            entity_name: The name of the entity
            value: The value to set
            
        Returns:
            True if the value is valid, False otherwise
        """
        if entity_name not in self.entities:
            return False
            
        entity = self.entities[entity_name]
        
        if entity.is_valid(value):
            entity.value = value
            entity.collected = True
            return True
        else:
            entity.attempts += 1
            
            # If we've exceeded max attempts, mark as exit condition
            if entity.attempts >= entity.max_attempts:
                self.exit_condition_met = True
                self.exit_reason = f"max_attempts_exceeded_for_{entity_name}"
                
            return False
            
    def get_next_missing_entity(self) -> Optional[str]:
        """
        Get the name of the next required entity that hasn't been collected.
        
        Returns:
            The name of the next entity to collect, or None if all required entities are collected
        """
        for name, entity in self.entities.items():
            if entity.required and not entity.collected:
                return name
        return None
        
    def get_missing_entities(self) -> List[str]:
        """
        Get a list of all required entities that haven't been collected.
        
        Returns:
            A list of entity names
        """
        return [name for name, entity in self.entities.items() 
                if entity.required and not entity.collected]
        
    def are_all_required_entities_collected(self) -> bool:
        """
        Check if all required entities have been collected.
        
        Returns:
            True if all required entities are collected, False otherwise
        """
        for entity in self.entities.values():
            if entity.required and not entity.collected:
                return False
        return True
        
    def get_collected_entities(self) -> Dict[str, Any]:
        """
        Get all collected entity values.
        
        Returns:
            A dictionary of entity names and their values
        """
        return {name: entity.value for name, entity in self.entities.items() 
                if entity.collected}
                
    def should_exit_collection(self) -> bool:
        """
        Determine if we should exit the entity collection process.
        
        Returns:
            True if we should exit, False otherwise
        """
        # Exit if all required entities are collected
        if self.are_all_required_entities_collected():
            self.exit_condition_met = True
            self.exit_reason = "all_required_entities_collected"
            return True
            
        # Exit if we've exceeded max collection turns
        if self.collection_turns >= self.max_collection_turns:
            self.exit_condition_met = True
            self.exit_reason = "max_collection_turns_exceeded"
            return True
            
        # Exit if an explicit exit condition has been met
        return self.exit_condition_met
        
    def increment_turn(self) -> None:
        """Increment the collection turn counter."""
        self.collection_turns += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the collection state to a dictionary.
        
        Returns:
            A dictionary representation of the collection state
        """
        return {
            "entities": {name: entity.to_dict() for name, entity in self.entities.items()},
            "current_entity": self.current_entity,
            "is_collecting": self.is_collecting,
            "collection_turns": self.collection_turns,
            "max_collection_turns": self.max_collection_turns,
            "exit_condition_met": self.exit_condition_met,
            "exit_reason": self.exit_reason
        }


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
        self.memory = []  # In-memory cache
        self.conversation_memory = None  # Will be set when processing with a session
        
        # Initialize guardrails
        self.guardrails = Guardrails()
        
        # Initialize entity collection state
        self.entity_collection_state = EntityCollectionState()
        
        # Customer service persona attributes
        self.persona = {
            "role": "Staples Customer Service Representative",
            "style": "helpful, friendly, and professional",
            "tone": "polite and supportive",
            "knowledge_areas": ["Staples products", "services", "policies"],
            "communication_preferences": ["clear", "concise", "solution-oriented"]
        }
        
        # Conversation metrics for continuous improvement
        self.metrics = {
            "total_queries": 0,
            "queries_with_violations": 0,
            "violations_by_type": {}
        }
        
        logger.info(f"Initialized agent: {name} with guardrails and customer service persona")
        
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
        # Access conversation memory if available in context
        if context and 'conversation_memory' in context:
            self.conversation_memory = context['conversation_memory']
        
        # Check for simple greetings (this is implemented in base agent to provide consistent behavior)
        import re
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', r'^howdy\b',
            r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
            r'^how are you\b', r'^what\'s up\b', r'^welcome\b', r'^hola\b'
        ]
        
        # Check if input is just a simple greeting
        is_greeting = any(re.search(pattern, user_input.lower()) for pattern in greeting_patterns)
        
        if is_greeting and len(user_input.split()) <= 3:
            # Return a friendly greeting specific to this agent's domain
            greeting_response = f"Hello! I'm the {self.name}. {self.description} How can I help you today?"
            
            return {
                "success": True,
                "response": greeting_response,
                "agent": self.name,
                "confidence": 1.0,
                "continue_with_same_agent": True
            }
        
        # Continue with implementation in subclasses for non-greeting inputs
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
        # Add to in-memory cache
        self.memory.append(message)
        # Limit memory size
        if len(self.memory) > 10:
            self.memory.pop(0)
            
        # If we have a conversation memory, update the context
        if self.conversation_memory:
            try:
                # Add to persistent memory if role and content are provided
                if 'role' in message and 'content' in message:
                    # Only add to database if we have a valid conversation_id
                    if 'conversation_id' in message and message['conversation_id'] is not None:
                        self.conversation_memory.add_message(
                            role=message['role'],
                            content=message['content'],
                            conversation_id=message['conversation_id']
                        )
                
                # Update agent context with any extracted information
                if 'extracted_info' in message:
                    # Only update context if we have a valid conversation_id
                    if 'conversation_id' in message and message['conversation_id'] is not None:
                        self.conversation_memory.update_context(
                            agent_name=self.name,
                            context_updates=message['extracted_info']
                        )
            except Exception as e:
                logger.error(f"Error adding to conversation memory: {str(e)}")
            
    def get_memory(self) -> List[Dict[str, Any]]:
        """
        Get the agent's memory.
        
        Returns:
            The agent's memory as a list of messages
        """
        # If we have conversation memory, try to load history
        if self.conversation_memory:
            try:
                # Load from database for persistent memory
                history = self.conversation_memory.load_conversation_history()
                if history:
                    return history
            except Exception as e:
                logger.error(f"Error loading conversation memory: {str(e)}")
        
        # Fall back to in-memory if needed
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear the agent's in-memory cache."""
        self.memory = []
        
    def get_system_prompt(self) -> str:
        """
        Get a system prompt with conversation context and customer service persona.
        
        Returns:
            A system prompt incorporating conversation history, context, and persona
        """
        # Start with persona-based system prompt
        persona_prompt = self._get_persona_prompt()
        
        if self.conversation_memory:
            try:
                # Add conversation context to the persona prompt
                memory_prompt = self.conversation_memory.get_system_prompt(self.name)
                return f"{persona_prompt}\n\n{memory_prompt}"
            except Exception as e:
                logger.error(f"Error getting system prompt from memory: {str(e)}")
                return persona_prompt
        
        # Default system prompt with persona if no conversation memory
        return persona_prompt
    
    def _get_persona_prompt(self) -> str:
        """
        Generate a system prompt based on the agent's customer service persona.
        
        Returns:
            A system prompt with persona instructions
        """
        prompt = f"""You are a {self.persona['role']} specializing in {self.name} at Staples. {self.description}

IMPORTANT GUIDELINES:
- Always maintain a {self.persona['style']} demeanor with customers
- Use a {self.persona['tone']} tone in all responses
- Your expertise includes: {', '.join(self.persona['knowledge_areas'])}
- Your communications should be: {', '.join(self.persona['communication_preferences'])}
- Never break character - you are a real Staples employee helping customers
- Do not mention AI, language models, or artificial intelligence
- Focus on delivering outstanding customer service and resolving issues efficiently
- When you don't know specific details, offer to help the customer connect with the right department
- Speak as a Staples representative using "we" when referring to Staples
- Always provide accurate information about Staples policies and procedures
- Protect customer privacy and never ask for or retain sensitive information

Remember: Your goal is to provide excellent customer service while representing Staples in a professional manner.
"""
        return prompt
    
    def apply_response_guardrails(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply guardrails to a response, ensuring it adheres to guidelines.
        
        Args:
            response_text: The raw response text to check
            
        Returns:
            Tuple of (corrected_response, list_of_violations_as_dicts)
        """
        # Track metrics
        self.metrics["total_queries"] += 1
        
        # Apply guardrails
        corrected_text, violations = self.guardrails.apply_guardrails(response_text)
        
        # Update violation metrics
        if violations:
            self.metrics["queries_with_violations"] += 1
            for violation in violations:
                rule_name = violation.rule_name
                if rule_name not in self.metrics["violations_by_type"]:
                    self.metrics["violations_by_type"][rule_name] = 0
                self.metrics["violations_by_type"][rule_name] += 1
            
            # Log violations
            logger.warning(f"Guardrail violations in {self.name} agent response: {len(violations)}")
            for violation in violations:
                logger.warning(f"  - {violation.rule_name} ({violation.severity}): {violation.description}")
        
        # Convert violations to dicts for serialization
        violation_dicts = [v.to_dict() for v in violations]
        
        return corrected_text, violation_dicts
    
    def setup_entity_collection(self, entity_definitions: List[EntityDefinition]) -> None:
        """
        Set up entity collection with the provided entity definitions.
        
        Args:
            entity_definitions: List of entity definitions to collect
        """
        # Reset entity collection state
        self.entity_collection_state = EntityCollectionState()
        
        # Add entities to collection state
        for entity in entity_definitions:
            self.entity_collection_state.add_entity(entity)
            
        # Mark entity collection as active
        self.entity_collection_state.is_collecting = True
        
        # Set the current entity to the first required entity
        self.entity_collection_state.current_entity = self.entity_collection_state.get_next_missing_entity()
        
    def extract_entities_from_input(self, user_input: str) -> Dict[str, str]:
        """
        Extract entity values from user input using string matching and patterns.
        This is a simple extraction mechanism, for complex extraction use LLM-based extraction.
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dictionary of entity names and their extracted values
        """
        extracted_values = {}
        
        # Simple pattern-based extraction for common entities
        # Order number pattern (alphanumeric with optional hyphen)
        order_number_match = re.search(r'\b([A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,})\b', user_input)
        if order_number_match and 'order_number' in self.entity_collection_state.entities:
            extracted_values['order_number'] = order_number_match.group(1)
            
        # Zip code pattern (5 digits, optionally followed by hyphen and 4 more digits)
        zip_code_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', user_input)
        if zip_code_match and 'zip_code' in self.entity_collection_state.entities:
            extracted_values['zip_code'] = zip_code_match.group(1)
            
        # Email pattern
        email_match = re.search(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', user_input)
        if email_match and 'email' in self.entity_collection_state.entities:
            extracted_values['email'] = email_match.group(1)
            
        # For other entity types, check for <entity_name>: <value> pattern in user input
        for entity_name in self.entity_collection_state.entities:
            if entity_name not in extracted_values:
                # Look for explicit entity mentions like "order number: ABC123"
                pattern = fr'\b{entity_name.replace("_", " ")}:?\s*([A-Za-z0-9@.\-_+]+)\b'
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    extracted_values[entity_name] = match.group(1)
                    
        return extracted_values
    
    async def process_entity_collection(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Process entity collection based on user input.
        
        Args:
            user_input: The user's input text
            context: Additional context information
            
        Returns:
            Tuple of (collection_complete, follow_up_prompt)
            - collection_complete: True if entity collection is complete, False otherwise
            - follow_up_prompt: A follow-up prompt for the user if collection is not complete
        """
        # If we're not in collection mode, return immediately
        if not self.entity_collection_state.is_collecting:
            return True, None
            
        # Increment the collection turn counter
        self.entity_collection_state.increment_turn()
        
        # Extract entities from user input
        extracted_entities = self.extract_entities_from_input(user_input)
        
        # Update entity values
        for entity_name, value in extracted_entities.items():
            self.entity_collection_state.set_value(entity_name, value)
            
        # Check if we should exit collection
        if self.entity_collection_state.should_exit_collection():
            logger.info(f"Entity collection complete for {self.name}. Reason: {self.entity_collection_state.exit_reason}")
            self.entity_collection_state.is_collecting = False
            
            # If exit due to max attempts, generate the appropriate response
            if self.entity_collection_state.exit_reason and "max_attempts_exceeded" in self.entity_collection_state.exit_reason:
                entity_name = self.entity_collection_state.exit_reason.split("_for_")[1]
                entity = self.entity_collection_state.entities.get(entity_name)
                
                if entity:
                    transfer_message = f"I'm having trouble collecting the {entity_name.replace('_', ' ')}. Let me transfer you to a customer service representative who can help you further."
                    return True, transfer_message
                    
            return True, None
            
        # Get the next entity to collect
        next_entity_name = self.entity_collection_state.get_next_missing_entity()
        
        if not next_entity_name:
            # All required entities have been collected
            self.entity_collection_state.is_collecting = False
            self.entity_collection_state.exit_condition_met = True
            self.entity_collection_state.exit_reason = "all_required_entities_collected"
            return True, None
            
        # Update the current entity
        self.entity_collection_state.current_entity = next_entity_name
        current_entity = self.entity_collection_state.entities[next_entity_name]
        
        # Use LLM to generate a natural follow-up prompt for missing entities
        return await self._generate_entity_collection_prompt(user_input, current_entity)
        
    async def _generate_entity_collection_prompt(self, user_input: str, current_entity: EntityDefinition) -> Tuple[bool, str]:
        """
        Use the LLM to generate a natural prompt for collecting missing entities.
        
        Args:
            user_input: The user's input text
            current_entity: The current entity being collected
            
        Returns:
            Tuple of (collection_complete, follow_up_prompt)
        """
        # Prepare context for the LLM
        missing_entities = self.entity_collection_state.get_missing_entities()
        collected_entities = self.entity_collection_state.get_collected_entities()
        
        # Create structured entity data for the LLM
        entity_data = []
        for entity_name in missing_entities:
            # Get the entity object from the dictionary
            entity = self.entity_collection_state.entities.get(entity_name)
            if entity:
                entity_info = {
                    "name": entity.name,
                    "description": entity.description,
                    "examples": entity.examples,
                    "validation_failed": entity.attempts > 0,
                    "error_message": entity.error_message if entity.attempts > 0 else None
                }
                entity_data.append(entity_info)
        
        # Create the prompt template
        template = """
        You are a customer service representative for Staples, helping a customer with their request.
        
        Customer's latest message: "{user_input}"
        
        You need to collect the following information from the customer:
        {entity_requirements}
        
        This is the context of already collected information:
        {collected_info}
        
        Generate a polite, conversational follow-up message asking for ONLY the missing information.
        The message should:
        1. Be friendly and conversational in tone, like a helpful human service representative
        2. Ask for all missing information at once if appropriate
        3. Include examples if available
        4. If validation has failed for an entity, politely mention the error and ask again
        5. Make the customer feel like they're talking to a helpful person, not a form-filling robot
        6. Be concise and to the point
        
        Your response:
        """
        
        # Format entity requirements for prompt
        entity_reqs = ""
        for entity in entity_data:
            entity_reqs += f"- {entity['name'].replace('_', ' ')}: {entity['description']}"
            if entity['examples']:
                entity_reqs += f" (example: {entity['examples'][0]})"
            if entity['validation_failed']:
                entity_reqs += f" [Validation error: {entity['error_message']}]"
            entity_reqs += "\n"
        
        # Format collected information for prompt
        collected_info = ""
        if collected_entities:
            for name, value in collected_entities.items():
                collected_info += f"- {name.replace('_', ' ')}: {value}\n"
        else:
            collected_info = "- No information collected yet.\n"
        
        # Create an LLM chain for generating the prompt
        prompt = ChatPromptTemplate.from_template(template)
        prompt_chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Generate the follow-up prompt
        try:
            response = await prompt_chain.arun(
                user_input=user_input,
                entity_requirements=entity_reqs,
                collected_info=collected_info
            )
            
            # Clean up any excess whitespace or newlines
            follow_up = response.strip()
            
            return False, follow_up
        except Exception as e:
            logger.error(f"Error generating entity collection prompt: {str(e)}")
            
            # Fall back to a basic prompt if LLM fails
            follow_up = f"Could you please provide your {current_entity.name.replace('_', ' ')}?"
            if current_entity.examples:
                example = current_entity.examples[0]
                follow_up += f" For example: {example}"
                
            return False, follow_up
        
    def get_collected_entity_values(self) -> Dict[str, Any]:
        """
        Get all collected entity values.
        
        Returns:
            Dictionary of entity names and their values
        """
        return self.entity_collection_state.get_collected_entities()
        
    def reset_entity_collection(self) -> None:
        """Reset the entity collection state."""
        self.entity_collection_state = EntityCollectionState()
        
    @classmethod
    def create_agent(cls, agent_type: str, llm, **kwargs):
        """
        Factory method to create a standardized agent with proper naming.
        
        Args:
            agent_type: The type of agent to create (package_tracking, store_locator, etc.)
            llm: The language model to use
            **kwargs: Additional arguments to pass to the agent constructor
            
        Returns:
            An instance of the requested agent type
        """
        # Import agent types here to avoid circular imports
        from agents.package_tracking import PackageTrackingAgent
        from agents.store_locator import StoreLocatorAgent
        from agents.reset_password import ResetPasswordAgent
        from agents.product_info import ProductInfoAgent
        
        # Map agent types to their proper class
        agent_map = {
            "package_tracking": PackageTrackingAgent,
            "store_locator": StoreLocatorAgent,
            "reset_password": ResetPasswordAgent,
            "product_info": ProductInfoAgent
        }
        
        if agent_type not in agent_map:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        agent_class = agent_map[agent_type]
        
        # Create and return the agent - agent already has the standardized name in its constructor
        return agent_class(llm=llm)

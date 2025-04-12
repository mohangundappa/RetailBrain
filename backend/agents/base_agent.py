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

# Import tool service for tool calling
try:
    from backend.brain.core_services.tool_service import tool_service
except ImportError:
    # This allows the module to be imported even if tool_service is not available
    # We'll handle this case in the BaseAgent class
    tool_service = None

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
        
        # Out of scope topics - topics that should be redirected to human agents
        self.out_of_scope_topics = {
            "hiring": ["job application", "hiring", "employment", "job opening", "career", "work at staples", "apply for job", "hiring process", "job interview", "resume"],
            "hr_policies": ["sick leave", "vacation policy", "employee benefits", "hr policies", "work hours", "employee handbook", "company policy", "maternity leave", "paternity leave"],
            "legal": ["lawsuit", "legal action", "settlement", "terms of service", "privacy policy", "gdpr", "ccpa", "data rights", "legal department"],
            "executive": ["ceo", "cfo", "executive team", "board of directors", "leadership team", "company earnings", "quarterly results", "annual report", "investor relations"],
            "unrelated": ["non-staples", "not related to staples", "other companies", "personal advice", "personal questions", "personal issues", "private matters"],
            "investments": ["stock price", "investment advice", "market share", "shareholders", "dividend", "investor", "financial projection", "market cap", "ipo"]
        }
    
    def is_out_of_scope(self, query_text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a user query is out of scope for the agent system.
        
        Args:
            query_text: The user's query text
            
        Returns:
            Tuple of (is_out_of_scope, topic_category)
            - is_out_of_scope: True if the query is out of scope
            - topic_category: The category of out of scope topic, or None if in scope
        """
        # Convert to lowercase for matching
        query_lower = query_text.lower()
        
        # Check each out of scope topic
        for topic, keywords in self.out_of_scope_topics.items():
            # Check for exact keyword matches with word boundaries
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', query_lower):
                    return True, topic
        
        # If no matches found, it's in scope
        return False, None
    
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
        self.value: Optional[str] = None
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
        self.entity_definitions: List[EntityDefinition] = []  # Store a list of entity definitions for reference
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
        self.entity_definitions.append(entity)  # Add to the list of entity definitions
        
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
            # Cast to Optional[str] to satisfy type checker
            entity.value = value  # type: ignore
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
        
    async def call_tool(self, tool_name: str, **tool_args) -> Dict[str, Any]:
        """
        Call a tool using the tool service.
        
        Args:
            tool_name: Name of the tool to call
            **tool_args: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        try:
            # Check if tool service is available
            if tool_service is None:
                return {
                    "status": "error",
                    "error": "Tool service is not initialized"
                }
            
            # Call the tool via the tool service
            return await tool_service.call_tool(tool_name, **tool_args)
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return {
                "status": "error",
                "error": f"Error calling tool {tool_name}: {str(e)}"
            }
            
    async def detect_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect tool calls in a text response from an LLM.
        This handles two formats:
        1. JSON structured tool calls with "tool_name" and "tool_args" keys
        2. Natural language requests that match known tool patterns
        
        Args:
            text: The text to detect tool calls in
            
        Returns:
            List of detected tool calls, each containing tool_name and tool_args
        """
        tool_calls = []
        
        # Try to detect JSON-structured tool calls
        try:
            # Look for JSON blocks in the text that might contain tool calls
            json_pattern = r'\{[\s\S]*?"tool_name"[\s\S]*?\}'
            json_matches = re.findall(json_pattern, text)
            
            for json_str in json_matches:
                try:
                    tool_call = json.loads(json_str)
                    if "tool_name" in tool_call and "tool_args" in tool_call:
                        tool_calls.append({
                            "tool_name": tool_call["tool_name"],
                            "tool_args": tool_call["tool_args"]
                        })
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Error parsing JSON tool calls: {str(e)}")
        
        # If no structured tool calls found, check for natural language tool patterns
        if not tool_calls and tool_service is not None:
            # Get all available tools and their schemas
            available_tools = tool_service.list_tools()
            
            # Create pattern matching for each tool
            for tool in available_tools:
                tool_name = tool["name"]
                
                # Create patterns based on tool name and parameters
                # Example: "find stores near <location>" for store_locator tool
                param_patterns = {}
                for param_name, param_info in tool.get("parameters", {}).items():
                    # Create pattern that looks for parameter values after certain keywords
                    if param_info.get("description"):
                        desc = param_info["description"].lower()
                        param_patterns[param_name] = [
                            fr'{param_name}\s*(?:is|=|:)\s*(["\']?)([^"\']+)\1',
                            fr'(?:{desc.split()[0]}|{param_name})[:\s]+(["\']?)([^"\']+)\1'
                        ]
                
                # Look for mentions of the tool function in text
                tool_name_pattern = fr'\b{tool_name.replace("_", " ")}\b'
                if re.search(tool_name_pattern, text.lower()):
                    # Tool name found, extract parameters
                    tool_args = {}
                    for param_name, patterns in param_patterns.items():
                        for pattern in patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                # Group 2 contains the actual value if quoted, otherwise it's in group 1
                                tool_args[param_name] = match.group(2) if len(match.groups()) > 1 else match.group(1)
                                break
                    
                    if tool_args:
                        tool_calls.append({
                            "tool_name": tool_name,
                            "tool_args": tool_args
                        })
        
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
                updated_text = updated_text.replace(json_str, f"Tool Result: {result_str}")
            
        return tool_results, updated_text
        
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
        
        # Check for conversation closings (thanks, etc.)
        closing_patterns = [
            r'^thanks?\b', r'^thank you\b', r'^thx\b', r'^ty\b', 
            r'^got it\b', r'^understood\b', r'^appreciate\b',
            r'^great\b', r'^awesome\b', r'^perfect\b', r'^excellent\b',
            r'^ok\b', r'^okay\b', r'^sure\b', r'^sounds good\b'
        ]
        
        # Check if the input indicates the user is closing the conversation with a thank you or acknowledgment
        is_closing = any(re.search(pattern, user_input.lower()) for pattern in closing_patterns)
        
        # Also check for very short responses which might indicate closure
        words = user_input.strip().split()
        if len(words) <= 3 and any(word.lower() in ['thanks', 'thank', 'ok', 'okay', 'good', 'great'] for word in words):
            is_closing = True
        
        # If the user is just saying thank you or acknowledging, provide a closing response
        if is_closing and len(user_input.split()) <= 5:
            # Return a concise closing response
            closing_responses = [
                "Glad I could help! Feel free to reach out if you need anything else.",
                "You're welcome! Is there anything else I can assist with?",
                "Happy to help! Have a great day!",
                "Anytime! Let me know if you need anything else from Staples."
            ]
            import random
            closing_response = random.choice(closing_responses)
            
            return {
                "success": True,
                "response": closing_response,
                "agent": self.name,
                "confidence": 1.0,
                "is_closing": True,
                "continue_with_same_agent": False  # Allow switching after a closing
            }
        
        if is_greeting and len(user_input.split()) <= 3:
            # Return a concise greeting specific to this agent's domain
            greeting_response = f"Hi! How can I help with {self.name.replace(' Agent', '')}?"
            
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
        # Default implementation uses a simple keyword matcher
        # Subclasses should override this with more sophisticated logic
        keywords = self.get_agent_keywords()
        if not keywords:
            return 0.5  # Default medium confidence
            
        # Count the number of keywords present in the input
        user_input_lower = user_input.lower()
        matched_keywords = sum(1 for keyword in keywords if keyword.lower() in user_input_lower)
        
        # Calculate confidence based on keyword matches
        if not matched_keywords:
            return 0.1  # Low base confidence if no keywords match
            
        # Scale confidence based on the ratio of matched keywords
        # But ensure even a single match gives reasonable confidence
        confidence = min(0.3 + (matched_keywords / len(keywords)) * 0.7, 0.95)
        
        return confidence
    
    def get_agent_keywords(self) -> List[str]:
        """
        Get a list of keywords that indicate this agent might be able to handle a request.
        
        Returns:
            A list of keywords
        """
        # Default implementation, should be overridden by subclasses
        return []
        
    async def handle_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle a user message and generate a response.
        
        This is the main entry point for processing messages through the agent.
        It calls the process method and extracts the text response.
        
        Args:
            message: The user's message
            context: Additional context information
            
        Returns:
            The agent's response as a string
        """
        try:
            # Process the message with the agent's specialized logic
            result = await self.process(message, context)
            
            # Extract the response text
            if isinstance(result, dict) and "response" in result:
                return result["response"]
            elif isinstance(result, str):
                return result
            else:
                return f"I processed your request about '{message}', but I'm not sure how to respond."
                
        except Exception as e:
            logger.error(f"Error handling message in {self.name}: {str(e)}", exc_info=True)
            return "I'm sorry, but I encountered an error while processing your request. Please try again or rephrase your question."
    
    def _create_chain(self, template: str, input_variables: List[str]) -> RunnableSequence:
        """
        Create a simple LLM chain with the given template.
        
        Args:
            template: The prompt template
            input_variables: The variables required by the template
            
        Returns:
            A RunnableSequence that can be invoked
        """
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
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
        
        # Enhanced pattern-based extraction for common entities
        
        # Order number patterns - Match various formats
        if 'order_number' in self.entity_collection_state.entities:
            # Try to find order number in multiple formats
            # First, check for explicit mentions with label
            order_pattern_explicit = r'(?:order(?:\s+number)?|confirmation(?:\s+number)?|order\s+id)[\s:]*([A-Za-z0-9]{2,}(?:-[A-Za-z0-9]{2,})?)'
            order_match_explicit = re.search(order_pattern_explicit, user_input, re.IGNORECASE)
            
            # Then try common formats without labels
            order_pattern_standard = r'\b([A-Za-z]{2}\d{6,})\b'  # e.g., OD1234567, ST7654321
            order_pattern_hyphen = r'\b([A-Za-z]{2,3}-\d{6,})\b'  # e.g., STB-123456
            
            if order_match_explicit:
                extracted_values['order_number'] = order_match_explicit.group(1).strip()
            else:
                # Try standard pattern
                order_match_std = re.search(order_pattern_standard, user_input)
                if order_match_std:
                    extracted_values['order_number'] = order_match_std.group(1)
                else:
                    # Try hyphenated pattern
                    order_match_hyphen = re.search(order_pattern_hyphen, user_input)
                    if order_match_hyphen:
                        extracted_values['order_number'] = order_match_hyphen.group(1)
                    else:
                        # Last resort, try a more general alphanumeric pattern when near "order" keywords
                        general_order_pattern = r'(?:order|number|confirmation).*?\b([A-Za-z0-9]{2,}[-]?[A-Za-z0-9]{2,})\b'
                        general_match = re.search(general_order_pattern, user_input, re.IGNORECASE)
                        if general_match:
                            extracted_values['order_number'] = general_match.group(1)
            
        # Zip code patterns - More comprehensive
        if 'zip_code' in self.entity_collection_state.entities:
            # First check for explicit mentions with label
            zip_pattern_explicit = r'(?:zip|postal)(?:\s+code)?[\s:]*(\d{5}(?:-\d{4})?)'
            zip_match_explicit = re.search(zip_pattern_explicit, user_input, re.IGNORECASE)
            
            # Standard US zip code pattern
            zip_pattern_standard = r'\b(\d{5}(?:-\d{4})?)\b'
            
            if zip_match_explicit:
                extracted_values['zip_code'] = zip_match_explicit.group(1).strip()
            else:
                # Try standard pattern
                zip_match_std = re.search(zip_pattern_standard, user_input)
                if zip_match_std:
                    extracted_values['zip_code'] = zip_match_std.group(1)
        
        # Location patterns - For Store Locator Agent
        if 'location' in self.entity_collection_state.entities:
            # Try to extract zip code pattern directly (5-digit US zip)
            zip_pattern = r'\b(\d{5})\b'
            zip_matches = re.findall(zip_pattern, user_input)
            if zip_matches:
                extracted_values['location'] = zip_matches[0]
                logger.info(f"Extracted zip code as location: {extracted_values['location']}")
            else:
                # Try to extract city, state pattern (e.g., "Natick, MA")
                city_state_pattern = r'\b([A-Za-z\s]+),\s*([A-Z]{2})\b'
                city_state_matches = re.findall(city_state_pattern, user_input)
                if city_state_matches:
                    city, state = city_state_matches[0]
                    extracted_values['location'] = f"{city.strip()}, {state.strip()}"
                    logger.info(f"Extracted city, state as location: {extracted_values['location']}")
                else:
                    # Check for common city names
                    common_cities = {
                        "natick": "Natick, MA",
                        "boston": "Boston, MA",
                        "cambridge": "Cambridge, MA",
                        "somerville": "Somerville, MA",
                        "framingham": "Framingham, MA",
                        "brookline": "Brookline, MA",
                        "newton": "Newton, MA",
                        "wellesley": "Wellesley, MA"
                    }
                    
                    for city_name, full_location in common_cities.items():
                        if city_name.lower() in user_input.lower():
                            extracted_values['location'] = full_location
                            logger.info(f"Matched common city name: {extracted_values['location']}")
                            break
            
        # Email pattern - Improved
        if 'email' in self.entity_collection_state.entities:
            email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'
            email_match = re.search(email_pattern, user_input)
            if email_match:
                extracted_values['email'] = email_match.group(1)
            
        # Phone number pattern
        if 'phone_number' in self.entity_collection_state.entities:
            phone_pattern = r'\b(?:\+?1[-\s]?)?(?:\(?([0-9]{3})\)?[-\s]?)?([0-9]{3})[-\s]?([0-9]{4})\b'
            phone_match = re.search(phone_pattern, user_input)
            if phone_match:
                # Format the phone number consistently
                area_code = phone_match.group(1) or ""
                prefix = phone_match.group(2) or ""
                line = phone_match.group(3) or ""
                if area_code and prefix and line:
                    extracted_values['phone_number'] = f"{area_code}-{prefix}-{line}"
                elif prefix and line:
                    extracted_values['phone_number'] = f"{prefix}-{line}"
            
        # For other entity types, check for <entity_name>: <value> pattern in user input
        for entity_name in self.entity_collection_state.entities:
            if entity_name not in extracted_values:
                # Look for explicit entity mentions like "order number: ABC123"
                pattern = fr'\b{entity_name.replace("_", " ")}:?\s*([^\s.,;!?]+(?:\s+[^\s.,;!?]+)*)'
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    extracted_values[entity_name] = match.group(1).strip()
                
                # Also check alt_names if defined for the entity
                entity_def = next((e for e in self.entity_collection_state.entity_definitions if e.name == entity_name), None)
                if entity_def and entity_def.alternate_names:
                    for alt_name in entity_def.alternate_names:
                        if entity_name not in extracted_values:
                            alt_pattern = fr'\b{alt_name}:?\s*([^\s.,;!?]+(?:\s+[^\s.,;!?]+)*)'
                            alt_match = re.search(alt_pattern, user_input, re.IGNORECASE)
                            if alt_match:
                                extracted_values[entity_name] = alt_match.group(1).strip()
                    
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
        logger.info(f"Extracted entities from input: {extracted_entities}")
        
        # Update entity values
        for entity_name, value in extracted_entities.items():
            self.entity_collection_state.set_value(entity_name, value)
        
        # Check if all required entities are collected after extraction
        if self.entity_collection_state.are_all_required_entities_collected():
            logger.info(f"All required entities collected for {self.name}. Proceeding.")
            self.entity_collection_state.is_collecting = False
            self.entity_collection_state.exit_condition_met = True
            self.entity_collection_state.exit_reason = "all_required_entities_collected"
            return True, None
            
        # Check if we should exit collection due to other reasons
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
        
        Generate an EXTREMELY BRIEF message asking for ONLY the missing information.
        IMPORTANT RULES:
        1. ONE SENTENCE ONLY - just request the specific field needed
        2. If example needed, include in a second sentence ONLY
        3. NO greeting, pleasantries, or explanations
        4. MAXIMUM 15 WORDS TOTAL
        5. Be direct - "Please provide [exact field name]."
        
        Your response should be in this style: "Please provide your ZIP code. For example, 90210."
        
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
        
        # Create a runnable sequence for generating the prompt
        prompt = ChatPromptTemplate.from_template(template)
        prompt_chain = prompt | self.llm | StrOutputParser()
        
        # Generate the follow-up prompt
        try:
            response = await prompt_chain.ainvoke({
                "user_input": user_input,
                "entity_requirements": entity_reqs,
                "collected_info": collected_info
            })
            
            # Clean up any excess whitespace or newlines
            follow_up = response.strip()
            
            return False, follow_up
        except Exception as e:
            logger.error(f"Error generating entity collection prompt: {str(e)}")
            
            # Fall back to a basic prompt if LLM fails - make it extremely concise
            follow_up = f"Please provide your {current_entity.name.replace('_', ' ')}."
            if current_entity.examples:
                example = current_entity.examples[0]
                follow_up += f" Example: {example}"
                
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
        from backend.agents.package_tracking import PackageTrackingAgent
        from backend.agents.store_locator import StoreLocatorAgent
        from backend.agents.reset_password import ResetPasswordAgent
        from backend.agents.product_info import ProductInfoAgent
        from backend.agents.returns_processing import ReturnsProcessingAgent
        
        # Map agent types to their proper class
        agent_map = {
            "package_tracking": PackageTrackingAgent,
            "store_locator": StoreLocatorAgent,
            "reset_password": ResetPasswordAgent,
            "product_info": ProductInfoAgent,
            "returns_processing": ReturnsProcessingAgent
        }
        
        if agent_type not in agent_map:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        agent_class = agent_map[agent_type]
        
        # Create and return the agent - agent already has the standardized name in its constructor
        return agent_class(llm=llm)

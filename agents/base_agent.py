from abc import ABC, abstractmethod
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from langchain.schema import BaseMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate

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
        
        # Continue with implementation in subclasses
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
        if self.conversation_memory and 'conversation_id' in message:
            try:
                # Add to persistent memory if role and content are provided
                if 'role' in message and 'content' in message:
                    self.conversation_memory.add_message(
                        role=message['role'],
                        content=message['content'],
                        conversation_id=message['conversation_id']
                    )
                
                # Update agent context with any extracted information
                if 'extracted_info' in message:
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

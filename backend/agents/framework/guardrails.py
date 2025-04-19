"""
Guardrails utilities for agent responses.

This module provides classes to implement guardrails for agent responses,
detecting and correcting violations of guidelines to ensure appropriate
agent behavior.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Logging setup
import logging
logger = logging.getLogger(__name__)

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
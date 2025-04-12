"""
Semantic utility functions for Staples Brain.

This module provides utilities for semantic analysis and similarity
calculations to improve agent selection and conversation flow.
"""

import logging
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union

# Import embeddings library conditionally
try:
    from langchain_openai import OpenAIEmbeddings
    has_openai = True
except ImportError:
    has_openai = False

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    """
    Utility class for semantic analysis of text.
    
    Provides methods for calculating semantic similarity between texts
    and detecting specific conversation patterns.
    """
    
    def __init__(self):
        """Initialize the semantic analyzer."""
        self.embeddings = None
        self._initialize_embeddings()
        
    def _initialize_embeddings(self):
        """Initialize the embeddings model."""
        if has_openai and os.environ.get("OPENAI_API_KEY"):
            try:
                self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                logger.info("Initialized OpenAI embeddings for semantic analysis")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI embeddings: {str(e)}")
        else:
            logger.warning("OpenAI embeddings unavailable, semantic similarity will use fallback method")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding vector for a text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector or None if embeddings not available
        """
        if not text:
            return None
            
        if self.embeddings:
            try:
                return self.embeddings.embed_query(text)
            except Exception as e:
                logger.warning(f"Error getting embedding: {str(e)}")
                return None
        else:
            # Fallback to simple bag of words representation
            return self._simple_text_representation(text)
    
    def _simple_text_representation(self, text: str) -> List[float]:
        """
        Create a simple numerical representation of text when embeddings are not available.
        This is a fallback method that uses character frequency.
        
        Args:
            text: Input text
            
        Returns:
            Simple vector representation of the text
        """
        # Count character frequencies and normalize
        char_freq = {}
        for char in text.lower():
            if char.isalnum():
                char_freq[char] = char_freq.get(char, 0) + 1
                
        # Create a simple fixed-length vector (26 letters + 10 digits)
        vector = [0] * 36
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz0123456789"):
            if i < len(vector):
                vector[i] = char_freq.get(char, 0) / max(len(text), 1)
                
        return vector
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0
            
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
            
        # Calculate cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        cosine_similarity = dot_product / (norm1 * norm2)
        return float(max(0.0, min(1.0, cosine_similarity)))
    
    def calculate_relevance_to_history(self, query: str, history: List[Dict[str, str]]) -> float:
        """
        Calculate relevance of a query to conversation history.
        
        Args:
            query: Current user query
            history: List of previous messages as dictionaries with 'content' key
            
        Returns:
            Relevance score between 0 and 1
        """
        if not query or not history:
            return 0.0
            
        # Extract text content from history
        history_texts = [msg.get('content', '') for msg in history if msg.get('role') == 'user']
        
        if not history_texts:
            return 0.0
            
        # Calculate similarity with each history item
        similarities = [self.calculate_similarity(query, text) for text in history_texts]
        
        # Return max similarity as the relevance score
        return max(similarities) if similarities else 0.0
    
    def detect_greeting(self, text: str) -> float:
        """
        Detect if text contains a greeting.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score that text is a greeting (0-1)
        """
        text = text.lower()
        greeting_phrases = [
            "hello", "hi ", "hey", "morning", "afternoon", "evening", 
            "good day", "greetings", "wassup", "what's up", "howdy"
        ]
        
        # Check for exact greeting matches
        for phrase in greeting_phrases:
            if phrase in text:
                # Higher confidence for short greetings
                if len(text) < 20:
                    return 0.95
                else:
                    return 0.8
                    
        # Calculate similarity with common greetings
        common_greetings = [
            "Hello there",
            "Hi, how are you?",
            "Hey, how's it going?",
            "Good morning",
            "Good afternoon"
        ]
        
        similarities = [self.calculate_similarity(text, greeting) for greeting in common_greetings]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_conversation_end(self, text: str) -> float:
        """
        Detect if text indicates the end of a conversation.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score that text indicates conversation end (0-1)
        """
        text = text.lower()
        end_phrases = [
            "goodbye", "bye", "see you", "farewell", "talk to you later",
            "have a good day", "have a nice day", "thanks for your help",
            "thank you for your assistance", "that's all", "that will be all"
        ]
        
        # Check for exact end phrase matches
        for phrase in end_phrases:
            if phrase in text:
                return 0.9
                
        # Calculate similarity with common end phrases
        common_ends = [
            "Goodbye for now",
            "Thank you for your help",
            "That's all I needed",
            "I'm done now"
        ]
        
        similarities = [self.calculate_similarity(text, end) for end in common_ends]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_human_transfer_request(self, text: str) -> float:
        """
        Detect if text contains a request to transfer to a human agent.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score that text is requesting human transfer (0-1)
        """
        text = text.lower()
        human_phrases = [
            "speak to a human", "talk to a person", "talk to a representative",
            "speak with an agent", "transfer to agent", "transfer to a human",
            "real person", "human agent", "customer service", "customer support",
            "speak to a manager", "talk to a supervisor", "talk to someone"
        ]
        
        # Check for exact human transfer phrase matches
        for phrase in human_phrases:
            if phrase in text:
                return 0.9
                
        # Calculate similarity with common human transfer requests
        common_requests = [
            "I want to speak to a human agent",
            "Can I talk to a real person?",
            "Transfer me to customer service please"
        ]
        
        similarities = [self.calculate_similarity(text, request) for request in common_requests]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_negative_feedback(self, text: str) -> float:
        """
        Detect negative feedback in text.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score that text contains negative feedback (0-1)
        """
        text = text.lower()
        negative_phrases = [
            "not helpful", "didn't help", "doesn't help", "useless",
            "wrong answer", "incorrect", "not what I asked", "not right",
            "doesn't understand", "didn't understand", "confused",
            "not working", "frustrating", "waste of time", "not relevant"
        ]
        
        # Check for exact negative feedback phrase matches
        for phrase in negative_phrases:
            if phrase in text:
                return 0.85
                
        # Calculate similarity with common negative feedback
        common_negative = [
            "This is not helpful at all",
            "You don't understand what I'm asking",
            "You're giving me the wrong information",
            "This is very frustrating"
        ]
        
        similarities = [self.calculate_similarity(text, neg) for neg in common_negative]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_conversation_interruption(self, 
                                        previous_topic: str, 
                                        current_query: str) -> Tuple[bool, float]:
        """
        Detect if current query represents a conversation topic interruption.
        
        Args:
            previous_topic: Previous conversation topic or summary
            current_query: Current user query
            
        Returns:
            Tuple of (is_interruption, confidence)
        """
        if not previous_topic or not current_query:
            return False, 0.0
            
        # Calculate similarity between previous topic and current query
        similarity = self.calculate_similarity(previous_topic, current_query)
        
        # Low similarity indicates potential topic change/interruption
        is_interruption = similarity < 0.3
        confidence = 1.0 - similarity if is_interruption else 0.0
        
        return is_interruption, confidence


# Create a singleton instance
semantic_analyzer = SemanticAnalyzer()
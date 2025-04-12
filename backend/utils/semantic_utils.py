"""
Semantic analysis utilities for Staples Brain.

This module provides utilities for semantic analysis of text, including
similarity calculations, embeddings, and various detection methods for
special conversation scenarios.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from numpy.linalg import norm

from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    """
    Utility class for semantic analysis, including text similarity calculations,
    embeddings, and special case detection.
    """
    
    def __init__(self):
        """Initialize the semantic analyzer with available embedding backends."""
        self.embedding_model = None
        
        # Check if OpenAI API key is available for embeddings
        if os.environ.get("OPENAI_API_KEY"):
            try:
                self.embedding_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    chunk_size=1000
                )
                logger.info("Initialized OpenAI embeddings for semantic analysis")
            except ImportError:
                logger.warning("OpenAI package not available, falling back to simpler text analysis")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI embeddings: {str(e)}")
                
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text using the configured backend.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Embedding vector (list of floats)
        """
        if not text:
            # Return zero vector for empty text
            return [0.0] * 1536  # Default dimension for OpenAI text-embedding-3-small
            
        if self.embedding_model:
            try:
                return self.embedding_model.embed_query(text)
            except Exception as e:
                logger.warning(f"Error getting embedding: {str(e)}, falling back to simple vector")
                
        # Fallback: generate a simple vector based on character frequencies
        # This is not a good embedding but serves as a fallback when no model is available
        char_counts = {}
        for char in text.lower():
            if char in char_counts:
                char_counts[char] += 1
            else:
                char_counts[char] = 1
                
        # Create a fixed-size vector (26 for letters + 10 for digits)
        vector = [0] * 36
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz0123456789"):
            if char in char_counts:
                vector[i] = char_counts[char]
                
        # Normalize vector
        magnitude = sum(v*v for v in vector) ** 0.5
        if magnitude > 0:
            vector = [v/magnitude for v in vector]
            
        # Pad to match typical embedding size for consistency
        return vector + [0.0] * (1536 - len(vector))
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
            
        # Try using embeddings for better semantic similarity
        try:
            if self.embedding_model:
                # Get embeddings for both texts
                embedding1 = self.get_embedding(text1)
                embedding2 = self.get_embedding(text2)
                
                # Calculate cosine similarity
                dot_product = sum(a*b for a, b in zip(embedding1, embedding2))
                magnitude1 = sum(a*a for a in embedding1) ** 0.5
                magnitude2 = sum(b*b for b in embedding2) ** 0.5
                
                if magnitude1 > 0 and magnitude2 > 0:
                    similarity = dot_product / (magnitude1 * magnitude2)
                    return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.warning(f"Error calculating embedding similarity: {str(e)}, falling back to token overlap")
                
        # Fallback: Use simple word overlap
        words1 = set(self._tokenize(text1.lower()))
        words2 = set(self._tokenize(text2.lower()))
        
        if not words1 or not words2:
            return 0.0
            
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for text.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Remove punctuation and split by whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        return [token for token in text.split() if token]
    
    def detect_greeting(self, text: str) -> float:
        """
        Detect if the text contains a greeting.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score (0.0-1.0)
        """
        text = text.lower()
        
        # Common greeting patterns
        greeting_phrases = [
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon", 
            "good evening", "howdy", "what's up", "how are you", "how's it going",
            "nice to meet you", "good day"
        ]
        
        # Get first few words (where greetings typically appear)
        first_words = ' '.join(self._tokenize(text)[:3])
        
        # Check for exact greeting matches at the start
        for phrase in greeting_phrases:
            if first_words.startswith(phrase) or text.startswith(phrase):
                return 0.95
        
        # Calculate similarity with common greetings
        greeting_examples = [
            "Hello there!",
            "Hi, I need help with something",
            "Hey, can you assist me?",
            "Good morning, I have a question"
        ]
        
        similarities = [self.calculate_similarity(text, example) for example in greeting_examples]
        max_similarity = max(similarities) if similarities else 0.0
        
        # Higher confidence for short texts that are likely just greetings
        if len(text) < 20 and max_similarity > 0.5:
            max_similarity += 0.2
            
        return min(1.0, max_similarity)
    
    def detect_conversation_end(self, text: str) -> float:
        """
        Detect if the text indicates the end of a conversation.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score (0.0-1.0)
        """
        text = text.lower()
        
        # Common goodbye patterns
        goodbye_phrases = [
            "goodbye", "bye", "see you", "talk to you later", "until next time",
            "that's all", "that will be all", "nothing else", "we're done", "i'm done",
            "thanks, bye", "thank you, bye", "have a good day", "have a nice day"
        ]
        
        # Check for exact goodbye matches
        for phrase in goodbye_phrases:
            if phrase in text:
                return 0.9
        
        # Calculate similarity with common goodbyes
        goodbye_examples = [
            "Thanks for your help, goodbye!",
            "That's all I needed, thanks!",
            "I think we're done here.",
            "I don't need anything else, bye.",
            "That's it, thank you."
        ]
        
        similarities = [self.calculate_similarity(text, example) for example in goodbye_examples]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_human_transfer_request(self, text: str) -> float:
        """
        Detect if the text is requesting a transfer to a human agent.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score (0.0-1.0)
        """
        text = text.lower()
        
        # Common human transfer request patterns
        transfer_phrases = [
            "speak to a human", "talk to a human", "connect to a person",
            "speak to a representative", "talk to a representative", "real person",
            "transfer me", "speak to someone else", "connect me with a representative",
            "agent please", "customer service", "connect to an agent",
            "i want to speak to a real person", "get me a human"
        ]
        
        # Check for exact transfer request matches
        for phrase in transfer_phrases:
            if phrase in text:
                return 0.95
        
        # Calculate similarity with common transfer requests
        transfer_examples = [
            "I want to speak to a customer service representative please.",
            "Can you transfer me to a real person?",
            "I need to talk to a human agent.",
            "This isn't working, I need to speak with a real person please.",
            "Connect me with someone who can help me better."
        ]
        
        similarities = [self.calculate_similarity(text, example) for example in transfer_examples]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_negative_feedback(self, text: str) -> float:
        """
        Detect if the text contains negative feedback or frustration.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score (0.0-1.0)
        """
        text = text.lower()
        
        # Common negative feedback patterns
        negative_phrases = [
            "not what i asked", "not what i was looking for", "not helping",
            "not relevant", "didn't understand", "don't understand",
            "this is wrong", "incorrect", "that's not right", "wrong answer",
            "i'm frustrated", "this is frustrating", "not working",
            "useless", "waste of time", "not useful", "bad response"
        ]
        
        # Check for exact negative feedback matches
        for phrase in negative_phrases:
            if phrase in text:
                return 0.9
        
        # Calculate similarity with common negative feedback examples
        negative_examples = [
            "That's not what I was asking about.",
            "You're not understanding my question.",
            "This isn't helpful at all.",
            "You're giving me the wrong information.",
            "This is frustrating, you're not answering my question."
        ]
        
        similarities = [self.calculate_similarity(text, example) for example in negative_examples]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    def detect_conversation_interruption(self, previous_topic: str, current_text: str) -> Tuple[bool, float]:
        """
        Detect if current text represents an interruption or topic switch.
        
        Args:
            previous_topic: The previous conversation topic or message
            current_text: The current user message
            
        Returns:
            Tuple of (is_interruption, confidence)
        """
        if not previous_topic or not current_text:
            return False, 0.0
            
        # Check for explicit interruption phrases
        interruption_phrases = [
            "actually", "wait", "hold on", "different question", 
            "change the subject", "something else", "nevermind", 
            "forget that", "different topic", "instead"
        ]
        
        # Check if the text starts with any interruption phrases
        text_lower = current_text.lower()
        for phrase in interruption_phrases:
            if text_lower.startswith(phrase) or f" {phrase} " in f" {text_lower} ":
                return True, 0.9
        
        # If no explicit interruption, calculate semantic similarity
        similarity = self.calculate_similarity(previous_topic, current_text)
        
        # Lower similarity suggests a topic switch
        dissimilarity = 1.0 - similarity
        
        # Set threshold for interruption detection
        is_interruption = dissimilarity > 0.7
        confidence = dissimilarity if is_interruption else 0.0
        
        return is_interruption, confidence


# Create a singleton instance for use throughout the application
semantic_analyzer = SemanticAnalyzer()
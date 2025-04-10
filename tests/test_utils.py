"""
Utilities for testing Staples Brain.
These utilities provide consistent mocking functionality for the tests.
"""

import asyncio
import json
from unittest.mock import MagicMock
from typing import Any, Dict, List, Optional, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult

class MockChatModel(BaseChatModel):
    """
    Mock chat model for testing.
    This model provides configurable responses for testing.
    Compatible with both older and newer OpenAI API versions.
    """

    def __init__(self, 
                 responses: Optional[List[str]] = None,
                 confidence_score: float = 0.9):
        """
        Initialize the mock chat model.
        
        Args:
            responses: List of responses to return in sequence
            confidence_score: Default confidence score for can_handle calls
        """
        super().__init__()
        self._responses = responses or [
            # Default sequence of responses
            str(confidence_score),  # For confidence checks
            '{"tracking_number": "TRACK123456", "shipping_carrier": "UPS", "order_number": null, "time_frame": "3 days"}',
            "Your package with tracking number TRACK123456 is currently in transit and expected to be delivered in 3 days.",
            str(confidence_score),
            '{"email": "user@example.com", "username": null, "account_type": "Staples.com", "issue": "forgot password"}',
            "I've sent password reset instructions to your email address (user@example.com). Please check your inbox."
        ]
        self._response_counter = 0
        # Add attributes needed for compatibility with newer API
        self.model_name = "gpt-4-mock"
        # Handle client attribute for testing
        self.client = self  # Make self.client point to self for compatibility
        
        # Initialize the chat attribute for the client
        class ChatCompletionsAPI:
            """Mock completions API interface"""
            
            @staticmethod
            def create(model=None, messages=None, **kwargs):
                """Mock create method for chat completions"""
                message_content = "0.9"  # Default confidence score
                
                # Handle case where messages is None or empty
                if messages:
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get("role") == "user" and isinstance(msg.get("content"), str):
                            content = msg.get("content", "")
                            if "confidence" in content.lower() or "can you handle" in content.lower():
                                # This is a confidence check, return a high score
                                message_content = "0.9"
                                break
                
                # Mock response object with OpenAI-style structure
                class MockChoice:
                    class Message:
                        def __init__(self, content):
                            self.content = content
                    
                    def __init__(self, content):
                        self.message = self.Message(content)
                        
                class MockResponse:
                    def __init__(self, choices):
                        self.choices = choices
                        
                return MockResponse([MockChoice(message_content)])
                
        # Create a chat namespace with completions API
        class ChatNamespace:
            def __init__(self):
                self.completions = ChatCompletionsAPI()
                
        # Assign chat namespace to client 
        self.chat = ChatNamespace()
    
    def _is_can_handle_call(self, messages: List[Any]) -> bool:
        """Check if this is a can_handle capability call"""
        for msg in messages:
            content = None
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content
                
            if content and isinstance(content, str) and (
                "can you handle" in content.lower() or
                "rate your confidence" in content.lower() or
                "confidence score" in content.lower()
            ):
                return True
        return False
    
    def _get_content_based_on_message(self, messages: List[Any]) -> str:
        """Process message content to determine appropriate response"""
        # Extract the last user message for easier analysis
        user_message = ""
        for msg in reversed(messages):
            content = None
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content
                
            if content:
                user_message = content
                break
        
        # Basic routing based on user message content
        if "package" in user_message.lower() or "track" in user_message.lower():
            return json.dumps({"tracking_number": None, "message": "Please provide your tracking number"})
        elif "password" in user_message.lower() or "login" in user_message.lower():
            return json.dumps({"email": None, "message": "Please provide your email address"})
        elif "store" in user_message.lower() or "location" in user_message.lower():
            return json.dumps({"location": None, "message": "Please provide your location"})
        elif "product" in user_message.lower():
            return json.dumps({"product_type": None, "message": "What product are you interested in?"})
        
        return self._responses[self._response_counter % len(self._responses)]
    
    @property
    def _llm_type(self) -> str:
        """Get the type of this LLM"""
        return "mock_chat_model"
    
    def _get_next_response(self) -> str:
        """Get the next response in the sequence"""
        response = self._responses[self._response_counter % len(self._responses)]
        self._response_counter += 1
        return response
    
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate a response asynchronously"""
        content = ""
        if self._is_can_handle_call(messages):
            content = "0.9"  # Standard confidence score for can_handle calls
        else:
            content = self._get_content_based_on_message(messages) or self._get_next_response()
            
        message = AIMessageChunk(content=content)
        chunk = ChatGenerationChunk(message=message)
        return ChatResult(generations=[chunk])
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate a response synchronously"""
        # Don't use asyncio.run() as it creates a new event loop, which can cause issues
        # when tests are running in an async context already
        content = ""
        if self._is_can_handle_call(messages):
            content = "0.9"  # Standard confidence score for can_handle calls
        else:
            content = self._get_content_based_on_message(messages) or self._get_next_response()
            
        message = AIMessageChunk(content=content)
        chunk = ChatGenerationChunk(message=message)
        return ChatResult(generations=[chunk])
        
    # Adding newer OpenAI client compatibility
    class chat:
        """Mock chat namespace for newer OpenAI client interface"""
        
        def __init__(self, parent):
            self.parent = parent
            
        class completions:
            """Mock completions namespace for newer OpenAI client interface"""
            
            @staticmethod
            def create(model=None, messages=None, **kwargs):
                """
                Mock implementation of chat.completions.create method for compatibility
                with newer OpenAI client interface.
                """
                # Simple response object similar to new OpenAI style
                message_content = "0.9"  # Default confidence score
                
                # Handle case where messages is None
                if messages:
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get("role") == "user" and isinstance(msg.get("content"), str):
                            content = msg.get("content", "")
                            if "confidence" in content.lower() or "can you handle" in content.lower():
                                # This is a confidence check, return a high score
                                message_content = "0.9"
                                break
                
                # Mock response object with OpenAI-style structure
                class MockChoice:
                    class Message:
                        def __init__(self, content):
                            self.content = content
                    
                    def __init__(self, content):
                        self.message = self.Message(content)
                        
                class MockResponse:
                    def __init__(self, choices):
                        self.choices = choices
                        
                return MockResponse([MockChoice(message_content)])


def create_mock_chat_model(responses=None, confidence_score=0.9):
    """
    Create a mock chat model for testing.
    
    Args:
        responses: List of responses to return in sequence
        confidence_score: Default confidence score for can_handle calls
        
    Returns:
        MockChatModel instance
    """
    return MockChatModel(responses=responses, confidence_score=confidence_score)


def patch_llm_in_brain(brain, mock_llm=None):
    """
    Patch the LLM in a StaplesBrain instance.
    
    Args:
        brain: The StaplesBrain instance to patch
        mock_llm: Optional mock LLM to use (creates one if not provided)
        
    Returns:
        The mock LLM that was used
    """
    if mock_llm is None:
        mock_llm = create_mock_chat_model()
    
    # Replace the LLM in the brain
    brain.llm = mock_llm
    
    # Replace the LLM in all agents
    for agent in brain.agents:
        agent.llm = mock_llm
        
        # Replace LLMs in all chains
        if hasattr(agent, "classifier_chain") and hasattr(agent.classifier_chain, "llm"):
            agent.classifier_chain.llm = mock_llm
        if hasattr(agent, "extraction_chain") and hasattr(agent.extraction_chain, "llm"):
            agent.extraction_chain.llm = mock_llm
        if hasattr(agent, "response_chain") and hasattr(agent.response_chain, "llm"):
            agent.response_chain.llm = mock_llm
    
    return mock_llm
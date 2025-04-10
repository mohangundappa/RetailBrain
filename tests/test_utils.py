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

class MockClient:
    """A mock client that mimics the OpenAI client structure for testing"""
    
    def __init__(self, parent=None):
        self.parent = parent
        
        # Create mock chat completions
        class ChatCompletionsAPI:
            def __init__(self, parent):
                self.parent = parent
                
            def create(self, model=None, messages=None, **kwargs):
                """Synchronous create method"""
                return self._create_response(model, messages, **kwargs)
                
            async def create(self, model=None, messages=None, **kwargs):
                """Async create method - returns the same result as sync version"""
                # We need to make this truly awaitable
                await asyncio.sleep(0)  # This makes the function awaitable
                return self._create_response(model, messages, **kwargs)
                
            def _create_response(self, model=None, messages=None, **kwargs):
                """Common implementation for both sync and async methods"""
                # Determine response content
                if self.parent is None:
                    response_content = "0.7"  # Default confidence
                else:
                    # Check if this is a confidence check
                    is_confidence_check = False
                    if messages:
                        for msg in messages:
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                content = msg.get("content", "")
                                if content and isinstance(content, str) and (
                                    "confidence" in content.lower() or 
                                    "can you handle" in content.lower() or 
                                    "rate your" in content.lower()
                                ):
                                    is_confidence_check = True
                                    break
                    
                    # Get appropriate response based on message type            
                    if is_confidence_check:
                        response_content = str(getattr(self.parent, "_confidence_score", 0.7))
                    else:
                        # Get content from parent's response list
                        if hasattr(self.parent, "_get_next_response"):
                            response_content = self.parent._get_next_response()
                        else:
                            response_content = "Mock response"
                
                # Create mock response structure
                class MockMessage:
                    def __init__(self, content):
                        self.content = content
                        
                class MockChoice:
                    def __init__(self, content):
                        self.message = MockMessage(content)
                        self.index = 0
                        self.finish_reason = "stop"
                        
                class MockResponse:
                    def __init__(self, choices):
                        self.choices = choices
                        self.id = "mock-response-id"
                        self.model = "mock-model"
                        self.usage = {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5}
                
                return MockResponse([MockChoice(response_content)])
        
        # Create mock chat namespace
        class ChatNamespace:
            def __init__(self, parent):
                self.parent = parent
                self.completions = ChatCompletionsAPI(parent)
        
        # Assign chat namespace
        self.chat = ChatNamespace(self)


class MockChatModel(BaseChatModel):
    """
    Mock chat model for testing.
    This model provides configurable responses for testing.
    Compatible with both older and newer OpenAI API versions.
    """
    
    # Define all required fields as class attributes for pydantic
    model_name: str = "gpt-4-mock"
    client: Any = None  # Define this as a field in the model
    async_client: Any = None  # Define this as a field in the model
    invoke: Any = None
    ainvoke: Any = None
    
    def __init__(self, 
                 responses: Optional[List[str]] = None,
                 confidence_score: float = 0.9):
        """
        Initialize the mock chat model.
        
        Args:
            responses: List of responses to return in sequence
            confidence_score: Default confidence score for can_handle calls
        """
        # Since BaseChatModel is a pydantic model, we need to initialize it properly
        super().__init__(callbacks=None)  # Initialize with required args
        
        # Set up responses
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
        self._confidence_score = confidence_score
        
        # Create mock client that can be accessed safely
        self._mock_client = MockClient(self)
        
        # Add required attributes for LangChain OpenAI compatibility
        self.client = self._mock_client
        self.async_client = self._mock_client  # Important for async calls
        self.model_name = "mock-chat-model"
        
        # Add support for invoking directly (used by some chains)
        self.invoke = MagicMock(return_value=MagicMock(content=self._get_next_response()))
        
        # For asynchronous calls, we need to return an awaitable
        async def _async_mock_ainvoke(*args, **kwargs):
            return MagicMock(content=self._get_next_response())
        
        self.ainvoke = MagicMock(side_effect=_async_mock_ainvoke)
    
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
        # Add a small sleep to make this truly awaitable
        await asyncio.sleep(0)
        
        content = ""
        if self._is_can_handle_call(messages):
            content = str(self._confidence_score)  # Use configured confidence score
        else:
            content = self._get_content_based_on_message(messages) or self._get_next_response()
            
        message = AIMessageChunk(content=content)
        chunk = ChatGenerationChunk(message=message)
        
        # Create a more complete response object that matches OpenAI's structure
        result = ChatResult(
            generations=[chunk], 
            llm_output={
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        )
        return result
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate a response synchronously"""
        # Don't use asyncio.run() as it creates a new event loop, which can cause issues
        # when tests are running in an async context already
        content = ""
        if self._is_can_handle_call(messages):
            content = str(self._confidence_score)  # Use configured confidence score
        else:
            content = self._get_content_based_on_message(messages) or self._get_next_response()
            
        message = AIMessageChunk(content=content)
        chunk = ChatGenerationChunk(message=message)
        
        # Create a more complete response object that matches OpenAI's structure
        result = ChatResult(
            generations=[chunk], 
            llm_output={
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        )
        return result
        
    # This class property is added for backward compatibility with some test code
    # The actual implementation is handled by the instance-based chat namespace
    @property
    def chat(self):
        """Mock chat namespace (class property) for older code compatibility"""
        if not hasattr(self, "_chat"):
            # Create the ChatNamespace on first access
            class ChatCompletionsAPI:
                """Mock completions API interface"""
                
                def __init__(self, parent):
                    self.parent = parent
                
                def create(self, model=None, messages=None, **kwargs):
                    """Mock synchronous create method for chat completions"""
                    return self._create_response(model, messages, **kwargs)
                
                async def create(self, model=None, messages=None, **kwargs):
                    """Mock asynchronous create method for chat completions"""
                    # We need to make this truly awaitable
                    await asyncio.sleep(0)  # This makes the function awaitable
                    return self._create_response(model, messages, **kwargs)
                
                def _create_response(self, model=None, messages=None, **kwargs):
                    """Common implementation for both sync and async methods"""
                    # Initialize with a default confidence score
                    message_content = str(self.parent._confidence_score)
                    
                    # Handle case where messages is None or empty
                    if messages:
                        for msg in messages:
                            if isinstance(msg, dict) and msg.get("role") == "user" and isinstance(msg.get("content"), str):
                                content = msg.get("content", "")
                                if "confidence" in content.lower() or "can you handle" in content.lower() or "rate your confidence" in content.lower():
                                    # This is a confidence check for an agent, use the configured confidence score
                                    message_content = str(self.parent._confidence_score)
                                    break
                                else:
                                    # For regular content responses, use the next in sequence
                                    message_content = self.parent._get_content_based_on_message(messages) or self.parent._get_next_response()
                    
                    # Mock response object with OpenAI-style structure
                    class MockChoice:
                        class Message:
                            def __init__(self, content):
                                self.content = content
                        
                        def __init__(self, content):
                            self.message = self.Message(content)
                            self.index = 0
                            self.finish_reason = "stop"
                            
                    class MockResponse:
                        def __init__(self, choices):
                            self.choices = choices
                            self.id = "mock-response-id"
                            self.model = "mock-model"
                            self.usage = {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5}
                            
                    return MockResponse([MockChoice(message_content)])
                    
            # Create a chat namespace with completions API
            class ChatNamespace:
                def __init__(self, parent):
                    self.parent = parent
                    self.completions = ChatCompletionsAPI(parent)
                    
            # Cache the namespace
            self._chat = ChatNamespace(self)
            
        return self._chat


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
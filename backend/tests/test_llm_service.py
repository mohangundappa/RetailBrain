"""
Tests for the LLM Service with Circuit Breaker functionality.
"""

import os
import unittest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from openai import APIError, RateLimitError, APIConnectionError
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageParam

from backend.services.llm_service import (
    generate_openai_response,
    get_chat_completion,
    get_json_response,
    LLMServiceError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMServiceUnavailableError
)
from backend.utils.circuit_breaker import reset_all_circuits


# Mock response for OpenAI
def create_mock_completion(content="Test response", model="gpt-4o"):
    """Create a mock ChatCompletion object."""
    mock_message = MagicMock()
    mock_message.content = content
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    
    mock_usage = MagicMock()
    mock_usage.total_tokens = 100
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 50
    
    mock_completion = MagicMock(spec=ChatCompletion)
    mock_completion.choices = [mock_choice]
    mock_completion.model = model
    mock_completion.usage = mock_usage
    
    return mock_completion


class TestLLMService(unittest.IsolatedAsyncioTestCase):
    """Tests for the LLM service with circuit breaker."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset all circuit breakers between tests
        reset_all_circuits()
        
        # Create a mock for os.environ to mock API keys
        self.env_patcher = patch.dict(os.environ, {"OPENAI_API_KEY": "mock-api-key"})
        self.env_patcher.start()
        
        # Set up a mock OpenAI client
        self.mock_client_patcher = patch("backend.services.llm_service.create_openai_client")
        self.mock_create_client = self.mock_client_patcher.start()
        
        self.mock_client = AsyncMock()
        self.mock_create_client.return_value = self.mock_client
        
        # Mock OpenAI chat completions create method
        self.mock_client.chat = AsyncMock()
        self.mock_client.chat.completions = AsyncMock()
        self.mock_client.chat.completions.create = AsyncMock()
    
    def tearDown(self):
        """Clean up after each test."""
        self.mock_client_patcher.stop()
        self.env_patcher.stop()
    
    async def test_successful_response(self):
        """Test that a successful response is correctly processed."""
        # Set up the mock response
        mock_completion = create_mock_completion(content="This is a test response")
        self.mock_client.chat.completions.create.return_value = mock_completion
        
        # Call the service
        messages = [{"role": "user", "content": "Hello"}]
        result = await generate_openai_response(messages=messages)
        
        # Check that the client was called with the correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["messages"], messages)
        
        # Check the result
        self.assertEqual(result["content"], "This is a test response")
        self.assertEqual(result["model"], "gpt-4o")
        self.assertEqual(result["usage"]["total_tokens"], 100)
        self.assertEqual(result["finish_reason"], "stop")
        self.assertFalse(result["is_fallback"])
    
    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors."""
        # Set up the mock to raise a rate limit error
        self.mock_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded")
        
        # Call the service and check that it raises the appropriate error
        messages = [{"role": "user", "content": "Hello"}]
        with self.assertRaises(LLMRateLimitError):
            await generate_openai_response(messages=messages)
    
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Set up the mock to raise a connection error
        self.mock_client.chat.completions.create.side_effect = APIConnectionError("Connection failed")
        
        # Call the service and check that it raises the appropriate error
        messages = [{"role": "user", "content": "Hello"}]
        with self.assertRaises(LLMConnectionError):
            await generate_openai_response(messages=messages)
    
    async def test_circuit_open_fallback(self):
        """Test fallback when circuit breaker is open."""
        # Set up the mock to raise errors to trigger circuit breaker
        self.mock_client.chat.completions.create.side_effect = APIError("Server error")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # Call repeatedly to open the circuit
        for _ in range(5):  # Should exceed the failure threshold
            try:
                await generate_openai_response(messages=messages)
            except LLMServiceError:
                pass
        
        # One more call should use the fallback
        result = await generate_openai_response(messages=messages)
        
        # Verify this is a fallback response
        self.assertTrue(result["is_fallback"])
        self.assertIn("temporarily unavailable", result["content"])
    
    async def test_get_chat_completion(self):
        """Test the convenience function for chat completion."""
        # Set up the mock response
        mock_completion = create_mock_completion(content="Chat response")
        self.mock_client.chat.completions.create.return_value = mock_completion
        
        # Call the service
        result = await get_chat_completion(
            user_message="Hello",
            system_message="You are a helpful assistant"
        )
        
        # Check that the client was called with the correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]
        self.assertEqual(len(call_args["messages"]), 2)  # System + user
        self.assertEqual(call_args["messages"][0]["role"], "system")
        self.assertEqual(call_args["messages"][1]["role"], "user")
        
        # Check the result
        self.assertEqual(result["content"], "Chat response")
    
    async def test_get_json_response(self):
        """Test getting a JSON formatted response."""
        # Set up the mock response with valid JSON
        json_content = '{"answer": "This is a test", "confidence": 0.95}'
        mock_completion = create_mock_completion(content=json_content)
        self.mock_client.chat.completions.create.return_value = mock_completion
        
        # Call the service
        result = await get_json_response(user_message="Generate JSON")
        
        # Check that the response format was set correctly
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["response_format"], {"type": "json_object"})
        
        # Check the parsed JSON result
        self.assertIn("parsed_json", result)
        self.assertEqual(result["parsed_json"]["answer"], "This is a test")
        self.assertEqual(result["parsed_json"]["confidence"], 0.95)
    
    async def test_handle_json_parse_error(self):
        """Test handling of invalid JSON in json_response."""
        # Set up the mock response with invalid JSON
        invalid_json = "This is not valid JSON"
        mock_completion = create_mock_completion(content=invalid_json)
        self.mock_client.chat.completions.create.return_value = mock_completion
        
        # Call the service
        result = await get_json_response(user_message="Generate JSON")
        
        # Check that a JSON error was recorded
        self.assertIn("json_error", result)
        self.assertNotIn("parsed_json", result)


if __name__ == "__main__":
    unittest.main()
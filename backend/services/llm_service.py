"""
LLM Service with circuit breaker integration.

This module provides services for interacting with LLMs (e.g., OpenAI)
with built-in circuit breaker pattern to handle failures gracefully.
"""

import json
import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Union, Optional, Tuple

import openai
from openai import OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from backend.utils.circuit_breaker import get_or_create_circuit
from backend.utils.retry import retry_async

logger = logging.getLogger(__name__)

# Define custom exceptions for the LLM service
class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass

class LLMRateLimitError(LLMServiceError):
    """Exception raised when LLM rate limits are hit."""
    pass

class LLMAuthenticationError(LLMServiceError):
    """Exception raised when authentication with the LLM provider fails."""
    pass

class LLMTimeoutError(LLMServiceError):
    """Exception raised when LLM requests time out."""
    pass

class LLMConnectionError(LLMServiceError):
    """Exception raised when connection to LLM provider fails."""
    pass

class LLMServiceUnavailableError(LLMServiceError):
    """Exception raised when the LLM service is unavailable (circuit open)."""
    pass

# Function to create OpenAI client
def create_openai_client() -> OpenAI:
    """
    Create an authenticated OpenAI client.
    
    Returns:
        OpenAI: Authenticated OpenAI client
        
    Raises:
        LLMAuthenticationError: If API key is not available or invalid
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMAuthenticationError("OpenAI API key not found in environment")
    
    try:
        # Set up the client with the API key
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
        raise LLMAuthenticationError(f"Failed to initialize OpenAI client: {str(e)}")


# Apply circuit breaker to OpenAI API calls
@retry_async(
    max_retries=2,
    retry_delay=1,
    max_delay=5,
    exceptions=(APIConnectionError, APITimeoutError)
)
async def generate_openai_response(
    messages: List[ChatCompletionMessageParam],
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Generate a response from OpenAI with circuit breaker protection.
    
    Args:
        messages: List of message objects for the conversation
        model: OpenAI model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        response_format: Format for the response
        timeout: Request timeout in seconds
        
    Returns:
        Dict containing the response and metadata
        
    Raises:
        LLMRateLimitError: If rate limits are hit
        LLMTimeoutError: If the request times out
        LLMConnectionError: If connection fails
        LLMServiceUnavailableError: If circuit is open
        LLMServiceError: For other errors
    """
    # Create a circuit breaker for OpenAI
    circuit = get_or_create_circuit(
        name="openai_api",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=timeout
    )
    
    # Set a fallback function
    def fallback_response() -> Dict[str, Any]:
        last_message = messages[-1]["content"] if messages else ""
        return {
            "content": f"I'm sorry, but the AI service is temporarily unavailable. "
                      f"Your request was: {last_message[:100]}... "
                      f"Please try again in a few minutes.",
            "model": model,
            "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
            "finish_reason": "service_unavailable",
            "is_fallback": True
        }
    
    circuit.set_fallback(fallback_response)
    
    # Define the wrapped function
    @circuit
    async def _generate_response() -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Create a client
            client = create_openai_client()
            
            # Call the OpenAI API
            completion_args = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens is not None:
                completion_args["max_tokens"] = max_tokens
                
            if response_format is not None:
                completion_args["response_format"] = response_format
            
            # Make the API call
            completion = await client.chat.completions.create(**completion_args)
            
            # Extract the response
            response = {
                "content": completion.choices[0].message.content,
                "model": completion.model,
                "usage": {
                    "total_tokens": completion.usage.total_tokens,
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens
                },
                "finish_reason": completion.choices[0].finish_reason,
                "is_fallback": False
            }
            
            # Log success
            elapsed = time.time() - start_time
            logger.info(f"OpenAI request successful ({elapsed:.2f}s, "
                       f"{response['usage']['total_tokens']} tokens, "
                       f"model={model})")
            
            return response
            
        except RateLimitError as e:
            elapsed = time.time() - start_time
            logger.warning(f"OpenAI rate limit error after {elapsed:.2f}s: {str(e)}")
            raise LLMRateLimitError(f"Rate limit exceeded: {str(e)}")
            
        except (APITimeoutError, asyncio.TimeoutError) as e:
            elapsed = time.time() - start_time
            logger.warning(f"OpenAI timeout error after {elapsed:.2f}s: {str(e)}")
            raise LLMTimeoutError(f"Request timed out: {str(e)}")
            
        except APIConnectionError as e:
            elapsed = time.time() - start_time
            logger.warning(f"OpenAI connection error after {elapsed:.2f}s: {str(e)}")
            raise LLMConnectionError(f"Connection error: {str(e)}")
            
        except (APIError, Exception) as e:
            elapsed = time.time() - start_time
            logger.error(f"OpenAI API error after {elapsed:.2f}s: {str(e)}")
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
    
    # Call the wrapped function
    try:
        return await _generate_response()
    except LLMServiceUnavailableError:
        # This is raised when the circuit is open and fallback fails
        return fallback_response()
    except Exception as e:
        logger.error(f"Unexpected error in generate_openai_response: {str(e)}")
        raise


async def get_chat_completion(
    user_message: str,
    system_message: str = "You are a helpful assistant.",
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a chat completion for a simple user message with system context.
    
    Args:
        user_message: The user's message
        system_message: System message for context
        model: OpenAI model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        Response containing the completion and metadata
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    
    return await generate_openai_response(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )


async def get_json_response(
    user_message: str,
    system_message: str = "You are a helpful assistant that responds with valid JSON.",
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    temperature: float = 0.3,  # Lower temperature for more deterministic JSON
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get a structured JSON response from the model.
    
    Args:
        user_message: The user's message
        system_message: System message for context
        model: OpenAI model to use
        temperature: Sampling temperature (low for structured output)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Response with parsed JSON data and metadata
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    
    response = await generate_openai_response(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"}
    )
    
    # Try to parse the JSON response
    try:
        response["parsed_json"] = json.loads(response["content"])
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        response["json_error"] = str(e)
    
    return response
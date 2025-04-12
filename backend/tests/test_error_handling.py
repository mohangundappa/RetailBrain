"""
Tests for error handling and retry mechanisms.

This module tests the functionality of error classification, recovery,
and retry mechanisms in the error_handling.py module.
"""
import json
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from backend.brain.native_graph.error_handling import (
    ErrorType,
    classify_error,
    record_error,
    get_error_recovery_response,
    with_error_handling,
    parse_json_with_recovery,
    retry_on_error
)
from backend.utils.retry import retry_async


class TestErrorClassification(unittest.TestCase):
    """Tests for error classification functions."""
    
    def test_classify_json_error(self):
        """Test classification of JSON decode errors."""
        # Create a JSONDecodeError
        try:
            json.loads("{invalid json")
        except Exception as e:
            error = e
        
        # Classify the error
        error_type = classify_error(error)
        
        # Assert
        self.assertEqual(error_type, ErrorType.JSON_DECODE_ERROR)
    
    def test_classify_llm_rate_limit(self):
        """Test classification of LLM rate limit errors."""
        class OpenAIRateLimitError(Exception):
            pass
        
        error = OpenAIRateLimitError("You exceeded your current quota, please check your plan and billing details. For more information on rate limits please refer to https://platform.openai.com/docs/guides/rate-limits")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.LLM_RATE_LIMIT)
    
    def test_classify_llm_context_limit(self):
        """Test classification of LLM context limit errors."""
        class OpenAIContextLimitError(Exception):
            pass
        
        error = OpenAIContextLimitError("This model's maximum context length is 16385 tokens. However, your messages resulted in 16586 tokens")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.LLM_CONTEXT_LIMIT)
    
    def test_classify_database_error(self):
        """Test classification of database errors."""
        error = Exception("sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to database failed")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.DATABASE_ERROR)
    
    def test_classify_state_persistence_error(self):
        """Test classification of state persistence errors."""
        error = Exception("Error saving state to database: could not connect to orchestration_state table")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.STATE_PERSISTENCE_ERROR)
    
    def test_classify_agent_not_found(self):
        """Test classification of agent not found errors."""
        error = Exception("agent not found: 'custom_agent'")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.AGENT_NOT_FOUND)
    
    def test_classify_unknown_error(self):
        """Test classification of unknown errors."""
        error = Exception("This is an unknown error type")
        error_type = classify_error(error)
        
        self.assertEqual(error_type, ErrorType.UNKNOWN)


class TestErrorRecording(unittest.TestCase):
    """Tests for error recording functions."""
    
    def test_record_error(self):
        """Test recording an error in the state."""
        # Arrange
        state = {"execution": {"errors": []}}
        node_name = "test_node"
        error = Exception("Test error")
        
        # Act
        updated_state = record_error(state, node_name, error)
        
        # Assert
        self.assertIn("execution", updated_state)
        self.assertIn("errors", updated_state["execution"])
        self.assertEqual(len(updated_state["execution"]["errors"]), 1)
        
        error_record = updated_state["execution"]["errors"][0]
        self.assertEqual(error_record["node"], node_name)
        self.assertEqual(error_record["error"], "Test error")
        self.assertIn("timestamp", error_record)
        self.assertIn("traceback", error_record)
    
    def test_record_error_with_type(self):
        """Test recording an error with a specified type."""
        # Arrange
        state = {"execution": {"errors": []}}
        node_name = "test_node"
        error = Exception("Test error")
        error_type = ErrorType.DATABASE_ERROR
        
        # Act
        updated_state = record_error(state, node_name, error, error_type)
        
        # Assert
        error_record = updated_state["execution"]["errors"][0]
        self.assertEqual(error_record["error_type"], error_type)
    
    def test_record_error_with_additional_info(self):
        """Test recording an error with additional information."""
        # Arrange
        state = {"execution": {"errors": []}}
        node_name = "test_node"
        error = Exception("Test error")
        additional_info = {"query_id": "123", "api_version": "v2"}
        
        # Act
        updated_state = record_error(state, node_name, error, additional_info=additional_info)
        
        # Assert
        error_record = updated_state["execution"]["errors"][0]
        self.assertIn("additional_info", error_record)
        self.assertEqual(error_record["additional_info"], additional_info)


class TestErrorRecoveryResponses(unittest.TestCase):
    """Tests for error recovery response generation."""
    
    def test_get_error_recovery_json_decode(self):
        """Test recovery response for JSON decode error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.JSON_DECODE_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("trouble understanding", response.lower())
    
    def test_get_error_recovery_rate_limit(self):
        """Test recovery response for rate limit error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.LLM_RATE_LIMIT
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("traffic", response.lower())
    
    def test_get_error_recovery_context_limit(self):
        """Test recovery response for context limit error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.LLM_CONTEXT_LIMIT
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("conversation is getting quite detailed", response.lower())
    
    def test_get_error_recovery_api_error(self):
        """Test recovery response for API error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.LLM_API_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("trouble connecting", response.lower())
    
    def test_get_error_recovery_agent_not_found(self):
        """Test recovery response for agent not found error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.AGENT_NOT_FOUND
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("don't seem to have the right expert", response.lower())
    
    def test_get_error_recovery_agent_execution(self):
        """Test recovery response for agent execution error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.AGENT_EXECUTION_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("ran into an issue", response.lower())
    
    def test_get_error_recovery_state_persistence(self):
        """Test recovery response for state persistence error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.STATE_PERSISTENCE_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("trouble with my memory storage", response.lower())
    
    def test_get_error_recovery_database(self):
        """Test recovery response for database error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.DATABASE_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("technical issue with my memory", response.lower())
    
    def test_get_error_recovery_memory(self):
        """Test recovery response for memory error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.MEMORY_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("difficulty accessing my previous memory", response.lower())
    
    def test_get_error_recovery_orchestration(self):
        """Test recovery response for orchestration error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.ORCHESTRATION_ERROR
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("trouble coordinating", response.lower())
    
    def test_get_error_recovery_unknown(self):
        """Test recovery response for unknown error."""
        state = {"conversation": {"last_user_message": "Test message"}}
        error = Exception("Test error")
        error_type = ErrorType.UNKNOWN
        response = get_error_recovery_response(state, error, error_type)
        self.assertIn("apologize", response.lower())


class TestErrorHandlingDecorator(unittest.TestCase):
    """Tests for the with_error_handling decorator."""
    
    def test_successful_execution(self):
        """Test normal execution without errors."""
        # Arrange
        @with_error_handling("test_node")
        def test_func(state):
            state["result"] = "success"
            return state
        
        initial_state = {"execution": {}}
        
        # Act
        result = test_func(initial_state)
        
        # Assert
        self.assertEqual(result["result"], "success")
        self.assertIn("performance", result["execution"])
        self.assertIn("test_node", result["execution"]["performance"])
    
    def test_error_handling(self):
        """Test handling of errors within the decorated function."""
        # Arrange
        @with_error_handling("error_node")
        def test_func(state):
            raise ValueError("Test error")
        
        initial_state = {"execution": {}}
        
        # Act
        result = test_func(initial_state)
        
        # Assert
        self.assertIn("errors", result["execution"])
        self.assertEqual(len(result["execution"]["errors"]), 1)
        self.assertEqual(result["execution"]["errors"][0]["node"], "error_node")
        self.assertIn("agent", result)
        self.assertTrue(result["agent"]["special_case_detected"])
        self.assertEqual(result["agent"]["special_case_type"], "error_recovery")
        self.assertIn("special_case_response", result["agent"])


class TestJsonParsing(unittest.TestCase):
    """Tests for JSON parsing with recovery."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        # Arrange
        json_str = '{"key": "value", "nested": {"key2": 123}}'
        
        # Act
        result = parse_json_with_recovery(json_str)
        
        # Assert
        self.assertEqual(result, {"key": "value", "nested": {"key2": 123}})
    
    def test_parse_invalid_json_with_recovery(self):
        """Test parsing invalid JSON with recovery."""
        # Arrange
        # JSON with text before and after
        json_str = 'Some text before {"key": "value"} and text after'
        
        # Act
        result = parse_json_with_recovery(json_str)
        
        # Assert
        self.assertEqual(result, {"key": "value"})
    
    def test_parse_invalid_json_no_recovery_possible(self):
        """Test parsing invalid JSON where recovery is not possible."""
        # Arrange
        json_str = 'No valid JSON here'
        default_value = {"default": True}
        
        # Act
        result = parse_json_with_recovery(json_str, default_value)
        
        # Assert
        self.assertEqual(result, default_value)
    
    def test_parse_json_with_default_value(self):
        """Test parsing with a custom default value."""
        # Arrange
        json_str = 'Invalid JSON'
        default_value = {"custom_default": True}
        
        # Act
        result = parse_json_with_recovery(json_str, default_value)
        
        # Assert
        self.assertEqual(result, default_value)


class TestRetryDecorator(unittest.IsolatedAsyncioTestCase):
    """Tests for the retry_on_error decorator."""
    
    async def test_retry_succeeds_after_failures(self):
        """Test that a function is retried and eventually succeeds."""
        # Arrange
        mock_func = AsyncMock()
        # Function fails twice, then succeeds
        mock_func.side_effect = [
            Exception("Database connection failed"),  # First call fails
            Exception("Database connection failed"),  # Second call fails
            "success"  # Third call succeeds
        ]
        
        # Apply the decorator
        decorated_func = retry_on_error(
            max_retries=3,
            delay=0.01,  # Short delay for testing
            retry_on=[ErrorType.DATABASE_ERROR]
        )(mock_func)
        
        # Act
        result = await decorated_func()
        
        # Assert
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
    
    async def test_retry_eventually_fails(self):
        """Test that a function that consistently fails eventually gives up."""
        # Arrange
        mock_func = AsyncMock()
        error = Exception("Database connection failed")
        # Function always fails
        mock_func.side_effect = error
        
        # Apply the decorator
        decorated_func = retry_on_error(
            max_retries=2,
            delay=0.01,  # Short delay for testing
            retry_on=[ErrorType.DATABASE_ERROR]
        )(mock_func)
        
        # Act/Assert
        with self.assertRaises(Exception) as context:
            await decorated_func()
        
        # Verify that the original error is propagated
        self.assertEqual(str(context.exception), str(error))
        self.assertEqual(mock_func.call_count, 2)
    
    async def test_retry_non_retryable_error(self):
        """Test that non-retryable errors are immediately propagated."""
        # Arrange
        mock_func = AsyncMock()
        # Function fails with a non-retryable error
        mock_func.side_effect = ValueError("Invalid input")
        
        # Apply the decorator
        decorated_func = retry_on_error(
            max_retries=3,
            delay=0.01,
            retry_on=[ErrorType.DATABASE_ERROR]  # Not including ValueError
        )(mock_func)
        
        # Act/Assert
        with self.assertRaises(ValueError):
            await decorated_func()
        
        # Verify that retry was not attempted
        self.assertEqual(mock_func.call_count, 1)


class TestUtilsRetryAsync(unittest.IsolatedAsyncioTestCase):
    """Tests for the retry_async decorator in utils.retry."""
    
    async def test_retry_async_success_first_attempt(self):
        """Test successful execution on the first attempt."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        
        # Apply the decorator
        decorated_func = retry_async()(mock_func)
        
        # Act
        result = await decorated_func()
        
        # Assert
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)
    
    async def test_retry_async_success_after_retries(self):
        """Test successful execution after several retries."""
        # Arrange
        mock_func = AsyncMock()
        # Function fails twice, then succeeds
        mock_func.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            "success"
        ]
        
        # Apply the decorator
        decorated_func = retry_async(
            max_retries=3,
            retry_delay=0.01  # Short delay for testing
        )(mock_func)
        
        # Act
        result = await decorated_func()
        
        # Assert
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
    
    async def test_retry_async_all_attempts_fail(self):
        """Test behavior when all retry attempts fail."""
        # Arrange
        mock_func = AsyncMock()
        original_error = Exception("Persistent error")
        # Function always fails
        mock_func.side_effect = original_error
        
        # Apply the decorator
        decorated_func = retry_async(
            max_retries=2,
            retry_delay=0.01  # Short delay for testing
        )(mock_func)
        
        # Act/Assert
        with self.assertRaises(Exception) as context:
            await decorated_func()
        
        # Verify that the original error is propagated
        self.assertEqual(str(context.exception), str(original_error))
        self.assertEqual(mock_func.call_count, 2)


if __name__ == "__main__":
    unittest.main()
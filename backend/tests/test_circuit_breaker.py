"""
Tests for the Circuit Breaker implementation.

This module tests the circuit breaker functionality, including state transitions,
failure tracking, and recovery mechanisms.
"""

import asyncio
import unittest
import logging
import time
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from backend.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_or_create_circuit,
    reset_circuit,
    reset_all_circuits,
    get_circuit_status,
    CircuitBreakerError,
    CircuitBreakerTimeoutError
)


class TestCircuitBreaker(unittest.IsolatedAsyncioTestCase):
    """Tests for the CircuitBreaker class functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Reset the circuit registry before each test
        reset_all_circuits()

    async def test_circuit_initialization(self):
        """Test that a circuit breaker initializes correctly."""
        cb = CircuitBreaker("test_circuit", failure_threshold=3, recovery_timeout=10)
        
        self.assertEqual(cb.name, "test_circuit")
        self.assertEqual(cb.failure_threshold, 3)
        self.assertEqual(cb.base_recovery_timeout, 10)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
        self.assertIsNone(cb.last_failure_time)

    async def test_successful_execution(self):
        """Test that successful executions go through the circuit."""
        cb = CircuitBreaker("test_success")
        
        # Define a test function that always succeeds
        @cb
        async def test_func():
            return "success"
        
        # Execute the function and check results
        result = await test_func()
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    async def test_failure_threshold(self):
        """Test that the circuit opens after reaching the failure threshold."""
        cb = CircuitBreaker("test_failure", failure_threshold=2)
        
        # Define a test function that always fails
        @cb
        async def test_func():
            raise ValueError("Test failure")
        
        # First failure
        with self.assertRaises(CircuitBreakerError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 1)
        
        # Second failure should open the circuit
        with self.assertRaises(CircuitBreakerError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertEqual(cb.failure_count, 2)
        
        # With circuit open, should fail fast without executing
        with self.assertRaises(CircuitBreakerError) as context:
            await test_func()
            
        self.assertIn("unavailable", str(context.exception))
    
    async def test_timeout_handling(self):
        """Test that operations exceeding the timeout count as failures."""
        cb = CircuitBreaker("test_timeout", timeout=0.1, failure_threshold=2)
        
        # Define a test function that times out
        @cb
        async def test_func():
            await asyncio.sleep(0.2)  # Longer than the timeout
            return "should not get here"
        
        # First timeout
        with self.assertRaises(CircuitBreakerTimeoutError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 1)
        
        # Second timeout should open the circuit
        with self.assertRaises(CircuitBreakerTimeoutError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
    
    async def test_fallback_mechanism(self):
        """Test that the fallback mechanism works when the circuit is open."""
        cb = CircuitBreaker("test_fallback", failure_threshold=1)
        
        # Set up a fallback function
        async def fallback(*args, **kwargs):
            return "fallback result"
        
        cb.set_fallback(fallback)
        
        # Define a test function that always fails
        @cb
        async def test_func():
            raise ValueError("Test failure")
        
        # First call fails and opens the circuit
        with self.assertRaises(CircuitBreakerError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # Second call should use the fallback
        result = await test_func()
        self.assertEqual(result, "fallback result")
    
    async def test_recovery_transition(self):
        """Test transition to half-open and closed states during recovery."""
        # Create a circuit breaker with a very short recovery timeout
        cb = CircuitBreaker(
            "test_recovery", 
            failure_threshold=1,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=2
        )
        
        # Define a test function that will fail once then succeed
        test_results = [ValueError("Fail"), "success", "success"]
        
        @cb
        async def test_func():
            result = test_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        
        # First call fails and opens the circuit
        with self.assertRaises(CircuitBreakerError):
            await test_func()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # Wait for the recovery timeout to pass
        await asyncio.sleep(0.2)
        
        # Next call should transition to half-open and succeed
        result = await test_func()
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertEqual(cb.success_count, 1)
        
        # Another successful call should close the circuit
        result = await test_func()
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
    
    async def test_half_open_failure(self):
        """Test that a failure in half-open state returns to open with backoff."""
        cb = CircuitBreaker(
            "test_half_open_failure", 
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2
        )
        
        # Set up test results: fail, transition to half-open, then fail again
        test_func = AsyncMock(side_effect=[
            ValueError("First failure"),  # Opens the circuit
            ValueError("Half-open failure")  # Fails during half-open
        ])
        
        # Wrap the mock
        wrapped_func = cb(test_func)
        
        # First call fails and opens the circuit
        with self.assertRaises(CircuitBreakerError):
            await wrapped_func()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # Wait for the recovery timeout
        await asyncio.sleep(0.2)
        
        # The next call should transition to half-open but fail
        with self.assertRaises(CircuitBreakerError):
            await wrapped_func()
        
        # Should be open again with increased timeout
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertGreater(cb.current_recovery_timeout, 0.1)
    
    async def test_excluded_exceptions(self):
        """Test that excluded exceptions don't affect the circuit state."""
        cb = CircuitBreaker(
            "test_excluded", 
            failure_threshold=2,
            excluded_exceptions=[KeyError]
        )
        
        # Create a function that raises different exceptions
        @cb
        async def test_func(exc_type):
            if exc_type:
                raise exc_type("Test exception")
            return "success"
        
        # KeyError should be excluded and not count toward failure threshold
        with self.assertRaises(KeyError):
            await test_func(KeyError)
        
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        
        # ValueError should count toward failure threshold
        with self.assertRaises(CircuitBreakerError):
            await test_func(ValueError)
        
        self.assertEqual(cb.failure_count, 1)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        
        # Another ValueError should open the circuit
        with self.assertRaises(CircuitBreakerError):
            await test_func(ValueError)
        
        self.assertEqual(cb.state, CircuitState.OPEN)


class TestCircuitBreakerRegistry(unittest.IsolatedAsyncioTestCase):
    """Tests for the circuit breaker registry functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        reset_all_circuits()
    
    async def test_get_or_create_circuit(self):
        """Test retrieving or creating circuits from the registry."""
        # First call should create a new circuit
        cb1 = get_or_create_circuit("test_circuit_1")
        self.assertEqual(cb1.name, "test_circuit_1")
        
        # Second call with the same name should return the same instance
        cb2 = get_or_create_circuit("test_circuit_1")
        self.assertIs(cb1, cb2)
        
        # Call with a different name should create a different instance
        cb3 = get_or_create_circuit("test_circuit_2")
        self.assertIsNot(cb1, cb3)
        self.assertEqual(cb3.name, "test_circuit_2")
    
    async def test_reset_circuit(self):
        """Test resetting a specific circuit."""
        # Create a circuit and induce a failure
        cb = get_or_create_circuit("test_reset")
        
        @cb
        async def test_func():
            raise ValueError("Test failure")
        
        # Call to increment failure count
        with self.assertRaises(CircuitBreakerError):
            await test_func()
        
        self.assertEqual(cb.failure_count, 1)
        
        # Reset the circuit
        result = reset_circuit("test_reset")
        self.assertTrue(result)
        self.assertEqual(cb.failure_count, 0)
        
        # Try to reset a non-existent circuit
        result = reset_circuit("nonexistent")
        self.assertFalse(result)
    
    async def test_reset_all_circuits(self):
        """Test resetting all circuits in the registry."""
        # Create multiple circuits with failures
        cb1 = get_or_create_circuit("test_reset_all_1")
        cb2 = get_or_create_circuit("test_reset_all_2")
        
        # Manually set some failure state
        cb1.failure_count = 3
        cb1.state = CircuitState.OPEN
        cb2.failure_count = 2
        
        # Reset all circuits
        reset_all_circuits()
        
        # Verify all circuits are reset
        self.assertEqual(cb1.failure_count, 0)
        self.assertEqual(cb1.state, CircuitState.CLOSED)
        self.assertEqual(cb2.failure_count, 0)
    
    async def test_get_circuit_status(self):
        """Test getting status information about all circuits."""
        # Create circuits with different states
        cb1 = get_or_create_circuit("status_test_1")
        cb2 = get_or_create_circuit("status_test_2")
        
        # Manually set states
        cb1.state = CircuitState.OPEN
        cb1.failure_count = 5
        cb1.last_failure_time = datetime.now()
        
        cb2.state = CircuitState.HALF_OPEN
        cb2.success_count = 1
        
        # Get status
        status = get_circuit_status()
        
        # Verify the status contains the expected information
        self.assertIn("status_test_1", status)
        self.assertIn("status_test_2", status)
        
        self.assertEqual(status["status_test_1"]["state"], "open")
        self.assertEqual(status["status_test_1"]["failure_count"], 5)
        
        self.assertEqual(status["status_test_2"]["state"], "half_open")
        self.assertEqual(status["status_test_2"]["success_count"], 1)


if __name__ == "__main__":
    unittest.main()
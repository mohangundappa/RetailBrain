"""
Circuit Breaker Implementation for Staples Brain.

This module provides a circuit breaker pattern implementation to prevent
cascading failures when external services are unavailable. It includes:

1. A configurable CircuitBreaker class
2. State tracking for failure rates
3. Automatic recovery with exponential backoff
4. Fallback mechanisms
"""

import asyncio
import logging
import time
import functools
from enum import Enum
from typing import Any, Callable, TypeVar, Dict, Optional, List, Awaitable, Union, cast
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

# Type variable for the return type of the function
T = TypeVar('T')

class CircuitState(Enum):
    """Possible states for the circuit breaker."""
    CLOSED = 'closed'       # Normal operation, requests pass through
    OPEN = 'open'           # Circuit is open, requests fail fast
    HALF_OPEN = 'half_open' # Testing if the service is back online


class CircuitBreaker:
    """
    Circuit Breaker implementation.
    
    This class implements the circuit breaker pattern to prevent cascading failures
    and provide graceful degradation when external services fail.
    
    Attributes:
        name: Unique identifier for this circuit breaker
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Seconds to wait before attempting recovery
        timeout: Maximum time in seconds to wait for a response before considering it a failure
        fallback: Optional fallback function to call when the circuit is open
        state: Current state of the circuit breaker
        failure_count: Current count of consecutive failures
        last_failure_time: Timestamp of the last failure
        success_count: Count of successful calls in half-open state
        success_threshold: Number of successful calls required to close the circuit
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        timeout: float = 30.0,
        success_threshold: int = 3,
        max_backoff: int = 3600,  # Maximum backoff in seconds (1 hour)
        excluded_exceptions: Optional[List[type]] = None,
    ):
        """
        Initialize a new circuit breaker.
        
        Args:
            name: Unique identifier for this circuit breaker
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Initial seconds to wait before attempting recovery
            timeout: Maximum time in seconds to wait for a response
            success_threshold: Number of successful calls required to close the circuit
            max_backoff: Maximum backoff in seconds
            excluded_exceptions: List of exception types that should not count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.base_recovery_timeout = recovery_timeout
        self.current_recovery_timeout = recovery_timeout
        self.max_backoff = max_backoff
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions or []
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
        # Fallback handler
        self._fallback: Optional[Callable] = None
        
        # For thread safety in concurrent environments
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized (threshold={failure_threshold}, "
                   f"recovery_timeout={recovery_timeout}s, timeout={timeout}s)")
    
    def set_fallback(self, fallback: Callable[..., T]) -> None:
        """
        Set a fallback function to be called when the circuit is open.
        
        Args:
            fallback: Function to call when the circuit is open
        """
        self._fallback = fallback
        
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the circuit breaker.
        
        Returns:
            Dictionary containing the circuit breaker state information
        """
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'recovery_timeout': self.current_recovery_timeout,
            'base_recovery_timeout': self.base_recovery_timeout,
            'failure_threshold': self.failure_threshold,
            'success_threshold': self.success_threshold,
            'timeout': self.timeout,
        }
    
    async def _update_state(self) -> None:
        """Update the state of the circuit breaker based on current conditions."""
        if self.state == CircuitState.OPEN and self.last_failure_time:
            # Check if recovery timeout has elapsed
            elapsed = datetime.now() - self.last_failure_time
            if elapsed.total_seconds() >= self.current_recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning from OPEN to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
        
        elif self.state == CircuitState.HALF_OPEN:
            # Check if we've had enough successes to close the circuit
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' transitioning from HALF_OPEN to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                # Reset the recovery timeout after successful recovery
                self.current_recovery_timeout = self.base_recovery_timeout
    
    async def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker '{self.name}' threshold reached, transitioning to OPEN")
            self.state = CircuitState.OPEN
        
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN state, returning to OPEN")
            self.state = CircuitState.OPEN
            # Exponential backoff with jitter for recovery timeout
            self.current_recovery_timeout = min(
                self.current_recovery_timeout * 2,
                self.max_backoff
            )
            # Add jitter (±20%)
            jitter = random.uniform(0.8, 1.2)
            self.current_recovery_timeout = int(self.current_recovery_timeout * jitter)
            logger.info(f"Circuit breaker '{self.name}' next recovery attempt in {self.current_recovery_timeout}s")
    
    async def _record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        if self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset failure count on success
        
        elif self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(f"Circuit breaker '{self.name}' recorded success "
                       f"({self.success_count}/{self.success_threshold}) in HALF_OPEN state")
    
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """
        Decorator for functions to apply the circuit breaker pattern.
        
        Args:
            func: The async function to wrap with circuit breaker functionality
            
        Returns:
            Wrapped function with circuit breaker logic
        """
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Check and potentially update circuit state
            async with self._lock:
                await self._update_state()
                
                if self.state == CircuitState.OPEN:
                    logger.warning(f"Circuit breaker '{self.name}' is OPEN, failing fast")
                    if self._fallback:
                        try:
                            return await self._fallback(*args, **kwargs)
                        except Exception as e:
                            logger.error(f"Fallback for circuit '{self.name}' also failed: {str(e)}")
                            raise CircuitBreakerError(f"Service '{self.name}' is unavailable and "
                                                     f"fallback failed: {str(e)}")
                    raise CircuitBreakerError(f"Service '{self.name}' is unavailable")
            
            # Execute the function with a timeout
            try:
                # Create a task for the function and wait with a timeout
                task = asyncio.create_task(func(*args, **kwargs))
                result = await asyncio.wait_for(task, timeout=self.timeout)
                
                # Record the success
                async with self._lock:
                    await self._record_success()
                    await self._update_state()
                
                return result
                
            except asyncio.TimeoutError:
                # Handle timeout
                logger.warning(f"Circuit breaker '{self.name}' - operation timed out after {self.timeout}s")
                
                # Record the failure
                async with self._lock:
                    await self._record_failure()
                    await self._update_state()
                
                # Try fallback if available
                if self._fallback:
                    try:
                        logger.info(f"Circuit breaker '{self.name}' - using fallback after timeout")
                        return await self._fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback for circuit '{self.name}' failed: {str(fallback_error)}")
                
                raise CircuitBreakerTimeoutError(f"Operation in '{self.name}' timed out after {self.timeout}s")
                
            except Exception as e:
                # Check if this exception type should be excluded from circuit breaker logic
                if any(isinstance(e, exc_type) for exc_type in self.excluded_exceptions):
                    logger.info(f"Circuit breaker '{self.name}' - excluded exception occurred: {type(e).__name__}")
                    raise  # Re-raise excluded exceptions without affecting circuit state
                
                # Record the failure for all other exceptions
                logger.warning(f"Circuit breaker '{self.name}' - operation failed with error: {str(e)}")
                async with self._lock:
                    await self._record_failure()
                    await self._update_state()
                
                # Try fallback if available
                if self._fallback:
                    try:
                        logger.info(f"Circuit breaker '{self.name}' - using fallback after error")
                        return await self._fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback for circuit '{self.name}' failed: {str(fallback_error)}")
                
                raise CircuitBreakerError(f"Operation in '{self.name}' failed: {str(e)}") from e
        
        return wrapper


# Registry to track and manage circuit breakers across the application
_circuit_registry: Dict[str, CircuitBreaker] = {}

# Define CircuitBreakerRegistry class for compatibility with existing code
class CircuitBreakerRegistry:
    """Registry for managing circuit breakers."""
    
    def __init__(self):
        """Initialize the registry."""
        # The actual registry is module-level so this is just a wrapper
        pass
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return _circuit_registry.get(name)
    
    def get_all_circuit_states(self) -> List[Dict[str, Any]]:
        """Get states of all circuit breakers."""
        states = []
        for name, circuit in _circuit_registry.items():
            states.append({
                'name': name,
                'state': circuit.state.value,
                'failure_count': circuit.failure_count,
                'success_count': circuit.success_count,
                'last_failure_time': circuit.last_failure_time.isoformat() if circuit.last_failure_time else None,
                'recovery_timeout': circuit.current_recovery_timeout,
            })
        return states
    
    def reset(self, name: str) -> bool:
        """Reset a circuit breaker by name."""
        return reset_circuit(name)

# Create a singleton instance for import
circuit_breaker_registry = CircuitBreakerRegistry()


def get_or_create_circuit(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    timeout: float = 30.0,
    success_threshold: int = 3,
    max_backoff: int = 3600,
    excluded_exceptions: Optional[List[type]] = None,
) -> CircuitBreaker:
    """
    Get an existing circuit breaker or create a new one.
    
    Args:
        name: Unique identifier for the circuit breaker
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Seconds to wait before attempting recovery
        timeout: Maximum time in seconds to wait for a response
        success_threshold: Number of successful calls required to close the circuit
        max_backoff: Maximum backoff in seconds
        excluded_exceptions: List of exception types that should not count as failures
        
    Returns:
        The circuit breaker instance
    """
    if name not in _circuit_registry:
        _circuit_registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            timeout=timeout,
            success_threshold=success_threshold,
            max_backoff=max_backoff,
            excluded_exceptions=excluded_exceptions,
        )
    return _circuit_registry[name]


def get_circuit_status() -> Dict[str, Dict[str, Any]]:
    """
    Get the status of all circuit breakers.
    
    Returns:
        Dictionary of circuit breaker states and statistics
    """
    status = {}
    for name, circuit in _circuit_registry.items():
        status[name] = {
            'state': circuit.state.value,
            'failure_count': circuit.failure_count,
            'success_count': circuit.success_count,
            'last_failure_time': circuit.last_failure_time.isoformat() if circuit.last_failure_time else None,
            'recovery_timeout': circuit.current_recovery_timeout,
        }
    return status


def reset_circuit(name: str) -> bool:
    """
    Reset a circuit breaker to its initial state.
    
    Args:
        name: Name of the circuit breaker to reset
        
    Returns:
        True if the circuit was reset, False if it doesn't exist
    """
    if name in _circuit_registry:
        circuit = _circuit_registry[name]
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        circuit.success_count = 0
        circuit.last_failure_time = None
        circuit.current_recovery_timeout = circuit.base_recovery_timeout
        logger.info(f"Circuit breaker '{name}' has been reset")
        return True
    return False


def reset_all_circuits() -> None:
    """Reset all circuit breakers to their initial state."""
    for name in _circuit_registry:
        reset_circuit(name)
    logger.info("All circuit breakers have been reset")


class CircuitBreakerError(Exception):
    """Generic exception for circuit breaker failures."""
    pass


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Exception raised when a circuit breaker operation times out."""
    pass
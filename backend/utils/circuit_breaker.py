"""
Circuit breaker pattern implementation for external API calls.

This module provides a circuit breaker pattern implementation that can be used to
wrap external API calls to prevent cascading failures when services are unavailable.
"""
import time
import logging
import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from functools import wraps

from backend.utils.observability import record_error, metrics_store

logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


class CircuitState(Enum):
    """
    Possible states for the circuit breaker.
    """
    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"  # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service is back online


class CircuitBreaker:
    """
    Implementation of the circuit breaker pattern.
    
    The circuit breaker pattern is used to detect failures and encapsulate the logic
    of preventing a failure from constantly recurring during maintenance, temporary
    external system failure, or unexpected system difficulties.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        fallback_function: Optional[Callable[..., Any]] = None,
    ):
        """
        Initialize a circuit breaker.
        
        Args:
            name: Name of the circuit breaker (used for logging and metrics)
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            fallback_function: Function to call when the circuit is open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback_function = fallback_function
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.lock = threading.RLock()
        
        # Record the creation of this circuit breaker in metrics
        metrics_store.add_error("circuit_breaker_created", f"Circuit breaker '{name}' created")
        logger.info(f"Circuit breaker '{name}' initialized")
    
    def _increment_failure(self) -> None:
        """
        Increment the failure count and open the circuit if threshold is reached.
        """
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                # Trip the circuit open
                if self.state != CircuitState.OPEN:
                    prev_state = self.state
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit '{self.name}' tripped from {prev_state.value} to {self.state.value} "
                        f"after {self.failure_count} failures"
                    )
                    metrics_store.add_error(
                        "circuit_breaker_tripped", 
                        f"Circuit '{self.name}' tripped open after {self.failure_count} failures"
                    )
    
    def _handle_success(self) -> None:
        """
        Handle a successful call by resetting failure count and closing circuit.
        """
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit '{self.name}' closed after successful test request")
                metrics_store.add_error(
                    "circuit_breaker_closed", 
                    f"Circuit '{self.name}' closed after successful test"
                )
                
            self.failure_count = 0
            self.state = CircuitState.CLOSED
    
    def _can_execute(self) -> bool:
        """
        Check if a call can be executed based on the circuit state.
        
        Returns:
            True if the call can proceed, False otherwise
        """
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
                
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if time.time() > self.last_failure_time + self.recovery_timeout:
                    logger.info(
                        f"Circuit '{self.name}' state changed from open to half-open after "
                        f"{self.recovery_timeout} seconds"
                    )
                    metrics_store.add_error(
                        "circuit_breaker_half_open", 
                        f"Circuit '{self.name}' entering half-open state"
                    )
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
                
            elif self.state == CircuitState.HALF_OPEN:
                # In half-open state, only allow one test request
                return True
                
            return False
    
    def execute(self, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute the given function with circuit breaker protection.
        
        Args:
            function: The function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If the circuit is open or the function call fails
        """
        if not self._can_execute():
            logger.warning(f"Circuit '{self.name}' is open, request rejected")
            metrics_store.add_error(
                "circuit_breaker_rejected",
                f"Request rejected by open circuit '{self.name}'"
            )
            
            # If a fallback function is provided, call it
            if self.fallback_function:
                logger.info(f"Circuit '{self.name}' using fallback function")
                return cast(T, self.fallback_function(*args, **kwargs))
            
            raise CircuitBreakerOpenException(
                f"Circuit '{self.name}' is open due to {self.failure_count} consecutive failures"
            )
        
        try:
            # Call the protected function
            result = function(*args, **kwargs)
            self._handle_success()
            return result
        except Exception as e:
            # Record the failure
            self._increment_failure()
            logger.error(f"Circuit '{self.name}' recorded failure: {str(e)}")
            record_error(
                "circuit_breaker_failure", 
                f"Circuit '{self.name}' failure: {e.__class__.__name__} - {str(e)}"
            )
            raise
    
    def __call__(self, function: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to apply circuit breaker to a function.
        
        Example:
            @circuit_breaker
            def api_call():
                pass
        
        Args:
            function: The function to wrap with the circuit breaker
            
        Returns:
            Wrapped function with circuit breaker logic
        """
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(function, *args, **kwargs)
        return wrapper
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the circuit breaker.
        
        Returns:
            Dictionary with state information
        """
        with self.lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "last_failure_time": self.last_failure_time,
                "time_remaining": max(
                    0, 
                    (self.last_failure_time + self.recovery_timeout) - time.time()
                ) if self.state == CircuitState.OPEN else 0
            }


class CircuitBreakerOpenException(Exception):
    """
    Exception raised when a request is rejected due to an open circuit.
    """
    pass


class CircuitBreakerRegistry:
    """
    Registry for all circuit breakers in the application.
    Allows for centralized tracking and management of circuit breakers.
    """
    
    def __init__(self):
        """Initialize the circuit breaker registry."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()
    
    def register(self, circuit_breaker: CircuitBreaker) -> None:
        """
        Register a circuit breaker with the registry.
        
        Args:
            circuit_breaker: The circuit breaker to register
        """
        with self.lock:
            self.circuit_breakers[circuit_breaker.name] = circuit_breaker
            logger.debug(f"Registered circuit breaker: {circuit_breaker.name}")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get a circuit breaker by name.
        
        Args:
            name: The name of the circuit breaker
            
        Returns:
            The circuit breaker, or None if not found
        """
        with self.lock:
            return self.circuit_breakers.get(name)
    
    def create_or_get(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        fallback_function: Optional[Callable[..., Any]] = None,
    ) -> CircuitBreaker:
        """
        Create a new circuit breaker or get an existing one.
        
        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            fallback_function: Function to call when the circuit is open
            
        Returns:
            New or existing circuit breaker
        """
        with self.lock:
            circuit_breaker = self.get(name)
            if not circuit_breaker:
                circuit_breaker = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    fallback_function=fallback_function,
                )
                self.register(circuit_breaker)
            return circuit_breaker
    
    def get_all_circuit_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the state of all registered circuit breakers.
        
        Returns:
            Dictionary mapping circuit breaker names to their states
        """
        with self.lock:
            return {name: cb.get_state() for name, cb in self.circuit_breakers.items()}
    
    def reset(self, name: str) -> bool:
        """
        Reset a circuit breaker to closed state.
        
        Args:
            name: Name of the circuit breaker to reset
            
        Returns:
            True if the circuit was reset, False if not found
        """
        with self.lock:
            circuit_breaker = self.get(name)
            if circuit_breaker:
                with circuit_breaker.lock:
                    circuit_breaker.failure_count = 0
                    circuit_breaker.state = CircuitState.CLOSED
                    logger.info(f"Circuit '{name}' manually reset to closed state")
                    metrics_store.add_error(
                        "circuit_breaker_reset", 
                        f"Circuit '{name}' manually reset"
                    )
                return True
            return False


# Create global registry for circuit breakers
circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    fallback_function: Optional[Callable[..., Any]] = None,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker with the given name.
    
    Args:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Seconds to wait before attempting recovery
        fallback_function: Function to call when the circuit is open
        
    Returns:
        The circuit breaker instance
    """
    return circuit_breaker_registry.create_or_get(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        fallback_function=fallback_function,
    )


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    fallback_function: Optional[Callable[..., Any]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator factory for circuit breaker pattern.
    
    Example:
        @circuit_breaker(name="api_call", failure_threshold=3)
        def api_call():
            pass
    
    Args:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Seconds to wait before attempting recovery
        fallback_function: Function to call when the circuit is open
        
    Returns:
        Decorator that wraps a function with circuit breaker logic
    """
    cb = get_circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        fallback_function=fallback_function,
    )
    
    def decorator(function: Callable[..., T]) -> Callable[..., T]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return cb.execute(function, *args, **kwargs)
        return wrapper
    
    return decorator
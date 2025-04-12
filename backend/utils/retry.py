"""
Retry utility functions for Staples Brain.

This module provides utilities for retrying operations that might fail
due to transient errors.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import TypeVar, Callable, Awaitable, Any, List, Type, Optional, Union, Tuple

logger = logging.getLogger(__name__)

# Type variable for the return type of the function
T = TypeVar('T')


async def with_retry(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    retry_delay: int = 1,
    max_delay: int = 60,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> T:
    """
    Execute an async function with retry logic.
    
    Args:
        func: The async function to execute with retries
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to increase delay on each retry
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exception types to catch and retry
        
    Returns:
        The result of the function
        
    Raises:
        Exception: The last exception caught if all retries fail
    """
    if exceptions is None:
        exceptions = (Exception,)
    
    last_exception = None
    delay = retry_delay
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries} after {delay:.2f}s")
            
            return await func()
            
        except exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.warning(f"All {max_retries} retry attempts failed")
                raise
            
            # Calculate next delay with exponential backoff
            delay = min(delay * backoff_factor, max_delay)
            
            # Add jitter if enabled (±25%)
            if jitter:
                delay = delay * random.uniform(0.75, 1.25)
            
            logger.info(f"Operation failed with error: {str(e)}. Retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
    
    # This shouldn't be reached due to the raise in the loop,
    # but added for type safety
    if last_exception:
        raise last_exception
    raise Exception("Retry failed for unknown reason")


def retry_async(
    max_retries: int = 3,
    retry_delay: int = 1,
    max_delay: int = 60,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for retrying async functions that might fail.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to increase delay on each retry
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exception types to catch and retry
        
    Returns:
        Decorator function that adds retry logic to an async function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async def retry_func() -> T:
                return await func(*args, **kwargs)
            
            return await with_retry(
                retry_func,
                max_retries=max_retries,
                retry_delay=retry_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
                exceptions=exceptions
            )
        
        return wrapper
    
    return decorator
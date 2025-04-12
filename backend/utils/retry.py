"""
Retry utilities for async operations.
Provides functions for retrying operations with exponential backoff.
"""
import logging
import asyncio
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_async(max_attempts=3, base_delay=1, max_delay=10):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        Decorated function that will retry on exceptions
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"Retry {attempt+1}/{max_attempts} after error: {str(e)}. Waiting {delay}s...")
                        await asyncio.sleep(delay)
            
            # If we've exhausted all retries, raise the last exception
            logger.error(f"Function {func.__name__} failed after {max_attempts} attempts")
            raise last_exception
        return wrapper
    return decorator
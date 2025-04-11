import time
from typing import Callable
from functools import wraps

from backend.utils.observability import TimingContext, logger


def track_db_operation(operation: str, table: str):
    """Decorator to track database operations."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TimingContext('db_query', {'operation': operation, 'table': table}):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def track_agent_processing(agent: str):
    """Decorator to track agent processing time."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TimingContext('agent_processing', {'agent': agent}):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def track_llm_request(model: str, endpoint: str):
    """Decorator to track LLM request time."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TimingContext('llm_request', {'model': model, 'endpoint': endpoint}):
                return func(*args, **kwargs)
        return wrapper
    return decorator
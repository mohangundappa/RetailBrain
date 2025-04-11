import time
from typing import Callable
from functools import wraps
from flask import request, Flask, Response, g
from werkzeug.routing import Rule

from backend.utils.observability import record_http_request, TimingContext, logger


class MetricsMiddleware:
    """Middleware to collect HTTP request metrics."""
    
    def __init__(self, app: Flask):
        self.app = app
        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)
    
    def before_request(self):
        """Record the start time of the request."""
        g.start_time = time.time()
        logger.info(f"Request started: {request.method} {request.path}")
    
    def after_request(self, response: Response):
        """Record metrics after the request completes."""
        if hasattr(g, 'start_time'):
            # Calculate request duration
            duration = time.time() - g.start_time
            
            # Get endpoint from the request
            endpoint = self._get_endpoint(request)
            
            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
                latency=duration
            )
            
            logger.info(f"Request completed: {request.method} {endpoint} "
                       f"- Status: {response.status_code} - Duration: {duration:.3f}s")
        
        return response
    
    def _get_endpoint(self, request):
        """Get a standardized endpoint name from the request."""
        # Get the endpoint from the matched route rule
        if request.url_rule:
            # Convert route parameters to placeholders (e.g., /users/123 -> /users/:id)
            endpoint = request.url_rule.rule
            for arg in request.view_args or {}:
                # Replace actual values with parameter placeholders
                if arg in endpoint:
                    endpoint = endpoint.replace(str(request.view_args[arg]), f":{arg}")
            return endpoint
        
        # Fallback to the raw path
        return request.path


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
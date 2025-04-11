import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("staples_brain.log")
    ]
)

logger = logging.getLogger("staples_brain")

# Prometheus metrics
# Request metrics
http_requests_total = Counter(
    'staples_brain_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

request_latency = Histogram(
    'staples_brain_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# LLM metrics
llm_requests_total = Counter(
    'staples_brain_llm_requests_total',
    'Total number of LLM API requests',
    ['model', 'endpoint']
)

llm_request_latency = Histogram(
    'staples_brain_llm_request_latency_seconds',
    'LLM request latency in seconds',
    ['model', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0)
)

llm_token_usage = Counter(
    'staples_brain_llm_token_usage_total',
    'Total number of tokens used in LLM requests',
    ['model', 'type']  # type can be 'prompt' or 'completion'
)

# Intent classification metrics
intent_classification = Counter(
    'staples_brain_intent_classification_total',
    'Total number of intent classifications',
    ['intent', 'confidence_bucket']
)

intent_confidence = Summary(
    'staples_brain_intent_confidence',
    'Confidence scores for intent classification',
    ['intent']
)

# Agent metrics
agent_selection = Counter(
    'staples_brain_agent_selection_total',
    'Total number of agent selections',
    ['agent']
)

agent_processing_time = Histogram(
    'staples_brain_agent_processing_seconds',
    'Agent processing time in seconds',
    ['agent'],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

# System metrics
active_conversations = Gauge(
    'staples_brain_active_conversations',
    'Number of active conversations'
)

db_query_latency = Histogram(
    'staples_brain_db_query_latency_seconds',
    'Database query latency in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

memory_usage = Gauge(
    'staples_brain_memory_usage_bytes',
    'Memory usage in bytes'
)

# In-memory metrics store for the dashboard
class MetricsStore:
    def __init__(self):
        # Time-series data for charts
        self.request_counts = []  # [(timestamp, count), ...]
        self.intent_distributions = {}  # {intent: count, ...}
        self.agent_usage = {}  # {agent: count, ...}
        self.response_times = []  # [(timestamp, latency), ...]
        self.llm_usage = []  # [(timestamp, tokens), ...]
        
        # Recent requests for display
        self.recent_requests = []  # [{timestamp, method, path, status, latency}, ...]
        self.max_recent_requests = 100
        
        # Error tracking
        self.errors = []  # [{timestamp, type, message}, ...]
        self.max_errors = 50
        
        # Start a background thread to clean up old data
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
    
    def add_request(self, method: str, path: str, status: int, latency: float):
        """Add a new request to the metrics store."""
        timestamp = datetime.now()
        
        # Add to time series
        self.request_counts.append((timestamp, 1))
        self.response_times.append((timestamp, latency))
        
        # Add to recent requests
        self.recent_requests.append({
            'timestamp': timestamp,
            'method': method,
            'path': path,
            'status': status,
            'latency': latency
        })
        
        # Trim if needed
        if len(self.recent_requests) > self.max_recent_requests:
            self.recent_requests = self.recent_requests[-self.max_recent_requests:]
    
    def add_intent(self, intent: str, confidence: float):
        """Track intent classifications."""
        if intent in self.intent_distributions:
            self.intent_distributions[intent] += 1
        else:
            self.intent_distributions[intent] = 1
    
    def add_agent_usage(self, agent: str):
        """Track agent usage."""
        if agent in self.agent_usage:
            self.agent_usage[agent] += 1
        else:
            self.agent_usage[agent] = 1
    
    def add_llm_usage(self, tokens: int):
        """Track LLM token usage."""
        self.llm_usage.append((datetime.now(), tokens))
    
    def add_error(self, error_type: str, message: str):
        """Track errors."""
        self.errors.append({
            'timestamp': datetime.now(),
            'type': error_type,
            'message': message
        })
        
        # Trim if needed
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of metrics for the dashboard."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Count requests in the last hour
        recent_requests = sum(1 for t, _ in self.request_counts if t >= one_hour_ago)
        
        # Average response time in the last hour
        recent_latencies = [lat for t, lat in self.response_times if t >= one_hour_ago]
        avg_latency = sum(recent_latencies) / len(recent_latencies) if recent_latencies else 0
        
        # Total LLM tokens in the last hour
        recent_tokens = sum(tokens for t, tokens in self.llm_usage if t >= one_hour_ago)
        
        # Top intents and agents
        top_intents = sorted(self.intent_distributions.items(), key=lambda x: x[1], reverse=True)[:5]
        top_agents = sorted(self.agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent errors count
        recent_errors = sum(1 for e in self.errors if e['timestamp'] >= one_hour_ago)
        
        return {
            'timestamp': now.isoformat(),
            'requests_last_hour': recent_requests,
            'avg_latency': avg_latency,
            'llm_tokens_last_hour': recent_tokens,
            'top_intents': top_intents,
            'top_agents': top_agents,
            'recent_errors': recent_errors,
            'recent_requests': self.recent_requests[-10:],  # Last 10 requests
            'recent_errors_list': self.errors[-10:]  # Last 10 errors
        }
    
    def _cleanup_old_data(self):
        """Clean up data older than 24 hours."""
        while True:
            time.sleep(3600)  # Run every hour
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            
            # Clean up time series data
            self.request_counts = [(t, c) for t, c in self.request_counts if t >= day_ago]
            self.response_times = [(t, l) for t, l in self.response_times if t >= day_ago]
            self.llm_usage = [(t, tokens) for t, tokens in self.llm_usage if t >= day_ago]


# Create a global metrics store
metrics_store = MetricsStore()

# Timing context manager
class TimingContext:
    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # Log the duration
        logger.debug(f"{self.name} completed in {duration:.3f} seconds")
        
        # Record different metrics based on the context
        if self.name == 'http_request':
            method = self.labels.get('method', 'unknown')
            endpoint = self.labels.get('endpoint', 'unknown')
            request_latency.labels(method=method, endpoint=endpoint).observe(duration)
        
        elif self.name == 'llm_request':
            model = self.labels.get('model', 'unknown')
            endpoint = self.labels.get('endpoint', 'unknown')
            llm_request_latency.labels(model=model, endpoint=endpoint).observe(duration)
        
        elif self.name == 'agent_processing':
            agent = self.labels.get('agent', 'unknown')
            agent_processing_time.labels(agent=agent).observe(duration)
        
        elif self.name == 'db_query':
            operation = self.labels.get('operation', 'unknown')
            table = self.labels.get('table', 'unknown')
            db_query_latency.labels(operation=operation, table=table).observe(duration)


# Function to get Prometheus metrics
def get_prometheus_metrics():
    """Get the latest Prometheus metrics."""
    return generate_latest(), CONTENT_TYPE_LATEST


# Initialize memory usage monitoring
def start_memory_monitoring(interval: int = 60):
    """Start monitoring memory usage at the given interval (in seconds)."""
    def _monitor_memory():
        while True:
            try:
                # This is a simple approach that works on most systems
                # For more accurate measurements, you might want to use a library like psutil
                import os
                import psutil
                
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_usage.set(memory_info.rss)  # Resident Set Size in bytes
                
            except Exception as e:
                logger.error(f"Error monitoring memory: {str(e)}")
            
            time.sleep(interval)
    
    threading.Thread(target=_monitor_memory, daemon=True).start()


# Function to record HTTP request metrics
def record_http_request(method: str, endpoint: str, status: int, latency: float):
    """Record metrics for an HTTP request."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    
    # Also add to the metrics store
    metrics_store.add_request(method, endpoint, status, latency)


# Function to record API calls
def log_api_call(api_name: str, endpoint: str, method: str, status_code: int, duration: float, error: Optional[str] = None):
    """
    Record metrics for an API call.
    
    Args:
        api_name: Name of the API service
        endpoint: API endpoint path
        method: HTTP method used
        status_code: HTTP status code received
        duration: Request duration in seconds
        error: Optional error message if the request failed
    """
    # Log the API call
    if error:
        logger.error(f"API call to {api_name}/{endpoint} failed: {error}")
    else:
        logger.debug(f"API call to {api_name}/{endpoint} completed in {duration:.3f}s with status {status_code}")
    
    # Record as HTTP request for metrics
    record_http_request(method, f"{api_name}/{endpoint}", status_code, duration)
    
    # If there was an error, record it
    if error:
        record_error("api_error", f"{api_name}/{endpoint}: {error}")
        
    # Store the metrics in the API specific counter/histogram if needed
    # This could be extended to create API-specific metrics


# Function to record intent classification
def record_intent_classification(intent: str, confidence: float):
    """Record metrics for intent classification."""
    # Define confidence buckets
    if confidence < 0.3:
        bucket = "low"
    elif confidence < 0.7:
        bucket = "medium"
    else:
        bucket = "high"
    
    intent_classification.labels(intent=intent, confidence_bucket=bucket).inc()
    intent_confidence.labels(intent=intent).observe(confidence)
    
    # Also add to the metrics store
    metrics_store.add_intent(intent, confidence)


# Function to record agent selection
def record_agent_selection(agent: str):
    """Record metrics for agent selection."""
    agent_selection.labels(agent=agent).inc()
    
    # Also add to the metrics store
    metrics_store.add_agent_usage(agent)


# Function to record LLM usage
def record_llm_request(model: str, endpoint: str, prompt_tokens: int, completion_tokens: int):
    """Record metrics for an LLM request."""
    llm_requests_total.labels(model=model, endpoint=endpoint).inc()
    llm_token_usage.labels(model=model, type="prompt").inc(prompt_tokens)
    llm_token_usage.labels(model=model, type="completion").inc(completion_tokens)
    
    # Also add to the metrics store
    metrics_store.add_llm_usage(prompt_tokens + completion_tokens)


# Function to record errors
def record_error(error_type: str, message: str):
    """Record an error."""
    logger.error(f"{error_type}: {message}")
    
    # Add to the metrics store
    metrics_store.add_error(error_type, message)


# Function to update active conversations
def update_active_conversations(count: int):
    """Update the number of active conversations."""
    active_conversations.set(count)


# Function to get metrics summary for the dashboard
def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of metrics for the dashboard."""
    return metrics_store.get_metrics_summary()


# Function to initialize external telemetry services
def initialize_external_telemetry():
    """Initialize connections to external telemetry services."""
    # Initialize Databricks telemetry
    try:
        from backend.utils.databricks_utils import get_databricks_client, get_or_create_experiment
        client = get_databricks_client()
        if client:
            experiment = get_or_create_experiment()
            if experiment:
                logger.info(f"Databricks telemetry initialized with experiment: {experiment.name}")
            else:
                logger.warning("Failed to create or retrieve Databricks experiment")
    except Exception as e:
        logger.warning(f"Failed to initialize Databricks telemetry: {str(e)}")
    
    # Initialize LangSmith telemetry
    try:
        import backend.utils.langsmith_utils as langsmith_utils
        client = langsmith_utils.get_langsmith_client()
        if client:
            tracer = langsmith_utils.get_langchain_tracer()
            if tracer:
                logger.info("LangSmith telemetry initialized")
            else:
                logger.warning("Failed to create LangChain tracer")
    except Exception as e:
        logger.warning(f"Failed to initialize LangSmith telemetry: {str(e)}")


# Initial setup
def initialize():
    """Initialize all observability components."""
    # Start resource monitoring
    start_memory_monitoring()
    
    # Initialize external telemetry
    initialize_external_telemetry()
    
    logger.info("Observability module initialized")


# Auto-initialize on import
initialize()
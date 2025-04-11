"""
Databricks integration utilities for Staples Brain observability.

This module provides utilities for integrating with Databricks for ML monitoring,
feature storage, and experiment tracking.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps
from datetime import datetime

from databricks.sdk import WorkspaceClient

logger = logging.getLogger("staples_brain")

# Check if Databricks access information is available
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
DATABRICKS_EXPERIMENT = os.environ.get("DATABRICKS_EXPERIMENT", "/Shared/staples-brain")

# Keep Databricks integration disabled for now
databricks_enabled = False  # Disabled as requested

# Global Databricks client
_databricks_client = None

def get_databricks_client() -> Optional[WorkspaceClient]:
    """Get or create a Databricks client."""
    global _databricks_client
    
    if not databricks_enabled:
        return None
    
    if _databricks_client is None:
        try:
            _databricks_client = WorkspaceClient(
                host=DATABRICKS_HOST,
                token=DATABRICKS_TOKEN
            )
            logger.info("Databricks client initialized")
        except Exception as e:
            logger.error(f"Error initializing Databricks client: {str(e)}")
            return None
    
    return _databricks_client

def get_or_create_experiment(experiment_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get or create a Databricks experiment tracking information.
    
    Args:
        experiment_path: The path to the experiment, defaults to DATABRICKS_EXPERIMENT
        
    Returns:
        A dictionary with experiment info if successful, None otherwise
    """
    if not databricks_enabled:
        return None
    
    client = get_databricks_client()
    if not client:
        return None
    
    experiment_path = experiment_path or DATABRICKS_EXPERIMENT
    
    try:
        # In newer SDK versions, we don't need ML experiment API
        # Instead, we'll just create a simple tracking object
        experiment = {
            "name": experiment_path,
            "experiment_id": experiment_path.replace("/", "_").strip("_"),
            "workspace_url": DATABRICKS_HOST
        }
        
        logger.info(f"Using Databricks tracking at: {experiment_path}")
        return experiment
    except Exception as e:
        logger.error(f"Error setting up Databricks tracking: {str(e)}")
        return None

def log_to_databricks(
    metrics: Optional[Dict[str, float]] = None,
    params: Optional[Dict[str, str]] = None,
    tags: Optional[Dict[str, str]] = None,
    experiment_path: Optional[str] = None
) -> Callable:
    """
    Decorator to log function execution to Databricks.
    
    Args:
        metrics: Metrics to log
        params: Parameters to log
        tags: Tags to log
        experiment_path: The path to the experiment, defaults to DATABRICKS_EXPERIMENT
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not databricks_enabled:
                return func(*args, **kwargs)
            
            client = get_databricks_client()
            if not client:
                return func(*args, **kwargs)
            
            # Get or create the experiment
            experiment = get_or_create_experiment(experiment_path)
            if not experiment:
                return func(*args, **kwargs)
            
            # For now we'll just log the execution but not send metrics to Databricks
            # as the ML module is not available in this version of the SDK
            try:
                # Call the function
                start_time = datetime.utcnow()
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    error = str(e)
                    success = False
                    raise
                finally:
                    # Calculate execution time
                    end_time = datetime.utcnow()
                    execution_time = (end_time - start_time).total_seconds()
                    
                    # Log metrics locally
                    all_metrics = metrics.copy() if metrics else {}
                    all_metrics["execution_time"] = execution_time
                    if success is not None:
                        all_metrics["success"] = 1.0 if success else 0.0
                    
                    # Log parameters locally
                    all_params = params.copy() if params else {}
                    all_params["function"] = func.__name__
                    
                    # Log execution locally
                    logger.info(f"Databricks tracking: {func.__name__} executed in {execution_time:.3f}s, success={success}")
                    
                    # If we got this far and succeeded, return the result
                    if success:
                        return result
            except Exception as e:
                logger.error(f"Error logging to Databricks: {str(e)}")
                # Fall back to just calling the function
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def log_agent_metrics(
    agent_name: str,
    confidence: float,
    execution_time: float,
    success: bool,
    additional_metrics: Optional[Dict[str, float]] = None,
    experiment_path: Optional[str] = None
) -> Optional[str]:
    """
    Log agent metrics to Databricks ML Tracking.
    
    Args:
        agent_name: The name of the agent
        confidence: The confidence score of the agent
        execution_time: The execution time in seconds
        success: Whether the agent execution was successful
        additional_metrics: Additional metrics to log
        experiment_path: The path to the experiment, defaults to DATABRICKS_EXPERIMENT
        
    Returns:
        The run ID if logging was successful, None otherwise
    """
    if not databricks_enabled:
        return None
    
    client = get_databricks_client()
    if not client:
        return None
    
    # Get or create the experiment
    experiment = get_or_create_experiment(experiment_path)
    if not experiment:
        return None
    
    try:
        # Start a run
        with client.ml.start_run(experiment_id=experiment.experiment_id) as run:
            # Log metrics
            metrics = {
                "confidence": confidence,
                "execution_time": execution_time,
                "success": 1.0 if success else 0.0
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            for metric_name, metric_value in metrics.items():
                client.ml.log_metric(run_id=run.info.run_id, key=metric_name, value=metric_value)
            
            # Log parameters
            params = {
                "agent": agent_name
            }
            
            for param_name, param_value in params.items():
                client.ml.log_param(run_id=run.info.run_id, key=param_name, value=str(param_value))
            
            # Log tags
            tags = {
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for tag_name, tag_value in tags.items():
                client.ml.set_tag(run_id=run.info.run_id, key=tag_name, value=str(tag_value))
            
            return run.info.run_id
    except Exception as e:
        logger.error(f"Error logging agent metrics to Databricks: {str(e)}")
        return None

def log_llm_metrics(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    execution_time: float,
    success: bool,
    additional_metrics: Optional[Dict[str, float]] = None,
    experiment_path: Optional[str] = None
) -> Optional[str]:
    """
    Log LLM metrics to Databricks ML Tracking.
    
    Args:
        model: The name of the LLM model
        prompt_tokens: The number of prompt tokens
        completion_tokens: The number of completion tokens
        execution_time: The execution time in seconds
        success: Whether the LLM call was successful
        additional_metrics: Additional metrics to log
        experiment_path: The path to the experiment, defaults to DATABRICKS_EXPERIMENT
        
    Returns:
        The run ID if logging was successful, None otherwise
    """
    if not databricks_enabled:
        return None
    
    client = get_databricks_client()
    if not client:
        return None
    
    # Get or create the experiment
    experiment = get_or_create_experiment(experiment_path)
    if not experiment:
        return None
    
    try:
        # Start a run
        with client.ml.start_run(experiment_id=experiment.experiment_id) as run:
            # Log metrics
            metrics = {
                "prompt_tokens": float(prompt_tokens),
                "completion_tokens": float(completion_tokens),
                "total_tokens": float(prompt_tokens + completion_tokens),
                "execution_time": execution_time,
                "tokens_per_second": float(prompt_tokens + completion_tokens) / execution_time if execution_time > 0 else 0,
                "success": 1.0 if success else 0.0
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            for metric_name, metric_value in metrics.items():
                client.ml.log_metric(run_id=run.info.run_id, key=metric_name, value=metric_value)
            
            # Log parameters
            params = {
                "model": model
            }
            
            for param_name, param_value in params.items():
                client.ml.log_param(run_id=run.info.run_id, key=param_name, value=str(param_value))
            
            # Log tags
            tags = {
                "model": model,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "llm"
            }
            
            for tag_name, tag_value in tags.items():
                client.ml.set_tag(run_id=run.info.run_id, key=tag_name, value=str(tag_value))
            
            return run.info.run_id
    except Exception as e:
        logger.error(f"Error logging LLM metrics to Databricks: {str(e)}")
        return None

def log_intent_metrics(
    intent: str,
    confidence: float,
    execution_time: float,
    additional_metrics: Optional[Dict[str, float]] = None,
    experiment_path: Optional[str] = None
) -> Optional[str]:
    """
    Log intent classification metrics to Databricks ML Tracking.
    
    Args:
        intent: The identified intent
        confidence: The confidence score
        execution_time: The execution time in seconds
        additional_metrics: Additional metrics to log
        experiment_path: The path to the experiment, defaults to DATABRICKS_EXPERIMENT
        
    Returns:
        The run ID if logging was successful, None otherwise
    """
    if not databricks_enabled:
        return None
    
    client = get_databricks_client()
    if not client:
        return None
    
    # Get or create the experiment
    experiment = get_or_create_experiment(experiment_path)
    if not experiment:
        return None
    
    try:
        # Start a run
        with client.ml.start_run(experiment_id=experiment.experiment_id) as run:
            # Log metrics
            metrics = {
                "confidence": confidence,
                "execution_time": execution_time
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            for metric_name, metric_value in metrics.items():
                client.ml.log_metric(run_id=run.info.run_id, key=metric_name, value=metric_value)
            
            # Log parameters
            params = {
                "intent": intent
            }
            
            for param_name, param_value in params.items():
                client.ml.log_param(run_id=run.info.run_id, key=param_name, value=str(param_value))
            
            # Log tags
            tags = {
                "intent": intent,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "intent"
            }
            
            for tag_name, tag_value in tags.items():
                client.ml.set_tag(run_id=run.info.run_id, key=tag_name, value=str(tag_value))
            
            return run.info.run_id
    except Exception as e:
        logger.error(f"Error logging intent metrics to Databricks: {str(e)}")
        return None

# Initialize Databricks client if possible
if databricks_enabled:
    get_databricks_client()
    get_or_create_experiment()
else:
    logger.warning("Databricks integration disabled: DATABRICKS_HOST and/or DATABRICKS_TOKEN not found")
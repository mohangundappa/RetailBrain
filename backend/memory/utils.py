"""
Utility functions for the mem0 memory system.

This module provides helper functions and utilities
for memory operations, including serialization, search,
and data manipulation.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

def serialize_datetime(dt: datetime) -> str:
    """
    Serialize a datetime object to ISO format string.
    
    Args:
        dt: Datetime object
        
    Returns:
        ISO format string
    """
    return dt.isoformat() if dt else None


def deserialize_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Deserialize an ISO format string to a datetime object.
    
    Args:
        dt_str: ISO format datetime string
        
    Returns:
        Datetime object or None
    """
    if not dt_str:
        return None
        
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Error deserializing datetime {dt_str}: {str(e)}")
        return None


def safe_json_dumps(obj: Any) -> str:
    """
    Safely convert an object to a JSON string,
    handling datetime objects and other special types.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON string
    """
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return serialize_datetime(o)
            return super().default(o)
    
    return json.dumps(obj, cls=DateTimeEncoder)


def safe_json_loads(json_str: str) -> Any:
    """
    Safely parse a JSON string.
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed object
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return None


def compute_memory_key(prefix: str, memory_type: str, identifier: str) -> str:
    """
    Compute a memory key for Redis storage.
    
    Args:
        prefix: Key prefix
        memory_type: Type of memory
        identifier: Unique identifier
        
    Returns:
        Redis key
    """
    return f"{prefix}:{memory_type}:{identifier}"


def compute_expiry_time(ttl: Optional[int]) -> Optional[datetime]:
    """
    Compute an expiry time based on TTL.
    
    Args:
        ttl: Time-to-live in seconds (None for no expiration)
        
    Returns:
        Expiry datetime or None
    """
    if ttl is None:
        return None
        
    return datetime.utcnow() + ttl
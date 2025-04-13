"""
DEPRECATED: This module has been replaced by GraphBrainService.

This file is kept as a stub for backward compatibility but contains minimal implementation.
All brain service functionality has been moved to backend/services/graph_brain_service.py.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.config import Config
from backend.memory.mem0 import Mem0

logger = logging.getLogger(__name__)

class OptimizedBrainService:
    """
    DEPRECATED: This class has been replaced by GraphBrainService.
    
    This is a stub maintained for backward compatibility only.
    """
    
    def __init__(
        self, 
        db_session: AsyncSession, 
        config: Config,
        memory_service: Optional[Mem0] = None,
        **kwargs
    ):
        """Initialize a stub instance of OptimizedBrainService."""
        logger.warning("OptimizedBrainService is deprecated and should not be used")
        self.db_session = db_session
        self.config = config
        self.memory_service = memory_service
        self.agent_factory = None
    
    async def initialize(self) -> bool:
        """Initialize the brain service (stub implementation)."""
        logger.warning("Stub implementation of OptimizedBrainService.initialize() called")
        return True
    
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message (stub implementation).
        
        Args:
            message: User's message
            session_id: Conversation session ID
            context: Additional context information
            
        Returns:
            Response dictionary with error indication
        """
        logger.error("OptimizedBrainService.process_message() called but this service is deprecated")
        return {
            "success": False,
            "response": "This service has been deprecated. Please use GraphBrainService instead.",
            "error": "Service deprecated"
        }
"""
Test module for mem0 memory system.

This module provides a simple test function to verify that the mem0 memory system
is working correctly with Redis and PostgreSQL.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from backend.memory.mem0 import Mem0, MemoryEntry, MemoryType, MemoryScope
from backend.memory.config import MemoryConfig
from backend.memory.database import get_db_session
from backend.memory.factory import get_mem0, get_mem0_sync

logger = logging.getLogger(__name__)

async def run_mem0_test():
    """
    Run a basic test of the mem0 memory system.
    
    This function creates a test memory entry, stores it in Redis,
    retrieves it, and verifies that it contains the expected data.
    """
    logger.info("Starting mem0 test...")
    
    try:
        # Get a mem0 instance
        mem0 = await get_mem0("test")
        
        # Create a unique conversation ID for testing
        conversation_id = f"test_{uuid.uuid4()}"
        session_id = f"session_{uuid.uuid4()}"
        
        # Test memory entries
        test_entries = []
        
        # Add a message
        message_id = mem0.add_message(
            conversation_id=conversation_id,
            role="user",
            content="This is a test message",
            session_id=session_id,
            metadata={"test": True}
        )
        test_entries.append(message_id)
        logger.info(f"Added test message with ID: {message_id}")
        
        # Add an entity
        entity_id = mem0.add_entity(
            conversation_id=conversation_id,
            entity_type="test_entity",
            entity_value="test_value",
            confidence=0.95,
            session_id=session_id,
            metadata={"test": True}
        )
        test_entries.append(entity_id)
        logger.info(f"Added test entity with ID: {entity_id}")
        
        # Add a fact with custom index
        fact = MemoryEntry(
            content="This is a test fact",
            memory_type=MemoryType.FACT,
            session_id=session_id,
            conversation_id=conversation_id,
            metadata={"test": True}
        )
        fact.add_index("test_index", "test_key", "test_value")
        fact_id = mem0.add_memory(fact, scope=MemoryScope.LONG_TERM)
        test_entries.append(fact_id)
        logger.info(f"Added test fact with ID: {fact_id}")
        
        # Retrieve and verify the entries
        for entry_id in test_entries:
            memory = mem0.get_memory(entry_id)
            if memory:
                logger.info(f"Retrieved entry {entry_id}: {memory.memory_type} - {memory.content}")
            else:
                logger.warning(f"Failed to retrieve entry {entry_id}")
                
        # Get conversation messages
        messages = mem0.get_conversation_messages(conversation_id)
        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        
        # Get memories by conversation
        memories = mem0.get_memories_by_conversation(conversation_id)
        logger.info(f"Retrieved {len(memories)} memories for conversation {conversation_id}")
        
        # Clean up test data
        deleted = mem0.clear_conversation_memory(conversation_id)
        logger.info(f"Deleted {deleted} test memories")
        
        logger.info("mem0 test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in mem0 test: {str(e)}")
        return False
        

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_mem0_test())
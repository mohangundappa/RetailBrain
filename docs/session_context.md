# Session Context Management

## Overview

The Staples Brain system implements a robust session context management system to track conversation state across multiple user interactions. This allows agents to maintain context awareness and provide consistent, coherent responses throughout a conversation.

## API Integration

Session context is managed through the API layer with these components:

### Request Context Format

```json
{
  "message": "I need to reset my password",
  "session_id": "user-123-session",
  "context": {
    "customer_id": "cust-456",
    "previous_agents": ["general_conversation"],
    "entity_memory": {
      "email": "user@example.com"
    },
    "workflow_state": {
      "current_step": "validate_email",
      "steps_completed": ["request_email"]
    }
  }
}
```

### Context Models

The system uses well-defined Pydantic models for context handling:

```python
class ChatContext(BaseModel):
    """Context information for chat processing"""
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    previous_agents: Optional[List[str]] = Field(None, description="Previously used agents")
    entity_memory: Optional[Dict[str, Any]] = Field(None, description="Entity memory")
    workflow_state: Optional[Dict[str, Any]] = Field(None, description="Workflow state")
    
class IdentityContext(BaseModel):
    """Identity information within chat context"""
    user_id: Optional[str] = Field(None, description="User identifier")
    email: Optional[str] = Field(None, description="User email address")
    roles: Optional[List[str]] = Field(None, description="User roles")
```

## Memory Types

The system supports multiple types of memory through the mem0 memory service:

| Memory Type | Purpose | Storage | Scope |
|-------------|---------|---------|-------|
| `MESSAGE` | Track user-agent exchanges | Database | Session |
| `ENTITY` | Remember identified entities | Database + Redis | Session, Cross-session |
| `FACT` | Store extracted information | Database | Cross-session |
| `CONTEXT` | Store contextual information | Database | Session |
| `SUMMARY` | Store conversation summaries | Database | Session |
| `INSTRUCTION` | Store system instructions | Database | Session |

## Memory Scope

Memory entries can be stored with different scopes:

```python
class MemoryScope(str, Enum):
    """Scope of memory storage."""
    WORKING = "working"           # Very short-term, active processing
    SHORT_TERM = "short_term"     # Recent conversation context
    LONG_TERM = "long_term"       # Persistent knowledge
```

## Implementation

### Memory Service

The memory service provides a unified interface for storing and retrieving memory entries:

```python
async def get_memory_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config)
) -> Any:
    """
    Get or create a memory service instance.
    Uses a singleton pattern to ensure only one instance exists.
    """
    global _memory_service
    
    try:
        if _memory_service is None:
            logger.info("Initializing memory service (mem0)")
            
            # Create memory config with default settings
            memory_config = MemoryConfig(
                use_fakeredis=True,  # Use fakeredis for development and testing
                db_url=str(db.bind.url)  # Get database URL from current session
            )
            
            # Initialize memory service
            _memory_service = await create_memory_service(memory_config)
            logger.info("Memory service (mem0) initialization complete")
            
        return _memory_service
    except Exception as e:
        logger.error(f"Failed to initialize memory service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Memory service initialization failed"
        )
```

### Database Schema

Memory entries are stored in a structured database schema:

```python
class MemoryEntryModel(Base):
    """
    Core memory entry model for mem0 system.
    
    This model represents the fundamental memory storage unit,
    with specialized memory types differentiated by the memory_type field.
    """
    __tablename__ = "memory_entry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Organizational fields
    memory_type = Column(String(32), nullable=False, index=True)  # 'message', 'fact', 'entity', etc.
    memory_scope = Column(String(32), nullable=False, index=True)  # 'working', 'short_term', 'long_term'
    source = Column(String(32), nullable=False, index=True)  # 'user', 'system', 'agent', etc.
    
    # Content fields
    content = Column(Text, nullable=False)  # Actual memory content
    content_embedding = Column(Vector(1536), nullable=True)  # Vector embedding for semantic search
    
    # Metadata fields
    metadata = Column(JSONB, nullable=True)  # Additional structured data
    
    # Conversation tracking
    session_id = Column(String(64), nullable=False, index=True)  # Conversation session identifier
    conversation_id = Column(String(64), nullable=True, index=True)  # Extended conversation identifier
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.now)
    
    # Relationship to context entries
    contexts = relationship("MemoryContextModel", back_populates="entry", cascade="all, delete-orphan")
```

### Context Model

Additional context information can be associated with memory entries:

```python
class MemoryContextModel(Base):
    """
    Context information associated with memory entries.
    
    Provides additional structured context for memory entries,
    such as entity relationships, attributions, or source information.
    """
    __tablename__ = "memory_context"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("memory_entry.id", ondelete="CASCADE"), nullable=False)
    
    # Context type and data
    context_type = Column(String(32), nullable=False, index=True)  # 'source', 'relation', 'attribution', etc.
    data = Column(JSONB, nullable=False)
    
    # Relationship
    entry = relationship("MemoryEntryModel", back_populates="contexts")
```

## Session State Management

In addition to general memory management, the system also provides specific support for workflow state persistence:

```python
class StatePersistenceManager:
    """
    Manager for persisting and recovering conversation state.
    
    This class provides methods for saving and loading conversation state
    to and from the database, with robust error handling and retry logic.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the state persistence manager.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
    
    async def persist_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Persist conversation state to the database.
        
        Args:
            session_id: Session identifier
            state: Conversation state
            
        Returns:
            Success status
        """
        try:
            # Create or update state record
            # Implementation details...
            
            return True
        except Exception as e:
            logger.error(f"Failed to persist state: {str(e)}", exc_info=True)
            return False
    
    async def recover_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover conversation state from the database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Recovered state or None if not found
        """
        try:
            # Retrieve state record
            # Implementation details...
            
            return state
        except Exception as e:
            logger.error(f"Failed to recover state: {str(e)}", exc_info=True)
            return None
```

## Best Practices

1. **Session Management**
   - Use consistent session_id format across all API calls
   - Include relevant context in each request
   - Maintain entity memory across session turns

2. **Entity Memory**
   - Extract and store entities from user messages
   - Reference entities in follow-up turns
   - Update entity values when new information is provided

3. **Workflow State**
   - Track current step in multi-turn workflows
   - Persist completed steps to allow resuming
   - Store workflow-specific variables in state

4. **Error Handling**
   - Implement robust recovery from state persistence failures
   - Provide graceful fallbacks when context is lost
   - Log context usage for debugging purposes

## Troubleshooting

| Issue | Possible Cause | Resolution |
|-------|----------------|------------|
| Context lost between turns | Incorrect session_id | Ensure consistent session_id usage |
| Entity values not retained | Missing entity memory | Check entity extraction and storage |
| Workflow steps repeated | State persistence failure | Verify database connections and error handling |
| Poor context awareness | Insufficient memory scope | Adjust memory retention settings |
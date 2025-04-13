# mem0 Memory System

The mem0 memory system is a high-performance memory management system designed for Staples Brain agents. It provides multi-level memory storage with both Redis and PostgreSQL backends.

## Key Features

- **Multi-level Memory Storage**: Working memory (5-min TTL), short-term memory (1-hour TTL), and long-term memory (persistent)
- **Dual Storage Backend**: Redis for high-speed, in-memory storage and PostgreSQL for long-term archival
- **Semantic Search**: Vector-based memory retrieval for related content
- **Memory Importance and Decay**: Memory entries have importance factors and automatic expiration
- **Efficient Indexing**: Multiple indexing strategies for fast retrieval
- **Fallback Mechanisms**: FakeRedis support for development and testing without Redis

## Memory Entry Types

- **Message**: Conversation messages (user, assistant, system)
- **Fact**: Extracted facts from conversations
- **Entity**: Recognized entities (tracking numbers, products, etc.)
- **Context**: Context information for agent processing
- **Summary**: Conversation summaries
- **Instruction**: System instructions

## Technical Design

### Storage Tiers

1. **Working Memory (Redis)**: Very short-term, active processing memory with a 5-minute TTL
2. **Short-term Memory (Redis)**: Recent conversation context with a 1-hour TTL
3. **Long-term Memory (PostgreSQL)**: Persistent knowledge stored in the database

### Architecture Components

- **MemoryEntry**: Core data structure for memory items
- **Mem0**: Central implementation of the memory system
- **MemoryConfig**: Configuration settings and environment management
- **Factory**: Factory pattern for memory system access
- **Schema**: Database schema for PostgreSQL storage

## Usage Examples

### Adding a Message

```python
from backend.memory.factory import get_mem0_sync

mem0 = get_mem0_sync()
mem0.add_message(
    conversation_id="conv123",
    role="user",
    content="Where is my order?",
    session_id="session456"
)
```

### Retrieving Conversation Context

```python
messages = mem0.get_conversation_messages(conversation_id="conv123")
```

### Adding an Entity

```python
mem0.add_entity(
    conversation_id="conv123",
    entity_type="tracking_number",
    entity_value="1Z999AA10123456784",
    confidence=0.95,
    session_id="session456"
)
```

## System Requirements

- **Redis**: For high-speed memory operations (FakeRedis available as fallback)
- **PostgreSQL**: For long-term storage and vector search
- **Python 3.10+**: For async/await support

## Environment Configuration

The memory system can be configured via environment variables or directly in the code:

- `REDIS_URL`: Redis connection URL (default: `fakeredis://mem0:0`)
- `WORKING_MEMORY_TTL`: Working memory TTL in seconds (default: 300)
- `SHORT_TERM_MEMORY_TTL`: Short-term memory TTL in seconds (default: 3600)
- `LONG_TERM_MEMORY_TTL`: Long-term memory TTL (default: None, no expiration)
- `USE_DATABASE_STORAGE`: Whether to use PostgreSQL storage (default: true)
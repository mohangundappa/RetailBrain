# Staples Brain Test Suite

This directory contains tests for the Staples Brain and its components.

## Test Organization

The tests are organized into several categories:

1. **Import Tests** (`test_imports.py`): Verify that all required dependencies are available.
2. **Agent Selection Tests** (`test_agent_interactions.py::TestAgentSelection`): Test basic agent selection capabilities.
3. **Agent Context Switching Tests** (`test_agent_interactions.py::TestAgentContextSwitching`): Test context switching between agents.
4. **Complex Conversation Flow Tests** (`test_conversation_flow.py`): Test complex, multi-turn conversations.
5. **Agent Routing Tests** (`test_agent_routing.py`): Test the routing mechanisms that select appropriate agents.

## Running Tests

To run all tests:

```bash
python tests/run_agent_tests.py
```

To run a specific category of tests:

```bash
python tests/run_agent_tests.py -t [imports|selection|context|flow|routing]
```

To run tests with more verbose output:

```bash
python tests/run_agent_tests.py -v
```

## Testing Considerations

### Mock LLM Implementation

Testing LangChain components requires a proper mock for the BaseChatModel class. A simple 
MagicMock is insufficient because LangChain expects methods with specific signatures and return types.

The `test_utils.py` module provides a `MockChatModel` class that extends `BaseChatModel` with 
appropriate methods for testing. Key considerations:

1. **Standard LangChain Methods**: The mock must implement `_generate`, `_agenerate`, and `_llm_type` methods.
2. **Message Structure**: Return values must have the proper message structure (AIMessageChunk, ChatGenerationChunk, ChatResult).
3. **Confidence Scoring**: For `can_handle` tests, the mock should return a numeric confidence score.
4. **Response Formats**: Regular responses may need to be in JSON format for entity extraction.
5. **Async Safety**: Avoid using `asyncio.run()` inside `_generate` to prevent "asyncio.run() cannot be called from a running event loop" errors.

### Example Mocking

To properly mock the LLM in a test:

```python
from tests.test_utils import create_mock_chat_model, patch_llm_in_brain

# Initialize the brain
brain = initialize_staples_brain()

# Create and patch the mock LLM
mock_llm = create_mock_chat_model(responses=[
    "0.9",  # Confidence score
    '{"entity": "value"}',  # Entity extraction response
    "Final human-readable response",  # Final response
])
patch_llm_in_brain(brain, mock_llm)
```

### Common Testing Issues

1. **Circular imports**: Import test utilities inside test methods to avoid circular imports.
2. **AsyncIO conflicts**: Be careful when mixing asyncio calls with testing, avoid nested event loops.
3. **Patching depth**: When patching, remember to patch deep enough to replace all instances of the LLM in chains.

## Test Data

The test suite uses synthetic data for testing. In a production environment, consider:

1. Using sanitized, realistic data for more thorough testing
2. Implementing integration tests with actual LLM services (with appropriate API keys)
3. Setting up continuous monitoring to catch issues in production
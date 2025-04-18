# Supervisor-Based Architecture

## Overview

The Staples Brain system has evolved to use a database-driven supervisor architecture for agent orchestration. This approach provides greater flexibility, configurability, and extensibility compared to the previous hardcoded graph approach.

## Key Components

| Component | Description |
|-----------|-------------|
| **SupervisorBrainService** | Core service managing the LangGraph supervisor workflow |
| **LangGraphSupervisorFactory** | Creates supervisor instances from database definitions |
| **LangGraphAgentFactory** | Creates agent instances from database definitions |
| **SupervisorRepository** | Database repository for supervisor configurations |
| **SupervisorAgentMapping** | Database mapping between supervisors and agents |

## Database Schema

The supervisor architecture relies on these key tables:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `supervisor_configurations` | Core supervisor definitions | id, name, description, routing_strategy, model_name, temperature, nodes, edges |
| `supervisor_agent_mappings` | Maps agents to supervisor nodes | supervisor_id, agent_id, node_id, execution_order |
| `agent_definitions` | Core agent definitions | id, name, description, status, agent_type |

## Architecture Diagram

```
┌─────────────────────────────────────┐
│         SupervisorBrainService      │
├─────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐ │
│  │  Supervisor │    │    Agents   │ │
│  │  Database   │───>│   Database  │ │
│  └─────────────┘    └─────────────┘ │
│          │                 │        │
│          ▼                 ▼        │
│  ┌─────────────┐    ┌─────────────┐ │
│  │ Supervisor  │    │    Agent    │ │
│  │   Factory   │    │   Factory   │ │
│  └─────────────┘    └─────────────┘ │
│          │                 │        │
│          ▼                 ▼        │
│  ┌─────────────┐    ┌─────────────┐ │
│  │ LangGraph   │◄───┤  LangGraph  │ │
│  │ Supervisor  │    │   Agents    │ │
│  └─────────────┘    └─────────────┘ │
└─────────────────────────────────────┘
```

## Supervisor Configuration

Supervisors are defined in the database with these key elements:

1. **Routing Strategy**: How the supervisor selects agents (pattern_match, vector_search, hybrid)
2. **Model and Parameters**: The LLM model and parameters used for routing decisions
3. **Graph Structure**: Nodes and edges defining the workflow
4. **Agent Mappings**: Which agents are mapped to which nodes in the graph

Example supervisor configuration:

```json
{
  "name": "Default Supervisor",
  "description": "Main supervisor for agent orchestration",
  "routing_strategy": "vector_search",
  "model_name": "gpt-4o",
  "temperature": 0.2,
  "entry_node": "router",
  "nodes": {
    "router": {"type": "router", "name": "Router"},
    "agent_executor": {"type": "agent", "name": "Agent Executor"},
    "guardrails": {"type": "guardrails", "name": "Guardrails"},
    "memory_store": {"type": "memory_store", "name": "Memory Store"}
  },
  "edges": {
    "router": [{"target": "agent_executor"}],
    "agent_executor": [{"target": "guardrails"}],
    "guardrails": [{"target": "memory_store"}],
    "memory_store": [{"target": "__end__"}]
  }
}
```

## Message Processing Flow

1. **Initial Processing**
   - User message is received via the `/api/v1/supervisor-chat/chat` endpoint
   - Message is validated and parsed using the `SupervisorChatRequest` model
   - `SupervisorBrainService.process_message()` is called with the message, session_id, and context

2. **State Initialization**
   - System creates a state object containing message, context, and session information
   - Any previous conversation history is retrieved from memory service

3. **Supervisor Graph Execution**
   - The LangGraph workflow executes based on the supervisor configuration
   - Each node in the graph processes the state in sequence
   - Common nodes include: router, agent_executor, guardrails, memory_store

4. **Agent Selection and Execution**
   - The router node selects the appropriate agent based on the configured strategy
   - The agent_executor node invokes the selected agent with the user input
   - The guardrails node applies policy checks to the response
   - The memory_store node persists the conversation history

5. **Response Generation**
   - Final processed response is returned to the caller

## Fallback Mechanism

If no supervisors are configured in the database, the system creates a fallback graph with a similar structure:

```python
# Create a fallback graph
builder = StateGraph(DictType)
builder.add_node("router", self._route_request)
builder.add_node("agent_executor", self._execute_agent)
builder.add_node("post_processor", self._apply_post_processing)
builder.set_entry_point("router")
builder.add_edge("router", "agent_executor")
builder.add_edge("agent_executor", "post_processor")
builder.add_edge("post_processor", END)
```

## API Integration

The supervisor architecture is accessible through these main endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/supervisor-chat/chat` | POST | Main chat endpoint that processes user messages through the supervisor |
| `/api/v1/supervisor-chat/execute-agent` | POST | Directly executes a specific agent, bypassing routing |

## Best Practices

1. **Supervisor Configuration**
   - Define a clear graph structure with appropriate nodes
   - Map agents to the correct nodes based on their purpose
   - Use meaningful node types (router, agent, guardrails, etc.)

2. **Agent Mapping**
   - Ensure the General Conversation Agent is available as a fallback
   - Include a Guardrails Agent for policy enforcement
   - Map specialized agents to appropriate nodes

3. **Performance Optimization**
   - Use pattern matching for faster agent selection when appropriate
   - Configure reasonable temperature settings for deterministic routing
   - Implement appropriate memory caching

4. **Testing**
   - Test with different user inputs to ensure proper agent selection
   - Verify that the graph handles all expected edge cases
   - Monitor routing decisions and adjust confidence thresholds as needed

## Advantages Over Previous Architecture

1. **Flexibility**: Supervisors can be created, modified, and deleted through database operations without code changes
2. **Configurability**: Routing strategies, models, and parameters can be adjusted per supervisor
3. **Multi-Supervisor Support**: Different supervisors can be created for different use cases
4. **Graph Customization**: Graph structures can be tailored to specific workflows and requirements
5. **Dynamic Agent Selection**: Agents can be assigned to different nodes based on their purpose and capabilities

## Future Improvements

1. **Conditional Routing**: Enhanced edge conditions for more complex decision trees
2. **Supervisor Selection**: A meta-supervisor to select the appropriate supervisor based on context
3. **Parallel Execution**: Support for parallel agent execution within a supervisor
4. **Incremental Learning**: Adaptation of routing strategies based on historical performance
5. **Visualization Tools**: UI components for designing and visualizing supervisor graphs
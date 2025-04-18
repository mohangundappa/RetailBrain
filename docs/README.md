# Staples Brain Documentation

## Introduction

Welcome to the Staples Brain documentation! This comprehensive guide provides detailed information about the Staples Brain multi-agent orchestration platform designed for intelligent customer engagement. The platform integrates specialized agents through a central orchestration system, with database-driven agent configurations, powerful workflow capabilities, and robust memory management.

## Documentation Map

### 1. System Architecture

* **[Orchestrator Overview](orchestrator.md)** - Introduction to the agent orchestration system
* **[Orchestrator Technical Details](orchestrator_technical.md)** - Deep dive into orchestrator implementation
* **[Agent Selection Process](agent_selection_process.md)** - Visual guide to agent routing decision logic

### 2. API Reference

* **[API Reference](api_reference.md)** - Complete API endpoint documentation
* **[Graph Chat API](orchestrator.md#api-integration)** - Chat API documentation
* **[Workflow API](workflow_api.md)** - Workflow-driven agent API

### 3. Agent Framework

* **[Adding New Agents](adding_new_agents.md)** - Guide to creating specialized agents
* **[Workflow Creation](workflow_creation.md)** - Building multi-step workflow agents
* **[Agent Selection Flow](agent_selection_process.md#agent-selection-flow)** - How agents are selected for user queries

### 4. Context & Memory Management  

* **[Session Context Management](session_context.md)** - Context across conversation turns
* **[Memory Types](session_context.md#memory-types)** - Types of memory in the system
* **[State Management](session_context.md#session-state-management)** - Persisting workflow state

### 5. Visual Diagrams

* **[Agent Selection Flow](assets/agent_selection_flow.svg)** - Visual diagram of selection process
* **[Agent Decision Sequence](assets/agent_decision_sequence.svg)** - Sequence diagram of agent selection
* **[Agent Routing Architecture](assets/agent_routing_architecture.svg)** - Component architecture diagram

### 6. Advanced Topics

* **[Advanced Usage Guide](advanced_usage.md)** - Performance optimization, scaling, and security
* **[Agent Validation Framework](advanced_usage.md#agent-validation-framework)** - Comprehensive testing framework
* **[Scaling Guidelines](advanced_usage.md#scaling-guidelines)** - Architecture for high-volume deployments

## System Overview

The Staples Brain platform is a LangGraph-based multi-agent orchestration system with these key components:

![Agent Routing Architecture](assets/agent_routing_architecture.svg)

### Key Components

| Component | Purpose | Technical Details |
|-----------|---------|-------------------|
| **API Gateway** | Entry point for chat requests | FastAPI-based REST API |
| **Orchestrator** | Agent selection and routing | LangGraph-based orchestration |
| **Agent Framework** | Base implementation for agents | Database-driven configurations |
| **Memory Service** | Context management | mem0 implementation with PostgreSQL |
| **Workflow Engine** | Execute multi-step workflows | LangGraph workflow execution |
| **Telemetry System** | Performance monitoring | API observability |

### Agent Types

The system supports multiple types of agents:

1. **Specialized Agents** - Domain-specific agents for particular tasks
2. **Workflow-Driven Agents** - Multi-step agents with state management
3. **General Conversation Agent** - Fallback for general queries
4. **Guardrails Agent** - Ensures responses meet quality and safety standards

### Core API Endpoints

| Endpoint | Method | Purpose | Documentation |
|----------|--------|---------|---------------|
| `/api/v1/graph-chat/chat` | POST | Process chat messages | [API Reference](api_reference.md#graph-chat-api) |
| `/api/v1/graph-chat/execute-agent` | POST | Direct agent execution | [API Reference](api_reference.md#graph-chat-api) |
| `/api/v1/agent-builder/agents` | GET/POST | Manage agent configurations | [API Reference](api_reference.md#agent-builder-api) |
| `/api/v1/workflow-agents/execute` | POST | Execute workflow agents | [API Reference](api_reference.md#workflow-api) |
| `/api/v1/agent-workflow/{agent_id}` | GET | Get workflow configuration | [Workflow API](workflow_api.md#workflow-configuration) |

## Agent Selection Process

The agent selection process is a critical component that determines which specialized agent should handle a user's query:

![Agent Selection Flow](assets/agent_selection_flow.svg)

The process follows these steps:

1. **User Message Intake** - Message received via API
2. **Preprocessing** - Text normalization and cleaning
3. **Pattern Matching** - Regex patterns for direct routing
4. **Semantic Matching** - Vector similarity for less explicit intents
5. **Conversational Check** - Fallback detection for small talk
6. **Agent Execution** - Selected agent processes the message

For more details, see the [Agent Selection Process](agent_selection_process.md) documentation.

## Workflow-Driven Agents

Workflow-driven agents handle multi-step interactions using a directed graph of nodes and edges:

```
User Input → Request Email → Validate Email → Send Code → Verify Code → Reset Password → Completion
```

Each node represents a distinct processing step:
- **Prompt Nodes** - Display messages to users
- **Tool Nodes** - Execute specific tools
- **Condition Nodes** - Make decisions
- **LLM Nodes** - Process with language models
- **End Nodes** - Terminate workflow paths

For more details, see the [Workflow Creation](workflow_creation.md) guide.

## Context Management

The system maintains context across conversation turns using the mem0 memory service:

```json
{
  "context": {
    "customer_id": "cust-456",
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

This context is passed with each API request to maintain conversation continuity.

For more details, see the [Session Context Management](session_context.md) documentation.

## Implementation Details

### Technical Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis (optional)
- **LLM Framework**: LangChain and LangGraph
- **LLM Provider**: OpenAI API
- **Deployment**: Databricks

### Agent Implementation

Agents are primarily defined in the database with these key elements:
- **Pattern Capabilities** - Regex patterns for intent detection
- **Prompts** - System and user prompts for generation
- **Tools** - Available tools for the agent to use
- **Entities** - Entity extraction patterns

For more details, see the [Adding New Agents](adding_new_agents.md) guide.

## Getting Started

1. Review the [API Reference](api_reference.md) for available endpoints
2. Understand the [Orchestrator](orchestrator.md) to learn about agent selection
3. Follow the [Adding New Agents](adding_new_agents.md) guide to create custom agents
4. Explore the [Workflow Creation](workflow_creation.md) guide for multi-step agents

## Best Practices

1. **Agent Design**
   - Focus on a single specific capability per agent
   - Define clear boundaries between agents
   - Design patterns for accurate intent detection
   - Test with a variety of user queries

2. **Workflow Design**
   - Keep workflows focused on single tasks
   - Include proper error handling and fallbacks
   - Design clear user interaction patterns
   - Persist state for conversation continuity

3. **Context Management**
   - Extract and store entities from user messages
   - Reference entities in follow-up turns
   - Include sufficient context for LLM operations
   - Clean up context when no longer needed

4. **Integration**
   - Use consistent session IDs across API calls
   - Include relevant context in each request
   - Handle API errors gracefully
   - Monitor agent selection metrics
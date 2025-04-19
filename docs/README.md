# Staples Brain Documentation

## Introduction

Welcome to the Staples Brain documentation! This comprehensive guide provides detailed information about the Staples Brain multi-agent orchestration platform designed for intelligent customer engagement. The platform integrates specialized agents through a central orchestration system, with database-driven supervisor configurations, powerful workflow capabilities, and robust memory management.

## Documentation Map

### 1. System Architecture

* **[Supervisor-Based Architecture](supervisor_based_architecture.md)** - Database-driven supervisors for agent orchestration
* **[Supervisor Database Schema](supervisor_database_schema.md)** - Schema for supervisor configurations
* **[Supervisor API Endpoints](supervisor_endpoints.md)** - API endpoints for the supervisor-based system

### 2. Agent Framework

* **[Adding New Agents](adding_new_agents.md)** - Guide to creating specialized agents
* **[Workflow Creation](workflow_creation.md)** - Building multi-step workflow agents

### 3. Context & Memory Management  

* **[Session Context Management](session_context.md)** - Context across conversation turns
* **[Advanced Context Management](advanced_context_management.md)** - Advanced memory integration and optimization
* **[Document Context Management](document_context_management.md)** - Document integration and knowledge retrieval

### 4. Advanced Topics

* **[Advanced Usage Guide](advanced_usage.md)** - Performance optimization, scaling, and security

## System Overview

The Staples Brain platform is a LangGraph-based multi-agent orchestration system with these key components:

### Key Components

| Component | Purpose | Technical Details |
|-----------|---------|-------------------|
| **API Gateway** | Entry point for chat requests | FastAPI-based REST API |
| **SupervisorBrainService** | Agent selection and orchestration | LangGraph-based supervisor |
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
| `/api/v1/supervisor-chat/chat` | POST | Process messages via supervisor | [Supervisor Endpoints](supervisor_endpoints.md) |
| `/api/v1/supervisor-chat/execute-agent` | POST | Direct agent execution via supervisor | [Supervisor Endpoints](supervisor_endpoints.md) |
| `/api/v1/agent-builder/agents` | GET/POST | Manage agent configurations | [Supervisor Endpoints](supervisor_endpoints.md) |
| `/api/v1/workflow-agents/execute` | POST | Execute workflow agents | [Supervisor Endpoints](supervisor_endpoints.md) |
| `/api/v1/agent-workflow/{agent_id}` | GET | Get workflow configuration | [Supervisor Endpoints](supervisor_endpoints.md) |

## Supervisor-Based Architecture

The Staples Brain system uses a database-driven supervisor architecture for agent orchestration. This approach provides greater flexibility, configurability, and extensibility by storing the orchestration logic in the database rather than hardcoding it.

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

Key features of the supervisor architecture:

1. **Database-Driven Configuration**: Supervisor configurations stored in database tables
2. **Dynamic Agent Mapping**: Agents can be mapped to specific nodes in the supervisor graph
3. **Flexible Routing Strategies**: Support for pattern matching, vector search, and hybrid approaches
4. **Customizable Graph Structure**: Nodes and edges define the execution flow and can be modified without code changes

For detailed information, see the [Supervisor-Based Architecture](supervisor_based_architecture.md) documentation.

## Message Processing Flow

1. **API Request**: User message received via the `/api/v1/supervisor-chat/chat` endpoint
2. **Supervisor Processing**: Message processed through the LangGraph supervisor workflow
3. **Agent Selection**: Appropriate agent selected based on routing strategy
4. **Agent Execution**: Selected agent processes the message
5. **Guardrails Application**: Guardrails agent ensures policy compliance
6. **Memory Management**: Conversation state persisted for future turns
7. **Response Generation**: Final response returned to the user

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

For basic context management, see the [Session Context Management](session_context.md) documentation.

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

1. Review the [Supervisor-Based Architecture](supervisor_based_architecture.md) to understand the latest design
2. Study the [Supervisor Database Schema](supervisor_database_schema.md) for configuring supervisors
3. Review the [Supervisor API Endpoints](supervisor_endpoints.md) for available endpoints
4. Follow the [Adding New Agents](adding_new_agents.md) guide to create custom agents
5. Explore the [Workflow Creation](workflow_creation.md) guide for multi-step agents

## Best Practices

1. **Supervisor Configuration**
   - Define a clear graph structure with appropriate nodes
   - Map agents to the correct nodes based on their purpose
   - Use meaningful node types (router, agent, guardrails, etc.)
   - Implement appropriate routing strategies for your use case

2. **Agent Design**
   - Focus on a single specific capability per agent
   - Define clear boundaries between agents
   - Design patterns for accurate intent detection
   - Test with a variety of user queries

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
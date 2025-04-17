# Staples Brain Documentation

## Introduction

This documentation provides a comprehensive guide to the Staples Brain AI orchestration platform. It covers API implementation details, integration points, and technical specifications for developers and architects.

## Table of Contents

### Core Concepts

- [Orchestrator Overview](orchestrator.md) - Introduction to the central orchestration system
- [Orchestrator Technical Details](orchestrator_technical.md) - Technical implementation of the orchestrator
- [Session Context Management](session_context.md) - How context is managed across conversation turns

### API Documentation

- [API Reference](api_reference.md) - Comprehensive API endpoint documentation
- [Workflow API](workflow_api.md) - Details on workflow-driven agent API

### Development Guides

- [Adding New Agents](adding_new_agents.md) - Guide to creating and integrating new agents
- [Workflow Creation](workflow_creation.md) - Building workflow-driven agents

## Architecture

The Staples Brain platform consists of these main components:

1. **API Gateway** - Central entry point for all API requests
2. **Orchestrator** - Routes user queries to specialized agents
3. **Agent Framework** - Base implementation for all agents
4. **Memory Service** - Context management system (mem0)
5. **Workflow Engine** - Executes workflow-based agents
6. **Telemetry System** - Tracks performance and usage metrics

## Key API Endpoints

| Endpoint | Purpose | Documentation |
|----------|---------|---------------|
| `/api/v1/graph-chat/chat` | Process chat messages through the orchestrator | [API Reference](api_reference.md#graph-chat-api) |
| `/api/v1/graph-chat/execute-agent` | Execute specific agent directly | [API Reference](api_reference.md#graph-chat-api) |
| `/api/v1/agent-builder/agents` | Manage agent configurations | [API Reference](api_reference.md#agent-builder-api) |
| `/api/v1/workflow-agents/execute` | Execute workflow-driven agents | [API Reference](api_reference.md#workflow-api) |
| `/api/v1/agent-workflow/{agent_id}` | Get workflow configuration | [Workflow API](workflow_api.md#workflow-configuration) |

## Request-Response Flow

```
Client -> API Gateway -> Orchestrator -> Agent Selection -> Specialized Agent -> Response
```

With workflow-driven agents:

```
Client -> API Gateway -> Workflow Service -> Workflow Interpreter -> Node Execution -> Response
```

## Integration Points

The system integrates with:

1. **PostgreSQL** - Persistent storage for agent configurations and memory
2. **Redis** - Fast caching for session context (optional)
3. **OpenAI API** - LLM provider for agent intelligence
4. **Databricks** - Deployment environment
5. **LangChain/LangGraph** - Agent orchestration framework

## Getting Started

1. Review the [API Reference](api_reference.md) for available endpoints
2. Understand the [Orchestrator](orchestrator.md) to learn about agent selection
3. Follow the [Adding New Agents](adding_new_agents.md) guide to create custom agents

## Best Practices

1. **Session Management**
   - Use consistent session_id across API calls
   - Include relevant context in each request
   - Maintain entity memory across turns

2. **Agent Selection**
   - Define clear patterns for agent selection
   - Use specific, high-confidence patterns for direct routing
   - Test routing with varied user inputs

3. **Workflow Design**
   - Keep workflows focused on single tasks
   - Design clear paths with error handling
   - Persist state between conversation turns

4. **Context Usage**
   - Extract and store entities
   - Reference entities in follow-up turns
   - Include sufficient context for LLM operations
# Staples Brain: Multi-Agent AI Orchestration Platform

## Project Overview

Staples Brain is an advanced multi-agent AI orchestration platform delivering intelligent customer engagement solutions. The system features specialized agents that communicate through a central orchestration layer, providing personalized and context-aware responses.

## Key Features

- **Intent-first agent routing** using pattern matching and semantic search
- **Database-driven agent configurations** for dynamic agent deployment
- **Multi-step workflow capabilities** for complex customer interactions
- **Context management** across conversation turns
- **Robust API** for integration with frontend applications

## Documentation

For detailed documentation, see the [Staples Brain Documentation](docs/README.md).

### Main Documentation Sections

- [System Architecture](docs/README.md#system-overview)
- [API Reference](docs/api_reference.md)
- [Agent Framework](docs/README.md#agent-types)
- [Agent Selection Process](docs/agent_selection_process.md)
- [Workflow Creation](docs/workflow_creation.md)
- [Advanced Usage](docs/advanced_usage.md)

## Getting Started

1. **API Exploration**: Review the [API endpoints](docs/api_reference.md)
2. **Understanding Agent Selection**: See the [agent selection process](docs/agent_selection_process.md)
3. **Creating Agents**: Follow the [adding new agents](docs/adding_new_agents.md) guide
4. **Building Workflows**: Learn about [workflow creation](docs/workflow_creation.md)

## Visual Documentation

The documentation includes detailed visual diagrams:

- [Agent Selection Flow](docs/assets/agent_selection_flow.svg)
- [Agent Decision Sequence](docs/assets/agent_decision_sequence.svg)
- [Agent Routing Architecture](docs/assets/agent_routing_architecture.svg)

## Supported Agent Types

- **Specialized Agents**: Domain-specific for particular tasks
- **Workflow-Driven Agents**: Multi-step interactions with state management
- **General Conversation Agent**: Fallback for general queries
- **Guardrails Agent**: Ensures response quality and safety

## Technology Stack

- **Backend**: FastAPI with PostgreSQL and Redis
- **AI Framework**: LangChain and LangGraph
- **LLM Integration**: OpenAI API
- **Deployment**: Databricks ecosystem
- **Vector Database**: pgvector for semantic search

## Project Structure

- **Backend**: API gateway, services, and agent implementations
- **Frontend**: React dashboard and chat interface
- **Documentation**: Comprehensive guides and references
- **Tests**: Unit and integration tests for components

For more information, refer to the full [documentation](docs/README.md).
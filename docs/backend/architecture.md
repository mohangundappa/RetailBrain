# Staples Brain Architecture

## Overview

Staples Brain is an AI orchestration platform that enables intelligent system management through a modular and scalable architecture. The system is composed of two main components:

1. **Backend** - Pure FastAPI implementation that provides all functionality through a standardized API gateway
2. **Frontend** - UI layer that interacts with the backend via API calls

## Backend Architecture

The backend follows a layered architecture with the following components:

### API Gateway

The API Gateway (`api_gateway.py`) serves as the entry point for all interactions with the system. It:

- Registers all API routes
- Handles cross-origin requests
- Implements global error handling
- Manages database initialization
- Provides health check endpoints

### Brain

The Brain (`brain/staples_brain.py`) is the core of the system, responsible for:

- Initializing and managing agents
- Orchestrating agent interactions
- Processing user inputs
- Managing system state

### Orchestrator

The Orchestrator (`brain/orchestrator/__init__.py`) coordinates the interaction between agents, including:

- Agent selection based on user query
- Message routing
- State management

### Agents

Agents are specialized components that handle specific tasks:

- **Package Tracking Agent**: Handles order and package tracking queries
- **Reset Password Agent**: Manages password reset requests
- **Store Locator Agent**: Provides store location information

### Database

The system uses PostgreSQL with the following tables:

- Conversation: Stores conversation history
- Message: Stores individual messages
- TelemetrySession: Tracks telemetry sessions
- TelemetryEvent: Records individual telemetry events
- CustomAgent: Stores custom agent configurations
- AgentComponent: Manages agent components
- ComponentConnection: Tracks connections between components
- ComponentTemplate: Stores component templates
- AgentTemplate: Manages agent templates

### Services

Services implement business logic and interact with external systems:

- **ChatService**: Manages conversation history and retrieval
- **TelemetryService**: Handles telemetry data collection and analysis
- **BrainService**: Provides core brain functionality

## Integration Points

The system integrates with several external services:

- **LangSmith**: For telemetry and tracing
- **OpenAI**: For GPT-based language processing
- **Databricks**: For advanced analytics (optional)

## Deployment Architecture

The system is designed to be deployed as a single service, with the FastAPI backend handling all requests and serving static frontend assets.
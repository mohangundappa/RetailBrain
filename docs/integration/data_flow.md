# Data Flow

## Overview

This document describes the flow of data between the frontend and backend components of Staples Brain.

## Core Data Flows

### User Conversation Flow

1. **User Input**:
   - User enters a message in the frontend UI
   - Frontend sends message to `/api/v1/chat/message` endpoint
   
2. **Backend Processing**:
   - API Gateway receives the message
   - Message is stored in the database
   - Brain determines the appropriate agent to handle the request
   - Selected agent processes the message
   
3. **Response Generation**:
   - Agent generates a response
   - Response is stored in the database
   - Response is returned to the frontend
   
4. **Frontend Display**:
   - Frontend displays the response in the conversation UI

### Telemetry Flow

1. **Event Generation**:
   - User actions or system events trigger telemetry
   - Events are collected by the TelemetryService
   
2. **Data Storage**:
   - Events are stored in the TelemetrySession and TelemetryEvent tables
   - Additional data is sent to LangSmith (if configured)
   
3. **Data Retrieval**:
   - Admin interface fetches telemetry data via `/api/v1/telemetry/sessions` endpoint
   - Data is displayed in the telemetry dashboard

## Sequence Diagrams

### User Message Sequence

```
User -> Frontend: Enter message
Frontend -> API Gateway: POST /api/v1/chat/message
API Gateway -> Database: Store message
API Gateway -> Brain: Process message
Brain -> Orchestrator: Determine agent
Orchestrator -> Agent: Process with selected agent
Agent -> Brain: Return response
Brain -> API Gateway: Return response
API Gateway -> Database: Store response
API Gateway -> Frontend: Return response
Frontend -> User: Display response
```

### Telemetry Sequence

```
System -> TelemetryService: Generate event
TelemetryService -> Database: Store event
TelemetryService -> LangSmith: Send telemetry (if configured)
Admin -> Frontend: View telemetry
Frontend -> API Gateway: GET /api/v1/telemetry/sessions
API Gateway -> Database: Fetch sessions
API Gateway -> Frontend: Return session data
Frontend -> Admin: Display telemetry dashboard
```

## Data Models

The primary data models that flow between components are:

1. **ChatMessage**: Contains message content, role, and metadata
2. **Session**: Represents a conversation session
3. **TelemetryEvent**: Represents a system or user event
4. **AgentResponse**: Contains the response from an agent

## Integration Points

1. **FastAPI Endpoints**: Primary integration points between frontend and backend
2. **WebSocket (future)**: For real-time communication
3. **Database**: Shared data store between components
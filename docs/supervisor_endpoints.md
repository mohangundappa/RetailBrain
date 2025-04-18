# Supervisor API Endpoints

## Overview

The Supervisor-based architecture exposes its functionality through dedicated API endpoints for chat and agent execution. These endpoints connect to the SupervisorBrainService, which manages the orchestration of agents using LangGraph Supervisors with database-driven configuration.

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/supervisor-chat/chat` | POST | Main chat endpoint that processes user messages through the supervisor |
| `/api/v1/supervisor-chat/execute-agent` | POST | Directly executes a specific agent, bypassing routing |

## Request Models

### SupervisorChatRequest

```python
class SupervisorChatRequest(BaseModel):
    """Request model for supervisor chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
```

### DirectAgentExecutionRequest

```python
class DirectAgentExecutionRequest(SupervisorChatRequest):
    """Request model for direct agent execution"""
    agent_id: str = Field(..., description="ID of the agent to execute")
```

## Response Models

### SupervisorChatResponse

```python
class SupervisorChatResponse(BaseModel):
    """Response model for supervisor chat"""
    success: bool = Field(..., description="Whether the request was successful")
    session_id: str = Field(..., description="Session ID")
    response: str = Field(..., description="Response text")
    agent: Dict[str, Any] = Field(..., description="Selected agent information")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")
```

## Example Usage

### Chat Request

```json
{
  "message": "I need to reset my password",
  "session_id": "user-123-session",
  "context": {
    "customer_id": "cust-456",
    "previous_agents": ["general_conversation"]
  }
}
```

### Chat Response

```json
{
  "success": true,
  "session_id": "user-123-session",
  "response": "I can help you reset your password. First, please tell me the email address associated with your account.",
  "agent": {
    "id": "ded3cb1c-6db4-4337-9b8a-c80668d14de3",
    "name": "Reset Password Agent",
    "confidence": 0.95
  },
  "metadata": {
    "processing_time": 0.254,
    "trace_id": "user-123-session"
  }
}
```

### Direct Agent Execution Request

```json
{
  "message": "Where is the closest Staples store?",
  "session_id": "user-123-session",
  "agent_id": "1ed554e4-8843-405a-ab3e-83866eb262bf"
}
```

## Integration with Front-end

The front-end application should use the supervisor-chat endpoints for all new chat interactions. The existing graph-chat endpoints are maintained for backward compatibility but will be deprecated in future releases.

### Migration from graph-chat

To migrate from the original graph-chat endpoints to the supervisor-chat endpoints:

1. Update all API calls to use the new endpoint paths
2. Adjust response handling to accommodate the slightly different response format
3. Update any direct agent execution calls to use the new format

## Error Handling

The supervisor endpoints use standard HTTP status codes for error reporting:

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (agent or resource not found) |
| 500 | Internal Server Error |

For error responses, the response body will include details:

```json
{
  "success": false,
  "session_id": "user-123-session",
  "response": "I encountered an error while processing your request.",
  "agent": null,
  "error": "Agent execution failed: Agent not found or unavailable"
}
```

## Telemetry and Observability

All supervisor-chat endpoints include telemetry and observability:

1. Processing times are recorded and included in response metadata
2. Agent selection details are logged for analysis
3. Session IDs are used as trace IDs for request tracking
4. Errors are logged with detailed information for debugging

## Security Considerations

The supervisor-chat endpoints enforce:

1. Request validation using Pydantic models
2. Session-based context isolation
3. Agent validation before execution
4. Error handling that prevents information leakage
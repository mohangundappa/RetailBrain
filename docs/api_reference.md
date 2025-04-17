# API Reference

## Overview

This document provides a comprehensive reference for the Staples Brain API endpoints. The API is organized into several functional areas:

- Chat API: Core chat functionality
- Graph Chat API: LangGraph-based agent orchestration
- Agent Builder API: Agent configuration and management
- Workflow API: Workflow-driven agent execution
- Observability API: Monitoring and telemetry

## Base URL

All API endpoints are relative to:

```
/api/v1
```

## Authentication

API endpoints use API key authentication. Include the API key in the `X-API-Key` header:

```
X-API-Key: your-api-key
```

## Chat API

### Send Chat Message

Process a chat message and return a response.

```
POST /chat
```

#### Request

```json
{
  "message": "I need to reset my password",
  "session_id": "user-123",
  "context": {
    "customer_id": "cust-456",
    "previous_messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "How can I help you today?"}
    ]
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "I can help you reset your password. First, please provide the email address associated with your account.",
    "agent": "reset_password",
    "confidence": 0.95
  },
  "metadata": {
    "processing_time_ms": 450,
    "context_used": true
  }
}
```

### Get Conversations

Get a list of all conversations.

```
GET /chat/conversations
```

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "conv-123",
      "start_time": "2025-04-15T14:30:22Z",
      "last_message_time": "2025-04-15T14:35:12Z",
      "message_count": 5,
      "summary": "Password reset assistance"
    },
    {
      "id": "conv-124",
      "start_time": "2025-04-15T16:10:45Z",
      "last_message_time": "2025-04-15T16:15:33Z",
      "message_count": 3,
      "summary": "Store location inquiry"
    }
  ]
}
```

## Graph Chat API

### Send Graph Chat Message

Process a chat message using the LangGraph-based brain service.

```
POST /graph-chat/chat
```

#### Request

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

#### Response

```json
{
  "success": true,
  "response": {
    "message": "I can help you reset your password. First, please tell me the email address associated with your account.",
    "type": "text"
  },
  "conversation_id": "conv-789",
  "external_conversation_id": "ext-123",
  "observability_trace_id": "trace-456"
}
```

### Execute Specific Agent

Execute a specific agent directly, bypassing the router.

```
POST /graph-chat/execute-agent
```

#### Request

```json
{
  "message": "What's the status of my order?",
  "agent_id": "6929f621-de11-4068-9d4b-b1f78c02a10f",
  "session_id": "user-123-session",
  "context": {
    "customer_id": "cust-456"
  }
}
```

#### Response

```json
{
  "success": true,
  "response": {
    "message": "I'll help you check your order status. Could you please provide your order number?",
    "type": "text"
  },
  "conversation_id": "conv-790",
  "external_conversation_id": "ext-124",
  "observability_trace_id": "trace-457"
}
```

## Agent Builder API

### List Agents

Get a list of all available agents.

```
GET /agent-builder/agents
```

#### Response

```json
{
  "success": true,
  "agents": [
    {
      "id": "d5e22e3a-1d83-49bf-baef-52c8f4d55a87",
      "name": "General Conversation Agent",
      "description": "Handles greetings, goodbyes, small talk, and general questions that don't fit other specialized agents.",
      "agent_type": "SMALL_TALK",
      "version": 1,
      "status": "active",
      "is_system": true,
      "created_at": "2025-04-13T18:52:37.077293",
      "updated_at": "2025-04-13T18:52:37.077293"
    },
    {
      "id": "f2feabb7-2279-4feb-875a-3c7f58105ac9",
      "name": "Guardrails Agent",
      "description": "Verifies all responses to ensure they meet policy requirements and maintain a professional tone.",
      "agent_type": "BUILT_IN",
      "version": 1,
      "status": "active",
      "is_system": true,
      "created_at": "2025-04-13T18:51:51.557184",
      "updated_at": "2025-04-13T18:51:51.557184"
    }
  ]
}
```

### Get Agent Details

Get detailed information about a specific agent.

```
GET /agent-builder/agents/{agent_id}
```

#### Response

```json
{
  "success": true,
  "agent": {
    "id": "6929f621-de11-4068-9d4b-b1f78c02a10f",
    "name": "Order Status Agent",
    "description": "Handles order status inquiries and tracking information requests.",
    "agent_type": "ORDER_STATUS",
    "version": 1,
    "status": "active",
    "is_system": false,
    "created_at": "2025-04-14T10:15:22.123456",
    "updated_at": "2025-04-14T10:15:22.123456",
    "created_by": "admin",
    "persona": "You are an Order Status specialist for Staples. Help customers check the status of their orders and provide tracking information when available.",
    "llm_config": {
      "model": "gpt-4o",
      "temperature": 0.2,
      "max_tokens": 500
    },
    "patterns": [
      {
        "id": "pat-123",
        "regex": "order status|track order|where is my order|when will my order arrive",
        "confidence": 0.85,
        "description": "Order status intent detection"
      }
    ],
    "tools": [
      {
        "id": "tool-123",
        "name": "check_order_status",
        "description": "Check the status of an order",
        "parameters": {
          "order_number": {
            "type": "string",
            "description": "Order number to check"
          }
        }
      }
    ]
  }
}
```

### Create Agent

Create a new agent.

```
POST /agent-builder/agents
```

#### Request

```json
{
  "name": "Product Recommendation Agent",
  "description": "Suggests products based on customer needs and preferences",
  "agent_type": "PRODUCT_RECOMMENDATION",
  "status": "active",
  "persona": "You are a Product Recommendation specialist for Staples. Help customers find the perfect products based on their needs."
}
```

#### Response

```json
{
  "success": true,
  "agent": {
    "id": "6929f621-de11-4068-9d4b-b1f78c02a10f",
    "name": "Product Recommendation Agent",
    "description": "Suggests products based on customer needs and preferences",
    "agent_type": "PRODUCT_RECOMMENDATION",
    "version": 1,
    "status": "active",
    "is_system": false,
    "created_at": "2025-04-17T15:20:33.123456",
    "updated_at": "2025-04-17T15:20:33.123456"
  }
}
```

### Add Pattern Capability

Add a pattern capability to an agent.

```
POST /agent-builder/agents/{agent_id}/patterns
```

#### Request

```json
{
  "regex": "recommend|suggest|what product|which product",
  "confidence": 0.75,
  "description": "Product recommendation intent detection"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "pat-456",
    "agent_id": "6929f621-de11-4068-9d4b-b1f78c02a10f",
    "regex": "recommend|suggest|what product|which product",
    "confidence": 0.75,
    "description": "Product recommendation intent detection",
    "created_at": "2025-04-17T15:25:12.123456"
  }
}
```

## Workflow API

### Get Workflow Information

Get information about an agent's workflow.

```
GET /workflow-agents/info/{agent_id}
```

#### Response

```json
{
  "id": "workflow-123",
  "agent_id": "agent-456",
  "name": "Reset Password Workflow",
  "description": "Workflow for handling password reset requests",
  "nodes": 5,
  "edges": 6,
  "entry_node": "request_email",
  "created_at": "2025-04-10T15:30:45.123Z",
  "updated_at": "2025-04-12T09:15:22.456Z"
}
```

### Execute Workflow Agent

Execute a workflow-driven agent.

```
POST /workflow-agents/execute
```

#### Request

```json
{
  "message": "I need to reset my password",
  "conversation_id": "conv-789",
  "session_id": "session-101112",
  "context": {
    "customer_id": "cust-456",
    "workflow_state": {
      "current_node": "request_email"
    }
  }
}
```

#### Response

```json
{
  "success": true,
  "response": {
    "message": "Please provide the email address associated with your account.",
    "type": "text"
  },
  "conversation_id": "conv-789",
  "observability_trace_id": "trace-458",
  "metadata": {
    "workflow_id": "workflow-123",
    "current_node": "request_email",
    "next_node": "validate_email"
  }
}
```

### Get Detailed Workflow

Get detailed workflow configuration for an agent.

```
GET /agent-workflow/{agent_id}
```

#### Response

```json
{
  "id": "workflow-123",
  "agent_id": "agent-456",
  "name": "Reset Password Workflow",
  "description": "Workflow for handling password reset requests",
  "nodes": {
    "request_email": {
      "type": "prompt",
      "prompt": "Please provide the email address associated with your account.",
      "output_key": "email_response"
    },
    "validate_email": {
      "type": "tool",
      "config": {
        "tool_name": "validate_email",
        "parameters": {
          "email": "{{email}}"
        }
      },
      "output_key": "email_validation_result"
    }
  },
  "edges": {
    "request_email": [
      {
        "target": "validate_email",
        "condition": "has_entity",
        "condition_value": "email"
      }
    ]
  },
  "entry_node": "request_email"
}
```

## Observability API

### Get Trace Information

Get detailed trace information for a conversation.

```
GET /observability/traces/{trace_id}
```

#### Response

```json
{
  "success": true,
  "trace": {
    "id": "trace-456",
    "conversation_id": "conv-789",
    "start_time": "2025-04-17T15:30:22.123Z",
    "end_time": "2025-04-17T15:30:23.456Z",
    "duration_ms": 1333,
    "steps": [
      {
        "id": "step-1",
        "name": "router",
        "start_time": "2025-04-17T15:30:22.123Z",
        "end_time": "2025-04-17T15:30:22.456Z",
        "duration_ms": 333,
        "input": {
          "message": "I need to reset my password"
        },
        "output": {
          "agent": "reset_password",
          "confidence": 0.95
        }
      },
      {
        "id": "step-2",
        "name": "reset_password",
        "start_time": "2025-04-17T15:30:22.456Z",
        "end_time": "2025-04-17T15:30:23.456Z",
        "duration_ms": 1000,
        "input": {
          "message": "I need to reset my password"
        },
        "output": {
          "response": "Please provide the email address associated with your account."
        }
      }
    ]
  }
}
```

### Get Agent Performance Metrics

Get performance metrics for agents.

```
GET /observability/metrics/agents
```

#### Response

```json
{
  "success": true,
  "metrics": {
    "by_agent": [
      {
        "agent": "reset_password",
        "count": 120,
        "avg_duration_ms": 1250,
        "success_rate": 0.95,
        "confidence_avg": 0.85
      },
      {
        "agent": "store_locator",
        "count": 85,
        "avg_duration_ms": 980,
        "success_rate": 0.98,
        "confidence_avg": 0.88
      }
    ],
    "overall": {
      "total_requests": 450,
      "avg_duration_ms": 1100,
      "success_rate": 0.96,
      "agent_count": 7
    }
  }
}
```

## Error Handling

All API endpoints use consistent error handling. When an error occurs, the response will include:

- `success: false` status
- `error` message with a description of the issue
- HTTP status code reflecting the error type

Example error response:

```json
{
  "success": false,
  "error": "Agent with ID '6929f621-de11-4068-9d4b-b1f78c02a10f' not found",
  "details": {
    "code": "AGENT_NOT_FOUND",
    "help_url": "https://docs.example.com/errors/agent-not-found"
  }
}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Invalid or missing API key |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Valid request but cannot be processed |
| 500 | Internal Server Error - Server-side issue |

## Rate Limiting

The API implements rate limiting to ensure fair usage. Rate limits are applied per API key.

Rate limit headers included in responses:

- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests for the current period
- `X-RateLimit-Reset`: Seconds until the rate limit resets

When a rate limit is exceeded, a 429 Too Many Requests response is returned:

```json
{
  "success": false,
  "error": "Rate limit exceeded. Please try again later.",
  "details": {
    "code": "RATE_LIMIT_EXCEEDED",
    "limit": 100,
    "reset_in": 45
  }
}
```
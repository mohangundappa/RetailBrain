# Workflow API

## Overview

The Workflow API provides endpoints for accessing and executing workflow-driven agents in the Staples Brain system. These workflows define step-by-step processing of user requests through a directed graph of nodes and edges, each representing a specific operation or decision point.

## API Endpoints

### Workflow Agents API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/workflow-agents/info/{agent_id}` | GET | Get workflow information for a specific agent |
| `/api/v1/workflow-agents/execute` | POST | Execute a workflow-driven agent |

### Agent Workflow API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/agent-workflow/{agent_id}` | GET | Get detailed workflow configuration |
| `/api/v1/agent-workflow/{agent_id}/nodes` | GET | Get workflow nodes for a specific agent |
| `/api/v1/agent-workflow/{agent_id}/edges` | GET | Get workflow edges for a specific agent |

## Request & Response Models

### Workflow Info Request

```
GET /api/v1/workflow-agents/info/{agent_id}
```

Where `agent_id` is the UUID of the agent.

### Workflow Info Response

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

### Workflow Execute Request

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

### Detailed Workflow Response

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
    },
    "send_code": {
      "type": "tool",
      "config": {
        "tool_name": "send_verification_code",
        "parameters": {
          "email": "{{email}}"
        }
      },
      "output_key": "code_sent_result"
    },
    "verify_code": {
      "type": "prompt",
      "prompt": "Please enter the verification code sent to your email.",
      "output_key": "code_verification_response"
    },
    "reset_password": {
      "type": "prompt",
      "prompt": "Please enter your new password.",
      "output_key": "password_reset_response"
    }
  },
  "edges": {
    "request_email": [
      {
        "target": "validate_email",
        "condition": "has_entity",
        "condition_value": "email"
      }
    ],
    "validate_email": [
      {
        "target": "send_code",
        "condition": "tool_success",
        "condition_value": true
      },
      {
        "target": "request_email",
        "condition": "tool_success",
        "condition_value": false
      }
    ],
    "send_code": [
      {
        "target": "verify_code",
        "condition": "tool_success",
        "condition_value": true
      }
    ],
    "verify_code": [
      {
        "target": "reset_password",
        "condition": "has_entity",
        "condition_value": "verification_code"
      }
    ]
  },
  "entry_node": "request_email",
  "created_at": "2025-04-10T15:30:45.123Z",
  "updated_at": "2025-04-12T09:15:22.456Z"
}
```

## Workflow Execution Process

The workflow execution process follows these steps:

1. Client sends a message to the `/api/v1/workflow-agents/execute` endpoint
2. Server retrieves the workflow configuration for the specified agent
3. Current state is determined from the context or initialized to the entry node
4. The workflow interpreter executes the current node:
   - Prompt nodes: Generate text using LLM
   - Tool nodes: Execute a specific tool with parameters
   - Condition nodes: Make decisions based on state
5. Edge conditions are evaluated to determine the next node
6. The process continues until a terminal node is reached
7. Final response is returned to the client

## Workflow Node Types

### Prompt Node

```json
{
  "type": "prompt",
  "prompt": "Please provide your email address to reset your password.",
  "output_key": "response"
}
```

### Tool Node

```json
{
  "type": "tool",
  "config": {
    "tool_name": "send_verification_code",
    "parameters": {
      "email": "{{email}}"
    }
  },
  "output_key": "tool_result"
}
```

### LLM Node

```json
{
  "type": "llm",
  "prompt_template": "Extract the email from this message: {{message}}",
  "output_key": "extracted_email",
  "output_parser": "json"
}
```

## Edge Types

Edges define transitions between nodes based on conditions:

### Has Entity Condition

```json
{
  "target": "validate_email",
  "condition": "has_entity",
  "condition_value": "email"
}
```

### Tool Success Condition

```json
{
  "target": "send_code",
  "condition": "tool_success",
  "condition_value": true
}
```

### Default Condition

```json
{
  "target": "general_help",
  "condition": "default"
}
```

## Implementation Details

### Workflow Service

The `WorkflowService` class provides methods for working with workflows:

```python
class WorkflowService:
    """
    Service for managing workflow-driven agents.
    
    This service provides methods for retrieving and manipulating workflow
    configurations, as well as executing workflow-driven agents.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the workflow service.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
    
    async def get_workflow_for_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the workflow configuration for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Workflow configuration or None if not found
        """
        # Implementation details...
    
    async def execute_workflow(
        self, 
        agent_id: str, 
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow-driven agent.
        
        Args:
            agent_id: Agent ID
            message: User message
            session_id: Session ID
            context: Additional context
            
        Returns:
            Execution result
        """
        # Implementation details...
```

### Workflow Interpreter

The `WorkflowInterpreter` class executes workflows:

```python
class WorkflowInterpreter:
    """
    Interpreter for executing workflows from a database.
    
    This class builds workflow graphs from configuration and executes them with user input.
    """
    
    def __init__(
        self,
        workflow_config: Dict[str, Any],
        llm: Optional[Any] = None,
        tools: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the workflow interpreter.
        
        Args:
            workflow_config: Workflow configuration
            llm: Language model for prompt execution
            tools: Tools available to the workflow
        """
        # Implementation details...
    
    def build_workflow_graph(self) -> StateGraph:
        """
        Build a workflow graph from the configuration.
        
        Returns:
            StateGraph instance
        """
        # Implementation details...
    
    async def execute(
        self, 
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the workflow with a user message.
        
        Args:
            message: User message
            session_id: Session ID
            context: Additional context
            
        Returns:
            Execution result
        """
        # Implementation details...
```

## State Management

Workflow state is managed as part of the session context:

```json
{
  "workflow_state": {
    "current_node": "verify_code",
    "extracted_entities": {
      "email": "user@example.com"
    },
    "nodes_visited": ["request_email", "validate_email", "send_code", "verify_code"],
    "tool_results": {
      "validate_email": {"valid": true, "exists": true},
      "send_code": {"sent": true, "code_id": "c123"}
    }
  }
}
```

## Best Practices

1. **Workflow Design**
   - Keep workflows focused on a single task
   - Design clear paths through the workflow
   - Include error handling for each step
   - Use meaningful node and edge names

2. **State Management**
   - Store entity values in workflow state
   - Persist state between conversation turns
   - Include sufficient context for LLM operations
   - Handle resuming interrupted workflows

3. **Error Handling**
   - Provide fallback paths for failed operations
   - Include user-friendly error messages
   - Log workflow execution for debugging
   - Add timeouts for long-running operations

4. **Testing**
   - Test each node individually
   - Verify edge conditions
   - Test complete workflows end-to-end
   - Include edge cases and error conditions

## Troubleshooting

| Issue | Possible Cause | Resolution |
|-------|----------------|------------|
| Workflow stuck on node | Missing edge condition | Add default edge or fix condition |
| Entity extraction failure | Unclear prompt | Improve prompt clarity or add examples |
| Tool execution error | Invalid parameters | Check parameter mappings in configuration |
| Infinite loop | Circular edge conditions | Review and fix workflow logic |
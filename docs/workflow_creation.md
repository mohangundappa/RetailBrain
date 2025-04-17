# Creating Workflow-Driven Agents

## Overview

Workflow-driven agents provide a powerful way to handle multi-step interactions with users. Unlike single-response agents, workflow agents maintain state across multiple conversation turns and can execute different actions based on the current state and user input.

This guide explains how to create, configure, and deploy workflow-driven agents in the Staples Brain system.

## Workflow Structure

A workflow consists of:

1. **Nodes** - Individual processing steps (prompts, tools, decision points)
2. **Edges** - Connections between nodes with conditions
3. **State** - Data maintained across the workflow execution

## Creating a Workflow Agent

### Step 1: Create Base Agent

First, create the base agent using the Agent Builder API:

```python
import aiohttp
import json

async def create_workflow_agent():
    async with aiohttp.ClientSession() as session:
        # Create agent definition
        agent_data = {
            "name": "Password Reset Agent",
            "description": "Helps users reset their passwords through a step-by-step process",
            "agent_type": "WORKFLOW_AGENT",
            "status": "active"
        }
        
        # POST to the agent builder endpoint
        async with session.post(
            "http://localhost:5000/api/v1/agent-builder/agents",
            json=agent_data
        ) as response:
            result = await response.json()
            agent_id = result["agent"]["id"]
            print(f"Created agent with ID: {agent_id}")
            return agent_id
```

### Step 2: Define Workflow Structure

Next, define the workflow structure with nodes and edges:

```python
async def create_workflow(agent_id):
    async with aiohttp.ClientSession() as session:
        # Define workflow structure
        workflow_data = {
            "name": "Password Reset Workflow",
            "description": "Step-by-step workflow for assisting users with password resets",
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
                },
                "completion": {
                    "type": "prompt",
                    "prompt": "Your password has been successfully reset. You can now log in with your new password.",
                    "output_key": "completion_response"
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
                ],
                "reset_password": [
                    {
                        "target": "completion",
                        "condition": "has_entity",
                        "condition_value": "new_password"
                    }
                ]
            },
            "entry_node": "request_email"
        }
        
        # POST to create workflow
        async with session.post(
            f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/workflow",
            json=workflow_data
        ) as response:
            result = await response.json()
            print(f"Created workflow: {result['success']}")
            return result.get("workflow_id")
```

### Step 3: Define Entity Extraction Patterns

Set up patterns to extract entities from user messages:

```python
async def add_entity_patterns(agent_id):
    async with aiohttp.ClientSession() as session:
        # Define entity extraction patterns
        entities = [
            {
                "name": "email",
                "patterns": [
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    r"my email is (.+)",
                    r"email address[:\s]+(.+)"
                ],
                "description": "Email address for account"
            },
            {
                "name": "verification_code",
                "patterns": [
                    r"\b\d{6}\b",
                    r"verification code[:\s]+(.+)",
                    r"code[:\s]+(.+)"
                ],
                "description": "Verification code sent to email"
            },
            {
                "name": "new_password",
                "patterns": [
                    r"new password[:\s]+(.+)",
                    r"password[:\s]+(.+)"
                ],
                "description": "New password for account reset"
            }
        ]
        
        # Add each entity pattern
        for entity in entities:
            async with session.post(
                f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/entities",
                json=entity
            ) as response:
                result = await response.json()
                print(f"Added entity pattern for {entity['name']}: {result['success']}")
```

### Step 4: Connect Agent to Tools

Register tools needed by the workflow:

```python
async def register_tools(agent_id):
    async with aiohttp.ClientSession() as session:
        # Define tools
        tools = [
            {
                "name": "validate_email",
                "description": "Validate an email address format and check if it exists in the system",
                "parameters": {
                    "email": {
                        "type": "string",
                        "description": "Email address to validate"
                    }
                }
            },
            {
                "name": "send_verification_code",
                "description": "Send a verification code to the provided email address",
                "parameters": {
                    "email": {
                        "type": "string",
                        "description": "Email address to send code to"
                    }
                }
            }
        ]
        
        # Register each tool
        for tool in tools:
            async with session.post(
                f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/tools",
                json=tool
            ) as response:
                result = await response.json()
                print(f"Registered tool {tool['name']}: {result['success']}")
```

### Step 5: Add Routing Patterns

Add patterns to help the orchestrator route to this agent:

```python
async def add_routing_patterns(agent_id):
    async with aiohttp.ClientSession() as session:
        # Define routing patterns
        patterns = [
            {
                "regex": r"password|reset password|forgot password|change password|login issue",
                "confidence": 0.85,
                "description": "Password reset intent detection"
            },
            {
                "regex": r"can'?t (log|sign) in|unable to (log|sign) in",
                "confidence": 0.8,
                "description": "Login issues intent detection"
            }
        ]
        
        # Add each pattern
        for pattern in patterns:
            async with session.post(
                f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/patterns",
                json=pattern
            ) as response:
                result = await response.json()
                print(f"Added routing pattern: {result['success']}")
```

## Node Types Reference

### Prompt Node

Displays a message to the user and collects their response.

```json
{
  "type": "prompt",
  "prompt": "Please provide your email address.",
  "output_key": "email_response"
}
```

### Tool Node

Executes a tool with parameters from the workflow state.

```json
{
  "type": "tool",
  "config": {
    "tool_name": "validate_email",
    "parameters": {
      "email": "{{email}}"
    }
  },
  "output_key": "email_validation_result"
}
```

### LLM Node

Uses an LLM to process input and generate output.

```json
{
  "type": "llm",
  "prompt_template": "Extract the following entities from this message: {{message}}",
  "output_key": "extracted_entities",
  "output_parser": "json"
}
```

### Condition Node

Makes decisions based on workflow state.

```json
{
  "type": "condition",
  "condition": "{{email_validation_result.valid}}",
  "output_key": "condition_result"
}
```

### End Node

Marks the end of a workflow path.

```json
{
  "type": "end",
  "end_message": "Thank you for using our password reset service."
}
```

## Edge Condition Types

### Has Entity

Transitions if an entity has been detected.

```json
{
  "target": "validate_email",
  "condition": "has_entity",
  "condition_value": "email"
}
```

### Tool Success

Transitions based on tool execution result.

```json
{
  "target": "send_code",
  "condition": "tool_success",
  "condition_value": true
}
```

### Value Match

Transitions if a value matches expected value.

```json
{
  "target": "success_node",
  "condition": "value_match",
  "condition_key": "verification_result.status",
  "condition_value": "verified"
}
```

### Default

Default transition if no other conditions match.

```json
{
  "target": "fallback_node",
  "condition": "default"
}
```

## Testing Workflow Agents

### Step 1: Execute Workflow Directly

Test the workflow agent by sending direct execution requests:

```python
async def test_workflow(agent_id):
    async with aiohttp.ClientSession() as session:
        # Test initial prompt
        test_data = {
            "message": "I need to reset my password",
            "agent_id": agent_id,
            "session_id": f"test-{agent_id}",
            "context": {}
        }
        
        async with session.post(
            "http://localhost:5000/api/v1/workflow-agents/execute",
            json=test_data
        ) as response:
            result = await response.json()
            print(f"Workflow response: {result['response']['message']}")
            
            # Continue with email response
            test_data = {
                "message": "My email is test@example.com",
                "agent_id": agent_id,
                "session_id": f"test-{agent_id}",
                "context": result.get("metadata", {}).get("context", {})
            }
            
            # Continue testing through the workflow...
```

### Step 2: End-to-End Testing

Test the entire workflow from start to finish:

```python
async def test_complete_workflow():
    # Create test session
    session_id = f"test-full-workflow-{uuid.uuid4()}"
    
    # Step 1: Initial message
    response1 = await send_message("I need to reset my password", session_id)
    print(f"Step 1: {response1['response']['message']}")
    
    # Step 2: Provide email
    response2 = await send_message("My email is test@example.com", session_id)
    print(f"Step 2: {response2['response']['message']}")
    
    # Step 3: Provide verification code
    response3 = await send_message("The code is 123456", session_id)
    print(f"Step 3: {response3['response']['message']}")
    
    # Step 4: Provide new password
    response4 = await send_message("My new password is SecurePass123!", session_id)
    print(f"Step 4: {response4['response']['message']}")
    
    # Final response should be completion message
    return response4
```

## State Management

Workflow state is managed across conversation turns:

```json
{
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
```

## Error Handling

Each node should include error handling:

1. **Tool Nodes** - Include failure edges
2. **Prompt Nodes** - Validate extracted entities
3. **Entity Extraction** - Handle missing or invalid data

Example error handling edge:

```json
{
  "target": "email_error",
  "condition": "tool_success",
  "condition_value": false
}
```

## Visualization

Workflow visualization is available through the frontend:

```
GET /api/v1/agent-workflow/{agent_id}/visualization
```

The response includes a JSON representation of the workflow graph that can be rendered using a visualization library like D3.js.

## Best Practices

1. **Node Design**
   - Keep prompts clear and concise
   - Include examples in prompts where helpful
   - Make tool parameters obvious from context
   - Use consistent naming conventions

2. **Edge Conditions**
   - Include default edges for unexpected cases
   - Create clear error paths
   - Validate entities before proceeding
   - Avoid complex conditional logic

3. **Testing**
   - Test each path independently
   - Test with valid and invalid inputs
   - Verify tool integrations
   - Test error recovery scenarios

4. **Workflow Structure**
   - Keep workflows focused on a single task
   - Break complex workflows into smaller ones
   - Design for logical conversation flow
   - Minimize unnecessary user interactions

5. **State Management**
   - Store all necessary context
   - Don't repeat questions unnecessarily
   - Maintain entity values across nodes
   - Clean up state when workflow completes
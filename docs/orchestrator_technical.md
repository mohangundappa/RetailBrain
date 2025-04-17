# Orchestrator Technical Documentation

## Implementation Details

The Staples Brain orchestrator is built on LangGraph and LangChain technologies, with a focus on database-driven agent configurations for maximum flexibility.

### Core Components

#### GraphBrainService

This service acts as the central orchestration engine. Key methods include:

```python
async def process_message(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a user message and generate a response.
    
    Args:
        message: User message
        session_id: Session identifier
        context: Additional context data
        
    Returns:
        Response data including agent, confidence, and response text
    """
    # Implementation details for message processing flow
```

The service manages a workflow graph created during initialization:

```python
def create_workflow_graph(self):
    """
    Create the LangGraph workflow graph for agent orchestration.
    This defines the execution flow between agents.
    """
    # Initialize StateGraph with LangGraph 0.3.x requirements
    from typing import Dict as DictType
    
    # For LangGraph 0.3.29, pass the type as the first arg
    builder = StateGraph(DictType)  # State is a dictionary
    
    # Add nodes to the graph
    builder.add_node("router", self._route_message)
    builder.add_node("executor", self._execute_agent)
    builder.add_node("guardrails", self._apply_guardrails)
    
    # Define edges between nodes
    builder.add_edge("router", "executor")
    builder.add_edge("executor", "guardrails")
    
    # Compile the graph
    self.graph = builder.compile()
```

#### Agent Router

The router component handles the selection of the most appropriate agent based on intent detection:

```python
async def route_message(self, message: str, context: Dict[str, Any] = None) -> Tuple[AgentDefinition, float, Dict[str, Any]]:
    """
    Route a message to the most appropriate agent.
    
    Args:
        message: User message
        context: Additional context data
        
    Returns:
        Tuple of (selected agent, confidence, updated context)
    """
    # Intent-first routing implementation
```

#### Agent Factory

The factory creates agent instances from database definitions:

```python
class LangGraphAgentFactory:
    """Factory for creating LangGraph-based agents from database definitions."""
    
    async def load_all_active_agents(self) -> List[LangGraphAgent]:
        """
        Load all active agents from the database.
        
        Returns:
            List of initialized LangGraphAgent instances
        """
        # Database loading implementation
```

### Database Schema

The orchestrator relies on several database tables:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `agents` | Core agent definitions | id, name, description, status, agent_type |
| `agent_configs` | Agent configuration details | agent_id, config_type, config_data (JSON) |
| `agent_patterns` | Intent detection patterns | agent_id, pattern_regex, confidence |
| `agent_entities` | Entity definitions | agent_id, entity_name, entity_type |
| `agent_workflows` | Workflow definitions | agent_id, workflow_id, nodes, edges |

### State Management

The orchestration system manages several types of state:

1. **Session State**: User conversation history and context
   ```python
   # Managed through memory service
   self.session_history[session_id] = []
   ```

2. **Workflow State**: Current position in the agent workflow
   ```python
   # LangGraph state for execution flow
   state = {
       "messages": messages,
       "current_agent_id": None,
       "context": context or {},
       "session_id": session_id,
       "user_input": message,
       "selected_agent": None,
       "confidence": 0.0,
       "processing_start": time.time(),
       "response": None,
       "trace": []
   }
   ```

3. **Agent State**: Per-agent memory and configuration state
   ```python
   # Each agent maintains its own state
   self.agent_state = {}
   ```

### API Models

The orchestrator uses well-defined API models for request and response handling:

```python
class GraphChatRequest(BaseModel):
    """Request model for graph chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ResponseContent(BaseModel):
    """Content model for response"""
    message: str = Field(..., description="Response message text")
    type: str = Field("text", description="Response content type")

class GraphChatResponse(BaseModel):
    """Response model for graph chat"""
    success: bool = Field(..., description="Whether the request was successful")
    response: ResponseContent = Field(..., description="Response content")
    conversation_id: Optional[str] = Field(None, description="ID of the conversation")
    external_conversation_id: Optional[str] = Field(None, description="External ID of the conversation")
    observability_trace_id: Optional[str] = Field(None, description="Observability trace ID")
    error: Optional[str] = Field(None, description="Error message if applicable")

class DirectAgentRequest(GraphChatRequest):
    """Request model for direct agent execution"""
    agent_id: str = Field(..., description="ID of the agent to execute")
```

### Execution Flow

1. Message received through `/api/v1/graph-chat/chat` endpoint
   ```python
   @router.post("/chat", response_model=GraphChatResponse)
   async def graph_chat(
       request: GraphChatRequest,
       brain_service: GraphBrainService = Depends(get_graph_brain_service)
   ):
       """Process a chat message using the LangGraph-based brain service."""
       return await _process_graph_chat_request(request, brain_service)
   ```

2. `_process_graph_chat_request()` calls `GraphBrainService.process_message()` with the message, session_id, and context
   ```python
   async def _process_graph_chat_request(
       request: GraphChatRequest,
       brain_service: GraphBrainService
   ) -> GraphChatResponse:
       """Process a chat request using the LangGraph brain service."""
       result = await brain_service.process_message(
           message=request.message,
           session_id=request.session_id,
           context=request.context
       )
       # Construct response...
   ```

3. LangGraph workflow executes:
   - Router node performs intent detection
   - Executor node invokes selected agent
   - Guardrails node ensures response quality
   
4. Response returned to caller

### Error Handling

The orchestrator implements several error handling strategies:

```python
try:
    # Main processing logic
except AgentExecutionError as e:
    # Handle agent-specific errors
    logger.error(f"Agent execution error: {str(e)}", exc_info=True)
    return {
        "success": False,
        "error": f"Agent error: {str(e)}",
        "response": "I encountered an issue while processing your request. Please try again."
    }
except Exception as e:
    # Handle general errors
    logger.error(f"Error processing message: {str(e)}", exc_info=True)
    return {
        "success": False,
        "error": f"Processing error: {str(e)}",
        "response": "I'm sorry, but I encountered an unexpected error. Please try again later."
    }
```

## API Reference

### GraphBrainService

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `initialize()` | Initialize service | None | `bool` - Success |
| `process_message()` | Process user message | message, session_id, context | Response dict |
| `create_workflow_graph()` | Build LangGraph workflow | None | None |
| `_route_message()` | Select agent | state | Updated state |
| `_execute_agent()` | Execute selected agent | state | Updated state |
| `_apply_guardrails()` | Apply safety checks | state | Updated state |

### Agent Router

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `route_message()` | Route to best agent | message, context | (agent, confidence, context) |
| `keyword_prefilter()` | Pattern matching | query | List of matching agents |
| `_seems_conversational()` | Detect conversation | query | Boolean |
| `_get_general_agent()` | Get fallback agent | None | Agent definition |

## Best Practices

1. **New Agent Integration**
   - Register the agent in the database
   - Define pattern capabilities for intent detection
   - Implement specialized handling logic

2. **Pattern Optimization**
   - Focus on unique, specific patterns per agent
   - Assign appropriate confidence levels
   - Test with varied user inputs

3. **Workflow Customization**
   - Modify create_workflow_graph() to add custom nodes
   - Ensure proper edge connections between nodes
   - Maintain state consistency across nodes

4. **Debugging**
   - Review session_history for conversation context
   - Check confidence scores in agent selection
   - Examine trace output for workflow execution details
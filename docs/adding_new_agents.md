# Adding New Agents to Staples Brain

This guide provides step-by-step instructions for adding new agents to the Staples Brain orchestration system.

## Overview

Adding a new agent involves:
1. Creating a database record for the agent definition
2. Configuring pattern capabilities for intent detection
3. Implementing the agent's specialized handling logic
4. Testing and deploying the agent

## Step 1: Define the Agent in the Database

New agents can be added through:
- The Agent Builder API (`/api/v1/agent-builder/agents`)
- Direct database insertion
- Admin UI (if available)

### Using the Agent Builder API

The agent builder API provides endpoints for managing agent definitions:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/agent-builder/agents` | POST | Create a new agent definition |
| `/api/v1/agent-builder/agents/{agent_id}` | GET | Retrieve agent details |
| `/api/v1/agent-builder/agents/{agent_id}` | PATCH | Update agent definition |
| `/api/v1/agent-builder/agents/{agent_id}/patterns` | POST | Add pattern capabilities |

```python
import aiohttp
import json

async def create_agent():
    async with aiohttp.ClientSession() as session:
        # Create basic agent definition
        agent_data = {
            "name": "Product Recommendation Agent",
            "description": "Suggests products based on customer needs and preferences",
            "agent_type": "PRODUCT_RECOMMENDATION",
            "status": "active"
        }
        
        # POST to the agent builder endpoint
        async with session.post(
            "http://localhost:5000/api/v1/agent-builder/agents",
            json=agent_data
        ) as response:
            result = await response.json()
            agent_id = result["data"]["id"]
            print(f"Created agent with ID: {agent_id}")
            return agent_id
```

## Step 2: Configure Intent Detection Patterns

For effective routing, define patterns that identify when this agent should be selected:

```python
async def add_agent_patterns(agent_id):
    async with aiohttp.ClientSession() as session:
        # Define patterns for intent detection
        patterns = [
            {
                "regex": r"recommend|suggest|what product|which product",
                "confidence": 0.75,
                "description": "Product recommendation intent detection"
            },
            {
                "regex": r"best (product|option) for|looking for a",
                "confidence": 0.8,
                "description": "Specific product search intent"
            }
        ]
        
        # Add each pattern to the agent
        for pattern in patterns:
            async with session.post(
                f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/patterns",
                json=pattern
            ) as response:
                result = await response.json()
                print(f"Added pattern: {result['data']['id']}")
```

## Step 3: Implement Agent Logic

### Database-Driven Agent Implementation

For agents defined entirely in the database:

1. Create prompt templates:
```python
async def add_agent_prompts(agent_id):
    async with aiohttp.ClientSession() as session:
        prompts = {
            "system_prompt": "You are a Product Recommendation specialist for Staples. Help customers find the perfect products based on their needs. Focus on office supplies, furniture, technology, and business services.",
            "user_prompt_template": "Please suggest products for this request: {{user_message}}",
            "response_format": "I recommend the following products for your needs:\n{{#each products}}\n- {{this.name}}: {{this.description}} ({{this.price}})\n{{/each}}"
        }
        
        async with session.post(
            f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/prompts",
            json=prompts
        ) as response:
            result = await response.json()
            print(f"Added prompts: {result['success']}")
```

2. Configure tools (if needed):
```python
async def add_agent_tools(agent_id):
    async with aiohttp.ClientSession() as session:
        tools = [
            {
                "name": "search_products",
                "description": "Search for products in the Staples catalog",
                "parameters": {
                    "keywords": {
                        "type": "string", 
                        "description": "Keywords to search for"
                    },
                    "category": {
                        "type": "string", 
                        "description": "Optional product category"
                    }
                }
            }
        ]
        
        async with session.post(
            f"http://localhost:5000/api/v1/agent-builder/agents/{agent_id}/tools",
            json={"tools": tools}
        ) as response:
            result = await response.json()
            print(f"Added tools: {result['success']}")
```

### Custom Agent Implementation

For more complex agents requiring custom code:

1. Create a new agent class in `backend/agents/specialized/`:

```python
# product_recommendation_agent.py
from backend.agents.framework.langgraph.database_agent import DatabaseAgent
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ProductRecommendationAgent(DatabaseAgent):
    """Agent that recommends products based on customer needs."""
    
    async def process_message(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message and generate product recommendations.
        
        Args:
            message: User message
            session_id: Session identifier
            context: Additional context data
            
        Returns:
            Response with recommended products
        """
        # Extract product needs from message
        product_needs = await self._extract_product_needs(message)
        
        # Search for matching products
        recommended_products = await self._search_products(product_needs)
        
        # Format recommendations
        response = self._format_recommendations(recommended_products)
        
        return {
            "success": True,
            "response": response,
            "agent": self.name,
            "metadata": {
                "product_count": len(recommended_products)
            }
        }
    
    async def _extract_product_needs(self, message: str) -> Dict[str, Any]:
        """Extract product needs from user message."""
        # Implementation details...
        
    async def _search_products(self, product_needs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for products matching the user's needs."""
        # Implementation details...
        
    def _format_recommendations(self, products: List[Dict[str, Any]]) -> str:
        """Format product recommendations into a response."""
        # Implementation details...
```

2. Register the agent factory in `backend/agents/framework/langgraph/agent_factory_util.py`:

```python
def create_agent_from_definition(agent_def: AgentDefinition, db_session) -> Optional[LangGraphAgent]:
    """Create a LangGraph agent from an agent definition."""
    try:
        # Handle different agent types
        if "product recommendation" in agent_def.name.lower():
            from backend.agents.specialized.product_recommendation_agent import ProductRecommendationAgent
            return ProductRecommendationAgent(agent_def, db_session)
        
        # Other agent types...
        
    except Exception as e:
        logger.error(f"Error creating agent from definition: {str(e)}", exc_info=True)
        return None
```

## Step 4: Testing Your Agent

### Test Direct Agent Execution

Use the direct agent execution endpoint to test your agent:

```python
async def test_agent(agent_id, test_message):
    async with aiohttp.ClientSession() as session:
        test_data = {
            "message": test_message,
            "agent_id": agent_id,
            "session_id": f"test-{agent_id}",
            "context": {}
        }
        
        async with session.post(
            "http://localhost:5000/api/v1/graph-chat/execute-agent",
            json=test_data
        ) as response:
            result = await response.json()
            print(f"Agent response: {result['response']['message']}")
            return result
```

### Test Agent Routing

Ensure the orchestrator correctly routes to your agent:

```python
async def test_agent_routing(test_message, expected_agent_name):
    async with aiohttp.ClientSession() as session:
        test_data = {
            "message": test_message,
            "session_id": f"test-routing-{uuid.uuid4()}",
            "context": {}
        }
        
        async with session.post(
            "http://localhost:5000/api/v1/graph-chat/chat",
            json=test_data
        ) as response:
            result = await response.json()
            selected_agent = result.get("metadata", {}).get("agent", "unknown")
            confidence = result.get("metadata", {}).get("confidence", 0)
            
            print(f"Selected agent: {selected_agent} (Confidence: {confidence})")
            print(f"Response: {result['response']['message']}")
            
            return selected_agent == expected_agent_name
```

## Best Practices

1. **Agent Design**
   - Focus on a single specific capability
   - Define clear boundaries between agent responsibilities
   - Ensure prompt templates are tailored to the agent's domain

2. **Pattern Capabilities**
   - Use specific, unique patterns relevant to your agent
   - Set appropriate confidence thresholds for pattern matches
   - Include variations in terminology and phrasing

3. **Tool Integration**
   - Keep tools focused and well-documented
   - Validate tool inputs before processing
   - Handle tool failures gracefully

4. **Testing**
   - Test with diverse user inputs
   - Verify confidence scores are appropriate
   - Ensure agent correctly handles edge cases

## Troubleshooting

### Agent Not Being Selected

If your agent isn't being selected by the orchestrator:

1. Check pattern confidence levels (may be too low)
2. Ensure patterns are specific enough to your agent's domain
3. Test patterns directly against test inputs
4. Review orchestrator logs for routing decisions

### Agent Errors During Execution

If your agent encounters errors:

1. Check database configuration completeness
2. Verify tool implementations and connections
3. Ensure prompt templates are properly formatted
4. Look for errors in custom agent code

### Poor Agent Responses

If your agent produces low-quality responses:

1. Refine system and user prompt templates
2. Add more specific examples to the prompt
3. Implement additional guardrails checks
4. Consider adding post-processing logic
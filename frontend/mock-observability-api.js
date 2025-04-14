/**
 * Mock Observability API
 * 
 * This module provides mock implementations of the observability API endpoints
 * for development and testing purposes when the real backend API is not available.
 */

// Mock backend route handler for Express
function setupMockObservabilityRoutes(app) {
    // Mock observability data endpoint
    app.get('/api/v1/chat/observability/:conversation_id', (req, res) => {
        const conversationId = req.params.conversation_id;
        console.log(`[Mock API] Request for observability data for conversation: ${conversationId}`);
        
        // Return mock data for demonstration
        const mockData = generateMockObservabilityData(conversationId);
        
        // Simulate network delay
        setTimeout(() => {
            res.json({
                success: true,
                data: mockData
            });
        }, 500);
    });
    
    console.log('[Mock API] Observability routes initialized');
}

// Generate mock observability data
function generateMockObservabilityData(conversationId) {
    const timestamp = new Date().toISOString();
    
    // Get agent based on conversation ID to make it somewhat consistent
    const agents = [
        'General Conversation Agent',
        'Package Tracking Agent',
        'Reset Password Agent',
        'Store Locator Agent',
        'Product Information Agent',
        'Returns Processing Agent'
    ];
    
    // Use the last character of the conversation ID to deterministically select an agent
    const lastChar = conversationId.charAt(conversationId.length - 1);
    const agentIndex = parseInt(lastChar, 16) % agents.length;
    const selectedAgent = agents[agentIndex];
    
    return {
        conversation_id: conversationId,
        timestamp: timestamp,
        request: {
            message: "Sample user message for testing observability features",
            conversation_id: conversationId,
            has_context: Math.random() > 0.5
        },
        processing: {
            intent_detection: {
                intents: {
                    "find_store": 0.75,
                    "product_info": 0.15,
                    "general_inquiry": 0.10
                },
                selected_intent: selectedAgent,
                context_influence: {
                    "weight": 0.3,
                    "factors": ["user_history", "recent_interactions"]
                }
            },
            entity_extraction: {
                entities: {
                    "location": "Boston",
                    "product_category": "Office Supplies",
                    "time_reference": "today"
                }
            },
            agent_selection: {
                selected_agent: selectedAgent,
                version: "1.0",
                reasoning: "Selected based on primary intent detection and available context information. The user's query matches patterns typically handled by this specialized agent.",
                personalization_applied: Math.random() > 0.5
            },
            execution_graph: {
                nodes: ["intent", "entity", "agent", "response"],
                current_node: "response",
                execution_path: [
                    {
                        node: "intent",
                        start_time: new Date(Date.now() - 1200).toISOString(),
                        end_time: new Date(Date.now() - 1000).toISOString()
                    },
                    {
                        node: "entity",
                        start_time: new Date(Date.now() - 1000).toISOString(),
                        end_time: new Date(Date.now() - 800).toISOString()
                    },
                    {
                        node: "agent",
                        start_time: new Date(Date.now() - 800).toISOString(),
                        end_time: new Date(Date.now() - 300).toISOString()
                    },
                    {
                        node: "response",
                        start_time: new Date(Date.now() - 300).toISOString(),
                        end_time: new Date(Date.now() - 100).toISOString()
                    }
                ]
            }
        },
        memory: {
            keys_accessed: ["user_preferences", "recent_conversations"],
            state_updates: ["conversation_history", "entity_memory"]
        }
    };
}

module.exports = {
    setupMockObservabilityRoutes
};
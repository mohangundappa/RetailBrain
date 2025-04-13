const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3001;

// Create a simple HTTP server
const server = http.createServer((req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle OPTIONS request
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  // Serve the dashboard
  if (req.url === '/' || req.url === '/index.html') {
    fs.readFile(path.join(__dirname, 'static-app.html'), (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading static-app.html');
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  
  // Serve the context-aware chat interface
  if (req.url === '/chat' || req.url === '/chat.html') {
    fs.readFile(path.join(__dirname, 'context-chat.html'), (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading context-chat.html');
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  
  // Mock API for chat interface
  if (req.url === '/api/v1/chat' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    
    req.on('end', () => {
      try {
        const requestData = JSON.parse(body);
        const conversationId = requestData.conversation_id || `conv_${Date.now()}`;
        const hasContext = !!(requestData.context && (requestData.context.identity || requestData.context.customer_profile));
        
        // Generate a response based on the message
        const message = requestData.message.toLowerCase();
        let responseText = '';
        
        if (hasContext && requestData.context.customer_profile) {
          // Personalized response
          const customerName = requestData.context.customer_profile.email.split('@')[0].replace('.', ' ');
          
          if (message.includes('store') || message.includes('location')) {
            responseText = `Hi ${customerName}, I can help you find a Staples store. The closest Staples to you is at 401 Park Drive, Boston, MA 02215. It's open from 8 AM to 9 PM Monday through Saturday, and 10 AM to 6 PM on Sunday.`;
          } else if (message.includes('order') || message.includes('package')) {
            responseText = `Hi ${customerName}, I've found your recent orders. Your most recent order #ORD-987654 was delivered on April 1st, and you have another order #ORD-876543 that's currently processing.`;
          } else {
            responseText = `Hello ${customerName}, thanks for your question. I'm here to help with store locations, order tracking, and other Staples-related inquiries. What specific information are you looking for today?`;
          }
        } else {
          // Generic response
          if (message.includes('store') || message.includes('location')) {
            responseText = 'I can help you find a Staples store. Could you provide your city or zip code so I can locate the nearest store to you?';
          } else if (message.includes('order') || message.includes('package')) {
            responseText = 'I can help you track your order. Could you provide your order number or the email address used for the purchase?';
          } else {
            responseText = 'Thank you for your question. I\'m here to help with store locations, order tracking, and other Staples-related inquiries. What specific information are you looking for today?';
          }
        }
        
        // Response object
        const responseObj = {
          success: true,
          data: {
            message: responseText,
            conversation_id: conversationId,
            timestamp: new Date().toISOString()
          },
          metadata: {
            processing_time_ms: 500,
            context_used: hasContext
          }
        };
        
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(responseObj));
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
          success: false, 
          error: 'Invalid request format'
        }));
      }
    });
    
    return;
  }
  
  // Mock observability API
  if (req.url.startsWith('/api/v1/chat/observability/') && req.method === 'GET') {
    const conversationId = req.url.split('/').pop();
    
    // Create mock observability data
    const observabilityData = {
      conversation_id: conversationId,
      timestamp: new Date().toISOString(),
      request: {
        message: "Sample user message",
        conversation_id: conversationId,
        has_context: true
      },
      processing: {
        intent_detection: {
          intents: [
            {"intent": "store_locator", "confidence": 0.78},
            {"intent": "order_tracking", "confidence": 0.12},
            {"intent": "general_query", "confidence": 0.10}
          ],
          selected_intent: "store_locator",
          context_influence: {
            "preferred_store_factor": 0.9
          }
        },
        entity_extraction: {
          entities: [
            {"type": "location", "value": "Boston", "confidence": 0.95}
          ]
        },
        agent_selection: {
          selected_agent: "store_locator",
          version: "1.0",
          reasoning: "Keyword-based intent detection",
          personalization_applied: true
        },
        execution_graph: {
          nodes: ["intent", "entity", "agent", "response"],
          current_node: "response",
          execution_path: [
            {
              "node": "intent", 
              "start_time": new Date(Date.now() - 400).toISOString(),
              "end_time": new Date(Date.now() - 350).toISOString()
            },
            {
              "node": "entity",
              "start_time": new Date(Date.now() - 340).toISOString(),
              "end_time": new Date(Date.now() - 280).toISOString()
            },
            {
              "node": "agent", 
              "start_time": new Date(Date.now() - 270).toISOString(),
              "end_time": new Date(Date.now() - 200).toISOString()
            },
            {
              "node": "response", 
              "start_time": new Date(Date.now() - 190).toISOString(),
              "end_time": new Date(Date.now() - 100).toISOString()
            }
          ]
        }
      }
    };
    
    const responseObj = {
      success: true,
      data: observabilityData
    };
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(responseObj));
    return;
  }
  
  // Mock conversations API
  if (req.url === '/api/v1/chat/conversations' && req.method === 'GET') {
    const responseObj = {
      success: true,
      data: [
        {
          id: "conv_123456",
          title: "Where is the nearest Staples?",
          timestamp: new Date(Date.now() - 1000000).toISOString(),
          message_count: 3
        },
        {
          id: "conv_234567",
          title: "Track my order please",
          timestamp: new Date(Date.now() - 2000000).toISOString(),
          message_count: 5
        }
      ]
    };
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(responseObj));
    return;
  }
  
  // Mock conversation history API
  if (req.url.startsWith('/api/v1/chat/conversations/') && req.method === 'GET') {
    const conversationId = req.url.split('/').pop();
    
    const responseObj = {
      success: true,
      data: {
        id: conversationId,
        title: "Sample conversation",
        messages: [
          {
            role: "user",
            content: "Where is the nearest Staples store?",
            timestamp: new Date(Date.now() - 1000000).toISOString()
          },
          {
            role: "assistant",
            content: "I can help you find a Staples store. The closest one to you is at 401 Park Drive, Boston, MA 02215. It's open from 8 AM to 9 PM Monday through Saturday, and 10 AM to 6 PM on Sunday.",
            timestamp: new Date(Date.now() - 990000).toISOString()
          }
        ],
        context: {
          identity: {
            visitor_id: "visitor_12345",
            authentication_level: "none"
          }
        }
      }
    };
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(responseObj));
    return;
  }
  
  // Handle other API requests
  if (req.url.startsWith('/api/')) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      success: false, 
      error: 'API endpoint not found'
    }));
    return;
  }
  
  // For any other request, return 404
  res.writeHead(404);
  res.end('Not found');
});

// Start the server
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Frontend server running at http://0.0.0.0:${PORT}`);
});
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3001;

// We'll use port 5000 for the backend as requested by the user
const BACKEND_PORT = 5000;
process.env.BACKEND_PORT = BACKEND_PORT.toString();
console.log(`Using backend port ${BACKEND_PORT} as requested`);

// For reference, port file location
const backendPortFile = path.join(__dirname, '..', 'backend_port.txt');

// Create a simple HTTP server
const server = http.createServer((req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Parse URL and query parameters
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const query = parsedUrl.query;
  
  // Enhance logging for debugging
  console.log(`Request received: ${req.method} ${req.url}`);
  console.log(`Parsed pathname: ${pathname}, Query params:`, query);
  
  // Handle OPTIONS request
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  // Serve the dashboard
  if (pathname === '/' || pathname === '/index.html') {
    console.log('Serving dashboard page');
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
  
  // Serve the context-aware chat interface - use exact URL matching to prevent bleed-through to backend
  if (pathname === '/chat' || pathname === '/chat.html' || pathname === '/chat/') {
    console.log('Serving simple chat interface page from frontend server');
    fs.readFile(path.join(__dirname, 'simple-chat.html'), (err, data) => {
      if (err) {
        console.error('Error reading simple-chat.html:', err);
        res.writeHead(500);
        res.end('Error loading simple-chat.html');
        return;
      }
      
      // Set content-type explicitly
      res.writeHead(200, { 
        'Content-Type': 'text/html',
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': 'no-store'
      });
      res.end(data);
    });
    return;
  }
  
  // Serve the agent routing architecture diagram
  if (pathname === '/routing-architecture' || pathname === '/agent_routing_architecture.html') {
    fs.readFile(path.join(__dirname, 'agent_routing_architecture.html'), (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading agent_routing_architecture.html');
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  
  // Serve the test page - check pathname and query parameters
  if (pathname === '/test' || 
      pathname === '/test.html' || 
      (pathname === '/' && (query.frontend_page === 'test' || query.page === 'test'))) {
    
    console.log('Serving test page');
    fs.readFile(path.join(__dirname, 'test.html'), (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading test.html');
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  
  // Handle API requests
  if (req.url.startsWith('/api/')) {
    console.log(`API request received: ${req.method} ${req.url}`);
    
    // Special case for chat API - implement our own mock instead of proxying
    if (req.url === '/api/v1/chat' && req.method === 'POST') {
      console.log("Handling chat API request with embedded mock handler");
      
      // Collect the request body
      let body = '';
      req.on('data', (chunk) => {
        body += chunk.toString();
      });
      
      req.on('end', () => {
        try {
          console.log('Chat request body:', body);
          const requestData = JSON.parse(body);
          const message = requestData.message;
          const sessionId = requestData.session_id || 'default-session';
          
          // Store conversation history in memory using the session ID
          if (!global.conversationHistory) {
            global.conversationHistory = {};
          }
          
          if (!global.conversationHistory[sessionId]) {
            global.conversationHistory[sessionId] = [];
          }
          
          // Add user message to history
          global.conversationHistory[sessionId].push({
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
          });
          
          // Get the last 5 messages for context
          const lastMessages = global.conversationHistory[sessionId].slice(-5);
          
          // Check if we're in a specific conversation flow
          let responseText = '';
          let agentName = 'General Conversation Agent';
          let entities = [];
          
          // Function to check if we're in a specific conversation flow
          const isInFlow = (agent, pattern) => {
            return lastMessages.some(msg => {
              if (msg.role === 'assistant' && msg.agent === agent && msg.content.match(pattern)) {
                return true;
              }
              return false;
            });
          };
          
          // Email response to password reset flow
          const inPasswordResetFlow = isInFlow('Reset Password Agent', /email|confirm/i);
          if (inPasswordResetFlow && message.includes('@')) {
            responseText = `Thank you for confirming your email address (${message}). I've sent a password reset link to this email. Please check your inbox and follow the instructions in the email to reset your password. The link will expire in 24 hours.`;
            agentName = 'Reset Password Agent';
            entities = [{ value: message, type: 'email_address' }];
          }
          // Standard keyword-based routing
          else if (message.toLowerCase().includes('track') || message.toLowerCase().includes('package') || message.toLowerCase().includes('order')) {
            responseText = "I can help you track your package. Could you please provide your order number?";
            agentName = "Package Tracking Agent";
          } else if (message.toLowerCase().includes('password') || message.toLowerCase().includes('reset')) {
            responseText = "I can help you reset your password. For security reasons, I'll need to verify your identity first. Could you please confirm the email address associated with your account?";
            agentName = "Reset Password Agent";
          } else if (message.toLowerCase().includes('store') || message.toLowerCase().includes('location')) {
            responseText = "I can help you find the nearest Staples store. Could you please share your zip code or city and state?";
            agentName = "Store Locator Agent";
          } else if (message.toLowerCase().includes('product') || message.toLowerCase().includes('item')) {
            responseText = "I'd be happy to provide information about our products. Which specific item are you interested in?";
            agentName = "Product Information Agent";
          } else if (message.toLowerCase().includes('return') || message.toLowerCase().includes('exchange')) {
            responseText = "I can help with your return or exchange. Do you have your order number and the item you'd like to return?";
            agentName = "Returns Processing Agent";
          } else {
            responseText = "Thanks for your message. How else can I assist you with Staples products or services today?";
            agentName = "General Conversation Agent";
          }
          
          // Add assistant message to history
          global.conversationHistory[sessionId].push({
            role: 'assistant',
            content: responseText,
            agent: agentName,
            timestamp: new Date().toISOString()
          });
          
          // Prepare mock observability data
          const observabilityData = {
            agent_selection: {
              agents: [
                {
                  name: "Guardrails Agent",
                  icon: "shield-check",
                  description: "Safety validation passed",
                  confidence: 1.0,
                  selected: true
                },
                {
                  name: agentName,
                  icon: "chat-dots",
                  description: "Primary responding agent",
                  confidence: 0.9,
                  selected: true
                }
              ]
            },
            tools_executed: [
              {
                name: `${agentName}ResponseGenerator`,
                parameters: {
                  message: message.substring(0, 50) + (message.length > 50 ? "..." : ""),
                  session_id: sessionId
                },
                success: true
              }
            ],
            entities: entities
          };
          
          // Generate a trace ID
          const traceId = `trace-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
          
          // Create mock response
          const response = {
            success: true,
            data: {
              message: responseText,
              agent: agentName,
              session_id: sessionId,
              observability_trace_id: traceId
            },
            metadata: {
              processing_time_ms: 345,
              observability_available: true
            }
          };
          
          // Store observability data for retrieval
          if (!global.observabilityData) {
            global.observabilityData = {};
          }
          global.observabilityData[traceId] = observabilityData;
          
          // Send the response
          res.writeHead(200, { 'Content-Type': 'application/json' });
          const responseJson = JSON.stringify(response);
          console.log('Mock API response:', responseJson);
          res.end(responseJson);
          
        } catch (error) {
          console.error('Error processing chat request:', error);
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: false,
            error: `Error processing request: ${error.message}`
          }));
        }
      });
      
      return;
    }
    
    // Handle observability API
    if (req.url.startsWith('/api/v1/chat/observability/') && req.method === 'GET') {
      console.log("Handling observability API request with embedded mock handler");
      
      // Extract trace ID from URL
      const traceId = req.url.split('/api/v1/chat/observability/')[1].split('?')[0];
      console.log(`Requested observability data for trace ID: ${traceId}`);
      
      if (global.observabilityData && global.observabilityData[traceId]) {
        // Return stored observability data
        res.writeHead(200, { 'Content-Type': 'application/json' });
        const response = {
          success: true,
          data: global.observabilityData[traceId]
        };
        res.end(JSON.stringify(response));
      } else {
        // No data found
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: false,
          error: `No observability data found for trace ID: ${traceId}`
        }));
      }
      
      return;
    }
    
    // For all other API requests, attempt to proxy to the backend
    const backendHost = '127.0.0.1';
    const backendPort = process.env.BACKEND_PORT || BACKEND_PORT;
    
    console.log(`Proxying API request to ${backendHost}:${backendPort}${req.url}`);
    
    // Copy headers from original request but clean them up
    const headers = {};
    for (const [key, value] of Object.entries(req.headers)) {
      // Skip headers that might cause issues when proxying
      if (['host', 'connection', 'origin', 'referer'].includes(key.toLowerCase())) {
        continue;
      }
      headers[key] = value;
    }
    
    // Set clean headers needed for the proxy
    headers['host'] = `${backendHost}:${backendPort}`;
    headers['connection'] = 'keep-alive';
    headers['content-type'] = 'application/json';
    headers['accept'] = 'application/json';
    
    // Create proxy request to backend API server
    const options = {
      hostname: backendHost,
      port: backendPort,
      path: req.url,
      method: req.method,
      headers: headers,
      timeout: 30000 // 30 second timeout
    };
    
    // Log complete options for debugging
    console.log('Proxy request options:', {
      url: `${backendHost}:${backendPort}${req.url}`,
      method: req.method,
      headers: headers
    });
    
    // Create proxy request to backend
    const proxyReq = http.request(options, (proxyRes) => {
      console.log(`Got response from backend: status ${proxyRes.statusCode}`);
      
      // Set response headers
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      
      // Collect and log the response body for debugging
      let responseBody = '';
      proxyRes.on('data', (chunk) => {
        responseBody += chunk;
      });
      
      proxyRes.on('end', () => {
        console.log('Backend API response body:', responseBody);
        
        // Send the response to the client
        res.end(responseBody);
      });
    });
    
    // Handle errors
    proxyReq.on('error', (error) => {
      console.error(`Error proxying request to ${options.hostname}:${options.port}${req.url}:`, error.message);
      
      // Return a fallback response when backend is unavailable
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: false,
        error: 'Backend service unavailable',
        message: `Cannot connect to backend at ${options.hostname}:${options.port}. Please check if the API server is running.`
      }));
    });
    
    // Forward request body to backend
    if (req.method === 'POST' || req.method === 'PUT') {
      req.on('data', (chunk) => {
        proxyReq.write(chunk);
      });
      
      req.on('end', () => {
        proxyReq.end();
      });
    } else {
      proxyReq.end();
    }
    
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
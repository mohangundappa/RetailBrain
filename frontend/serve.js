const http = require('http');
const fs = require('fs');
const path = require('path');

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
    fs.readFile(path.join(__dirname, 'chat-interface.html'), (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading chat-interface.html');
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  
  // Serve the agent routing architecture diagram
  if (req.url === '/routing-architecture' || req.url === '/agent_routing_architecture.html') {
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
  
  // Proxy API requests to backend server
  if (req.url.startsWith('/api/')) {
    // Get backend hostname and port from environment or use defaults
    // For Replit, we need to use 127.0.0.1 instead of localhost to avoid DNS resolution issues
    const backendHost = '127.0.0.1';
    const backendPort = process.env.BACKEND_PORT || BACKEND_PORT;
    
    console.log(`Proxying API request to ${backendHost}:${backendPort}${req.url}`);
    
    // Copy headers from original request
    const headers = {...req.headers};
    
    // Override specific headers needed for the proxy
    headers['host'] = `${backendHost}:${backendPort}`;
    headers['origin'] = `http://${backendHost}:${backendPort}`;
    headers['content-type'] = headers['content-type'] || 'application/json';
    headers['accept'] = 'application/json';
    headers['connection'] = 'keep-alive';
    
    // Proxy request to backend API server
    const options = {
      hostname: backendHost,
      port: backendPort,
      path: req.url,
      method: req.method,
      headers: headers,
      timeout: 30000 // 30 second timeout
    };
    
    // Create proxy request to backend
    const proxyReq = http.request(options, (proxyRes) => {
      // Set response headers
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      
      // Forward response data
      proxyRes.pipe(res);
    });
    
    // Handle errors
    proxyReq.on('error', (error) => {
      console.error(`Error proxying request to ${options.hostname}:${options.port}${req.url}:`, error.message);
      
      // For API requests to /agents, provide a mock response with system agents included
      if (req.url === '/api/v1/agents') {
        console.log('Returning cached agents response since backend is unavailable');
        
        // Check if we're running in a development environment
        const isDev = process.env.NODE_ENV !== 'production';
        
        // Find the port that the real API is running on
        const expectedPort = process.env.BACKEND_PORT || BACKEND_PORT;
        console.log(`The backend API should be running on port ${expectedPort}, but we couldn't connect. Please check if the backend server is running.`);
        
        // Return a fallback response with the list of agents - this should include the system agents
        res.writeHead(200, { 'Content-Type': 'application/json' });
        
        // Try to make a direct HTTP request to the backend at a different port to see if it's running
        // We'll only use port 5000 for the backend API as requested
        const tryBackendPorts = [5000];
        console.log(`Trying to find backend on ports: ${tryBackendPorts.join(', ')}`);
        
        let portFound = false;
        let portChecks = 0;
        
        // Check each port
        tryBackendPorts.forEach(portToCheck => {
          const testReq = http.request({
            hostname: '127.0.0.1',
            port: portToCheck,
            path: '/api/v1/agents',
            method: 'GET',
            headers: {'Accept': 'application/json'}
          }, (testRes) => {
            // If we get a response, read it and proxy it back
            let data = '';
            testRes.on('data', (chunk) => {
              data += chunk;
            });
            
            testRes.on('end', () => {
              if (!portFound) {
                portFound = true;
                console.log(`✅ Found working backend API on port ${portToCheck}!`);
                console.log(`Updating BACKEND_PORT environment variable to ${portToCheck}`);
                BACKEND_PORT = portToCheck;
                process.env.BACKEND_PORT = portToCheck.toString();
                
                // Write to port file for future use
                try {
                  fs.writeFileSync(backendPortFile, portToCheck.toString());
                  console.log(`Updated ${backendPortFile} with new port ${portToCheck}`);
                } catch (e) {
                  console.error(`Failed to write port file: ${e.message}`);
                }
                
                // Forward the successful response
                res.end(data);
              }
            });
          });
          
          testReq.on('error', () => {
            portChecks++;
            // If we've checked all ports and none worked, return an error
            if (portChecks === tryBackendPorts.length && !portFound) {
              console.log('❌ Could not find backend API on any port');
              res.end(JSON.stringify({
                success: false,
                error: 'Backend service unavailable',
                message: `Cannot connect to backend. Tried ports ${tryBackendPorts.join(', ')}. Please restart the backend API server.`
              }));
            }
          });
          
          testReq.end();
        });
      } else {
        // Return a fallback response when backend is unavailable for other endpoints
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: false,
          error: 'Backend service unavailable',
          message: `Cannot connect to backend at ${options.hostname}:${options.port}. Please check if the API server is running.`
        }));
      }
    });
    
    // Forward request body to backend
    if (req.method === 'POST' || req.method === 'PUT') {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk.toString();
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
  
  // No need for specific path handling - all API requests are proxied to backend
  
  // For any other request, return 404
  res.writeHead(404);
  res.end('Not found');
});

// Start the server
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Frontend server running at http://0.0.0.0:${PORT}`);
});
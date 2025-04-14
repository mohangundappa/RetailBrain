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
  
  // Enhance logging for debugging
  console.log(`Request received: ${req.method} ${req.url}`);
  
  // Handle OPTIONS request
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  // Serve the dashboard
  if (req.url === '/' || req.url === '/index.html') {
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
  if (req.url === '/chat' || req.url === '/chat.html' || req.url === '/chat/') {
    console.log('Serving chat interface page from frontend server');
    fs.readFile(path.join(__dirname, 'chat-interface.html'), (err, data) => {
      if (err) {
        console.error('Error reading chat-interface.html:', err);
        res.writeHead(500);
        res.end('Error loading chat-interface.html');
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
    console.log(`API request received: ${req.method} ${req.url}`);
    
    // Get backend hostname and port from environment or use defaults
    // For Replit, we need to use 127.0.0.1 instead of localhost to avoid DNS resolution issues
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
      
      // Forward response data
      proxyRes.pipe(res);
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
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
  
  // Serve the agent routing architecture diagram
  if (req.url === '/routing-architecture') {
    fs.readFile(path.join(__dirname, 'public', 'agent_routing_architecture.html'), (err, data) => {
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
    // Proxy request to backend API server
    const options = {
      hostname: 'localhost',
      port: 5000,
      path: req.url,
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
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
      console.error('Error proxying request:', error.message);
      
      // Return a fallback response when backend is unavailable
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: false,
        error: 'Backend service unavailable',
        message: 'The API service is currently unavailable. Please try again later.'
      }));
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
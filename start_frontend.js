/**
 * Frontend Starter Script
 * This script configures and starts the React frontend application
 */
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

// Helper function to log with color
function log(message, color = colors.reset) {
  console.log(`${color}[Frontend Starter]${colors.reset} ${message}`);
}

// Check if frontend directory exists
const frontendDir = path.join(__dirname, 'frontend');
if (!fs.existsSync(frontendDir)) {
  log(`Frontend directory not found at ${frontendDir}`, colors.red);
  process.exit(1);
}

// Check for package.json
const packageJsonPath = path.join(frontendDir, 'package.json');
if (!fs.existsSync(packageJsonPath)) {
  log('package.json not found in frontend directory', colors.red);
  process.exit(1);
}

// Set up environment variables
process.env.PORT = process.env.FRONTEND_PORT || 3000;
process.env.BROWSER = 'none'; // Don't open browser automatically

log(`Starting frontend on port ${process.env.PORT}...`, colors.cyan);

// Start the React development server
const frontend = exec('npm start', { cwd: frontendDir });

frontend.stdout.on('data', (data) => {
  const lines = data.toString().trim().split('\n');
  lines.forEach(line => {
    if (line.includes('Compiled successfully') || line.includes('compiled successfully')) {
      log(`React application compiled successfully and is running on port ${process.env.PORT}`, colors.green);
      log(`Open http://localhost:${process.env.PORT} in your browser`, colors.blue);
    } else if (line.includes('error')) {
      log(line, colors.red);
    } else {
      log(line);
    }
  });
});

frontend.stderr.on('data', (data) => {
  log(data.toString().trim(), colors.red);
});

frontend.on('close', (code) => {
  if (code !== 0) {
    log(`Frontend process exited with code ${code}`, colors.red);
  } else {
    log('Frontend process closed', colors.yellow);
  }
});

// Handle termination
process.on('SIGINT', () => {
  log('Shutting down frontend...', colors.yellow);
  frontend.kill();
  process.exit(0);
});

process.on('SIGTERM', () => {
  log('Shutting down frontend...', colors.yellow);
  frontend.kill();
  process.exit(0);
});
# Staples Brain Frontend

React-based frontend for the Staples Brain multi-agent AI orchestration platform.

## Architecture

The frontend follows modern React best practices with a clean, maintainable architecture:

### Component Structure

- `layout/`: Layout components (AppLayout, Sidebar, TopNavbar, etc.)
- `common/`: Reusable UI components
- `dashboard/`: Dashboard and analytics components
- `chat/`: Chat interface components
- `settings/`: Application settings components

### State Management

Uses React Context API for global state management:
- `AppContext`: Global application state and actions
- Reducer pattern for predictable state updates
- Custom hooks for business logic encapsulation

### API Communication

Clean abstraction for API calls:
- `api/apiService.js`: Core API service with Axios
- `hooks/useApi.js`: Custom hook for API interaction
- `hooks/useChat.js`: Specialized hook for chat functionality
- Automatic error handling and notifications

### Styling

- Bootstrap 5 for responsive layouts
- Replit dark theme for consistent styling
- Feather icons for clean, modern UI

## Development

### Requirements

- Node.js 18+
- npm 9+

### Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm start
   ```

This will start the development server at http://localhost:3000.
API requests are automatically proxied to the backend at port 5000.

### Available Scripts

- `npm start`: Start development server
- `npm build`: Build production version
- `npm test`: Run tests
- `npm run eject`: Eject from Create React App
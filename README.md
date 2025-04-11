# Staples Brain

An advanced multi-agent AI orchestration platform for intelligent system management, featuring modular architecture and comprehensive developer tooling.

## Overview

Staples Brain is an AI super-brain agent system specifically for Staples Customer Engagement focusing on Sales and Services. It serves as an integration hub for specialized agents (Order Tracking, Reset Password, Store Locator, and others), supporting integrations with external platforms.

## Core Technologies

- Python-based agent framework
- FastAPI microservices architecture
- LangChain/LangGraph contextual intelligence
- OpenAI GPT-4o integration
- Comprehensive static documentation
- Modular backend design with clear architectural separation

## Project Structure

- `/backend` - Server-side code and components
- `/frontend` - React application code
- `/docs` - Documentation and guides

## Getting Started

See the [Installation Guide](docs/installation/README.md) for setup instructions.

## Development

The application is structured as follows:

1. Backend (FastAPI):
   - API Gateway for all interactions
   - Multi-agent brain system
   - Database integration

2. Frontend (React):
   - User interface for interacting with the system
   - Admin dashboard for monitoring agent performance
   - Agent Builder interface

## Running the Application

```bash
# Start the backend server
python run.py

# Start the frontend development server (in another terminal)
cd frontend
npm start
```

The application will be available at http://localhost:5000

## Testing

```bash
# Run all tests
python -m backend.scripts.run_tests
```
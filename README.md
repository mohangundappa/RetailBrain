# Staples Brain

An advanced multi-agent AI orchestration platform for intelligent system management, featuring a modular architecture and comprehensive developer tooling.

## Overview

Staples Brain is an AI super-brain agent system specifically designed for Staples Customer Engagement. It focuses on Sales and Services, serving as an integration hub for specialized agents (Order Tracking, Reset Password, Store Locator, and others). 

## Architecture

The system has a simplified architecture with two main components:

1. **Backend**: Pure FastAPI implementation with no Flask/WSGI compatibility layers
2. **Frontend**: React-based UI for user interactions

All services are consolidated within the backend component, maintaining a clear separation through a standardized API gateway serving as the primary entry point for all interactions.

## Key Technologies

- **Python 3.12+**: For backend and agent logic
- **FastAPI**: Main API framework (replacing older Flask implementation)
- **PostgreSQL with PgVec**: For database storage including vector embeddings
- **LangChain/LangGraph**: For contextual intelligence
- **OpenAI GPT-4o**: Core language model integration
- **LangSmith**: For telemetry and observability

## Project Structure

```
staples-brain/
├── backend/               # Backend services and components
│   ├── agents/            # Agent implementations
│   ├── api/               # API modules for specific services
│   ├── brain/             # Core brain logic
│   ├── config/            # Configuration files
│   ├── database/          # Database models and connections
│   ├── scripts/           # Utility scripts
│   ├── services/          # Service implementations
│   ├── static/            # Static resources
│   ├── tests/             # Backend tests
│   ├── utils/             # Utility functions
│   ├── api_gateway.py     # Main FastAPI entry point
│   └── main.py            # Backend application entry point
├── docs/                  # Documentation
│   ├── api/               # API documentation
│   ├── development/       # Development guidelines
│   ├── installation/      # Installation guides
│   └── user-guides/       # End-user documentation
├── frontend/              # React frontend (separate repo)
├── .env                   # Environment variables (local development)
├── .env.example           # Example environment variables
├── main.py                # Root application entry point
└── run.py                 # Application runner for Replit
```

## Running the Application

```bash
# Start the application
python run.py

# Run tests
python run_tests.py
```

## Environment Variables

The application requires several environment variables to be set. See `.env.example` for required variables.

## API Reference

API documentation is available at `/static/documentation` when the server is running.

## Contributing

See the development guidelines in the [docs/development](docs/development) directory for more information on contributing to the project.

## License

Proprietary - All rights reserved
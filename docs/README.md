# Staples Brain Documentation

This directory contains comprehensive documentation for the Staples Brain project.

## Directory Structure

- `assets/` - Visual assets for documentation
  - `architecture_diagrams/` - High-level architecture SVG diagrams
  - `diagrams/` - Detailed component and flow diagrams

- `html/` - HTML documentation pages

- `installation/` - Installation and setup guides
  - `INSTALLATION_GUIDE.md` - General installation instructions
  - `LOCAL_INSTALLATION.md` - Local development setup
  - `ENVIRONMENT_VARIABLES.md` - Environment variables documentation
  - `TROUBLESHOOTING.md` - Common installation issues and solutions

## Viewing Documentation

The documentation is also available through the running application:

- When the application is running, visit: http://localhost:5000/
- API documentation is available at: http://localhost:5000/docs

## Documentation Guidelines

- SVG format is preferred for all diagrams
- HTML documentation should use the Replit dark theme CSS
- Keep documentation updated with the latest architectural changes

## Core Architecture Components

The Staples Brain architecture consists of:

1. **FastAPI Backend**
   - Pure ASGI implementation (no Flask/WSGI)
   - Standardized API response format
   - LangChain/LangGraph integration
   - PostgreSQL with pgvector for vector storage

2. **Agent System**
   - Microservices architecture
   - Agent orchestration
   - Context management
   - Intent-based routing

3. **Telemetry and Monitoring**
   - Comprehensive telemetry collection
   - LangSmith integration
   - Performance metrics

## Backend Structure

The backend component follows a clear separation of concerns:

- `api/` - API routes and controllers
- `brain/` - Core brain implementation with agent orchestration
- `database/` - Database models and scripts
- `services/` - Service layer implementation
- `utils/` - Utility functions and helpers

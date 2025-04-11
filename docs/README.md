# Staples Brain Documentation

This directory contains documentation for the Staples Brain project, organized by component.

## Structure

- **Backend**: API reference, database schema, and backend architecture documentation
  - [API Reference](./backend/api_reference.md)
  - [Architecture](./backend/architecture.md)
  - [Database Schema](./backend/database_schema.md)
  - [Deployment](./backend/deployment.md)

- **Frontend**: UI components, state management, and design system documentation
  - [Components](./frontend/components.md)
  - [State Management](./frontend/state_management.md)
  - [Routing](./frontend/routing.md)
  - [Design System](./frontend/design_system.md)

- **Integration**: Documentation for integration between frontend and backend
  - [API Integration Guide](./integration/api_integration_guide.md)
  - [Data Flow](./integration/data_flow.md)

- **Cross-Component**: Documentation covering multiple components
  - [Circuit Breaker Overview](./backend/circuit_breaker.md)

## Getting Started

For new team members, we recommend starting with:

1. Review the [Installation Guide](../INSTALLATION_GUIDE.md)
2. Read the [Backend Architecture](./backend/architecture.md)
3. Explore the [API Integration Guide](./integration/api_integration_guide.md)

## FastAPI Documentation

The API is self-documented using FastAPI. When the server is running, you can access:

- Interactive API documentation: [/docs](http://localhost:5000/docs)
- Alternative API documentation: [/redoc](http://localhost:5000/redoc)
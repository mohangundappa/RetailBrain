# Deployment Guide

## Overview

This document provides instructions for deploying the Staples Brain application to various environments.

## Requirements

- Python 3.11 or higher
- PostgreSQL 15 or higher (with pgvector extension)
- Access to required environment variables

## Environment Variables

The following environment variables are required for deployment:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for language model access
- `LANGSMITH_API_KEY`: LangSmith API key for telemetry (optional)
- `DATABRICKS_HOST` and `DATABRICKS_TOKEN`: For Databricks integration (optional)

See [Environment Variables](../ENVIRONMENT_VARIABLES.md) for a complete list.

## Deployment Steps

### Local Deployment

1. Install dependencies:
   ```bash
   pip install -r requirements-standard.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run the application:
   ```bash
   python run.py
   ```

### Production Deployment

1. Set up a PostgreSQL database with pgvector extension
2. Configure environment variables in your production environment
3. Deploy using your preferred hosting method:
   - Docker container
   - Kubernetes cluster
   - Cloud platform (AWS, Azure, GCP)

## Health Checks

The application provides a health check endpoint at `/api/v1/health` that can be used to verify the deployment is functioning correctly.

## Monitoring

The application integrates with:

1. LangSmith for telemetry and tracing
2. Prometheus for metrics collection
3. Internal telemetry endpoints for custom monitoring

## Backup and Recovery

See the database backup and recovery procedures in [Database Maintenance](../db_scripts/maintenance.sql).

## Troubleshooting

See the [Troubleshooting Guide](../TROUBLESHOOTING.md) for common deployment issues and solutions.
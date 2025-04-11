# Environment Variables Configuration

Staples Brain uses environment variables for configuration across different environments. This guide explains how to set up environment variables for local development and production deployments.

## Setting Up Environment Variables

### Local Development

For local development, use a `.env` file in the project root:

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific configuration values:
   ```bash
   # Open with your editor
   vim .env  # or nano .env, or open in your IDE
   ```

### Production Deployment

For production environments, set environment variables according to your deployment platform:

- **Docker**: Use environment variables in your Docker Compose file or Dockerfile
- **Kubernetes**: Use ConfigMaps and Secrets
- **Cloud Platforms**: Use the platform's environment variable configuration system

## Required Environment Variables

These variables must be set for the application to function properly:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `DATABASE_URL` | Database connection string | `postgresql://user:password@host:port/dbname` |
| `SECRET_KEY` | Secret key for sessions and security | (random string, keep secure) |
| `OPENAI_API_KEY` | API key for OpenAI services | (your OpenAI API key) |

## Optional Environment Variables

These variables can be set to customize application behavior:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `APP_ENV` | Application environment | `development` |
| `DEBUG` | Enable debug mode | `False` in production, `True` in development |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |
| `DATABRICKS_HOST` | Databricks host for AI integration | None |
| `DATABRICKS_TOKEN` | Databricks API token | None |
| `LANGSMITH_API_KEY` | LangSmith API key for observability | None |

## Fallback Behavior

When certain environment variables are missing, the application provides fallbacks:

- **Missing DATABASE_URL**: A SQLite database is created at `staples_brain_dev.db` (development only)
- **Missing SECRET_KEY**: A random key is generated on startup (not suitable for production)
- **Missing OPENAI_API_KEY**: The application runs in demo mode with mock responses

## Security Considerations

- **Never commit** your `.env` file to source control
- Use different values for `SECRET_KEY` in each environment
- In production, use a secret management system when possible
- Rotate API keys periodically according to your security policy

## Troubleshooting

If your environment variables don't seem to be loading:

1. Verify the `.env` file exists in the project root
2. Check for syntax errors in your `.env` file
3. Make sure you don't have conflicting environment variables set in your shell
4. Try running the application with explicit variables:
   ```bash
   DATABASE_URL=postgresql://user:pass@localhost/testdb python main.py
   ```

For more information on configuration, see the application documentation.
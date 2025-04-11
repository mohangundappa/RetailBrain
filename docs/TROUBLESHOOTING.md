# Troubleshooting Guide

This document contains solutions for common issues you might encounter when running the Staples Brain application.

## OpenAI Client Initialization Errors

### Issue: "Client.__init__() got an unexpected keyword argument 'proxies'"

**Error Message:**
```
ValidationError: 1 validation error for ChatOpenAI
__root__
  Client.__init__() got an unexpected keyword argument 'proxies' (type=type_error)
```

**Cause:**
This error occurs due to a compatibility issue between different versions of the OpenAI library and LangChain. The newer version of the OpenAI client (v1.x+) doesn't accept a `proxies` parameter, but some older versions of LangChain still try to pass it.

**Solution:**
The application has been updated to handle this compatibility issue automatically by:

1. Creating a dedicated OpenAI client without proxy settings
2. Using multiple initialization approaches with proper fallbacks
3. Providing detailed error logging for troubleshooting

If you still encounter this issue in your local environment, try one of these solutions:

**Option 1: Upgrade your dependencies**
```bash
pip install --upgrade langchain-openai openai
```

**Option 2: Apply the patch manually**
Find where `ChatOpenAI` is initialized in your code and update it to use a custom client:

```python
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Then use the client
llm = ChatOpenAI(
    model_name="gpt-4o",
    client=openai_client,
    temperature=0.3
)
```

## Database Connection Issues

### Issue: "Could not parse SQLAlchemy URL from string ''"

**Error Message:**
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string ''
```

**Cause:**
This error occurs when the `DATABASE_URL` environment variable is not properly set or not being loaded from your `.env` file.

**Solution:**

1. Make sure you have a `.env` file in the project root directory
2. Verify that your `.env` file contains a valid `DATABASE_URL` setting
3. For local development, you can use SQLite: `DATABASE_URL=sqlite:///staples_brain_dev.db`
4. Ensure that python-dotenv is installed: `pip install python-dotenv`

The application now includes a fallback to SQLite when no database URL is provided, but it's still recommended to set this variable explicitly.

## LangSmith Connectivity Issues

### Issue: "Cannot connect to LangSmith API"

**Cause:**
This error occurs when the application can't connect to LangSmith for telemetry and observability.

**Solution:**

1. Check if your `LANGSMITH_API_KEY` is set correctly
2. If you don't want to use LangSmith, you can safely ignore this warning
3. For local development, you can disable LangSmith by setting `LANGSMITH_API_KEY=` (empty string)

## Databricks Integration Issues

### Issue: "Databricks integration disabled"

**Cause:**
This warning appears when the Databricks host or token is not configured.

**Solution:**

1. If you're using Databricks, set both `DATABRICKS_HOST` and `DATABRICKS_TOKEN` in your environment
2. If you're not using Databricks, you can safely ignore this warning

## General Troubleshooting Steps

If you encounter any other issues:

1. Check the logs for detailed error messages
2. Verify that all required environment variables are set correctly
3. Ensure all dependencies are installed and up to date
4. Try restarting the application with a clean environment
5. For persistent issues, check the GitHub issues page or contact support

## Getting Additional Help

If you're still experiencing issues:

1. Capture the full error message and stack trace
2. Note which versions of Python and key libraries you're using
3. Describe the steps to reproduce the issue
4. Open an issue in the GitHub repository with this information
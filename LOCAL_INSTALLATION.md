# Local Installation Guide for Staples Brain

This guide will help you set up the Staples Brain project locally on your system, specifically addressing compatibility with Python 3.12.

## Prerequisites

- Python 3.12 installed
- Virtual environment tool (venv, conda, etc.)
- PostgreSQL database (optional, for full functionality)
- OpenAI API key

## Step 1: Create and activate a virtual environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate it (macOS/Linux)
source .venv/bin/activate

# Activate it (Windows)
.venv\Scripts\activate
```

## Step 2: Install dependencies (Option 1 - Basic)

Try this approach first:

```bash
# Install using the standardized requirements file
pip install -r requirements-standard.txt
```

## Step 3: Install dependencies (Option 2 - If Option 1 fails)

If you encounter dependency resolution errors, try this alternative method:

```bash
# First, upgrade pip
pip install --upgrade pip

# Install with more forgiving options
pip install -r requirements-standard.txt --use-pep517

# If that also fails, try installing without dependency resolution
pip install --no-deps -r requirements-standard.txt

# Then manually install core packages in the correct order
pip install flask==2.3.3 werkzeug==2.3.7 sqlalchemy==2.0.27
pip install langchain-core==0.1.18 langchain-community==0.0.18 langchain-openai==0.0.5 langchain==0.0.335
pip install openai==1.6.1
```

## Step 4: Set up environment variables

Create a `.env` file in the project root with the following variables:

```
# Required environment variables
DATABASE_URL=postgresql://username:password@localhost:5432/staples_brain
OPENAI_API_KEY=your_openai_api_key

# Optional environment variables
LANGSMITH_API_KEY=your_langsmith_api_key
DATABRICKS_HOST=your_databricks_host
DATABRICKS_TOKEN=your_databricks_token
```

## Step 5: Initialize the database (if using PostgreSQL)

```bash
# Log into PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE staples_brain;

# Create a user (optional)
CREATE USER staples WITH PASSWORD 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE staples_brain TO staples;
```

## Step 6: Run database setup scripts

```bash
# Navigate to the db_scripts directory
cd db_scripts

# Run the setup script
python setup_database.py
```

## Step 7: Start the application

```bash
# Run with Python directly (development mode)
python main.py

# Or use Gunicorn (production-like environment)
gunicorn --bind 0.0.0.0:5000 main:app
```

The application should now be accessible at http://localhost:5000.

## Troubleshooting

### Dependency Conflicts

If you still encounter dependency conflicts, try installing the packages one by one in order of their dependencies.

```bash
# Core packages first
pip install flask flask-sqlalchemy flask-login psycopg2-binary

# Then langchain - note the order is important to resolve dependencies correctly
pip install langchain-core langchain-community langchain-openai langchain

# Then other packages
pip install openai flask-cors gunicorn prometheus-client
```

### Import Errors

If you encounter import errors, check that the correct package versions are installed:

```bash
pip list | grep langchain
pip list | grep flask
```

### Database Connection Issues

If you can't connect to the database, make sure:
1. PostgreSQL is running
2. The DATABASE_URL is correctly formatted 
3. The user has proper permissions

### LangChain Warnings

You may see warnings about deprecated LangChain methods, like warning about ChatOpenAI being imported from langchain_community rather than langchain_openai. This is due to LangChain's modular restructuring. Make sure to use the correct imports as follows:

```python
# Old/deprecated imports
from langchain_community.chat_models import ChatOpenAI  # Will show deprecation warning

# New/recommended imports
from langchain_openai import ChatOpenAI  # Correct import
```

These warnings are informational and don't affect functionality, but it's best to use the latest import patterns to future-proof your code.
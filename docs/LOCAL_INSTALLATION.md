# Staples Brain - Local Installation Guide

This guide provides step-by-step instructions for setting up the Staples Brain project in your local development environment.

## Prerequisites

- Python 3.9+ installed
- PostgreSQL (optional, SQLite will be used as fallback)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-organization/staples-brain.git
cd staples-brain
```

### 2. Create and Activate a Virtual Environment

#### For macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

#### For Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

Use our setup script which handles dependency conflicts properly:

```bash
python setup_local_env.py
```

Alternatively, you can install dependencies manually:

```bash
pip install --upgrade pip
pip install -r requirements-standard.txt
```

### 4. Configure Environment Variables

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
```

Then edit the `.env` file with your preferred text editor:

```bash
# Open with your editor
vim .env  # or use any editor you prefer
```

At minimum, you'll need to set:
- `DATABASE_URL` - Your database connection string (or leave empty for SQLite)
- `SECRET_KEY` - Set a secure random string
- `OPENAI_API_KEY` - Your OpenAI API key for LLM functionality

For details on all available environment variables, see [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

### 5. Set Up the Database

#### Option A: Using PostgreSQL (Recommended for Production)

If you're using PostgreSQL:

1. Create a database:
```bash
createdb staples_brain_dev
```

2. Update your `.env` file with the connection string:
```
DATABASE_URL=postgresql://username:password@localhost:5432/staples_brain_dev
```

#### Option B: Using SQLite (Simplest for Development)

If you prefer SQLite (or don't have PostgreSQL):

1. Set an empty or SQLite connection string in your `.env` file:
```
DATABASE_URL=sqlite:///staples_brain_dev.db
```

2. The application will automatically create and set up the SQLite database file.

### 6. Run the Application

Start the application with:

```bash
python main.py
```

The server will start at http://localhost:5000

## Troubleshooting

### Environment Variables Not Loading

If your environment variables aren't loading properly:

1. Make sure your `.env` file exists in the project root
2. Check the syntax of your `.env` file for any errors
3. Try running with explicit environment variables:
   ```bash
   DATABASE_URL=sqlite:///staples_brain_dev.db python main.py
   ```

### Database Connection Issues

If you encounter database connection problems:

1. Make sure your database server is running
2. Verify the connection string in your `.env` file
3. Check that the database exists and your user has access to it
4. For SQLite, ensure your application has write permission to the directory

### OpenAI API Connection

If the LLM features aren't working:

1. Check that your `OPENAI_API_KEY` is set correctly in your `.env` file
2. Verify your API key is valid and has not expired
3. Check your internet connection

### Package Conflicts

If you encounter package conflicts or import errors:

1. Make sure you're using a clean virtual environment
2. Use the `setup_local_env.py` script which handles dependencies properly
3. Check if your Python version is compatible (Python 3.9+ recommended)

## Next Steps

Once your installation is complete:

1. See the API documentation at http://localhost:5000/documentation
2. Try the agent builder interface at http://localhost:5000/agent-builder
3. Check out the dashboard at http://localhost:5000/dashboard

For more details on using and extending the Staples Brain, refer to the other documentation files in this repository.
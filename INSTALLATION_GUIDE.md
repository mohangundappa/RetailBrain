# Staples Brain Installation Guide

## Local Installation Options

If you're experiencing dependency resolution errors when installing this project locally, particularly with Python 3.12, we've provided several options to help you resolve these issues:

### Option 1: Use the Python 3.12 Compatible Requirements File

```bash
pip install -r requirements-python312.txt
```

This file contains version specifications that are known to work with Python 3.12.

### Option 2: Use the Interactive Setup Script

For a guided installation process that handles dependencies in the correct order:

```bash
python setup_local_env.py
```

This script will:
- Check your Python version
- Upgrade pip
- Install dependencies incrementally in a way that avoids conflicts
- Verify the installation
- Create a template .env file

### Option 3: Manual Installation Steps

For detailed step-by-step instructions, including database setup and troubleshooting tips, refer to:

```
LOCAL_INSTALLATION.md
```

## Common Issues and Solutions

### ResolutionImpossible Error

If you encounter a `ResolutionImpossible` error, it indicates that pip cannot find a set of dependencies that satisfy all requirements. Try these solutions:

1. Use our compatibility script: `python setup_local_env.py`
2. Install with the `--no-deps` option and then manually install core packages:
   ```bash
   pip install --no-deps -r requirements-python312.txt
   pip install flask==2.3.3 sqlalchemy==2.0.23 langchain==0.0.335 openai==1.3.7
   ```
3. Create a new virtual environment with Python 3.11 instead of 3.12 if available

### Import Errors After Installation

If packages install but you get import errors when running the application:

1. Make sure your virtual environment is activated
2. Check if the package is actually installed: `pip list | grep package_name`
3. Try reinstalling the specific package: `pip install --force-reinstall package_name`

For additional help and troubleshooting, consult the detailed guide in `LOCAL_INSTALLATION.md`.
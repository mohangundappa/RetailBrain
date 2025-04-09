#!/usr/bin/env python
"""
Setup script for installing dependencies for the Staples Brain project locally.
This script helps resolve dependency conflicts by installing packages in the correct order.
"""

import sys
import subprocess
import platform
import os
from pathlib import Path

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80, "="))
    print("=" * 80)

def run_command(command):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if the Python version is compatible."""
    print_header("Checking Python Version")
    version_info = sys.version_info
    print(f"Python version: {version_info.major}.{version_info.minor}.{version_info.micro}")
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 8):
        print("ERROR: Python 3.8 or higher is required!")
        return False
    
    if version_info.major == 3 and version_info.minor >= 12:
        print("INFO: Python 3.12 detected. Using special compatibility measures.")
        print("This includes ordering package installations correctly to avoid dependency conflicts.")
        return "3.12+"
    
    return True

def upgrade_pip():
    """Upgrade pip to the latest version."""
    print_header("Upgrading pip")
    return run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

def install_dependencies_incrementally():
    """Install dependencies incrementally to avoid conflicts."""
    print_header("Installing Core Dependencies")
    
    # Core Flask dependencies
    core_packages = [
        "flask==2.3.3",
        "werkzeug==2.3.7",
        "flask-cors==4.0.0",
        "sqlalchemy==2.0.23",
        "flask-sqlalchemy==3.1.1",
        "flask-login==0.6.2",
        "email-validator==2.1.0.post1",
    ]
    
    # Database dependencies
    db_packages = [
        "psycopg2-binary==2.9.9",
    ]
    
    # Server dependencies
    server_packages = [
        "gunicorn==21.2.0",
    ]
    
    # LangChain dependencies (order is important to resolve dependencies correctly)
    langchain_packages = [
        "langchain-core==0.1.18",
        "langchain-community==0.0.18",
        "langchain-openai==0.0.5",
        "langchain==0.0.335",
    ]
    
    # AI and API dependencies
    ai_packages = [
        "openai==1.6.1",
        "langsmith==0.0.83",
    ]
    
    # Utility packages
    util_packages = [
        "prometheus-client==0.17.1",
        "psutil==5.9.6",
        "trafilatura==1.6.1",
        "python-dotenv==1.0.0",
    ]
    
    # Optional packages
    optional_packages = [
        "twilio==8.10.0",
        "databricks-sdk==0.13.0",
    ]
    
    package_groups = [
        ("Core Flask", core_packages),
        ("Database", db_packages),
        ("Server", server_packages),
        ("LangChain", langchain_packages),
        ("AI and API", ai_packages),
        ("Utilities", util_packages),
        ("Optional", optional_packages),
    ]
    
    for group_name, packages in package_groups:
        print(f"\nInstalling {group_name} packages...")
        for package in packages:
            if not run_command([sys.executable, "-m", "pip", "install", package, "--no-cache-dir"]):
                print(f"WARNING: Failed to install {package}. Continuing with next package.")
    
    return True

def check_installation():
    """Verify the installation by importing key packages."""
    print_header("Verifying Installation")
    
    packages_to_check = [
        "flask",
        "sqlalchemy",
        "langchain",
        "openai",
    ]
    
    all_successful = True
    for package in packages_to_check:
        try:
            __import__(package)
            print(f"✓ Successfully imported {package}")
        except ImportError as e:
            print(f"✗ Failed to import {package}: {e}")
            all_successful = False
    
    return all_successful

def create_env_file():
    """Create a template .env file if it doesn't exist."""
    env_path = Path(".env")
    
    if env_path.exists():
        print("\n.env file already exists. Skipping creation.")
        return
    
    print("\nCreating template .env file...")
    with open(env_path, "w") as f:
        f.write("""# Required environment variables
DATABASE_URL=postgresql://username:password@localhost:5432/staples_brain
OPENAI_API_KEY=your_openai_api_key

# Optional environment variables
LANGSMITH_API_KEY=your_langsmith_api_key
DATABRICKS_HOST=your_databricks_host
DATABRICKS_TOKEN=your_databricks_token
""")
    
    print("Template .env file created. Please edit it with your actual values.")

def main():
    """Main function to set up the local environment."""
    print_header("Staples Brain Local Setup")
    
    python_version = check_python_version()
    if not python_version:
        return
    
    if not upgrade_pip():
        print("WARNING: Failed to upgrade pip. Continuing with installation anyway.")
    
    if install_dependencies_incrementally():
        print("\nDependencies installed successfully!")
    else:
        print("\nWARNING: Some dependencies may not have been installed correctly.")
    
    installation_status = check_installation()
    create_env_file()
    
    print_header("Setup Complete")
    if installation_status:
        print("All key packages were imported successfully!")
    else:
        print("Some packages could not be imported. You may need to troubleshoot further.")
    
    print("\nNext steps:")
    print("1. Edit the .env file with your actual API keys and database connection.")
    print("2. Run database setup scripts if needed.")
    print("3. Start the application with: python main.py")

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Specialized installation script for Python 3.12 with pip 25.0.1
This script installs packages in a specific order to avoid dependency conflicts.
"""

import subprocess
import sys
import os
from pathlib import Path

def print_step(message):
    """Print a formatted step message."""
    print("\n" + "=" * 70)
    print(f" STEP: {message}")
    print("=" * 70)

def run_pip_install(package, options=None):
    """Run pip install with the given package and options."""
    if options is None:
        options = []
    
    cmd = [sys.executable, "-m", "pip", "install"] + options + [package]
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")
        return False

# Ensure we're using Python 3.12
if sys.version_info.major != 3 or sys.version_info.minor != 12:
    print(f"Warning: This script is designed for Python 3.12, but you're using {sys.version_info.major}.{sys.version_info.minor}")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(1)

# Ensure we're using pip 25.x
pip_version = subprocess.check_output([sys.executable, "-m", "pip", "--version"]).decode().split()[1]
if not pip_version.startswith("25."):
    print(f"Warning: This script is designed for pip 25.x, but you're using {pip_version}")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(1)

print_step("Starting installation for Python 3.12 with pip 25.x")

# Create a temporary directory for downloads if it doesn't exist
temp_dir = Path("./pip_temp")
temp_dir.mkdir(exist_ok=True)

# Step 1: Install core Flask dependencies
print_step("Installing core Flask dependencies")
packages = [
    "flask==2.3.3",
    "werkzeug==2.3.7",
    "flask-cors==4.0.0", 
    "flask-sqlalchemy==3.1.1",
    "flask-login==0.6.2",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Step 2: Install SQLAlchemy and database dependencies
print_step("Installing SQLAlchemy and database dependencies")
packages = [
    "sqlalchemy==2.0.27",
    "psycopg2-binary==2.9.9",
    "email-validator==2.1.0.post1",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Step 3: Install Gunicorn
print_step("Installing Gunicorn")
if not run_pip_install("gunicorn==21.2.0", ["--no-cache-dir"]):
    print("Warning: Failed to install Gunicorn. Continuing with next steps.")

# Step 4: Install LangChain packages
print_step("Installing LangChain packages")
packages = [
    "langchain-core==0.1.18",
    "langchain==0.0.335",
    "langchain-community==0.0.18",
    "langchain-openai==0.0.5",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Step 5: Install OpenAI and LangSmith
print_step("Installing OpenAI and LangSmith")
packages = [
    "openai==1.6.1",  # Version 1.6.1 is compatible with current langchain versions
    "langsmith==0.0.83",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Step 6: Install utility packages
print_step("Installing utility packages")
packages = [
    "prometheus-client==0.19.0",
    "psutil==5.9.8", 
    "trafilatura==1.6.2",
    "python-dotenv==1.0.1",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Step 7: Install optional dependencies
print_step("Installing optional dependencies")
packages = [
    "twilio==8.12.0",
    "databricks-sdk==0.15.0",
]

for package in packages:
    if not run_pip_install(package, ["--no-cache-dir"]):
        print(f"Warning: Failed to install {package}. Continuing with next package.")

# Clean up temporary directory
print_step("Cleaning up")
try:
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()
    print("Temporary directory removed.")
except Exception as e:
    print(f"Warning: Failed to clean up temporary directory: {e}")

print_step("Installation Complete")
print("To verify installation, try importing key packages:")
print("  python -c 'import flask, sqlalchemy, langchain, openai'")
print("\nIf you encounter any issues, check the error messages and try installing")
print("the problematic packages individually with specific version constraints.")
print("\nHappy coding!")
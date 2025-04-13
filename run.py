#!/usr/bin/env python
"""
Staples Brain Application Runner.

This script is the primary entry point for starting the Staples Brain API in development or
production environments. It handles database initialization and API server startup, with
robust error handling and fallback mechanisms.

This script is designed for use in:
- Replit workflows
- Development environments
- CI/CD pipelines
- Production deployment scripts
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Ensure proper path setup
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT_DIR / "staples_brain.log")
    ]
)

logger = logging.getLogger("staples_brain_runner")
logger.info("Starting Staples Brain application")

# Server configuration
HOST = os.environ.get("API_HOST", "0.0.0.0")
PORT = int(os.environ.get("API_PORT", 5000))
APP_MODULE = "main:app"
RELOAD = os.environ.get("ENVIRONMENT", "development") != "production"

logger.info(f"Configuration: host={HOST}, port={PORT}, reload={RELOAD}")

# Primary entry point - uses the centralized backend.main functions
async def start_app():
    """Initialize database and start the API server."""
    try:
        # Import the core initialization and runner functions
        from backend.main import init_db, run_api

        # Initialize the database first
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization complete")
        
        # Initialize core agents (General Conversation and Guardrails)
        try:
            from backend.scripts.initialize_agents import initialize_core_agents
            logger.info("Initializing core agents...")
            await initialize_core_agents()
            logger.info("Core agents initialization complete")
        except Exception as agent_error:
            logger.error(f"Error initializing core agents: {str(agent_error)}", exc_info=True)
            logger.warning("Continuing despite core agent initialization error")
        
        # Start the API server with explicit reload flag
        logger.info("Starting API server...")
        run_api(reload=RELOAD)
        
    except ImportError as e:
        logger.error(f"Could not import core modules: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

# Fallback method if the primary method fails
def start_with_uvicorn_module():
    """Start the application using the uvicorn module directly."""
    logger.info("Using uvicorn module as fallback")
    import uvicorn
    uvicorn.run(
        APP_MODULE,
        host=HOST,
        port=PORT,
        reload=RELOAD
    )

# Main execution
def main():
    """Main application entry point with error handling."""
    try:
        # First attempt: Use our managed async startup
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        return 0
    except Exception as e:
        logger.error(f"Primary startup method failed: {e}", exc_info=True)
        
        # Second attempt: Try direct uvicorn module
        try:
            logger.info("Falling back to direct uvicorn execution")
            start_with_uvicorn_module()
            return 0
        except KeyboardInterrupt:
            logger.info("Server shutdown requested by user")
            return 0
        except Exception as e2:
            logger.error(f"Fallback startup method failed: {e2}", exc_info=True)
            
            # Last resort: Use subprocess
            try:
                logger.info("Attempting subprocess execution as last resort")
                import subprocess
                cmd = [
                    sys.executable, "-m", "uvicorn", 
                    APP_MODULE, 
                    "--host", HOST, 
                    "--port", str(PORT),
                    "--reload" if RELOAD else ""
                ]
                cmd = [c for c in cmd if c]  # Remove empty strings
                
                logger.info(f"Executing: {' '.join(cmd)}")
                process = subprocess.run(cmd, check=True)
                logger.info(f"Process exited with code {process.returncode}")
                return process.returncode
            except Exception as e3:
                logger.critical(f"All startup methods failed. Last error: {e3}", exc_info=True)
                return 1

if __name__ == "__main__":
    sys.exit(main())
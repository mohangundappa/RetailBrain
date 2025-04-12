#!/usr/bin/env python
"""
Test runner for Staples Brain application
"""
import os
import sys
import argparse
import unittest
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_runner")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run tests for Staples Brain")
    
    parser.add_argument(
        "-a", "--api",
        action="store_true",
        help="Run API tests"
    )
    
    parser.add_argument(
        "-f", "--frontend",
        action="store_true",
        help="Run frontend tests (requires Chrome/Chromium)"
    )
    
    parser.add_argument(
        "-g", "--agent",
        action="store_true",
        help="Run agent tests"
    )
    
    parser.add_argument(
        "--agent-type",
        choices=["selection", "context", "flow", "routing", "all"],
        default="all",
        help="Specific agent test type to run"
    )
    
    parser.add_argument(
        "-e", "--error-handling",
        action="store_true",
        help="Run error handling and state persistence tests"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    return parser.parse_args()

def run_api_tests(verbose=False):
    """Run API tests"""
    logger.info("Running API tests...")
    
    # Load API tests
    from backend.tests.test_api_routes import TestApiRoutes
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestApiRoutes)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_frontend_tests(verbose=False):
    """Run frontend tests"""
    logger.info("Running frontend tests...")
    
    try:
        # Attempt to import Selenium
        from selenium import webdriver
    except ImportError:
        logger.error("Selenium is not installed. Run: pip install selenium")
        return False
    
    # Try to import frontend tests
    try:
        from backend.tests.test_frontend import TestFrontend
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestFrontend)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except Exception as e:
        logger.error(f"Error running frontend tests: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

def run_agent_tests(agent_type="all", verbose=False):
    """Run agent tests"""
    logger.info(f"Running agent tests (type: {agent_type})...")
    
    try:
        # Import our agent testing module
        from backend.tests.test_agent_interactions import TestAgentSelection, TestAgentContextSwitching
        from backend.tests.test_conversation_flow import TestComplexConversationFlow
        from backend.tests.test_agent_routing import TestAgentRouting
        
        # Create test suite
        suite = unittest.TestSuite()
        
        # Add tests based on agent_type
        if agent_type == "selection" or agent_type == "all":
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestAgentSelection))
        
        if agent_type == "context" or agent_type == "all":
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestAgentContextSwitching))
        
        if agent_type == "flow" or agent_type == "all":
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestComplexConversationFlow))
        
        if agent_type == "routing" or agent_type == "all":
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestAgentRouting))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except Exception as e:
        logger.error(f"Error running agent tests: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def run_all_tests(verbose=False):
    """Run all available tests"""
    logger.info("Running all tests...")
    
    api_success = run_api_tests(verbose)
    frontend_success = run_frontend_tests(verbose)
    agent_success = run_agent_tests("all", verbose)
    
    return api_success and frontend_success and agent_success

def main():
    """Main entry point"""
    args = parse_args()
    
    logger.info("Starting test run")
    
    if args.api:
        success = run_api_tests(args.verbose)
    elif args.frontend:
        success = run_frontend_tests(args.verbose)
    elif args.agent:
        success = run_agent_tests(args.agent_type, args.verbose)
    else:
        # Run all tests if no specific test is requested
        success = run_all_tests(args.verbose)
    
    logger.info("Test run completed")
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
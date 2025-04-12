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


def run_error_handling_tests(verbose=False):
    """Run error handling and state persistence tests"""
    logger.info("Running error handling and state persistence tests...")
    
    try:
        # Import our error handling and state persistence test modules
        from backend.tests.test_error_handling import TestErrorClassification, TestErrorRecording
        from backend.tests.test_error_handling import TestErrorRecoveryResponses, TestErrorHandlingDecorator
        from backend.tests.test_error_handling import TestJsonParsing, TestRetryDecorator, TestUtilsRetryAsync
        from backend.tests.test_state_persistence import TestStatePersistenceManager
        from backend.tests.test_state_recovery import TestWithRetry, TestResilientStatePersistence
        from backend.tests.test_state_recovery import TestResilientStateRecovery, TestResilientCheckpoint
        from backend.tests.test_state_recovery import TestResilientRollback, TestRecoveryOperations
        
        # Create test suite
        suite = unittest.TestSuite()
        
        # Add error handling tests
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestErrorClassification))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestErrorRecording))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestErrorRecoveryResponses))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestErrorHandlingDecorator))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestJsonParsing))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRetryDecorator))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUtilsRetryAsync))
        
        # Add state persistence tests
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestStatePersistenceManager))
        
        # Add state recovery tests
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestWithRetry))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestResilientStatePersistence))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestResilientStateRecovery))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestResilientCheckpoint))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestResilientRollback))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRecoveryOperations))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except Exception as e:
        logger.error(f"Error running error handling tests: {e}")
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
    error_handling_success = run_error_handling_tests(verbose)
    
    return api_success and frontend_success and agent_success and error_handling_success

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
    elif args.error_handling:
        success = run_error_handling_tests(args.verbose)
    else:
        # Run all tests if no specific test is requested
        success = run_all_tests(args.verbose)
    
    logger.info("Test run completed")
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
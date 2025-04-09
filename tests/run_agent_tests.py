#!/usr/bin/env python3
"""
Script to run agent interaction tests.
This script allows selective running of agent interaction test cases.
"""

import unittest
import argparse
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_imports import TestImports
from tests.test_agent_interactions import TestAgentSelection, TestAgentContextSwitching
from tests.test_conversation_flow import TestComplexConversationFlow
from tests.test_agent_routing import TestAgentRouting


def run_tests(test_class=None, verbose=False):
    """
    Run the specified tests.
    
    Args:
        test_class: The test class to run, or None to run all tests
        verbose: Whether to run tests in verbose mode
    """
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add tests to the suite based on the selected test class
    if test_class == 'imports':
        suite.addTest(loader.loadTestsFromTestCase(TestImports))
    elif test_class == 'selection':
        suite.addTest(loader.loadTestsFromTestCase(TestAgentSelection))
    elif test_class == 'context':
        suite.addTest(loader.loadTestsFromTestCase(TestAgentContextSwitching))
    elif test_class == 'flow':
        suite.addTest(loader.loadTestsFromTestCase(TestComplexConversationFlow))
    elif test_class == 'routing':
        suite.addTest(loader.loadTestsFromTestCase(TestAgentRouting))
    else:
        # Add all test cases
        suite.addTest(loader.loadTestsFromTestCase(TestImports))
        suite.addTest(loader.loadTestsFromTestCase(TestAgentSelection))
        suite.addTest(loader.loadTestsFromTestCase(TestAgentContextSwitching))
        suite.addTest(loader.loadTestsFromTestCase(TestComplexConversationFlow))
        suite.addTest(loader.loadTestsFromTestCase(TestAgentRouting))
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    
    # Run the tests
    return runner.run(suite)


if __name__ == '__main__':
    # Create an argument parser
    parser = argparse.ArgumentParser(description='Run agent interaction tests')
    
    # Add arguments
    parser.add_argument('--test-class', '-t', 
                        choices=['imports', 'selection', 'context', 'flow', 'routing', 'all'], 
                        default='all', help='Which test class to run')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Run tests in verbose mode')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run tests
    test_class = None if args.test_class == 'all' else args.test_class
    run_tests(test_class, args.verbose)
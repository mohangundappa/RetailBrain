# Staples Brain Tests

This directory contains tests for the Staples Brain backend.

## Test Organization

- **Unit Tests**: Tests for individual components
- **Integration Tests**: Tests for component interactions
- **API Tests**: Tests for API endpoints
- **Agent Tests**: Tests for agent behavior and interactions

## Running Tests

Tests can be run using pytest:

```bash
cd /path/to/staples_brain
python -m pytest backend/tests
```

Or using the test runner script:

```bash
python -m backend.scripts.run_tests
```

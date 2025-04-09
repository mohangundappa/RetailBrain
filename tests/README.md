# Testing Framework for Staples Brain

This directory contains tests for the Staples Brain application. The tests are designed to ensure that the application functions correctly and that new changes don't break existing functionality.

## Test Types

1. **API Tests** - Tests the backend API endpoints
2. **Frontend Tests** - Tests the frontend UI functionality using Selenium

## Running Tests

You can run tests using the `run_tests.py` script in the root directory:

```bash
# Run all tests
python run_tests.py

# Run only API tests
python run_tests.py --api

# Run only frontend tests
python run_tests.py --frontend

# Run tests with verbose output
python run_tests.py --verbose
```

## Setup for Testing

### Prerequisites

1. Install test dependencies:
   ```bash
   pip install -r tests/requirements.txt
   ```

2. For frontend tests, you need Chrome/Chromium and ChromeDriver installed:
   - ChromeDriver should be available in your PATH

### Test Database

The tests use the same database as configured in your environment variables (DATABASE_URL).
Tests are designed to clean up after themselves, but be cautious when running tests in a production environment.

## Adding New Tests

### API Tests

Add new test methods to `tests/test_api_routes.py` or create new test files as needed.

Example:

```python
def test_new_feature(self):
    """Test a new feature"""
    # Setup test data
    # ...
    
    # Call API
    response = self.client.get('/api/new-feature')
    
    # Assertions
    self.assertEqual(response.status_code, 200)
    # More assertions...
```

### Frontend Tests

Add new test methods to `tests/test_frontend.py` or create new test files as needed.

Example:

```python
def test_new_ui_feature(self):
    """Test a new UI feature"""
    self.driver.get(f"{self.base_url}/feature-page")
    
    # Interact with UI
    button = self.driver.find_element(By.ID, 'feature-button')
    button.click()
    
    # Wait for result
    self.wait.until(EC.presence_of_element_located((By.ID, 'result-element')))
    
    # Assertions
    result = self.driver.find_element(By.ID, 'result-element')
    self.assertEqual(result.text, 'Expected Value')
```

## Continuous Integration

These tests can be integrated into a CI/CD pipeline to automatically test changes before deployment.

## Troubleshooting

If frontend tests fail:
1. Check that ChromeDriver is installed and accessible
2. Ensure the application is running at the expected URL
3. Look for timing issues - you may need to adjust wait times

If API tests fail:
1. Ensure the application server is running
2. Check database connectivity
3. Look for schema changes that might require test updates
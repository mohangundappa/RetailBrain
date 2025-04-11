"""
Test suite for frontend functionality using Python and Selenium
"""
import unittest
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestFrontend(unittest.TestCase):
    """Test case for frontend functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up browser for tests"""
        # Configure headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Create browser instance
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.wait = WebDriverWait(cls.driver, 10)
        
        # Base URL for tests
        cls.base_url = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.driver.quit()
    
    def test_homepage_loads(self):
        """Test that the homepage loads correctly"""
        self.driver.get(self.base_url)
        
        # Check title
        self.assertIn('Staples Brain', self.driver.title)
        
        # Check for key elements
        self.assertIsNotNone(self.driver.find_element(By.ID, 'user-input'))
        self.assertIsNotNone(self.driver.find_element(By.ID, 'send-button'))
    
    def test_agent_builder_page(self):
        """Test that the agent builder page loads correctly"""
        self.driver.get(f"{self.base_url}/agent-builder")
        
        # Check for key elements
        self.assertIsNotNone(self.driver.find_element(By.ID, 'agent-canvas'))
        self.assertIsNotNone(self.driver.find_element(By.ID, 'component-palette'))
        self.assertIsNotNone(self.driver.find_element(By.ID, 'existing-agents-list'))
    
    def test_agent_creation_workflow(self):
        """Test the full workflow of creating an agent"""
        self.driver.get(f"{self.base_url}/agent-builder")
        
        # Generate a unique name to avoid conflicts
        agent_name = f"Test Agent {int(time.time())}"
        
        # Fill in agent details
        name_field = self.driver.find_element(By.ID, 'agent-name')
        name_field.clear()
        name_field.send_keys(agent_name)
        
        description_field = self.driver.find_element(By.ID, 'agent-description')
        description_field.clear()
        description_field.send_keys('Test agent created by automated tests')
        
        # Add an intent classifier component by simulating drag and drop
        intent_comp = self.driver.find_element(
            By.XPATH, 
            "//div[@data-component-type='prompt' and @data-component-template='intent_classifier']"
        )
        canvas = self.driver.find_element(By.ID, 'agent-canvas')
        
        # Use JavaScript to simulate drop since selenium doesn't handle drag and drop well
        self.driver.execute_script("""
            var e = document.createEvent('CustomEvent');
            e.initCustomEvent('drop', true, true, null);
            e.dataTransfer = {
                getData: function(type) { 
                    if (type === 'componentType') return 'prompt';
                    if (type === 'componentTemplate') return 'intent_classifier';
                }
            };
            arguments[0].dispatchEvent(e);
        """, canvas)
        
        # Wait for component to appear
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'canvas-component')]")
        ))
        
        # Save the agent
        save_button = self.driver.find_element(By.ID, 'save-agent')
        save_button.click()
        
        # Wait for success message
        self.wait.until(EC.alert_is_present())
        alert = self.driver.switch_to.alert
        self.assertIn('successfully', alert.text)
        alert.accept()
        
        # Verify agent appears in the list
        self.driver.get(f"{self.base_url}/agent-builder")  # Refresh page
        
        # Wait for agents list to load
        time.sleep(2)  # Give some time for AJAX call to complete
        
        # Look for our new agent in the list
        agent_row = self.driver.find_element(
            By.XPATH, 
            f"//td[text()='{agent_name}']"
        )
        self.assertIsNotNone(agent_row)
        
        # Clean up - delete the test agent
        delete_button = agent_row.find_element(
            By.XPATH, 
            "..//button[contains(@class, 'delete-agent-btn')]"
        )
        delete_button.click()
        
        # Wait for confirmation modal and confirm deletion
        self.wait.until(EC.visibility_of_element_located(
            (By.ID, 'confirm-delete-agent')
        ))
        confirm_delete = self.driver.find_element(By.ID, 'confirm-delete-agent')
        confirm_delete.click()
        
        # Wait for success message
        self.wait.until(EC.alert_is_present())
        alert = self.driver.switch_to.alert
        self.assertIn('deleted', alert.text)
        alert.accept()


if __name__ == '__main__':
    unittest.main()
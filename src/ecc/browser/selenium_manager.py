"""Selenium browser management extracted and refactored from legacy code."""

import time
from typing import Optional, Tuple, Any, List, Callable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    StaleElementReferenceException
)


class SeleniumBrowserManager:
    """
    Manages Selenium WebDriver operations with robust error handling.
    
    Extracted and refactored from legacy MF extractor for reusability.
    """
    
    def __init__(self, headless: bool = False, window_size: Tuple[int, int] = (1200, 800)):
        """
        Initialize browser manager.
        
        Args:
            headless: Run browser in headless mode
            window_size: Browser window dimensions (width, height)
        """
        self.headless = headless
        self.window_size = window_size
        self.driver: Optional[webdriver.Chrome] = None
        self.wait_timeout = 10  # Default wait timeout
        self.retry_attempts = 3  # Default retry attempts
        
    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup and configure Chrome driver with optimal settings.
        
        Returns:
            Configured Chrome WebDriver instance
        """
        chrome_options = Options()
        
        # Essential options for stability
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        
        # Additional stability options
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            chrome_options.add_argument('--headless')
            
        # Disable images for faster loading (optional)
        # prefs = {"profile.managed_default_content_settings.images": 2}
        # chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(self.window_size[0], self.window_size[1])
        
        # Set reasonable timeouts
        self.driver.implicitly_wait(5)
        self.driver.set_page_load_timeout(30)
        
        return self.driver
    
    def wait_for_element(
        self, 
        by: By, 
        value: str, 
        timeout: Optional[int] = None,
        condition: str = "presence"
    ) -> Optional[Any]:
        """
        Wait for element with specified condition.
        
        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Wait timeout in seconds
            condition: Wait condition (presence, visible, clickable)
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Call setup_driver() first.")
            
        timeout = timeout or self.wait_timeout
        
        conditions = {
            "presence": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable
        }
        
        wait_condition = conditions.get(condition, EC.presence_of_element_located)
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                wait_condition((by, value))
            )
            return element
        except TimeoutException:
            return None
            
    def safe_click(
        self, 
        element: Any, 
        retry_attempts: Optional[int] = None
    ) -> bool:
        """
        Safely click an element with retry logic.
        
        Args:
            element: WebElement to click
            retry_attempts: Number of retry attempts
            
        Returns:
            True if click successful, False otherwise
        """
        attempts = retry_attempts or self.retry_attempts
        
        for attempt in range(attempts):
            try:
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Try regular click
                element.click()
                return True
                
            except (StaleElementReferenceException, WebDriverException) as e:
                if attempt < attempts - 1:
                    time.sleep(1)
                    continue
                    
                # If regular click fails, try JavaScript click
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except:
                    return False
                    
        return False
    
    def safe_send_keys(
        self, 
        element: Any, 
        text: str, 
        clear_first: bool = True
    ) -> bool:
        """
        Safely send keys to an element.
        
        Args:
            element: WebElement to send keys to
            text: Text to send
            clear_first: Clear element before sending keys
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if clear_first:
                element.clear()
                # Backup clear method
                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(Keys.DELETE)
                
            element.send_keys(text)
            return True
        except Exception as e:
            print(f"Failed to send keys: {e}")
            return False
            
    def navigate_with_retry(
        self, 
        url: str, 
        retry_attempts: Optional[int] = None
    ) -> bool:
        """
        Navigate to URL with retry logic.
        
        Args:
            url: URL to navigate to
            retry_attempts: Number of retry attempts
            
        Returns:
            True if navigation successful, False otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Call setup_driver() first.")
            
        attempts = retry_attempts or self.retry_attempts
        
        for attempt in range(attempts):
            try:
                self.driver.get(url)
                # Wait for page to start loading
                time.sleep(2)
                
                # Check if page loaded (basic check)
                if self.driver.current_url:
                    return True
                    
            except WebDriverException as e:
                print(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < attempts - 1:
                    time.sleep(3)
                    continue
                    
        return False
    
    def dismiss_cookie_banner(self) -> bool:
        """
        Dismiss cookie consent banner if present.
        
        Common patterns from various sites.
        
        Returns:
            True if banner dismissed, False otherwise
        """
        cookie_selectors = [
            "#onetrust-reject-all-handler",  # OneTrust
            "#onetrust-accept-btn-handler",
            "button[id*='cookie-reject']",
            "button[id*='cookie-accept']",
            "button[class*='cookie-reject']",
            "button[class*='cookie-accept']",
            "button:contains('Reject')",
            "button:contains('Accept')"
        ]
        
        for selector in cookie_selectors:
            try:
                # Try ID selector
                if selector.startswith("#"):
                    element = self.driver.find_element(By.ID, selector[1:])
                # Try CSS selector
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                if element and element.is_displayed():
                    self.safe_click(element)
                    time.sleep(1)
                    return True
            except:
                continue
                
        return False
    
    def switch_to_popup_window(self) -> bool:
        """
        Switch to popup window.
        
        Returns:
            True if switched successfully, False otherwise
        """
        try:
            # Store main window handle
            main_window = self.driver.current_window_handle
            
            # Wait for popup to appear
            WebDriverWait(self.driver, 5).until(
                lambda d: len(d.window_handles) > 1
            )
            
            # Switch to popup
            for window_handle in self.driver.window_handles:
                if window_handle != main_window:
                    self.driver.switch_to.window(window_handle)
                    return True
                    
        except Exception as e:
            print(f"Failed to switch to popup: {e}")
            
        return False
    
    def close_popup_and_return(self) -> bool:
        """
        Close popup window and return to main window.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Close current window
            self.driver.close()
            
            # Switch back to main window
            self.driver.switch_to.window(self.driver.window_handles[0])
            return True
            
        except Exception as e:
            print(f"Failed to close popup: {e}")
            return False
    
    def execute_script_safe(self, script: str, *args) -> Optional[Any]:
        """
        Safely execute JavaScript with error handling.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to script
            
        Returns:
            Script result or None if failed
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            print(f"Script execution failed: {e}")
            return None
    
    def take_screenshot(self, filename: str) -> bool:
        """
        Take screenshot for debugging.
        
        Args:
            filename: Path to save screenshot
            
        Returns:
            True if screenshot saved, False otherwise
        """
        try:
            self.driver.save_screenshot(filename)
            return True
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return False
    
    def get_page_source_safe(self) -> str:
        """
        Safely get page source.
        
        Returns:
            Page source HTML or empty string if failed
        """
        try:
            return self.driver.page_source
        except:
            return ""
    
    def cleanup(self):
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        self.setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        
    def with_retry(
        self, 
        operation: Callable, 
        max_attempts: int = 3,
        delay: float = 1.0
    ) -> Optional[Any]:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Function to execute
            max_attempts: Maximum retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            Operation result or None if all attempts failed
        """
        for attempt in range(max_attempts):
            try:
                result = operation()
                if result is not None:
                    return result
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(delay)
                else:
                    print(f"All {max_attempts} attempts failed.")
                    
        return None
"""Browser management for web scraping."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class BrowserManager:
    """Manages browser instances for web scraping."""
    
    def __init__(self, download_dir: Optional[Path] = None, headless: bool = False):
        self.download_dir = download_dir or Path.cwd() / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome driver."""
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Headless mode
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--window-size=1920,1080')
        
        # Download preferences
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Create driver
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("Browser created successfully")
            return self.driver
        except WebDriverException as e:
            self.logger.error(f"Failed to create browser: {e}")
            raise
    
    def quit(self):
        """Quit the browser."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def wait_for_element(
        self, 
        by: By, 
        value: str, 
        timeout: int = 10,
        condition: str = "presence"
    ) -> Optional[Any]:
        """Wait for an element with specified condition."""
        if not self.driver:
            raise RuntimeError("Browser not initialized")
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            if condition == "presence":
                element = wait.until(EC.presence_of_element_located((by, value)))
            elif condition == "clickable":
                element = wait.until(EC.element_to_be_clickable((by, value)))
            elif condition == "visible":
                element = wait.until(EC.visibility_of_element_located((by, value)))
            else:
                raise ValueError(f"Unknown condition: {condition}")
            
            return element
            
        except TimeoutException:
            self.logger.debug(f"Element not found: {by}={value} after {timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Error waiting for element: {e}")
            return None
    
    def safe_click(self, element) -> bool:
        """Safely click an element with fallback methods."""
        try:
            # Try normal click
            element.click()
            return True
        except:
            try:
                # Try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                try:
                    # Try scrolling into view first
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    element.click()
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to click element: {e}")
                    return False
    
    def handle_popup_window(self, action: str = "switch") -> Optional[str]:
        """Handle popup windows."""
        if not self.driver:
            return None
        
        try:
            # Get current window
            current_window = self.driver.current_window_handle
            
            # Wait for new window
            WebDriverWait(self.driver, 5).until(
                lambda d: len(d.window_handles) > 1
            )
            
            # Find the new window
            for window in self.driver.window_handles:
                if window != current_window:
                    if action == "switch":
                        self.driver.switch_to.window(window)
                        return window
                    elif action == "close":
                        self.driver.switch_to.window(window)
                        self.driver.close()
                        self.driver.switch_to.window(current_window)
                        return current_window
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling popup: {e}")
            return None
    
    def dismiss_cookie_banner(self):
        """Dismiss common cookie banners."""
        cookie_selectors = [
            "onetrust-reject-all-handler",
            "accept-cookies",
            "cookie-accept",
            "gdpr-accept"
        ]
        
        for selector in cookie_selectors:
            try:
                # Try by ID
                element = self.driver.find_element(By.ID, selector)
                self.safe_click(element)
                self.logger.info(f"Dismissed cookie banner: {selector}")
                return True
            except:
                pass
            
            try:
                # Try by class
                element = self.driver.find_element(By.CLASS_NAME, selector)
                self.safe_click(element)
                self.logger.info(f"Dismissed cookie banner: {selector}")
                return True
            except:
                pass
        
        return False
    
    def take_screenshot(self, filename: str):
        """Take a screenshot for debugging."""
        if self.driver:
            try:
                screenshot_path = self.download_dir / f"screenshots/{filename}"
                screenshot_path.parent.mkdir(exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.logger.error(f"Failed to take screenshot: {e}")
    
    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser."""
        if not self.driver:
            raise RuntimeError("Browser not initialized")
        
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            raise
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get current page information."""
        if not self.driver:
            return {}
        
        return {
            'url': self.driver.current_url,
            'title': self.driver.title,
            'ready_state': self.execute_script("return document.readyState"),
            'body_text_length': len(self.driver.find_element(By.TAG_NAME, "body").text)
        }
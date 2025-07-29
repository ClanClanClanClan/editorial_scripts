"""
Unified Browser Session Management

Provides a standardized interface for browser automation with
anti-detection capabilities and resource management.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver

from .browser_config import BrowserConfig, BrowserType


class BrowserSession:
    """
    Unified browser session abstraction.
    
    Provides consistent interface for browser automation across
    all journal platforms with anti-detection and resource management.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize browser session.
        
        Args:
            config: Browser configuration settings
            logger: Logger instance for debugging
        """
        self.config = config or BrowserConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.driver: Optional[WebDriver] = None
        self._session_id: Optional[str] = None
        self._is_initialized = False
    
    async def __aenter__(self) -> 'BrowserSession':
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self) -> None:
        """
        Initialize browser session with anti-detection settings.
        
        Raises:
            WebDriverException: If browser initialization fails
        """
        if self._is_initialized:
            self.logger.warning("Browser session already initialized")
            return
        
        try:
            self.logger.info(f"Initializing {self.config.browser_type.value} browser session")
            
            # Create driver based on browser type
            if self.config.browser_type == BrowserType.UNDETECTED_CHROME:
                self.driver = await self._create_undetected_chrome()
            elif self.config.browser_type == BrowserType.CHROME:
                self.driver = await self._create_chrome()
            elif self.config.browser_type == BrowserType.FIREFOX:
                self.driver = await self._create_firefox()
            else:
                raise ValueError(f"Unsupported browser type: {self.config.browser_type}")
            
            # Configure timeouts
            self.driver.implicitly_wait(self.config.implicit_wait)
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.set_script_timeout(self.config.script_timeout)
            
            # Store session info
            self._session_id = self.driver.session_id
            self._is_initialized = True
            
            self.logger.info(f"Browser session initialized: {self._session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser session: {str(e)}")
            await self.cleanup()
            raise WebDriverException(f"Browser initialization failed: {str(e)}")
    
    async def _create_undetected_chrome(self) -> WebDriver:
        """Create undetected Chrome driver for anti-detection."""
        try:
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            
            # Add Chrome options
            for option in self.config.get_chrome_options():
                options.add_argument(option)
            
            # Add experimental options
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Download preferences
            if self.config.download_directory:
                prefs = {
                    "download.default_directory": self.config.download_directory,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True
                }
                options.add_experimental_option("prefs", prefs)
            
            # Create driver
            driver = uc.Chrome(options=options, version_main=None)
            
            # Execute stealth script
            await self._apply_stealth_settings(driver)
            
            return driver
            
        except ImportError:
            self.logger.warning("undetected_chromedriver not available, falling back to regular Chrome")
            return await self._create_chrome()
    
    async def _create_chrome(self) -> WebDriver:
        """Create regular Chrome driver."""
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        
        # Add Chrome options
        for option in self.config.get_chrome_options():
            options.add_argument(option)
        
        # Add experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Download preferences
        if self.config.download_directory:
            prefs = {
                "download.default_directory": self.config.download_directory,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
        
        # Create driver
        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        
        # Apply stealth settings
        await self._apply_stealth_settings(driver)
        
        return driver
    
    async def _create_firefox(self) -> WebDriver:
        """Create Firefox driver."""
        from selenium.webdriver.firefox.options import Options
        
        options = Options()
        
        if self.config.headless:
            options.add_argument("--headless")
        
        # Set preferences
        for key, value in self.config.get_firefox_prefs().items():
            options.set_preference(key, value)
        
        # Create driver
        service = FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)
        
        return driver
    
    async def _apply_stealth_settings(self, driver: WebDriver) -> None:
        """Apply stealth settings to evade detection."""
        try:
            # Override webdriver property
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Override plugins
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            # Override languages
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            self.logger.debug("Applied stealth settings")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply stealth settings: {str(e)}")
    
    async def navigate(self, url: str, wait_for_load: bool = True) -> None:
        """
        Navigate to URL with optional load waiting.
        
        Args:
            url: URL to navigate to
            wait_for_load: Whether to wait for page load completion
        """
        if not self.driver:
            raise RuntimeError("Browser session not initialized")
        
        self.logger.info(f"Navigating to: {url}")
        
        try:
            self.driver.get(url)
            
            if wait_for_load:
                await self.wait_for_page_load()
                
        except TimeoutException:
            self.logger.error(f"Navigation timeout for URL: {url}")
            raise
        except Exception as e:
            self.logger.error(f"Navigation failed for URL {url}: {str(e)}")
            raise
    
    async def find_element(self, selector: str, by: By = By.CSS_SELECTOR, 
                         timeout: int = 10) -> Optional[object]:
        """
        Find element with wait and error handling.
        
        Args:
            selector: Element selector
            by: Selenium By method
            timeout: Wait timeout in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            raise RuntimeError("Browser session not initialized")
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element
            
        except TimeoutException:
            self.logger.debug(f"Element not found: {selector}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {selector}: {str(e)}")
            return None
    
    async def find_elements(self, selector: str, by: By = By.CSS_SELECTOR) -> List[object]:
        """
        Find multiple elements.
        
        Args:
            selector: Element selector
            by: Selenium By method
            
        Returns:
            List of WebElements
        """
        if not self.driver:
            raise RuntimeError("Browser session not initialized")
        
        try:
            elements = self.driver.find_elements(by, selector)
            return elements
            
        except Exception as e:
            self.logger.error(f"Error finding elements {selector}: {str(e)}")
            return []
    
    async def click_element(self, selector: str, by: By = By.CSS_SELECTOR, 
                          timeout: int = 10) -> bool:
        """
        Click element with wait and error handling.
        
        Args:
            selector: Element selector
            by: Selenium By method
            timeout: Wait timeout in seconds
            
        Returns:
            True if clicked successfully
        """
        element = await self.find_element(selector, by, timeout)
        
        if element:
            try:
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                await asyncio.sleep(0.5)
                
                # Wait for clickable
                wait = WebDriverWait(self.driver, timeout)
                clickable_element = wait.until(EC.element_to_be_clickable((by, selector)))
                
                clickable_element.click()
                await asyncio.sleep(1)
                
                self.logger.debug(f"Clicked element: {selector}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to click element {selector}: {str(e)}")
                return False
        
        return False
    
    async def send_keys(self, selector: str, text: str, by: By = By.CSS_SELECTOR, 
                       clear_first: bool = True, timeout: int = 10) -> bool:
        """
        Send keys to element.
        
        Args:
            selector: Element selector
            text: Text to send
            by: Selenium By method
            clear_first: Whether to clear field first
            timeout: Wait timeout in seconds
            
        Returns:
            True if successful
        """
        element = await self.find_element(selector, by, timeout)
        
        if element:
            try:
                if clear_first:
                    element.clear()
                
                element.send_keys(text)
                await asyncio.sleep(0.5)
                
                self.logger.debug(f"Sent keys to element: {selector}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to send keys to {selector}: {str(e)}")
                return False
        
        return False
    
    async def download_file(self, url: str, filepath: Path, timeout: int = 60) -> bool:
        """
        Download file from URL.
        
        Args:
            url: File URL
            filepath: Local file path
            timeout: Download timeout in seconds
            
        Returns:
            True if download successful
        """
        try:
            self.logger.info(f"Downloading file: {url}")
            
            # Use requests for direct download
            import requests
            
            headers = {
                'User-Agent': self.config.user_agent
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=timeout)
            response.raise_for_status()
            
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify download
            if filepath.exists() and filepath.stat().st_size > 0:
                self.logger.info(f"Downloaded: {filepath.name} ({filepath.stat().st_size} bytes)")
                return True
            else:
                self.logger.error(f"Download failed or file empty: {filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"Download error for {url}: {str(e)}")
            return False
    
    async def wait_for_page_load(self, timeout: int = 30) -> None:
        """
        Wait for page to fully load.
        
        Args:
            timeout: Wait timeout in seconds
        """
        if not self.driver:
            return
        
        try:
            # Wait for document ready state
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for jQuery if available
            try:
                self.driver.execute_script("""
                    return (typeof jQuery !== 'undefined') ? jQuery.active == 0 : true;
                """)
            except:
                pass
            
            # Additional wait
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.debug(f"Page load wait error: {str(e)}")
    
    async def dismiss_overlays(self) -> None:
        """Dismiss common overlays and popups."""
        if not self.driver:
            return
        
        overlay_selectors = [
            # Cookie banners
            "#onetrust-accept-btn-handler",
            ".cookie-accept",
            "[class*='cookie'] button",
            
            # Modal dialogs
            ".modal-close",
            ".close-modal",
            "[aria-label='Close']",
            
            # Notifications
            ".notification-close",
            ".alert-close"
        ]
        
        for selector in overlay_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    element.click()
                    await asyncio.sleep(0.5)
                    self.logger.debug(f"Dismissed overlay: {selector}")
            except:
                continue
    
    async def take_screenshot(self, filepath: Path) -> bool:
        """
        Take screenshot of current page.
        
        Args:
            filepath: Screenshot file path
            
        Returns:
            True if screenshot taken successfully
        """
        if not self.driver:
            return False
        
        try:
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Take screenshot
            success = self.driver.save_screenshot(str(filepath))
            
            if success:
                self.logger.info(f"Screenshot saved: {filepath}")
                return True
            else:
                self.logger.error(f"Screenshot failed: {filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"Screenshot error: {str(e)}")
            return False
    
    def get_page_source(self) -> str:
        """Get current page source."""
        if not self.driver:
            return ""
        
        return self.driver.page_source
    
    def get_current_url(self) -> str:
        """Get current URL."""
        if not self.driver:
            return ""
        
        return self.driver.current_url
    
    async def cleanup(self) -> None:
        """Clean up browser session and resources."""
        if self.driver:
            try:
                self.logger.info("Cleaning up browser session")
                
                # Clear cache and cookies
                try:
                    self.driver.delete_all_cookies()
                    self.driver.execute_script("window.localStorage.clear();")
                    self.driver.execute_script("window.sessionStorage.clear();")
                except:
                    pass
                
                # Close browser
                self.driver.quit()
                self.logger.info("Browser session cleaned up")
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {str(e)}")
            finally:
                self.driver = None
                self._session_id = None
                self._is_initialized = False


@asynccontextmanager
async def browser_session(config: Optional[BrowserConfig] = None, 
                         logger: Optional[logging.Logger] = None):
    """
    Async context manager for browser sessions.
    
    Args:
        config: Browser configuration
        logger: Logger instance
        
    Yields:
        BrowserSession instance
    """
    session = BrowserSession(config, logger)
    try:
        await session.initialize()
        yield session
    finally:
        await session.cleanup()
"""Browser management module for web automation.

Provides centralized browser setup, configuration, and lifecycle management
for extraction operations. Handles Chrome/Firefox setup, options, waits, and
safe cleanup.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .error_handling import ExtractorError, SafeExecutor
from .logging_system import ExtractorLogger, LogCategory
from .retry_strategies import RetryConfigs, retry


class BrowserType(Enum):
    """Supported browser types."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


@dataclass
class BrowserConfig:
    """Browser configuration settings."""

    browser_type: BrowserType = BrowserType.CHROME
    headless: bool = False
    window_size: tuple = (1440, 900)
    download_dir: Path | None = None
    disable_gpu: bool = True
    no_sandbox: bool = True
    disable_dev_shm: bool = True
    disable_blink_features: bool = True
    user_agent: str | None = None
    implicit_wait: int = 10
    page_load_timeout: int = 30
    script_timeout: int = 30
    accept_insecure_certs: bool = False

    def __post_init__(self):
        """Set up default download directory if not provided."""
        if self.download_dir is None:
            # Use project-specific directory - NO POLLUTION of user Downloads
            project_root = Path(__file__).parent.parent.parent.parent
            self.download_dir = project_root / "dev" / "outputs" / "downloads"

        # Ensure download directory exists
        self.download_dir.mkdir(parents=True, exist_ok=True)


class BrowserManager:
    """Manages browser lifecycle and operations for extraction."""

    def __init__(
        self,
        config: BrowserConfig | None = None,
        logger: ExtractorLogger | None = None,
        safe_executor: SafeExecutor | None = None,
    ):
        """
        Initialize browser manager.

        Args:
            config: Browser configuration settings
            logger: Logger instance for output
            safe_executor: Safe executor for error handling
        """
        self.config = config or BrowserConfig()
        self.logger = logger or ExtractorLogger("browser_manager")
        self.safe_executor = safe_executor or SafeExecutor(self.logger.logger)
        self.driver: webdriver.Chrome | webdriver.Firefox | None = None
        self._original_window = None

    def setup_chrome_options(self) -> ChromeOptions:
        """Configure Chrome browser options."""
        options = ChromeOptions()

        # Basic options
        if self.config.headless:
            options.add_argument("--headless")

        options.add_argument(
            f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}"
        )

        # Performance and stability options
        if self.config.disable_gpu:
            options.add_argument("--disable-gpu")
        if self.config.no_sandbox:
            options.add_argument("--no-sandbox")
        if self.config.disable_dev_shm:
            options.add_argument("--disable-dev-shm-usage")
        if self.config.disable_blink_features:
            options.add_argument("--disable-blink-features=AutomationControlled")

        # Download configuration
        prefs = {
            "download.default_directory": str(self.config.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)

        # User agent if specified
        if self.config.user_agent:
            options.add_argument(f"--user-agent={self.config.user_agent}")

        # Disable automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def setup_firefox_options(self) -> FirefoxOptions:
        """Configure Firefox browser options."""
        options = FirefoxOptions()

        if self.config.headless:
            options.add_argument("--headless")

        # Set window size
        options.add_argument(f"--width={self.config.window_size[0]}")
        options.add_argument(f"--height={self.config.window_size[1]}")

        # Download preferences
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", str(self.config.download_dir))
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/x-pdf,application/octet-stream",
        )

        return options

    def setup_driver(self) -> webdriver.Chrome | webdriver.Firefox:
        """
        Set up and configure the web driver.

        Returns:
            Configured web driver instance

        Raises:
            ExtractorError: If driver setup fails
        """
        self.logger.enter_context("browser_setup")

        try:
            if self.config.browser_type == BrowserType.CHROME:
                options = self.setup_chrome_options()
                self.driver = webdriver.Chrome(options=options)
                self.logger.success("Chrome driver initialized", LogCategory.NAVIGATION)

            elif self.config.browser_type == BrowserType.FIREFOX:
                options = self.setup_firefox_options()
                self.driver = webdriver.Firefox(options=options)
                self.logger.success("Firefox driver initialized", LogCategory.NAVIGATION)

            else:
                raise ExtractorError(f"Unsupported browser type: {self.config.browser_type}")

            # Configure timeouts
            self.driver.implicitly_wait(self.config.implicit_wait)
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.set_script_timeout(self.config.script_timeout)

            # Store original window handle
            self._original_window = self.driver.current_window_handle

            self.logger.success("Browser setup complete")
            return self.driver

        except Exception as e:
            self.logger.error(f"Failed to setup browser: {e}")
            raise ExtractorError(f"Browser setup failed: {e}") from e

        finally:
            self.logger.exit_context(success=self.driver is not None)

    @retry(config=RetryConfigs.NAVIGATION)
    def navigate_to(self, url: str, wait_for: tuple | None = None):
        """
        Navigate to a URL with retry logic.

        Args:
            url: Target URL
            wait_for: Optional (By, value) tuple to wait for after navigation
        """
        if not self.driver:
            raise ExtractorError("Browser not initialized")

        self.logger.info(f"Navigating to: {url}", LogCategory.NAVIGATION)

        self.driver.get(url)

        if wait_for:
            self.wait_for_element(wait_for[0], wait_for[1])

        self.logger.success("Navigation complete", LogCategory.NAVIGATION)

    def wait_for_element(
        self, by: By, value: str, timeout: int = 10, condition: str = "presence"
    ) -> Any:
        """
        Wait for an element with specified condition.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum wait time in seconds
            condition: Wait condition (presence, visible, clickable)

        Returns:
            Web element when found

        Raises:
            TimeoutException: If element not found within timeout
        """
        if not self.driver:
            raise ExtractorError("Browser not initialized")

        wait = WebDriverWait(self.driver, timeout)

        conditions = {
            "presence": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "all_present": EC.presence_of_all_elements_located,
        }

        condition_func = conditions.get(condition, EC.presence_of_element_located)

        try:
            element = wait.until(condition_func((by, value)))
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            raise

    def safe_click(self, element, retry_stale: bool = True) -> bool:
        """
        Safely click an element with error handling.

        Args:
            element: Web element to click
            retry_stale: Whether to retry on stale element

        Returns:
            True if click successful, False otherwise
        """
        if element is None:
            return False

        try:
            element.click()
            return True

        except StaleElementReferenceException:
            if retry_stale:
                self.logger.warning("Stale element, retrying click")
                time.sleep(0.5)
                return self.safe_click(element, retry_stale=False)
            return False

        except WebDriverException as e:
            # Try JavaScript click as fallback
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                self.logger.error(f"Failed to click element: {e}")
                return False

    def switch_to_popup(self) -> bool:
        """
        Switch to popup window.

        Returns:
            True if switched successfully
        """
        if not self.driver:
            return False

        try:
            # Wait for new window
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)

            # Switch to new window
            for window_handle in self.driver.window_handles:
                if window_handle != self._original_window:
                    self.driver.switch_to.window(window_handle)
                    self.logger.success("Switched to popup window", LogCategory.POPUP)
                    return True

            return False

        except TimeoutException:
            self.logger.warning("No popup window found")
            return False

    def close_popup_and_return(self) -> bool:
        """
        Close current popup and return to original window.

        Returns:
            True if returned successfully
        """
        if not self.driver or not self._original_window:
            return False

        try:
            # Close current window if it's not the original
            if self.driver.current_window_handle != self._original_window:
                self.driver.close()

            # Switch back to original
            self.driver.switch_to.window(self._original_window)
            self.logger.success("Returned to main window", LogCategory.POPUP)
            return True

        except WebDriverException as e:
            self.logger.error(f"Failed to return from popup: {e}")
            return False

    def handle_alerts(self, accept: bool = True) -> str | None:
        """
        Handle JavaScript alerts.

        Args:
            accept: Whether to accept or dismiss the alert

        Returns:
            Alert text if present, None otherwise
        """
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text

            if accept:
                alert.accept()
                self.logger.info(f"Accepted alert: {alert_text}")
            else:
                alert.dismiss()
                self.logger.info(f"Dismissed alert: {alert_text}")

            return alert_text

        except Exception:
            return None

    def take_screenshot(self, filename: str | None = None) -> Path | None:
        """
        Take a screenshot for debugging.

        Args:
            filename: Optional filename for screenshot

        Returns:
            Path to saved screenshot or None
        """
        if not self.driver:
            return None

        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        screenshot_path = self.config.download_dir / "screenshots" / filename
        screenshot_path.parent.mkdir(exist_ok=True)

        try:
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None

    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser.

        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script

        Returns:
            Script execution result
        """
        if not self.driver:
            raise ExtractorError("Browser not initialized")

        return self.driver.execute_script(script, *args)

    def scroll_to_element(self, element) -> bool:
        """
        Scroll element into view.

        Args:
            element: Web element to scroll to

        Returns:
            True if successful
        """
        try:
            self.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)  # Allow time for scroll
            return True
        except Exception as e:
            self.logger.error(f"Failed to scroll to element: {e}")
            return False

    def cleanup(self):
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.success("Browser closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self._original_window = None

    @contextmanager
    def browser_session(self):
        """
        Context manager for browser session.

        Usage:
            with browser_manager.browser_session():
                # Browser operations here
                pass
        """
        try:
            self.setup_driver()
            yield self.driver
        finally:
            self.cleanup()

    def is_alive(self) -> bool:
        """
        Check if browser is still responsive.

        Returns:
            True if browser is alive
        """
        if not self.driver:
            return False

        try:
            _ = self.driver.current_url
            return True
        except Exception:
            return False

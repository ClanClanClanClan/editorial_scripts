"""
Browser management for the Editorial Assistant system.

This module handles all browser/driver creation and management,
including robust error handling and multiple fallback strategies.
"""

import logging
import os
import time
from pathlib import Path

try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.remote.webdriver import WebDriver
except ImportError:
    raise ImportError("Please install selenium and undetected-chromedriver")

from .exceptions import BrowserError


class BrowserManager:
    """Manages browser instances with robust error handling."""

    def __init__(self, headless: bool = True, download_dir: Path | None = None):
        """
        Initialize browser manager.

        Args:
            headless: Run browser in headless mode
            download_dir: Directory for downloads
        """
        self.headless = headless
        self.download_dir = download_dir or Path.cwd() / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("editorial_assistant.browser")
        self.driver_creation_attempts = 0
        self.max_creation_attempts = 5

    def create_driver(self) -> WebDriver:
        """
        Create a WebDriver instance with fallback strategies.

        Returns:
            WebDriver instance

        Raises:
            BrowserError: If all creation attempts fail
        """
        strategies = [
            self._create_undetected_chrome,
            self._create_undetected_chrome_with_options,
            self._create_standard_chrome,
            self._create_chrome_with_minimal_options,
            self._create_chrome_with_different_binary,
        ]

        for i, strategy in enumerate(strategies):
            try:
                self.logger.info(
                    f"Attempting driver creation strategy {i+1}/{len(strategies)}: {strategy.__name__}"
                )
                driver = strategy()

                # Test the driver
                driver.get("about:blank")
                self.logger.info(f"Successfully created driver using {strategy.__name__}")

                # Configure driver settings
                self._configure_driver(driver)

                return driver

            except Exception as e:
                self.logger.error(f"Strategy {strategy.__name__} failed: {str(e)}")
                if i == len(strategies) - 1:
                    raise BrowserError(
                        f"All driver creation strategies failed. Last error: {str(e)}"
                    )
                time.sleep(2)  # Brief pause between attempts

    def _create_undetected_chrome(self) -> WebDriver:
        """Create undetected Chrome driver with default settings."""
        options = self._get_chrome_options()

        driver = uc.Chrome(
            options=options,
            version_main=None,  # Auto-detect version
            driver_executable_path=None,  # Auto-download
        )

        return driver

    def _create_undetected_chrome_with_options(self) -> WebDriver:
        """Create undetected Chrome with specific options."""
        options = self._get_chrome_options()

        # Additional options for stability
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = uc.Chrome(
            options=options,
            use_subprocess=True,  # Use subprocess for better stability
            version_main=None,
        )

        return driver

    def _create_standard_chrome(self) -> WebDriver:
        """Create standard Chrome driver."""
        options = self._get_chrome_options()

        # Try to find Chrome binary
        chrome_binary = self._find_chrome_binary()
        if chrome_binary:
            options.binary_location = chrome_binary

        driver = webdriver.Chrome(options=options)

        return driver

    def _create_chrome_with_minimal_options(self) -> WebDriver:
        """Create Chrome with minimal options."""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Minimal required options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)

        return driver

    def _create_chrome_with_different_binary(self) -> WebDriver:
        """Try different Chrome binary locations."""
        options = self._get_chrome_options()

        # Common Chrome binary locations
        binary_locations = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "/usr/bin/google-chrome",  # Linux
            "/usr/bin/chromium-browser",  # Linux chromium
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows 32-bit
        ]

        for binary in binary_locations:
            if os.path.exists(binary):
                self.logger.info(f"Trying Chrome binary: {binary}")
                options.binary_location = binary

                try:
                    driver = webdriver.Chrome(options=options)
                    return driver
                except:
                    continue

        raise WebDriverException("No valid Chrome binary found")

    def _get_chrome_options(self) -> Options:
        """Get Chrome options with all necessary settings."""
        options = uc.ChromeOptions() if hasattr(uc, "ChromeOptions") else Options()

        # Basic options
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-extensions")

        # Headless mode
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")

        # Download settings
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)

        # Performance options
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_argument("--silent")

        # Stability options
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")

        return options

    def _find_chrome_binary(self) -> str | None:
        """Find Chrome binary location."""
        import platform

        system = platform.system()

        if system == "Darwin":  # macOS
            paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        elif system == "Linux":
            paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
        elif system == "Windows":
            paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
            ]
        else:
            return None

        for path in paths:
            if os.path.exists(path):
                return path

        return None

    def _configure_driver(self, driver: WebDriver) -> None:
        """Configure driver with optimal settings."""
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        # Enable downloads in headless mode
        if self.headless:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(self.download_dir)},
            )

    def quit_driver(self, driver: WebDriver) -> None:
        """Safely quit driver."""
        try:
            driver.quit()
            self.logger.info("Driver quit successfully")
        except Exception as e:
            self.logger.error(f"Error quitting driver: {e}")
            # Force kill if needed
            try:
                driver.service.process.kill()
            except:
                pass

    def restart_driver(self, driver: WebDriver) -> WebDriver:
        """Restart driver instance."""
        self.logger.info("Restarting driver...")
        self.quit_driver(driver)
        time.sleep(2)  # Brief pause
        return self.create_driver()

    def dismiss_overlays(self, driver: WebDriver) -> None:
        """Aggressively dismiss all overlays and popups."""
        scripts = [
            # Remove cookie banners
            """
            ['#onetrust-banner-sdk', '.onetrust-pc-dark-filter', '#onetrust-consent-sdk',
             '[class*="cookie"]', '[id*="cookie"]', '[class*="consent"]', '[id*="consent"]',
             '.cc-window', '#cookieModal', '.gdpr', '.privacy-prompt'].forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
            """,
            # Remove overlays
            """
            document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="popup"]').forEach(el => {
                if (window.getComputedStyle(el).position === 'fixed' ||
                    window.getComputedStyle(el).position === 'absolute') {
                    el.remove();
                }
            });
            """,
            # Reset body scroll
            """
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
            """,
            # Remove high z-index elements
            """
            document.querySelectorAll('*').forEach(el => {
                const zIndex = window.getComputedStyle(el).zIndex;
                if (zIndex && parseInt(zIndex) > 9000) {
                    el.style.display = 'none';
                }
            });
            """,
        ]

        for script in scripts:
            try:
                driver.execute_script(script)
            except Exception as e:
                self.logger.debug(f"Overlay removal script failed: {e}")

    def handle_download(self, driver: WebDriver, timeout: int = 30) -> Path | None:
        """
        Wait for and handle file download.

        Args:
            driver: WebDriver instance
            timeout: Maximum wait time

        Returns:
            Path to downloaded file if successful
        """
        import glob

        # Get initial file list
        initial_files = set(glob.glob(str(self.download_dir / "*")))

        # Wait for new file
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_files = set(glob.glob(str(self.download_dir / "*")))
            new_files = current_files - initial_files

            if new_files:
                # Wait for download to complete
                new_file = Path(list(new_files)[0])

                # Check if file is still downloading
                if new_file.suffix == ".crdownload":
                    time.sleep(1)
                    continue

                # Verify file is complete
                size = new_file.stat().st_size
                time.sleep(1)
                if new_file.stat().st_size == size:
                    self.logger.info(f"Downloaded: {new_file}")
                    return new_file

            time.sleep(1)

        self.logger.warning(f"Download timeout after {timeout} seconds")
        return None

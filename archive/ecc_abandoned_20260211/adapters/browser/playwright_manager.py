"""Async Playwright browser manager for ECC.

Replaces Selenium-based browser automation with modern async Playwright.
Implements the browser automation requirements from ECC specifications v2.0:
- Async/await throughout
- Modern browser automation
- Better performance and reliability
- Advanced debugging capabilities
"""

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.ecc.core.error_handling import ExtractorError, SafeExecutor
from src.ecc.core.logging_system import ExtractorLogger, LogCategory
from src.ecc.core.retry_strategies import RetryConfigs, retry


class BrowserType(Enum):
    """Supported browser types."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ViewportSize(Enum):
    """Common viewport sizes."""

    LAPTOP = {"width": 1366, "height": 768}
    DESKTOP = {"width": 1920, "height": 1080}
    TABLET = {"width": 768, "height": 1024}
    MOBILE = {"width": 375, "height": 667}


@dataclass
class PlaywrightConfig:
    """Playwright browser configuration."""

    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    viewport: dict[str, int] = None
    download_dir: Path | None = None
    timeout: int = 30000  # 30 seconds
    navigation_timeout: int = 60000  # 1 minute
    slow_mo: int = 0  # Delay between actions in milliseconds
    user_agent: str | None = None
    ignore_https_errors: bool = True
    java_script_enabled: bool = True

    # Security settings
    bypass_csp: bool = False
    ignore_default_args: list[str] = None

    # Recording and debugging
    record_video: bool = False
    record_trace: bool = False
    screenshot_mode: str = "only-on-failure"  # "off", "on", "only-on-failure", "retain-on-failure"

    def __post_init__(self):
        """Set up default configurations."""
        if self.viewport is None:
            self.viewport = ViewportSize.DESKTOP.value

        if self.download_dir is None:
            # Use project-specific directory - NO POLLUTION
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.download_dir = project_root / "dev" / "outputs" / "downloads"

        # Ensure download directory exists
        self.download_dir.mkdir(parents=True, exist_ok=True)

        if self.ignore_default_args is None:
            self.ignore_default_args = []


class PlaywrightManager:
    """Async browser manager using Playwright."""

    def __init__(
        self,
        config: PlaywrightConfig | None = None,
        logger: ExtractorLogger | None = None,
        safe_executor: SafeExecutor | None = None,
    ):
        """
        Initialize Playwright manager.

        Args:
            config: Playwright configuration
            logger: Logger instance
            safe_executor: Safe executor for error handling
        """
        self.config = config or PlaywrightConfig()
        self.logger = logger or ExtractorLogger("playwright_manager")
        self.safe_executor = safe_executor or SafeExecutor(self.logger.logger)

        # Playwright instances
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        # State tracking
        self.is_initialized = False
        self.pages_opened = 0
        self.screenshots_taken = 0

        # Performance tracking
        self.navigation_times = []
        self.action_times = []

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def initialize(self):
        """Initialize Playwright browser."""
        self.logger.enter_context("playwright_init")

        try:
            # Start Playwright
            self.playwright = await async_playwright().start()

            # Get browser type
            if self.config.browser_type == BrowserType.CHROMIUM:
                browser_type = self.playwright.chromium
            elif self.config.browser_type == BrowserType.FIREFOX:
                browser_type = self.playwright.firefox
            elif self.config.browser_type == BrowserType.WEBKIT:
                browser_type = self.playwright.webkit
            else:
                raise ExtractorError(f"Unsupported browser type: {self.config.browser_type}")

            # Launch browser
            launch_options = {
                "headless": self.config.headless,
                "slow_mo": self.config.slow_mo,
                "timeout": self.config.timeout,
            }

            if self.config.ignore_default_args:
                launch_options["args"] = [f"--{arg}" for arg in self.config.ignore_default_args]

            self.browser = await browser_type.launch(**launch_options)

            # Create context
            context_options = {
                "viewport": self.config.viewport,
                "ignore_https_errors": self.config.ignore_https_errors,
                "java_script_enabled": self.config.java_script_enabled,
                "bypass_csp": self.config.bypass_csp,
                "accept_downloads": True,
            }

            if self.config.user_agent:
                context_options["user_agent"] = self.config.user_agent

            # Set up downloads
            if self.config.download_dir:
                context_options["accept_downloads"] = True

            # Recording options
            if self.config.record_video:
                context_options["record_video"] = {"dir": str(self.config.download_dir / "videos")}

            if self.config.record_trace:
                context_options["record_trace"] = {"dir": str(self.config.download_dir / "traces")}

            self.context = await self.browser.new_context(**context_options)

            # Set timeouts
            self.context.set_default_timeout(self.config.timeout)
            self.context.set_default_navigation_timeout(self.config.navigation_timeout)

            # Create initial page
            self.page = await self.context.new_page()
            self.pages_opened += 1

            # Set up page event handlers
            await self._setup_page_handlers()

            self.is_initialized = True

            self.logger.success(
                f"Playwright initialized: {self.config.browser_type.value} "
                f"(headless: {self.config.headless})",
                LogCategory.NAVIGATION,
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            await self.cleanup()
            raise ExtractorError("Playwright initialization failed") from e

        finally:
            self.logger.exit_context(success=self.is_initialized)

    async def _setup_page_handlers(self):
        """Set up page event handlers for debugging and logging."""
        if not self.page:
            return

        # Request/response logging
        async def log_request(request):
            if self.logger:
                self.logger.debug(f"Request: {request.method} {request.url}")

        async def log_response(response):
            if self.logger and response.status >= 400:
                self.logger.warning(f"Response error: {response.status} {response.url}")

        # Console message handling
        async def log_console(msg):
            if self.logger:
                if msg.type == "error":
                    self.logger.warning(f"Browser console error: {msg.text}")
                elif msg.type == "warning":
                    self.logger.info(f"Browser console warning: {msg.text}")

        # Page crash handling
        async def handle_crash():
            if self.logger:
                self.logger.error("Browser page crashed")

        # Set up handlers
        self.page.on("request", log_request)
        self.page.on("response", log_response)
        self.page.on("console", log_console)
        self.page.on("crash", handle_crash)

    @retry(config=RetryConfigs.NAVIGATION)
    async def navigate_to(
        self,
        url: str,
        wait_until: str = "networkidle",
        wait_for_selector: str | None = None,
        timeout: int | None = None,
    ):
        """
        Navigate to a URL with advanced waiting options.

        Args:
            url: Target URL
            wait_until: When to consider navigation complete
                      ("load", "domcontentloaded", "networkidle", "commit")
            wait_for_selector: Optional selector to wait for after navigation
            timeout: Optional timeout override
        """
        if not self.page:
            raise ExtractorError("Browser not initialized")

        self.logger.enter_context(f"navigate_to_{url}")
        start_time = time.time()

        try:
            # Navigate
            await self.page.goto(
                url, wait_until=wait_until, timeout=timeout or self.config.navigation_timeout
            )

            # Wait for specific selector if provided
            if wait_for_selector:
                await self.page.wait_for_selector(
                    wait_for_selector, timeout=timeout or self.config.timeout
                )

            # Track performance
            navigation_time = time.time() - start_time
            self.navigation_times.append(navigation_time)

            self.logger.success(
                f"Navigation complete: {url} ({navigation_time:.2f}s)", LogCategory.NAVIGATION
            )

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Navigation timeout: {url} - {e}")
            raise ExtractorError(f"Navigation timeout: {url}") from e

        except Exception as e:
            self.logger.error(f"Navigation failed: {url} - {e}")
            raise ExtractorError(f"Navigation failed: {url} - {e}") from e

        finally:
            self.logger.exit_context(success=True)

    async def wait_for_selector(
        self, selector: str, state: str = "visible", timeout: int | None = None
    ) -> Any:
        """
        Wait for element with advanced state options.

        Args:
            selector: CSS/XPath selector
            state: Element state to wait for
                  ("attached", "detached", "visible", "hidden")
            timeout: Optional timeout override

        Returns:
            Element handle when found
        """
        if not self.page:
            raise ExtractorError("Browser not initialized")

        try:
            element = await self.page.wait_for_selector(
                selector, state=state, timeout=timeout or self.config.timeout
            )

            return element

        except PlaywrightTimeoutError:
            self.logger.warning(f"Element not found: {selector} (state: {state})")
            raise

    async def click_element(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        delay: int = 0,
        force: bool = False,
        no_wait_after: bool = False,
        timeout: int | None = None,
    ) -> bool:
        """
        Click element with advanced options.

        Args:
            selector: CSS/XPath selector
            button: Mouse button ("left", "right", "middle")
            click_count: Number of clicks
            delay: Delay between clicks
            force: Force click even if element not visible
            no_wait_after: Don't wait for navigation after click
            timeout: Optional timeout override

        Returns:
            True if click successful
        """
        if not self.page:
            return False

        start_time = time.time()

        try:
            await self.page.click(
                selector,
                button=button,
                click_count=click_count,
                delay=delay,
                force=force,
                no_wait_after=no_wait_after,
                timeout=timeout or self.config.timeout,
            )

            # Track performance
            action_time = time.time() - start_time
            self.action_times.append(action_time)

            return True

        except PlaywrightTimeoutError:
            self.logger.warning(f"Click timeout: {selector}")
            return False

        except Exception as e:
            self.logger.error(f"Click failed: {selector} - {e}")
            return False

    async def fill_input(
        self,
        selector: str,
        value: str,
        clear: bool = True,
        force: bool = False,
        no_wait_after: bool = False,
        timeout: int | None = None,
    ) -> bool:
        """
        Fill input field with text.

        Args:
            selector: CSS/XPath selector
            value: Text to fill
            clear: Clear field before filling
            force: Force fill even if element not visible
            no_wait_after: Don't wait after filling
            timeout: Optional timeout override

        Returns:
            True if fill successful
        """
        if not self.page:
            return False

        try:
            if clear:
                await self.page.fill(
                    selector,
                    value,
                    force=force,
                    no_wait_after=no_wait_after,
                    timeout=timeout or self.config.timeout,
                )
            else:
                await self.page.type(
                    selector,
                    value,
                    delay=50,  # Small delay between keystrokes
                    timeout=timeout or self.config.timeout,
                )

            return True

        except Exception as e:
            self.logger.error(f"Fill input failed: {selector} - {e}")
            return False

    async def select_option(
        self,
        selector: str,
        value: str | None = None,
        index: int | None = None,
        label: str | None = None,
        timeout: int | None = None,
    ) -> list[str]:
        """
        Select option from dropdown.

        Args:
            selector: CSS/XPath selector for select element
            value: Option value to select
            index: Option index to select
            label: Option label to select
            timeout: Optional timeout override

        Returns:
            List of selected option values
        """
        if not self.page:
            return []

        try:
            if value:
                return await self.page.select_option(
                    selector, value=value, timeout=timeout or self.config.timeout
                )
            elif index is not None:
                return await self.page.select_option(
                    selector, index=index, timeout=timeout or self.config.timeout
                )
            elif label:
                return await self.page.select_option(
                    selector, label=label, timeout=timeout or self.config.timeout
                )
            else:
                raise ExtractorError("Must specify value, index, or label for select option")

        except Exception as e:
            self.logger.error(f"Select option failed: {selector} - {e}")
            return []

    async def get_text(self, selector: str, timeout: int | None = None) -> str | None:
        """
        Get text content of element.

        Args:
            selector: CSS/XPath selector
            timeout: Optional timeout override

        Returns:
            Element text content or None
        """
        if not self.page:
            return None

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout or self.config.timeout
            )

            if element:
                return await element.text_content()

            return None

        except PlaywrightTimeoutError:
            return None

        except Exception as e:
            self.logger.error(f"Get text failed: {selector} - {e}")
            return None

    async def get_attribute(
        self, selector: str, attribute: str, timeout: int | None = None
    ) -> str | None:
        """
        Get attribute value of element.

        Args:
            selector: CSS/XPath selector
            attribute: Attribute name
            timeout: Optional timeout override

        Returns:
            Attribute value or None
        """
        if not self.page:
            return None

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout or self.config.timeout
            )

            if element:
                return await element.get_attribute(attribute)

            return None

        except PlaywrightTimeoutError:
            return None

        except Exception as e:
            self.logger.error(f"Get attribute failed: {selector}.{attribute} - {e}")
            return None

    async def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in browser.

        Args:
            script: JavaScript code
            *args: Arguments to pass to script

        Returns:
            Script execution result
        """
        if not self.page:
            raise ExtractorError("Browser not initialized")

        try:
            # Handle common Selenium-style return statements for Playwright compatibility
            if script.strip().startswith("return "):
                # Convert "return expression;" to "() => expression"
                expression = script.strip()[7:].rstrip(";")
                script = f"() => {expression}"

            return await self.page.evaluate(script, *args)

        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            raise ExtractorError(f"Script execution failed: {e}") from e

    async def take_screenshot(
        self, path: Path | None = None, full_page: bool = False, clip: dict[str, int] | None = None
    ) -> Path:
        """
        Take screenshot of current page.

        Args:
            path: Optional path for screenshot
            full_page: Capture full page or just viewport
            clip: Optional area to clip {"x": 0, "y": 0, "width": 100, "height": 100}

        Returns:
            Path to saved screenshot
        """
        if not self.page:
            raise ExtractorError("Browser not initialized")

        if path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = self.config.download_dir / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            path = screenshot_dir / f"screenshot_{timestamp}.png"

        try:
            await self.page.screenshot(path=str(path), full_page=full_page, clip=clip)

            self.screenshots_taken += 1
            self.logger.success(f"Screenshot saved: {path}", LogCategory.NAVIGATION)

            return path

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            raise ExtractorError(f"Screenshot failed: {e}") from e

    async def handle_dialog(self, accept: bool = True, prompt_text: str | None = None):
        """
        Set up dialog handler for alerts, confirms, prompts.

        Args:
            accept: Whether to accept or dismiss dialog
            prompt_text: Text to enter in prompt dialogs
        """
        if not self.page:
            return

        async def dialog_handler(dialog):
            dialog_type = dialog.type
            dialog_message = dialog.message

            self.logger.info(f"Browser dialog: {dialog_type} - {dialog_message}")

            if dialog_type == "prompt" and prompt_text:
                await dialog.accept(prompt_text)
            elif accept:
                await dialog.accept()
            else:
                await dialog.dismiss()

        self.page.on("dialog", dialog_handler)

    async def switch_to_popup(self) -> Optional["PlaywrightManager"]:
        """
        Switch to popup window and return new manager instance.

        Returns:
            New PlaywrightManager for popup or None
        """
        if not self.context:
            return None

        try:
            # Wait for new page (popup)
            async with self.context.expect_page() as page_info:
                popup_page = await page_info.value

            # Create new manager for popup
            popup_manager = PlaywrightManager(self.config, self.logger)
            popup_manager.playwright = self.playwright
            popup_manager.browser = self.browser
            popup_manager.context = self.context
            popup_manager.page = popup_page
            popup_manager.is_initialized = True

            await popup_manager._setup_page_handlers()

            self.logger.success("Switched to popup window", LogCategory.POPUP)

            return popup_manager

        except Exception as e:
            self.logger.error(f"Failed to switch to popup: {e}")
            return None

    async def close_page(self):
        """Close current page."""
        if self.page:
            await self.page.close()
            self.page = None

    async def wait_for_download(self, timeout: int | None = None) -> dict[str, Any] | None:
        """
        Wait for download to start and return download info.

        Args:
            timeout: Optional timeout override

        Returns:
            Download information or None
        """
        if not self.page:
            return None

        try:
            async with self.page.expect_download(
                timeout=timeout or self.config.timeout
            ) as download_info:
                download = await download_info.value

            # Get download details
            download_path = self.config.download_dir / download.suggested_filename
            await download.save_as(download_path)

            download_info = {
                "filename": download.suggested_filename,
                "path": download_path,
                "url": download.url,
                "size": download_path.stat().st_size if download_path.exists() else 0,
            }

            self.logger.success(
                f"Download completed: {download.suggested_filename}", LogCategory.EXTRACTION
            )

            return download_info

        except PlaywrightTimeoutError:
            self.logger.warning("Download timeout")
            return None

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None

    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies from current context."""
        if not self.context:
            return []

        return await self.context.cookies()

    async def set_cookies(self, cookies: list[dict[str, Any]]):
        """Set cookies in current context."""
        if not self.context:
            return

        await self.context.add_cookies(cookies)

    async def clear_cookies(self):
        """Clear all cookies from current context."""
        if not self.context:
            return

        await self.context.clear_cookies()

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        avg_nav_time = (
            sum(self.navigation_times) / len(self.navigation_times) if self.navigation_times else 0
        )
        avg_action_time = (
            sum(self.action_times) / len(self.action_times) if self.action_times else 0
        )

        return {
            "pages_opened": self.pages_opened,
            "screenshots_taken": self.screenshots_taken,
            "navigations": len(self.navigation_times),
            "actions": len(self.action_times),
            "avg_navigation_time": avg_nav_time,
            "avg_action_time": avg_action_time,
            "total_navigation_time": sum(self.navigation_times),
            "total_action_time": sum(self.action_times),
        }

    async def cleanup(self):
        """Clean up Playwright resources."""
        try:
            if self.page:
                await self.page.close()
                self.page = None

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.is_initialized = False

            # Log performance stats
            stats = self.get_performance_stats()
            self.logger.success(
                f"Playwright cleaned up - Pages: {stats['pages_opened']}, "
                f"Navigations: {stats['navigations']}, Screenshots: {stats['screenshots_taken']}",
                LogCategory.NAVIGATION,
            )

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# Utility functions for common operations
async def quick_screenshot(
    url: str, output_path: Path, config: PlaywrightConfig | None = None
) -> bool:
    """Take a quick screenshot of a URL."""
    config = config or PlaywrightConfig(headless=True)

    try:
        async with PlaywrightManager(config) as manager:
            await manager.navigate_to(url, wait_until="networkidle")
            await manager.take_screenshot(output_path, full_page=True)
            return True
    except Exception:
        return False


async def extract_page_data(
    url: str, selectors: dict[str, str], config: PlaywrightConfig | None = None
) -> dict[str, str | None]:
    """Extract data from page using CSS selectors."""
    config = config or PlaywrightConfig(headless=True)
    data = {}

    try:
        async with PlaywrightManager(config) as manager:
            await manager.navigate_to(url, wait_until="networkidle")

            for key, selector in selectors.items():
                data[key] = await manager.get_text(selector)

        return data
    except Exception as e:
        return {"error": str(e)}


@asynccontextmanager
async def browser_session(config: PlaywrightConfig | None = None):
    """Context manager for browser sessions."""
    manager = PlaywrightManager(config)
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.cleanup()

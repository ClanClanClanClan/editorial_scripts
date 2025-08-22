"""Async base adapter for journal platforms using Playwright."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ecc.core.domain.models import Manuscript


@dataclass
class JournalConfig:
    """Configuration for journal adapter."""
    
    journal_id: str
    name: str
    url: str
    platform: str
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    headless: bool = True
    download_dir: Optional[Path] = None
    timeout: int = 30000  # 30 seconds default
    viewport: Dict[str, int] = None
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}
        if self.download_dir is None:
            self.download_dir = Path.cwd() / "downloads" / self.journal_id


class AsyncJournalAdapter(ABC):
    """Async base adapter using Playwright for all journal platforms."""
    
    def __init__(self, config: JournalConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{config.journal_id}")
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Metrics for observability
        self.request_count = 0
        self.error_count = 0
        self.start_time = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def initialize(self):
        """Initialize browser and context."""
        self.logger.info(f"Initializing {self.config.platform} adapter for {self.config.journal_id}")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with optimized settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with download handling
        self.config.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.context = await self.browser.new_context(
            viewport=self.config.viewport,
            user_agent=self.config.user_agent,
            accept_downloads=True,
            ignore_https_errors=True,
            locale='en-US',
        )
        
        # Set default timeout
        self.context.set_default_timeout(self.config.timeout)
        
        # Create main page
        self.page = await self.context.new_page()
        
        # Enable request/response logging for debugging
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        
        self.logger.info("Browser initialized successfully")
        
    async def cleanup(self):
        """Clean up browser resources."""
        self.logger.info("Cleaning up browser resources")
        
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
        self.logger.info(f"Session stats: {self.request_count} requests, {self.error_count} errors")
        
    def _on_request(self, request):
        """Log requests for debugging."""
        self.request_count += 1
        self.logger.debug(f"Request: {request.method} {request.url}")
        
    def _on_response(self, response):
        """Log responses and track errors."""
        if response.status >= 400:
            self.error_count += 1
            self.logger.warning(f"Error response: {response.status} {response.url}")
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def navigate_with_retry(self, url: str, wait_until: str = "networkidle"):
        """Navigate to URL with automatic retry and error handling."""
        self.logger.info(f"Navigating to {url}")
        
        try:
            response = await self.page.goto(url, wait_until=wait_until)
            if response and response.status >= 400:
                raise Exception(f"Navigation failed with status {response.status}")
            await self.dismiss_popups()
            return response
            
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            await self.page.reload()
            await self.page.wait_for_load_state("networkidle")
            raise
            
    async def dismiss_popups(self):
        """Dismiss common popups (cookies, notifications, etc.)."""
        popup_selectors = [
            "button:has-text('Accept')",
            "button:has-text('I Agree')",
            "button:has-text('OK')",
            "button:has-text('Close')",
            "#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            ".cookie-accept",
            ".gdpr-accept",
        ]
        
        for selector in popup_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    self.logger.debug(f"Dismissed popup: {selector}")
                    await asyncio.sleep(0.5)
            except:
                continue
                
    async def wait_for_navigation(self, trigger_action, wait_until: str = "networkidle"):
        """Execute action and wait for navigation."""
        async with self.page.expect_navigation(wait_until=wait_until):
            await trigger_action()
            
    async def extract_text(self, selector: str) -> str:
        """Extract text from element with error handling."""
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_text()
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting text from {selector}: {e}")
            return ""
            
    async def extract_all_texts(self, selector: str) -> List[str]:
        """Extract text from all matching elements."""
        try:
            elements = await self.page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.inner_text()
                texts.append(text.strip())
            return texts
        except Exception as e:
            self.logger.error(f"Error extracting texts from {selector}: {e}")
            return []
            
    async def click_and_wait(self, selector: str, wait_after: float = 1.0):
        """Click element and wait for response."""
        try:
            element = await self.page.wait_for_selector(selector, state="visible")
            await element.click()
            await asyncio.sleep(wait_after)
            await self.page.wait_for_load_state("networkidle")
        except Exception as e:
            self.logger.error(f"Error clicking {selector}: {e}")
            raise
            
    async def fill_form_field(self, selector: str, value: str, clear_first: bool = True):
        """Fill form field with value."""
        try:
            element = await self.page.wait_for_selector(selector, state="visible")
            if clear_first:
                await element.fill("")
            await element.fill(value)
        except Exception as e:
            self.logger.error(f"Error filling {selector}: {e}")
            raise
            
    async def download_file(self, trigger_action, filename: Optional[str] = None) -> Path:
        """Handle file download with proper waiting."""
        try:
            async with self.page.expect_download() as download_info:
                await trigger_action()
            download = await download_info.value
            
            # Save to specified path
            if filename:
                save_path = self.config.download_dir / filename
            else:
                save_path = self.config.download_dir / download.suggested_filename
                
            await download.save_as(save_path)
            self.logger.info(f"Downloaded file to {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            raise
            
    async def handle_popup_window(self, trigger_action):
        """Handle popup windows and extract content."""
        try:
            # Wait for popup
            async with self.context.expect_page() as popup_info:
                await trigger_action()
            popup_page = await popup_info.value
            
            # Wait for popup to load
            await popup_page.wait_for_load_state("networkidle")
            
            # Extract content (override in subclass for specific extraction)
            content = await self.extract_popup_content(popup_page)
            
            # Close popup
            await popup_page.close()
            
            return content
            
        except Exception as e:
            self.logger.error(f"Popup handling failed: {e}")
            return None
            
    async def extract_popup_content(self, popup_page: Page) -> Dict[str, Any]:
        """Extract content from popup window (override in subclass)."""
        return {
            "url": popup_page.url,
            "title": await popup_page.title(),
            "text": await popup_page.content(),
        }
        
    async def take_screenshot(self, name: str = "screenshot"):
        """Take screenshot for debugging."""
        try:
            screenshot_path = self.config.download_dir / f"{name}_{self.config.journal_id}.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            self.logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the journal platform."""
        pass
        
    @abstractmethod
    async def fetch_manuscripts(self, categories: List[str]) -> List[Manuscript]:
        """Fetch manuscripts from specified categories."""
        pass
        
    @abstractmethod
    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        """Extract detailed information for a specific manuscript."""
        pass
        
    @abstractmethod
    async def download_manuscript_files(self, manuscript: Manuscript) -> List[Path]:
        """Download all files associated with a manuscript."""
        pass
"""
Base scraper class with common functionality for all journal scrapers
Provides async browser management, error handling, and rate limiting
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from abc import ABC, abstractmethod

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.core.domain.manuscript import Manuscript


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    success: bool
    manuscripts: List[Manuscript]
    total_count: int
    extraction_time: timedelta
    journal_code: str
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseScraper(ABC):
    """Base class for all journal scrapers"""
    
    def __init__(self, name: str, base_url: str, rate_limit_delay: float = 2.0):
        """Initialize base scraper"""
        self.name = name
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        
        # Setup logging
        self.logger = logging.getLogger(f"scrapers.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Browser settings
        self.browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Speed optimization
            '--disable-javascript-harmony-shipping',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--no-first-run',
            '--no-default-browser-check',
        ]
        
        # Performance and stealth settings
        self.browser_options = {
            'headless': True,
            'args': self.browser_args
        }
    
    async def create_browser(self) -> Browser:
        """Create browser instance with optimal settings"""
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(**self.browser_options)
        return browser
    
    async def setup_browser_context(self, browser: Browser) -> BrowserContext:
        """Setup browser context - override in subclasses for custom setup"""
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        return context
    
    @abstractmethod
    async def authenticate(self, page: Page) -> bool:
        """Authenticate with the journal system"""
        pass
    
    @abstractmethod
    async def extract_manuscripts(self, page: Page) -> List[Manuscript]:
        """Extract manuscripts from the journal"""
        pass
    
    @abstractmethod
    async def run_extraction(self) -> ScrapingResult:
        """Run the complete extraction process"""
        pass
    
    async def rate_limit(self):
        """Apply rate limiting between requests"""
        await asyncio.sleep(self.rate_limit_delay)
    
    def setup_logging(self, level: str = "INFO"):
        """Setup structured logging"""
        log_level = getattr(logging, level.upper())
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # Configure logger
        self.logger.handlers.clear()
        self.logger.addHandler(console_handler)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
    
    def log_performance_metrics(self, operation: str, start_time: datetime, count: int = 1):
        """Log performance metrics"""
        duration = datetime.now() - start_time
        rate = count / duration.total_seconds() if duration.total_seconds() > 0 else 0
        
        self.logger.info(
            f"📊 Performance: {operation} - "
            f"Duration: {duration.total_seconds():.2f}s, "
            f"Count: {count}, "
            f"Rate: {rate:.2f}/sec"
        )
    
    async def handle_errors(self, page: Page, operation: str):
        """Generic error handling with screenshots"""
        try:
            # Take screenshot for debugging
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f"error_{self.name}_{operation}_{timestamp}.png"
            await page.screenshot(path=screenshot_path)
            self.logger.error(f"Error screenshot saved: {screenshot_path}")
        except:
            pass
    
    def validate_extraction_result(self, manuscripts: List[Manuscript]) -> bool:
        """Validate extraction results"""
        if not manuscripts:
            self.logger.warning("No manuscripts extracted")
            return False
        
        # Check for basic data quality
        valid_manuscripts = 0
        for manuscript in manuscripts:
            if manuscript.id and manuscript.title:
                valid_manuscripts += 1
        
        quality_ratio = valid_manuscripts / len(manuscripts)
        if quality_ratio < 0.8:
            self.logger.warning(f"Low data quality: {quality_ratio:.1%} valid manuscripts")
            return False
        
        self.logger.info(f"Data quality check passed: {quality_ratio:.1%} valid manuscripts")
        return True
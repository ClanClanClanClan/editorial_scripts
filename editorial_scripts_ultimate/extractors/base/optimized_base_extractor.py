"""
Optimized Base Extractor - Ultimate Production Version
Fixes all critical issues identified in the comprehensive audit
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, TimeoutError as PlaywrightTimeout
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import optimized models
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.models.optimized_models import OptimizedManuscript, OptimizedReferee, OptimizedExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Connection configuration for robust networking"""
    timeout_ms: int = 120000  # 2 minutes (fixed from 60s)
    max_retries: int = 3
    retry_delay_base: float = 2.0  # Exponential backoff base
    browser_pool_size: int = 3
    concurrent_limit: int = 5


@dataclass
class ExtractionMetrics:
    """Metrics tracking for performance monitoring"""
    start_time: float
    manuscripts_found: int = 0
    referees_found: int = 0
    pdfs_downloaded: int = 0
    errors_encountered: int = 0
    connection_retries: int = 0
    
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'elapsed_time_seconds': self.elapsed_time(),
            'manuscripts_found': self.manuscripts_found,
            'referees_found': self.referees_found,
            'pdfs_downloaded': self.pdfs_downloaded,
            'errors_encountered': self.errors_encountered,
            'connection_retries': self.connection_retries,
            'manuscripts_per_minute': self.manuscripts_found / max(self.elapsed_time() / 60, 1),
            'referees_per_minute': self.referees_found / max(self.elapsed_time() / 60, 1)
        }


class BrowserPool:
    """Optimized browser pool for concurrent processing"""
    
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.available_browsers: asyncio.Queue = asyncio.Queue()
        self.active_browsers: List[Browser] = []
        self.playwright = None
    
    async def initialize(self):
        """Initialize the browser pool"""
        self.playwright = await async_playwright().start()
        
        for _ in range(self.pool_size):
            browser = await self._create_browser()
            await self.available_browsers.put(browser)
            self.active_browsers.append(browser)
    
    async def _create_browser(self) -> Browser:
        """Create a new browser with anti-detection settings"""
        browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-ipc-flooding-protection'
            ]
        )
        return browser
    
    async def get_browser(self) -> Browser:
        """Get a browser from the pool"""
        if self.available_browsers.empty():
            # If pool is empty, create a new temporary browser
            logger.warning("Browser pool exhausted, creating temporary browser")
            return await self._create_browser()
        
        return await self.available_browsers.get()
    
    async def return_browser(self, browser: Browser):
        """Return a browser to the pool"""
        if browser in self.active_browsers:
            await self.available_browsers.put(browser)
        else:
            # Temporary browser, close it
            try:
                await browser.close()
            except:
                pass
    
    async def close_all(self):
        """Close all browsers and cleanup"""
        for browser in self.active_browsers:
            try:
                await browser.close()
            except:
                pass
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass


class RobustConnectionManager:
    """Robust connection management with retry logic"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
        retry=retry_if_exception_type((PlaywrightTimeout, ConnectionError))
    )
    async def robust_navigate(self, page: Page, url: str) -> Page:
        """Navigate with robust error handling and retries"""
        try:
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=self.config.timeout_ms)
            
            # Verify page loaded correctly
            if await self._is_error_page(page):
                raise ConnectionError(f"Error page detected for {url}")
            
            return page
            
        except PlaywrightTimeout as e:
            logger.warning(f"Timeout navigating to {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise ConnectionError(f"Navigation failed: {e}")
    
    async def _is_error_page(self, page: Page) -> bool:
        """Check if current page is an error page"""
        try:
            # Check for common error patterns
            content = await page.content()
            error_patterns = [
                "404", "Not Found", "Page not found",
                "403", "Forbidden", "Access denied",
                "500", "Internal Server Error",
                "Connection refused", "Timeout"
            ]
            
            content_lower = content.lower()
            return any(pattern.lower() in content_lower for pattern in error_patterns)
        except:
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10)
    )
    async def wait_for_element(self, page: Page, selector: str, timeout: int = 30000) -> bool:
        """Wait for element with retry logic"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeout:
            logger.warning(f"Element not found: {selector}")
            return False


class OptimizedPDFDownloader:
    """Optimized PDF downloader that maintains authentication context"""
    
    def __init__(self, page: Page):
        self.page = page
        self.download_session = None
    
    async def download_pdf(self, url: str, filename: str, output_dir: Path) -> Optional[Path]:
        """Download PDF using authenticated browser session"""
        try:
            logger.info(f"Downloading PDF: {filename} from {url}")
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            
            # Navigate to PDF URL using authenticated session
            response = await self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            if not response or response.status != 200:
                logger.error(f"Failed to access PDF URL: {url} (status: {response.status if response else 'No response'})")
                return None
            
            # Get content
            content = await response.body()
            
            # Verify it's actually a PDF
            if not content or content[:4] != b'%PDF':
                logger.error(f"Downloaded content is not a valid PDF from {url}")
                return None
            
            # Verify minimum size (avoid empty/corrupted files)
            if len(content) < 1000:  # Less than 1KB is suspicious
                logger.warning(f"PDF content very small ({len(content)} bytes): {filename}")
                return None
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"✅ Successfully downloaded PDF: {filename} ({len(content):,} bytes)")
            return output_path
            
        except Exception as e:
            logger.error(f"PDF download failed for {filename}: {e}")
            return None


class OptimizedCacheManager:
    """Optimized caching with change detection"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session_cache = {}  # In-memory cache for current session
    
    def get_cache_key(self, journal: str, manuscript_id: str) -> str:
        """Generate cache key"""
        return f"{journal}_{manuscript_id}"
    
    async def get_cached_data(self, journal: str, manuscript_id: str) -> Optional[Dict[str, Any]]:
        """Get cached data if still fresh"""
        cache_key = self.get_cache_key(journal, manuscript_id)
        
        # Check session cache first
        if cache_key in self.session_cache:
            cached_data, timestamp = self.session_cache[cache_key]
            if time.time() - timestamp < 300:  # 5 minutes
                return cached_data
        
        # Check file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still fresh (1 hour)
                cache_time = cached_data.get('cache_timestamp', 0)
                if time.time() - cache_time < 3600:
                    self.session_cache[cache_key] = (cached_data, time.time())
                    return cached_data
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    async def cache_data(self, journal: str, manuscript_id: str, data: Dict[str, Any]):
        """Cache data to both session and file cache"""
        cache_key = self.get_cache_key(journal, manuscript_id)
        
        # Add timestamp
        data['cache_timestamp'] = time.time()
        
        # Session cache
        self.session_cache[cache_key] = (data, time.time())
        
        # File cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")


class OptimizedBaseExtractor(ABC):
    """
    Ultimate production-ready base extractor
    Fixes all critical issues and optimizes for performance
    """
    
    # Journal-specific settings (override in subclasses)
    journal_name: str = None
    base_url: str = None
    login_type: str = "orcid"  # "orcid", "email", "custom"
    requires_cloudflare_wait: bool = False
    cloudflare_wait_seconds: int = 60
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[ConnectionConfig] = None):
        """Initialize optimized extractor"""
        self.output_dir = output_dir or Path(f"output/{self.journal_name.lower()}")
        self.config = config or ConnectionConfig()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "pdfs").mkdir(exist_ok=True)
        
        # Initialize components
        self.browser_pool = BrowserPool(self.config.browser_pool_size)
        self.cache_manager = OptimizedCacheManager()
        self.connection_manager = RobustConnectionManager(self.config)
        
        # Performance tracking
        self.metrics = ExtractionMetrics(start_time=time.time())
        
        # Browser session
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        
        # Credentials
        self.username: Optional[str] = None
        self.password: Optional[str] = None
    
    async def extract(self, headless: bool = True, use_cache: bool = True) -> OptimizedExtractionResult:
        """
        Main extraction method - optimized and robust
        """
        logger.info(f"🚀 Starting optimized {self.journal_name} extraction")
        
        try:
            # Initialize browser pool
            await self.browser_pool.initialize()
            
            # Get browser from pool
            self.browser = await self.browser_pool.get_browser()
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await self.context.new_page()
            
            # Add anti-detection scripts
            await self._setup_anti_detection()
            
            # Get credentials
            await self._load_credentials()
            
            # Authenticate with retry logic
            if not await self._authenticate_with_retry():
                raise Exception("Authentication failed after retries")
            
            # Extract manuscripts with optimization
            manuscripts = await self._extract_all_manuscripts_optimized(use_cache)
            
            if not manuscripts:
                logger.warning("No manuscripts found - this may indicate a problem")
                self.metrics.errors_encountered += 1
            
            # Process each manuscript with concurrency control
            await self._process_manuscripts_concurrently(manuscripts)
            
            # Create optimized result
            result = OptimizedExtractionResult.create_from_manuscripts(self.journal_name, manuscripts)
            
            # Save results
            await self._save_results(result)
            
            # Log success metrics
            self._log_success_metrics(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            self.metrics.errors_encountered += 1
            raise
        finally:
            await self._cleanup()
    
    async def _setup_anti_detection(self):
        """Setup anti-detection measures"""
        await self.page.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5].map(i => ({
                    name: `Plugin ${i}`,
                    description: `Description ${i}`,
                    filename: `plugin${i}.dll`
                }))
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' 
                    ? Promise.resolve({ state: Notification.permission }) 
                    : originalQuery(parameters)
            );
            
            // Remove automation indicators
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
    
    async def _load_credentials(self):
        """Load credentials from environment or config"""
        import os
        
        if self.login_type == "orcid":
            self.username = os.getenv('ORCID_EMAIL')
            self.password = os.getenv('ORCID_PASSWORD')
        elif self.login_type == "email":
            self.username = os.getenv('SCHOLARONE_EMAIL')
            self.password = os.getenv('SCHOLARONE_PASSWORD')
        
        if not self.username or not self.password:
            raise Exception(f"Missing credentials for {self.login_type} authentication")
    
    async def _authenticate_with_retry(self) -> bool:
        """Authenticate with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🔐 Authentication attempt {attempt + 1}/{self.config.max_retries}")
                
                # Navigate to base URL
                await self.connection_manager.robust_navigate(self.page, self.base_url)
                
                # Handle CloudFlare if needed
                if self.requires_cloudflare_wait:
                    await self._handle_cloudflare_challenge()
                
                # Perform authentication
                if await self._perform_authentication():
                    logger.info("✅ Authentication successful")
                    return True
                
            except Exception as e:
                logger.warning(f"Authentication attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_base ** attempt)
                    continue
        
        return False
    
    async def _handle_cloudflare_challenge(self):
        """Handle CloudFlare challenge with optimized detection"""
        logger.info(f"⏳ Waiting for CloudFlare challenge ({self.cloudflare_wait_seconds}s)")
        
        # Wait for CloudFlare
        await asyncio.sleep(self.cloudflare_wait_seconds)
        
        # Wait for page to be ready
        await self.page.wait_for_load_state("networkidle", timeout=60000)
        
        # Check if we're still on CloudFlare page
        content = await self.page.content()
        if any(indicator in content for indicator in ["challenge", "Just a moment", "Checking your browser"]):
            logger.warning("Still on CloudFlare page after wait - may need longer wait")
            await asyncio.sleep(30)  # Additional wait
    
    async def _extract_all_manuscripts_optimized(self, use_cache: bool) -> List[OptimizedManuscript]:
        """Extract all manuscripts with caching and optimization"""
        logger.info("📋 Starting manuscript discovery")
        
        # Get manuscript list
        manuscript_urls = await self._discover_manuscripts()
        logger.info(f"Found {len(manuscript_urls)} manuscripts")
        
        manuscripts = []
        for i, (manuscript_id, url) in enumerate(manuscript_urls.items()):
            logger.info(f"📄 Processing manuscript {i+1}/{len(manuscript_urls)}: {manuscript_id}")
            
            try:
                # Check cache first
                cached_data = None
                if use_cache:
                    cached_data = await self.cache_manager.get_cached_data(self.journal_name, manuscript_id)
                
                if cached_data:
                    logger.info(f"Using cached data for {manuscript_id}")
                    manuscript = OptimizedManuscript(**cached_data)
                else:
                    # Fresh extraction
                    manuscript = await self._extract_single_manuscript_optimized(manuscript_id, url)
                    
                    # Cache the result
                    if manuscript:
                        await self.cache_manager.cache_data(self.journal_name, manuscript_id, manuscript.to_dict())
                
                if manuscript:
                    manuscripts.append(manuscript)
                    self.metrics.manuscripts_found += 1
                    self.metrics.referees_found += len(manuscript.referees)
                
            except Exception as e:
                logger.error(f"Failed to process manuscript {manuscript_id}: {e}")
                self.metrics.errors_encountered += 1
                continue
        
        return manuscripts
    
    async def _extract_single_manuscript_optimized(self, manuscript_id: str, url: str) -> Optional[OptimizedManuscript]:
        """Extract single manuscript with optimization and error handling"""
        try:
            # Navigate to manuscript page
            await self.connection_manager.robust_navigate(self.page, url)
            
            # Parse page content
            content = await self.page.content()
            soup = await self._parse_html_content(content)
            
            # CRITICAL FIX: Parse metadata FIRST, then create object
            metadata = await self._parse_manuscript_metadata_optimized(soup)
            
            # Create manuscript with parsed data
            manuscript = OptimizedManuscript(
                id=manuscript_id,
                journal=self.journal_name,
                title=metadata.get('title', f"Manuscript {manuscript_id}"),
                authors=metadata.get('authors', ["Authors not available"]),
                status=metadata.get('status', 'Unknown'),
                submission_date=metadata.get('submission_date'),
                corresponding_editor=metadata.get('corresponding_editor'),
                associate_editor=metadata.get('associate_editor')
            )
            
            # Extract referees
            referees = await self._extract_referees_optimized(soup, manuscript_id)
            for referee in referees:
                manuscript.add_referee(referee)
            
            # Extract PDF URLs
            pdf_urls = await self._extract_pdf_urls(soup)
            manuscript.pdf_urls = pdf_urls
            
            return manuscript
            
        except Exception as e:
            logger.error(f"Failed to extract manuscript {manuscript_id}: {e}")
            return None
    
    async def _process_manuscripts_concurrently(self, manuscripts: List[OptimizedManuscript]):
        """Process manuscripts with controlled concurrency"""
        semaphore = asyncio.Semaphore(self.config.concurrent_limit)
        
        async def process_single_manuscript(manuscript: OptimizedManuscript):
            async with semaphore:
                # Extract referee emails
                await self._extract_referee_emails_optimized(manuscript)
                
                # Download PDFs
                await self._download_pdfs_optimized(manuscript)
        
        # Process all manuscripts concurrently
        tasks = [process_single_manuscript(manuscript) for manuscript in manuscripts]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _extract_referee_emails_optimized(self, manuscript: OptimizedManuscript):
        """Extract referee emails with optimization"""
        pdf_downloader = OptimizedPDFDownloader(self.page)
        
        for referee in manuscript.referees:
            if referee.email:
                continue  # Skip if email already exists
            
            try:
                if referee.biblio_url:
                    # Navigate to referee bio page
                    await self.connection_manager.robust_navigate(self.page, referee.biblio_url)
                    
                    # Extract email
                    email = await self._extract_email_from_page()
                    if email:
                        referee.email = email
                        referee.email_verification = {'verified': True, 'source': 'bio_page'}
                        logger.info(f"✅ Found email for {referee.name}: {email}")
                
            except Exception as e:
                logger.warning(f"Failed to extract email for {referee.name}: {e}")
                continue
    
    async def _download_pdfs_optimized(self, manuscript: OptimizedManuscript):
        """Download PDFs with optimization and error handling"""
        pdf_downloader = OptimizedPDFDownloader(self.page)
        pdf_dir = self.output_dir / "pdfs"
        
        for pdf_type, pdf_url in manuscript.pdf_urls.items():
            try:
                filename = f"{manuscript.id}_{pdf_type}.pdf"
                downloaded_path = await pdf_downloader.download_pdf(pdf_url, filename, pdf_dir)
                
                if downloaded_path:
                    manuscript.pdf_paths[pdf_type] = str(downloaded_path)
                    self.metrics.pdfs_downloaded += 1
                
            except Exception as e:
                logger.error(f"Failed to download {pdf_type} PDF for {manuscript.id}: {e}")
                self.metrics.errors_encountered += 1
    
    async def _save_results(self, result: OptimizedExtractionResult):
        """Save results with error handling"""
        try:
            # Save main result
            output_file = self.output_dir / f"{self.journal_name.lower()}_{self.session_id}.json"
            result.save_to_file(output_file)
            
            # Save metrics
            metrics_file = self.output_dir / f"metrics_{self.session_id}.json"
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
            
            logger.info(f"✅ Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _log_success_metrics(self, result: OptimizedExtractionResult):
        """Log success metrics"""
        logger.info(f"""
🎯 Extraction Complete - {self.journal_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Results:
   Manuscripts: {result.total_manuscripts}
   Referees: {result.total_referees} ({result.referees_with_emails} with emails)
   PDFs: {result.pdfs_downloaded}
   
⏱️  Performance:
   Duration: {self.metrics.elapsed_time():.1f}s
   Quality Score: {result.overall_quality_score:.2f}
   Success Rate: {result._calculate_success_rate():.1%}
   
🔧 Technical:
   Errors: {self.metrics.errors_encountered}
   Retries: {self.metrics.connection_retries}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
    
    async def _cleanup(self):
        """Cleanup resources"""
        try:
            if self.browser:
                await self.browser_pool.return_browser(self.browser)
            
            await self.browser_pool.close_all()
            
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def _perform_authentication(self) -> bool:
        """Perform authentication - implement in subclass"""
        pass
    
    @abstractmethod
    async def _discover_manuscripts(self) -> Dict[str, str]:
        """Discover manuscript IDs and URLs - implement in subclass"""
        pass
    
    @abstractmethod
    async def _parse_manuscript_metadata_optimized(self, soup) -> Dict[str, Any]:
        """Parse manuscript metadata - implement in subclass"""
        pass
    
    @abstractmethod
    async def _extract_referees_optimized(self, soup, manuscript_id: str) -> List[OptimizedReferee]:
        """Extract referees - implement in subclass"""
        pass
    
    @abstractmethod
    async def _extract_pdf_urls(self, soup) -> Dict[str, str]:
        """Extract PDF URLs - implement in subclass"""
        pass
    
    @abstractmethod
    async def _extract_email_from_page(self) -> Optional[str]:
        """Extract email from current page - implement in subclass"""
        pass
    
    @abstractmethod
    async def _parse_html_content(self, content: str):
        """Parse HTML content - implement in subclass"""
        pass
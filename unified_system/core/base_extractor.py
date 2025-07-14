"""
Unified Base Extractor - Single source of truth for all journal extractions
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import aiohttp
import aiofiles
from playwright.async_api import async_playwright, Page, Browser
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Referee:
    """Referee information"""
    name: str
    email: str
    status: str = "Unknown"
    institution: Optional[str] = None
    report_submitted: Optional[bool] = False
    report_date: Optional[str] = None
    reminder_count: int = 0
    days_since_invited: Optional[int] = None


@dataclass
class Manuscript:
    """Manuscript information"""
    id: str
    title: str
    authors: List[str]
    status: str
    submission_date: Optional[str] = None
    journal: Optional[str] = None
    corresponding_editor: Optional[str] = None
    associate_editor: Optional[str] = None
    referees: List[Referee] = None
    pdf_urls: Dict[str, str] = None  # {"manuscript": url, "supplement": url}
    pdf_paths: Dict[str, str] = None  # {"manuscript": "/path/to/file.pdf"}
    referee_reports: Dict[str, str] = None  # {referee_email: report_text}
    
    def __post_init__(self):
        if self.referees is None:
            self.referees = []
        if self.pdf_urls is None:
            self.pdf_urls = {}
        if self.pdf_paths is None:
            self.pdf_paths = {}
        if self.referee_reports is None:
            self.referee_reports = {}


class BaseExtractor(ABC):
    """Base class for all journal extractors"""
    
    # Journal-specific settings (override in subclasses)
    journal_name: str = None
    base_url: str = None
    login_type: str = "orcid"  # "orcid", "email", "custom"
    requires_cloudflare_wait: bool = False
    cloudflare_wait_seconds: int = 60
    
    def __init__(self, cache_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """Initialize extractor with directories"""
        self.cache_dir = cache_dir or Path(f"cache/{self.journal_name.lower()}")
        self.output_dir = output_dir or Path(f"output/{self.journal_name.lower()}")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Session data
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.manuscripts: List[Manuscript] = []
        
        # Authentication
        self.username = None
        self.password = None
        
    async def extract(self, username: str, password: str, headless: bool = False) -> Dict[str, Any]:
        """Main extraction method - same interface for all journals"""
        logger.info(f"🚀 Starting {self.journal_name} extraction")
        
        self.username = username
        self.password = password
        
        try:
            # Initialize browser
            await self._init_browser(headless)
            
            # Authenticate
            if not await self._authenticate():
                raise Exception("Authentication failed")
            
            # Navigate to manuscripts
            if not await self._navigate_to_manuscripts():
                raise Exception("Could not navigate to manuscripts")
            
            # Extract manuscripts
            self.manuscripts = await self._extract_manuscripts()
            
            # For each manuscript, extract details
            for i, manuscript in enumerate(self.manuscripts):
                logger.info(f"📄 Processing manuscript {i+1}/{len(self.manuscripts)}: {manuscript.id}")
                
                # Extract referee information
                await self._extract_referee_details(manuscript)
                
                # Extract PDFs
                await self._extract_pdfs(manuscript)
                
                # Extract referee reports
                await self._extract_referee_reports(manuscript)
            
            # Save results
            results = self._prepare_results()
            await self._save_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _init_browser(self, headless: bool):
        """Initialize browser with anti-detection measures"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        self.page = await context.new_page()
        
        # Anti-detection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
    async def _authenticate(self) -> bool:
        """Authenticate with journal website"""
        logger.info(f"🔐 Authenticating with {self.journal_name}")
        
        # Navigate to base URL with longer timeout
        await self.page.goto(self.base_url, wait_until="networkidle", timeout=60000)
        
        # Handle CloudFlare if needed
        if self.requires_cloudflare_wait:
            await self._handle_cloudflare()
        
        # Perform authentication based on type
        if self.login_type == "orcid":
            # Check if subclass has overridden ORCID auth
            if hasattr(self, '_authenticate_orcid') and self._authenticate_orcid != BaseExtractor._authenticate_orcid:
                return await self._authenticate_orcid()
            else:
                return await self._authenticate_orcid()
        elif self.login_type == "email":
            return await self._authenticate_email()
        else:
            return await self._authenticate_custom()
    
    async def _handle_cloudflare(self):
        """Handle CloudFlare protection"""
        logger.info(f"⏳ Waiting {self.cloudflare_wait_seconds}s for CloudFlare...")
        
        # Check for CloudFlare challenge
        if "challenge" in await self.page.content():
            await asyncio.sleep(self.cloudflare_wait_seconds)
            
        # Also check for "Just a moment" text
        if "Just a moment" in await self.page.content():
            await asyncio.sleep(self.cloudflare_wait_seconds)
    
    async def _authenticate_orcid(self) -> bool:
        """ORCID authentication flow"""
        try:
            # Find and click ORCID login
            orcid_link = await self.page.wait_for_selector(
                "a[href*='orcid'], button:has-text('ORCID')", 
                timeout=10000
            )
            await orcid_link.click()
            
            # Wait for ORCID page
            await self.page.wait_for_load_state("networkidle")
            
            # Fill credentials
            await self.page.fill("input[name='userId'], input[type='email']", self.username)
            await self.page.fill("input[name='password'], input[type='password']", self.password)
            
            # Submit
            await self.page.click("button[type='submit']")
            
            # Wait for redirect back
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Verify we're logged in
            return self.journal_name.lower() in self.page.url.lower()
            
        except Exception as e:
            logger.error(f"ORCID authentication failed: {e}")
            return False
    
    async def _authenticate_email(self) -> bool:
        """Email/password authentication flow"""
        try:
            # Fill email
            await self.page.fill("input[type='email'], input[name='email']", self.username)
            
            # Fill password
            await self.page.fill("input[type='password']", self.password)
            
            # Submit
            await self.page.click("button[type='submit'], input[type='submit']")
            
            # Wait for login
            await self.page.wait_for_load_state("networkidle")
            
            return True
            
        except Exception as e:
            logger.error(f"Email authentication failed: {e}")
            return False
    
    @abstractmethod
    async def _authenticate_custom(self) -> bool:
        """Custom authentication - override in subclass if needed"""
        pass
    
    @abstractmethod
    async def _navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts list - override in subclass"""
        pass
    
    @abstractmethod
    async def _extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscript list - override in subclass"""
        pass
    
    @abstractmethod
    async def _extract_referee_details(self, manuscript: Manuscript):
        """Extract referee details for a manuscript - override in subclass"""
        pass
    
    @abstractmethod
    async def _extract_pdfs(self, manuscript: Manuscript):
        """Extract PDF URLs for a manuscript - override in subclass"""
        pass
    
    @abstractmethod
    async def _extract_referee_reports(self, manuscript: Manuscript):
        """Extract referee reports for a manuscript - override in subclass"""
        pass
    
    async def download_pdf(self, url: str, filename: str, use_browser: bool = True) -> Optional[Path]:
        """Download PDF to output directory with authentication support"""
        try:
            pdf_path = self.output_dir / "pdfs" / filename
            pdf_path.parent.mkdir(exist_ok=True)
            
            if use_browser and self.page:
                # Use browser for authenticated downloads
                logger.info(f"📥 Downloading PDF via browser: {filename}")
                
                # Create a new page to handle download
                download_page = await self.page.context.new_page()
                
                try:
                    # Set up download handling
                    async with download_page.expect_download() as download_info:
                        # Navigate to PDF URL
                        await download_page.goto(url)
                        
                    download = await download_info.value
                    
                    # Save to our path
                    await download.save_as(pdf_path)
                    
                    # Verify it's a PDF
                    async with aiofiles.open(pdf_path, 'rb') as f:
                        header = await f.read(4)
                        if header == b'%PDF':
                            logger.info(f"✅ Downloaded PDF: {pdf_path}")
                            return pdf_path
                        else:
                            logger.warning(f"Downloaded file is not a PDF: {filename}")
                            pdf_path.unlink()  # Remove invalid file
                            
                finally:
                    await download_page.close()
                    
            else:
                # Fallback to direct download
                logger.info(f"📥 Downloading PDF directly: {filename}")
                
                # Get cookies from browser if available
                cookies = {}
                if self.page:
                    browser_cookies = await self.page.context.cookies()
                    cookies = {c['name']: c['value'] for c in browser_cookies}
                
                async with aiohttp.ClientSession(cookies=cookies) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            
                            # Verify it's a PDF
                            if content[:4] == b'%PDF':
                                async with aiofiles.open(pdf_path, 'wb') as f:
                                    await f.write(content)
                                logger.info(f"✅ Downloaded PDF: {pdf_path}")
                                return pdf_path
                            else:
                                logger.warning(f"Not a PDF: {url}")
                        else:
                            logger.error(f"HTTP {response.status} downloading {url}")
                            
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
        
        return None
    
    def _prepare_results(self) -> Dict[str, Any]:
        """Prepare extraction results"""
        return {
            "journal": self.journal_name,
            "session_id": self.session_id,
            "extraction_time": datetime.now().isoformat(),
            "total_manuscripts": len(self.manuscripts),
            "manuscripts": [asdict(ms) for ms in self.manuscripts],
            "statistics": {
                "total_referees": sum(len(ms.referees) for ms in self.manuscripts),
                "manuscripts_with_reports": sum(1 for ms in self.manuscripts if ms.referee_reports),
                "pdfs_found": sum(len(ms.pdf_urls) for ms in self.manuscripts),
                "pdfs_downloaded": sum(len(ms.pdf_paths) for ms in self.manuscripts)
            }
        }
    
    async def _save_results(self, results: Dict[str, Any]):
        """Save results to output directory"""
        output_file = self.output_dir / f"{self.journal_name.lower()}_{self.session_id}.json"
        
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(json.dumps(results, indent=2))
        
        logger.info(f"💾 Results saved: {output_file}")
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
    
    def get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        return self.cache_dir / f"{key}.json"
    
    async def load_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from cache"""
        cache_path = self.get_cache_path(key)
        if cache_path.exists():
            async with aiofiles.open(cache_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        return None
    
    async def save_to_cache(self, key: str, data: Dict[str, Any]):
        """Save data to cache"""
        cache_path = self.get_cache_path(key)
        async with aiofiles.open(cache_path, 'w') as f:
            await f.write(json.dumps(data, indent=2))
"""
Base Extractor - Final Implementation
Clean, simple, and proven to work
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser

from core.models import Manuscript, Referee, ExtractionResult
from core.credentials import CredentialManager

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all journal extractors - simplified and working"""
    
    # Journal-specific settings (override in subclasses)
    journal_name: str = None
    base_url: str = None
    login_type: str = "orcid"  # "orcid", "email", "custom"
    requires_cloudflare_wait: bool = False
    cloudflare_wait_seconds: int = 60
    default_timeout: int = 120000  # 2 minutes (FIXED from 60s)
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize extractor"""
        self.output_dir = output_dir or Path(f"output/{self.journal_name.lower()}")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "pdfs").mkdir(exist_ok=True)
        
        # Browser session
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Credentials
        self.credential_manager = CredentialManager()
        self.username = None
        self.password = None
    
    async def extract(self, headless: bool = True) -> ExtractionResult:
        """Main extraction method - proven workflow"""
        logger.info(f"🚀 Starting {self.journal_name} extraction")
        
        try:
            # Get credentials
            creds = self.credential_manager.get_credentials(self.journal_name)
            if not creds:
                raise Exception(f"No credentials found for {self.journal_name}")
            
            self.username = creds['username']
            self.password = creds['password']
            
            # Initialize browser with anti-detection
            await self._init_browser(headless)
            
            # Authenticate
            if not await self._authenticate():
                raise Exception("Authentication failed")
            
            # Get ALL manuscripts (not just first page)
            manuscripts = await self._get_all_manuscripts()
            logger.info(f"📋 Found {len(manuscripts)} manuscripts")
            
            # Process each manuscript
            for i, manuscript in enumerate(manuscripts):
                logger.info(f"📄 Processing manuscript {i+1}/{len(manuscripts)}: {manuscript.id}")
                
                # Extract full details (with proper parsing)
                await self._extract_manuscript_details(manuscript)
                
                # Get referee emails (click bio links)
                await self._extract_referee_emails(manuscript)
                
                # Download PDFs (simple method)
                await self._download_pdfs(manuscript)
            
            # Create result
            result = ExtractionResult.create_from_manuscripts(self.journal_name, manuscripts)
            
            # Save results
            output_file = self.output_dir / f"{self.journal_name.lower()}_{self.session_id}.json"
            result.save_to_file(str(output_file))
            
            logger.info(f"✅ Extraction complete: {result.total_manuscripts} manuscripts, {result.total_referees} referees")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _init_browser(self, headless: bool):
        """Initialize browser with proper anti-detection"""
        self.playwright = await async_playwright().start()
        
        # Launch with anti-detection arguments
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-accelerated-2d-canvas',
                '--no-zygote',
                '--single-process'
            ]
        )
        
        # Create context with anti-detection
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
            }
        )
        
        self.page = await context.new_page()
        
        # Add anti-detection scripts
        await self.page.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Override plugins to look normal
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
        """)
    
    async def _authenticate(self) -> bool:
        """Authenticate with journal website"""
        logger.info(f"🔐 Authenticating with {self.journal_name}")
        
        try:
            # Navigate to base URL with proper timeout
            await self.page.goto(self.base_url, wait_until="networkidle", timeout=self.default_timeout)
            
            # Handle CloudFlare if needed
            if self.requires_cloudflare_wait:
                await self._handle_cloudflare()
            
            # Perform authentication
            if self.login_type == "orcid":
                return await self._authenticate_orcid()
            elif self.login_type == "email":
                return await self._authenticate_email()
            else:
                return await self._authenticate_custom()
        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _handle_cloudflare(self):
        """Handle CloudFlare protection"""
        content = await self.page.content()
        
        if any(indicator in content for indicator in ["challenge", "Just a moment", "Checking your browser"]):
            logger.info(f"⏳ CloudFlare detected, waiting {self.cloudflare_wait_seconds}s...")
            await asyncio.sleep(self.cloudflare_wait_seconds)
            await self.page.wait_for_load_state("networkidle", timeout=self.default_timeout)
    
    async def _download_pdf_simple(self, url: str, filename: str) -> Optional[Path]:
        """Simple PDF download using authenticated browser"""
        try:
            pdf_path = self.output_dir / "pdfs" / filename
            
            logger.info(f"📥 Downloading PDF: {filename}")
            
            # Navigate to PDF URL
            response = await self.page.goto(url, wait_until="networkidle", timeout=self.default_timeout)
            
            if response and response.status == 200:
                # Get the content
                content = await response.body()
                
                # Verify it's a PDF
                if content[:4] == b'%PDF':
                    # Save to file
                    pdf_path.write_bytes(content)
                    
                    if pdf_path.stat().st_size > 1000:  # At least 1KB
                        logger.info(f"✅ Downloaded: {filename} ({len(content):,} bytes)")
                        return pdf_path
                    else:
                        logger.warning(f"PDF too small: {filename}")
                        pdf_path.unlink()
                else:
                    logger.warning(f"Not a PDF: {url}")
            else:
                logger.error(f"HTTP {response.status if response else 'No response'}: {url}")
                
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
        
        return None
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def _authenticate_orcid(self) -> bool:
        """ORCID authentication - implement in subclass"""
        pass
    
    @abstractmethod
    async def _authenticate_email(self) -> bool:
        """Email authentication - implement in subclass"""
        pass
    
    async def _authenticate_custom(self) -> bool:
        """Custom authentication - override if needed"""
        return False
    
    @abstractmethod
    async def _get_all_manuscripts(self) -> List[Manuscript]:
        """Get list of all manuscripts - implement in subclass"""
        pass
    
    @abstractmethod
    async def _extract_manuscript_details(self, manuscript: Manuscript):
        """Extract full details for a manuscript - implement in subclass"""
        pass
    
    @abstractmethod
    async def _extract_referee_emails(self, manuscript: Manuscript):
        """Extract referee emails by clicking bio links - implement in subclass"""
        pass
    
    @abstractmethod
    async def _download_pdfs(self, manuscript: Manuscript):
        """Download PDFs for a manuscript - implement in subclass"""
        pass
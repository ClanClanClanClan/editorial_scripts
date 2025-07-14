"""
Base Extractor for Production Editorial Scripts
Clean, optimized implementation based on working components
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser
import json

from .models import Manuscript, Referee, ExtractionResult
from .credentials import CredentialManager

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all journal extractors - clean and simple"""
    
    # Journal-specific settings (override in subclasses)
    journal_name: str = None
    base_url: str = None
    login_type: str = "orcid"  # "orcid", "email", "custom"
    requires_cloudflare_wait: bool = False
    cloudflare_wait_seconds: int = 60
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize extractor"""
        self.output_dir = output_dir or Path(f"output/{self.journal_name.lower()}")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "pdfs").mkdir(exist_ok=True)
        
        # Browser session
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Credentials
        self.credential_manager = CredentialManager()
        self.username = None
        self.password = None
    
    async def extract(self, headless: bool = False) -> ExtractionResult:
        """Main extraction method - same interface for all journals"""
        logger.info(f"🚀 Starting {self.journal_name} extraction")
        
        try:
            # Get credentials
            creds = self.credential_manager.get_credentials(self.journal_name)
            if not creds:
                raise Exception(f"No credentials found for {self.journal_name}")
            
            self.username = creds['username']
            self.password = creds['password']
            
            # Initialize browser
            await self._init_browser(headless)
            
            # Authenticate
            if not await self._authenticate():
                raise Exception("Authentication failed")
            
            # Extract manuscripts
            manuscripts = await self._extract_manuscripts()
            
            # Process each manuscript
            for i, manuscript in enumerate(manuscripts):
                logger.info(f"📄 Processing manuscript {i+1}/{len(manuscripts)}: {manuscript.id}")
                
                # Extract details
                await self._extract_manuscript_details(manuscript)
                
                # Download PDFs
                await self._download_pdfs(manuscript)
            
            # Create result
            result = ExtractionResult.create_from_manuscripts(self.journal_name, manuscripts)
            
            # Save results
            output_file = self.output_dir / f"{self.journal_name.lower()}_{self.session_id}.json"
            result.save_to_file(str(output_file))
            
            logger.info(f"✅ Extraction complete: {result.total_manuscripts} manuscripts, {result.total_referees} referees")
            logger.info(f"💾 Results saved: {output_file}")
            
            return result
            
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
        
        try:
            # Navigate to base URL with increased timeout
            await self.page.goto(self.base_url, wait_until="networkidle", timeout=120000)
            
            # Handle CloudFlare if needed
            if self.requires_cloudflare_wait:
                await self._handle_cloudflare()
            
            # Perform authentication based on type
            if self.login_type == "orcid":
                return await self._authenticate_orcid()
            elif self.login_type == "email":
                return await self._authenticate_email()
            else:
                return await self._authenticate_custom()
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def _handle_cloudflare(self):
        """Handle CloudFlare protection"""
        logger.info(f"⏳ Waiting {self.cloudflare_wait_seconds}s for CloudFlare...")
        
        # Check for CloudFlare indicators
        content = await self.page.content()
        if any(indicator in content for indicator in ["challenge", "Just a moment", "Checking your browser"]):
            await asyncio.sleep(self.cloudflare_wait_seconds)
            await self.page.wait_for_load_state("networkidle")
    
    async def _authenticate_orcid(self) -> bool:
        """ORCID authentication flow"""
        try:
            # Find and click ORCID login
            orcid_selectors = [
                "a[href*='orcid']",
                "button:has-text('ORCID')",
                "a:has-text('ORCID')",
                ".orcid-login",
                "#orcid-login"
            ]
            
            orcid_link = None
            for selector in orcid_selectors:
                try:
                    orcid_link = await self.page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue
            
            if not orcid_link:
                logger.error("❌ ORCID login button not found")
                return False
            
            await orcid_link.click()
            logger.info("✅ Clicked ORCID login")
            
            # Wait for ORCID page
            await self.page.wait_for_load_state("networkidle")
            
            # Fill credentials
            await self.page.fill("input[name='userId'], input[type='email']", self.username)
            await self.page.fill("input[name='password'], input[type='password']", self.password)
            
            # Submit
            await self.page.click("button[type='submit']")
            logger.info("✅ Submitted ORCID credentials")
            
            # Wait for redirect back
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)  # Additional wait for full page load
            
            # Verify we're logged in
            success = self.journal_name.lower() in self.page.url.lower()
            if success:
                logger.info("✅ ORCID authentication successful")
            else:
                logger.error("❌ ORCID authentication failed - not redirected to journal")
            
            return success
            
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
            
            logger.info("✅ Email authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Email authentication failed: {e}")
            return False
    
    async def _authenticate_custom(self) -> bool:
        """Custom authentication - override in subclass if needed"""
        logger.warning("Custom authentication not implemented")
        return False
    
    async def _download_pdf(self, url: str, filename: str) -> Optional[Path]:
        """Simple PDF download using authenticated browser session"""
        try:
            pdf_path = self.output_dir / "pdfs" / filename
            pdf_path.parent.mkdir(exist_ok=True)
            
            logger.info(f"📥 Downloading PDF: {filename}")
            
            # Navigate to PDF URL
            response = await self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            if response.status == 200:
                # Get the content
                content = await response.body()
                
                # Verify it's a PDF
                if content[:4] == b'%PDF':
                    # Save to file
                    with open(pdf_path, 'wb') as f:
                        f.write(content)
                    
                    # Verify size
                    if pdf_path.stat().st_size > 1000:  # At least 1KB
                        logger.info(f"✅ Downloaded: {filename} ({len(content)} bytes)")
                        return pdf_path
                    else:
                        logger.warning(f"PDF too small: {filename}")
                        pdf_path.unlink()
                else:
                    logger.warning(f"Not a PDF: {url}")
            else:
                logger.error(f"HTTP {response.status}: {url}")
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
        
        return None
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def _extract_manuscripts(self) -> List[Manuscript]:
        """Extract list of manuscripts - override in subclass"""
        pass
    
    @abstractmethod
    async def _extract_manuscript_details(self, manuscript: Manuscript):
        """Extract detailed information for a manuscript - override in subclass"""
        pass
    
    @abstractmethod
    async def _download_pdfs(self, manuscript: Manuscript):
        """Download PDFs for a manuscript - override in subclass"""
        pass
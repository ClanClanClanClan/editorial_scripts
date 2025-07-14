"""
Mathematical Finance (MF) Journal Scraper - Fixed Version
Async implementation with document download support
"""

import asyncio
import logging
import re
import os
import aiohttp
import aiofiles
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from playwright.async_api import Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from src.infrastructure.config import settings
from src.core.domain.manuscript import Manuscript, ManuscriptStatus, RefereeInfo, RefereeStatus
from src.infrastructure.scrapers.base_scraper import BaseScraper, ScrapingResult
from src.infrastructure.storage.document_storage import DocumentStorage


class MFScraperFixed(BaseScraper):
    """Mathematical Finance journal scraper for ScholarOne platform"""
    
    def __init__(self):
        """Initialize MF scraper"""
        super().__init__(
            name="MF_Scraper",
            base_url="https://mc.manuscriptcentral.com/mafi",
            rate_limit_delay=2.0
        )
        
        self.journal_code = "MF"
        self.document_storage = DocumentStorage()
        
        self.authenticated = False
        self.session_cookies = None
        self.manuscripts: List[Manuscript] = []
        
    async def setup_browser_context(self, browser: Browser) -> BrowserContext:
        """Setup browser context with stealth measures"""
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            bypass_csp=True
        )
        
        # Add basic stealth
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return context
    
    async def authenticate(self, page: Page) -> bool:
        """Authenticate with ScholarOne platform"""
        try:
            self.logger.info("🔐 Starting MF authentication...")
            
            # Navigate to login page
            await page.goto(self.base_url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # Accept cookies if present
            try:
                await page.click("#onetrust-accept-btn-handler", timeout=3000)
                self.logger.info("🍪 Accepted cookies")
            except:
                self.logger.debug("No cookie banner")
            
            # Get credentials
            username = os.environ.get('MF_USER') or settings.mf_username
            password = os.environ.get('MF_PASS') or settings.mf_password
            
            if not username or not password:
                # Try ScholarOne credentials as fallback
                username = os.environ.get('SCHOLARONE_USER') or settings.scholarone_username
                password = os.environ.get('SCHOLARONE_PASS') or settings.scholarone_password
            
            if not username or not password:
                raise ValueError("MF/ScholarOne credentials not configured")
            
            # Fill login form
            await page.fill("#USERID", username)
            await page.fill("#PASSWORD", password)
            
            # Check "Remember Me" if available
            try:
                remember_checkbox = page.locator("#REMEMBER_ME")
                if await remember_checkbox.is_visible():
                    await remember_checkbox.check()
            except:
                pass
            
            # Submit login
            await page.click("#logInButton")
            await page.wait_for_timeout(5000)
            
            # Handle 2FA if required
            if await self._check_2fa_required(page):
                self.logger.warning("⚠️ 2FA required - manual intervention needed")
                # In production, implement email fetching for 2FA code
                return False
            
            # Verify authentication
            current_url = page.url
            if "Dashboard" in current_url or "Author" in current_url:
                self.authenticated = True
                self.session_cookies = await page.context.cookies()
                self.logger.info("✅ MF authentication successful")
                return True
            else:
                self.logger.error("❌ MF authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def _check_2fa_required(self, page: Page) -> bool:
        """Check if 2FA is required"""
        try:
            # Check for various 2FA selectors
            selectors = ["#TOKEN_VALUE", "#validationCode", "#verificationCode"]
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    return True
                except:
                    continue
            return False
        except:
            return False
    
    async def extract_manuscripts(self, page: Page) -> List[Manuscript]:
        """Extract manuscripts from MF dashboard"""
        try:
            self.logger.info("📄 Starting manuscript extraction...")
            
            # Navigate to author dashboard
            dashboard_url = f"{self.base_url}/Author/AuthorDashboard"
            await page.goto(dashboard_url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # Wait for manuscript table
            await page.wait_for_selector("table.BorderTable", timeout=10000)
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            manuscripts = []
            
            # Find manuscript tables
            tables = soup.find_all('table', class_='BorderTable')
            
            for table in tables:
                # Check if this is a manuscript table
                headers = table.find_all('th')
                if not any('Manuscript' in str(h) for h in headers):
                    continue
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    try:
                        ms_data = await self._parse_manuscript_row(row)
                        if ms_data:
                            # Extract additional details
                            await self._extract_manuscript_details(page, ms_data)
                            
                            # Download documents
                            await self._download_manuscript_documents(ms_data)
                            
                            # Create manuscript object
                            manuscript = self._create_manuscript_object(ms_data)
                            manuscripts.append(manuscript)
                            
                            # Rate limiting
                            await page.wait_for_timeout(2000)
                            
                    except Exception as e:
                        self.logger.error(f"Error processing manuscript: {e}")
                        continue
            
            self.manuscripts = manuscripts
            self.logger.info(f"✅ Extracted {len(manuscripts)} manuscripts")
            
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"❌ Extraction failed: {e}")
            raise
    
    async def _parse_manuscript_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a manuscript row from the table"""
        cells = row.find_all('td')
        if len(cells) < 4:
            return None
        
        try:
            # Extract manuscript info
            ms_id = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            status = cells[2].get_text(strip=True)
            date = cells[3].get_text(strip=True)
            
            # Get manuscript link
            ms_link = cells[0].find('a')
            href = ms_link.get('href', '') if ms_link else ''
            
            return {
                'id': ms_id,
                'title': title,
                'status_text': status,
                'submission_date': date,
                'url': href,
                'journal_code': self.journal_code,
                'documents': {},
                'referees': []
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing row: {e}")
            return None
    
    async def _extract_manuscript_details(self, page: Page, ms_data: Dict[str, Any]):
        """Extract detailed manuscript information"""
        try:
            if not ms_data.get('url'):
                return
            
            # Navigate to manuscript details
            detail_url = f"{self.base_url}{ms_data['url']}"
            await page.goto(detail_url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract documents
            doc_links = soup.find_all('a', href=lambda x: x and ('download' in str(x).lower() or 'view' in str(x).lower()))
            
            for link in doc_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Make URL absolute
                if href.startswith('/'):
                    href = f"{self.base_url}{href}"
                elif not href.startswith('http'):
                    href = f"{self.base_url}/{href}"
                
                # Categorize document
                if 'manuscript' in text or 'pdf' in text:
                    ms_data['documents']['manuscript_pdf'] = href
                elif 'cover' in text:
                    ms_data['documents']['cover_letter'] = href
                elif 'review' in text or 'report' in text:
                    if 'referee_reports' not in ms_data['documents']:
                        ms_data['documents']['referee_reports'] = []
                    ms_data['documents']['referee_reports'].append(href)
            
            # Extract referees
            referee_sections = soup.find_all('td', class_='detailsheaderbg')
            for section in referee_sections:
                if 'reviewer' in section.get_text().lower():
                    table = section.find_parent('table')
                    if table:
                        referee_rows = table.find_all('tr')[1:]
                        for ref_row in referee_rows:
                            ref_data = self._parse_referee_row(ref_row)
                            if ref_data:
                                ms_data['referees'].append(ref_data)
            
            # Navigate back
            await page.go_back()
            
        except Exception as e:
            self.logger.error(f"Error extracting details: {e}")
    
    def _parse_referee_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse referee information from row"""
        cells = row.find_all('td')
        if len(cells) < 3:
            return None
        
        try:
            name = cells[0].get_text(strip=True)
            email = cells[1].get_text(strip=True) if len(cells) > 1 else ''
            status = cells[2].get_text(strip=True) if len(cells) > 2 else ''
            
            # Normalize name
            name = self._normalize_name(name)
            
            return {
                'name': name,
                'email': email,
                'status': status
            }
        except:
            return None
    
    def _normalize_name(self, name: str) -> str:
        """Convert 'Last, First' to 'First Last' format"""
        name = name.replace('(contact)', '').strip()
        if ',' in name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                return f"{parts[1].strip()} {parts[0].strip()}"
        return name
    
    async def _download_manuscript_documents(self, ms_data: Dict[str, Any]):
        """Download manuscript documents"""
        manuscript_id = ms_data['id']
        
        async with aiohttp.ClientSession() as session:
            # Add cookies
            if self.session_cookies:
                for cookie in self.session_cookies:
                    session.cookie_jar.update_cookies({cookie['name']: cookie['value']})
            
            # Download manuscript PDF
            if ms_data['documents'].get('manuscript_pdf'):
                try:
                    pdf_path = await self._download_document(
                        session,
                        ms_data['documents']['manuscript_pdf'],
                        manuscript_id,
                        'manuscript.pdf'
                    )
                    ms_data['documents']['manuscript_pdf_local'] = pdf_path
                    self.logger.info(f"✅ Downloaded PDF for {manuscript_id}")
                except Exception as e:
                    self.logger.error(f"Failed to download PDF: {e}")
            
            # Download cover letter
            if ms_data['documents'].get('cover_letter'):
                try:
                    cover_path = await self._download_document(
                        session,
                        ms_data['documents']['cover_letter'],
                        manuscript_id,
                        'cover_letter.pdf'
                    )
                    ms_data['documents']['cover_letter_local'] = cover_path
                    self.logger.info(f"✅ Downloaded cover letter for {manuscript_id}")
                except Exception as e:
                    self.logger.error(f"Failed to download cover letter: {e}")
    
    async def _download_document(self, session: aiohttp.ClientSession, url: str, manuscript_id: str, filename: str) -> str:
        """Download a document"""
        # Create directory
        base_dir = Path.home() / '.editorial_scripts' / 'documents' / 'manuscripts' / self.journal_code / manuscript_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = base_dir / filename
        
        # Download
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            content = await response.read()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        
        # Store in document storage
        self.document_storage.store_document(
            content,
            self.journal_code,
            manuscript_id,
            filename.replace('.pdf', ''),
            filename
        )
        
        return str(file_path)
    
    def _create_manuscript_object(self, ms_data: Dict[str, Any]) -> Manuscript:
        """Create Manuscript domain object"""
        # Parse referees
        referees = []
        for ref in ms_data.get('referees', []):
            referees.append(RefereeInfo(
                name=ref.get('name', ''),
                email=ref.get('email', ''),
                status=self._map_referee_status(ref.get('status', ''))
            ))
        
        # Create manuscript
        manuscript = Manuscript(
            id=ms_data['id'],
            title=ms_data['title'],
            journal_code=self.journal_code,
            status=self._map_manuscript_status(ms_data.get('status_text', '')),
            submission_date=self._parse_date(ms_data.get('submission_date')),
            corresponding_editor='',
            associate_editor='',
            referees=referees,
            metadata={
                'documents': ms_data.get('documents', {}),
                'scraped_at': datetime.now().isoformat(),
                'platform': 'ScholarOne'
            }
        )
        
        return manuscript
    
    def _map_manuscript_status(self, status_text: str) -> ManuscriptStatus:
        """Map status text to domain enum"""
        status = status_text.lower()
        
        if 'accept' in status:
            return ManuscriptStatus.ACCEPTED
        elif 'reject' in status:
            return ManuscriptStatus.REJECTED
        elif 'revisi' in status:
            return ManuscriptStatus.AWAITING_REVISION
        elif 'review' in status:
            return ManuscriptStatus.UNDER_REVIEW
        else:
            return ManuscriptStatus.SUBMITTED
    
    def _map_referee_status(self, status_text: str) -> RefereeStatus:
        """Map referee status"""
        status = status_text.lower()
        
        if 'accept' in status or 'agreed' in status:
            return RefereeStatus.ACCEPTED
        elif 'declin' in status:
            return RefereeStatus.DECLINED
        elif 'complet' in status:
            return RefereeStatus.COMPLETED
        else:
            return RefereeStatus.INVITED
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string"""
        if not date_str:
            return None
        
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None
    
    async def run_extraction(self) -> ScrapingResult:
        """Run complete extraction"""
        start_time = datetime.now()
        
        try:
            # Create browser
            browser = await self.create_browser()
            context = await self.setup_browser_context(browser)
            page = await context.new_page()
            
            # Authenticate
            if not await self.authenticate(page):
                raise Exception("Authentication failed")
            
            # Extract manuscripts
            manuscripts = await self.extract_manuscripts(page)
            
            # Store metadata
            await self._store_manuscript_metadata(manuscripts)
            
            # Cleanup
            await context.close()
            await browser.close()
            
            # Create result
            result = ScrapingResult(
                success=True,
                manuscripts=manuscripts,
                total_count=len(manuscripts),
                extraction_time=datetime.now() - start_time,
                journal_code=self.journal_code,
                metadata={
                    'scraper_version': '2.0',
                    'platform': 'ScholarOne',
                    'documents_downloaded': self._count_downloaded_documents(manuscripts)
                }
            )
            
            self.logger.info(f"🎉 Extraction complete: {len(manuscripts)} manuscripts")
            return result
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return ScrapingResult(
                success=False,
                manuscripts=[],
                total_count=0,
                extraction_time=datetime.now() - start_time,
                journal_code=self.journal_code,
                error_message=str(e)
            )
    
    async def _store_manuscript_metadata(self, manuscripts: List[Manuscript]):
        """Store manuscript metadata"""
        metadata_dir = Path.home() / '.editorial_scripts' / 'documents' / 'metadata' / self.journal_code
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Store individual metadata
        for ms in manuscripts:
            metadata_file = metadata_dir / f"{ms.id}_metadata.json"
            metadata = {
                'id': ms.id,
                'title': ms.title,
                'journal_code': ms.journal_code,
                'status': ms.status.value if hasattr(ms.status, 'value') else str(ms.status),
                'submission_date': ms.submission_date.isoformat() if ms.submission_date else None,
                'referees': [
                    {
                        'name': ref.name,
                        'email': ref.email,
                        'status': ref.status.value if hasattr(ref.status, 'value') else str(ref.status)
                    }
                    for ref in ms.referees
                ],
                'metadata': ms.metadata,
                'scraped_at': datetime.now().isoformat()
            }
            
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
        
        self.logger.info(f"✅ Metadata stored in {metadata_dir}")
    
    def _count_downloaded_documents(self, manuscripts: List[Manuscript]) -> Dict[str, int]:
        """Count downloaded documents"""
        counts = {
            'manuscripts': 0,
            'cover_letters': 0,
            'referee_reports': 0
        }
        
        for ms in manuscripts:
            docs = ms.metadata.get('documents', {})
            if docs.get('manuscript_pdf_local'):
                counts['manuscripts'] += 1
            if docs.get('cover_letter_local'):
                counts['cover_letters'] += 1
            if docs.get('referee_reports_local'):
                counts['referee_reports'] += len(docs['referee_reports_local'])
        
        return counts


# Import json
import json
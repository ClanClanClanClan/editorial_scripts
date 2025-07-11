"""
SIAM Journal on Financial Mathematics (SIFIN) Scraper
Async implementation using Playwright and clean architecture
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from ...core.domain.models import (
    Manuscript, Review, Referee, Author, 
    ManuscriptStatus, RefereeStatus, ReviewQuality
)
from ...core.ports.journal_extractor import JournalExtractor
from ...core.ports.browser_pool import BrowserPool
from ..config import get_settings


class SIFINScraper(JournalExtractor):
    """SIFIN journal scraper for SIAM ORCID platform"""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "SIFIN"
        self.base_url = "http://sifin.siam.org"
        self.folder_id = "1802"  # SIFIN folder ID
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from SIFIN journal"""
        async with self.browser_pool.get_browser() as browser:
            page = await browser.new_page()
            
            try:
                await self._login(page)
                manuscripts = await self._scrape_manuscripts(page)
                
                # Extract referee information for each manuscript
                for manuscript in manuscripts:
                    await self._extract_manuscript_referees(page, manuscript)
                
                return manuscripts
                
            except Exception as e:
                self.logger.error(f"Error extracting SIFIN manuscripts: {e}")
                raise
            finally:
                await page.close()
    
    async def _login(self, page: Page) -> None:
        """Login to SIFIN journal using ORCID"""
        self.logger.info("Logging into SIFIN journal...")
        
        # Navigate to login page
        login_url = f"{self.base_url}/cgi-bin/main.plex"
        await page.goto(login_url)
        await page.wait_for_load_state("networkidle")
        
        # Handle privacy notification modal for SIFIN
        try:
            continue_button = page.locator("button:has-text('Continue')").first
            if await continue_button.is_visible():
                await continue_button.click()
                await page.wait_for_load_state("networkidle")
                self.logger.info("Clicked privacy notification Continue button")
        except:
            self.logger.info("No privacy notification modal found")
        
        # Look for ORCID login link
        orcid_selectors = [
            "a[href*='orcid']",
            "text=Sign in with ORCID",
            "text=ORCID",
            "button:has-text('ORCID')"
        ]
        
        orcid_element = None
        for selector in orcid_selectors:
            try:
                orcid_element = page.locator(selector).first
                if await orcid_element.is_visible():
                    break
            except:
                continue
        
        if orcid_element and await orcid_element.is_visible():
            await orcid_element.click()
            await page.wait_for_load_state("networkidle")
        
        # Enter ORCID credentials
        email = self.settings.orcid_email or ""
        password = self.settings.orcid_password or ""
        
        if not email or not password:
            raise ValueError("ORCID credentials not configured for SIFIN")
        
        # Fill ORCID login form
        try:
            await page.fill("input[name='userId'], input[name='username'], #username", email)
            await page.fill("input[name='password'], #password", password)
            await page.click("button[type='submit'], input[type='submit']")
            await page.wait_for_load_state("networkidle")
        except Exception as e:
            self.logger.error(f"ORCID login failed: {e}")
            raise
        
        self.logger.info("Successfully logged into SIFIN")
    
    async def _scrape_manuscripts(self, page: Page) -> List[Manuscript]:
        """Scrape manuscripts from the SIAM platform"""
        manuscripts = []
        
        # Navigate to manuscripts folder
        try:
            # SIAM platforms typically have folder-based navigation
            folder_url = f"{self.base_url}/cgi-bin/main.plex?form_type=file_manager&folder_id={self.folder_id}"
            await page.goto(folder_url)
            await page.wait_for_load_state("networkidle")
        except Exception as e:
            self.logger.warning(f"Could not navigate to folder {self.folder_id}: {e}")
        
        # Parse manuscript listings
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for manuscript tables - SIAM typically uses tables for listing
        manuscript_tables = soup.find_all('table')
        
        for table in manuscript_tables:
            # Look for tables that contain manuscript data
            rows = table.find_all('tr')
            
            # Check if this table has manuscript-related headers
            headers = [th.get_text().lower() for th in rows[0].find_all(['th', 'td']) if rows]
            manuscript_indicators = ['manuscript', 'title', 'author', 'submission', 'status']
            
            if any(indicator in ' '.join(headers) for indicator in manuscript_indicators):
                # Process manuscript rows
                for row in rows[1:]:  # Skip header
                    try:
                        manuscript = await self._parse_manuscript_row(row)
                        if manuscript:
                            manuscripts.append(manuscript)
                    except Exception as e:
                        self.logger.error(f"Error parsing manuscript row: {e}")
                        continue
        
        # Also look for individual manuscript entries (not in tables)
        manuscript_divs = soup.find_all('div', class_=lambda x: x and 'manuscript' in x.lower())
        for div in manuscript_divs:
            try:
                manuscript = await self._parse_manuscript_div(div)
                if manuscript:
                    manuscripts.append(manuscript)
            except Exception as e:
                self.logger.error(f"Error parsing manuscript div: {e}")
                continue
        
        self.logger.info(f"Found {len(manuscripts)} manuscripts")
        return manuscripts
    
    async def _parse_manuscript_row(self, row) -> Optional[Manuscript]:
        """Parse a single manuscript row"""
        cells = row.find_all(['td', 'th'])
        if len(cells) < 2:
            return None
        
        try:
            # Extract manuscript information based on SIAM table structure
            manuscript_id = None
            title = "Unknown Title"
            authors = []
            status_text = "Under Review"
            submission_date = datetime.now()
            
            # Parse cells - SIAM tables vary but typically have:
            # [ID/Number, Title, Authors, Status, Date, Actions]
            for i, cell in enumerate(cells):
                cell_text = cell.get_text(strip=True)
                
                # Try to find manuscript ID
                if not manuscript_id and re.match(r'\d+', cell_text):
                    manuscript_id = f"SIFIN-{cell_text}"
                
                # Try to find title (usually longest text or in specific position)
                if len(cell_text) > 20 and 'http' not in cell_text.lower():
                    title = cell_text
                
                # Try to find date
                date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', cell_text)
                if date_match:
                    submission_date = self._parse_date(date_match.group()) or datetime.now()
            
            # Generate ID if not found
            if not manuscript_id:
                manuscript_id = f"SIFIN-{hash(title) % 10000}"
            
            # Map status
            status = self._map_manuscript_status(status_text)
            
            manuscript = Manuscript(
                journal_code=self.journal_code,
                external_id=manuscript_id,
                title=title,
                authors=authors,
                submission_date=submission_date,
                status=status,
                custom_metadata={
                    'platform': 'SIAM ORCID',
                    'folder_id': self.folder_id,
                    'original_status': status_text
                }
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript row: {e}")
            return None
    
    async def _parse_manuscript_div(self, div) -> Optional[Manuscript]:
        """Parse manuscript from div container"""
        try:
            # Extract title from heading tags
            title_elem = div.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Look for manuscript ID in div text
            div_text = div.get_text()
            id_match = re.search(r'SIFIN[-_]?\d+|\d{4,}', div_text)
            manuscript_id = id_match.group(0) if id_match else f"SIFIN-{hash(title) % 10000}"
            
            # Extract authors if available
            authors = self._extract_authors_from_text(div_text)
            
            manuscript = Manuscript(
                journal_code=self.journal_code,
                external_id=manuscript_id,
                title=title,
                authors=authors,
                submission_date=datetime.now(),
                status=ManuscriptStatus.UNDER_REVIEW,
                custom_metadata={
                    'platform': 'SIAM ORCID',
                    'source': 'div_listing'
                }
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript div: {e}")
            return None
    
    async def _extract_manuscript_referees(self, page: Page, manuscript: Manuscript) -> None:
        """Extract referee information for a manuscript"""
        try:
            # Try to navigate to manuscript details
            # SIAM platforms typically have detail links
            detail_selectors = [
                f"a:has-text('{manuscript.external_id}')",
                f"a:has-text('{manuscript.title[:30]}')",
                "a:has-text('View'), a:has-text('Details'), a:has-text('Edit')"
            ]
            
            for selector in detail_selectors:
                try:
                    detail_link = page.locator(selector).first
                    if await detail_link.is_visible():
                        await detail_link.click()
                        await page.wait_for_load_state("networkidle")
                        
                        # Extract referees from details page
                        await self._extract_referees_from_details(page, manuscript)
                        
                        # Navigate back
                        await page.go_back()
                        await page.wait_for_load_state("networkidle")
                        break
                        
                except Exception:
                    continue
            
        except Exception as e:
            self.logger.error(f"Error extracting referees for {manuscript.external_id}: {e}")
    
    async def _extract_referees_from_details(self, page: Page, manuscript: Manuscript) -> None:
        """Extract referees from manuscript details page"""
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for referee/reviewer sections
        referee_keywords = ['referee', 'reviewer', 'editor', 'associate']
        
        for keyword in referee_keywords:
            # Find sections containing the keyword
            sections = soup.find_all(text=re.compile(keyword, re.I))
            
            for section in sections:
                parent = section.parent
                if parent:
                    # Look for email addresses and names
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                                      parent.get_text())
                    
                    for email in emails:
                        # Try to find associated name
                        name = self._extract_name_near_email(parent.get_text(), email)
                        
                        if name:
                            referee = Referee(
                                name=name,
                                email=email,
                                expertise_areas=[]
                            )
                            
                            review = Review(
                                referee_id=referee.id,
                                manuscript_id=manuscript.id,
                                status=RefereeStatus.INVITED,
                                invited_date=datetime.now(),
                                custom_metadata={
                                    'platform': 'SIAM ORCID'
                                }
                            )
                            
                            manuscript.add_review(review)
    
    def _extract_authors_from_text(self, text: str) -> List[Author]:
        """Extract author names from text"""
        # Look for author patterns
        author_patterns = [
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'authors?[:\s]+([^.\n]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*)'
        ]
        
        authors = []
        for pattern in author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                authors_text = match.group(1)
                # Split by common separators
                author_names = re.split(r'[,;]|\sand\s', authors_text)
                
                for name in author_names:
                    name = name.strip()
                    if name and len(name) > 2:
                        author = Author(
                            name=name,
                            email=None,
                            affiliation=None
                        )
                        authors.append(author)
                break
        
        return authors
    
    def _extract_name_near_email(self, text: str, email: str) -> Optional[str]:
        """Extract name that appears near an email address"""
        email_pos = text.find(email)
        if email_pos == -1:
            return None
        
        # Get text around the email
        start = max(0, email_pos - 50)
        end = min(len(text), email_pos + len(email) + 50)
        context = text[start:end]
        
        # Look for name patterns
        name_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z]\.\s*[A-Z][a-z]+)',
            r'(Dr\.\s*[A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'(Prof\.\s*[A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str or not date_str.strip():
            return None
            
        date_str = date_str.strip()
        
        # Try common date formats
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%b %d, %Y"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _map_manuscript_status(self, status_text: str) -> ManuscriptStatus:
        """Map SIFIN status to domain status"""
        status = status_text.lower().strip()
        
        if 'submit' in status:
            return ManuscriptStatus.SUBMITTED
        elif 'review' in status:
            return ManuscriptStatus.UNDER_REVIEW
        elif 'accept' in status:
            return ManuscriptStatus.ACCEPTED
        elif 'reject' in status:
            return ManuscriptStatus.REJECTED
        elif 'revisi' in status:
            return ManuscriptStatus.AWAITING_REVISION
        elif 'withdraw' in status:
            return ManuscriptStatus.WITHDRAWN
        else:
            return ManuscriptStatus.UNDER_REVIEW
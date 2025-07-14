"""
Nonlinear Analysis (NACO) Journal Scraper
Async implementation using Playwright and clean architecture
MSP Custom platform
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


class NACOScraper(JournalExtractor):
    """NACO journal scraper for MSP Custom platform"""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "NACO"
        self.base_url = "https://ef.msp.org/login.php"
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from NACO journal"""
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
                self.logger.error(f"Error extracting NACO manuscripts: {e}")
                raise
            finally:
                await page.close()
    
    async def _login(self, page: Page) -> None:
        """Login to NACO journal using MSP platform"""
        self.logger.info("Logging into NACO journal...")
        
        await page.goto(self.base_url)
        await page.wait_for_load_state("networkidle")
        
        # Get credentials
        username = self.settings.naco_username or ""
        password = self.settings.naco_password or ""
        
        if not username or not password:
            raise ValueError("NACO credentials not configured")
        
        # Fill login form
        await page.fill("input[name='login']", username)
        await page.fill("input[name='password']", password)
        await page.click("input[type='submit']")
        
        await page.wait_for_load_state("networkidle")
        
        # Navigate to the manuscripts section - look for "Mine" link
        try:
            await page.click("text=Mine", timeout=10000)
            await page.wait_for_load_state("networkidle")
            self.logger.info("Successfully navigated to manuscripts section")
        except PlaywrightTimeoutError:
            self.logger.warning("Could not find 'Mine' link - checking for alternative navigation")
        
        self.logger.info("Successfully logged into NACO")
    
    async def _scrape_manuscripts(self, page: Page) -> List[Manuscript]:
        """Scrape manuscripts from the MSP platform"""
        manuscripts = []
        
        # Look for manuscript listings - MSP typically uses specific table structures
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find manuscript tables or listings
        # MSP platform typically has tables with manuscript information
        manuscript_tables = soup.find_all('table')
        
        for table in manuscript_tables:
            # Look for tables that contain manuscript data
            headers = table.find_all('th')
            if headers and any(keyword in th.get_text().lower() 
                             for th in headers 
                             for keyword in ['article', 'manuscript', 'title', 'author']):
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    try:
                        manuscript = await self._parse_manuscript_row(row)
                        if manuscript:
                            manuscripts.append(manuscript)
                    except Exception as e:
                        self.logger.error(f"Error parsing manuscript row: {e}")
                        continue
        
        # Also look for JournalView-Listing sections
        listing_sections = soup.find_all('div', class_=re.compile(r'JournalView-Listing', re.I))
        for section in listing_sections:
            try:
                manuscript = await self._parse_listing_section(section)
                if manuscript:
                    manuscripts.append(manuscript)
            except Exception as e:
                self.logger.error(f"Error parsing listing section: {e}")
                continue
        
        self.logger.info(f"Found {len(manuscripts)} manuscripts")
        return manuscripts
    
    async def _parse_manuscript_row(self, row) -> Optional[Manuscript]:
        """Parse a single manuscript row from table"""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None
        
        try:
            # Extract manuscript information
            # MSP tables typically have: ID, Title, Authors, Status, Date
            manuscript_id = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True) if len(cells) > 1 else "Unknown Title"
            
            # Extract authors if available
            authors_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            authors = self._parse_authors(authors_text)
            
            # Extract status and date
            status_text = cells[3].get_text(strip=True) if len(cells) > 3 else "Unknown"
            date_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            
            # Parse date
            submission_date = self._parse_date(date_text) or datetime.now()
            
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
                    'platform': 'MSP Custom',
                    'original_status': status_text
                }
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript row: {e}")
            return None
    
    async def _parse_listing_section(self, section) -> Optional[Manuscript]:
        """Parse manuscript from JournalView-Listing section"""
        try:
            # Extract manuscript details from listing section
            title_elem = section.find('h3') or section.find('h2') or section.find('strong')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Look for manuscript ID in various places
            manuscript_id = None
            id_patterns = [r'NACO[-_]?\d+', r'ID[:\s]+(\d+)', r'#(\d+)']
            section_text = section.get_text()
            
            for pattern in id_patterns:
                match = re.search(pattern, section_text, re.IGNORECASE)
                if match:
                    manuscript_id = match.group(0) if 'NACO' in match.group(0) else f"NACO-{match.group(1)}"
                    break
            
            if not manuscript_id:
                # Generate ID from title or use timestamp
                manuscript_id = f"NACO-{hash(title) % 10000}"
            
            # Extract authors
            authors = self._extract_authors_from_section(section)
            
            manuscript = Manuscript(
                journal_code=self.journal_code,
                external_id=manuscript_id,
                title=title,
                authors=authors,
                submission_date=datetime.now(),
                status=ManuscriptStatus.UNDER_REVIEW,
                custom_metadata={
                    'platform': 'MSP Custom',
                    'source': 'listing_section'
                }
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing listing section: {e}")
            return None
    
    async def _extract_manuscript_referees(self, page: Page, manuscript: Manuscript) -> None:
        """Extract referee information for a manuscript"""
        try:
            # In MSP platform, referee information might be in manuscript details
            # Try to navigate to manuscript details
            manuscript_link = page.locator(f"text={manuscript.title}").first
            
            if await manuscript_link.is_visible():
                await manuscript_link.click()
                await page.wait_for_load_state("networkidle")
                
                # Extract referees from details page
                await self._extract_referees_from_details_page(page, manuscript)
                
                # Navigate back
                await page.go_back()
                await page.wait_for_load_state("networkidle")
            
        except Exception as e:
            self.logger.error(f"Error extracting referees for {manuscript.external_id}: {e}")
    
    async def _extract_referees_from_details_page(self, page: Page, manuscript: Manuscript) -> None:
        """Extract referees from manuscript details page"""
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for referee sections
        referee_keywords = ['referee', 'reviewer', 'editor']
        
        for keyword in referee_keywords:
            sections = soup.find_all(text=re.compile(keyword, re.I))
            
            for section in sections:
                parent = section.parent
                if parent:
                    # Look for email addresses or names near the keyword
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
                                    'platform': 'MSP Custom'
                                }
                            )
                            
                            manuscript.add_review(review)
    
    def _parse_authors(self, authors_text: str) -> List[Author]:
        """Parse authors from text"""
        authors = []
        
        if not authors_text:
            return authors
        
        # Split by common separators
        author_parts = re.split(r'[,;]|\sand\s', authors_text)
        
        for author_part in author_parts:
            name = author_part.strip()
            if name:
                author = Author(
                    name=name,
                    email=None,
                    affiliation=None
                )
                authors.append(author)
        
        return authors
    
    def _extract_authors_from_section(self, section) -> List[Author]:
        """Extract authors from a section element"""
        # Look for author patterns in the section
        author_patterns = [
            r'by\s+([^.\n]+)',
            r'authors?[:\s]+([^.\n]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*)'
        ]
        
        section_text = section.get_text()
        
        for pattern in author_patterns:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                authors_text = match.group(1)
                return self._parse_authors(authors_text)
        
        return []
    
    def _extract_name_near_email(self, text: str, email: str) -> Optional[str]:
        """Extract name that appears near an email address"""
        # Look for name patterns before or after the email
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
        """Map NACO status to domain status"""
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
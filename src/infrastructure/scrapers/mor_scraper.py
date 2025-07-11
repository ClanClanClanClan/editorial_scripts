"""
Mathematics of Operations Research (MOR) Journal Scraper
Async implementation using Playwright and clean architecture
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from ...core.domain.models import (
    Manuscript, Review, Referee, Author, 
    ManuscriptStatus, RefereeStatus, ReviewQuality
)
from ...core.ports.journal_extractor import JournalExtractor
from ...core.ports.browser_pool import BrowserPool
from ..config import get_settings


class MORScraper(JournalExtractor):
    """Mathematics of Operations Research journal scraper for ScholarOne platform"""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "MOR"
        self.base_url = "https://mc.manuscriptcentral.com/mathor"
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from MOR journal"""
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
                self.logger.error(f"Error extracting MOR manuscripts: {e}")
                raise
            finally:
                await page.close()
    
    async def _login(self, page: Page) -> None:
        """Login to Mathematics of Operations Research journal"""
        self.logger.info("Logging into MOR journal...")
        
        await page.goto(self.base_url)
        await page.wait_for_load_state("networkidle")
        
        # Accept cookies if present
        try:
            await page.click("#onetrust-accept-btn-handler", timeout=2000)
            self.logger.info("Accepted cookies")
        except PlaywrightTimeoutError:
            self.logger.debug("No cookie banner found")
        
        # Enter credentials - MOR can use MF credentials as fallback
        username = (self.settings.mor_username or 
                   self.settings.mf_username or 
                   self.settings.scholarone_username or "")
        password = (self.settings.mor_password or 
                   self.settings.mf_password or 
                   self.settings.scholarone_password or "")
        
        if not username or not password:
            raise ValueError("MOR/ScholarOne credentials not configured")
        
        await page.fill("#USERID", username)
        await page.fill("#PASSWORD", password)
        await page.click("#logInButton")
        
        # Handle 2FA if required
        await self._handle_2fa(page)
        
        self.logger.info("Successfully logged into MOR")
    
    async def _handle_2fa(self, page: Page) -> None:
        """Handle two-factor authentication"""
        try:
            # Wait for 2FA input field
            code_input = None
            try:
                await page.wait_for_selector("#TOKEN_VALUE", timeout=5000)
                code_input = page.locator("#TOKEN_VALUE")
            except PlaywrightTimeoutError:
                try:
                    await page.wait_for_selector("#validationCode", timeout=5000)
                    code_input = page.locator("#validationCode")
                except PlaywrightTimeoutError:
                    return  # No 2FA required
            
            if code_input:
                self.logger.info("2FA required - waiting for verification code")
                
                # In production, this would fetch from email or other source
                verification_code = await self._get_verification_code()
                
                if verification_code:
                    await code_input.fill(verification_code)
                    
                    # Check "Remember this device" if available
                    try:
                        remember_checkbox = page.locator("#REMEMBER_THIS_DEVICE")
                        if await remember_checkbox.is_visible():
                            await remember_checkbox.check()
                            self.logger.info("Checked 'Remember this device'")
                    except:
                        pass
                    
                    # Click verify button
                    await page.click("#VERIFY_BTN")
                    await page.wait_for_load_state("networkidle")
                    
                    self.logger.info("2FA verification completed")
                else:
                    raise RuntimeError("No verification code available")
                    
        except Exception as e:
            self.logger.error(f"Error handling 2FA: {e}")
            raise
    
    async def _get_verification_code(self) -> Optional[str]:
        """Get verification code from email or other source"""
        # This would be implemented to fetch from email
        # For now, return None to indicate manual input needed
        self.logger.warning("Verification code fetching not implemented - manual input required")
        return None
    
    async def _scrape_manuscripts(self, page: Page) -> List[Manuscript]:
        """Scrape manuscripts from the dashboard"""
        manuscripts = []
        
        # Navigate to manuscript list
        await page.goto(f"{self.base_url}/Author/AuthorDashboard.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Parse manuscript table
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find manuscript table
        manuscript_tables = soup.find_all('table', class_='BorderTable')
        
        for table in manuscript_tables:
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                try:
                    manuscript = await self._parse_manuscript_row(row)
                    if manuscript:
                        manuscripts.append(manuscript)
                except Exception as e:
                    self.logger.error(f"Error parsing manuscript row: {e}")
                    continue
        
        self.logger.info(f"Found {len(manuscripts)} manuscripts")
        return manuscripts
    
    async def _parse_manuscript_row(self, row) -> Optional[Manuscript]:
        """Parse a single manuscript row"""
        cells = row.find_all('td')
        if len(cells) < 4:
            return None
        
        try:
            # Extract basic manuscript info
            manuscript_id = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            status_text = cells[2].get_text(strip=True)
            submission_date_text = cells[3].get_text(strip=True)
            
            # Parse submission date
            submission_date = self._parse_date(submission_date_text) or datetime.now()
            
            # Map status
            status = self._map_manuscript_status(status_text)
            
            manuscript = Manuscript(
                journal_code=self.journal_code,
                external_id=manuscript_id,
                title=title,
                submission_date=submission_date,
                status=status,
                custom_metadata={
                    'platform': 'ScholarOne',
                    'original_status': status_text
                }
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript: {e}")
            return None
    
    async def _extract_manuscript_referees(self, page: Page, manuscript: Manuscript) -> None:
        """Extract referee information for a manuscript"""
        try:
            # Navigate to manuscript details
            detail_url = f"{self.base_url}/Reviewer/Manuscripts_Details_Popup.aspx?MGID={manuscript.external_id}"
            await page.goto(detail_url)
            await page.wait_for_load_state("networkidle")
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Parse referee information
            referees = self._parse_referee_list(soup, manuscript.external_id)
            
            # Convert to Review objects and add to manuscript
            for referee_data in referees:
                referee = Referee(
                    name=referee_data['name'],
                    email=referee_data['email'],
                    institution=referee_data.get('institution'),
                    expertise_areas=referee_data.get('expertise_areas', [])
                )
                
                review = Review(
                    referee_id=referee.id,
                    manuscript_id=manuscript.id,
                    status=self._map_referee_status(referee_data.get('status', '')),
                    invited_date=self._parse_date(referee_data.get('invited_date')) or datetime.now(),
                    due_date=self._parse_date(referee_data.get('due_date')),
                    responded_date=self._parse_date(referee_data.get('responded_date'))
                )
                
                manuscript.add_review(review)
            
            self.logger.debug(f"Added {len(referees)} referees to manuscript {manuscript.external_id}")
            
        except Exception as e:
            self.logger.error(f"Error extracting referees for {manuscript.external_id}: {e}")
    
    def _parse_referee_list(self, soup: BeautifulSoup, manuscript_id: str) -> List[Dict[str, Any]]:
        """Parse referee list from manuscript details page"""
        referees = []
        
        # Find reviewer tables
        reviewer_sections = soup.find_all('td', class_='detailsheaderbg')
        
        for section in reviewer_sections:
            if 'reviewer list' in section.get_text().lower():
                # Find the associated table
                table = section.find_parent('table')
                if table:
                    referee_rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in referee_rows:
                        try:
                            referee_data = self._parse_referee_row(row)
                            if referee_data:
                                referees.append(referee_data)
                        except Exception as e:
                            self.logger.error(f"Error parsing referee row: {e}")
                            continue
        
        return referees
    
    def _parse_referee_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single referee row"""
        cells = row.find_all('td')
        if len(cells) < 3:
            return None
        
        try:
            name = cells[0].get_text(strip=True)
            email = cells[1].get_text(strip=True)
            status = cells[2].get_text(strip=True)
            
            # Normalize name format
            name = self._normalize_name(name)
            
            return {
                'name': name,
                'email': email,
                'status': status,
                'invited_date': None,  # Would extract from additional columns
                'due_date': None,
                'responded_date': None,
                'institution': None,
                'expertise_areas': []
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing referee data: {e}")
            return None
    
    def _normalize_name(self, name: str) -> str:
        """Convert 'Last, First' to 'First Last' format"""
        name = name.replace('(contact)', '').replace(';', '').strip()
        if ',' in name:
            last, first = [part.strip() for part in name.split(',', 1)]
            return f"{first} {last}"
        return name.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str or not date_str.strip():
            return None
            
        date_str = date_str.strip()
        
        # Try common date formats
        formats = ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _map_manuscript_status(self, status_text: str) -> ManuscriptStatus:
        """Map MOR status to domain status"""
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
        else:
            return ManuscriptStatus.UNDER_REVIEW
    
    def _map_referee_status(self, status_text: str) -> RefereeStatus:
        """Map MOR referee status to domain status"""
        status = status_text.lower().strip()
        
        if status in {'agreed', 'accepted', 'accept'}:
            return RefereeStatus.ACCEPTED
        elif status in {'declined', 'decline'}:
            return RefereeStatus.DECLINED
        elif status in {'completed', 'complete'}:
            return RefereeStatus.COMPLETED
        elif status in {'overdue'}:
            return RefereeStatus.OVERDUE
        elif status in {'contacted', 'invited'}:
            return RefereeStatus.INVITED
        else:
            return RefereeStatus.INVITED
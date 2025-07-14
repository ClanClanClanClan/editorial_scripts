"""
Mathematics and Financial Economics (MAFE) Journal Scraper
Async implementation using Playwright and clean architecture
Editorial Manager Cloud platform
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


class MAFEScraper(JournalExtractor):
    """MAFE journal scraper for Editorial Manager Cloud platform"""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "MAFE"
        self.base_url = "https://www2.cloud.editorialmanager.com/mafe/default2.aspx"
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from MAFE journal"""
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
                self.logger.error(f"Error extracting MAFE manuscripts: {e}")
                raise
            finally:
                await page.close()
    
    async def _login(self, page: Page) -> None:
        """Login to MAFE journal using Editorial Manager Cloud"""
        self.logger.info("Logging into MAFE journal...")
        
        await page.goto(self.base_url)
        await page.wait_for_load_state("networkidle")
        
        # Handle cookie consent
        await self._dismiss_cookies(page)
        
        # Get credentials
        username = self.settings.mafe_username or ""
        password = self.settings.mafe_password or ""
        
        if not username or not password:
            raise ValueError("MAFE credentials not configured")
        
        # Wait for and handle iframe login if present
        try:
            # Check for iframe
            iframe_selector = "iframe[src*='login']"
            await page.wait_for_selector(iframe_selector, timeout=5000)
            
            # Switch to iframe
            iframe = page.frame_locator(iframe_selector)
            
            # Enter credentials in iframe
            await iframe.locator("#login").fill(username)
            await iframe.locator("#password").fill(password)
            await iframe.locator("input[type='submit']").click()
            
        except PlaywrightTimeoutError:
            # No iframe, try direct login
            await page.fill("#login", username)
            await page.fill("#password", password)
            await page.click("input[type='submit']")
        
        await page.wait_for_load_state("networkidle")
        self.logger.info("Successfully logged into MAFE")
    
    async def _dismiss_cookies(self, page: Page) -> None:
        """Dismiss cookie banners"""
        cookie_selectors = [
            "button:has-text('Accept all cookies')",
            "button:has-text('Accept cookies')", 
            "button:has-text('Accept')",
            "button:has-text('Got it')",
            "button:has-text('Agree')",
            ".cc-btn",
            ".cookie-accept",
            ".accept-cookies"
        ]
        
        for selector in cookie_selectors:
            try:
                await page.click(selector, timeout=2000)
                self.logger.info(f"Dismissed cookies using: {selector}")
                break
            except PlaywrightTimeoutError:
                continue
    
    async def _scrape_manuscripts(self, page: Page) -> List[Manuscript]:
        """Scrape manuscripts from the dashboard"""
        manuscripts = []
        
        # Navigate to manuscripts list
        try:
            # Look for manuscripts menu/link
            await page.click("text=Manuscripts", timeout=5000)
        except PlaywrightTimeoutError:
            # Try alternative navigation
            await page.click("text=My Manuscripts", timeout=5000)
        
        await page.wait_for_load_state("networkidle")
        
        # Parse manuscript table
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find manuscript tables
        manuscript_tables = soup.find_all('table')
        
        for table in manuscript_tables:
            # Look for table with manuscript data
            headers = table.find_all('th')
            if headers and any('manuscript' in th.get_text().lower() for th in headers):
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
        if len(cells) < 3:
            return None
        
        try:
            # Extract manuscript info (adjust indices based on table structure)
            manuscript_id = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            status_text = cells[2].get_text(strip=True) if len(cells) > 2 else "Unknown"
            submission_date_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            
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
                    'platform': 'Editorial Manager Cloud',
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
            # Navigate to manuscript details - this depends on MAFE's specific interface
            # Try to find and click on manuscript link
            manuscript_link = page.locator(f"text={manuscript.external_id}").first
            if await manuscript_link.is_visible():
                await manuscript_link.click()
                await page.wait_for_load_state("networkidle")
                
                # Look for reviewer section
                await self._extract_reviewers_from_page(page, manuscript)
                
                # Navigate back
                await page.go_back()
                await page.wait_for_load_state("networkidle")
            
        except Exception as e:
            self.logger.error(f"Error extracting referees for {manuscript.external_id}: {e}")
    
    async def _extract_reviewers_from_page(self, page: Page, manuscript: Manuscript) -> None:
        """Extract reviewers from manuscript detail page"""
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for reviewer sections
        reviewer_sections = soup.find_all('div', class_=re.compile(r'reviewer|referee', re.I))
        reviewer_sections.extend(soup.find_all('table', class_=re.compile(r'reviewer|referee', re.I)))
        
        for section in reviewer_sections:
            try:
                # Look for reviewer emails in popup windows or links
                email_links = section.find_all('a', href=re.compile(r'mailto:', re.I))
                
                for link in email_links:
                    email = link.get('href', '').replace('mailto:', '')
                    name = link.get_text(strip=True) or self._clean_author_name(link.parent.get_text())
                    
                    if email and name:
                        referee = Referee(
                            name=name,
                            email=email,
                            expertise_areas=[]
                        )
                        
                        review = Review(
                            referee_id=referee.id,
                            manuscript_id=manuscript.id,
                            status=RefereeStatus.INVITED,  # Default status
                            invited_date=datetime.now(),
                            custom_metadata={
                                'platform': 'Editorial Manager Cloud'
                            }
                        )
                        
                        manuscript.add_review(review)
                        
            except Exception as e:
                self.logger.error(f"Error parsing reviewer section: {e}")
                continue
    
    def _clean_author_name(self, raw: str) -> str:
        """Clean author name by removing titles and extra text"""
        if not raw:
            return ""
        
        name = re.sub(r"(Pr\.|Prof\.|Dr\.|Ph\.?D\.?|Professor|,.*)", "", raw, flags=re.IGNORECASE)
        name = re.sub(r"\s+", " ", name)
        return name.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str or not date_str.strip():
            return None
            
        date_str = date_str.strip()
        
        # Try common date formats for Editorial Manager
        formats = ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _map_manuscript_status(self, status_text: str) -> ManuscriptStatus:
        """Map MAFE status to domain status"""
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
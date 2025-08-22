"""ScholarOne (Manuscript Central) async adapter implementation."""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional

from playwright.async_api import Page

from src.ecc.adapters.journals.base import AsyncJournalAdapter, JournalConfig
from src.ecc.core.domain.models import (
    Author,
    File,
    Manuscript,
    ManuscriptStatus,
    Referee,
    RefereeStatus,
)


class ScholarOneAdapter(AsyncJournalAdapter):
    """Adapter for ScholarOne journals (MF, MOR)."""
    
    def __init__(self, config: JournalConfig):
        super().__init__(config)
        self.manuscript_pattern = self._get_manuscript_pattern()
        
    def _get_manuscript_pattern(self) -> str:
        """Get journal-specific manuscript ID pattern."""
        patterns = {
            "MF": r"MAFI-\d{4}-\d{4}",
            "MOR": r"MOR-\d{4}-\d{4}",
        }
        return patterns.get(self.config.journal_id, r"\w+-\d{4}-\d{4}")
        
    async def authenticate(self) -> bool:
        """Handle ScholarOne authentication with 2FA support."""
        try:
            self.logger.info("Starting ScholarOne authentication")
            
            # Navigate to login page
            await self.navigate_with_retry(self.config.url)
            
            # Get credentials from secure storage (TODO: integrate with Vault)
            credentials = await self._get_credentials()
            
            # Fill login form
            await self.fill_form_field("#USERID", credentials["username"])
            await self.fill_form_field("#PASSWORD", credentials["password"])
            
            # Submit login
            await self.click_and_wait("#logInButton", wait_after=3)
            
            # Check for 2FA
            if await self._requires_2fa():
                await self._handle_2fa()
                
            # Verify login success
            if await self.page.query_selector("text=Dashboard"):
                self.logger.info("Authentication successful")
                return True
            else:
                self.logger.error("Authentication failed - dashboard not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
            
    async def _requires_2fa(self) -> bool:
        """Check if 2FA is required."""
        token_field = await self.page.query_selector("#TOKEN_VALUE")
        return token_field is not None
        
    async def _handle_2fa(self):
        """Handle 2FA verification."""
        self.logger.info("2FA required, fetching code...")
        
        # TODO: Integrate with Gmail service to fetch 2FA code
        # For now, using a placeholder
        code = await self._fetch_2fa_code()
        
        await self.fill_form_field("#TOKEN_VALUE", code)
        await self.page.press("#TOKEN_VALUE", "Enter")
        await self.page.wait_for_load_state("networkidle")
        
    async def _fetch_2fa_code(self) -> str:
        """Fetch 2FA code from email (placeholder for Gmail integration)."""
        # TODO: Implement Gmail integration
        self.logger.warning("2FA code fetch not implemented - manual entry required")
        await asyncio.sleep(30)  # Wait for manual entry
        return ""
        
    async def _get_credentials(self) -> Dict[str, str]:
        """Get credentials from secure storage."""
        # TODO: Integrate with HashiCorp Vault
        import os
        return {
            "username": os.environ.get(f"{self.config.journal_id}_EMAIL", ""),
            "password": os.environ.get(f"{self.config.journal_id}_PASSWORD", ""),
        }
        
    async def fetch_manuscripts(self, categories: List[str]) -> List[Manuscript]:
        """Fetch manuscripts from specified categories."""
        manuscripts = []
        
        try:
            # Navigate to Associate Editor Center
            await self.click_and_wait("text=Associate Editor Center")
            
            for category in categories:
                try:
                    manuscripts_in_category = await self._fetch_category_manuscripts(category)
                    manuscripts.extend(manuscripts_in_category)
                except Exception as e:
                    self.logger.error(f"Error fetching category {category}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error fetching manuscripts: {e}")
            
        self.logger.info(f"Fetched {len(manuscripts)} manuscripts total")
        return manuscripts
        
    async def _fetch_category_manuscripts(self, category: str) -> List[Manuscript]:
        """Fetch manuscripts from a specific category."""
        manuscripts = []
        
        # Find category link with count
        category_selector = f"td:has-text('{category}')"
        category_elem = await self.page.query_selector(category_selector)
        
        if not category_elem:
            self.logger.warning(f"Category not found: {category}")
            return manuscripts
            
        # Get count from adjacent cell
        count_elem = await self.page.query_selector(f"{category_selector} >> xpath=.. >> td:first-child")
        if count_elem:
            count_text = await count_elem.inner_text()
            count = int(re.search(r'\d+', count_text).group()) if re.search(r'\d+', count_text) else 0
            
            if count == 0:
                self.logger.info(f"No manuscripts in category: {category}")
                return manuscripts
                
            # Click to view manuscripts
            await count_elem.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Parse manuscript list
            manuscripts = await self._parse_manuscript_list()
            
            # Return to dashboard
            await self.page.go_back()
            await self.page.wait_for_load_state("networkidle")
            
        return manuscripts
        
    async def _parse_manuscript_list(self) -> List[Manuscript]:
        """Parse manuscripts from the current list page."""
        manuscripts = []
        
        # Find manuscript rows
        rows = await self.page.query_selector_all("tr.manuscriptRow, tr[class*='tablerow']")
        
        for row in rows:
            try:
                manuscript = await self._parse_manuscript_row(row)
                if manuscript:
                    manuscripts.append(manuscript)
            except Exception as e:
                self.logger.error(f"Error parsing manuscript row: {e}")
                continue
                
        return manuscripts
        
    async def _parse_manuscript_row(self, row) -> Optional[Manuscript]:
        """Parse a single manuscript row."""
        try:
            # Extract manuscript ID
            id_elem = await row.query_selector("a[href*='MANUSCRIPT']")
            if not id_elem:
                return None
                
            manuscript_id = await id_elem.inner_text()
            manuscript_id = manuscript_id.strip()
            
            # Extract title
            title_elem = await row.query_selector("td:nth-child(2)")
            title = await title_elem.inner_text() if title_elem else ""
            
            # Extract status
            status_elem = await row.query_selector("td:nth-child(3)")
            status_text = await status_elem.inner_text() if status_elem else ""
            status = self._parse_status(status_text)
            
            # Create manuscript object
            manuscript = Manuscript(
                journal_id=self.config.journal_id,
                external_id=manuscript_id,
                title=title.strip(),
                current_status=status,
            )
            
            return manuscript
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript row: {e}")
            return None
            
    def _parse_status(self, status_text: str) -> ManuscriptStatus:
        """Parse manuscript status from text."""
        status_text = status_text.lower().strip()
        
        status_map = {
            "submitted": ManuscriptStatus.SUBMITTED,
            "under review": ManuscriptStatus.UNDER_REVIEW,
            "awaiting": ManuscriptStatus.AWAITING_REFEREE_REPORTS,
            "decision": ManuscriptStatus.AWAITING_DECISION,
            "revision": ManuscriptStatus.REVISION_REQUESTED,
            "accepted": ManuscriptStatus.ACCEPTED,
            "rejected": ManuscriptStatus.REJECTED,
        }
        
        for key, value in status_map.items():
            if key in status_text:
                return value
                
        return ManuscriptStatus.SUBMITTED
        
    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        """Extract detailed information for a specific manuscript."""
        manuscript = Manuscript(
            journal_id=self.config.journal_id,
            external_id=manuscript_id,
        )
        
        try:
            # Navigate to manuscript details
            await self.click_and_wait(f"text={manuscript_id}")
            
            # Extract all details in parallel
            await asyncio.gather(
                self._extract_basic_info(manuscript),
                self._extract_authors(manuscript),
                self._extract_referees(manuscript),
                self._extract_metadata(manuscript),
            )
            
            # Return to list
            await self.page.go_back()
            
        except Exception as e:
            self.logger.error(f"Error extracting manuscript details: {e}")
            
        return manuscript
        
    async def _extract_basic_info(self, manuscript: Manuscript):
        """Extract basic manuscript information."""
        try:
            # Title
            title_elem = await self.page.query_selector("td:has-text('Title:') >> xpath=.. >> td:last-child")
            if title_elem:
                manuscript.title = await title_elem.inner_text()
                
            # Abstract (might be in popup)
            abstract_link = await self.page.query_selector("a:has-text('View Abstract')")
            if abstract_link:
                abstract = await self.handle_popup_window(abstract_link.click)
                if abstract:
                    manuscript.abstract = abstract.get("text", "")
                    
            # Keywords
            keywords_elem = await self.page.query_selector("td:has-text('Keywords:') >> xpath=.. >> td:last-child")
            if keywords_elem:
                keywords_text = await keywords_elem.inner_text()
                manuscript.keywords = [k.strip() for k in keywords_text.split(",")]
                
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")
            
    async def _extract_authors(self, manuscript: Manuscript):
        """Extract author information."""
        try:
            author_rows = await self.page.query_selector_all("tr:has(td:has-text('Author'))")
            
            for row in author_rows:
                author = Author()
                
                # Name (might be link)
                name_elem = await row.query_selector("a")
                if name_elem:
                    author.name = await name_elem.inner_text()
                    
                    # Try to get email from popup
                    email_data = await self.handle_popup_window(name_elem.click)
                    if email_data:
                        author.email = self._extract_email_from_popup(email_data)
                        
                # Institution
                inst_elem = await row.query_selector("td:nth-child(3)")
                if inst_elem:
                    author.institution = await inst_elem.inner_text()
                    
                manuscript.authors.append(author)
                
        except Exception as e:
            self.logger.error(f"Error extracting authors: {e}")
            
    async def _extract_referees(self, manuscript: Manuscript):
        """Extract referee information."""
        try:
            referee_rows = await self.page.query_selector_all("tr:has(td:has-text('Referee'))")
            
            for row in referee_rows:
                referee = Referee()
                
                # Name (might be link)
                name_elem = await row.query_selector("a")
                if name_elem:
                    referee.name = await name_elem.inner_text()
                    
                    # Try to get email from popup
                    email_data = await self.handle_popup_window(name_elem.click)
                    if email_data:
                        referee.email = self._extract_email_from_popup(email_data)
                        
                # Status
                status_elem = await row.query_selector("td:nth-child(4)")
                if status_elem:
                    status_text = await status_elem.inner_text()
                    referee.status = self._parse_referee_status(status_text)
                    
                manuscript.referees.append(referee)
                
        except Exception as e:
            self.logger.error(f"Error extracting referees: {e}")
            
    def _parse_referee_status(self, status_text: str) -> RefereeStatus:
        """Parse referee status from text."""
        status_text = status_text.lower().strip()
        
        if "agreed" in status_text:
            return RefereeStatus.AGREED
        elif "declined" in status_text:
            return RefereeStatus.DECLINED
        elif "submitted" in status_text:
            return RefereeStatus.REPORT_SUBMITTED
        elif "overdue" in status_text:
            return RefereeStatus.OVERDUE
        else:
            return RefereeStatus.INVITED
            
    async def _extract_metadata(self, manuscript: Manuscript):
        """Extract additional metadata."""
        try:
            # Page count
            pages_elem = await self.page.query_selector("td:has-text('Pages:') >> xpath=.. >> td:last-child")
            if pages_elem:
                pages_text = await pages_elem.inner_text()
                if pages_text.isdigit():
                    manuscript.page_count = int(pages_text)
                    
            # Word count
            words_elem = await self.page.query_selector("td:has-text('Word Count:') >> xpath=.. >> td:last-child")
            if words_elem:
                words_text = await words_elem.inner_text()
                words_text = re.sub(r'[^\d]', '', words_text)
                if words_text:
                    manuscript.word_count = int(words_text)
                    
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            
    def _extract_email_from_popup(self, popup_data: Dict) -> str:
        """Extract email address from popup content."""
        text = popup_data.get("text", "")
        
        # Look for email pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        
        return match.group() if match else ""
        
    async def download_manuscript_files(self, manuscript: Manuscript) -> List[Path]:
        """Download all files associated with a manuscript."""
        downloaded_files = []
        
        try:
            # Navigate to manuscript if not already there
            if manuscript.external_id not in await self.page.content():
                await self.click_and_wait(f"text={manuscript.external_id}")
                
            # Find download links
            download_links = await self.page.query_selector_all("a[href*='download'], a:has-text('PDF')")
            
            for link in download_links:
                try:
                    filename = f"{manuscript.external_id}_{await link.inner_text()}.pdf"
                    file_path = await self.download_file(link.click, filename)
                    downloaded_files.append(file_path)
                    
                    # Add to manuscript files
                    manuscript.files.append(File(
                        manuscript_id=manuscript.id,
                        filename=filename,
                        storage_path=str(file_path),
                    ))
                    
                except Exception as e:
                    self.logger.error(f"Error downloading file: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error downloading manuscript files: {e}")
            
        return downloaded_files
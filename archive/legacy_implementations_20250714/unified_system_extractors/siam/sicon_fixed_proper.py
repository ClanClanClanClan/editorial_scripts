"""
SICON Extractor - PROPERLY FIXED Implementation
Following the exact workflow provided by the user
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from .base import SIAMBaseExtractor
from ...core.base_extractor import Manuscript, Referee

logger = logging.getLogger(__name__)


class SICONExtractorProper(SIAMBaseExtractor):
    """
    PROPERLY FIXED SICON extractor that follows the correct workflow:
    1. Navigate through category pages (not direct URLs)
    2. Parse TWO distinct referee sections correctly
    3. No duplicates - each referee appears once
    4. Proper status assignment based on section
    """
    
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manuscript_urls = {}  # Store URLs for each manuscript
    
    async def _navigate_to_manuscripts(self) -> bool:
        """
        FIXED: Navigate through category pages to collect all manuscripts
        Click on all "N AE" links where N > 0
        """
        try:
            logger.info("🔍 Navigating to manuscript categories...")
            
            # Navigate to main AE page after login
            main_url = f"{self.base_url}/cgi-bin/sicon/main.plex"
            await self.page.goto(main_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            # Categories to check - order matters!
            categories_to_check = [
                ("Under Review", "ViewUnderReview"),
                ("All Pending Manuscripts", "ViewAllPending"),
                ("Waiting for Revision", "ViewWaitingRevision"),
                ("Awaiting Referee Assignment", "ViewAwaitingReferee"),
                ("Awaiting Associate Editor Recommendation", "ViewAwaitingAE")
            ]
            
            all_manuscript_ids = set()
            
            for category_name, view_name in categories_to_check:
                logger.info(f"📂 Checking category: {category_name}")
                
                try:
                    # Find link containing both the category name and "AE"
                    # Look for pattern like "Under Review 4 AE"
                    links = await self.page.query_selector_all('a')
                    
                    for link in links:
                        text = await link.inner_text()
                        if category_name in text and "AE" in text:
                            # Extract count
                            count_match = re.search(r'(\d+)\s*AE', text)
                            if count_match:
                                count = int(count_match.group(1))
                                if count > 0:
                                    logger.info(f"✅ Found {count} manuscripts in {category_name}")
                                    
                                    # Click the link
                                    await link.click()
                                    await self.page.wait_for_load_state("networkidle")
                                    await asyncio.sleep(2)
                                    
                                    # Extract manuscript IDs from the list page
                                    content = await self.page.content()
                                    soup = BeautifulSoup(content, 'html.parser')
                                    
                                    # Find all manuscript links (pattern: /m/M172838)
                                    ms_links = soup.find_all('a', href=re.compile(r'/m/M\d+'))
                                    
                                    for ms_link in ms_links:
                                        href = ms_link.get('href', '')
                                        ms_id_match = re.search(r'(M\d+)', href)
                                        if ms_id_match:
                                            ms_id = ms_id_match.group(1)
                                            all_manuscript_ids.add(ms_id)
                                            # Store the full URL for later navigation
                                            full_url = f"{self.base_url}{href}" if not href.startswith('http') else href
                                            self.manuscript_urls[ms_id] = full_url
                                            logger.info(f"   📄 Found manuscript: {ms_id}")
                                    
                                    # Go back to main page for next category
                                    await self.page.goto(main_url, wait_until="networkidle")
                                    await asyncio.sleep(1)
                                    break
                
                except Exception as e:
                    logger.error(f"❌ Error checking category {category_name}: {e}")
                    continue
            
            logger.info(f"✅ Found {len(all_manuscript_ids)} total manuscripts")
            return len(all_manuscript_ids) > 0
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    async def _extract_manuscripts(self) -> List[Manuscript]:
        """
        FIXED: Extract manuscripts by visiting each detail page
        """
        manuscripts = []
        
        for ms_id, ms_url in self.manuscript_urls.items():
            try:
                logger.info(f"📄 Processing manuscript {ms_id}")
                
                # Navigate to manuscript detail page
                await self.page.goto(ms_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
                content = await self.page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract manuscript details
                manuscript = await self._extract_manuscript_details(ms_id, soup, content)
                if manuscript:
                    manuscripts.append(manuscript)
                    
            except Exception as e:
                logger.error(f"❌ Failed to extract manuscript {ms_id}: {e}")
                continue
        
        return manuscripts
    
    async def _extract_manuscript_details(self, ms_id: str, soup: BeautifulSoup, content: str) -> Optional[Manuscript]:
        """
        FIXED: Extract complete manuscript details including proper referee parsing
        """
        try:
            # Create manuscript object
            manuscript = Manuscript(
                id=ms_id,
                title=self._extract_field_value(soup, "Title"),
                authors=[],
                status=self._extract_field_value(soup, "Current Stage") or "Under Review",
                submission_date=self._extract_field_value(soup, "Submission Date"),
                journal="SICON",
                corresponding_editor=self._extract_field_value(soup, "Corresponding Editor"),
                associate_editor=self._extract_field_value(soup, "Associate Editor")
            )
            
            # Extract authors
            authors_text = self._extract_field_value(soup, "Corresponding Author")
            contrib_authors = self._extract_field_value(soup, "Contributing Authors")
            
            if authors_text:
                # Clean author names
                author_name = re.sub(r'\s*\([^)]*\)', '', authors_text).strip()
                if author_name:
                    manuscript.authors.append(author_name)
            
            if contrib_authors:
                # Split by common delimiters and clean
                for author in re.split(r'[,;]', contrib_authors):
                    author_name = re.sub(r'\s*\([^)]*\)', '', author).strip()
                    author_name = re.sub(r'\s*orcid$', '', author_name, flags=re.IGNORECASE).strip()
                    if author_name and len(author_name) > 2:
                        manuscript.authors.append(author_name)
            
            # CRITICAL FIX: Extract referees from TWO distinct sections
            declined_referees = await self._extract_potential_referees(soup, content)
            active_referees = await self._extract_active_referees(soup, content)
            
            # Combine without duplicates
            all_referees = declined_referees + active_referees
            
            # Deduplicate by email
            unique_referees = {}
            for referee in all_referees:
                key = (referee.email.upper() if referee.email else referee.name)
                if key not in unique_referees:
                    unique_referees[key] = referee
            
            manuscript.referees = list(unique_referees.values())
            
            logger.info(f"✅ Extracted {len(manuscript.referees)} unique referees for {ms_id}")
            logger.info(f"   - Declined: {len([r for r in manuscript.referees if r.status == 'Declined'])}")
            logger.info(f"   - Accepted: {len([r for r in manuscript.referees if 'Accept' in r.status or 'submitted' in r.status])}")
            
            # Extract PDF URLs
            manuscript.pdf_urls = self._extract_pdf_urls(soup, content)
            
            return manuscript
            
        except Exception as e:
            logger.error(f"❌ Failed to extract manuscript details: {e}")
            return None
    
    async def _extract_potential_referees(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """
        Extract referees from 'Potential Referees' section
        These can be:
        - Declined referees: (Status: Declined)
        - Contacted but no response yet: (Status: No Response) or no status
        Pattern: Name #N (Last Contact Date: YYYY-MM-DD) (Status: [Status])
        """
        referees = []
        
        try:
            logger.info("🔍 Extracting Potential Referees...")
            
            # Find the Potential Referees row
            potential_row = None
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2 and 'Potential Referees' in cells[0].get_text():
                    potential_row = row
                    break
            
            if not potential_row:
                logger.warning("⚠️ No Potential Referees section found")
                return referees
            
            # Get the content cell (second td)
            content_cell = potential_row.find_all('td')[1] if len(potential_row.find_all('td')) > 1 else None
            if not content_cell:
                return referees
            
            # Parse each referee entry
            # Pattern: Name #N (Last Contact Date: YYYY-MM-DD) (Status: Declined)
            cell_text = content_cell.get_text()
            
            # Split by line breaks or referee number pattern
            entries = re.split(r'(?=#\d+)', cell_text)
            
            for entry in entries:
                if not entry.strip():
                    continue
                
                # Extract referee info
                # Pattern variations:
                # Name #N (Last Contact Date: YYYY-MM-DD) (Status: Declined)
                # Name #N (Last Contact Date: YYYY-MM-DD) (Status: No Response)
                # Name #N (Last Contact Date: YYYY-MM-DD)
                
                # First try pattern with status
                pattern_with_status = r'([^#]+?)\s*#(\d+)\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)\s*\(Status:\s*([^)]+)\)'
                match = re.search(pattern_with_status, entry)
                
                if match:
                    name = match.group(1).strip()
                    ref_num = match.group(2)
                    contact_date = match.group(3)
                    status_text = match.group(4).strip()
                    
                    # Determine actual status
                    if "Declined" in status_text:
                        status = "Declined"
                        is_declined = True
                        logger.info(f"   ❌ Declined: {name} (contacted {contact_date})")
                    elif "No Response" in status_text:
                        status = "No Response"
                        is_declined = False
                        logger.info(f"   ⏳ No Response: {name} (contacted {contact_date})")
                    else:
                        status = status_text
                        is_declined = False
                        logger.info(f"   ❓ {status}: {name} (contacted {contact_date})")
                else:
                    # Try pattern without status (assume contacted but no response)
                    pattern_no_status = r'([^#]+?)\s*#(\d+)\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)'
                    match = re.search(pattern_no_status, entry)
                    
                    if match:
                        name = match.group(1).strip()
                        ref_num = match.group(2)
                        contact_date = match.group(3)
                        status = "Contacted, awaiting response"
                        is_declined = False
                        logger.info(f"   ⏳ Awaiting Response: {name} (contacted {contact_date})")
                    else:
                        continue
                
                # Create referee object
                referee = Referee(
                    name=name,
                    email="",  # Will be filled by clicking on name
                    status=status,
                    institution=None
                )
                
                # Set fields based on status
                referee.contact_date = contact_date
                if is_declined:
                    referee.declined = True
                    referee.declined_date = contact_date
                
                # Find the link for this referee to get details
                referee_link = content_cell.find('a', text=re.compile(re.escape(name)))
                if referee_link:
                    await self._fetch_referee_details(referee, referee_link)
                
                referees.append(referee)
            
            return referees
            
        except Exception as e:
            logger.error(f"❌ Potential referees extraction failed: {e}")
            return referees
    
    async def _extract_active_referees(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """
        FIXED: Extract ACCEPTED referees from 'Referees' section
        Patterns:
        - Name #N (Rcvd: YYYY-MM-DD) = Report submitted
        - Name #N (Due: YYYY-MM-DD) = Accepted, awaiting report
        """
        referees = []
        
        try:
            logger.info("🔍 Extracting Active Referees (Accepted)...")
            
            # Find the Referees row (not Potential Referees)
            referees_row = None
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    cell_text = cells[0].get_text().strip()
                    if cell_text == 'Referees' or (cell_text.startswith('Referees') and 'Potential' not in cell_text):
                        referees_row = row
                        break
            
            if not referees_row:
                logger.warning("⚠️ No Referees section found")
                return referees
            
            # Get the content cell
            content_cell = referees_row.find_all('td')[1] if len(referees_row.find_all('td')) > 1 else None
            if not content_cell:
                return referees
            
            cell_text = content_cell.get_text()
            
            # Parse referees with Rcvd dates (submitted reports)
            rcvd_pattern = r'([^#,]+?)\s*#(\d+)\s*\(Rcvd:\s*(\d{4}-\d{2}-\d{2})\)'
            for match in re.finditer(rcvd_pattern, cell_text):
                name = match.group(1).strip()
                ref_num = match.group(2)
                received_date = match.group(3)
                
                referee = Referee(
                    name=name,
                    email="",
                    status="Report submitted",
                    institution=None,
                    report_submitted=True,
                    report_date=received_date
                )
                
                # Find the link for details
                referee_link = content_cell.find('a', text=re.compile(re.escape(name)))
                if referee_link:
                    await self._fetch_referee_details(referee, referee_link)
                
                referees.append(referee)
                logger.info(f"   ✅ Submitted: {referee.name} (received {received_date})")
            
            # Parse referees with Due dates (pending reports)
            due_pattern = r'([^#,]+?)\s*#(\d+)\s*\(Due:\s*(\d{4}-\d{2}-\d{2})\)'
            for match in re.finditer(due_pattern, cell_text):
                name = match.group(1).strip()
                ref_num = match.group(2)
                due_date = match.group(3)
                
                referee = Referee(
                    name=name,
                    email="",
                    status="Accepted, awaiting report",
                    institution=None,
                    report_submitted=False
                )
                
                # Set due date
                referee.due_date = due_date
                
                # Find the link for details
                referee_link = content_cell.find('a', text=re.compile(re.escape(name)))
                if referee_link:
                    await self._fetch_referee_details(referee, referee_link)
                
                referees.append(referee)
                logger.info(f"   ⏳ Pending: {referee.name} (due {due_date})")
            
            return referees
            
        except Exception as e:
            logger.error(f"❌ Active referees extraction failed: {e}")
            return referees
    
    async def _fetch_referee_details(self, referee: Referee, link_element) -> None:
        """
        Click on referee name to get email and affiliation
        """
        try:
            href = link_element.get('href', '')
            if not href:
                return
            
            # Build full URL
            biblio_url = f"{self.base_url}{href}" if not href.startswith('http') else href
            
            # Open in new tab to preserve current page
            new_page = await self.page.context.new_page()
            
            try:
                # Navigate to biblio page
                await new_page.goto(biblio_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)
                
                content = await new_page.content()
                
                # Extract email - SIAM uses uppercase emails
                email_patterns = [
                    r'([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})',
                    r'(?i)email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                    r'(?i)e-mail[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                ]
                
                for pattern in email_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        # Take first valid email
                        email = matches[0] if isinstance(matches[0], str) else matches[0]
                        referee.email = email.upper()
                        break
                
                # Extract institution
                inst_patterns = [
                    r'(?:University|Institute|Université|École)\s+(?:of\s+)?[^,<\n]+',
                    r'[A-Z][a-z]+\s+(?:University|Institute|College)',
                    r'(?:ETH|MIT|UCLA|NYU|INRIA|CNRS)\s*[^,<\n]*'
                ]
                
                for pattern in inst_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        institution = match.group(0).strip()
                        # Clean up institution name
                        institution = re.sub(r'\s+', ' ', institution)
                        if len(institution) > 5:  # Reasonable length
                            referee.institution = institution
                            break
                
                logger.info(f"      📧 {referee.name}: {referee.email or 'No email'} ({referee.institution or 'No institution'})")
                
            finally:
                await new_page.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch details for {referee.name}: {e}")
    
    def _extract_field_value(self, soup: BeautifulSoup, field_name: str) -> Optional[str]:
        """Extract value for a field from the manuscript page"""
        try:
            # Look for pattern: <td>Field Name</td><td>Value</td>
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    if field_name.lower() in cells[0].get_text().lower():
                        value = cells[1].get_text(strip=True)
                        # Clean up the value
                        value = re.sub(r'\s+', ' ', value)
                        return value if value and value != 'N/A' else None
            return None
        except Exception:
            return None
    
    def _extract_pdf_urls(self, soup: BeautifulSoup, content: str) -> Dict[str, str]:
        """Extract PDF URLs from manuscript page"""
        pdf_urls = {}
        
        try:
            # Find Manuscript Items section
            items_section = None
            for heading in soup.find_all(['h2', 'h3', 'b']):
                if 'Manuscript Items' in heading.get_text():
                    items_section = heading.parent
                    break
            
            if items_section:
                # Look for PDF links
                pdf_links = items_section.find_all('a', href=True)
                
                for link in pdf_links:
                    href = link.get('href', '')
                    text = link.get_text()
                    
                    if 'PDF' in text or '.pdf' in href.lower():
                        # Determine PDF type
                        if 'Article' in text or 'Manuscript' in text:
                            pdf_urls['manuscript'] = f"{self.base_url}{href}" if not href.startswith('http') else href
                        elif 'Referee' in text and 'Review' in text:
                            # Extract referee number
                            ref_num_match = re.search(r'#(\d+)', text)
                            if ref_num_match:
                                ref_num = ref_num_match.group(1)
                                pdf_urls[f'referee_report_{ref_num}'] = f"{self.base_url}{href}" if not href.startswith('http') else href
                        elif 'Source' in text:
                            pdf_urls['source'] = f"{self.base_url}{href}" if not href.startswith('http') else href
            
            if pdf_urls:
                logger.info(f"   📎 Found {len(pdf_urls)} PDFs to download")
            
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
        
        return pdf_urls
    
    async def _extract_referee_details(self, manuscript: Manuscript):
        """Override to prevent the broken implementation from running"""
        # Already handled in _extract_manuscript_details
        pass
    
    async def _extract_pdfs(self, manuscript: Manuscript):
        """Download PDFs for manuscript"""
        if not manuscript.pdf_urls:
            return
        
        for pdf_type, url in manuscript.pdf_urls.items():
            try:
                filename = f"{manuscript.id}_{pdf_type}.pdf"
                pdf_path = await self.download_pdf(url, filename)
                if pdf_path:
                    manuscript.pdf_paths[pdf_type] = str(pdf_path)
                    logger.info(f"   ✅ Downloaded {pdf_type}")
            except Exception as e:
                logger.error(f"   ❌ Failed to download {pdf_type}: {e}")
    
    async def _extract_referee_reports(self, manuscript: Manuscript):
        """Referee reports are downloaded as PDFs, not extracted as text"""
        # Reports are already handled in PDF downloads
        pass


# For direct testing
if __name__ == "__main__":
    async def test_proper_sicon():
        from src.core.credential_manager import get_credential_manager
        
        creds = get_credential_manager().get_credentials('SICON')
        if not creds:
            print("❌ No credentials found")
            return
        
        extractor = SICONExtractorProper()
        results = await extractor.extract(
            username=creds['username'],
            password=creds['password'],
            headless=True
        )
        
        print(f"✅ Extraction complete: {results['total_manuscripts']} manuscripts")
        
        # Show referee summary
        for ms in results['manuscripts']:
            print(f"\n{ms['id']}:")
            declined = [r for r in ms['referees'] if r['status'] == 'Declined']
            submitted = [r for r in ms['referees'] if 'submitted' in r['status']]
            pending = [r for r in ms['referees'] if 'awaiting' in r['status']]
            
            print(f"  - Declined: {len(declined)}")
            print(f"  - Submitted: {len(submitted)}")
            print(f"  - Pending: {len(pending)}")
            print(f"  - Total unique: {len(ms['referees'])}")
    
    import asyncio
    # asyncio.run(test_proper_sicon())
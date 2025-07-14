"""
SICON Extractor - Final Implementation
Combines July 11 working logic with all identified fixes
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeout

from extractors.base import BaseExtractor
from core.models import Manuscript, Referee
from utils.gmail import GmailService

logger = logging.getLogger(__name__)


class SICONExtractor(BaseExtractor):
    """SICON extractor - proven to work"""
    
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    login_type = "orcid"
    requires_cloudflare_wait = True
    cloudflare_wait_seconds = 60
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        
        # Initialize Gmail service for email verification
        try:
            self.gmail_service = GmailService()
            logger.info("✅ Gmail service initialized for email verification")
        except Exception as e:
            logger.warning(f"⚠️ Gmail service not available: {e}")
            self.gmail_service = None
    
    async def _authenticate_orcid(self) -> bool:
        """ORCID authentication - proven to work"""
        try:
            logger.info("🔐 Starting ORCID authentication")
            
            # Find ORCID login button - try multiple selectors
            orcid_selectors = [
                "a[href*='orcid']",
                "button:has-text('ORCID')",
                "a:has-text('Sign in with ORCID')",
                "a:has-text('ORCID')",
                ".orcid-signin-button"
            ]
            
            orcid_found = False
            for selector in orcid_selectors:
                try:
                    orcid_link = await self.page.wait_for_selector(selector, timeout=5000)
                    if orcid_link:
                        orcid_found = True
                        await orcid_link.click()
                        logger.info("✅ Clicked ORCID login button")
                        break
                except:
                    continue
            
            if not orcid_found:
                logger.error("❌ ORCID login button not found")
                return False
            
            # Wait for ORCID page
            await self.page.wait_for_load_state("networkidle", timeout=self.default_timeout)
            await asyncio.sleep(2)
            
            # Fill ORCID credentials
            try:
                # Username field
                await self.page.fill("input[name='userId']", self.username)
                logger.info("✅ Filled username")
                
                # Password field
                await self.page.fill("input[name='password']", self.password)
                logger.info("✅ Filled password")
                
                # Submit
                await self.page.click("button[type='submit']")
                logger.info("✅ Submitted credentials")
                
            except Exception as e:
                logger.error(f"❌ Failed to fill ORCID form: {e}")
                return False
            
            # Wait for redirect back to SICON
            await self.page.wait_for_load_state("networkidle", timeout=self.default_timeout)
            await asyncio.sleep(3)
            
            # Verify we're logged in
            current_url = self.page.url
            if 'sicon' in current_url.lower():
                logger.info("✅ Successfully authenticated with ORCID")
                return True
            else:
                logger.error(f"❌ Not redirected to SICON. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ ORCID authentication failed: {e}")
            return False
    
    async def _get_all_manuscripts(self) -> List[Manuscript]:
        """Get all manuscripts from AE dashboard"""
        logger.info("📋 Getting manuscripts from dashboard")
        manuscripts = []
        
        try:
            # Navigate to AE dashboard - proven URL from July 11
            dashboard_url = f"{self.base_url}/cgi-bin/main.plex?form_type=display_ae_dash"
            await self.page.goto(dashboard_url, wait_until="networkidle", timeout=self.default_timeout)
            
            # Wait for content
            await asyncio.sleep(3)
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all manuscript links - proven selector from July 11
            manuscript_links = soup.find_all('a', href=re.compile(r'display_auth_page.*ms_id='))
            
            logger.info(f"Found {len(manuscript_links)} manuscript links")
            
            for link in manuscript_links:
                href = link.get('href', '')
                
                # Extract manuscript ID
                ms_id_match = re.search(r'ms_id=(\d+)', href)
                if ms_id_match:
                    ms_id = ms_id_match.group(1)
                    manuscript_id = f"M{ms_id}"
                    
                    # Create basic manuscript object
                    manuscript = Manuscript(
                        id=manuscript_id,
                        title="",  # Will be filled in _extract_manuscript_details
                        authors=[],
                        status="Under Review",
                        journal="SICON"
                    )
                    
                    manuscripts.append(manuscript)
                    logger.info(f"📄 Found manuscript: {manuscript_id}")
            
            # Handle "All Pending Manuscripts" folder if needed
            if len(manuscripts) == 0:
                logger.info("📁 Checking All Pending Manuscripts folder...")
                try:
                    # Click on folder link
                    folder_link = await self.page.wait_for_selector("a[href*='folder_id=1800']", timeout=5000)
                    if folder_link:
                        await folder_link.click()
                        await self.page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2)
                        
                        # Re-parse page
                        content = await self.page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        manuscript_links = soup.find_all('a', href=re.compile(r'display_auth_page.*ms_id='))
                        
                        for link in manuscript_links:
                            href = link.get('href', '')
                            ms_id_match = re.search(r'ms_id=(\d+)', href)
                            if ms_id_match:
                                ms_id = ms_id_match.group(1)
                                manuscript_id = f"M{ms_id}"
                                
                                manuscript = Manuscript(
                                    id=manuscript_id,
                                    title="",
                                    authors=[],
                                    status="Under Review",
                                    journal="SICON"
                                )
                                
                                manuscripts.append(manuscript)
                                logger.info(f"📄 Found manuscript in folder: {manuscript_id}")
                except:
                    pass
            
            logger.info(f"✅ Found total {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logger.error(f"Failed to get manuscripts: {e}")
            return manuscripts
    
    async def _extract_manuscript_details(self, manuscript: Manuscript):
        """Extract full details for a manuscript - WITH FIXES APPLIED"""
        logger.info(f"🔍 Extracting details for {manuscript.id}")
        
        try:
            # Navigate to manuscript detail page
            ms_id = manuscript.id.replace('M', '')
            detail_url = f"{self.base_url}/cgi-bin/main.plex?form_type=display_auth_page&j_id=8&ms_id={ms_id}&ms_rev_no=0"
            
            await self.page.goto(detail_url, wait_until="networkidle", timeout=self.default_timeout)
            await asyncio.sleep(2)
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # CRITICAL FIX: Parse metadata FIRST
            metadata = self._parse_manuscript_metadata(soup)
            
            # Update manuscript with parsed data
            manuscript.title = metadata['title'] or f"Manuscript {manuscript.id}"
            manuscript.authors = metadata['authors'] or ["Author information not available"]
            manuscript.submission_date = metadata['submission_date']
            manuscript.corresponding_editor = metadata['corresponding_editor']
            manuscript.associate_editor = metadata['associate_editor']
            
            logger.info(f"📝 Title: {manuscript.title[:60]}...")
            logger.info(f"✍️ Authors: {', '.join(manuscript.authors[:2])}")
            logger.info(f"👤 AE: {manuscript.associate_editor}")
            
            # Extract referees
            await self._extract_referees(manuscript, soup)
            
            # Extract PDF URLs
            manuscript.pdf_urls = self._extract_pdf_urls(soup)
            
            logger.info(f"✅ Extracted details: {len(manuscript.referees)} referees, {len(manuscript.pdf_urls)} PDFs")
            
        except Exception as e:
            logger.error(f"Failed to extract details for {manuscript.id}: {e}")
    
    def _parse_manuscript_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse manuscript metadata from HTML - FIXED implementation"""
        metadata = {
            'title': '',
            'authors': [],
            'submission_date': None,
            'corresponding_editor': None,
            'associate_editor': None
        }
        
        try:
            # Find all table rows
            for row in soup.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label_cell = cells[0]
                    value_cell = cells[1]
                    
                    label = label_cell.get_text(strip=True)
                    value = value_cell.get_text(strip=True)
                    
                    # Title
                    if any(t in label for t in ['Title', 'Article Title', 'Manuscript Title']):
                        metadata['title'] = value
                        logger.debug(f"Found title: {value[:60]}...")
                    
                    # Submission date
                    elif any(d in label for d in ['Submission Date', 'Submitted', 'Date Submitted']):
                        metadata['submission_date'] = value
                        logger.debug(f"Found submission date: {value}")
                    
                    # Associate Editor
                    elif 'Associate Editor' in label or 'AE' in label:
                        metadata['associate_editor'] = value
                        logger.debug(f"Found AE: {value}")
                    
                    # Corresponding Editor
                    elif 'Corresponding Editor' in label or 'CE' in label:
                        metadata['corresponding_editor'] = value
                        logger.debug(f"Found CE: {value}")
                    
                    # Authors
                    elif any(a in label for a in ['Author', 'Corresponding Author', 'Contact Author']):
                        # Clean author name (remove affiliation)
                        author_name = re.sub(r'\([^)]*\)', '', value).strip()
                        if author_name and author_name not in metadata['authors']:
                            metadata['authors'].append(author_name)
                            logger.debug(f"Found author: {author_name}")
            
            # If no title found, try headers
            if not metadata['title']:
                for tag in ['h1', 'h2', 'h3']:
                    headers = soup.find_all(tag)
                    for header in headers:
                        header_text = header.get_text(strip=True)
                        # Skip headers that are just the manuscript ID
                        if len(header_text) > 20 and not header_text.startswith('M'):
                            metadata['title'] = header_text
                            logger.debug(f"Found title from header: {header_text[:60]}...")
                            break
                    if metadata['title']:
                        break
        
        except Exception as e:
            logger.error(f"Error parsing metadata: {e}")
        
        return metadata
    
    async def _extract_referees(self, manuscript: Manuscript, soup: BeautifulSoup):
        """Extract referees from manuscript page"""
        try:
            # 1. Parse Potential Referees section
            potential_referees = self._parse_potential_referees(soup)
            for ref in potential_referees:
                manuscript.add_referee(ref)
            
            # 2. Parse Active Referees section
            active_referees = self._parse_active_referees(soup)
            for ref in active_referees:
                manuscript.add_referee(ref)
            
            logger.info(f"👥 Found {len(manuscript.referees)} referees total")
            
        except Exception as e:
            logger.error(f"Failed to extract referees: {e}")
    
    def _parse_potential_referees(self, soup: BeautifulSoup) -> List[Referee]:
        """Parse potential referees section"""
        referees = []
        
        try:
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                
                if th and td and 'Potential Referees' in th.get_text():
                    # Get referee links
                    referee_links = td.find_all('a', href=re.compile(r'biblio_dump'))
                    td_html = str(td)
                    
                    for link in referee_links:
                        name = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Clean name
                        name_match = re.match(r'(.+?)\s*#(\d+)', name)
                        clean_name = name_match.group(1).strip() if name_match else name
                        
                        # Extract status and date
                        escaped_name = re.escape(name)
                        pattern = escaped_name + r'</a>\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)\s*(?:\(Status:\s*([^)]+)\))?'
                        match = re.search(pattern, td_html)
                        
                        status = "Invited"
                        contact_date = None
                        
                        if match:
                            contact_date = match.group(1)
                            status_text = match.group(2) or "Invited"
                            
                            if "Declined" in status_text:
                                status = "Declined"
                            elif "No Response" in status_text:
                                status = "No Response"
                            else:
                                status = status_text
                        
                        referee = Referee(
                            name=clean_name,
                            email="",  # Will be filled by email extraction
                            status=status,
                            contact_date=contact_date,
                            biblio_url=f"{self.base_url}/{href}" if not href.startswith('http') else href
                        )
                        
                        referees.append(referee)
                        logger.debug(f"Potential referee: {clean_name} - {status}")
                    
                    break
        
        except Exception as e:
            logger.error(f"Error parsing potential referees: {e}")
        
        return referees
    
    def _parse_active_referees(self, soup: BeautifulSoup) -> List[Referee]:
        """Parse active referees section"""
        referees = []
        
        try:
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                
                if th and td and 'Referees' in th.get_text() and 'Potential' not in th.get_text():
                    # Get referee links
                    referee_links = td.find_all('a', href=re.compile(r'biblio_dump'))
                    td_text = td.get_text()
                    
                    for link in referee_links:
                        name = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Clean name
                        name_match = re.match(r'(.+?)\s*#(\d+)', name)
                        clean_name = name_match.group(1).strip() if name_match else name
                        
                        # Determine status
                        status = "Accepted"
                        report_submitted = False
                        report_date = None
                        
                        # Check for report submission
                        if "Report submitted" in td_text:
                            report_submitted = True
                            status = "Report submitted"
                            
                            # Try to extract date
                            date_match = re.search(r'Report submitted[:\s]+(\d{4}-\d{2}-\d{2})', td_text)
                            if date_match:
                                report_date = date_match.group(1)
                        elif "awaiting report" in td_text.lower():
                            status = "Accepted, awaiting report"
                        
                        referee = Referee(
                            name=clean_name,
                            email="",  # Will be filled by email extraction
                            status=status,
                            report_submitted=report_submitted,
                            report_date=report_date,
                            biblio_url=f"{self.base_url}/{href}" if not href.startswith('http') else href
                        )
                        
                        referees.append(referee)
                        logger.debug(f"Active referee: {clean_name} - {status}")
                    
                    break
        
        except Exception as e:
            logger.error(f"Error parsing active referees: {e}")
        
        return referees
    
    async def _extract_referee_emails(self, manuscript: Manuscript):
        """Extract referee emails by clicking bio links"""
        logger.info(f"📧 Extracting referee emails for {manuscript.id}")
        
        for referee in manuscript.referees:
            if hasattr(referee, 'biblio_url') and referee.biblio_url and not referee.email:
                try:
                    # Navigate to bio page
                    await self.page.goto(referee.biblio_url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(1)
                    
                    # Get page content
                    content = await self.page.content()
                    
                    # Extract email
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
                    if email_match:
                        referee.email = email_match.group(1)
                        logger.info(f"✅ Found email for {referee.name}: {referee.email}")
                    else:
                        logger.debug(f"No email found for {referee.name}")
                    
                except Exception as e:
                    logger.debug(f"Failed to get email for {referee.name}: {e}")
            
            # Gmail verification if available
            if self.gmail_service and referee.email:
                try:
                    email_data = self.gmail_service.search_referee_emails(
                        referee.name,
                        referee.email,
                        manuscript.id,
                        manuscript.submission_date
                    )
                    
                    referee.email_verification = email_data
                    referee.reminder_count = email_data.get('reminder_count', 0)
                    
                    logger.info(f"📧 Gmail verification for {referee.name}: {email_data['emails_found']} emails found")
                    
                except Exception as e:
                    logger.debug(f"Gmail verification failed for {referee.name}: {e}")
    
    def _extract_pdf_urls(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract PDF URLs from manuscript page"""
        pdf_urls = {}
        
        try:
            # Find all PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf'))
            
            for i, link in enumerate(pdf_links):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Make URL absolute
                if not href.startswith('http'):
                    href = f"{self.base_url}/{href.lstrip('/')}"
                
                # Categorize PDFs
                if 'cover' in text or 'letter' in text:
                    pdf_urls['cover_letter'] = href
                elif 'supplement' in text:
                    pdf_urls['supplement'] = href
                elif 'manuscript' in text or 'article' in text:
                    pdf_urls['manuscript'] = href
                else:
                    # Generic naming for other PDFs
                    pdf_urls[f'pdf_{i+1}'] = href
                
                logger.debug(f"Found PDF: {text} -> {href}")
        
        except Exception as e:
            logger.error(f"Error extracting PDF URLs: {e}")
        
        return pdf_urls
    
    async def _download_pdfs(self, manuscript: Manuscript):
        """Download PDFs for manuscript"""
        if not manuscript.pdf_urls:
            logger.info(f"No PDFs to download for {manuscript.id}")
            return
        
        logger.info(f"📥 Downloading {len(manuscript.pdf_urls)} PDFs for {manuscript.id}")
        
        for pdf_type, url in manuscript.pdf_urls.items():
            try:
                filename = f"{manuscript.id}_{pdf_type}.pdf"
                pdf_path = await self._download_pdf_simple(url, filename)
                
                if pdf_path:
                    manuscript.pdf_paths[pdf_type] = str(pdf_path)
                    
            except Exception as e:
                logger.error(f"Failed to download {pdf_type}: {e}")
        
        logger.info(f"✅ Downloaded {len(manuscript.pdf_paths)}/{len(manuscript.pdf_urls)} PDFs")
    
    async def _authenticate_email(self) -> bool:
        """Not used for SICON"""
        return False
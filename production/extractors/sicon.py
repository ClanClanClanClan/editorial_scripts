"""
SICON Extractor - Production Implementation
Optimized based on working July 11 system with all identified fixes
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from core.extractor import BaseExtractor
from core.models import Manuscript, Referee

logger = logging.getLogger(__name__)


class SICONExtractor(BaseExtractor):
    """SICON extractor with all fixes applied"""
    
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    login_type = "orcid"
    requires_cloudflare_wait = True
    cloudflare_wait_seconds = 60
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self.manuscripts_cache = {}
    
    async def _extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts from SICON dashboard"""
        logger.info("📋 Extracting manuscripts from SICON dashboard")
        
        try:
            # Navigate to AE dashboard
            await self.page.goto(f"{self.base_url}/cgi-bin/main.plex?form_type=display_ae_dash", 
                               wait_until="networkidle", timeout=60000)
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            manuscripts = []
            
            # Find manuscript links in the dashboard
            manuscript_links = soup.find_all('a', href=re.compile(r'display_auth_page.*ms_id='))
            
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
                        authors=[],  # Will be filled in _extract_manuscript_details
                        status="Under Review",
                        journal="SICON"
                    )
                    
                    manuscripts.append(manuscript)
                    logger.info(f"📄 Found manuscript: {manuscript_id}")
            
            logger.info(f"✅ Found {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logger.error(f"Failed to extract manuscripts: {e}")
            return []
    
    async def _extract_manuscript_details(self, manuscript: Manuscript):
        """Extract detailed information for a manuscript"""
        logger.info(f"🔍 Extracting details for {manuscript.id}")
        
        try:
            # Navigate to manuscript detail page
            ms_id = manuscript.id.replace('M', '')
            detail_url = f"{self.base_url}/cgi-bin/main.plex?form_type=display_auth_page&j_id=8&ms_id={ms_id}&ms_rev_no=0"
            
            await self.page.goto(detail_url, wait_until="networkidle", timeout=60000)
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # CRITICAL FIX: Parse metadata BEFORE updating manuscript
            title, authors, submission_date, corresponding_editor, associate_editor = self._parse_manuscript_metadata(soup)
            
            # Update manuscript with parsed data
            manuscript.title = title or f"Manuscript {manuscript.id}"
            manuscript.authors = authors or ["Author information not available"]
            manuscript.submission_date = submission_date
            manuscript.corresponding_editor = corresponding_editor
            manuscript.associate_editor = associate_editor
            
            # Extract referees
            await self._extract_referees(manuscript, soup)
            
            # Extract PDF URLs
            manuscript.pdf_urls = self._extract_pdf_urls(soup)
            
            logger.info(f"✅ Extracted details for {manuscript.id}: {len(manuscript.referees)} referees")
            
        except Exception as e:
            logger.error(f"Failed to extract details for {manuscript.id}: {e}")
    
    def _parse_manuscript_metadata(self, soup: BeautifulSoup) -> tuple:
        """Parse manuscript metadata from HTML - FIXED implementation"""
        title = ""
        authors = []
        submission_date = None
        corresponding_editor = None
        associate_editor = None
        
        try:
            # Extract from table rows using multiple patterns
            for row in soup.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label_cell = cells[0]
                    value_cell = cells[1]
                    
                    label = label_cell.get_text(strip=True)
                    value = value_cell.get_text(strip=True)
                    
                    # Title matching - flexible patterns
                    if any(pattern in label for pattern in ['Title', 'Article Title', 'Manuscript Title']):
                        title = value
                        logger.debug(f"📝 Found title: {title[:60]}...")
                    
                    # Submission date
                    elif any(pattern in label for pattern in ['Submission Date', 'Submitted', 'Date Submitted']):
                        submission_date = value
                        logger.debug(f"📅 Found submission date: {submission_date}")
                    
                    # Associate Editor
                    elif 'Associate Editor' in label or 'AE' in label:
                        associate_editor = value
                        logger.debug(f"👤 Found AE: {associate_editor}")
                    
                    # Corresponding Editor
                    elif 'Corresponding Editor' in label or 'CE' in label:
                        corresponding_editor = value
                        logger.debug(f"👤 Found CE: {corresponding_editor}")
                    
                    # Authors - multiple patterns
                    elif any(pattern in label for pattern in ['Author', 'Corresponding Author', 'Contact Author']):
                        # Clean author name (remove affiliation in parentheses)
                        author_name = re.sub(r'\([^)]*\)', '', value).strip()
                        if author_name and author_name not in authors:
                            authors.append(author_name)
                            logger.debug(f"✍️ Found author: {author_name}")
            
            # If no title found, try headers
            if not title:
                for tag in ['h1', 'h2', 'h3']:
                    headers = soup.find_all(tag)
                    for header in headers:
                        header_text = header.get_text(strip=True)
                        if len(header_text) > 20 and 'M' not in header_text[:5]:
                            title = header_text
                            logger.debug(f"📝 Found title from header: {title[:60]}...")
                            break
                    if title:
                        break
        
        except Exception as e:
            logger.error(f"Error parsing manuscript metadata: {e}")
        
        return title, authors, submission_date, corresponding_editor, associate_editor
    
    async def _extract_referees(self, manuscript: Manuscript, soup: BeautifulSoup):
        """Extract referees from manuscript page"""
        try:
            # Extract from multiple referee sections
            
            # 1. Potential Referees section
            potential_referees = self._parse_potential_referees(soup)
            for ref in potential_referees:
                manuscript.add_referee(ref)
            
            # 2. Active Referees section
            active_referees = self._parse_active_referees(soup)
            for ref in active_referees:
                manuscript.add_referee(ref)
            
            # 3. Get referee emails by clicking bio links
            await self._extract_referee_emails(manuscript)
            
        except Exception as e:
            logger.error(f"Failed to extract referees: {e}")
    
    def _parse_potential_referees(self, soup: BeautifulSoup) -> List[Referee]:
        """Parse potential referees section"""
        referees = []
        
        try:
            # Find Potential Referees row
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
                        
                        # Clean name (remove referee number)
                        name_match = re.match(r'(.+?)\s*#(\d+)', name)
                        clean_name = name_match.group(1).strip() if name_match else name
                        
                        # Extract status and date
                        escaped_name = re.escape(name)
                        pattern = escaped_name + r'</a>\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)\s*(?:\(Status:\s*([^)]+)\))?'
                        match = re.search(pattern, td_html)
                        
                        if match:
                            contact_date = match.group(1)
                            status_text = match.group(2) or "Contacted, awaiting response"
                            
                            # Determine status
                            if "Declined" in status_text:
                                status = "Declined"
                            elif "No Response" in status_text:
                                status = "No Response"
                            else:
                                status = status_text
                            
                            referee = Referee(
                                name=clean_name,
                                email="",  # Will be filled later
                                status=status,
                                contact_date=contact_date,
                                biblio_url=f"{self.base_url}/{href}" if not href.startswith('http') else href
                            )
                            
                            referees.append(referee)
                            logger.debug(f"👥 Potential referee: {clean_name} - {status}")
                    
                    break
        
        except Exception as e:
            logger.error(f"Error parsing potential referees: {e}")
        
        return referees
    
    def _parse_active_referees(self, soup: BeautifulSoup) -> List[Referee]:
        """Parse active referees section"""
        referees = []
        
        try:
            # Find Referees row
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                
                if th and td and 'Referees' in th.get_text() and 'Potential' not in th.get_text():
                    # Get referee links
                    referee_links = td.find_all('a', href=re.compile(r'biblio_dump'))
                    td_html = str(td)
                    
                    for link in referee_links:
                        name = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Clean name
                        name_match = re.match(r'(.+?)\s*#(\d+)', name)
                        clean_name = name_match.group(1).strip() if name_match else name
                        
                        # Look for status information
                        status = "Accepted"  # Default for active referees
                        
                        # Check for report submitted
                        if "Report submitted" in td_html:
                            status = "Report submitted"
                        elif "Accepted, awaiting report" in td_html:
                            status = "Accepted, awaiting report"
                        
                        referee = Referee(
                            name=clean_name,
                            email="",  # Will be filled later
                            status=status,
                            biblio_url=f"{self.base_url}/{href}" if not href.startswith('http') else href
                        )
                        
                        referees.append(referee)
                        logger.debug(f"👥 Active referee: {clean_name} - {status}")
                    
                    break
        
        except Exception as e:
            logger.error(f"Error parsing active referees: {e}")
        
        return referees
    
    async def _extract_referee_emails(self, manuscript: Manuscript):
        """Extract referee emails by clicking bio links"""
        try:
            for referee in manuscript.referees:
                if referee.biblio_url and not referee.email:
                    try:
                        # Navigate to referee bio page
                        await self.page.goto(referee.biblio_url, wait_until="networkidle", timeout=30000)
                        
                        # Extract email from bio page
                        content = await self.page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Look for email patterns
                        email_patterns = [
                            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                            r'mailto:([^"]*)',
                        ]
                        
                        for pattern in email_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                email = matches[0]
                                if isinstance(email, tuple):
                                    email = email[0]
                                
                                referee.email = email.strip()
                                logger.debug(f"📧 Found email for {referee.name}: {email}")
                                break
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract email for {referee.name}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error extracting referee emails: {e}")
    
    def _extract_pdf_urls(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract PDF URLs from manuscript page"""
        pdf_urls = {}
        
        try:
            # Find PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf'))
            
            for link in pdf_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Categorize PDFs
                if 'cover' in text.lower():
                    pdf_urls['cover_letter'] = href
                elif 'supplement' in text.lower():
                    pdf_urls['supplement'] = href
                elif 'manuscript' in text.lower() or 'article' in text.lower():
                    pdf_urls['manuscript'] = href
                else:
                    # Generic PDF
                    pdf_urls[f'pdf_{len(pdf_urls)}'] = href
                
                logger.debug(f"📄 Found PDF: {text} -> {href}")
        
        except Exception as e:
            logger.error(f"Error extracting PDF URLs: {e}")
        
        return pdf_urls
    
    async def _download_pdfs(self, manuscript: Manuscript):
        """Download PDFs for manuscript"""
        if not manuscript.pdf_urls:
            logger.info(f"📄 No PDFs found for {manuscript.id}")
            return
        
        logger.info(f"📥 Downloading {len(manuscript.pdf_urls)} PDFs for {manuscript.id}")
        
        for pdf_type, url in manuscript.pdf_urls.items():
            try:
                # Create filename
                filename = f"{manuscript.id}_{pdf_type}.pdf"
                
                # Download PDF
                pdf_path = await self._download_pdf(url, filename)
                
                if pdf_path:
                    manuscript.pdf_paths[pdf_type] = str(pdf_path)
                    logger.info(f"✅ Downloaded {pdf_type} PDF for {manuscript.id}")
                else:
                    logger.warning(f"❌ Failed to download {pdf_type} PDF for {manuscript.id}")
            
            except Exception as e:
                logger.error(f"Error downloading {pdf_type} PDF for {manuscript.id}: {e}")
        
        logger.info(f"📄 Downloaded {len(manuscript.pdf_paths)}/{len(manuscript.pdf_urls)} PDFs for {manuscript.id}")
"""
Enhanced Referee Extractor
Extracts detailed referee timelines and all available documents
"""

import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from playwright.async_api import Page
from bs4 import BeautifulSoup
import aiohttp
import aiofiles

from src.core.referee_analytics import RefereeTimeline, RefereeEvent, RefereeEventType
from src.infrastructure.storage.document_storage import DocumentStorage


class EnhancedRefereeExtractor:
    """Extract comprehensive referee information from journal pages"""
    
    def __init__(self, journal_code: str, base_url: str):
        self.journal_code = journal_code
        self.base_url = base_url
        self.document_storage = DocumentStorage()
    
    async def extract_referee_timeline_siam(self, page: Page, manuscript_id: str) -> List[RefereeTimeline]:
        """Extract detailed referee timelines from SIAM journals (SICON/SIFIN)"""
        timelines = []
        
        try:
            # Navigate to referee details page
            if self.journal_code == 'SICON':
                # Click on manuscript
                ms_link = page.locator(f"a:has-text('{manuscript_id}')")
                if await ms_link.is_visible():
                    await ms_link.click()
                    await page.wait_for_timeout(3000)
                    
                    # Click referee list
                    referee_btn = page.locator("input[value='Referee List']")
                    if await referee_btn.is_visible():
                        await referee_btn.click()
                        await page.wait_for_timeout(3000)
            else:  # SIFIN
                # Navigate to manuscript URL
                ms_url = f"{self.base_url}/manuscripts/{manuscript_id}/referees"
                await page.goto(ms_url)
                await page.wait_for_timeout(3000)
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract referee table with timeline details
            referee_table = soup.find('table', {'class': 'referee-list'}) or soup.find('table', {'border': '1'})
            
            if referee_table:
                rows = referee_table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    timeline = self._parse_siam_referee_row(row, manuscript_id)
                    if timeline:
                        # Look for additional timeline details
                        referee_name = timeline.name
                        
                        # Click on referee name for detailed history
                        referee_link = page.locator(f"a:has-text('{referee_name}')")
                        if await referee_link.is_visible():
                            await referee_link.click()
                            await page.wait_for_timeout(2000)
                            
                            # Extract detailed timeline
                            detail_content = await page.content()
                            self._extract_siam_referee_details(timeline, detail_content)
                            
                            # Download referee report if available
                            await self._download_referee_report_siam(page, timeline, manuscript_id)
                            
                            # Go back
                            await page.go_back()
                            await page.wait_for_timeout(2000)
                        
                        timelines.append(timeline)
            
            # Navigate back to manuscript list
            if self.journal_code == 'SICON':
                await page.go_back()
                await page.wait_for_timeout(2000)
                await page.go_back()
                await page.wait_for_timeout(2000)
                
        except Exception as e:
            print(f"Error extracting SIAM referee timeline: {e}")
        
        return timelines
    
    def _parse_siam_referee_row(self, row, manuscript_id: str) -> Optional[RefereeTimeline]:
        """Parse a SIAM referee table row"""
        cells = row.find_all('td')
        if len(cells) < 3:
            return None
        
        try:
            # Extract basic info
            name_cell = cells[0]
            email_cell = cells[1] if len(cells) > 1 else None
            status_cell = cells[2] if len(cells) > 2 else None
            
            # Extract name and email
            name = name_cell.get_text(strip=True)
            email = email_cell.get_text(strip=True) if email_cell else self._extract_email_from_text(str(name_cell))
            
            timeline = RefereeTimeline(
                name=name,
                email=email or f"{name.replace(' ', '.').lower()}@unknown.edu",
                manuscript_id=manuscript_id,
                journal_code=self.journal_code
            )
            
            # Parse status text for dates
            if status_cell:
                status_text = status_cell.get_text(strip=True)
                self._parse_status_dates(timeline, status_text)
            
            return timeline
            
        except Exception as e:
            print(f"Error parsing referee row: {e}")
            return None
    
    def _extract_email_from_text(self, text: str) -> Optional[str]:
        """Extract email from text"""
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        return email_match.group(0) if email_match else None
    
    def _parse_status_dates(self, timeline: RefereeTimeline, status_text: str):
        """Parse dates from status text"""
        # Common patterns
        patterns = {
            'invited': r'(?:Invited|Contacted).*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'accepted': r'(?:Accepted|Agreed).*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'declined': r'(?:Declined|Refused).*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'due': r'(?:Due|Deadline).*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'submitted': r'(?:Submitted|Completed).*?(\d{1,2}[-/]\w{3}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        }
        
        for date_type, pattern in patterns.items():
            match = re.search(pattern, status_text, re.IGNORECASE)
            if match:
                date = self._parse_date_string(match.group(1))
                if date:
                    if date_type == 'invited':
                        timeline.invited_date = date
                        timeline.add_event(RefereeEvent(RefereeEventType.INVITED, date))
                    elif date_type == 'accepted':
                        timeline.accepted_date = date
                        timeline.add_event(RefereeEvent(RefereeEventType.ACCEPTED, date))
                    elif date_type == 'declined':
                        timeline.declined_date = date
                        timeline.add_event(RefereeEvent(RefereeEventType.DECLINED, date))
                    elif date_type == 'due':
                        timeline.due_date = date
                    elif date_type == 'submitted':
                        timeline.submitted_date = date
                        timeline.add_event(RefereeEvent(RefereeEventType.REPORT_SUBMITTED, date))
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        date_str = date_str.strip()
        
        # Try different formats
        formats = [
            '%d-%b-%Y', '%d-%b-%y',  # 15-Jan-2024, 15-Jan-24
            '%d/%m/%Y', '%d/%m/%y',  # 15/01/2024, 15/01/24
            '%m/%d/%Y', '%m/%d/%y',  # 01/15/2024, 01/15/24
            '%Y-%m-%d',              # 2024-01-15
            '%d %b %Y', '%d %b %y'   # 15 Jan 2024, 15 Jan 24
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _extract_siam_referee_details(self, timeline: RefereeTimeline, content: str):
        """Extract detailed timeline from referee detail page"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for timeline/history table
        history_table = soup.find('table', {'class': 'history'}) or soup.find('table', string=re.compile('History|Timeline'))
        
        if history_table:
            rows = history_table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_text = cells[0].get_text(strip=True)
                    event_text = cells[1].get_text(strip=True)
                    
                    date = self._parse_date_string(date_text)
                    if date:
                        # Classify event
                        event_type = self._classify_event(event_text)
                        if event_type:
                            timeline.add_event(RefereeEvent(event_type, date, event_text))
        
        # Count emails sent
        email_count = len(re.findall(r'(?:email|message|reminder) sent', content, re.IGNORECASE))
        reminder_count = len(re.findall(r'reminder sent', content, re.IGNORECASE))
        
        timeline.total_emails_sent = email_count
        timeline.reminder_emails_sent = reminder_count
    
    def _classify_event(self, event_text: str) -> Optional[RefereeEventType]:
        """Classify event type from text"""
        event_text = event_text.lower()
        
        if 'invited' in event_text or 'invitation' in event_text:
            return RefereeEventType.INVITED
        elif 'reminder' in event_text:
            return RefereeEventType.REMINDER_SENT
        elif 'accepted' in event_text or 'agreed' in event_text:
            return RefereeEventType.ACCEPTED
        elif 'declined' in event_text or 'refused' in event_text:
            return RefereeEventType.DECLINED
        elif 'submitted' in event_text or 'completed' in event_text:
            return RefereeEventType.REPORT_SUBMITTED
        elif 'overdue' in event_text:
            return RefereeEventType.OVERDUE
        
        return None
    
    async def _download_referee_report_siam(self, page: Page, timeline: RefereeTimeline, manuscript_id: str):
        """Download referee report for SIAM journals"""
        try:
            # Look for report download link
            report_links = await page.locator("a:has-text('Report'), a:has-text('Download'), a[href*='report']").all()
            
            for link in report_links:
                href = await link.get_attribute('href')
                if href:
                    # Make URL absolute
                    if not href.startswith('http'):
                        href = f"{self.base_url}{href}"
                    
                    # Download report
                    filename = f"referee_report_{timeline.name.replace(' ', '_')}.pdf"
                    file_path = await self._download_document(href, manuscript_id, timeline.email, filename)
                    
                    if file_path:
                        timeline.report_pdf_path = file_path
                        break
                        
        except Exception as e:
            print(f"Error downloading referee report: {e}")
    
    async def extract_referee_timeline_scholarone(self, page: Page, manuscript_id: str) -> List[RefereeTimeline]:
        """Extract referee timelines from ScholarOne journals (MF/MOR)"""
        timelines = []
        
        try:
            # Navigate to referee details
            detail_url = f"{self.base_url}/Reviewer/Manuscripts_Details_Popup.aspx?MGID={manuscript_id}"
            await page.goto(detail_url)
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find reviewer sections
            reviewer_sections = soup.find_all('td', class_='detailsheaderbg')
            
            for section in reviewer_sections:
                if 'reviewer' in section.get_text().lower():
                    table = section.find_parent('table')
                    if table:
                        # Find the detailed reviewer table
                        detail_table = table.find_next_sibling('table')
                        if detail_table:
                            rows = detail_table.find_all('tr')[1:]
                            
                            for row in rows:
                                timeline = self._parse_scholarone_referee_row(row, manuscript_id)
                                if timeline:
                                    # Click on reviewer for more details
                                    reviewer_link = page.locator(f"a:has-text('{timeline.name}')")
                                    if await reviewer_link.is_visible():
                                        await reviewer_link.click()
                                        await page.wait_for_timeout(2000)
                                        
                                        # Extract detailed info
                                        detail_content = await page.content()
                                        self._extract_scholarone_referee_details(timeline, detail_content)
                                        
                                        # Download report
                                        await self._download_referee_report_scholarone(page, timeline, manuscript_id)
                                        
                                        # Go back
                                        await page.go_back()
                                        await page.wait_for_timeout(2000)
                                    
                                    timelines.append(timeline)
                                    
        except Exception as e:
            print(f"Error extracting ScholarOne referee timeline: {e}")
        
        return timelines
    
    def _parse_scholarone_referee_row(self, row, manuscript_id: str) -> Optional[RefereeTimeline]:
        """Parse ScholarOne referee row"""
        cells = row.find_all('td')
        if len(cells) < 4:
            return None
        
        try:
            # ScholarOne typically has: Name, Email, Status, Dates
            name = cells[0].get_text(strip=True)
            email = cells[1].get_text(strip=True)
            status = cells[2].get_text(strip=True)
            
            # Normalize name
            if ',' in name:
                parts = name.split(',', 1)
                name = f"{parts[1].strip()} {parts[0].strip()}"
            
            timeline = RefereeTimeline(
                name=name,
                email=email,
                manuscript_id=manuscript_id,
                journal_code=self.journal_code
            )
            
            # Parse dates from remaining cells
            for i in range(3, len(cells)):
                date_text = cells[i].get_text(strip=True)
                if date_text:
                    # Try to determine what type of date this is
                    if i == 3:  # Usually invited date
                        date = self._parse_date_string(date_text)
                        if date:
                            timeline.invited_date = date
                            timeline.add_event(RefereeEvent(RefereeEventType.INVITED, date))
                    elif i == 4:  # Usually response date
                        date = self._parse_date_string(date_text)
                        if date:
                            if 'accept' in status.lower():
                                timeline.accepted_date = date
                                timeline.add_event(RefereeEvent(RefereeEventType.ACCEPTED, date))
                            elif 'declin' in status.lower():
                                timeline.declined_date = date
                                timeline.add_event(RefereeEvent(RefereeEventType.DECLINED, date))
                    elif i == 5:  # Usually due date
                        date = self._parse_date_string(date_text)
                        if date:
                            timeline.due_date = date
                    elif i == 6:  # Usually submitted date
                        date = self._parse_date_string(date_text)
                        if date:
                            timeline.submitted_date = date
                            timeline.add_event(RefereeEvent(RefereeEventType.REPORT_SUBMITTED, date))
            
            return timeline
            
        except Exception as e:
            print(f"Error parsing ScholarOne referee row: {e}")
            return None
    
    def _extract_scholarone_referee_details(self, timeline: RefereeTimeline, content: str):
        """Extract detailed info from ScholarOne referee page"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for email history
        email_section = soup.find('div', {'class': 'email-history'}) or soup.find('table', string=re.compile('Email|Communication'))
        
        if email_section:
            # Count different types of emails
            invitation_count = len(re.findall(r'invitation|invite', str(email_section), re.IGNORECASE))
            reminder_count = len(re.findall(r'reminder|follow.?up', str(email_section), re.IGNORECASE))
            
            timeline.invitation_emails_sent = max(1, invitation_count)  # At least 1 invitation
            timeline.reminder_emails_sent = reminder_count
            timeline.total_emails_sent = invitation_count + reminder_count
        
        # Look for review quality/length info
        quality_info = soup.find('td', string=re.compile('Quality|Rating'))
        if quality_info:
            quality_text = quality_info.find_next_sibling('td')
            if quality_text:
                timeline.report_quality = quality_text.get_text(strip=True)
        
        # Extract report length if available
        length_info = soup.find('td', string=re.compile('Length|Words'))
        if length_info:
            length_text = length_info.find_next_sibling('td')
            if length_text:
                length_match = re.search(r'(\d+)', length_text.get_text())
                if length_match:
                    timeline.report_length = int(length_match.group(1))
    
    async def _download_referee_report_scholarone(self, page: Page, timeline: RefereeTimeline, manuscript_id: str):
        """Download referee report from ScholarOne"""
        try:
            # Look for download links
            download_links = await page.locator("a[href*='download'], a[href*='view'], a:has-text('Report')").all()
            
            for link in download_links:
                text = await link.text_content()
                if 'report' in text.lower() or 'review' in text.lower():
                    href = await link.get_attribute('href')
                    if href:
                        # Make URL absolute
                        if not href.startswith('http'):
                            href = f"{self.base_url}{href}"
                        
                        # Download report
                        filename = f"referee_report_{timeline.name.replace(' ', '_')}.pdf"
                        file_path = await self._download_document(href, manuscript_id, timeline.email, filename)
                        
                        if file_path:
                            timeline.report_pdf_path = file_path
                            break
                            
        except Exception as e:
            print(f"Error downloading ScholarOne referee report: {e}")
    
    async def _download_document(self, url: str, manuscript_id: str, referee_email: str, filename: str) -> Optional[str]:
        """Download a document"""
        try:
            # Create directory
            base_dir = Path.home() / '.editorial_scripts' / 'documents' / 'referee_reports' / self.journal_code / manuscript_id
            base_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = base_dir / filename
            
            # Download with aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        # Store in document storage
                        self.document_storage.store_document(
                            content,
                            self.journal_code,
                            manuscript_id,
                            f'referee_report_{referee_email}',
                            filename
                        )
                        
                        return str(file_path)
            
            return None
            
        except Exception as e:
            print(f"Error downloading document: {e}")
            return None
    
    async def download_all_manuscript_documents(self, page: Page, manuscript_id: str) -> Dict[str, List[str]]:
        """Download ALL available documents for a manuscript"""
        downloaded = {
            'manuscript_pdfs': [],
            'cover_letters': [],
            'referee_reports': [],
            'other_documents': []
        }
        
        try:
            # Get all download links
            all_links = await page.locator("a[href*='download'], a[href*='view'], a[href*='.pdf']").all()
            
            for link in all_links:
                text = (await link.text_content() or '').lower()
                href = await link.get_attribute('href')
                
                if not href:
                    continue
                
                # Make URL absolute
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"
                
                # Categorize and download
                if 'manuscript' in text or 'article' in text or 'paper' in text:
                    filename = f"manuscript_{manuscript_id}_{len(downloaded['manuscript_pdfs'])}.pdf"
                    path = await self._download_manuscript_document(href, manuscript_id, filename, 'manuscript')
                    if path:
                        downloaded['manuscript_pdfs'].append(path)
                
                elif 'cover' in text:
                    filename = f"cover_letter_{manuscript_id}.pdf"
                    path = await self._download_manuscript_document(href, manuscript_id, filename, 'cover_letter')
                    if path:
                        downloaded['cover_letters'].append(path)
                
                elif 'report' in text or 'review' in text or 'referee' in text:
                    filename = f"referee_report_{manuscript_id}_{len(downloaded['referee_reports'])}.pdf"
                    path = await self._download_manuscript_document(href, manuscript_id, filename, 'referee_report')
                    if path:
                        downloaded['referee_reports'].append(path)
                
                elif '.pdf' in href:
                    # Any other PDF
                    filename = f"document_{manuscript_id}_{len(downloaded['other_documents'])}.pdf"
                    path = await self._download_manuscript_document(href, manuscript_id, filename, 'other')
                    if path:
                        downloaded['other_documents'].append(path)
                        
        except Exception as e:
            print(f"Error downloading manuscript documents: {e}")
        
        return downloaded
    
    async def _download_manuscript_document(self, url: str, manuscript_id: str, filename: str, doc_type: str) -> Optional[str]:
        """Download a manuscript document"""
        try:
            base_dir = Path.home() / '.editorial_scripts' / 'documents' / 'manuscripts' / self.journal_code / manuscript_id
            base_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = base_dir / filename
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        # Store in document storage
                        self.document_storage.store_document(
                            content,
                            self.journal_code,
                            manuscript_id,
                            doc_type,
                            filename
                        )
                        
                        return str(file_path)
            
            return None
            
        except Exception as e:
            print(f"Error downloading {doc_type}: {e}")
            return None
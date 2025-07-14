"""
Journal of Optimization Theory and Applications (JOTA) Scraper
Email-based implementation using Gmail API and clean architecture
"""

import asyncio
import logging
import re
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.core.domain.models import (
    Manuscript, Review, Referee, Author, 
    ManuscriptStatus, RefereeStatus, ReviewQuality
)
from src.core.ports.journal_extractor import JournalExtractor
from src.core.ports.browser_pool import BrowserPool
from src.infrastructure.config import get_settings


class JOTAScraper(JournalExtractor):
    """JOTA journal scraper using Gmail API for email-based extraction"""
    
    def __init__(self, browser_pool: BrowserPool = None):
        # JOTA doesn't need browser pool as it's email-based
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "JOTA"
        self.base_url = "https://www.editorialmanager.com/jota/"
        
        # Gmail API setup
        self.gmail_service = None
        self.user_id = "me"
        
        # Email query patterns
        self.flagged_query = "is:starred subject:(JOTA)"
        self.weekly_overview_query = 'subject:"JOTA - Weekly Overview Of Your Assignments"'
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from JOTA emails"""
        try:
            await self._setup_gmail_service()
            
            # Fetch and parse emails
            email_data = await self._fetch_and_parse_emails()
            
            # Convert to manuscript objects
            manuscripts = await self._convert_to_manuscripts(email_data)
            
            self.logger.info(f"Successfully extracted {len(manuscripts)} manuscripts from JOTA emails")
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"Error extracting JOTA manuscripts: {e}")
            raise
    
    async def _setup_gmail_service(self) -> None:
        """Setup Gmail API service"""
        try:
            from ..services.gmail_service import get_gmail_service
            self.gmail_service = await get_gmail_service()
            self.logger.info("Gmail service setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up Gmail service: {e}")
            raise
    
    async def _fetch_and_parse_emails(self) -> Dict[str, Any]:
        """Fetch and parse all relevant JOTA emails"""
        # Fetch flagged emails (acceptance + invitation)
        flagged_msgs = await self._list_messages(self.flagged_query)
        flagged_data = []
        
        for msg in flagged_msgs:
            subject, body, date = await self._get_message(msg['id'])
            
            if "Reviewer has agreed to review" in subject:
                flagged_data.append(self._parse_acceptance_email(subject, body, date))
            elif "Reviewer Invitation for" in subject:
                flagged_data.append(self._parse_invitation_email(subject, body, date))
        
        # Fetch weekly overview emails
        weekly_msgs = await self._list_messages(self.weekly_overview_query)
        weekly_data = []
        
        for msg in weekly_msgs:
            subject, body, date = await self._get_message(msg['id'])
            weekly_data.append(self._parse_weekly_overview_email(subject, body, date))
        
        return {
            "flagged_emails": flagged_data,
            "weekly_overviews": weekly_data
        }
    
    async def _list_messages(self, query: str) -> List[Dict]:
        """List message IDs matching the query"""
        if not self.gmail_service:
            return []
        
        return await self.gmail_service.list_messages(query)
    
    async def _get_message(self, msg_id: str) -> tuple:
        """Fetch full message content and headers"""
        if not self.gmail_service:
            return "", "", None
        
        subject, body, date_str = await self.gmail_service.get_message(msg_id)
        
        # Convert date string back to datetime if available
        date = None
        if date_str:
            try:
                from datetime import datetime
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except Exception:
                pass
        
        return subject, body, date
    
    
    def _parse_acceptance_email(self, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse flagged acceptance email"""
        # Extract manuscript ID: "JOTA-D-24-00769R1"
        ms_id_match = re.search(r'JOTA-D-\d{2}-\d{5}R?\d*', subject)
        ms_id = ms_id_match.group(0) if ms_id_match else None
        
        # Extract referee name: "Olivier Menoukeu Pamen, Ph.D has agreed"
        referee_match = re.search(
            r"([A-Z][a-zA-Z\s\.\-']{2,}),?\s*(Ph\.D\.?|PhD|MD)?\s*has agreed", 
            body, re.IGNORECASE
        )
        referee_name = referee_match.group(1).strip() if referee_match else None
        
        return {
            "type": "acceptance",
            "manuscript_id": ms_id,
            "referee_name": referee_name,
            "date": date,
            "subject": subject,
            "body": body,
        }
    
    def _parse_invitation_email(self, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse flagged invitation email"""
        # Extract manuscript ID
        ms_id_match = re.search(r'JOTA-D-\d{2}-\d{5}R?\d*', subject + " " + body)
        ms_id = ms_id_match.group(0) if ms_id_match else None
        
        # Extract referee name: "Dear Prof. NAME," or "Dear Dr. NAME,"
        referee_match = re.search(r"Dear\s+(Prof\.|Dr\.|Mr\.|Ms\.)?\s*([A-Z][a-zA-Z\s\.\-']+),", body)
        referee_name = referee_match.group(2).strip() if referee_match else None
        
        # Extract title: 'for the article "TITLE"'
        title_match = re.search(r'for the article "(.+?)"', body, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None
        
        return {
            "type": "invitation",
            "manuscript_id": ms_id,
            "referee_name": referee_name,
            "title": title,
            "date": date,
            "subject": subject,
            "body": body,
        }
    
    def _parse_weekly_overview_email(self, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse weekly overview email with manuscript statuses"""
        # Pattern for manuscript entries:
        # JOTA-D-24-00769R1  submitted 288 days ago  Under Review (31 days) 1 Agreed ...
        # Title: Maximum principle of stochastic optimal control problems with model uncertainty
        # Authors: Tao Hao , Shandong University of Finance and Economics; ...
        
        ms_pattern = re.compile(
            r"(JOTA-D-\d{2}-\d{5}R?\d*)\s+submitted.*?Title:\s*(.+?)\s*Authors:\s*(.+?)(?=(JOTA-D-|$))",
            re.DOTALL
        )
        
        manuscripts = []
        for match in ms_pattern.finditer(body):
            ms_id = match.group(1).strip()
            title = match.group(2).strip().replace('\n', ' ').replace('\r', '')
            authors = match.group(3).strip().replace('\n', ' ').replace('\r', '')
            
            manuscripts.append({
                "manuscript_id": ms_id,
                "title": title,
                "authors": authors,
            })
        
        return {
            "type": "weekly_overview",
            "date": date,
            "subject": subject,
            "body": body,
            "manuscripts": manuscripts,
        }
    
    async def _convert_to_manuscripts(self, email_data: Dict[str, Any]) -> List[Manuscript]:
        """Convert email data to Manuscript domain objects"""
        manuscripts = {}
        
        # First, process weekly overview emails to get basic manuscript info
        for weekly_email in email_data['weekly_overviews']:
            for ms_data in weekly_email['manuscripts']:
                ms_id = ms_data['manuscript_id']
                
                if ms_id not in manuscripts:
                    # Parse authors
                    author_list = self._parse_authors(ms_data['authors'])
                    
                    manuscript = Manuscript(
                        journal_code=self.journal_code,
                        external_id=ms_id,
                        title=ms_data['title'],
                        authors=author_list,
                        submission_date=weekly_email['date'] or datetime.now(),
                        status=ManuscriptStatus.UNDER_REVIEW,
                        custom_metadata={
                            'platform': 'Email',
                            'source': 'weekly_overview'
                        }
                    )
                    manuscripts[ms_id] = manuscript
        
        # Then, process flagged emails to add referee information
        for flagged_email in email_data['flagged_emails']:
            ms_id = flagged_email['manuscript_id']
            
            if not ms_id:
                continue
            
            # Create manuscript if not exists (from invitation without weekly overview)
            if ms_id not in manuscripts:
                title = flagged_email.get('title', f"Manuscript {ms_id}")
                manuscript = Manuscript(
                    journal_code=self.journal_code,
                    external_id=ms_id,
                    title=title,
                    submission_date=flagged_email['date'] or datetime.now(),
                    status=ManuscriptStatus.UNDER_REVIEW,
                    custom_metadata={
                        'platform': 'Email',
                        'source': 'flagged_email'
                    }
                )
                manuscripts[ms_id] = manuscript
            
            manuscript = manuscripts[ms_id]
            
            # Add referee information
            if flagged_email['referee_name']:
                referee = Referee(
                    name=flagged_email['referee_name'],
                    email="",  # Email not available from JOTA emails
                    expertise_areas=[]
                )
                
                # Determine review status
                if flagged_email['type'] == 'acceptance':
                    status = RefereeStatus.ACCEPTED
                elif flagged_email['type'] == 'invitation':
                    status = RefereeStatus.INVITED
                else:
                    status = RefereeStatus.INVITED
                
                review = Review(
                    referee_id=referee.id,
                    manuscript_id=manuscript.id,
                    status=status,
                    invited_date=flagged_email['date'] or datetime.now(),
                    custom_metadata={
                        'email_type': flagged_email['type'],
                        'subject': flagged_email['subject']
                    }
                )
                
                manuscript.add_review(review)
        
        return list(manuscripts.values())
    
    def _parse_authors(self, authors_str: str) -> List[Author]:
        """Parse authors string into Author objects"""
        authors = []
        
        # Split by semicolon and clean up
        author_parts = [part.strip() for part in authors_str.split(';') if part.strip()]
        
        for author_part in author_parts:
            # Split name and affiliation by comma
            parts = [p.strip() for p in author_part.split(',')]
            if parts:
                name = parts[0]
                affiliation = ', '.join(parts[1:]) if len(parts) > 1 else None
                
                author = Author(
                    name=name,
                    affiliation=affiliation
                )
                authors.append(author)
        
        return authors
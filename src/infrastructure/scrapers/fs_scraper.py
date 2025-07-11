"""
Finance and Stochastics (FS) Journal Scraper
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

from ...core.domain.models import (
    Manuscript, Review, Referee, Author, 
    ManuscriptStatus, RefereeStatus, ReviewQuality
)
from ...core.ports.journal_extractor import JournalExtractor
from ...core.ports.browser_pool import BrowserPool
from ..config import get_settings


class FSScraper(JournalExtractor):
    """Finance and Stochastics journal scraper using Gmail API for email-based extraction"""
    
    def __init__(self, browser_pool: BrowserPool = None):
        # FS doesn't need browser pool as it's email-based
        self.browser_pool = browser_pool
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.journal_code = "FS"
        
        # Gmail API setup
        self.gmail_service = None
        self.user_id = "me"
        
        # Email query patterns for FS
        self.fs_query = "subject:(Finance and Stochastics) OR subject:(FS) OR from:(springer.com)"
        
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from FS emails"""
        try:
            await self._setup_gmail_service()
            
            # Fetch and parse emails
            email_data = await self._fetch_and_parse_emails()
            
            # Convert to manuscript objects
            manuscripts = await self._convert_to_manuscripts(email_data)
            
            self.logger.info(f"Successfully extracted {len(manuscripts)} manuscripts from FS emails")
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"Error extracting FS manuscripts: {e}")
            raise
    
    async def _setup_gmail_service(self) -> None:
        """Setup Gmail API service"""
        try:
            from ..services.gmail_service import get_gmail_service
            self.gmail_service = await get_gmail_service()
            self.logger.info("Gmail service setup completed for FS")
            
        except Exception as e:
            self.logger.error(f"Error setting up Gmail service: {e}")
            raise
    
    async def _fetch_and_parse_emails(self) -> List[Dict[str, Any]]:
        """Fetch and parse all relevant FS emails"""
        if not self.gmail_service:
            return []
        
        # Fetch FS-related emails
        fs_msgs = await self._list_messages(self.fs_query)
        parsed_emails = []
        
        for msg in fs_msgs:
            try:
                subject, body, date = await self._get_message(msg['id'])
                
                # Parse different types of FS emails
                if self._is_manuscript_email(subject, body):
                    email_data = self._parse_manuscript_email(subject, body, date)
                    if email_data:
                        parsed_emails.append(email_data)
                        
                elif self._is_referee_email(subject, body):
                    email_data = self._parse_referee_email(subject, body, date)
                    if email_data:
                        parsed_emails.append(email_data)
                        
            except Exception as e:
                self.logger.error(f"Error parsing FS email {msg['id']}: {e}")
                continue
        
        return parsed_emails
    
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
    
    
    def _is_manuscript_email(self, subject: str, body: str) -> bool:
        """Check if email contains manuscript information"""
        manuscript_keywords = [
            'manuscript', 'submission', 'paper', 'article',
            'Finance and Stochastics', 'FS-'
        ]
        
        text = (subject + " " + body).lower()
        return any(keyword.lower() in text for keyword in manuscript_keywords)
    
    def _is_referee_email(self, subject: str, body: str) -> bool:
        """Check if email contains referee information"""
        referee_keywords = [
            'referee', 'reviewer', 'review', 'invitation',
            'agree', 'accept', 'decline'
        ]
        
        text = (subject + " " + body).lower()
        return any(keyword.lower() in text for keyword in referee_keywords)
    
    def _parse_manuscript_email(self, subject: str, body: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Parse manuscript-related email"""
        try:
            # Extract manuscript ID (FS format may vary)
            ms_id_match = re.search(r'FS[-_]?\d{4}[-_]?\d{4,5}', subject + " " + body, re.IGNORECASE)
            ms_id = ms_id_match.group(0) if ms_id_match else None
            
            # Extract title
            title_patterns = [
                r'title[:\s]+(["\']?)([^"\'\n]+)\1',
                r'paper[:\s]+(["\']?)([^"\'\n]+)\1',
                r'manuscript[:\s]+(["\']?)([^"\'\n]+)\1'
            ]
            
            title = None
            for pattern in title_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    title = match.group(2).strip()
                    break
            
            # Extract authors
            authors = self._extract_authors_from_text(body)
            
            return {
                "type": "manuscript",
                "manuscript_id": ms_id,
                "title": title,
                "authors": authors,
                "date": date,
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing manuscript email: {e}")
            return None
    
    def _parse_referee_email(self, subject: str, body: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Parse referee-related email"""
        try:
            # Extract manuscript ID
            ms_id_match = re.search(r'FS[-_]?\d{4}[-_]?\d{4,5}', subject + " " + body, re.IGNORECASE)
            ms_id = ms_id_match.group(0) if ms_id_match else None
            
            # Extract referee name
            referee_patterns = [
                r'Dear\s+(Prof\.|Dr\.|Mr\.|Ms\.)?\s*([A-Z][a-zA-Z\s\.\-\']+),',
                r'([A-Z][a-zA-Z\s\.\-\']+)\s+has\s+(agreed|accepted|declined)',
                r'Referee[:\s]+([A-Z][a-zA-Z\s\.\-\']+)'
            ]
            
            referee_name = None
            for pattern in referee_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    # Take the last capturing group that contains the name
                    groups = match.groups()
                    referee_name = groups[-1].strip() if groups else None
                    break
            
            # Determine status
            status = "invited"
            if re.search(r'(agreed|accepted)', body, re.IGNORECASE):
                status = "accepted"
            elif re.search(r'declined', body, re.IGNORECASE):
                status = "declined"
            elif re.search(r'completed', body, re.IGNORECASE):
                status = "completed"
            
            return {
                "type": "referee",
                "manuscript_id": ms_id,
                "referee_name": referee_name,
                "status": status,
                "date": date,
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing referee email: {e}")
            return None
    
    def _extract_authors_from_text(self, text: str) -> List[str]:
        """Extract author names from email text"""
        # Look for author patterns
        author_patterns = [
            r'Authors?[:\s]+([^\n]+)',
            r'By[:\s]+([^\n]+)',
            r'Author\(s\)[:\s]+([^\n]+)'
        ]
        
        authors = []
        for pattern in author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author_text = match.group(1).strip()
                # Split by common separators
                author_list = re.split(r'[,;]|\sand\s', author_text)
                authors.extend([author.strip() for author in author_list if author.strip()])
                break
        
        return authors
    
    async def _convert_to_manuscripts(self, email_data: List[Dict[str, Any]]) -> List[Manuscript]:
        """Convert email data to Manuscript domain objects"""
        manuscripts = {}
        
        # Group emails by manuscript ID
        for email in email_data:
            ms_id = email.get('manuscript_id')
            if not ms_id:
                continue
            
            if ms_id not in manuscripts:
                # Create manuscript from first email
                title = email.get('title', f"FS Manuscript {ms_id}")
                authors = self._convert_authors(email.get('authors', []))
                
                manuscript = Manuscript(
                    journal_code=self.journal_code,
                    external_id=ms_id,
                    title=title,
                    authors=authors,
                    submission_date=email.get('date') or datetime.now(),
                    status=ManuscriptStatus.UNDER_REVIEW,
                    custom_metadata={
                        'platform': 'Email',
                        'source': 'gmail'
                    }
                )
                manuscripts[ms_id] = manuscript
            
            manuscript = manuscripts[ms_id]
            
            # Add referee information if this is a referee email
            if email.get('type') == 'referee' and email.get('referee_name'):
                referee = Referee(
                    name=email['referee_name'],
                    email="",  # Email not available from FS emails
                    expertise_areas=[]
                )
                
                # Map status
                status_map = {
                    'invited': RefereeStatus.INVITED,
                    'accepted': RefereeStatus.ACCEPTED,
                    'declined': RefereeStatus.DECLINED,
                    'completed': RefereeStatus.COMPLETED
                }
                
                status = status_map.get(email.get('status', 'invited'), RefereeStatus.INVITED)
                
                review = Review(
                    referee_id=referee.id,
                    manuscript_id=manuscript.id,
                    status=status,
                    invited_date=email.get('date') or datetime.now(),
                    custom_metadata={
                        'email_subject': email.get('subject', ''),
                        'source': 'gmail'
                    }
                )
                
                manuscript.add_review(review)
        
        return list(manuscripts.values())
    
    def _convert_authors(self, author_names: List[str]) -> List[Author]:
        """Convert author name strings to Author objects"""
        authors = []
        
        for name in author_names:
            if name and name.strip():
                author = Author(
                    name=name.strip(),
                    email=None,
                    affiliation=None
                )
                authors.append(author)
        
        return authors
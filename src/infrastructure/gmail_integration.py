"""
Gmail Integration for Referee Email Cross-Checking
Searches and analyzes referee-related emails
"""

import os
import re
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.core.referee_analytics import RefereeEvent, RefereeEventType, RefereeTimeline


class GmailRefereeTracker:
    """Track referee communications through Gmail"""
    
    # If modifying these scopes, delete the token file
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    # Common referee email patterns
    REFEREE_PATTERNS = {
        'invitation': [
            r'invitation.*review',
            r'referee.*invitation',
            r'review.*manuscript',
            r'invited.*referee',
            r'would you.*review'
        ],
        'reminder': [
            r'reminder.*review',
            r'review.*reminder',
            r'overdue.*review',
            r'pending.*review',
            r'follow.?up.*review'
        ],
        'acceptance': [
            r'agreed.*review',
            r'accepted.*review',
            r'will.*review',
            r'confirm.*review'
        ],
        'decline': [
            r'decline.*review',
            r'unable.*review',
            r'cannot.*review',
            r'unavailable.*review'
        ],
        'submission': [
            r'submitted.*review',
            r'completed.*review',
            r'review.*submitted',
            r'review.*complete'
        ]
    }
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        """Initialize Gmail tracker"""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def authenticate(self) -> bool:
        """Public authentication method for testing"""
        try:
            if self.service is None:
                self._authenticate()
            
            # Test the service with a simple call
            if self.service:
                # Try to get user profile to verify connection
                profile = self.service.users().getProfile(userId='me').execute()
                return profile is not None
            return False
        except Exception:
            return False
    
    def search_referee_emails(self, referee_email: str, manuscript_id: str, 
                            journal_code: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Search for emails related to a specific referee and manuscript"""
        try:
            # Build search query
            query_parts = [
                f'to:{referee_email} OR from:{referee_email}',
                f'("{manuscript_id}" OR "{journal_code}")'
            ]
            
            # Add date range if specified
            if date_range:
                start_date = date_range[0].strftime('%Y/%m/%d')
                end_date = date_range[1].strftime('%Y/%m/%d')
                query_parts.append(f'after:{start_date} before:{end_date}')
            
            query = ' '.join(query_parts)
            
            # Search emails
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get full message details
            email_data = []
            for msg in messages:
                msg_data = self._get_message_details(msg['id'])
                if msg_data:
                    email_data.append(msg_data)
            
            return email_data
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def _get_message_details(self, msg_id: str) -> Optional[Dict]:
        """Get details of a specific email message"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract body
            body = self._get_message_body(message['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            date = self._parse_email_date(date_str)
            
            return {
                'id': msg_id,
                'thread_id': message.get('threadId'),
                'subject': header_dict.get('Subject', ''),
                'from': header_dict.get('From', ''),
                'to': header_dict.get('To', ''),
                'date': date,
                'body': body,
                'snippet': message.get('snippet', '')
            }
            
        except HttpError as error:
            print(f'Error getting message {msg_id}: {error}')
            return None
    
    def _get_message_body(self, payload) -> str:
        """Extract body from email payload"""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        return body
    
    def _parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string"""
        try:
            # Remove timezone info for simplicity
            date_str = re.sub(r'\s*\([^)]*\)', '', date_str)
            date_str = re.sub(r'\s*[+-]\d{4}$', '', date_str)
            
            # Try common formats
            formats = [
                '%a, %d %b %Y %H:%M:%S',
                '%d %b %Y %H:%M:%S',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            return None
        except:
            return None
    
    def analyze_referee_timeline(self, emails: List[Dict], referee_email: str, 
                               manuscript_id: str) -> RefereeTimeline:
        """Analyze emails to build referee timeline"""
        timeline = RefereeTimeline(
            name=self._extract_name_from_emails(emails, referee_email),
            email=referee_email,
            manuscript_id=manuscript_id,
            journal_code=self._extract_journal_from_emails(emails)
        )
        
        # Sort emails by date
        emails.sort(key=lambda e: e['date'] if e['date'] else datetime.min)
        
        # Analyze each email
        for email in emails:
            event_type = self._classify_email(email)
            if event_type:
                event = RefereeEvent(
                    event_type=event_type,
                    date=email['date'],
                    details=email['snippet'],
                    email_subject=email['subject'],
                    email_id=email['id']
                )
                timeline.add_event(event)
                
                # Add thread ID
                if email['thread_id'] not in timeline.gmail_thread_ids:
                    timeline.gmail_thread_ids.append(email['thread_id'])
        
        timeline.gmail_verified = True
        return timeline
    
    def _classify_email(self, email: Dict) -> Optional[RefereeEventType]:
        """Classify email type based on content"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        content = f"{subject} {body}"
        
        # Check patterns
        for event_type, patterns in self.REFEREE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if event_type == 'invitation':
                        return RefereeEventType.INVITED
                    elif event_type == 'reminder':
                        return RefereeEventType.REMINDER_SENT
                    elif event_type == 'acceptance':
                        return RefereeEventType.ACCEPTED
                    elif event_type == 'decline':
                        return RefereeEventType.DECLINED
                    elif event_type == 'submission':
                        return RefereeEventType.REPORT_SUBMITTED
        
        return None
    
    def _extract_name_from_emails(self, emails: List[Dict], referee_email: str) -> str:
        """Extract referee name from email headers"""
        for email in emails:
            if referee_email in email.get('from', ''):
                # Extract name from "Name <email>" format
                match = re.match(r'^([^<]+)<', email['from'])
                if match:
                    return match.group(1).strip()
        
        # Fallback to email prefix
        return referee_email.split('@')[0]
    
    def _extract_journal_from_emails(self, emails: List[Dict]) -> str:
        """Extract journal code from emails"""
        journal_patterns = {
            'SICON': r'sicon|control',
            'SIFIN': r'sifin|finance',
            'MF': r'mathematical finance|matfin',
            'MOR': r'operations research|mor\b'
        }
        
        for email in emails:
            content = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            for journal, pattern in journal_patterns.items():
                if re.search(pattern, content, re.IGNORECASE):
                    return journal
        
        return 'UNKNOWN'
    
    def find_missing_referee_emails(self, scraped_referees: List[Dict], 
                                   date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Find referee emails in Gmail that weren't found by scraping"""
        # Build query for referee-related emails
        query_parts = [
            '(review OR referee OR manuscript)',
            '(invitation OR invited OR "would you" OR reminder)'
        ]
        
        if date_range:
            start_date = date_range[0].strftime('%Y/%m/%d')
            end_date = date_range[1].strftime('%Y/%m/%d')
            query_parts.append(f'after:{start_date} before:{end_date}')
        
        query = ' '.join(query_parts)
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            # Check each message for referee emails not in scraped list
            scraped_emails = {ref['email'] for ref in scraped_referees}
            missing_referees = []
            
            for msg in messages:
                msg_data = self._get_message_details(msg['id'])
                if msg_data:
                    # Extract email addresses from To field
                    to_emails = self._extract_emails_from_field(msg_data.get('to', ''))
                    
                    for email in to_emails:
                        if email not in scraped_emails and self._is_likely_referee_email(msg_data):
                            missing_referees.append({
                                'email': email,
                                'found_in_email': msg_data['subject'],
                                'date': msg_data['date'],
                                'thread_id': msg_data['thread_id']
                            })
                            scraped_emails.add(email)  # Avoid duplicates
            
            return missing_referees
            
        except HttpError as error:
            print(f'Error searching for missing referees: {error}')
            return []
    
    def _extract_emails_from_field(self, field: str) -> List[str]:
        """Extract email addresses from To/From/CC field"""
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', field)
        return [email.lower() for email in emails]
    
    def _is_likely_referee_email(self, email_data: Dict) -> bool:
        """Check if email is likely referee-related"""
        content = f"{email_data.get('subject', '')} {email_data.get('snippet', '')}".lower()
        
        referee_keywords = [
            'review', 'referee', 'manuscript', 'invitation',
            'paper', 'article', 'submission', 'journal'
        ]
        
        return any(keyword in content for keyword in referee_keywords)
    
    def search_emails(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Generic email search method for testing
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results to return
            
        Returns:
            List of email dictionaries
        """
        try:
            if not self.service:
                return []
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get details for each message
            emails = []
            for msg in messages:
                msg_details = self._get_message_details(msg['id'])
                if msg_details:
                    emails.append(msg_details)
            
            return emails
            
        except HttpError as error:
            print(f'Email search error: {error}')
            return []
    
    def list_labels(self) -> List[Dict]:
        """
        List all Gmail labels
        
        Returns:
            List of label dictionaries
        """
        try:
            if not self.service:
                return []
            
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])
            
        except HttpError as error:
            print(f'Label listing error: {error}')
            return []
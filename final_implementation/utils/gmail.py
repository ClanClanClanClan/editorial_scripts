"""
Gmail Integration - Final Implementation
Based on July 11 working code
"""

import os
import re
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailService:
    """Gmail service for email verification and reminder counting"""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """Initialize Gmail service"""
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service"""
        try:
            creds = None
            
            # Token file stores the user's access and refresh tokens
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail API service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gmail service: {e}")
            self.service = None
    
    def search_referee_emails(self, referee_name: str, referee_email: str, 
                            manuscript_id: str, submission_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for emails related to a specific referee and manuscript
        Based on July 11 working implementation
        """
        if not self.service:
            return {
                'emails_found': 0,
                'emails': [],
                'invitation_date': None,
                'reminder_count': 0,
                'verification_status': 'gmail_unavailable'
            }
        
        try:
            # Parse submission date for time window
            if submission_date:
                submission_dt = self._parse_date(submission_date)
                if submission_dt:
                    # Search from 1 month before submission to now
                    start_date = submission_dt - timedelta(days=30)
                    after_date = start_date.strftime('%Y/%m/%d')
                else:
                    after_date = None
            else:
                after_date = None
            
            # Build search queries - must include manuscript ID
            search_queries = []
            
            # Email-based queries
            if referee_email:
                search_queries.extend([
                    f'to:{referee_email} "{manuscript_id}"',
                    f'from:{referee_email} "{manuscript_id}"',
                    f'to:{referee_email} subject:"{manuscript_id}"',
                    f'from:{referee_email} subject:"{manuscript_id}"',
                ])
            
            # Name-based queries
            search_queries.extend([
                f'"{referee_name}" "{manuscript_id}"',
                f'subject:"{manuscript_id}" "{referee_name}"',
                f'subject:"review" "{manuscript_id}" "{referee_name}"',
                f'subject:"referee" "{manuscript_id}" "{referee_name}"',
            ])
            
            # Add date filter
            if after_date:
                search_queries = [f'{q} after:{after_date}' for q in search_queries]
            
            all_emails = []
            invitation_date = None
            reminder_count = 0
            
            for query in search_queries:
                try:
                    results = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=20
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    for message in messages:
                        try:
                            # Get message details
                            msg = self.service.users().messages().get(
                                userId='me',
                                id=message['id'],
                                format='full'
                            ).execute()
                            
                            headers = msg['payload'].get('headers', [])
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                            from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
                            to_header = next((h['value'] for h in headers if h['name'] == 'To'), '')
                            snippet = msg.get('snippet', '')
                            
                            # Verify manuscript ID is in the email
                            if manuscript_id not in subject and manuscript_id not in snippet:
                                continue
                            
                            # Categorize email type
                            subject_lower = subject.lower()
                            email_type = 'other'
                            
                            if any(word in subject_lower for word in ['invitation', 'invite', 'review request']):
                                email_type = 'invitation'
                                if not invitation_date:
                                    invitation_date = date
                            elif 'accept' in subject_lower:
                                email_type = 'acceptance'
                            elif 'decline' in subject_lower or 'unable' in subject_lower:
                                email_type = 'decline'
                            elif 'reminder' in subject_lower or 'review pending' in subject_lower:
                                email_type = 'reminder'
                                reminder_count += 1
                            elif 'report' in subject_lower or 'review' in subject_lower:
                                email_type = 'report'
                            
                            email_data = {
                                'id': message['id'],
                                'subject': subject,
                                'date': date,
                                'from': from_header,
                                'to': to_header,
                                'type': email_type,
                                'snippet': snippet[:200]
                            }
                            
                            all_emails.append(email_data)
                            
                        except Exception as e:
                            logger.debug(f"Error processing message: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error with query {query}: {e}")
                    continue
            
            # Remove duplicates
            unique_emails = []
            seen_ids = set()
            for email in all_emails:
                if email['id'] not in seen_ids:
                    unique_emails.append(email)
                    seen_ids.add(email['id'])
            
            # Sort by date
            unique_emails.sort(key=lambda x: self._parse_date(x['date']) or datetime.min)
            
            # Build email type summary
            email_types = {}
            for email in unique_emails:
                email_type = email['type']
                if email_type not in email_types:
                    email_types[email_type] = 0
                email_types[email_type] += 1
            
            verification_status = 'verified' if unique_emails else 'not_found'
            
            return {
                'emails_found': len(unique_emails),
                'emails': unique_emails,
                'email_types': email_types,
                'invitation_date': invitation_date,
                'reminder_count': reminder_count,
                'verification_status': verification_status,
                'email_subjects': [
                    {
                        'subject': email['subject'],
                        'date': email['date'],
                        'type': email['type']
                    }
                    for email in unique_emails[:10]  # First 10 for summary
                ]
            }
            
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return {
                'emails_found': 0,
                'emails': [],
                'invitation_date': None,
                'reminder_count': 0,
                'verification_status': 'error',
                'error': str(e)
            }
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None
        
        # Common date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%b %d, %Y',
            '%d %b %Y',
            '%B %d, %Y',
            '%d %B %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # Gmail date format
        try:
            # Remove timezone and day name
            clean_date = re.sub(r'^[A-Za-z]+,\s*', '', date_str)
            clean_date = re.sub(r'\s*\([^)]+\)$', '', clean_date)
            clean_date = re.sub(r'\s*[+-]\d{4}$', '', clean_date)
            
            return datetime.strptime(clean_date.strip(), '%d %b %Y %H:%M:%S')
        except:
            pass
        
        return None
    
    def count_reminders(self, referee_email: str, manuscript_id: str) -> int:
        """Count reminder emails sent to a referee for a specific manuscript"""
        if not self.service or not referee_email:
            return 0
        
        try:
            # Search for reminder emails
            query = f'to:{referee_email} "{manuscript_id}" (subject:reminder OR subject:"review pending")'
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            return len(results.get('messages', []))
            
        except Exception as e:
            logger.error(f"Error counting reminders: {e}")
            return 0
"""
Gmail API Service for email-based scrapers
Handles OAuth2 authentication and email access
"""

import os
import pickle
import base64
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from email.utils import parsedate_to_datetime

from ..config import get_settings


class GmailService:
    """Gmail API service with OAuth2 authentication"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.settings = get_settings()
        self.service = None
        self.credentials = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2"""
        try:
            credentials_path = Path(self.settings.gmail_credentials_path or "credentials.json")
            token_path = Path(self.settings.gmail_token_path or "token.pickle")
            
            # Check if we have stored credentials
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # If credentials don't exist or are invalid, refresh or create new ones
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # Refresh expired credentials
                    self.credentials.refresh(Request())
                else:
                    # Create new credentials
                    if not credentials_path.exists():
                        raise FileNotFoundError(f"Gmail credentials file not found: {credentials_path}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            return True
            
        except Exception as e:
            print(f"Gmail authentication failed: {e}")
            return False
    
    async def list_messages(self, query: str, max_results: int = 100) -> List[Dict]:
        """List messages matching the query"""
        if not self.service:
            if not await self.authenticate():
                return []
        
        try:
            messages = []
            request = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            )
            
            while request is not None:
                response = request.execute()
                msgs = response.get('messages', [])
                messages.extend(msgs)
                request = self.service.users().messages().list_next(request, response)
                
                # Prevent infinite loops
                if len(messages) >= max_results:
                    break
            
            return messages
            
        except Exception as e:
            print(f"Error listing messages: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Tuple[str, str, Optional[str]]:
        """Get message content by ID"""
        if not self.service:
            if not await self.authenticate():
                return "", "", None
        
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract headers
            subject = self._get_header(headers, 'Subject')
            date_str = self._get_header(headers, 'Date')
            
            # Parse date
            date = None
            try:
                if date_str:
                    date = parsedate_to_datetime(date_str).isoformat()
            except Exception:
                pass
            
            # Extract body
            body = self._extract_body(payload)
            
            return subject, body, date
            
        except Exception as e:
            print(f"Error getting message {message_id}: {e}")
            return "", "", None
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ""
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            # Handle single part messages
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    async def search_emails(self, journal_code: str, email_type: str = "all") -> List[Dict]:
        """Search for journal-specific emails"""
        queries = {
            "JOTA": {
                "flagged": "is:starred subject:(JOTA)",
                "weekly": 'subject:"JOTA - Weekly Overview Of Your Assignments"',
                "all": "subject:(JOTA) OR from:(editorialmanager.com)"
            },
            "FS": {
                "all": "subject:(Finance and Stochastics) OR subject:(FS) OR from:(springer.com)"
            }
        }
        
        journal_queries = queries.get(journal_code, {})
        query = journal_queries.get(email_type, journal_queries.get("all", f"subject:({journal_code})"))
        
        if query:
            return await self.list_messages(query)
        return []


# Global service instance
_gmail_service = None

async def get_gmail_service() -> GmailService:
    """Get or create Gmail service instance"""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
        await _gmail_service.authenticate()
    return _gmail_service
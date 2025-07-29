#!/usr/bin/env python3
"""
Working Gmail Utilities for SICON Email Timeline Crosschecking
Based on existing editorial_scripts Gmail integration
"""

import os
import re
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow  
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class WorkingGmailService:
    """Working Gmail service for SICON email timeline crosschecking"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.service = None
        self.credentials = None
        
    def setup_service(self) -> bool:
        """Setup Gmail service with existing credentials"""
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API libraries not available")
            return False
            
        try:
            # Check for existing credentials
            creds = self._load_credentials()
            if not creds:
                logger.error("No Gmail credentials found")
                return False
                
            # Build service
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Gmail service: {e}")
            return False
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load Gmail credentials from various locations"""
        # Check common credential locations
        credential_paths = [
            "config/gmail_token.json",
            "config/token.json",
            "scripts/setup/token.json",
            "token.json",
            "gmail_token.json",
            os.path.expanduser("~/.config/editorial_scripts/gmail_token.json"),
            os.path.expanduser("~/.gmail_token.json")
        ]
        
        for path in credential_paths:
            if os.path.exists(path):
                try:
                    creds = Credentials.from_authorized_user_file(path, self.SCOPES)
                    logger.info(f"Loaded credentials from: {path}")
                    return creds
                except Exception as e:
                    logger.warning(f"Failed to load credentials from {path}: {e}")
                    continue
        
        # Try to create credentials if credentials.json exists
        credentials_json_paths = [
            "config/credentials.json",
            "config/gmail_credentials.json",
            "scripts/setup/credentials.json",
            "credentials.json",
            os.path.expanduser("~/.config/editorial_scripts/credentials.json")
        ]
        
        for path in credentials_json_paths:
            if os.path.exists(path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    # Save for future use
                    with open("gmail_token.json", 'w') as token:
                        token.write(creds.to_json())
                    
                    logger.info(f"Created new token from: {path}")
                    return creds
                except Exception as e:
                    logger.warning(f"Failed to create credentials from {path}: {e}")
                    continue
        
        return None
    
    def search_sicon_emails(self, manuscript_id: str, days_back: int = 365) -> List[Dict]:
        """Search for SICON emails related to manuscript"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return []
        
        try:
            # Build search queries for SICON emails
            queries = [
                f'subject:{manuscript_id}',
                f'subject:SICON {manuscript_id}',
                f'subject:"SIAM Journal" {manuscript_id}',
                f'body:{manuscript_id}',
                f'(subject:referee OR subject:reviewer) {manuscript_id}',
                f'(subject:invitation OR subject:accepted OR subject:declined) {manuscript_id}',
                f'from:sicon.siam.org {manuscript_id}',
                f'from:@siam.org {manuscript_id}',
            ]
            
            all_emails = []
            seen_ids = set()
            
            for query in queries:
                logger.info(f"Searching: {query}")
                
                try:
                    response = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=100
                    ).execute()
                    
                    messages = response.get('messages', [])
                    logger.info(f"  Found {len(messages)} messages")
                    
                    for msg in messages:
                        if msg['id'] in seen_ids:
                            continue
                            
                        try:
                            email_data = self._get_email_details(msg['id'])
                            if email_data and self._is_sicon_relevant(email_data, manuscript_id):
                                all_emails.append(email_data)
                                seen_ids.add(msg['id'])
                                
                        except Exception as e:
                            logger.warning(f"Error processing message {msg['id']}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error with query '{query}': {e}")
                    
            logger.info(f"Found {len(all_emails)} relevant SICON emails for {manuscript_id}")
            return all_emails
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed email information"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            payload = message.get('payload', {})
            
            for header in payload.get('headers', []):
                name = header.get('name', '').lower()
                if name in ['subject', 'from', 'to', 'date', 'cc']:
                    headers[name] = header.get('value', '')
            
            # Extract body
            body = self._extract_body(payload)
            
            # Parse date
            date_str = headers.get('date', '')
            parsed_date = self._parse_date(date_str)
            
            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': headers.get('subject', ''),
                'from': headers.get('from', ''),
                'to': headers.get('to', ''),
                'cc': headers.get('cc', ''),
                'date': parsed_date,
                'body': body,
                'raw_date': date_str
            }
            
        except Exception as e:
            logger.error(f"Error getting email details: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body text"""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        try:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
                        except:
                            continue
        else:
            data = payload.get('body', {}).get('data', '')
            if data:
                try:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                except:
                    pass
        
        return body
    
    def _parse_date(self, date_str: str) -> str:
        """Parse email date to ISO format"""
        if not date_str:
            return ''
        
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except:
            return date_str
    
    def _is_sicon_relevant(self, email: Dict, manuscript_id: str) -> bool:
        """Check if email is relevant to SICON manuscript"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        # Must contain manuscript ID
        if manuscript_id.lower() not in subject and manuscript_id.lower() not in body:
            return False
        
        # Must be SICON/SIAM related
        sicon_indicators = ['sicon', 'siam', 'control', 'optimization', 'referee', 'reviewer']
        return any(indicator in subject or indicator in body for indicator in sicon_indicators)


class SICONEmailTimelineAnalyzer:
    """Analyze SICON email timeline for referee interactions"""
    
    def __init__(self):
        self.gmail_service = WorkingGmailService()
        
    def analyze_manuscript_timeline(self, manuscript: Dict) -> Dict:
        """Analyze complete email timeline for manuscript"""
        if not self.gmail_service.setup_service():
            return {'error': 'Gmail service not available'}
        
        manuscript_id = manuscript.get('id', '')
        logger.info(f"Analyzing email timeline for {manuscript_id}")
        
        # Get all emails for this manuscript
        emails = self.gmail_service.search_sicon_emails(manuscript_id)
        
        if not emails:
            return {'error': 'No emails found', 'manuscript_id': manuscript_id}
        
        # Analyze timeline
        timeline = self._analyze_email_timeline(emails, manuscript)
        
        # Enhance referee data
        enhanced_referees = self._enhance_referee_data(manuscript, timeline)
        
        return {
            'manuscript_id': manuscript_id,
            'total_emails': len(emails),
            'timeline': timeline,
            'enhanced_referees': enhanced_referees,
            'analysis_date': datetime.now().isoformat()
        }
    
    def _analyze_email_timeline(self, emails: List[Dict], manuscript: Dict) -> Dict:
        """Analyze email timeline for patterns"""
        timeline = {
            'invitations': [],
            'responses': [],
            'reminders': [],
            'reports': []
        }
        
        for email in emails:
            category = self._categorize_email(email)
            if category:
                timeline[category].append({
                    'date': email.get('date', ''),
                    'subject': email.get('subject', ''),
                    'from': email.get('from', ''),
                    'to': email.get('to', ''),
                    'referee_info': self._extract_referee_from_email(email)
                })
        
        # Sort by date
        for category in timeline:
            timeline[category].sort(key=lambda x: x['date'])
        
        return timeline
    
    def _categorize_email(self, email: Dict) -> Optional[str]:
        """Categorize email type"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        if any(term in subject or term in body for term in ['invitation', 'invite', 'request to review']):
            return 'invitations'
        elif any(term in subject or term in body for term in ['accepted', 'declined', 'agreed', 'unable']):
            return 'responses'
        elif any(term in subject or term in body for term in ['reminder', 'overdue', 'follow-up']):
            return 'reminders'
        elif any(term in subject or term in body for term in ['report', 'review submitted']):
            return 'reports'
        
        return None
    
    def _extract_referee_from_email(self, email: Dict) -> Dict:
        """Extract referee information from email"""
        to_field = email.get('to', '')
        
        # Extract email address
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', to_field)
        referee_email = email_match.group(0) if email_match else ''
        
        # Extract name
        name = ''
        if '"' in to_field:
            name_match = re.search(r'"([^"]+)"', to_field)
            if name_match:
                name = name_match.group(1)
        elif '<' in to_field:
            name = to_field.split('<')[0].strip()
        
        return {
            'name': name,
            'email': referee_email
        }
    
    def _enhance_referee_data(self, manuscript: Dict, timeline: Dict) -> List[Dict]:
        """Enhance referee data with email timeline"""
        enhanced_referees = []
        
        # Get all referees from manuscript
        all_referees = (
            manuscript.get('declined_referees', []) + 
            manuscript.get('accepted_referees', [])
        )
        
        for referee in all_referees:
            enhanced_ref = referee.copy()
            
            # Find relevant emails for this referee
            referee_emails = self._find_referee_emails(referee, timeline)
            
            # Add timeline data
            enhanced_ref['email_timeline'] = referee_emails
            
            # Calculate response metrics
            if referee_emails.get('invitation') and referee_emails.get('response'):
                enhanced_ref['email_response_time'] = self._calculate_response_time(
                    referee_emails['invitation']['date'],
                    referee_emails['response']['date']
                )
            
            enhanced_referees.append(enhanced_ref)
        
        return enhanced_referees
    
    def _find_referee_emails(self, referee: Dict, timeline: Dict) -> Dict:
        """Find emails related to specific referee"""
        referee_name = referee.get('name', '').lower()
        referee_email = referee.get('email', '').lower()
        
        referee_emails = {
            'invitation': None,
            'response': None,
            'reminders': []
        }
        
        # Search in each category
        for category, emails in timeline.items():
            for email in emails:
                referee_info = email.get('referee_info', {})
                email_name = referee_info.get('name', '').lower()
                email_addr = referee_info.get('email', '').lower()
                
                # Check if this email involves the referee
                if (referee_email and referee_email == email_addr) or \
                   (referee_name and referee_name in email_name):
                    
                    if category == 'invitations' and not referee_emails['invitation']:
                        referee_emails['invitation'] = email
                    elif category == 'responses' and not referee_emails['response']:
                        referee_emails['response'] = email
                    elif category == 'reminders':
                        referee_emails['reminders'].append(email)
        
        return referee_emails
    
    def _calculate_response_time(self, invitation_date: str, response_date: str) -> Optional[int]:
        """Calculate response time in days"""
        try:
            inv_dt = datetime.fromisoformat(invitation_date.replace('Z', '+00:00'))
            resp_dt = datetime.fromisoformat(response_date.replace('Z', '+00:00'))
            return (resp_dt - inv_dt).days
        except:
            return None


def deploy_sicon_email_timeline(manuscript_file: str) -> str:
    """Deploy SICON email timeline crosschecking"""
    logger.info("🚀 Deploying SICON Email Timeline Crosschecking")
    
    # Load manuscript data
    with open(manuscript_file, 'r') as f:
        manuscripts = json.load(f)
    
    analyzer = SICONEmailTimelineAnalyzer()
    
    enhanced_manuscripts = []
    
    for manuscript in manuscripts:
        ms_id = manuscript.get('id', '')
        logger.info(f"📧 Processing {ms_id}")
        
        # Analyze email timeline
        timeline_result = analyzer.analyze_manuscript_timeline(manuscript)
        
        # Enhance manuscript with timeline data
        enhanced_ms = manuscript.copy()
        enhanced_ms['email_timeline_analysis'] = timeline_result
        
        enhanced_manuscripts.append(enhanced_ms)
        
        # Rate limiting
        time.sleep(1)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"sicon_email_timeline_deployed_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(enhanced_manuscripts, f, indent=2)
    
    logger.info(f"✅ Email timeline deployment complete: {output_file}")
    return output_file


if __name__ == "__main__":
    # Test the system
    input_file = "scripts/sicon/sicon_extraction_20250715_134149.json"
    output_file = deploy_sicon_email_timeline(input_file)
    print(f"✅ SICON Email Timeline Deployed: {output_file}")
#!/usr/bin/env python3
"""
FS EXTRACTOR - EMAIL-BASED WORKFLOW
====================================

Production-ready extractor for Finance and Stochastics journal.
Uses Gmail API to extract manuscripts from email notifications.

Authentication: Gmail API OAuth
Platform: Email-based (Gmail)
"""

import os
import sys
import json
import re
import base64
from pathlib import Path
from datetime import datetime, timedelta
import traceback
from typing import Optional, Dict, List, Any

# Add cache integration
sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin

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
    print("⚠️ Gmail API not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class ComprehensiveFSExtractor(CachedExtractorMixin):
    """Email-based extractor for Finance and Stochastics journal."""
    
    def __init__(self):
        self.init_cached_extractor("FS")
        
        # Gmail API scopes
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        
        # Extraction state
        self.manuscripts = []
        self.service = None
        
        # Email patterns for FS
        self.email_patterns = {
            'new_submission': 'new submission.*finance.*stochastics',
            'revision_request': 'revision requested.*finance.*stochastics',
            'review_invitation': 'invitation to review.*finance.*stochastics',
            'review_submitted': 'review submitted.*finance.*stochastics',
            'decision_made': 'decision.*finance.*stochastics',
            'manuscript_id': r'(?:FS|FSTO|fs)[-\s]?(\d{4,})',
            'title_pattern': r'Title:\s*([^\n]+)',
            'author_pattern': r'Author(?:s)?:\s*([^\n]+)',
            'status_pattern': r'Status:\s*([^\n]+)'
        }
        
        if not GMAIL_AVAILABLE:
            print("❌ Gmail API libraries not installed")
    
    def setup_gmail_service(self) -> bool:
        """Initialize Gmail API service."""
        if not GMAIL_AVAILABLE:
            print("❌ Gmail API not available")
            return False
            
        try:
            creds = None
            
            # Token file paths
            token_paths = [
                "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json",
                "config/gmail_token.json",
                str(Path.home() / ".gmail_token.json")
            ]
            
            # Load existing token
            for token_path in token_paths:
                if os.path.exists(token_path):
                    try:
                        creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                        print(f"✅ Loaded Gmail credentials from {token_path}")
                        break
                    except Exception as e:
                        print(f"⚠️ Failed to load {token_path}: {e}")
                        continue
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✅ Refreshed Gmail token")
                    # Save refreshed token
                    if token_paths and os.path.exists(token_paths[0]):
                        with open(token_paths[0], 'w') as token:
                            token.write(creds.to_json())
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    return False
            
            if not creds or not creds.valid:
                print("❌ No valid Gmail credentials found")
                print("💡 Run setup_gmail_auth.py to configure Gmail API")
                return False
            
            # Build service
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Test service
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"✅ Gmail API initialized for: {profile['emailAddress']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Gmail setup error: {e}")
            traceback.print_exc()
            return False
    
    def search_emails(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search Gmail for emails matching query."""
        emails = []
        
        try:
            # Search for emails
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg in messages:
                try:
                    # Get full message
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    
                    emails.append(message)
                    
                except Exception as e:
                    print(f"⚠️ Error fetching message {msg['id']}: {e}")
                    continue
            
            print(f"📧 Found {len(emails)} emails matching query")
            return emails
            
        except Exception as e:
            print(f"❌ Email search error: {e}")
            return []
    
    def get_email_attachments(self, email_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from email."""
        attachments = []
        
        def process_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachment = {
                        'filename': part['filename'],
                        'mime_type': part.get('mimeType', ''),
                        'size': part['body'].get('size', 0),
                        'attachment_id': part['body'].get('attachmentId', ''),
                        'part_id': part.get('partId', '')
                    }
                    attachments.append(attachment)
                if part.get('parts'):
                    process_parts(part['parts'])
        
        payload = email_message.get('payload', {})
        if payload.get('parts'):
            process_parts(payload['parts'])
        
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str, filename: str) -> Optional[str]:
        """Download attachment and save to disk."""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            # Save to downloads directory
            download_dir = Path("downloads/fs")
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean filename
            safe_filename = re.sub(r'[^\w\s.-]', '_', filename)
            file_path = download_dir / safe_filename
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"      📎 Downloaded: {safe_filename}")
            return str(file_path)
            
        except Exception as e:
            print(f"      ⚠️ Failed to download {filename}: {e}")
            return None
    
    def extract_title_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract title from PDF manuscript."""
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Try metadata first
                if reader.metadata and '/Title' in reader.metadata:
                    title = reader.metadata['/Title']
                    if title and len(title.strip()) > 10:
                        return title.strip()
                
                # Try first page text
                if reader.pages:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()
                    
                    # Split into lines and clean up
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # The title is usually one of the first non-empty lines
                    # Skip author names (contain @ or are very short) and dates
                    for line in lines[:15]:  # Check first 15 lines
                        # Skip if it's too short or looks like metadata
                        if len(line) < 15:
                            continue
                        
                        # Skip author lines (names with symbols or short lines)
                        if '@' in line or '∗' in line or '†' in line or '‡' in line:
                            continue
                        
                        # Skip dates (common date patterns)
                        if any(month in line for month in ['January', 'February', 'March', 'April', 'May', 'June', 
                                                           'July', 'August', 'September', 'October', 'November', 'December']):
                            continue
                        
                        # Skip if it's a number or version
                        if line.replace('.', '').replace(',', '').isdigit():
                            continue
                        
                        # Skip common headers
                        if any(skip in line.lower() for skip in ['abstract', 'keywords', 'page', 'volume', 'issue']):
                            continue
                        
                        # This is likely the title
                        return line
                        
        except ImportError:
            print("      ⚠️ PyPDF2 not installed - can't extract PDF titles")
        except Exception as e:
            print(f"      ⚠️ Failed to extract title from PDF: {e}")
        
        return None
    
    def build_manuscript_timeline(self, manuscript_id: str, emails: List[Dict[str, Any]], is_current: bool = False) -> Dict[str, Any]:
        """Build complete manuscript timeline from all related emails."""
        import re
        
        manuscript = {
            'id': manuscript_id,
            'title': 'Title not found',
            'is_current': is_current,
            'authors': [],
            'referees': {},  # Dict to track referee by name
            'timeline': [],  # Complete event timeline
            'manuscript_pdfs': [],
            'referee_reports': [],
            'editor': None,
            'status': 'Unknown',
            'submission_date': None,
            'decision_date': None,
            'all_attachments': []
        }
        
        # Sort emails by date
        emails_with_dates = []
        for email in emails:
            headers = email['payload'].get('headers', [])
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
            
            emails_with_dates.append({
                'email': email,
                'date': date,
                'subject': subject,
                'from': from_header
            })
        
        # Sort chronologically
        emails_with_dates.sort(key=lambda x: x['date'])
        
        # Process each email in chronological order
        for email_data in emails_with_dates:
            email = email_data['email']
            subject = email_data['subject']
            from_header = email_data['from']
            date = email_data['date']
            
            # Extract email body
            body = self.get_email_body(email.get('payload', {}))
            
            # Create timeline event
            event = {
                'date': date,
                'subject': subject,
                'from': from_header,
                'type': self.classify_email_type(subject, body),
                'details': {}
            }
            
            # Check if this is from an editor (first email with PDF is usually from editor)
            if 'possamai' not in from_header.lower() and not manuscript['editor']:
                # Likely an editor email
                if any(title in from_header.lower() for title in ['prof', 'dr', 'professor']):
                    manuscript['editor'] = from_header
                    event['details']['is_editor'] = True
            
            # Check if sender is a referee (e.g., sending report)
            sender_is_referee = False
            sender_name = None
            
            # Extract sender name and check if they're a referee
            if from_header and 'possamai' not in from_header.lower():
                # Skip known editors
                editor_patterns = ['Martin Schweizer', 'Giulia Di Nunno', 'Zhou Zhou', 'Cvitanic']
                is_editor = any(ed.lower() in from_header.lower() for ed in editor_patterns)
                
                if not is_editor:
                    # Check if this email contains referee-like content
                    referee_indicators = [
                        'report', 'review', 'referee', 'recommendation', 'comments',
                        'accept', 'decline', 'manuscript', 'paper'
                    ]
                    
                    # Extract name from sender
                    name_match = re.search(r'^([^<]+)<', from_header)
                    if name_match:
                        sender_name = name_match.group(1).strip()
                        # Check if sender might be a referee based on email content
                        if any(ind in subject.lower() or ind in body.lower()[:1000] for ind in referee_indicators):
                            sender_is_referee = True
                            
                            # Extract institution from email
                            email_match = re.search(r'<([^>]+)>', from_header)
                            institution = 'Unknown'
                            if email_match:
                                email_addr = email_match.group(1)
                                domain = email_addr.split('@')[1] if '@' in email_addr else ''
                                institution_map = {
                                    'cuhk.edu.hk': 'Chinese University of Hong Kong',
                                    'princeton.edu': 'Princeton University',
                                    'math.ethz.ch': 'ETH Zurich',
                                    'uio.no': 'University of Oslo',
                                    'caltech.edu': 'Caltech',
                                    'sydney.edu.au': 'University of Sydney',
                                    'gmail.com': 'Independent',
                                }
                                for domain_part, inst_name in institution_map.items():
                                    if domain_part in domain:
                                        institution = inst_name
                                        break
                                if institution == 'Unknown' and domain:
                                    institution = domain
                            
                            # Add sender as referee
                            if sender_name and sender_name not in manuscript['referees']:
                                manuscript['referees'][sender_name] = {
                                    'name': sender_name,
                                    'email': email_addr if email_match else '',
                                    'institution': institution,
                                    'invited_date': None,
                                    'response': None,
                                    'response_date': None,
                                    'report_submitted': False,
                                    'report_date': None,
                                    'recommendation': None
                                }
            
            # Extract referee information from email body
            if 'referee' in body.lower() or 'reviewer' in body.lower() or 'review' in body.lower():
                # Special handling for Editorial Digest emails
                if 'Editorial Digest' in subject:
                    # Parse referee assignments from digest format
                    import re
                    # Look for patterns like "Mastrogiacomo Elisa (ms FS-25-47-25) — Accepted"
                    # Note: The digest has typos like "47-25" for "4725"
                    digest_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\(ms\s+(FS-\d+-\d+-\d+)\)\s+—\s+(\w+)'
                    digest_matches = re.findall(digest_pattern, body)
                    
                    for name, ms_code, status in digest_matches:
                        # Normalize manuscript codes (FS-25-47-25 -> FS-25-4725)
                        ms_code_normalized = ms_code.replace('-', '')
                        if 'FS254725' in ms_code_normalized and manuscript_id == 'FS-25-4725':
                            # This referee is for FS-25-4725
                            if name not in manuscript['referees'] and name != 'Dylan' and 'Possamai' not in name:
                                manuscript['referees'][name] = {
                                    'name': name,
                                    'email': '',
                                    'institution': 'Unknown',
                                    'invited_date': None,
                                    'response': status if status in ['Accepted', 'Declined'] else None,
                                    'response_date': date if status == 'Accepted' else None,
                                    'report_submitted': False,
                                    'report_date': None,
                                    'recommendation': None
                                }
                                if status == 'Accepted':
                                    event['details']['referee_accepted'] = name
                        elif 'FS254733' in ms_code_normalized and manuscript_id == 'FS-25-4733':
                            # This referee is for FS-25-4733
                            if name not in manuscript['referees'] and name != 'Dylan' and 'Possamai' not in name:
                                manuscript['referees'][name] = {
                                    'name': name,
                                    'email': '',
                                    'institution': 'Unknown',
                                    'invited_date': None,
                                    'response': status if status in ['Accepted', 'Declined'] else None,
                                    'response_date': date if status == 'Accepted' else None,
                                    'report_submitted': False,
                                    'report_date': None,
                                    'recommendation': None
                                }
                                if status == 'Accepted':
                                    event['details']['referee_accepted'] = name
                        elif 'FS254680' in ms_code_normalized and manuscript_id == 'FS-25-4680':
                            # This referee is for FS-25-4680
                            if name not in manuscript['referees'] and name != 'Dylan' and 'Possamai' not in name:
                                manuscript['referees'][name] = {
                                    'name': name,
                                    'email': '',
                                    'institution': 'Unknown',
                                    'invited_date': None,
                                    'response': status if status in ['Accepted', 'Declined'] else None,
                                    'response_date': date if status == 'Accepted' else None,
                                    'report_submitted': False,
                                    'report_date': None,
                                    'recommendation': None
                                }
                                if status == 'Accepted':
                                    event['details']['referee_accepted'] = name
                
                # Regular referee extraction
                referees_found = self.extract_referees_from_email(body, subject)
                for referee in referees_found:
                    referee_name = referee['name']
                    if referee_name not in manuscript['referees']:
                        manuscript['referees'][referee_name] = {
                            'name': referee_name,
                            'email': referee.get('email', ''),
                            'institution': referee.get('institution', ''),
                            'invited_date': date if 'invit' in subject.lower() else None,
                            'response': None,
                            'response_date': None,
                            'report_submitted': False,
                            'report_date': None,
                            'recommendation': None
                        }
            
            # Update referee status based on email content for all known referees
            for referee_name in list(manuscript['referees'].keys()):
                referee_mentioned = referee_name.lower() in body.lower() or (sender_name and referee_name == sender_name)
                if referee_mentioned:
                    if 'accepted' in body.lower() or 'agreed' in body.lower():
                        manuscript['referees'][referee_name]['response'] = 'Accepted'
                        manuscript['referees'][referee_name]['response_date'] = date
                        event['details']['referee_accepted'] = referee_name
                    elif 'declined' in body.lower() or 'unable' in body.lower():
                        manuscript['referees'][referee_name]['response'] = 'Declined'
                        manuscript['referees'][referee_name]['response_date'] = date
                        event['details']['referee_declined'] = referee_name
                    elif 'submitted' in subject.lower() and 'report' in body.lower():
                        manuscript['referees'][referee_name]['report_submitted'] = True
                        manuscript['referees'][referee_name]['report_date'] = date
                        event['details']['report_submitted_by'] = referee_name
            
            # Process attachments
            attachments = self.get_email_attachments(email)
            for attachment in attachments:
                filename = attachment['filename']
                filename_lower = filename.lower()
                
                # Download important files
                if filename_lower.endswith('.pdf') or filename_lower.endswith('.docx'):
                    # Check if it's a manuscript PDF
                    is_manuscript = (
                        any(keyword in filename_lower for keyword in ['manuscript', 'paper', 'article', 'submission']) or
                        re.match(r'^fs-\d{2}-\d{3,4}', filename_lower)
                    )
                    
                    # Check if it's a referee report
                    is_report = any(keyword in filename_lower for keyword in ['report', 'review', 'referee', 'comments'])
                    
                    if is_manuscript and not is_report:
                        file_path = self.download_attachment(email['id'], attachment['attachment_id'], filename)
                        if file_path:
                            manuscript['manuscript_pdfs'].append(file_path)
                            event['details']['manuscript_pdf'] = filename
                            
                            # Try to extract title
                            if not manuscript['title'] or manuscript['title'] == 'Title not found':
                                if file_path.endswith('.pdf'):
                                    pdf_title = self.extract_title_from_pdf(file_path)
                                    if pdf_title:
                                        manuscript['title'] = pdf_title
                    
                    elif is_report:
                        file_path = self.download_attachment(email['id'], attachment['attachment_id'], filename)
                        if file_path:
                            # Try to match report to specific referee
                            report_referee = None
                            
                            # First check if sender is a known referee
                            if sender_name and sender_name in manuscript['referees']:
                                report_referee = sender_name
                                manuscript['referees'][sender_name]['report_submitted'] = True
                                manuscript['referees'][sender_name]['report_date'] = date
                            else:
                                # Try to match based on filename or email content
                                for referee_name in manuscript['referees'].keys():
                                    # Check if referee name is in filename or body
                                    if referee_name.split()[0].lower() in filename_lower or \
                                       referee_name.lower() in body.lower()[:500]:
                                        report_referee = referee_name
                                        manuscript['referees'][referee_name]['report_submitted'] = True
                                        manuscript['referees'][referee_name]['report_date'] = date
                                        break
                            
                            manuscript['referee_reports'].append({
                                'filename': filename,
                                'path': file_path,
                                'date': date,
                                'from': from_header,
                                'referee': report_referee or 'Unknown'
                            })
                            event['details']['report_file'] = filename
                            if report_referee:
                                event['details']['report_by'] = report_referee
                
                manuscript['all_attachments'].append({
                    'filename': filename,
                    'date': date,
                    'email_subject': subject
                })
            
            # Update manuscript status based on email
            if 'decision' in subject.lower():
                if 'accept' in body.lower():
                    manuscript['status'] = 'Accepted'
                    manuscript['decision_date'] = date
                elif 'reject' in body.lower():
                    manuscript['status'] = 'Rejected'  
                    manuscript['decision_date'] = date
                elif 'revision' in body.lower():
                    manuscript['status'] = 'Revision Requested'
            elif 'new submission' in subject.lower():
                manuscript['status'] = 'New Submission'
                manuscript['submission_date'] = date
            elif 'under review' in body.lower():
                manuscript['status'] = 'Under Review'
            
            # Add event to timeline
            manuscript['timeline'].append(event)
        
        # Convert referees dict to list
        manuscript['referees'] = list(manuscript['referees'].values())
        
        # Summary statistics
        manuscript['total_emails'] = len(emails_with_dates)
        manuscript['total_referees'] = len(manuscript['referees'])
        manuscript['referees_accepted'] = sum(1 for r in manuscript['referees'] if r['response'] == 'Accepted')
        manuscript['referees_declined'] = sum(1 for r in manuscript['referees'] if r['response'] == 'Declined')
        manuscript['reports_received'] = sum(1 for r in manuscript['referees'] if r['report_submitted'])
        
        return manuscript
    
    def classify_email_type(self, subject: str, body: str) -> str:
        """Classify the type of email based on content."""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        if 'invitation' in subject_lower and 'review' in subject_lower:
            return 'Referee Invitation'
        elif 'accepted to review' in body_lower or 'agreed to review' in body_lower:
            return 'Referee Acceptance'
        elif 'declined' in body_lower or 'unable to review' in body_lower:
            return 'Referee Decline'
        elif 'report' in subject_lower and 'submitted' in subject_lower:
            return 'Report Submission'
        elif 'decision' in subject_lower:
            return 'Editorial Decision'
        elif 'new submission' in subject_lower:
            return 'New Submission'
        elif 'revision' in subject_lower:
            return 'Revision Request'
        elif 'reminder' in subject_lower:
            return 'Reminder'
        else:
            return 'Correspondence'
    
    def extract_referees_from_email(self, body: str, subject: str) -> List[Dict[str, str]]:
        """Extract referee names and details from email body."""
        referees = []
        
        # Common patterns for referee mentions
        patterns = [
            r'(?:Prof(?:essor)?|Dr|Mr|Ms|Mrs)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'referee[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'reviewer[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+has\s+(?:accepted|agreed|declined)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+from\s+([A-Za-z\s]+University|[A-Za-z\s]+Institute)',
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0]
                    institution = match[1] if len(match) > 1 else ''
                else:
                    name = match
                    institution = ''
                
                # Clean up name
                name = name.strip()
                
                # Skip common false positives
                if name.lower() in ['finance and stochastics', 'dear', 'sincerely', 'best', 'regards']:
                    continue
                    
                # Look for email in nearby text
                email = ''
                email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                email_matches = re.findall(email_pattern, body[max(0, body.find(name)-100):body.find(name)+100])
                if email_matches:
                    email = email_matches[0]
                
                referees.append({
                    'name': name,
                    'email': email,
                    'institution': institution
                })
        
        return referees
    
    def extract_manuscript_from_email(self, email_message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract manuscript data from an email message."""
        try:
            # Get email metadata
            headers = email_message['payload'].get('headers', [])
            subject = ''
            sender = ''
            date = ''
            
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
                elif header['name'] == 'Date':
                    date = header['value']
            
            # Get email body
            body = self.get_email_body(email_message['payload'])
            
            if not body:
                return None
            
            # Extract manuscript ID
            manuscript_id = None
            id_match = re.search(self.email_patterns['manuscript_id'], subject + ' ' + body, re.IGNORECASE)
            if id_match:
                manuscript_id = f'FS-{id_match.group(1)}'
            else:
                manuscript_id = f'FS-{datetime.now().strftime("%Y%m%d")}-{email_message["id"][:6]}'
            
            # Extract title
            title = 'Title not found'
            title_match = re.search(self.email_patterns['title_pattern'], body, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
            
            # Extract authors
            authors = []
            author_match = re.search(self.email_patterns['author_pattern'], body, re.IGNORECASE)
            if author_match:
                author_names = author_match.group(1).strip()
                for name in re.split(r'[,;]', author_names):
                    name = name.strip()
                    if name:
                        authors.append({
                            'name': name,
                            'email': '',
                            'institution': ''
                        })
            
            # Determine status from email type
            status = 'Unknown'
            body_lower = body.lower()
            subject_lower = subject.lower()
            
            if 'new submission' in subject_lower or 'submitted' in body_lower:
                status = 'New Submission'
            elif 'revision' in subject_lower or 'revise' in body_lower:
                status = 'Revision Requested'
            elif 'review' in subject_lower and 'invitation' in subject_lower:
                status = 'Review Invitation'
            elif 'review' in subject_lower and 'submitted' in subject_lower:
                status = 'Review Submitted'
            elif 'accept' in subject_lower or 'accepted' in body_lower:
                status = 'Accepted'
            elif 'reject' in subject_lower or 'rejected' in body_lower:
                status = 'Rejected'
            elif 'decision' in subject_lower:
                status = 'Decision Made'
            
            # Get attachments
            attachments = self.get_email_attachments(email_message)
            
            # Try to get title from PDF attachments
            pdf_title = None
            manuscript_pdfs = []
            referee_reports = []
            
            for attachment in attachments:
                filename = attachment['filename']
                filename_lower = filename.lower()
                
                # Download important attachments
                if filename_lower.endswith('.pdf') or filename_lower.endswith('.docx'):
                    # Check if it's a manuscript PDF (by name or by ID pattern)
                    is_manuscript = (
                        any(keyword in filename_lower for keyword in ['manuscript', 'paper', 'article', 'submission']) or
                        re.match(r'^fs-\d{2}-\d{4}', filename_lower)  # Matches FS-XX-XXXX pattern
                    )
                    
                    # Check if it's a referee report
                    is_report = any(keyword in filename_lower for keyword in ['report', 'review', 'referee', 'comments'])
                    
                    # Manuscript PDFs
                    if is_manuscript and not is_report:
                        file_path = self.download_attachment(email_message['id'], attachment['attachment_id'], filename)
                        if file_path:
                            manuscript_pdfs.append(file_path)
                            if not pdf_title and file_path.endswith('.pdf'):
                                pdf_title = self.extract_title_from_pdf(file_path)
                    
                    # Referee reports
                    elif is_report:
                        file_path = self.download_attachment(email_message['id'], attachment['attachment_id'], filename)
                        if file_path:
                            referee_reports.append({
                                'filename': filename,
                                'path': file_path
                            })
            
            # Use PDF title if found
            if pdf_title:
                title = pdf_title
            
            # Build manuscript object
            manuscript = {
                'id': manuscript_id,
                'title': title,
                'status': status,
                'authors': authors,
                'journal': 'FS',
                'platform': 'Email',
                'email_subject': subject,
                'email_sender': sender,
                'email_date': date,
                'email_id': email_message['id'],
                'extracted_at': datetime.now().isoformat(),
                'referees': [],
                'submission_date': date,
                'attachments': attachments,
                'manuscript_pdfs': manuscript_pdfs,
                'referee_reports': referee_reports
            }
            
            # Extract referee information from email body
            referee_patterns = [
                r'Referee[:\s]+([A-Za-z\s]+?)(?:\n|$)',
                r'Reviewer[:\s]+([A-Za-z\s]+?)(?:\n|$)',
                r'(?:Referee|Reviewer)\s+(\d+)[:\s]+([A-Za-z\s]+?)(?:\n|$)',
                r'Assigned to[:\s]+([A-Za-z\s]+?)(?:\n|$)'
            ]
            
            referees_found = set()
            for pattern in referee_patterns:
                referee_matches = re.findall(pattern, body, re.IGNORECASE | re.MULTILINE)
                for match in referee_matches:
                    # Handle numbered referees
                    if isinstance(match, tuple) and len(match) == 2:
                        referee_name = match[1].strip()
                    else:
                        referee_name = match.strip() if isinstance(match, str) else match[0].strip()
                    
                    if referee_name and len(referee_name) > 2 and referee_name not in referees_found:
                        referees_found.add(referee_name)
                        manuscript['referees'].append({
                            'name': referee_name,
                            'email': '',
                            'status': 'Assigned',
                            'affiliation': '',
                            'report_available': len([r for r in referee_reports if referee_name.split()[0].lower() in r['filename'].lower()]) > 0
                        })
            
            # Parse referee decisions from body
            decision_patterns = [
                r'(?:Referee|Reviewer)\s+\d+[:\s]+(?:recommends?\s+)?(\w+)',
                r'Decision[:\s]+(\w+)',
                r'Recommendation[:\s]+(\w+)'
            ]
            
            for pattern in decision_patterns:
                decision_matches = re.findall(pattern, body, re.IGNORECASE)
                for decision in decision_matches:
                    decision_lower = decision.lower()
                    if 'accept' in decision_lower:
                        manuscript['referee_recommendation'] = 'Accept'
                    elif 'reject' in decision_lower:
                        manuscript['referee_recommendation'] = 'Reject'
                    elif 'revise' in decision_lower or 'revision' in decision_lower:
                        manuscript['referee_recommendation'] = 'Revise'
            
            return manuscript
            
        except Exception as e:
            print(f"⚠️ Error extracting from email: {e}")
            return None
    
    def get_email_body(self, payload) -> str:
        """Extract body text from email payload."""
        body = ""
        
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    elif part['mimeType'] == 'text/html' and not body:
                        # Use HTML if no plain text
                        data = part['body'].get('data', '')
                        if data:
                            html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            # Simple HTML stripping
                            body = re.sub('<[^<]+?>', '', html)
            elif payload.get('body', {}).get('data'):
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"⚠️ Error extracting email body: {e}")
        
        return body
    
    def extract_all(self) -> List[Dict[str, Any]]:
        """Main extraction method for email-based workflow."""
        print("🚀 FS EXTRACTION - COMPREHENSIVE EMAIL ANALYSIS")
        print("=" * 60)
        
        try:
            # Setup Gmail service
            if not self.setup_gmail_service():
                print("❌ Gmail service setup failed")
                return []
            
            # Step 1: Find current manuscripts (starred emails)
            print("\n📌 STEP 1: Finding current manuscripts (starred emails)")
            starred_query = 'is:starred (FS- OR FIST)'
            starred_emails = self.search_emails(starred_query, max_results=50)
            
            current_manuscript_ids = set()
            for email in starred_emails:
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                
                # Extract manuscript IDs from starred emails
                import re
                fs_match = re.search(r'FS-\d{2}-\d{3,4}', subject)
                if fs_match:
                    current_manuscript_ids.add(fs_match.group(0))
                    print(f"   ⭐ Current manuscript: {fs_match.group(0)}")
            
            # Step 2: Get ALL emails for each manuscript ID
            print(f"\n📚 STEP 2: Building complete timeline for {len(current_manuscript_ids)} current + historical manuscripts")
            
            # Also search for historical manuscripts
            historical_queries = [
                'subject:"FS-" -is:starred',
                'subject:"FIST" -is:starred'
            ]
            
            all_manuscript_ids = current_manuscript_ids.copy()
            
            for query in historical_queries:
                emails = self.search_emails(query, max_results=100)
                for email in emails:
                    headers = email['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    
                    fs_match = re.search(r'FS-\d{2}-\d{3,4}', subject)
                    if fs_match:
                        all_manuscript_ids.add(fs_match.group(0))
            
            print(f"   Found {len(all_manuscript_ids)} total unique manuscripts")
            
            # Step 3: For each manuscript, get COMPLETE email history
            manuscripts = {}
            
            total_manuscripts = len(all_manuscript_ids)
            for idx, manuscript_id in enumerate(sorted(all_manuscript_ids), 1):
                print(f"\n🔍 Processing {manuscript_id}... ({idx}/{total_manuscripts})")
                
                # Get ALL emails for this manuscript
                manuscript_query = f'"{manuscript_id}"'
                manuscript_emails = self.search_emails(manuscript_query, max_results=500)
                
                print(f"   📧 Found {len(manuscript_emails)} emails for {manuscript_id}")
                
                # Build comprehensive manuscript data
                manuscript = self.build_manuscript_timeline(manuscript_id, manuscript_emails, 
                                                           is_current=(manuscript_id in current_manuscript_ids))
                
                if manuscript:
                    manuscripts[manuscript_id] = manuscript
            
            self.manuscripts = list(manuscripts.values())
            
            # Sort by whether current and by date
            self.manuscripts.sort(key=lambda x: (not x['is_current'], x['submission_date'] or ''), reverse=True)
            
            print(f"\n📊 Extracted {len(self.manuscripts)} manuscripts with complete timelines")
            
            # Show summary
            if self.manuscripts:
                print("\n📋 MANUSCRIPT SUMMARY:")
                for ms in self.manuscripts:
                    status_icon = "⭐" if ms['is_current'] else "📄"
                    print(f"{status_icon} {ms['id']}: {ms['title'][:50]}...")
                    print(f"   📧 {ms['total_emails']} emails | 👥 {ms['total_referees']} referees")
                    print(f"   ✅ {ms['referees_accepted']} accepted | ❌ {ms['referees_declined']} declined | 📝 {ms['reports_received']} reports")
            
            return self.manuscripts
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    
    def save_results(self):
        """Save extraction results."""
        if not self.manuscripts:
            print("⚠️ No manuscripts to save")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save using cache system
        try:
            for manuscript in self.manuscripts:
                self.cache_manuscript(manuscript)
            print(f"💾 Cached {len(self.manuscripts)} manuscripts")
        except Exception as e:
            print(f"⚠️ Cache save error: {e}")
        
        # Save JSON file
        try:
            output_dir = Path("results/fs")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"fs_extraction_{timestamp}.json"
            
            extraction_data = {
                'journal': 'fs',
                'journal_name': 'Finance and Stochastics',
                'platform': 'Email (Gmail)',
                'extraction_time': timestamp,
                'manuscripts_count': len(self.manuscripts),
                'manuscripts': self.manuscripts
            }
            
            with open(output_file, 'w') as f:
                json.dump(extraction_data, f, indent=2, default=str)
                
            print(f"💾 Results saved: {output_file}")
            
        except Exception as e:
            print(f"⚠️ File save error: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        # No browser to close for email-based extractor
        print("🧹 Email extractor cleanup complete")
        
        # Clean up test cache if in test mode
        if hasattr(self, 'cache_manager') and hasattr(self.cache_manager, 'test_mode'):
            if self.cache_manager.test_mode:
                try:
                    import shutil
                    shutil.rmtree(self.cache_manager.cache_dir, ignore_errors=True)
                    print(f"🧹 Cleaned up test cache: {self.cache_manager.cache_dir}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not fully cleanup test cache: {e}")


def main():
    """Run FS email-based extractor."""
    extractor = ComprehensiveFSExtractor()
    
    try:
        manuscripts = extractor.extract_all()
        
        if manuscripts:
            extractor.save_results()
            
            print(f"\n📊 EXTRACTION SUMMARY:")
            print(f"Total manuscripts: {len(manuscripts)}")
            for i, ms in enumerate(manuscripts[:10]):  # Show first 10
                print(f"  {i+1}. {ms['id']}: {ms['title'][:50]}... [{ms['status']}]")
        else:
            print("❌ No manuscripts extracted")
            
    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        traceback.print_exc()
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    main()
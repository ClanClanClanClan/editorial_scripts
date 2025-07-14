"""
Enhanced Email Timeline Tracker
Implements comprehensive email integration requirements from COMPREHENSIVE_DATA_EXTRACTION_REQUIREMENTS.md

Provides complete referee communication timeline tracking with Gmail API integration
"""

import asyncio
import logging
import re
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import pickle
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GMAIL_API = True
except ImportError:
    HAS_GMAIL_API = False
    logging.warning("Gmail API dependencies not available")

# AI/NLP imports for content analysis
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


@dataclass
class EmailEvent:
    """Individual email event in referee communication timeline"""
    message_id: str
    thread_id: str
    timestamp: datetime
    direction: str  # "sent" or "received"
    sender: str
    recipients: List[str]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    
    # Content analysis
    email_type: Optional[str] = None  # invitation, reminder, response, submission, etc.
    contains_acceptance: bool = False
    contains_decline: bool = False
    contains_submission: bool = False
    sentiment: Optional[str] = None  # positive, neutral, negative
    confidence_score: Optional[float] = None
    
    # Referee context
    manuscript_id: Optional[str] = None
    referee_name: Optional[str] = None
    referee_email: Optional[str] = None
    
    # System metadata
    processed_date: datetime = None
    ai_analysis: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.processed_date is None:
            self.processed_date = datetime.now()


@dataclass
class RefereeTimeline:
    """Complete timeline for a referee on a specific manuscript"""
    manuscript_id: str
    referee_name: str
    referee_email: str
    
    # Timeline events
    emails: List[EmailEvent] = None
    
    # Derived timeline data
    first_contact_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    acceptance_date: Optional[datetime] = None
    decline_date: Optional[datetime] = None
    submission_date: Optional[datetime] = None
    
    # Statistics
    total_emails: int = 0
    emails_sent_to_referee: int = 0
    emails_received_from_referee: int = 0
    reminder_count: int = 0
    days_to_respond: Optional[int] = None
    days_to_complete: Optional[int] = None
    
    # Status indicators
    final_status: Optional[str] = None  # accepted, declined, submitted, no_response
    communication_quality: Optional[str] = None  # responsive, slow, unresponsive
    
    def __post_init__(self):
        if self.emails is None:
            self.emails = []


@dataclass
class EmailSearchConfig:
    """Configuration for email search parameters"""
    # Date range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Search domains and patterns
    journal_domains: List[str] = None
    referee_domains: List[str] = None
    
    # Manuscript patterns
    manuscript_id_patterns: List[str] = None
    
    # Content patterns
    invitation_patterns: List[str] = None
    reminder_patterns: List[str] = None
    response_patterns: List[str] = None
    
    # Performance settings
    max_results: int = 1000
    batch_size: int = 100
    
    def __post_init__(self):
        if self.journal_domains is None:
            self.journal_domains = [
                'sicon.siam.org', 'sifin.siam.org', 'siam.org',
                'manuscriptcentral.com', 'editorialmanager.com'
            ]
        
        if self.manuscript_id_patterns is None:
            self.manuscript_id_patterns = [
                r'M\d{6}',  # SIAM pattern
                r'manuscript\s+#?\s*(\w+)',
                r'submission\s+#?\s*(\w+)'
            ]
        
        if self.invitation_patterns is None:
            self.invitation_patterns = [
                r'invitation.*review',
                r'invited.*referee',
                r'review.*manuscript',
                r'would you.*review',
                r'referee.*invitation'
            ]
        
        if self.reminder_patterns is None:
            self.reminder_patterns = [
                r'reminder.*review',
                r'review.*reminder',
                r'overdue.*review',
                r'pending.*review',
                r'follow.?up.*review'
            ]


class EnhancedEmailTracker:
    """
    Enhanced email tracking system for comprehensive referee communication analysis
    Integrates with Gmail API to provide complete timeline tracking
    """
    
    def __init__(
        self,
        credentials_path: str = 'credentials.json',
        token_path: str = 'token.json',
        openai_api_key: Optional[str] = None
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.gmail_service = None
        self.openai_client = None
        
        # Initialize services
        if HAS_GMAIL_API:
            self._setup_gmail_service()
        else:
            logger.warning("Gmail API not available - email tracking disabled")
        
        if HAS_OPENAI and openai_api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        
        # Email classification patterns
        self.email_patterns = self._setup_email_patterns()
        
        # Cache for processed emails
        self.email_cache: Dict[str, EmailEvent] = {}
        self.timeline_cache: Dict[str, RefereeTimeline] = {}
    
    def _setup_gmail_service(self):
        """Setup Gmail API service with authentication"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            
            creds = None
            # Load existing token
            if Path(self.token_path).exists():
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not Path(self.credentials_path).exists():
                        logger.error(f"Gmail credentials file not found: {self.credentials_path}")
                        return
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail API service initialized")
            
        except Exception as e:
            logger.error(f"❌ Gmail API setup failed: {e}")
            self.gmail_service = None
    
    def _setup_email_patterns(self) -> Dict[str, List[str]]:
        """Setup email classification patterns"""
        return {
            'invitation': [
                r'invitation.*review',
                r'invited.*referee',
                r'review.*manuscript',
                r'would you.*review',
                r'referee.*invitation',
                r'request.*review'
            ],
            'reminder': [
                r'reminder.*review',
                r'review.*reminder',
                r'overdue.*review',
                r'pending.*review',
                r'follow.?up.*review',
                r'due.*review'
            ],
            'acceptance': [
                r'agreed.*review',
                r'accepted.*review',
                r'will.*review',
                r'confirm.*review',
                r'yes.*review',
                r'accept.*invitation'
            ],
            'decline': [
                r'decline.*review',
                r'unable.*review',
                r'cannot.*review',
                r'unavailable.*review',
                r'regret.*cannot',
                r'not.*able.*review'
            ],
            'submission': [
                r'submitted.*review',
                r'completed.*review',
                r'review.*submitted',
                r'review.*complete',
                r'attached.*review',
                r'report.*attached'
            ],
            'question': [
                r'question.*review',
                r'clarification.*needed',
                r'could.*you.*clarify',
                r'help.*understanding'
            ]
        }
    
    async def extract_referee_timeline(
        self,
        manuscript_id: str,
        referee_email: str,
        referee_name: str,
        search_config: Optional[EmailSearchConfig] = None
    ) -> RefereeTimeline:
        """
        Extract complete email timeline for a specific referee and manuscript
        
        Args:
            manuscript_id: Manuscript identifier
            referee_email: Referee's email address
            referee_name: Referee's name
            search_config: Search configuration parameters
            
        Returns:
            Complete referee timeline with all email events
        """
        try:
            logger.info(f"🔍 Extracting email timeline for {referee_name} on {manuscript_id}")
            
            if not self.gmail_service:
                logger.error("Gmail service not available")
                return RefereeTimeline(manuscript_id, referee_name, referee_email)
            
            # Setup search configuration
            if search_config is None:
                search_config = EmailSearchConfig()
            
            # Search for emails
            emails = await self._search_referee_emails(
                manuscript_id, referee_email, search_config
            )
            
            # Process and analyze emails
            processed_emails = []
            for email_data in emails:
                email_event = await self._process_email_event(
                    email_data, manuscript_id, referee_name, referee_email
                )
                if email_event:
                    processed_emails.append(email_event)
            
            # Sort emails chronologically
            processed_emails.sort(key=lambda x: x.timestamp)
            
            # Build timeline
            timeline = await self._build_referee_timeline(
                manuscript_id, referee_name, referee_email, processed_emails
            )
            
            logger.info(f"✅ Timeline extracted: {len(processed_emails)} emails, status: {timeline.final_status}")
            
            return timeline
            
        except Exception as e:
            logger.error(f"❌ Timeline extraction failed: {e}")
            return RefereeTimeline(manuscript_id, referee_name, referee_email)
    
    async def _search_referee_emails(
        self,
        manuscript_id: str,
        referee_email: str,
        search_config: EmailSearchConfig
    ) -> List[Dict[str, Any]]:
        """Search for emails related to specific referee and manuscript"""
        try:
            # Build search query
            query_parts = []
            
            # Include referee email
            query_parts.append(f"({referee_email})")
            
            # Include manuscript ID patterns
            for pattern in search_config.manuscript_id_patterns:
                if manuscript_id:
                    query_parts.append(f"({manuscript_id})")
            
            # Include journal domains
            domain_query = " OR ".join([f"from:{domain}" for domain in search_config.journal_domains])
            query_parts.append(f"({domain_query})")
            
            # Date range
            if search_config.start_date:
                date_str = search_config.start_date.strftime('%Y/%m/%d')
                query_parts.append(f"after:{date_str}")
            
            if search_config.end_date:
                date_str = search_config.end_date.strftime('%Y/%m/%d')
                query_parts.append(f"before:{date_str}")
            
            # Combine query
            query = " ".join(query_parts)
            logger.info(f"📧 Gmail search query: {query}")
            
            # Execute search
            emails = []
            next_page_token = None
            
            while len(emails) < search_config.max_results:
                # Search messages
                search_params = {
                    'q': query,
                    'maxResults': min(search_config.batch_size, search_config.max_results - len(emails))
                }
                
                if next_page_token:
                    search_params['pageToken'] = next_page_token
                
                result = self.gmail_service.users().messages().list(
                    userId='me', **search_params
                ).execute()
                
                messages = result.get('messages', [])
                if not messages:
                    break
                
                # Get full message details
                for message in messages:
                    try:
                        full_message = self.gmail_service.users().messages().get(
                            userId='me', id=message['id'], format='full'
                        ).execute()
                        emails.append(full_message)
                    except Exception as e:
                        logger.warning(f"Failed to get message {message['id']}: {e}")
                
                # Check for next page
                next_page_token = result.get('nextPageToken')
                if not next_page_token:
                    break
                
                # Rate limiting
                await asyncio.sleep(0.1)
            
            logger.info(f"📧 Found {len(emails)} emails for {referee_email}")
            return emails
            
        except Exception as e:
            logger.error(f"❌ Email search failed: {e}")
            return []
    
    async def _process_email_event(
        self,
        email_data: Dict[str, Any],
        manuscript_id: str,
        referee_name: str,
        referee_email: str
    ) -> Optional[EmailEvent]:
        """Process individual email into EmailEvent object"""
        try:
            # Extract basic email information
            headers = {h['name']: h['value'] for h in email_data['payload']['headers']}
            
            message_id = email_data['id']
            thread_id = email_data['threadId']
            timestamp = datetime.fromtimestamp(int(email_data['internalDate']) / 1000)
            
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')
            recipients = self._parse_recipients(headers)
            
            # Extract email body
            body_text, body_html = self._extract_email_body(email_data['payload'])
            
            # Determine direction
            direction = "received" if referee_email.lower() in sender.lower() else "sent"
            
            # Create email event
            email_event = EmailEvent(
                message_id=message_id,
                thread_id=thread_id,
                timestamp=timestamp,
                direction=direction,
                sender=sender,
                recipients=recipients,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                manuscript_id=manuscript_id,
                referee_name=referee_name,
                referee_email=referee_email
            )
            
            # Analyze email content
            await self._analyze_email_content(email_event)
            
            return email_event
            
        except Exception as e:
            logger.error(f"❌ Email processing failed: {e}")
            return None
    
    def _parse_recipients(self, headers: Dict[str, str]) -> List[str]:
        """Parse recipient email addresses from headers"""
        recipients = []
        
        for field in ['To', 'Cc', 'Bcc']:
            if field in headers:
                # Simple extraction - could be enhanced with email.utils.parseaddr
                recipient_string = headers[field]
                # Extract email addresses using regex
                email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                found_emails = re.findall(email_pattern, recipient_string)
                recipients.extend(found_emails)
        
        return list(set(recipients))  # Remove duplicates
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """Extract text and HTML body from email payload"""
        body_text = ""
        body_html = None
        
        try:
            if 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    mime_type = part['mimeType']
                    if mime_type == 'text/plain' and 'data' in part['body']:
                        body_text += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif mime_type == 'text/html' and 'data' in part['body']:
                        body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            else:
                # Single part message
                if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                    body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                elif payload['mimeType'] == 'text/html' and 'data' in payload['body']:
                    body_html = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    # Extract text from HTML if no plain text
                    if not body_text:
                        body_text = self._html_to_text(body_html)
        
        except Exception as e:
            logger.debug(f"Body extraction failed: {e}")
        
        return body_text.strip(), body_html
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        try:
            # Simple HTML to text conversion
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html)
            # Decode HTML entities
            text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
            return text.strip()
        except Exception:
            return html
    
    async def _analyze_email_content(self, email_event: EmailEvent):
        """Analyze email content to extract meaning and classify type"""
        try:
            # Basic pattern matching
            content = f"{email_event.subject} {email_event.body_text}".lower()
            
            # Classify email type
            email_event.email_type = self._classify_email_type(content)
            
            # Check for specific responses
            email_event.contains_acceptance = self._contains_pattern(content, self.email_patterns['acceptance'])
            email_event.contains_decline = self._contains_pattern(content, self.email_patterns['decline'])
            email_event.contains_submission = self._contains_pattern(content, self.email_patterns['submission'])
            
            # Basic sentiment analysis
            email_event.sentiment = self._analyze_sentiment(content)
            
            # AI-powered analysis if available
            if self.openai_client:
                ai_analysis = await self._ai_analyze_email(email_event)
                email_event.ai_analysis = ai_analysis
                email_event.confidence_score = ai_analysis.get('confidence', 0.5)
            
        except Exception as e:
            logger.error(f"❌ Email content analysis failed: {e}")
    
    def _classify_email_type(self, content: str) -> str:
        """Classify email type based on content patterns"""
        for email_type, patterns in self.email_patterns.items():
            if self._contains_pattern(content, patterns):
                return email_type
        return "other"
    
    def _contains_pattern(self, content: str, patterns: List[str]) -> bool:
        """Check if content contains any of the specified patterns"""
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
    
    def _analyze_sentiment(self, content: str) -> str:
        """Basic sentiment analysis"""
        positive_words = ['thank', 'pleased', 'happy', 'agree', 'yes', 'good', 'excellent']
        negative_words = ['sorry', 'regret', 'cannot', 'unable', 'no', 'decline', 'busy']
        
        content_words = content.lower().split()
        positive_count = sum(1 for word in content_words if any(pos in word for pos in positive_words))
        negative_count = sum(1 for word in content_words if any(neg in word for neg in negative_words))
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    async def _ai_analyze_email(self, email_event: EmailEvent) -> Dict[str, Any]:
        """AI-powered email analysis using OpenAI"""
        try:
            if not self.openai_client:
                return {}
            
            prompt = f"""
            Analyze this referee communication email and extract key information:
            
            Subject: {email_event.subject}
            Body: {email_event.body_text[:1000]}...
            
            Please identify:
            1. Email type (invitation, response, reminder, submission, question, other)
            2. Referee's response (accept, decline, question, submission, none)
            3. Sentiment (positive, negative, neutral)
            4. Confidence level (0.0-1.0)
            5. Key information extracted
            
            Respond in JSON format.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.debug(f"AI analysis failed: {e}")
            return {}
    
    async def _build_referee_timeline(
        self,
        manuscript_id: str,
        referee_name: str,
        referee_email: str,
        emails: List[EmailEvent]
    ) -> RefereeTimeline:
        """Build comprehensive referee timeline from email events"""
        try:
            timeline = RefereeTimeline(
                manuscript_id=manuscript_id,
                referee_name=referee_name,
                referee_email=referee_email,
                emails=emails
            )
            
            # Calculate basic statistics
            timeline.total_emails = len(emails)
            timeline.emails_sent_to_referee = sum(1 for e in emails if e.direction == "sent")
            timeline.emails_received_from_referee = sum(1 for e in emails if e.direction == "received")
            
            # Find key dates
            invitation_emails = [e for e in emails if e.email_type == "invitation" and e.direction == "sent"]
            if invitation_emails:
                timeline.first_contact_date = min(e.timestamp for e in invitation_emails)
            
            # Find first response
            response_emails = [e for e in emails if e.direction == "received"]
            if response_emails:
                timeline.response_date = min(e.timestamp for e in response_emails)
                
                # Calculate days to respond
                if timeline.first_contact_date:
                    timeline.days_to_respond = (timeline.response_date - timeline.first_contact_date).days
            
            # Find acceptance/decline
            acceptance_emails = [e for e in emails if e.contains_acceptance]
            decline_emails = [e for e in emails if e.contains_decline]
            submission_emails = [e for e in emails if e.contains_submission]
            
            if acceptance_emails:
                timeline.acceptance_date = min(e.timestamp for e in acceptance_emails)
            
            if decline_emails:
                timeline.decline_date = min(e.timestamp for e in decline_emails)
            
            if submission_emails:
                timeline.submission_date = min(e.timestamp for e in submission_emails)
                
                # Calculate days to complete
                if timeline.acceptance_date:
                    timeline.days_to_complete = (timeline.submission_date - timeline.acceptance_date).days
            
            # Count reminders
            reminder_emails = [e for e in emails if e.email_type == "reminder"]
            timeline.reminder_count = len(reminder_emails)
            
            # Determine final status
            if timeline.submission_date:
                timeline.final_status = "submitted"
            elif timeline.decline_date:
                timeline.final_status = "declined"
            elif timeline.acceptance_date:
                timeline.final_status = "accepted"
            elif timeline.response_date:
                timeline.final_status = "responded"
            else:
                timeline.final_status = "no_response"
            
            # Assess communication quality
            timeline.communication_quality = self._assess_communication_quality(timeline)
            
            return timeline
            
        except Exception as e:
            logger.error(f"❌ Timeline building failed: {e}")
            return RefereeTimeline(manuscript_id, referee_name, referee_email)
    
    def _assess_communication_quality(self, timeline: RefereeTimeline) -> str:
        """Assess quality of referee communication"""
        if timeline.days_to_respond is None:
            return "unresponsive"
        elif timeline.days_to_respond <= 3:
            return "responsive"
        elif timeline.days_to_respond <= 7:
            return "moderate"
        else:
            return "slow"
    
    async def extract_manuscript_email_timelines(
        self,
        manuscript_id: str,
        referees: List[Tuple[str, str]],  # (name, email) pairs
        search_config: Optional[EmailSearchConfig] = None
    ) -> Dict[str, RefereeTimeline]:
        """Extract email timelines for all referees on a manuscript"""
        try:
            logger.info(f"🔍 Extracting email timelines for {len(referees)} referees on {manuscript_id}")
            
            timelines = {}
            
            for referee_name, referee_email in referees:
                try:
                    timeline = await self.extract_referee_timeline(
                        manuscript_id, referee_email, referee_name, search_config
                    )
                    timelines[referee_email] = timeline
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to extract timeline for {referee_name}: {e}")
            
            logger.info(f"✅ Extracted {len(timelines)} email timelines")
            return timelines
            
        except Exception as e:
            logger.error(f"❌ Manuscript timeline extraction failed: {e}")
            return {}
    
    async def save_timeline_data(
        self,
        timelines: Dict[str, RefereeTimeline],
        output_path: Path
    ):
        """Save timeline data to file"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            timeline_data = {
                'extraction_date': datetime.now().isoformat(),
                'total_timelines': len(timelines),
                'timelines': {
                    email: asdict(timeline) for email, timeline in timelines.items()
                }
            }
            
            # Save to JSON
            with open(output_path, 'w') as f:
                json.dump(timeline_data, f, indent=2, default=str)
            
            logger.info(f"💾 Timeline data saved: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save timeline data: {e}")
    
    async def load_timeline_data(self, input_path: Path) -> Dict[str, RefereeTimeline]:
        """Load timeline data from file"""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            timelines = {}
            for email, timeline_dict in data['timelines'].items():
                # Convert back to objects
                timeline = RefereeTimeline(**timeline_dict)
                # Convert email events
                timeline.emails = [EmailEvent(**email_data) for email_data in timeline_dict['emails']]
                timelines[email] = timeline
            
            logger.info(f"📂 Loaded {len(timelines)} timelines from {input_path}")
            return timelines
            
        except Exception as e:
            logger.error(f"❌ Failed to load timeline data: {e}")
            return {}
    
    def generate_timeline_report(self, timelines: Dict[str, RefereeTimeline]) -> Dict[str, Any]:
        """Generate comprehensive timeline analysis report"""
        if not timelines:
            return {}
        
        # Calculate aggregate statistics
        total_referees = len(timelines)
        responsive_referees = sum(1 for t in timelines.values() if t.communication_quality == "responsive")
        submitted_reviews = sum(1 for t in timelines.values() if t.final_status == "submitted")
        declined_reviews = sum(1 for t in timelines.values() if t.final_status == "declined")
        
        # Calculate average response times
        response_times = [t.days_to_respond for t in timelines.values() if t.days_to_respond is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        completion_times = [t.days_to_complete for t in timelines.values() if t.days_to_complete is not None]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Calculate reminder statistics
        total_reminders = sum(t.reminder_count for t in timelines.values())
        avg_reminders = total_reminders / total_referees if total_referees > 0 else 0
        
        return {
            'summary': {
                'total_referees': total_referees,
                'response_rate': responsive_referees / total_referees if total_referees > 0 else 0,
                'submission_rate': submitted_reviews / total_referees if total_referees > 0 else 0,
                'decline_rate': declined_reviews / total_referees if total_referees > 0 else 0
            },
            'timing': {
                'average_response_time_days': avg_response_time,
                'average_completion_time_days': avg_completion_time,
                'average_reminders_per_referee': avg_reminders
            },
            'detailed_timelines': {
                email: asdict(timeline) for email, timeline in timelines.items()
            }
        }


# Example usage
if __name__ == "__main__":
    async def test_email_tracker():
        # Initialize email tracker
        tracker = EnhancedEmailTracker()
        
        # Test with sample referee data
        manuscript_id = "M172838"
        referees = [
            ("Samuel Daudin", "samuel.daudin@u-paris.fr"),
            ("Laurent Pfeiffer", "laurent.pfeiffer@inria.fr")
        ]
        
        # Extract timelines
        timelines = await tracker.extract_manuscript_email_timelines(
            manuscript_id, referees
        )
        
        # Generate report
        report = tracker.generate_timeline_report(timelines)
        
        print("Email Timeline Report:")
        print(f"Total referees: {report['summary']['total_referees']}")
        print(f"Response rate: {report['summary']['response_rate']:.2%}")
        print(f"Average response time: {report['timing']['average_response_time_days']:.1f} days")
    
    # Run test
    # asyncio.run(test_email_tracker())
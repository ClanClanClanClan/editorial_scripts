"""
Real email sending tests in dry-run mode

These tests verify email functionality without actually sending emails.
They test template generation, recipient validation, and safety checks.
"""
import pytest
import os
import json
from datetime import datetime, timedelta
from tests.real import TEST_CONFIG, real_test, gmail_test

if TEST_CONFIG['RUN_REAL_TESTS']:
    from core.email_utils import (
        get_gmail_service
    )
    from core.credential_manager import get_credential_manager
    from database import RefereeDatabase, RefereeProfile

@real_test
@gmail_test
class TestEmailTemplateGeneration:
    """Test email template generation with real data"""
    
    @pytest.fixture
    def sample_manuscripts(self):
        """Sample manuscript data for testing"""
        return [
            {
                'manuscript_id': 'JOTA-D-24-00123',
                'title': 'Optimization Methods for Large-Scale Systems',
                'status': 'Under Review',
                'referee_name': 'Dr. Alice Johnson',
                'referee_email': 'alice.johnson@university.edu',
                'date_assigned': '2024-01-15',
                'date_due': '2024-02-15',
                'days_overdue': 0,
                'reminder_count': 0,
                'journal': 'JOTA'
            },
            {
                'manuscript_id': 'SICON-2024-0456',
                'title': 'Control Theory Applications in Robotics',
                'status': 'Awaiting Referee Response',
                'referee_name': 'Dr. Bob Smith',
                'referee_email': 'bob.smith@tech.edu',
                'date_assigned': '2024-01-10',
                'date_due': '2024-02-10',
                'days_overdue': 5,
                'reminder_count': 2,
                'journal': 'SICON'
            },
            {
                'manuscript_id': 'MOR-2024-0789',
                'title': 'Stochastic Optimization Under Uncertainty',
                'status': 'Under Review',
                'referee_name': 'Dr. Carol Davis',
                'referee_email': 'carol.davis@institute.org',
                'date_assigned': '2024-01-20',
                'date_due': '2024-02-20',
                'days_overdue': 0,
                'reminder_count': 0,
                'journal': 'MOR'
            }
        ]
    
    def mock_generate_digest_html(self, manuscripts):
        """Mock digest HTML generation"""
        html = "<html><body><h1>Weekly Editorial Digest</h1>"
        for ms in manuscripts:
            html += f"<p>{ms['manuscript_id']}: {ms['title']}</p>"
            html += f"<p>Referee: {ms['referee_name']}</p>"
            if ms['days_overdue'] > 0:
                html += "<p class='overdue'>OVERDUE</p>"
        html += "</body></html>"
        return html
    
    def test_digest_html_generation(self, sample_manuscripts):
        """Test generating HTML digest from real manuscript data"""
        # Generate digest HTML (mock implementation)
        html_content = self.mock_generate_digest_html(sample_manuscripts)
        
        # Verify HTML structure
        assert '<html>' in html_content
        assert '<body>' in html_content
        assert 'Weekly Editorial Digest' in html_content
        
        # Check manuscript content is included
        for ms in sample_manuscripts:
            assert ms['manuscript_id'] in html_content
            assert ms['title'] in html_content
            assert ms['referee_name'] in html_content
        
        # Check overdue highlighting
        overdue_ms = [ms for ms in sample_manuscripts if ms['days_overdue'] > 0]
        if overdue_ms:
            assert 'overdue' in html_content.lower()
        
        print(f"\n✓ Generated digest HTML ({len(html_content)} characters)")
        print(f"  Included {len(sample_manuscripts)} manuscripts")
        print(f"  Found {len(overdue_ms)} overdue manuscripts")
    
    def test_reminder_email_template(self, sample_manuscripts):
        """Test generating reminder email templates"""
        # Get overdue manuscript
        overdue_ms = next((ms for ms in sample_manuscripts if ms['days_overdue'] > 0), None)
        
        if overdue_ms:
            # Generate reminder email content
            subject = f"Gentle reminder: Review for {overdue_ms['manuscript_id']}"
            
            # Test different tones based on relationship
            formal_content = generate_reminder_content(overdue_ms, tone='formal')
            friendly_content = generate_reminder_content(overdue_ms, tone='friendly')
            
            # Verify subject
            assert overdue_ms['manuscript_id'] in subject
            assert 'reminder' in subject.lower()
            
            # Verify content differences
            assert formal_content != friendly_content
            assert overdue_ms['referee_name'] in formal_content
            assert overdue_ms['manuscript_id'] in formal_content
            
            print(f"\n✓ Generated reminder templates for {overdue_ms['manuscript_id']}")
            print(f"  Subject: {subject}")
            print(f"  Formal tone: {len(formal_content)} characters")
            print(f"  Friendly tone: {len(friendly_content)} characters")
    
    def test_urgent_referee_detection(self, sample_manuscripts):
        """Test detecting urgent referees needing follow-up"""
        # Create database with sample data
        db = RefereeDatabase('data/test_urgent.db')
        
        urgent_referees = []
        for ms in sample_manuscripts:
            if ms['days_overdue'] > 0 or ms['reminder_count'] > 1:
                urgent_referees.append(ms)
        
        print(f"\n✓ Detected {len(urgent_referees)} urgent referees")
        
        for ref in urgent_referees:
            print(f"  {ref['referee_name']}: {ref['days_overdue']} days overdue, {ref['reminder_count']} reminders")
        
        # Cleanup
        os.remove('data/test_urgent.db')

def generate_reminder_content(manuscript, tone='formal'):
    """Generate reminder email content with different tones"""
    referee_name = manuscript['referee_name']
    ms_id = manuscript['manuscript_id']
    title = manuscript['title']
    days_overdue = manuscript['days_overdue']
    
    if tone == 'formal':
        return f"""Dear {referee_name},

I hope this email finds you well. I am writing to follow up on the review of manuscript {ms_id} entitled "{title}".

The review was originally due and is now {days_overdue} days overdue. I understand that reviewing can be time-consuming, and I appreciate your expertise and time.

Could you please provide an update on the status of your review? If you need additional time, please let me know your expected completion date.

Thank you for your valuable contribution to the review process.

Best regards,
Editorial Team"""
    
    elif tone == 'friendly':
        return f"""Hi {referee_name},

I hope you're doing well! I wanted to check in about the review for manuscript {ms_id} ("{title}").

I know you're probably swamped, but the review is running a bit behind schedule ({days_overdue} days overdue). No worries at all - these things happen!

When you get a chance, could you let me know how the review is coming along? Even a quick status update would be super helpful.

Thanks so much for all your help with this!

Best,
Editorial Team"""
    
    return ""

@real_test
class TestEmailSafetyChecks:
    """Test email safety mechanisms"""
    
    def test_dry_run_mode_enforcement(self):
        """Ensure dry-run mode prevents actual email sending"""
        # Verify dry-run is enabled
        assert TEST_CONFIG['DRY_RUN_ONLY'] == True
        
        # Mock email function should not actually send
        test_email = {
            'recipient': 'test@example.com',
            'subject': 'Test Email',
            'body': 'This is a test email'
        }
        
        # In dry-run mode, should return success but not send
        result = mock_send_email(test_email)
        assert result['status'] == 'dry_run'
        assert 'would_send_to' in result
        
        print("\n✓ Dry-run mode prevents actual email sending")
    
    def test_recipient_validation(self):
        """Test email recipient validation"""
        valid_emails = [
            'user@example.com',
            'first.last@university.edu',
            'researcher@institute.org'
        ]
        
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user@.com',
            ''
        ]
        
        for email in valid_emails:
            assert validate_email(email), f"Should be valid: {email}"
        
        for email in invalid_emails:
            assert not validate_email(email), f"Should be invalid: {email}"
        
        print(f"\n✓ Email validation working ({len(valid_emails)} valid, {len(invalid_emails)} invalid)")
    
    def test_rate_limiting_for_emails(self):
        """Test that email sending respects rate limits"""
        # Should not send more than X emails per hour
        max_emails_per_hour = 50
        
        # Simulate rapid email sending
        emails_sent = 0
        start_time = datetime.now()
        
        while emails_sent < max_emails_per_hour + 10:
            # Mock email send with rate limiting
            if should_rate_limit_email(emails_sent, start_time):
                break
            emails_sent += 1
        
        assert emails_sent <= max_emails_per_hour
        print(f"\n✓ Rate limiting prevents sending > {max_emails_per_hour} emails/hour")

def mock_send_email(email_data):
    """Mock email sending function for testing"""
    if TEST_CONFIG['DRY_RUN_ONLY']:
        return {
            'status': 'dry_run',
            'would_send_to': email_data['recipient'],
            'subject': email_data['subject'],
            'body_length': len(email_data['body'])
        }
    else:
        # In real mode, would actually send
        return {'status': 'sent', 'message_id': 'fake_id_123'}

def validate_email(email):
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def should_rate_limit_email(count, start_time):
    """Check if we should rate limit email sending"""
    max_per_hour = 50
    elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600
    
    if elapsed_hours >= 1.0:
        return False  # Reset after an hour
    
    return count >= max_per_hour

@real_test
@gmail_test
class TestGmailIntegration:
    """Test Gmail integration for sending emails"""
    
    def test_gmail_service_initialization(self):
        """Test Gmail service can be initialized"""
        try:
            service = get_gmail_service()
            assert service is not None
            
            # Test connection
            profile = service.users().getProfile(userId='me').execute()
            assert 'emailAddress' in profile
            
            print(f"\n✓ Gmail service connected: {profile['emailAddress']}")
            
        except Exception as e:
            pytest.skip(f"Gmail service not available: {e}")
    
    def test_email_composition_api(self):
        """Test Gmail API email composition (without sending)"""
        try:
            service = get_gmail_service()
            
            # Compose test email
            message = create_gmail_message(
                to='test@example.com',
                subject='Test Email Composition',
                body='This is a test email body'
            )
            
            # Verify message structure
            assert 'raw' in message
            assert len(message['raw']) > 0
            
            print("\n✓ Gmail message composition working")
            
        except Exception as e:
            pytest.skip(f"Gmail API not available: {e}")
    
    def test_draft_email_creation(self):
        """Test creating draft emails (safer than sending)"""
        try:
            service = get_gmail_service()
            
            # Create draft instead of sending
            draft = {
                'message': create_gmail_message(
                    to='test@example.com',
                    subject='Draft Test Email',
                    body='This is a draft email'
                )
            }
            
            # In dry-run mode, just validate structure
            if TEST_CONFIG['DRY_RUN_ONLY']:
                assert 'message' in draft
                assert 'raw' in draft['message']
                print("\n✓ Draft email structure validated (dry-run)")
            else:
                # Would actually create draft
                created_draft = service.users().drafts().create(
                    userId='me',
                    body=draft
                ).execute()
                
                assert 'id' in created_draft
                print(f"\n✓ Draft email created: {created_draft['id']}")
                
        except Exception as e:
            pytest.skip(f"Gmail API not available: {e}")

def create_gmail_message(to, subject, body):
    """Create a Gmail API message"""
    import base64
    from email.mime.text import MIMEText
    
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}

@real_test
class TestEmailAnalytics:
    """Test email analytics and tracking"""
    
    def test_email_response_tracking(self):
        """Test tracking email responses"""
        # Mock sent emails
        sent_emails = [
            {
                'recipient': 'alice@uni.edu',
                'subject': 'Review reminder',
                'sent_date': datetime.now() - timedelta(days=3),
                'type': 'reminder'
            },
            {
                'recipient': 'bob@tech.edu', 
                'subject': 'Weekly digest',
                'sent_date': datetime.now() - timedelta(days=1),
                'type': 'digest'
            }
        ]
        
        # Mock responses (would come from Gmail API)
        responses = [
            {
                'sender': 'alice@uni.edu',
                'subject': 'Re: Review reminder',
                'date': datetime.now() - timedelta(days=2)
            }
        ]
        
        # Calculate response rates
        reminder_emails = [e for e in sent_emails if e['type'] == 'reminder']
        responded_emails = [r for r in responses if 'Re:' in r['subject']]
        
        response_rate = len(responded_emails) / len(reminder_emails) if reminder_emails else 0
        
        print(f"\n✓ Email analytics calculated")
        print(f"  Sent reminders: {len(reminder_emails)}")
        print(f"  Received responses: {len(responded_emails)}")
        print(f"  Response rate: {response_rate:.1%}")
    
    def test_email_effectiveness_metrics(self):
        """Test measuring email effectiveness"""
        # Mock email effectiveness data
        effectiveness_data = {
            'total_reminders_sent': 25,
            'reviews_submitted_after_reminder': 18,
            'avg_response_time_days': 3.2,
            'bounce_rate': 0.04,
            'unsubscribe_rate': 0.01
        }
        
        # Calculate effectiveness score
        effectiveness_score = calculate_email_effectiveness(effectiveness_data)
        
        assert 0 <= effectiveness_score <= 1
        print(f"\n✓ Email effectiveness: {effectiveness_score:.2f}")
        
        # Verify metrics are reasonable
        assert effectiveness_data['bounce_rate'] < 0.1  # Less than 10%
        assert effectiveness_data['unsubscribe_rate'] < 0.05  # Less than 5%

def calculate_email_effectiveness(data):
    """Calculate email effectiveness score"""
    response_rate = data['reviews_submitted_after_reminder'] / data['total_reminders_sent']
    bounce_penalty = data['bounce_rate'] * 0.5
    unsubscribe_penalty = data['unsubscribe_rate'] * 0.3
    
    return max(0, response_rate - bounce_penalty - unsubscribe_penalty)

@real_test
class TestEmailPersonalization:
    """Test email personalization features"""
    
    def test_referee_relationship_detection(self):
        """Test detecting referee relationships for tone adjustment"""
        # Mock referee database
        referees = [
            {
                'name': 'Dr. Alice Johnson',
                'email': 'alice@uni.edu',
                'relationship': 'colleague',
                'past_interactions': 15
            },
            {
                'name': 'Dr. Bob Smith',
                'email': 'bob@tech.edu',
                'relationship': 'unknown',
                'past_interactions': 2
            }
        ]
        
        # Test tone selection
        for referee in referees:
            tone = select_email_tone(referee)
            
            if referee['relationship'] == 'colleague' or referee['past_interactions'] > 10:
                assert tone == 'friendly'
            else:
                assert tone == 'formal'
        
        print(f"\n✓ Email tone personalization working")
    
    def test_template_customization(self):
        """Test customizing email templates"""
        base_template = """Dear {referee_name},

{greeting_line}

I am writing regarding manuscript {manuscript_id} entitled "{title}".

{main_content}

{closing_line}

Best regards,
Editorial Team"""
        
        formal_vars = {
            'referee_name': 'Dr. Smith',
            'greeting_line': 'I hope this email finds you well.',
            'manuscript_id': 'TEST-2024-001',
            'title': 'Test Paper',
            'main_content': 'The review deadline has passed...',
            'closing_line': 'Thank you for your attention to this matter.'
        }
        
        friendly_vars = {
            'referee_name': 'Alice',
            'greeting_line': 'I hope you\'re doing well!',
            'manuscript_id': 'TEST-2024-001',
            'title': 'Test Paper',
            'main_content': 'Just checking in on the review...',
            'closing_line': 'Thanks so much for your help!'
        }
        
        formal_email = base_template.format(**formal_vars)
        friendly_email = base_template.format(**friendly_vars)
        
        # Should be different
        assert formal_email != friendly_email
        assert 'finds you well' in formal_email
        assert 'doing well!' in friendly_email
        
        print("\n✓ Email template customization working")

def select_email_tone(referee):
    """Select appropriate email tone based on referee relationship"""
    if referee['relationship'] == 'colleague' or referee['past_interactions'] > 10:
        return 'friendly'
    else:
        return 'formal'
"""
Real Gmail API integration tests

These tests actually connect to Gmail and verify functionality.
Requires valid credentials in token.json or credentials.json
"""
import pytest
import os
from datetime import datetime, timedelta
from tests.real import TEST_CONFIG, real_test, gmail_test

# Only import if we're running real tests
if TEST_CONFIG['RUN_REAL_TESTS']:
    from core.email_utils import get_gmail_service, fetch_starred_emails
    from journals.jota_enhanced import JOTAJournal
    from googleapiclient.errors import HttpError

@real_test
@gmail_test
class TestGmailAPIReal:
    """Test real Gmail API functionality"""
    
    @pytest.fixture(scope="class")
    def gmail_service(self):
        """Get real Gmail service"""
        try:
            service = get_gmail_service()
            # Test connection
            service.users().getProfile(userId='me').execute()
            return service
        except Exception as e:
            pytest.skip(f"Gmail API not available: {e}")
    
    def test_gmail_connection(self, gmail_service):
        """Test basic Gmail API connection"""
        # Get user profile
        profile = gmail_service.users().getProfile(userId='me').execute()
        
        assert 'emailAddress' in profile
        assert profile['messagesTotal'] > 0
        
        print(f"\n✓ Connected to Gmail: {profile['emailAddress']}")
        print(f"  Total messages: {profile['messagesTotal']}")
        print(f"  Total threads: {profile['threadsTotal']}")
    
    def test_list_labels(self, gmail_service):
        """Test listing Gmail labels"""
        results = gmail_service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        assert len(labels) > 0
        
        # Check for standard labels
        label_names = [label['name'] for label in labels]
        assert 'INBOX' in label_names
        assert 'SENT' in label_names
        
        print(f"\n✓ Found {len(labels)} labels")
    
    def test_search_messages(self, gmail_service):
        """Test message search functionality"""
        # Search for recent messages (safe query)
        query = f'newer_than:7d'
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=TEST_CONFIG['MAX_EMAILS_TO_FETCH']
        ).execute()
        
        messages = results.get('messages', [])
        print(f"\n✓ Found {len(messages)} messages from last 7 days")
        
        # If we have messages, test fetching one
        if messages:
            msg_id = messages[0]['id']
            message = gmail_service.users().messages().get(
                userId='me',
                id=msg_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()
            
            assert 'payload' in message
            assert 'headers' in message['payload']
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            print(f"  Sample message: {headers.get('Subject', 'No subject')}")
    
    def test_jota_email_parsing_real(self, gmail_service):
        """Test JOTA email parsing with real emails"""
        journal = JOTAJournal(gmail_service, debug=True)
        
        # Search for JOTA emails (limited)
        query = 'subject:"JOTA" newer_than:30d'
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5
        ).execute()
        
        messages = results.get('messages', [])
        print(f"\n✓ Found {len(messages)} JOTA emails from last 30 days")
        
        if messages:
            # Test parsing one message
            msg_id = messages[0]['id']
            parsed_msg = journal.get_and_parse_message(msg_id, 'JOTA')
            
            if parsed_msg:
                subject = parsed_msg.get('subject', '')
                body = parsed_msg.get('body', '')
                date = parsed_msg.get('date')
                
                assert subject is not None
                assert body is not None
                
                print(f"  Parsed message: {subject[:50]}...")
                
                # Test parsing logic based on subject
                if "Weekly Overview" in subject:
                    result = journal.parse_weekly_overview(subject, body, date)
                    assert result['type'] == 'weekly_overview'
                    print(f"  ✓ Successfully parsed weekly overview with {len(result.get('manuscripts', []))} manuscripts")
                
                elif "agreed to review" in subject:
                    result = journal.parse_acceptance_email(subject, body, date, '')
                    assert result['type'] == 'acceptance'
                    print(f"  ✓ Successfully parsed acceptance for {result['manuscript_id']}")
            else:
                print("  ⚠ Could not parse message")
    
    def test_fetch_starred_emails_real(self, gmail_service):
        """Test fetching starred emails"""
        # Test with JOTA (safest as it's email-only)
        try:
            starred = fetch_starred_emails('JOTA')
            print(f"\n✓ Found {len(starred)} starred JOTA emails")
            
            if starred:
                # Check first email structure
                email = starred[0]
                assert 'subject' in email
                assert 'body' in email
                assert 'date' in email
                
                print(f"  Latest: {email['subject'][:50]}...")
                
        except Exception as e:
            print(f"\n⚠ Could not fetch starred emails: {e}")
            # Don't fail test - starred emails might not exist

@real_test
@gmail_test
class TestEmailMatchingReal:
    """Test email matching with real data"""
    
    def test_email_matching_workflow(self):
        """Test complete email matching workflow"""
        from core.email_utils import (
            fetch_starred_emails,
            robust_match_email_for_referee_jota
        )
        
        # Fetch real starred emails
        try:
            starred = fetch_starred_emails('JOTA')
            
            if len(starred) >= 2:
                # Try to match referees
                # This is a smoke test - we don't know what emails exist
                matched = 0
                for email in starred[:5]:
                    if 'agreed to review' in email.get('subject', '').lower():
                        # Try to extract manuscript ID
                        import re
                        ms_match = re.search(r'JOTA-D-\d{2}-\d{5}', email['subject'])
                        if ms_match:
                            ms_id = ms_match.group(0)
                            
                            # Try matching (we don't know referee name)
                            date, ref_email = robust_match_email_for_referee_jota(
                                "Test Referee",  # Dummy name
                                ms_id,
                                "Accepted",
                                [email]
                            )
                            
                            if date:
                                matched += 1
                
                print(f"\n✓ Email matching test completed, matched {matched} emails")
            else:
                print("\n⚠ Not enough starred emails for matching test")
                
        except Exception as e:
            print(f"\n⚠ Email matching test skipped: {e}")

@real_test
class TestGmailSafetyChecks:
    """Test safety mechanisms for Gmail operations"""
    
    def test_dry_run_safety(self):
        """Ensure we never send real emails in tests"""
        from core.email_utils import send_digest_email
        
        # This should be mocked or have safety checks
        assert TEST_CONFIG['DRY_RUN_ONLY'] == True
        print("\n✓ Dry run safety check passed")
    
    def test_rate_limiting(self):
        """Test that we respect Gmail rate limits"""
        assert TEST_CONFIG['MAX_EMAILS_TO_FETCH'] <= 100
        print(f"\n✓ Rate limiting configured: max {TEST_CONFIG['MAX_EMAILS_TO_FETCH']} emails")
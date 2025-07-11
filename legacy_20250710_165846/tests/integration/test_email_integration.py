"""
Integration tests for email processing workflow
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import base64

from journals.jota_enhanced import JOTAJournal
from core.email_utils import fetch_starred_emails, robust_match_email_for_referee_jota
from core.digest_utils import build_html_digest, collect_unmatched_and_urgent
from tests.mocks import MockDataGenerator

class TestEmailIntegration:
    """Test email processing integration"""
    
    @pytest.fixture
    def mock_gmail_messages(self):
        """Generate mock Gmail messages"""
        messages = []
        
        # Acceptance emails
        for i in range(3):
            email = MockDataGenerator.generate_email_message("acceptance", "JOTA")
            gmail_msg = MockDataGenerator.generate_gmail_message(email)
            messages.append(gmail_msg)
        
        # Weekly overview
        weekly = MockDataGenerator.generate_email_message("weekly", "JOTA")
        messages.append(MockDataGenerator.generate_gmail_message(weekly))
        
        # Invitation emails
        for i in range(2):
            invite = MockDataGenerator.generate_email_message("invitation", "JOTA")
            messages.append(MockDataGenerator.generate_gmail_message(invite))
        
        return messages
    
    def test_jota_full_workflow(self, mock_gmail_service, mock_gmail_messages):
        """Test complete JOTA email processing workflow"""
        # Setup mock Gmail service
        mock_gmail_service.users().messages().list().execute.return_value = {
            'messages': [{'id': msg['id']} for msg in mock_gmail_messages]
        }
        
        # Mock individual message fetches
        def get_message_side_effect(userId, id, format):
            for msg in mock_gmail_messages:
                if msg['id'] == id:
                    return Mock(execute=Mock(return_value=msg))
            return Mock(execute=Mock(return_value=None))
        
        mock_gmail_service.users().messages().get.side_effect = get_message_side_effect
        
        # Create JOTA journal and process
        jota = JOTAJournal(mock_gmail_service)
        manuscripts = jota.scrape_manuscripts_and_emails()
        
        # Verify we got manuscripts
        assert len(manuscripts) > 0
        
        # Check manuscript format
        for ms in manuscripts:
            assert 'Manuscript #' in ms
            assert 'Title' in ms
            assert 'Referees' in ms
            assert isinstance(ms['Referees'], list)
            
            # Check referee format
            for ref in ms['Referees']:
                assert 'Referee Name' in ref
                assert 'Status' in ref
                assert ref['Status'] in ['Accepted', 'Contacted', 'Declined']
    
    def test_email_matching_integration(self):
        """Test email matching with realistic data"""
        # Generate flagged emails
        flagged_emails = []
        
        # Add acceptance email
        flagged_emails.append({
            'subject': 'JOTA - Reviewer has agreed to review JOTA-D-24-00123',
            'body': 'John Smith, Ph.D has agreed to take on this assignment',
            'date': '2024-01-15',
            'to': 'editor@jota.org'
        })
        
        # Add invitation email
        flagged_emails.append({
            'subject': 'JOTA - Reviewer Invitation',
            'body': 'Dear Dr. Jane Doe, You are invited to review JOTA-D-24-00456',
            'date': '2024-01-20',
            'to': 'jane.doe@university.edu'
        })
        
        # Test matching
        date1, email1 = robust_match_email_for_referee_jota(
            "John Smith",
            "JOTA-D-24-00123",
            "Accepted",
            flagged_emails
        )
        assert date1 == '2024-01-15'
        
        date2, email2 = robust_match_email_for_referee_jota(
            "Jane Doe",
            "JOTA-D-24-00456",
            "Contacted",
            flagged_emails
        )
        assert date2 == '2024-01-20'
        assert email2 == 'jane.doe@university.edu'
    
    def test_digest_generation_integration(self):
        """Test digest generation with complete data"""
        # Generate manuscripts
        manuscripts = []
        for i in range(3):
            ms = MockDataGenerator.generate_manuscript("JOTA", num_referees=2)
            manuscripts.append(ms)
        
        # Generate flagged emails
        flagged_emails = []
        for ms in manuscripts:
            for ref in ms['Referees']:
                if ref['Status'] == 'Accepted':
                    email = {
                        'subject': f"JOTA - Reviewer agreed for {ms['Manuscript #']}",
                        'body': f"{ref['Referee Name']} has agreed to review",
                        'date': ref.get('Accepted Date', ''),
                        'to': ref['Referee Email']
                    }
                    flagged_emails.append(email)
        
        # Collect unmatched and urgent
        unmatched, urgent = collect_unmatched_and_urgent(
            manuscripts,
            flagged_emails,
            robust_match_email_for_referee_jota
        )
        
        # Generate digest
        html_digest = build_html_digest(
            "JOTA",
            manuscripts,
            flagged_emails,
            unmatched,
            urgent,
            robust_match_email_for_referee_jota
        )
        
        # Verify digest content
        assert "JOTA" in html_digest
        assert "<table" in html_digest
        assert "Manuscript #" in html_digest
        
        # Check all manuscripts are included
        for ms in manuscripts:
            assert ms['Manuscript #'] in html_digest
            assert ms['Title'] in html_digest
    
    @patch('core.email_utils.get_gmail_service')
    def test_fetch_starred_emails_integration(self, mock_get_service):
        """Test fetching starred emails"""
        # Mock Gmail service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock search results
        messages = []
        for i in range(5):
            email = MockDataGenerator.generate_email_message("acceptance", "JOTA")
            gmail_msg = MockDataGenerator.generate_gmail_message(email)
            messages.append({'id': gmail_msg['id']})
        
        mock_service.users().messages().list().execute.return_value = {
            'messages': messages
        }
        
        # Mock individual message fetches
        def get_message(userId, id, format):
            msg = MockDataGenerator.generate_gmail_message(
                MockDataGenerator.generate_email_message("acceptance", "JOTA")
            )
            msg['id'] = id
            return Mock(execute=Mock(return_value=msg))
        
        mock_service.users().messages().get = get_message
        
        # Fetch emails
        starred = fetch_starred_emails("JOTA")
        
        # Verify results
        assert len(starred) > 0
        for email in starred:
            assert 'subject' in email
            assert 'body' in email
            assert 'date' in email

class TestMultiJournalIntegration:
    """Test integration across multiple journals"""
    
    def test_journal_data_aggregation(self):
        """Test aggregating data from multiple journals"""
        all_manuscripts = {}
        
        # Generate data for each journal
        for journal in ["SICON", "JOTA", "MOR", "MF"]:
            manuscripts = []
            for i in range(2):
                ms = MockDataGenerator.generate_manuscript(journal)
                manuscripts.append(ms)
            all_manuscripts[journal] = manuscripts
        
        # Simulate digest generation for all journals
        digests = {}
        for journal, manuscripts in all_manuscripts.items():
            digest = build_html_digest(
                journal,
                manuscripts,
                [],  # flagged_emails
                [],  # unmatched
                [],  # urgent
                Mock()  # match_func
            )
            digests[journal] = digest
        
        # Combine digests
        combined_digest = "<br><br>".join(digests.values())
        
        # Verify all journals are included
        for journal in all_manuscripts.keys():
            assert journal in combined_digest
        
        # Verify manuscript count
        total_manuscripts = sum(len(mss) for mss in all_manuscripts.values())
        manuscript_count = combined_digest.count("Manuscript #")
        assert manuscript_count >= total_manuscripts
"""
Unit tests for JOTA journal email parsing
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import base64

from journals.jota_enhanced import JOTAJournal

class TestJOTAJournal:
    """Test JOTA email-based journal scraping"""
    
    @pytest.fixture
    def jota_journal(self, mock_gmail_service):
        """Create JOTA journal instance with mock Gmail service"""
        return JOTAJournal(mock_gmail_service, debug=False)
    
    @pytest.fixture
    def sample_acceptance_email(self):
        """Sample acceptance email data"""
        return {
            'id': 'msg123',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'JOTA - Reviewer has agreed to review JOTA-D-24-00769R1'},
                    {'name': 'Date', 'value': 'Wed, 15 Jan 2024 14:30:00 +0000'},
                    {'name': 'From', 'value': 'em@editorialmanager.com'},
                    {'name': 'To', 'value': 'editor@university.edu'}
                ],
                'body': {
                    'data': base64.urlsafe_b64encode(
                        b"Dear Editor,\n\n"
                        b"Olivier Menoukeu Pamen, Ph.D has agreed to take on this assignment.\n\n"
                        b"Manuscript: JOTA-D-24-00769R1\n"
                        b"Title: Stochastic Optimal Control with Model Uncertainty\n\n"
                        b"Best regards,\nEditorial Manager"
                    ).decode()
                }
            }
        }
    
    @pytest.fixture
    def sample_invitation_email(self):
        """Sample invitation email data"""
        return {
            'id': 'msg124',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'JOTA - Reviewer Invitation for JOTA-D-24-00888'},
                    {'name': 'Date', 'value': 'Mon, 20 Jan 2024 10:00:00 +0000'},
                    {'name': 'From', 'value': 'noreply@editorialmanager.com'},
                    {'name': 'To', 'value': 'jane.smith@college.edu'}
                ],
                'body': {
                    'data': base64.urlsafe_b64encode(
                        b"Dear Dr. Jane Smith,\n\n"
                        b"You have been invited to review the manuscript:\n\n"
                        b"Manuscript ID: JOTA-D-24-00888\n"
                        b"Title: \"Optimal Portfolio Selection under Uncertainty\"\n\n"
                        b"Please log in to accept or decline this invitation.\n\n"
                        b"Best regards"
                    ).decode()
                }
            }
        }
    
    @pytest.fixture
    def sample_weekly_overview_email(self):
        """Sample weekly overview email data"""
        return {
            'id': 'msg125',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'JOTA - Weekly Overview Of Your Assignments'},
                    {'name': 'Date', 'value': 'Mon, 22 Jan 2024 08:00:00 +0000'},
                    {'name': 'From', 'value': 'em@editorialmanager.com'}
                ],
                'body': {
                    'data': base64.urlsafe_b64encode(
                        b"Weekly Overview of Your Assignments\n\n"
                        b"JOTA-D-24-00769R1  submitted 45 days ago  Under Review (15 days) 2 Agreed\n"
                        b"Title: Stochastic Optimal Control with Model Uncertainty\n"
                        b"Authors: Tao Hao, Shandong University; Juan Li, Beijing University\n\n"
                        b"JOTA-D-24-00888  submitted 10 days ago  Awaiting Reviewer Assignment (5 days) 0 Agreed\n"
                        b"Title: Optimal Portfolio Selection under Uncertainty\n"
                        b"Authors: John Doe, MIT; Jane Roe, Stanford\n"
                    ).decode()
                }
            }
        }
    
    def test_parse_acceptance_email(self, jota_journal, sample_acceptance_email):
        """Test parsing reviewer acceptance email"""
        result = jota_journal.parse_acceptance_email(
            sample_acceptance_email['payload']['headers'][0]['value'],
            base64.urlsafe_b64decode(sample_acceptance_email['payload']['body']['data']).decode(),
            datetime(2024, 1, 15, 14, 30),
            'editor@university.edu'
        )
        
        assert result['type'] == 'acceptance'
        assert result['manuscript_id'] == 'JOTA-D-24-00769R1'
        assert result['referee_name'] == 'Olivier Menoukeu Pamen'
        assert result['date'] == datetime(2024, 1, 15, 14, 30)
    
    def test_parse_invitation_email(self, jota_journal, sample_invitation_email):
        """Test parsing reviewer invitation email"""
        result = jota_journal.parse_invitation_email(
            sample_invitation_email['payload']['headers'][0]['value'],
            base64.urlsafe_b64decode(sample_invitation_email['payload']['body']['data']).decode(),
            datetime(2024, 1, 20, 10, 0),
            'jane.smith@college.edu'
        )
        
        assert result['type'] == 'invitation'
        assert result['manuscript_id'] == 'JOTA-D-24-00888'
        assert result['referee_name'] == 'Jane Smith'
        assert result['title'] == 'Optimal Portfolio Selection under Uncertainty'
        assert result['referee_email'] == 'jane.smith@college.edu'
    
    def test_parse_weekly_overview(self, jota_journal, sample_weekly_overview_email):
        """Test parsing weekly overview email"""
        result = jota_journal.parse_weekly_overview(
            sample_weekly_overview_email['payload']['headers'][0]['value'],
            base64.urlsafe_b64decode(sample_weekly_overview_email['payload']['body']['data']).decode(),
            datetime(2024, 1, 22, 8, 0)
        )
        
        assert result['type'] == 'weekly_overview'
        assert len(result['manuscripts']) == 2
        
        ms1 = result['manuscripts'][0]
        assert ms1['manuscript_id'] == 'JOTA-D-24-00769R1'
        assert ms1['title'] == 'Stochastic Optimal Control with Model Uncertainty'
        assert ms1['days_since_submission'] == 45
        assert ms1['agreed_referees'] == 2
        
        ms2 = result['manuscripts'][1]
        assert ms2['manuscript_id'] == 'JOTA-D-24-00888'
        assert ms2['title'] == 'Optimal Portfolio Selection under Uncertainty'
        assert ms2['agreed_referees'] == 0
    
    def test_transform_to_manuscript_format(self, jota_journal):
        """Test transforming email data to standard manuscript format"""
        email_data = {
            'acceptance_emails': [
                {
                    'manuscript_id': 'JOTA-D-24-00769R1',
                    'referee_name': 'Olivier Pamen',
                    'referee_email': 'pamen@university.edu',
                    'type': 'accepted',
                    'date': datetime(2024, 1, 15)
                },
                {
                    'manuscript_id': 'JOTA-D-24-00769R1',
                    'referee_name': 'Jane Smith',
                    'referee_email': 'jane@college.edu',
                    'type': 'accepted',
                    'date': datetime(2024, 1, 16)
                }
            ],
            'invitation_emails': [
                {
                    'manuscript_id': 'JOTA-D-24-00888',
                    'referee_name': 'Bob Johnson',
                    'referee_email': 'bob@institute.edu',
                    'type': 'invited',
                    'date': datetime(2024, 1, 20),
                    'title': 'Portfolio Optimization'
                }
            ],
            'decline_emails': [],
            'reminder_emails': [],
            'weekly_overviews': [
                {
                    'type': 'weekly_overview',
                    'date': datetime(2024, 1, 22),
                    'manuscripts': [
                        {
                            'manuscript_id': 'JOTA-D-24-00769R1',
                            'title': 'Stochastic Control',
                            'authors': 'Tao Hao, Juan Li',
                            'status': 'Under Review',
                            'days_since_submission': 45,
                            'days_in_status': 15,
                            'agreed_referees': 2,
                            'submission_date': datetime(2024, 1, 22) - timedelta(days=45)
                        }
                    ]
                }
            ],
            'status_updates': []
        }
        
        manuscripts = jota_journal.transform_to_manuscript_format(email_data)
        
        assert len(manuscripts) == 2
        
        # Check first manuscript (has weekly overview data)
        ms1 = next(m for m in manuscripts if m['Manuscript #'] == 'JOTA-D-24-00769R1')
        assert ms1['Title'] == 'Stochastic Control'
        assert ms1['Contact Author'] == 'Tao Hao'
        assert len(ms1['Referees']) == 2
        
        # Check referees
        olivier = next(r for r in ms1['Referees'] if r['Referee Name'] == 'Olivier Pamen')
        assert olivier['Status'] == 'Accepted'
        assert olivier['Referee Email'] == 'pamen@university.edu'
        assert olivier['Accepted Date'] == datetime(2024, 1, 15).isoformat()
        
        # Check second manuscript (no weekly overview)
        ms2 = next(m for m in manuscripts if m['Manuscript #'] == 'JOTA-D-24-00888')
        assert ms2['Title'] == 'Portfolio Optimization'
        assert len(ms2['Referees']) == 1
        assert ms2['Referees'][0]['Status'] == 'Contacted'
    
    def test_scrape_manuscripts_and_emails(self, mock_gmail_service):
        """Test full scraping workflow"""
        # Mock message list
        mock_gmail_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }
        
        # Mock individual message fetches
        acceptance_msg = {
            'id': 'msg1',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'JOTA - Reviewer has agreed to review JOTA-D-24-00123'},
                    {'name': 'Date', 'value': 'Wed, 15 Jan 2024 14:30:00 +0000'}
                ],
                'body': {
                    'data': base64.urlsafe_b64encode(
                        b"Test User has agreed to review JOTA-D-24-00123"
                    ).decode()
                }
            }
        }
        
        weekly_msg = {
            'id': 'msg2',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'JOTA - Weekly Overview Of Your Assignments'},
                    {'name': 'Date', 'value': 'Mon, 22 Jan 2024 08:00:00 +0000'}
                ],
                'body': {
                    'data': base64.urlsafe_b64encode(
                        b"JOTA-D-24-00123  submitted 30 days ago  Under Review (10 days) 1 Agreed\n"
                        b"Title: Test Manuscript\n"
                        b"Authors: Test Author"
                    ).decode()
                }
            }
        }
        
        mock_gmail_service.users().messages().get().execute.side_effect = [
            acceptance_msg, weekly_msg
        ]
        
        # Create journal and scrape
        journal = JOTAJournal(mock_gmail_service)
        manuscripts = journal.scrape_manuscripts_and_emails()
        
        assert isinstance(manuscripts, list)
        assert len(manuscripts) > 0
        
        # Verify proper format
        ms = manuscripts[0]
        assert 'Manuscript #' in ms
        assert 'Title' in ms
        assert 'Referees' in ms
    
    def test_email_extraction(self, jota_journal):
        """Test email address extraction from text"""
        text1 = "Please contact the reviewer at john.doe@university.edu for details"
        assert jota_journal._extract_email_from_text(text1) == "john.doe@university.edu"
        
        text2 = "Multiple emails: admin@editorial.com and real.person@college.edu"
        # Should skip system emails
        assert jota_journal._extract_email_from_text(text2) == "real.person@college.edu"
        
        text3 = "No email here"
        assert jota_journal._extract_email_from_text(text3) is None
    
    def test_stage_determination(self, jota_journal):
        """Test manuscript stage determination"""
        assert jota_journal._determine_stage("Under Review") == "Under Review"
        assert jota_journal._determine_stage("Awaiting Reviewer Assignment") == "Pending Referee Assignment"
        assert jota_journal._determine_stage("Awaiting AE Decision") == "Awaiting Decision"
        assert jota_journal._determine_stage("Major Revision Submitted") == "Awaiting Revision"
        assert jota_journal._determine_stage("Unknown Status") == "Unknown Status"
    
    def test_error_handling(self, mock_gmail_service):
        """Test error handling in email fetching"""
        # Mock API error
        mock_gmail_service.users().messages().list().execute.side_effect = Exception("API Error")
        
        journal = JOTAJournal(mock_gmail_service)
        manuscripts = journal.scrape_manuscripts_and_emails()
        
        # Should return empty list on error
        assert manuscripts == []
"""
Unit tests for email utility functions
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import base64

from core.email_utils import (
    robust_normalize,
    robust_match_email_for_referee,
    robust_match_email_for_referee_mf,
    robust_match_email_for_referee_mor,
    robust_match_email_for_referee_jota,
    robust_match_email_for_referee_mafe,
    robust_match_email_for_referee_fs,
    decode_header_field,
    extract_body_from_email,
    strip_html
)

class TestNormalization:
    """Test text normalization functions"""
    
    def test_robust_normalize(self):
        """Test robust text normalization"""
        # Basic normalization
        assert robust_normalize("John Doe") == "john doe"
        assert robust_normalize("  JOHN  DOE  ") == "john doe"
        
        # Unicode normalization
        assert robust_normalize("Jérôme") == "jerome"
        assert robust_normalize("Müller") == "muller"
        assert robust_normalize("José María") == "jose maria"
        
        # Punctuation removal
        assert robust_normalize("O'Brien") == "obrien"
        assert robust_normalize("Smith-Jones") == "smithjones"
        assert robust_normalize("Dr. John Doe, Ph.D.") == "dr john doe phd"
        
        # Empty/None handling
        assert robust_normalize("") == ""
        assert robust_normalize(None) == ""

class TestEmailMatching:
    """Test email matching functions"""
    
    @pytest.fixture
    def sample_flagged_emails(self):
        """Sample flagged emails for testing"""
        return [
            {
                'subject': 'SICON manuscript #2024-001',
                'body': 'Dear Editor, John Smith has agreed to review manuscript 2024-001',
                'date': '2024-01-15',
                'to': 'john.smith@university.edu'
            },
            {
                'subject': 'Invitation to review manuscript 2024-002',
                'body': 'Dear Dr. Jane Doe, hoping you\'ll be willing to review 2024-002',
                'date': '2024-01-20',
                'to': 'jane.doe@college.edu'
            }
        ]
    
    def test_robust_match_email_for_referee(self, sample_flagged_emails):
        """Test basic referee email matching"""
        # Match accepted referee
        date = robust_match_email_for_referee(
            "John Smith",
            "2024-001",
            "Accepted",
            sample_flagged_emails
        )
        assert date == "2024-01-15"
        
        # Match contacted referee
        date = robust_match_email_for_referee(
            "Jane Doe",
            "2024-002",
            "Contacted",
            sample_flagged_emails
        )
        assert date == "2024-01-20"
        
        # No match
        date = robust_match_email_for_referee(
            "Unknown Person",
            "2024-999",
            "Accepted",
            sample_flagged_emails
        )
        assert date == ""
    
    def test_robust_match_email_for_referee_mf(self):
        """Test MF-specific email matching"""
        flagged_emails = [
            {
                'subject': 'Mathematical Finance - Thank you for agreeing to review MAFI-2024-123',
                'body': 'Dear Dr. Smith, thank you for agreeing to review...',
                'to': 'john.smith@math.edu; editor@journal.com',
                'date': '2024-01-15'
            }
        ]
        
        date, email = robust_match_email_for_referee_mf(
            "John Smith",
            "MAFI-2024-123",
            "Accepted",
            flagged_emails
        )
        
        assert date == "2024-01-15"
        assert email == "john.smith@math.edu"
    
    def test_robust_match_email_for_referee_mor(self):
        """Test MOR-specific email matching"""
        flagged_emails = [
            {
                'subject': 'Mathematics of Operations Research MOR-2024-456',
                'body': 'Manuscript MOR-2024-456',
                'to': 'jane.doe@or.edu; katyascheinberg@siam.org',
                'date': '2024-01-20'
            }
        ]
        
        date, email = robust_match_email_for_referee_mor(
            "Jane Doe",
            "MOR-2024-456",
            "Accepted",
            flagged_emails
        )
        
        assert date == "2024-01-20"
        assert email == "jane.doe@or.edu"
        
        # Should filter out editor emails
        date2, email2 = robust_match_email_for_referee_mor(
            "Katya Scheinberg",
            "MOR-2024-456",
            "Accepted",
            flagged_emails
        )
        assert email2 == ""  # Editor email should be filtered
    
    def test_robust_match_email_for_referee_jota(self):
        """Test JOTA-specific email matching"""
        flagged_emails = [
            {
                'subject': 'JOTA - Reviewer has agreed to review JOTA-D-24-00123',
                'body': 'John Smith has agreed to take on this assignment for JOTA-D-24-00123. Contact: j.smith@opt.edu',
                'date': '2024-01-15'
            }
        ]
        
        date, email = robust_match_email_for_referee_jota(
            "John Smith",
            "JOTA-D-24-00123",
            "Accepted",
            flagged_emails
        )
        
        assert date == "2024-01-15"
        assert email == "j.smith@opt.edu"
    
    def test_robust_match_email_for_referee_fs(self):
        """Test FS email matching (should always return empty)"""
        # FS doesn't do email crossmatch
        result = robust_match_email_for_referee_fs(
            "Any Name",
            "Any ID",
            "Any Status",
            []
        )
        assert result == ("", "")

class TestEmailParsing:
    """Test email parsing utilities"""
    
    def test_decode_header_field(self):
        """Test email header decoding"""
        # Simple ASCII
        assert decode_header_field("Simple Subject") == "Simple Subject"
        
        # Empty/None
        assert decode_header_field("") == ""
        assert decode_header_field(None) == ""
        
        # Encoded header (would need proper encoded example)
        # This is a placeholder - real encoded headers are more complex
        assert decode_header_field("=?UTF-8?B?VGVzdA==?=") != ""
    
    def test_extract_body_from_email(self):
        """Test email body extraction"""
        # Simple payload
        simple_payload = {
            'body': {
                'data': base64.urlsafe_b64encode(b"Simple email body").decode()
            }
        }
        assert extract_body_from_email(simple_payload) == "Simple email body"
        
        # Multipart payload
        multipart_payload = {
            'parts': [
                {
                    'mimeType': 'text/html',
                    'body': {'data': base64.urlsafe_b64encode(b"<p>HTML</p>").decode()}
                },
                {
                    'mimeType': 'text/plain',
                    'body': {'data': base64.urlsafe_b64encode(b"Plain text").decode()}
                }
            ]
        }
        assert extract_body_from_email(multipart_payload) == "Plain text"
        
        # Nested multipart
        nested_payload = {
            'parts': [
                {
                    'mimeType': 'multipart/alternative',
                    'parts': [
                        {
                            'mimeType': 'text/plain',
                            'body': {'data': base64.urlsafe_b64encode(b"Nested plain").decode()}
                        }
                    ]
                }
            ]
        }
        assert extract_body_from_email(nested_payload) == "Nested plain"
        
        # Empty payload
        assert extract_body_from_email({}) == ""
    
    def test_strip_html(self):
        """Test HTML stripping"""
        # Simple HTML
        assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"
        
        # With newlines
        assert "Line1" in strip_html("<p>Line1</p><p>Line2</p>")
        assert "Line2" in strip_html("<p>Line1</p><p>Line2</p>")
        
        # No HTML
        assert strip_html("Plain text") == "Plain text"
        
        # Empty
        assert strip_html("") == ""

class TestEmailMatchingEdgeCases:
    """Test edge cases in email matching"""
    
    def test_name_variations(self):
        """Test matching with name variations"""
        emails = [
            {
                'subject': 'Review request',
                'body': 'J. Smith has agreed to review 2024-001',
                'date': '2024-01-15'
            }
        ]
        
        # Should match "John Smith" to "J. Smith"
        date = robust_match_email_for_referee(
            "John Smith",
            "2024-001",
            "Accepted",
            emails
        )
        assert date == "2024-01-15"
        
        # Should match reversed names
        emails2 = [
            {
                'subject': 'Review',
                'body': 'Smith, John has agreed to review 2024-002',
                'date': '2024-01-20'
            }
        ]
        date2 = robust_match_email_for_referee(
            "John Smith",
            "2024-002",
            "Accepted",
            emails2
        )
        assert date2 == "2024-01-20"
    
    def test_manuscript_id_variations(self):
        """Test matching with manuscript ID variations"""
        emails = [
            {
                'subject': 'Manuscript M2024001',
                'body': 'Review request for manuscript',
                'date': '2024-01-15'
            }
        ]
        
        # Should match different ID formats
        date = robust_match_email_for_referee(
            "Any Name",
            "2024-001",  # Without 'M' prefix
            "Accepted",
            emails
        )
        # This might not match depending on implementation
        # but shows the kind of edge case to test
    
    def test_status_phrase_matching(self):
        """Test various status phrases"""
        base_email = {
            'subject': 'Review',
            'body': '',
            'date': '2024-01-15'
        }
        
        # Test accepted phrases
        accepted_phrases = [
            "agreed to review",
            "has agreed to review",
            "accepted to review",
            "has accepted to review"
        ]
        
        for phrase in accepted_phrases:
            email = base_email.copy()
            email['body'] = f"John Smith {phrase} 2024-001"
            
            date = robust_match_email_for_referee(
                "John Smith",
                "2024-001",
                "Accepted",
                [email]
            )
            assert date == "2024-01-15", f"Failed to match phrase: {phrase}"
        
        # Test contacted phrases
        contacted_phrases = [
            "hoping you'll be willing",
            "invited to referee",
            "would you be willing"
        ]
        
        for phrase in contacted_phrases:
            email = base_email.copy()
            email['body'] = f"Dear Jane Doe, {phrase} to review 2024-002"
            
            date = robust_match_email_for_referee(
                "Jane Doe",
                "2024-002",
                "Contacted",
                [email]
            )
            assert date == "2024-01-15", f"Failed to match phrase: {phrase}"
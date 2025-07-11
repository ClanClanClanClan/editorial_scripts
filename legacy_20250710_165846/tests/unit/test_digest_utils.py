"""
Unit tests for digest utility functions
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from core.digest_utils import (
    titlecase_name,
    european_date,
    days_ago,
    time_since,
    normalize_ref_status,
    compute_lateness,
    build_urgent_report_html,
    get_ref_date,
    get_ref_email,
    get_current_stage,
    build_html_digest,
    collect_unmatched_and_urgent
)

class TestTextFormatting:
    """Test text formatting utilities"""
    
    def test_titlecase_name(self):
        """Test name title casing"""
        assert titlecase_name("john doe") == "John Doe"
        assert titlecase_name("JANE SMITH") == "Jane Smith"
        assert titlecase_name("jean-pierre martin") == "Jean-pierre Martin"
        assert titlecase_name("o'brien") == "O'brien"
        
        # Remove trailing numbers
        assert titlecase_name("John Doe #123") == "John Doe"
        
        # Handle empty/None
        assert titlecase_name("") == ""
        assert titlecase_name(None) == ""
    
    def test_european_date(self):
        """Test European date formatting"""
        assert european_date("2024-01-15") == "15/01/2024"
        assert european_date("2024-12-31") == "31/12/2024"
        
        # ISO datetime
        assert european_date("2024-01-15T10:30:00") == "15/01/2024"
        
        # Invalid date
        assert european_date("invalid") == "invalid"
        
        # Empty/None
        assert european_date("") == ""
        assert european_date(None) == ""
    
    def test_days_ago(self):
        """Test days ago calculation"""
        # Recent date
        recent = (datetime.now() - timedelta(days=5)).isoformat()
        assert days_ago(recent) == 5
        
        # Today
        today = datetime.now().isoformat()
        assert days_ago(today) == 0
        
        # Future date (negative days)
        future = (datetime.now() + timedelta(days=3)).isoformat()
        assert days_ago(future) == -3
        
        # Invalid date
        assert days_ago("invalid") is None
        assert days_ago("") is None
        assert days_ago(None) is None
    
    def test_time_since(self):
        """Test human-readable time since"""
        # Various time periods
        assert time_since(datetime.now().isoformat()) == "today"
        
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        assert "1 weeks" in time_since(week_ago) or "7 days" in time_since(week_ago)
        
        month_ago = (datetime.now() - timedelta(days=35)).isoformat()
        result = time_since(month_ago)
        assert "weeks" in result or "month" in result
        
        # Invalid
        assert time_since("invalid") == ""
        assert time_since("") == ""

class TestStatusHandling:
    """Test referee status handling"""
    
    def test_normalize_ref_status(self):
        """Test status normalization"""
        # Accepted variations
        assert normalize_ref_status("agreed") == "Accepted"
        assert normalize_ref_status("accepted") == "Accepted"
        assert normalize_ref_status("overdue") == "Accepted"
        assert normalize_ref_status("AGREED") == "Accepted"
        
        # Contacted variations
        assert normalize_ref_status("contacted") == "Contacted"
        assert normalize_ref_status("pending") == "Contacted"
        assert normalize_ref_status("PENDING") == "Contacted"
        
        # Other statuses
        assert normalize_ref_status("declined") == "Declined"
        assert normalize_ref_status("unknown") == "Unknown"
        
        # Empty/None
        assert normalize_ref_status("") == ""
        assert normalize_ref_status(None) == ""
    
    def test_compute_lateness(self):
        """Test lateness computation"""
        # Overdue accepted review
        past_due = (datetime.now() - timedelta(days=5)).isoformat()
        assert compute_lateness("Accepted", past_due) == "5 days late"
        
        # Due today
        today = datetime.now().isoformat()
        assert compute_lateness("Accepted", today) == "Due today"
        
        # Future due date (not late)
        future = (datetime.now() + timedelta(days=5)).isoformat()
        assert compute_lateness("Accepted", future) == ""
        
        # Non-accepted status (no lateness)
        assert compute_lateness("Contacted", past_due) == ""
        
        # No due date
        assert compute_lateness("Accepted", None) == ""
        assert compute_lateness("Accepted", "") == ""
    
    def test_get_current_stage(self):
        """Test manuscript stage determination"""
        # All assigned
        referees_all_accepted = [
            {"Status": "Accepted"},
            {"Status": "Accepted"}
        ]
        assert get_current_stage(referees_all_accepted) == "All Referees Assigned"
        
        # Some pending
        referees_mixed = [
            {"Status": "Accepted"},
            {"Status": "Contacted"},
            {"Status": "Accepted"}
        ]
        assert get_current_stage(referees_mixed) == "Pending Referee Assignment"
        
        # Empty referees
        assert get_current_stage([]) == ""
        assert get_current_stage(None) == ""

class TestUrgentReporting:
    """Test urgent report generation"""
    
    def test_build_urgent_report_html(self):
        """Test urgent report HTML generation"""
        urgent_refs = [
            ("MS-001", "John Doe", "Overdue", "2024-01-01", "2024-01-15"),
            ("MS-002", "Jane Smith", "Accepted", "2024-01-05", "2024-01-20")
        ]
        
        html = build_urgent_report_html(urgent_refs)
        
        assert "URGENT: Action Required" in html
        assert "John Doe" in html
        assert "MS-001" in html
        assert "01/01/2024" in html  # European date format
        assert "15/01/2024" in html
        
        # Empty list
        assert build_urgent_report_html([]) == ""
        assert build_urgent_report_html(None) == ""

class TestRefereeDataExtraction:
    """Test referee data extraction functions"""
    
    def test_get_ref_date(self):
        """Test referee date extraction"""
        # Referee with accepted date
        ref = {
            "Referee Name": "John Doe",
            "Contacted Date": "2024-01-01",
            "Accepted Date": "2024-01-03"
        }
        
        # Should return accepted date if available
        date = get_ref_date(ref, "MS-001", "Accepted", [], Mock())
        assert date == "2024-01-03"
        
        # Only contacted date
        ref2 = {
            "Referee Name": "Jane Doe",
            "Contacted Date": "2024-01-05",
            "Accepted Date": ""
        }
        date2 = get_ref_date(ref2, "MS-002", "Contacted", [], Mock())
        assert date2 == "2024-01-05"
        
        # No dates - use match function
        ref3 = {"Referee Name": "Bob Smith"}
        mock_match = Mock(return_value="2024-01-10")
        date3 = get_ref_date(ref3, "MS-003", "Accepted", [], mock_match)
        assert date3 == "2024-01-10"
    
    def test_get_ref_email(self):
        """Test referee email extraction"""
        # Various field names
        ref1 = {"Referee Email": "john@test.com"}
        assert get_ref_email(ref1, [], "MS-001", "Accepted", Mock()) == "john@test.com"
        
        ref2 = {"Email": "jane@test.com"}
        assert get_ref_email(ref2, [], "MS-002", "Accepted", Mock()) == "jane@test.com"
        
        ref3 = {"email": "bob@test.com"}
        assert get_ref_email(ref3, [], "MS-003", "Accepted", Mock()) == "bob@test.com"
        
        # No email
        ref4 = {"Referee Name": "No Email"}
        assert get_ref_email(ref4, [], "MS-004", "Accepted", Mock()) == ""

class TestDigestGeneration:
    """Test HTML digest generation"""
    
    def test_build_html_digest_basic(self):
        """Test basic digest HTML generation"""
        manuscripts = [
            {
                "Manuscript #": "TEST-001",
                "Title": "Test Paper",
                "Contact Author": "Test Author",
                "Current Stage": "Under Review",
                "Referees": [
                    {
                        "Referee Name": "John Reviewer",
                        "Status": "Accepted",
                        "Referee Email": "john@test.com",
                        "Accepted Date": "2024-01-01",
                        "Due Date": "2024-02-01"
                    }
                ]
            }
        ]
        
        html = build_html_digest(
            "TEST",
            manuscripts,
            [],  # flagged_emails
            [],  # unmatched
            [],  # urgent
            Mock()  # match_func
        )
        
        assert "TEST" in html
        assert "TEST-001" in html
        assert "Test Paper" in html
        assert "John Reviewer" in html
        assert "Accepted" in html
    
    def test_collect_unmatched_and_urgent(self):
        """Test collecting unmatched and urgent referees"""
        manuscripts = [
            {
                "Manuscript #": "MS-001",
                "Title": "Paper 1",
                "Referees": [
                    {
                        "Referee Name": "Urgent Referee",
                        "Status": "Accepted",
                        "Accepted Date": (datetime.now() - timedelta(days=130)).isoformat(),
                        "Due Date": (datetime.now() - timedelta(days=10)).isoformat()
                    },
                    {
                        "Referee Name": "Normal Referee",
                        "Status": "Accepted",
                        "Accepted Date": datetime.now().isoformat(),
                        "Due Date": (datetime.now() + timedelta(days=20)).isoformat()
                    }
                ]
            }
        ]
        
        # Mock match function that returns empty for first referee
        def mock_match(name, ms_id, status, emails):
            if name == "Urgent Referee":
                return ""  # No email match
            return "matched@test.com"
        
        unmatched, urgent = collect_unmatched_and_urgent(
            manuscripts,
            [],  # flagged_emails
            mock_match
        )
        
        # Should have one unmatched
        assert len(unmatched) == 1
        assert unmatched[0][1] == "Urgent Referee"
        
        # Should have one urgent (old accepted + overdue)
        assert len(urgent) == 1
        assert urgent[0][1] == "Urgent Referee"
    
    def test_journal_specific_formatting(self):
        """Test journal-specific digest formatting"""
        # FS has different columns
        fs_manuscripts = [
            {
                "Manuscript #": "FS-001",
                "Title": "FS Paper",
                "Contact Author": "FS Author",
                "Current Stage": "Review",
                "Referee Name": "FS Referee",
                "Status": "Accepted",
                "Referee Email": "fs@test.com",
                "Accepted Date": "2024-01-01",
                "Due Date": "2024-02-01"
            }
        ]
        
        fs_html = build_html_digest(
            "FS",
            fs_manuscripts,
            [],
            [],
            [],
            Mock()
        )
        
        # Should include Contact Author column for FS
        assert "Contact Author" in fs_html
        assert "FS Author" in fs_html
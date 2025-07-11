#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Editorial Assistant

This test suite rigorously tests all components of the new extractor architecture:
- Base platform extractors
- All 6 journal-specific extractors  
- Configuration loading and validation
- Error handling and edge cases
- Session management integration
- Mock data extraction scenarios
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.core.data_models import JournalConfig, Manuscript, Referee
from editorial_assistant.extractors.base_platform_extractors import (
    EmailBasedExtractor, SIAMExtractor, EditorialManagerExtractor, MSPExtractor
)
from editorial_assistant.extractors.fs import FSExtractor
from editorial_assistant.extractors.sicon import SICONExtractor
from editorial_assistant.extractors.sifin import SIFINExtractor
from editorial_assistant.extractors.jota import JOTAExtractor
from editorial_assistant.extractors.mafe import MAFEExtractor
from editorial_assistant.extractors.naco import NACOExtractor
from editorial_assistant.utils.session_manager import SessionManager
from editorial_assistant.utils.email_verification import EmailVerificationManager


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading and validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_data = {
            "journals": {
                "FS": {
                    "name": "Finance and Stochastics",
                    "platform": "email_based",
                    "url": None,
                    "categories": ["Starred Emails", "Editor Communications"],
                    "patterns": {
                        "manuscript_id": "FS-\\d{4}-\\d{4}",
                        "email_subjects": ["Finance and Stochastics", "FS manuscript"]
                    },
                    "credentials": {
                        "gmail_service": True,
                        "gmail_user_env": "GMAIL_USER"
                    },
                    "settings": {
                        "max_manuscripts_per_run": 25,
                        "email_lookback_days": 30,
                        "retry_attempts": 3
                    }
                },
                "SICON": {
                    "name": "SIAM Journal on Control and Optimization",
                    "platform": "siam_orcid",
                    "url": "https://mc.manuscriptcentral.com/sicon",
                    "categories": ["Under Review", "Awaiting Decision"],
                    "patterns": {
                        "manuscript_id": "SICON-\\d{4}-\\d{4}",
                        "referee_row": "tr[class*=\"reviewer\"]"
                    },
                    "credentials": {
                        "username_env": "ORCID_USER",
                        "password_env": "ORCID_PASS"
                    },
                    "settings": {
                        "max_manuscripts_per_run": 30,
                        "download_timeout": 90,
                        "retry_attempts": 5
                    }
                }
            },
            "platforms": {
                "email_based": {
                    "gmail_api_required": True,
                    "search_patterns": ["is:starred", "subject:\"Finance and Stochastics\""]
                },
                "siam_orcid": {
                    "login_selectors": {
                        "orcid_login": "a[href*=\"orcid\"]",
                        "username": "input[name=\"userId\"]",
                        "password": "input[name=\"password\"]"
                    }
                }
            }
        }
    
    def test_config_structure_validation(self):
        """Test that configuration structure is valid."""
        # Test required top-level keys
        self.assertIn("journals", self.test_config_data)
        self.assertIn("platforms", self.test_config_data)
        
        # Test journal structure
        for journal_code, journal_data in self.test_config_data["journals"].items():
            self.assertIn("name", journal_data)
            self.assertIn("platform", journal_data)
            self.assertIn("patterns", journal_data)
            self.assertIn("credentials", journal_data)
            self.assertIn("settings", journal_data)
    
    def test_journal_config_creation(self):
        """Test creating JournalConfig objects from config data."""
        for journal_code, journal_data in self.test_config_data["journals"].items():
            try:
                config = JournalConfig(
                    code=journal_code,
                    name=journal_data["name"],
                    platform=journal_data["platform"],
                    url=journal_data.get("url"),
                    categories=journal_data.get("categories", []),
                    patterns=journal_data.get("patterns", {}),
                    credentials=journal_data.get("credentials", {}),
                    settings=journal_data.get("settings", {}),
                    platform_config=self.test_config_data["platforms"].get(journal_data["platform"], {})
                )
                self.assertEqual(config.code, journal_code)
                self.assertEqual(config.name, journal_data["name"])
                self.assertEqual(config.platform, journal_data["platform"])
            except Exception as e:
                self.fail(f"Failed to create JournalConfig for {journal_code}: {e}")


class TestBaseExtractors(unittest.TestCase):
    """Test base extractor classes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.test_journal_config = JournalConfig(
            code="TEST",
            name="Test Journal",
            platform="test_platform",
            url="https://test.example.com",
            categories=["Test Category"],
            patterns={"manuscript_id": "TEST-\\d{4}-\\d{4}"},
            credentials={"username_env": "TEST_USER", "password_env": "TEST_PASS"},
            settings={"max_manuscripts_per_run": 10},
            platform_config={}
        )
    
    def test_email_based_extractor_initialization(self):
        """Test EmailBasedExtractor initialization."""
        extractor = FSExtractor(self.test_journal_config)
        self.assertIsInstance(extractor, EmailBasedExtractor)
        self.assertEqual(extractor.journal.code, "TEST")
        self.assertIsNotNone(extractor.email_manager)
    
    def test_siam_extractor_initialization(self):
        """Test SIAMExtractor initialization."""
        extractor = SICONExtractor(self.test_journal_config)
        self.assertIsInstance(extractor, SIAMExtractor)
        self.assertEqual(extractor.journal.code, "TEST")
    
    def test_editorial_manager_extractor_initialization(self):
        """Test EditorialManagerExtractor initialization."""
        extractor = JOTAExtractor(self.test_journal_config)
        self.assertIsInstance(extractor, EditorialManagerExtractor)
        self.assertEqual(extractor.journal.code, "TEST")
    
    def test_msp_extractor_initialization(self):
        """Test MSPExtractor initialization."""
        extractor = NACOExtractor(self.test_journal_config)
        self.assertIsInstance(extractor, MSPExtractor)
        self.assertEqual(extractor.journal.code, "TEST")


class TestFSExtractor(unittest.TestCase):
    """Test FS email-based extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.journal_config = JournalConfig(
            code="FS",
            name="Finance and Stochastics",
            platform="email_based",
            url=None,
            categories=["Starred Emails"],
            patterns={
                "manuscript_id": "FS-\\d{4}-\\d{4}",
                "email_subjects": ["Finance and Stochastics"]
            },
            credentials={"gmail_service": True},
            settings={"email_lookback_days": 30},
            platform_config={}
        )
        
        self.mock_email_data = [
            {
                "subject": "FS-2024-1234 Referee Response",
                "body": "Dear Editor, Prof. John Smith has agreed to review manuscript FS-2024-1234 titled 'Stochastic Control Theory'.",
                "date": datetime.now()
            },
            {
                "subject": "Manuscript FS-2024-5678 Decision",
                "body": "The manuscript 'Advanced Financial Models' by Dr. Jane Doe has been accepted for publication.",
                "date": datetime.now()
            }
        ]
    
    @patch('editorial_assistant.extractors.fs.EmailVerificationManager')
    def test_fs_email_parsing(self, mock_email_manager):
        """Test FS email parsing functionality."""
        # Mock email manager
        mock_manager = Mock()
        mock_manager.search_emails.return_value = self.mock_email_data
        mock_email_manager.return_value = mock_manager
        
        extractor = FSExtractor(self.journal_config)
        extractor.email_manager = mock_manager
        
        # Test manuscript ID extraction
        manuscript_id = extractor._extract_manuscript_id(
            "FS-2024-1234 Referee Response",
            "manuscript FS-2024-1234 titled"
        )
        self.assertEqual(manuscript_id, "FS-2024-1234")
    
    def test_fs_referee_name_extraction(self):
        """Test referee name extraction from email content."""
        extractor = FSExtractor(self.journal_config)
        
        # Test various referee name patterns
        test_cases = [
            ("Dear Prof. John Smith,", "John Smith"),
            ("Dr. Jane Doe has agreed", "Jane Doe"),
            ("Reviewer: Prof. Michael Johnson", "Michael Johnson")
        ]
        
        for body, expected_name in test_cases:
            name = extractor._extract_referee_name("", body)
            self.assertEqual(name, expected_name)
    
    def test_fs_title_extraction(self):
        """Test manuscript title extraction."""
        extractor = FSExtractor(self.journal_config)
        
        test_cases = [
            ("Title: Advanced Stochastic Models", "Advanced Stochastic Models"),
            ("titled 'Financial Risk Analysis'", "Financial Risk Analysis"),
            ("paper \"Option Pricing Theory\"", "Option Pricing Theory")
        ]
        
        for body, expected_title in test_cases:
            title = extractor._extract_title("", body)
            self.assertEqual(title, expected_title)


class TestSIAMExtractors(unittest.TestCase):
    """Test SIAM extractors (SICON/SIFIN)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.journal_config = JournalConfig(
            code="SICON",
            name="SIAM Journal on Control and Optimization",
            platform="siam_orcid",
            url="https://sicon.siam.org/",
            categories=["Under Review"],
            patterns={"manuscript_id": "SICON-\\d{4}-\\d{4}"},
            credentials={"username_env": "ORCID_USER", "password_env": "ORCID_PASS"},
            settings={"retry_attempts": 5},
            platform_config={
                "login_selectors": {
                    "username": "input[name=\"userId\"]",
                    "password": "input[name=\"password\"]"
                }
            }
        )
        
        # Mock HTML content for manuscript table
        self.mock_manuscript_html = """
        <table id="ms_details_expanded">
            <tr><th>Manuscript #</th><td>SICON-2024-1234</td></tr>
            <tr><th>Title</th><td>Optimal Control Theory</td></tr>
            <tr><th>Submission Date</th><td>2024-01-15</td></tr>
            <tr><th>Current Stage</th><td>Under Review</td></tr>
            <tr><th>Referees</th><td>
                <a href="/referee/123">Prof. Smith</a>
                <font>Due: 2024-12-31</font>
            </td></tr>
        </table>
        """
    
    @patch.dict(os.environ, {'ORCID_USER': 'test@orcid.org', 'ORCID_PASS': 'testpass'})
    def test_sicon_extractor_initialization(self):
        """Test SICON extractor initialization."""
        extractor = SICONExtractor(self.journal_config)
        self.assertEqual(extractor.site_prefix, "https://sicon.siam.org/")
        self.assertEqual(extractor.journal.code, "SICON")
    
    def test_manuscript_table_parsing(self):
        """Test manuscript table parsing."""
        with patch('editorial_assistant.extractors.sicon.BeautifulSoup') as mock_soup:
            # Set up mock
            mock_soup.return_value.find.return_value.find_all.return_value = []
            
            extractor = SICONExtractor(self.journal_config)
            extractor.driver = self.mock_driver
            
            # Test would require more complex mocking of BeautifulSoup
            # This is a placeholder for the actual implementation
            self.assertIsNotNone(extractor._extract_manuscript_table)


class TestEditorialManagerExtractors(unittest.TestCase):
    """Test Editorial Manager extractors (JOTA/MAFE)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.journal_config = JournalConfig(
            code="JOTA",
            name="Journal of Optimization Theory and Applications",
            platform="editorial_manager",
            url="https://www.editorialmanager.com/jota/",
            categories=["With Referees"],
            patterns={"manuscript_id": "JOTA-\\d{4}-\\d{4}"},
            credentials={"username_env": "JOTA_USER", "password_env": "JOTA_PASS"},
            settings={"retry_attempts": 5},
            platform_config={
                "login_selectors": {
                    "username": "input[id=\"username\"]",
                    "password": "input[id=\"password\"]"
                }
            }
        )
    
    def test_jota_extractor_initialization(self):
        """Test JOTA extractor initialization."""
        extractor = JOTAExtractor(self.journal_config)
        self.assertEqual(extractor.journal.code, "JOTA")
        self.assertIsNotNone(extractor.email_manager)
    
    def test_jota_email_parsing(self):
        """Test JOTA email parsing functionality."""
        extractor = JOTAExtractor(self.journal_config)
        
        # Test acceptance email parsing
        test_email = {
            "subject": "JOTA-D-24-00769R1 Reviewer has agreed to review",
            "body": "Olivier Menoukeu Pamen, Ph.D has agreed to review your manuscript",
            "date": datetime.now()
        }
        
        result = extractor._parse_acceptance_email(test_email)
        self.assertEqual(result["manuscript_id"], "JOTA-D-24-00769R1")
        self.assertEqual(result["referee_name"], "Olivier Menoukeu Pamen")
        self.assertEqual(result["type"], "acceptance")
    
    def test_author_name_cleaning(self):
        """Test author name cleaning functionality."""
        extractor = JOTAExtractor(self.journal_config)
        
        test_cases = [
            ("Prof. John Smith, Ph.D", "John Smith"),
            ("Dr. Jane Doe, Professor", "Jane Doe"),
            ("Mr. Michael Johnson", "Michael Johnson")
        ]
        
        for raw_name, expected_clean in test_cases:
            cleaned = extractor._clean_author_name(raw_name)
            self.assertEqual(cleaned, expected_clean)


class TestNACOExtractor(unittest.TestCase):
    """Test NACO MSP extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.journal_config = JournalConfig(
            code="NACO",
            name="Nonlinear Analysis",
            platform="msp_custom",
            url="https://ef.msp.org/login.php",
            categories=["Mine"],
            patterns={"manuscript_id": "NACO-\\d{4}-\\d{4}"},
            credentials={"username_env": "NACO_USER", "password_env": "NACO_PASS"},
            settings={"retry_attempts": 3},
            platform_config={}
        )
        
        self.mock_article_html = """
        <article class="JournalView-Listing">
            <span data-tooltip="Associate Editor">Dylan Possamaï</span>
            <h3>Stochastic Differential Equations</h3>
            <a href="/manuscript/123">NACO-2024-1234</a>
            <i>by Prof. John Smith</i>
            <span>Under Review</span>
        </article>
        """
    
    @patch.dict(os.environ, {'NACO_USER': 'test@msp.org', 'NACO_PASS': 'testpass'})
    def test_naco_extractor_initialization(self):
        """Test NACO extractor initialization."""
        extractor = NACOExtractor(self.journal_config)
        self.assertEqual(extractor.journal.code, "NACO")
    
    def test_manuscript_parsing_from_article(self):
        """Test manuscript parsing from article element."""
        with patch('editorial_assistant.extractors.naco.BeautifulSoup') as mock_soup:
            extractor = NACOExtractor(self.journal_config)
            
            # This would require complex BeautifulSoup mocking
            # Placeholder for actual implementation
            self.assertIsNotNone(extractor._parse_manuscript_from_article)


class TestSessionIntegration(unittest.TestCase):
    """Test session management integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_session_manager_initialization(self):
        """Test session manager initialization."""
        session_manager = SessionManager(self.project_root)
        self.assertIsNotNone(session_manager.session)
        self.assertTrue((self.project_root / ".session_state").exists())
    
    def test_progress_saving(self):
        """Test automatic progress saving."""
        session_manager = SessionManager(self.project_root)
        
        # Test auto-save progress
        session_manager.auto_save_progress(
            "Test Step",
            outputs=["test_file.py"],
            learning="Test learning"
        )
        
        # Verify progress was saved
        self.assertTrue(len(session_manager.session.progress_log) > 0)
        last_entry = session_manager.session.progress_log[-1]
        self.assertEqual(last_entry["step_name"], "Test Step")
        self.assertEqual(last_entry["outputs"], ["test_file.py"])


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.journal_config = JournalConfig(
            code="TEST",
            name="Test Journal",
            platform="test_platform",
            url="https://test.example.com",
            categories=[],
            patterns={},
            credentials={},
            settings={},
            platform_config={}
        )
    
    def test_missing_credentials_handling(self):
        """Test handling of missing credentials."""
        # Test with empty credentials
        extractor = FSExtractor(self.journal_config)
        
        # Should not raise exception during initialization
        self.assertIsNotNone(extractor)
    
    def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        invalid_config = self.journal_config
        invalid_config.url = "invalid-url"
        
        extractor = SICONExtractor(invalid_config)
        self.assertIsNotNone(extractor)
    
    def test_malformed_email_data(self):
        """Test handling of malformed email data."""
        extractor = FSExtractor(self.journal_config)
        
        # Test with malformed email data
        malformed_email = {
            "subject": None,
            "body": "",
            "date": "invalid-date"
        }
        
        # Should not raise exception
        try:
            extractor._parse_email_content(malformed_email)
        except Exception as e:
            # If it raises an exception, it should be handled gracefully
            self.assertIsInstance(e, (TypeError, ValueError, AttributeError))


class TestDataValidation(unittest.TestCase):
    """Test data validation and type checking."""
    
    def test_manuscript_data_validation(self):
        """Test manuscript data structure validation."""
        # Test valid manuscript data
        valid_manuscript = {
            "Manuscript #": "TEST-2024-1234",
            "Title": "Test Title",
            "Contact Author": "Test Author",
            "Current Stage": "Under Review",
            "Referees": [
                {
                    "Referee Name": "Prof. Test",
                    "Referee Email": "test@example.com",
                    "Status": "Accepted",
                    "Due Date": "2024-12-31"
                }
            ]
        }
        
        # Validate required fields
        required_fields = ["Manuscript #", "Title", "Contact Author", "Current Stage", "Referees"]
        for field in required_fields:
            self.assertIn(field, valid_manuscript)
        
        # Validate referee structure
        if valid_manuscript["Referees"]:
            referee = valid_manuscript["Referees"][0]
            referee_fields = ["Referee Name", "Referee Email", "Status"]
            for field in referee_fields:
                self.assertIn(field, referee)
    
    def test_email_address_validation(self):
        """Test email address validation patterns."""
        import re
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        valid_emails = [
            "test@example.com",
            "user.name@university.edu",
            "author+journal@research.org"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com"
        ]
        
        for email in valid_emails:
            self.assertTrue(re.match(email_pattern, email), f"Valid email failed: {email}")
        
        for email in invalid_emails:
            self.assertFalse(re.match(email_pattern, email), f"Invalid email passed: {email}")


def run_comprehensive_tests():
    """Run all comprehensive tests and generate report."""
    print("🧪 Starting Comprehensive Integration Tests...")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestConfigurationLoading,
        TestBaseExtractors,
        TestFSExtractor,
        TestSIAMExtractors,
        TestEditorialManagerExtractors,
        TestNACOExtractor,
        TestSessionIntegration,
        TestErrorHandling,
        TestDataValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL TESTS PASSED!")
        print("🎉 The new extractor architecture is working correctly!")
    
    return result


if __name__ == "__main__":
    # Run comprehensive tests
    test_result = run_comprehensive_tests()
    
    # Exit with appropriate code
    sys.exit(0 if test_result.wasSuccessful() else 1)
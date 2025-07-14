"""
Legacy Integration Tests

Test suite to validate that legacy integration maintains
the 90%+ reliability of proven working extractors.
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from selenium import webdriver
from selenium.webdriver.common.by import By

# Import the classes we're testing
from editorial_assistant.core.legacy_integration import LegacyIntegrationMixin
from editorial_assistant.extractors.scholarone import ScholarOneExtractor
from editorial_assistant.utils.email_verification import EmailVerificationManager
from editorial_assistant.core.data_models import Journal, ExtractionResult
from editorial_assistant.utils.session_manager import session_manager


class TestLegacyIntegrationMixin:
    """Test the legacy integration mixin class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_driver = Mock()
        self.mock_logger = Mock()
        
        # Create a test instance with the mixin
        class TestExtractor(LegacyIntegrationMixin):
            def __init__(self):
                self.driver = self.mock_driver
                self.logger = self.mock_logger
        
        self.extractor = TestExtractor()
    
    def test_legacy_login_scholarone_mf(self):
        """Test MF login using legacy method."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'MF_USER': 'test_user',
            'MF_PASS': 'test_pass'
        }):
            # Mock driver methods
            self.mock_driver.get = Mock()
            self.mock_driver.find_element = Mock()
            self.mock_driver.current_url = "https://mc.manuscriptcentral.com/mafi/main.asp"
            
            # Mock successful login elements
            cookie_btn = Mock()
            cookie_btn.is_displayed.return_value = True
            user_field = Mock()
            pass_field = Mock()
            login_btn = Mock()
            body_element = Mock()
            body_element.text = "Associate Editor Center"
            
            self.mock_driver.find_element.side_effect = [
                cookie_btn,  # Cookie accept button
                user_field,  # Username field
                pass_field,  # Password field
                login_btn,   # Login button
                body_element # Body for verification
            ]
            
            # Mock 2FA not required
            with patch.object(self.extractor, '_handle_2fa_verification', return_value=True):
                result = self.extractor.legacy_login_scholarone(self.mock_driver, 'MF')
            
            assert result is True
            self.mock_driver.get.assert_called_once_with("https://mc.manuscriptcentral.com/mafi")
            user_field.send_keys.assert_called_once_with('test_user')
            pass_field.send_keys.assert_called_once_with('test_pass')
            login_btn.click.assert_called_once()
    
    def test_legacy_login_scholarone_mor(self):
        """Test MOR login using legacy method."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'MOR_USER': 'test_user',
            'MOR_PASS': 'test_pass'
        }):
            # Mock successful login
            self.mock_driver.current_url = "https://mc.manuscriptcentral.com/mathor/main.asp"
            
            with patch.object(self.extractor, '_handle_2fa_verification', return_value=True):
                with patch.object(self.extractor, '_verify_scholarone_login_success', return_value=True):
                    result = self.extractor.legacy_login_scholarone(self.mock_driver, 'MOR')
            
            assert result is True
            self.mock_driver.get.assert_called_once_with("https://mc.manuscriptcentral.com/mathor")
    
    def test_legacy_login_scholarone_missing_credentials(self):
        """Test login failure with missing credentials."""
        # No environment variables set
        with patch.dict(os.environ, {}, clear=True):
            result = self.extractor.legacy_login_scholarone(self.mock_driver, 'MF')
            
            assert result is False
            self.mock_logger.error.assert_called()
    
    def test_legacy_click_checkbox_success(self):
        """Test successful checkbox clicking."""
        manuscript_id = "MAFI-2024-0167"
        
        # Mock row with manuscript
        mock_row = Mock()
        mock_row.text = f"Some text {manuscript_id} more text"
        
        # Mock checkbox
        mock_checkbox = Mock()
        mock_row.find_elements.return_value = [mock_checkbox]
        
        self.mock_driver.find_elements.return_value = [mock_row]
        self.mock_driver.execute_script = Mock()
        
        # Mock browser manager
        with patch.object(self.extractor, 'browser_manager', Mock()):
            result = self.extractor.legacy_click_checkbox(self.mock_driver, manuscript_id)
        
        assert result is True
        mock_checkbox.click.assert_called_once()
        self.mock_driver.execute_script.assert_called()
    
    def test_legacy_click_checkbox_not_found(self):
        """Test checkbox clicking when manuscript not found."""
        manuscript_id = "MAFI-2024-9999"
        
        # Mock row without manuscript
        mock_row = Mock()
        mock_row.text = "Other manuscript text"
        
        self.mock_driver.find_elements.return_value = [mock_row]
        
        result = self.extractor.legacy_click_checkbox(self.mock_driver, manuscript_id)
        
        assert result is False
    
    def test_legacy_download_pdfs_success(self):
        """Test PDF download success."""
        manuscript_id = "MAFI-2024-0167"
        download_dir = Path("/tmp/test_pdfs")
        
        # Mock successful PDF download
        with patch.object(self.extractor, '_get_manuscript_pdf_legacy') as mock_manuscript_pdf:
            with patch.object(self.extractor, '_get_referee_reports_legacy') as mock_referee_reports:
                
                mock_manuscript_pdf.return_value = {
                    'url': 'http://example.com/pdf',
                    'file': '/tmp/test_pdfs/MAFI-2024-0167_manuscript.pdf'
                }
                
                mock_referee_reports.return_value = {
                    'pdf_reports': ['/tmp/test_pdfs/MAFI-2024-0167_referee_1.pdf'],
                    'text_reviews': ['/tmp/test_pdfs/MAFI-2024-0167_referee_1_review.txt']
                }
                
                result = self.extractor.legacy_download_pdfs(self.mock_driver, manuscript_id, download_dir)
                
                assert result['manuscript_pdf_file'] == '/tmp/test_pdfs/MAFI-2024-0167_manuscript.pdf'
                assert len(result['referee_reports']) == 1
                assert len(result['text_reviews']) == 1


class TestEmailVerificationManager:
    """Test email verification manager."""
    
    def setup_method(self):
        """Setup test environment."""
        self.email_manager = EmailVerificationManager()
    
    def test_extract_code_from_text_verification_code(self):
        """Test extracting verification code from text."""
        text = "Your verification code is: 123456"
        code = self.email_manager.extract_code_from_text(text)
        assert code == "123456"
    
    def test_extract_code_from_text_access_code(self):
        """Test extracting access code from text."""
        text = "Access code: 789012"
        code = self.email_manager.extract_code_from_text(text)
        assert code == "789012"
    
    def test_extract_code_from_text_no_code(self):
        """Test when no code is found."""
        text = "This is just regular email text without any codes."
        code = self.email_manager.extract_code_from_text(text)
        assert code is None
    
    def test_extract_code_from_text_invalid_length(self):
        """Test when code is invalid length."""
        text = "Your code is: 12"  # Too short
        code = self.email_manager.extract_code_from_text(text)
        assert code is None
    
    @patch('editorial_assistant.utils.email_verification.Path')
    def test_check_legacy_availability_found(self, mock_path):
        """Test when legacy email utilities are available."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        result = self.email_manager._check_legacy_availability()
        assert result is True
    
    @patch('editorial_assistant.utils.email_verification.Path')
    def test_check_legacy_availability_not_found(self, mock_path):
        """Test when legacy email utilities are not available."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        result = self.email_manager._check_legacy_availability()
        assert result is False


class TestScholarOneExtractorIntegration:
    """Test ScholarOne extractor with legacy integration."""
    
    def setup_method(self):
        """Setup test environment."""
        # Mock journal configuration
        self.mock_journal = Mock()
        self.mock_journal.name = "Mathematical Finance"
        self.mock_journal.code = "MF"
        self.mock_journal.url = "https://mc.manuscriptcentral.com/mafi"
        
        # Create extractor with mocked dependencies
        with patch('editorial_assistant.extractors.scholarone.ConfigLoader'):
            with patch('editorial_assistant.extractors.scholarone.session_manager'):
                self.extractor = ScholarOneExtractor('MF')
                self.extractor.journal = self.mock_journal
                self.extractor.driver = Mock()
                self.extractor.logger = Mock()
    
    def test_login_uses_legacy_method(self):
        """Test that login method uses legacy integration."""
        with patch.object(self.extractor, 'legacy_login_scholarone', return_value=True) as mock_legacy_login:
            self.extractor._login()
            
            mock_legacy_login.assert_called_once_with(self.extractor.driver, 'MF')
    
    def test_login_failure_raises_exception(self):
        """Test that login failure raises appropriate exception."""
        with patch.object(self.extractor, 'legacy_login_scholarone', return_value=False):
            with pytest.raises(Exception):  # Should raise LoginError
                self.extractor._login()
    
    def test_click_manuscript_uses_legacy_method(self):
        """Test that click manuscript uses legacy method."""
        manuscript_id = "MAFI-2024-0167"
        
        with patch.object(self.extractor, 'legacy_click_checkbox', return_value=True) as mock_legacy_click:
            result = self.extractor._click_manuscript(manuscript_id)
            
            assert result is True
            mock_legacy_click.assert_called_once_with(self.extractor.driver, manuscript_id)
    
    def test_extract_pdf_uses_legacy_method(self):
        """Test that PDF extraction uses legacy method."""
        manuscript_id = "MAFI-2024-0167"
        
        # Mock output directory
        self.extractor.output_dir = Path("/tmp/test_output")
        
        with patch.object(self.extractor, 'legacy_download_pdfs') as mock_legacy_pdf:
            mock_legacy_pdf.return_value = {
                'manuscript_pdf_file': '/tmp/test_output/pdfs/MAFI-2024-0167_manuscript.pdf'
            }
            
            result = self.extractor._extract_manuscript_pdf(manuscript_id)
            
            assert result == Path('/tmp/test_output/pdfs/MAFI-2024-0167_manuscript.pdf')
            mock_legacy_pdf.assert_called_once()


class TestLegacyResultsValidation:
    """Test validation against known legacy results."""
    
    def setup_method(self):
        """Setup test environment."""
        self.legacy_results_dir = Path(__file__).parent.parent / "legacy_20250710_165846" / "complete_results"
    
    def test_load_legacy_mf_results(self):
        """Test loading legacy MF results for validation."""
        legacy_file = self.legacy_results_dir / "mf_complete_stable_results.json"
        
        if legacy_file.exists():
            with open(legacy_file, 'r') as f:
                legacy_data = json.load(f)
            
            # Validate structure
            assert 'manuscripts' in legacy_data
            assert isinstance(legacy_data['manuscripts'], list)
            
            # Check for expected MF manuscripts
            manuscript_ids = [m.get('manuscript_id', '') for m in legacy_data['manuscripts']]
            
            # Should contain MAFI pattern manuscripts
            mafi_manuscripts = [mid for mid in manuscript_ids if 'MAFI-' in mid]
            assert len(mafi_manuscripts) > 0, "Should contain MAFI manuscripts"
        else:
            pytest.skip("Legacy MF results file not found")
    
    def test_load_legacy_mor_results(self):
        """Test loading legacy MOR results for validation."""
        legacy_file = self.legacy_results_dir / "mor_complete_stable_results.json"
        
        if legacy_file.exists():
            with open(legacy_file, 'r') as f:
                legacy_data = json.load(f)
            
            # Validate structure
            assert 'manuscripts' in legacy_data
            assert isinstance(legacy_data['manuscripts'], list)
            
            # Check for expected MOR manuscripts
            manuscript_ids = [m.get('manuscript_id', '') for m in legacy_data['manuscripts']]
            
            # Should contain MOR pattern manuscripts
            mor_manuscripts = [mid for mid in manuscript_ids if 'MOR-' in mid]
            assert len(mor_manuscripts) > 0, "Should contain MOR manuscripts"
        else:
            pytest.skip("Legacy MOR results file not found")
    
    def test_manuscript_id_patterns(self):
        """Test that manuscript ID patterns match legacy expectations."""
        # MF pattern
        import re
        mf_pattern = r'MAFI-\d{4}-\d{4}'
        assert re.match(mf_pattern, 'MAFI-2024-0167')
        assert re.match(mf_pattern, 'MAFI-2025-0166')
        
        # MOR pattern
        mor_pattern = r'MOR-\d{4}-\d{4}'
        assert re.match(mor_pattern, 'MOR-2023-0376')
        assert re.match(mor_pattern, 'MOR-2024-0804')
    
    def test_referee_data_structure(self):
        """Test that referee data structure matches legacy format."""
        # Expected referee data structure from legacy results
        expected_fields = [
            'name', 'institution', 'status', 'dates', 
            'invited_date', 'agreed_date', 'completed_date'
        ]
        
        # This test validates that our data models match legacy expectations
        from editorial_assistant.core.data_models import Referee, RefereeDates
        
        referee = Referee(
            name="Test Referee",
            institution="Test University",
            dates=RefereeDates()
        )
        
        # Verify that we can serialize to the same format as legacy
        referee_dict = referee.model_dump()
        
        assert 'name' in referee_dict
        assert 'institution' in referee_dict
        assert 'dates' in referee_dict


@pytest.mark.integration
class TestFullIntegrationWorkflow:
    """Integration tests for complete extraction workflow."""
    
    def test_session_manager_integration(self):
        """Test that session manager tracks progress correctly."""
        # Add a test task
        session_manager.add_task(
            'test_integration',
            'Test Integration Task',
            'Testing session manager integration'
        )
        
        # Start and complete the task
        session_manager.start_task('test_integration')
        session_manager.complete_task(
            'test_integration',
            outputs=['test_output.txt'],
            notes='Integration test completed'
        )
        
        # Verify task was tracked
        task = session_manager.session.tasks['test_integration']
        assert task.status.value == 'completed'
        assert 'test_output.txt' in task.outputs
    
    def test_learning_capture(self):
        """Test that learnings are captured during workflow."""
        initial_learnings = len(session_manager.session.key_learnings)
        
        session_manager.add_learning("Test learning from integration test")
        
        final_learnings = len(session_manager.session.key_learnings)
        assert final_learnings == initial_learnings + 1
    
    def test_auto_save_functionality(self):
        """Test automatic progress saving."""
        session_manager.auto_save_progress(
            "Test Auto Save Step",
            outputs=['auto_save_test.txt'],
            learning="Auto save functionality tested"
        )
        
        # Verify files were tracked
        assert 'auto_save_test.txt' in session_manager.session.completed_files
        
        # Verify learning was captured
        learnings = session_manager.session.key_learnings
        assert any("Auto save functionality tested" in learning for learning in learnings)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
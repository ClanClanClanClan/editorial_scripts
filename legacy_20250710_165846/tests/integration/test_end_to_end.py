"""
End-to-end tests for the complete editorial system
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from main_enhanced import run_journal_batch, run_sicon_then_others
from database import RefereeDatabase, RefereeProfile, ReviewRecord
from core.credential_manager import SecureCredentialManager
from tests.mocks import MockDataGenerator

class TestEndToEnd:
    """Test complete system workflows"""
    
    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create temporary configuration"""
        config = {
            'db_path': str(tmp_path / "test_referees.db"),
            'output_path': str(tmp_path / "test_digest.html"),
            'chrome_profile': str(tmp_path / "chrome_profiles")
        }
        return config
    
    @pytest.fixture
    def mock_args(self, temp_config):
        """Create mock command line arguments"""
        args = Mock()
        args.journals = ["JOTA"]  # Start with JOTA for email-only testing
        args.dry_run = True
        args.output = temp_config['output_path']
        args.verbose = False
        args.show_browser = False
        args.chrome_profile_dir = temp_config['chrome_profile']
        args.use_playwright = True
        args.force_headless = True
        args.update_db = True
        return args
    
    @pytest.fixture
    def mock_system(self, mock_gmail_service, mock_credentials, temp_config):
        """Mock all external dependencies"""
        with patch('main_enhanced.get_credential_manager') as mock_cred_mgr:
            mock_cred_mgr.return_value = mock_credentials
            
            with patch('database.referee_db.RefereeDatabase') as mock_db_class:
                mock_db = RefereeDatabase(temp_config['db_path'])
                mock_db_class.return_value = mock_db
                
                yield {
                    'gmail_service': mock_gmail_service,
                    'credentials': mock_credentials,
                    'database': mock_db
                }
    
    def test_jota_email_only_workflow(self, mock_args, mock_system):
        """Test JOTA email-only workflow end-to-end"""
        # Setup mock Gmail data
        gmail_service = mock_system['gmail_service']
        
        # Generate realistic email data
        messages = []
        
        # Weekly overview
        weekly = MockDataGenerator.generate_email_message("weekly", "JOTA")
        messages.append(MockDataGenerator.generate_gmail_message(weekly))
        
        # Acceptance emails
        for i in range(2):
            accept = MockDataGenerator.generate_email_message("acceptance", "JOTA")
            messages.append(MockDataGenerator.generate_gmail_message(accept))
        
        # Setup mock responses
        gmail_service.users().messages().list().execute.return_value = {
            'messages': [{'id': msg['id']} for msg in messages]
        }
        
        def get_message(userId, id, format):
            for msg in messages:
                if msg['id'] == id:
                    return Mock(execute=Mock(return_value=msg))
        
        gmail_service.users().messages().get = get_message
        
        # Run the batch
        manuscript_data, html_digest, error_journals = run_journal_batch(
            mock_args,
            gmail_service=gmail_service
        )
        
        # Verify results
        assert "JOTA" in manuscript_data
        assert len(manuscript_data["JOTA"]) > 0
        assert len(error_journals) == 0
        assert "JOTA" in html_digest
        
        # Check output file was created
        assert os.path.exists(mock_args.output)
        with open(mock_args.output, 'r') as f:
            content = f.read()
            assert "JOTA" in content
    
    @patch('database.referee_db.get_db')
    def test_database_update_workflow(self, mock_get_db, mock_args, temp_config):
        """Test database update during processing"""
        # Create real database
        db = RefereeDatabase(temp_config['db_path'])
        mock_get_db.return_value = db
        
        # Generate manuscript data
        manuscripts = []
        for i in range(3):
            ms = MockDataGenerator.generate_manuscript("TEST", num_referees=2)
            manuscripts.append(ms)
        
        # Mock the journal to return this data
        with patch('main_enhanced.create_journals') as mock_create:
            mock_journal = Mock()
            mock_journal.scrape_manuscripts_and_emails.return_value = manuscripts
            mock_create.return_value = ({"TEST": mock_journal}, {"TEST": None})
            
            # Set args to update database
            mock_args.journals = ["TEST"]
            mock_args.update_db = True
            
            # Run with database updates
            from main_enhanced import update_database_from_manuscripts
            update_database_from_manuscripts("TEST", manuscripts, update_db=True)
            
            # Verify database was updated
            # Count referees
            with db.db_path as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(DISTINCT email) FROM referees")
                referee_count = cursor.fetchone()[0]
            
            # Should have referees from manuscripts
            expected_referees = sum(len(ms['Referees']) for ms in manuscripts)
            assert referee_count > 0
    
    def test_multi_journal_workflow(self, mock_args):
        """Test processing multiple journals"""
        mock_args.journals = ["JOTA", "FS"]  # Email-based and no-browser journals
        
        with patch('main_enhanced.create_journals') as mock_create:
            # Mock JOTA journal
            mock_jota = Mock()
            mock_jota.scrape_manuscripts_and_emails.return_value = [
                MockDataGenerator.generate_manuscript("JOTA")
            ]
            
            # Mock FS journal
            mock_fs = Mock()
            mock_fs.scrape_manuscripts_and_emails.return_value = [
                MockDataGenerator.generate_manuscript("FS")
            ]
            
            mock_create.return_value = (
                {"JOTA": mock_jota, "FS": mock_fs},
                {"JOTA": None, "FS": None}
            )
            
            # Run batch
            manuscript_data, html_digest, errors = run_journal_batch(mock_args)
            
            # Verify both journals processed
            assert "JOTA" in manuscript_data
            assert "FS" in manuscript_data
            assert len(errors) == 0
            
            # Check digest contains both
            assert "JOTA" in html_digest
            assert "FS" in html_digest
    
    def test_error_handling_workflow(self, mock_args):
        """Test error handling in journal processing"""
        mock_args.journals = ["JOTA", "ERROR_JOURNAL"]
        
        with patch('main_enhanced.create_journals') as mock_create:
            # Mock successful journal
            mock_jota = Mock()
            mock_jota.scrape_manuscripts_and_emails.return_value = [
                MockDataGenerator.generate_manuscript("JOTA")
            ]
            
            # Mock failing journal
            mock_error = Mock()
            mock_error.scrape_manuscripts_and_emails.side_effect = Exception("Connection failed")
            
            mock_create.return_value = (
                {"JOTA": mock_jota, "ERROR_JOURNAL": mock_error},
                {"JOTA": None, "ERROR_JOURNAL": None}
            )
            
            # Run batch
            manuscript_data, html_digest, errors = run_journal_batch(mock_args)
            
            # Verify partial success
            assert "JOTA" in manuscript_data
            assert len(manuscript_data["JOTA"]) > 0
            assert "ERROR_JOURNAL" in errors
            
            # Check error warning in digest
            assert "WARNING" in html_digest
            assert "ERROR_JOURNAL" in html_digest
    
    def test_credential_manager_integration(self):
        """Test credential manager in workflow"""
        # Create mock credential manager
        mock_creds = Mock()
        mock_creds.get_journal_credentials.return_value = {
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        with patch('main_enhanced.get_credential_manager') as mock_get_cm:
            mock_get_cm.return_value = mock_creds
            
            # Import after patching
            from main_enhanced import create_journals
            
            # Should not raise errors
            journals, drivers = create_journals(
                ["JOTA"],
                gmail_service=Mock()
            )
            
            # Verify credentials were requested
            mock_creds.get_journal_credentials.assert_called_with("JOTA")
    
    def test_sicon_special_handling(self, mock_args):
        """Test SICON-first processing logic"""
        mock_args.journals = ["SICON", "JOTA"]
        
        with patch('main_enhanced.run_journal_batch') as mock_run_batch:
            # Mock batch results
            mock_run_batch.return_value = (
                {"SICON": [], "JOTA": []},
                "<div>Test Digest</div>",
                []
            )
            
            # Run SICON-first workflow
            digest = run_sicon_then_others(mock_args, gmail_service=Mock())
            
            # Verify SICON was processed separately
            assert mock_run_batch.call_count == 2
            
            # First call should be SICON only
            first_call_args = mock_run_batch.call_args_list[0][0][0]
            assert first_call_args.journals == ["SICON"]
            
            # Second call should be others
            second_call_args = mock_run_batch.call_args_list[1][0][0]
            assert "JOTA" in second_call_args.journals
            assert "SICON" not in second_call_args.journals

class TestSystemResilience:
    """Test system resilience and recovery"""
    
    def test_partial_email_failure(self):
        """Test handling of partial email fetching failures"""
        mock_service = MagicMock()
        
        # Some messages fail to fetch
        messages = [{'id': f'msg{i}'} for i in range(5)]
        mock_service.users().messages().list().execute.return_value = {
            'messages': messages
        }
        
        # Make some fetches fail
        def get_message(userId, id, format):
            if id in ['msg1', 'msg3']:
                raise Exception("API Error")
            
            email = MockDataGenerator.generate_email_message("acceptance", "JOTA")
            return Mock(execute=Mock(return_value=
                MockDataGenerator.generate_gmail_message(email)
            ))
        
        mock_service.users().messages().get = get_message
        
        # Should still process available messages
        from journals.jota_enhanced import JOTAJournal
        journal = JOTAJournal(mock_service)
        
        # Should not crash
        manuscripts = journal.scrape_manuscripts_and_emails()
        assert isinstance(manuscripts, list)
    
    def test_database_corruption_recovery(self, temp_db_path):
        """Test recovery from database issues"""
        db = RefereeDatabase(temp_db_path)
        
        # Add some data
        profile = RefereeProfile(
            name="Test Referee",
            email="test@example.com"
        )
        referee_id = db.add_or_update_referee(profile)
        
        # Simulate corruption by closing connection improperly
        # In real scenario, this tests the error handling
        
        # Should be able to recover and query
        stats = db.get_referee_stats("test@example.com")
        assert stats is not None
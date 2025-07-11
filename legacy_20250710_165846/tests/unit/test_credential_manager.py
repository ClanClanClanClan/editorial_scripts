"""
Unit tests for credential manager
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json
import os

from core.credential_manager import (
    CredentialProvider,
    OnePasswordProvider,
    KeyringProvider,
    EnvProvider,
    SecureCredentialManager,
    get_credential_manager,
    get_credential
)

class TestOnePasswordProvider:
    """Test 1Password CLI integration"""
    
    @patch('subprocess.run')
    def test_verify_cli_success(self, mock_run):
        """Test successful CLI verification"""
        # Mock successful version check
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "2.24.0"
        
        provider = OnePasswordProvider()
        assert provider.vault == "Editorial Scripts"
        assert mock_run.call_count == 2  # version + vault list
    
    @patch('subprocess.run')
    def test_verify_cli_not_installed(self, mock_run):
        """Test CLI not installed"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'op')
        
        with pytest.raises(RuntimeError, match="1Password CLI not installed"):
            OnePasswordProvider()
    
    @patch('subprocess.run')
    def test_get_credential_success(self, mock_run):
        """Test successful credential retrieval"""
        # Mock CLI verification
        mock_run.return_value.returncode = 0
        provider = OnePasswordProvider()
        
        # Mock credential retrieval
        mock_run.return_value.stdout = json.dumps({
            'value': 'test_password_123'
        })
        
        result = provider.get_credential('TestService', 'password')
        assert result == 'test_password_123'
    
    @patch('subprocess.run')
    def test_get_credential_not_found(self, mock_run):
        """Test credential not found"""
        # Mock CLI verification
        mock_run.return_value.returncode = 0
        provider = OnePasswordProvider()
        
        # Mock failed retrieval
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Item not found"
        
        result = provider.get_credential('NonExistent', 'password')
        assert result is None

class TestKeyringProvider:
    """Test system keyring integration"""
    
    @patch('keyring.get_password')
    def test_get_credential_success(self, mock_keyring):
        """Test successful keyring retrieval"""
        mock_keyring.return_value = 'keyring_password'
        
        provider = KeyringProvider()
        result = provider.get_credential('TestService', 'username')
        
        mock_keyring.assert_called_once_with('TestService', 'username')
        assert result == 'keyring_password'
    
    @patch('keyring.get_password')
    def test_get_credential_not_found(self, mock_keyring):
        """Test keyring credential not found"""
        mock_keyring.return_value = None
        
        provider = KeyringProvider()
        result = provider.get_credential('TestService', 'username')
        assert result is None

class TestEnvProvider:
    """Test environment variable provider"""
    
    def test_get_credential_exact_match(self, monkeypatch):
        """Test exact environment variable match"""
        monkeypatch.setenv('SICON_USERNAME', 'env_user')
        
        provider = EnvProvider()
        result = provider.get_credential('SICON', 'USERNAME')
        assert result == 'env_user'
    
    def test_get_credential_service_only(self, monkeypatch):
        """Test service-only environment variable"""
        monkeypatch.setenv('GMAIL', 'gmail_value')
        
        provider = EnvProvider()
        result = provider.get_credential('GMAIL', 'anything')
        assert result == 'gmail_value'
    
    def test_get_credential_not_found(self):
        """Test environment variable not found"""
        provider = EnvProvider()
        result = provider.get_credential('NONEXISTENT', 'VALUE')
        assert result is None

class TestSecureCredentialManager:
    """Test main credential manager"""
    
    @patch('subprocess.run')
    def test_auto_detect_providers(self, mock_run):
        """Test automatic provider detection"""
        # Mock 1Password not available
        mock_run.side_effect = subprocess.CalledProcessError(1, 'op')
        
        manager = SecureCredentialManager()
        
        # Should have KeyringProvider and EnvProvider
        assert len(manager.providers) == 2
        assert any(isinstance(p, KeyringProvider) for p in manager.providers)
        assert any(isinstance(p, EnvProvider) for p in manager.providers)
    
    def test_get_credential_chain(self):
        """Test credential retrieval through provider chain"""
        # Create mock providers
        provider1 = Mock()
        provider1.get_credential.return_value = None
        
        provider2 = Mock()
        provider2.get_credential.return_value = 'found_value'
        
        provider3 = Mock()
        provider3.get_credential.return_value = 'should_not_reach'
        
        manager = SecureCredentialManager(providers=[provider1, provider2, provider3])
        
        result = manager.get('TestService', 'password')
        
        assert result == 'found_value'
        provider1.get_credential.assert_called_once_with('TestService', 'password')
        provider2.get_credential.assert_called_once_with('TestService', 'password')
        provider3.get_credential.assert_not_called()
    
    def test_get_journal_credentials(self):
        """Test journal-specific credential retrieval"""
        mock_provider = Mock()
        mock_provider.get_credential.side_effect = lambda s, a: f"{s}_{a}_value"
        
        manager = SecureCredentialManager(providers=[mock_provider])
        
        # Test SICON credentials
        sicon_creds = manager.get_journal_credentials('SICON')
        assert sicon_creds['username'] == 'SICON_username_value'
        assert sicon_creds['password'] == 'SICON_password_value'
        
        # Test MOR credentials
        mor_creds = manager.get_journal_credentials('MOR')
        assert mor_creds['username'] == 'MOR_email_value'
        assert mor_creds['password'] == 'MOR_password_value'
    
    def test_get_email_credentials(self):
        """Test email credential retrieval"""
        mock_provider = Mock()
        mock_provider.get_credential.side_effect = {
            ('GMAIL', 'username'): 'test@gmail.com',
            ('GMAIL', 'app_password'): 'app_pass_123',
            ('RECIPIENT', 'email'): 'recipient@test.com'
        }.get
        
        manager = SecureCredentialManager(providers=[mock_provider])
        
        email_creds = manager.get_email_credentials()
        assert email_creds['email'] == 'test@gmail.com'
        assert email_creds['password'] == 'app_pass_123'
        assert email_creds['recipient'] == 'recipient@test.com'
    
    def test_caching(self):
        """Test credential caching"""
        mock_provider = Mock()
        mock_provider.get_credential.return_value = 'cached_value'
        
        manager = SecureCredentialManager(providers=[mock_provider])
        
        # Call multiple times
        result1 = manager.get('Service', 'field')
        result2 = manager.get('Service', 'field')
        result3 = manager.get('Service', 'field')
        
        # Should all return same value
        assert result1 == result2 == result3 == 'cached_value'
        
        # Provider should only be called once due to caching
        mock_provider.get_credential.assert_called_once()

class TestModuleFunctions:
    """Test module-level functions"""
    
    def test_get_credential_manager_singleton(self):
        """Test credential manager singleton"""
        manager1 = get_credential_manager()
        manager2 = get_credential_manager()
        
        assert manager1 is manager2
    
    @patch('core.credential_manager.get_credential_manager')
    def test_get_credential_convenience(self, mock_get_manager):
        """Test convenience function"""
        mock_manager = Mock()
        mock_manager.get.return_value = 'test_value'
        mock_get_manager.return_value = mock_manager
        
        result = get_credential('Service', 'field')
        
        assert result == 'test_value'
        mock_manager.get.assert_called_once_with('Service', 'field')
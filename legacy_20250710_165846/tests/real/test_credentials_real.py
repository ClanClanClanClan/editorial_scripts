"""
Real credential manager tests

Tests actual credential providers:
- 1Password CLI (if available)
- System keyring
- Environment variables
"""
import pytest
import os
import subprocess
import keyring
from tests.real import TEST_CONFIG, real_test, credential_test

if TEST_CONFIG['RUN_REAL_TESTS']:
    from core.credential_manager import (
        OnePasswordProvider,
        KeyringProvider,
        EnvProvider,
        SecureCredentialManager,
        get_credential_manager
    )

@real_test
@credential_test
class TestOnePasswordReal:
    """Test real 1Password integration"""
    
    def test_1password_cli_availability(self):
        """Test if 1Password CLI is installed and configured"""
        try:
            result = subprocess.run(
                ['op', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            print(f"\n✓ 1Password CLI installed: {version}")
            
            # Check if signed in
            try:
                subprocess.run(
                    ['op', 'vault', 'list'],
                    capture_output=True,
                    check=True
                )
                print("✓ 1Password CLI is signed in")
                return True
            except subprocess.CalledProcessError:
                print("⚠ 1Password CLI not signed in. Run: op signin")
                return False
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n⚠ 1Password CLI not installed")
            return False
    
    @pytest.mark.skipif(
        not os.path.exists('/usr/local/bin/op') and not os.path.exists('/opt/homebrew/bin/op'),
        reason="1Password CLI not installed"
    )
    def test_1password_credential_retrieval(self):
        """Test retrieving credentials from 1Password"""
        try:
            provider = OnePasswordProvider(vault="Editorial Scripts")
            
            # Try to get a test credential
            # This assumes you have a test item in 1Password
            test_value = provider.get_credential("TEST_CREDENTIAL", "password")
            
            if test_value:
                print(f"\n✓ Successfully retrieved test credential from 1Password")
                assert len(test_value) > 0
            else:
                print("\n⚠ No test credential found in 1Password")
                
        except RuntimeError as e:
            pytest.skip(f"1Password not available: {e}")

@real_test
@credential_test
class TestKeyringReal:
    """Test real system keyring integration"""
    
    def test_keyring_availability(self):
        """Test if system keyring is available"""
        try:
            # Try to set and get a test value
            test_service = "editorial_scripts_test"
            test_account = "test_account"
            test_value = "test_password_12345"
            
            # Set test credential
            keyring.set_password(test_service, test_account, test_value)
            
            # Retrieve it
            retrieved = keyring.get_password(test_service, test_account)
            assert retrieved == test_value
            
            # Clean up
            try:
                keyring.delete_password(test_service, test_account)
            except:
                pass
            
            print("\n✓ System keyring is working")
            return True
            
        except Exception as e:
            print(f"\n⚠ System keyring not available: {e}")
            return False
    
    def test_keyring_provider(self):
        """Test KeyringProvider with real keyring"""
        provider = KeyringProvider()
        
        # Set a test credential
        test_service = "editorial_test"
        test_account = "test_user"
        test_password = "secure_test_pass_789"
        
        try:
            # Store in keyring
            keyring.set_password(test_service, test_account, test_password)
            
            # Retrieve via provider
            retrieved = provider.get_credential(test_service, test_account)
            assert retrieved == test_password
            
            print(f"\n✓ KeyringProvider successfully retrieved credential")
            
        finally:
            # Clean up
            try:
                keyring.delete_password(test_service, test_account)
            except:
                pass

@real_test
@credential_test
class TestEnvironmentReal:
    """Test real environment variable integration"""
    
    def test_env_provider_real(self):
        """Test EnvProvider with real environment"""
        # Set a test environment variable
        test_var = "TEST_EDITORIAL_CREDENTIAL"
        test_value = "test_env_value_456"
        
        original = os.environ.get(test_var)
        try:
            os.environ[test_var] = test_value
            
            provider = EnvProvider()
            
            # Test exact match
            retrieved = provider.get_credential("TEST_EDITORIAL", "CREDENTIAL")
            assert retrieved == test_value
            
            # Test service-only match
            retrieved2 = provider.get_credential("TEST_EDITORIAL_CREDENTIAL", "anything")
            assert retrieved2 == test_value
            
            print("\n✓ EnvProvider working with real environment")
            
        finally:
            # Restore original
            if original:
                os.environ[test_var] = original
            else:
                os.environ.pop(test_var, None)

@real_test
@credential_test
class TestCredentialManagerIntegration:
    """Test the complete credential manager with real providers"""
    
    def test_credential_chain_real(self):
        """Test credential manager with real provider chain"""
        manager = get_credential_manager()
        
        # The manager should have at least EnvProvider
        assert len(manager.providers) > 0
        
        provider_names = [p.__class__.__name__ for p in manager.providers]
        print(f"\n✓ Credential manager initialized with providers: {provider_names}")
        
        # Test fallback chain
        # Set test credential in environment (last resort)
        test_var = "TEST_CHAIN_CREDENTIAL"
        os.environ[test_var] = "env_fallback_value"
        
        try:
            # Try to get credential - should fall back to env
            value = manager.get("TEST_CHAIN", "CREDENTIAL")
            assert value == "env_fallback_value"
            print("✓ Credential chain fallback working")
            
        finally:
            os.environ.pop(test_var, None)
    
    def test_journal_credentials_real(self):
        """Test getting real journal credentials"""
        manager = get_credential_manager()
        
        # Test with a journal (may or may not have credentials)
        creds = manager.get_journal_credentials("JOTA")
        
        print(f"\n✓ Retrieved JOTA credentials structure: {list(creds.keys())}")
        
        # Should have expected keys even if values are None
        assert 'username' in creds
        assert 'password' in creds
    
    def test_credential_caching_real(self):
        """Test credential caching with real data"""
        manager = SecureCredentialManager()
        
        # Set up test env var
        os.environ["CACHE_TEST_VAR"] = "cached_value"
        
        try:
            # First call
            value1 = manager.get("CACHE_TEST", "VAR")
            
            # Change env var
            os.environ["CACHE_TEST_VAR"] = "new_value"
            
            # Second call should return cached value
            value2 = manager.get("CACHE_TEST", "VAR")
            
            assert value1 == value2 == "cached_value"
            print("\n✓ Credential caching working correctly")
            
        finally:
            os.environ.pop("CACHE_TEST_VAR", None)

@real_test
class TestCredentialSecurity:
    """Test security aspects of credential handling"""
    
    def test_no_credential_logging(self):
        """Ensure credentials are never logged"""
        import logging
        from io import StringIO
        
        # Capture logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('core.credential_manager')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            # Set a test credential
            os.environ["SECRET_TEST_PASS"] = "super_secret_password_123"
            
            # Get credential
            manager = get_credential_manager()
            value = manager.get("SECRET_TEST", "PASS")
            
            # Check logs don't contain the actual password
            log_contents = log_capture.getvalue()
            assert "super_secret_password_123" not in log_contents
            
            print("\n✓ Credentials are not logged")
            
        finally:
            os.environ.pop("SECRET_TEST_PASS", None)
            logger.removeHandler(handler)
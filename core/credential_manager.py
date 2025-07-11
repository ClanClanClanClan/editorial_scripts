"""
Secure credential management using 1Password CLI or system keyring as fallback
"""
import subprocess
import json
import os
import logging
from functools import lru_cache
from typing import Dict, Optional
from pathlib import Path
import keyring
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class CredentialProvider:
    """Base class for credential providers"""
    def get_credential(self, service: str, account: str) -> Optional[str]:
        raise NotImplementedError

class OnePasswordProvider(CredentialProvider):
    """1Password CLI integration with proper session management"""
    
    def __init__(self, vault: str = "Private"):
        self.vault = vault
        self.session_token = None
        self._setup_session()
        self._verify_cli()
    
    def _check_session(self) -> bool:
        """Check if current session is valid"""
        try:
            # Check if we have a session token
            if self.session_token:
                os.environ['OP_SESSION_my'] = self.session_token
            
            # Try to execute a simple command
            result = subprocess.run(['op', 'whoami'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def _setup_session(self):
        """Set up automatic session management"""
        session_file = Path.home() / ".config" / "op" / "session"
        
        # Try to load existing session
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    self.session_token = f.read().strip()
                    if self.session_token:
                        os.environ['OP_SESSION_my'] = self.session_token
                        if self._check_session():
                            return  # Session is valid
            except Exception:
                pass
        
        # If no valid session, try to create one using eval op signin
        try:
            # First check if already signed in
            result = subprocess.run(['op', 'whoami'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Already signed in, get session token
                signin_result = subprocess.run(['op', 'signin', '--raw'], 
                                             capture_output=True, text=True, timeout=15)
                if signin_result.returncode == 0:
                    self.session_token = signin_result.stdout.strip()
                    os.environ['OP_SESSION_my'] = self.session_token
                    
                    # Save session for future use
                    session_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(session_file, 'w') as f:
                        f.write(self.session_token)
                    os.chmod(session_file, 0o600)
                    return
        except Exception:
            pass
        
        # If still no session, user needs to sign in manually
        logger.warning("1Password session not established. You may need to run 'op signin' manually.")
    
    def _verify_cli(self):
        """Verify 1Password CLI is installed"""
        try:
            result = subprocess.run(['op', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                logger.info(f"1Password CLI version: {result.stdout.strip()}")
            else:
                raise subprocess.CalledProcessError(result.returncode, 'op --version')
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError(
                "1Password CLI not installed. "
                "Install from: https://1password.com/downloads/command-line/"
            )
    
    @lru_cache(maxsize=128)
    def get_credential(self, service: str, field: str = "password") -> Optional[str]:
        """Fetch credential from 1Password with automatic session management"""
        # Ensure session is active
        if not self._check_session():
            self._setup_session()
            if not self._check_session():
                logger.warning(f"1Password session not available for {service}/{field}")
                return None
        
        try:
            # Try to get the credential
            cmd = ['op', 'item', 'get', service, f'--fields={field}']
            if self.vault:
                cmd.extend(['--vault', self.vault])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                logger.debug(f"Failed to fetch {service}/{field}: {result.stderr}")
                return None
            
            credential = result.stdout.strip()
            if credential:
                return credential
            
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching {service}/{field}: {e}")
            return None

class KeyringProvider(CredentialProvider):
    """System keyring fallback"""
    def get_credential(self, service: str, account: str) -> Optional[str]:
        try:
            return keyring.get_password(service, account)
        except Exception as e:
            logger.error(f"Keyring error for {service}/{account}: {e}")
            return None

class EnvProvider(CredentialProvider):
    """Environment variable fallback (for backwards compatibility)"""
    def __init__(self):
        load_dotenv()
    
    def get_credential(self, service: str, account: str) -> Optional[str]:
        # Try different env var naming conventions
        env_names = [
            f"{service.upper()}_{account.upper()}",
            f"{service.upper()}",
            f"{account.upper()}"
        ]
        
        for env_name in env_names:
            value = os.getenv(env_name)
            if value:
                return value
        
        return None

class SecureCredentialManager:
    """Main credential manager with provider chain"""
    def __init__(self, providers: list = None):
        self.providers = providers or self._detect_providers()
        
    def _detect_providers(self) -> list:
        """Auto-detect available credential providers"""
        providers = []
        
        # Try 1Password first
        try:
            providers.append(OnePasswordProvider())
            logger.info("Using 1Password for credentials")
        except RuntimeError:
            logger.info("1Password not available")
        
        # Add keyring
        providers.append(KeyringProvider())
        
        # Add env fallback
        providers.append(EnvProvider())
        
        return providers
    
    @lru_cache(maxsize=None)
    def get(self, service: str, account: str = "password") -> Optional[str]:
        """Get credential from first available provider"""
        for provider in self.providers:
            try:
                value = provider.get_credential(service, account)
                if value:
                    return value
            except Exception as e:
                logger.debug(f"Provider {provider.__class__.__name__} failed: {e}")
        
        logger.warning(f"No credential found for {service}/{account}")
        return None
    
    def get_journal_credentials(self, journal: str) -> Dict[str, str]:
        """Get all credentials for a specific journal"""
        creds = {}
        
        # Define credential mappings
        mappings = {
            'SICON': {
                'username': ('SICON', 'username'),
                'password': ('SICON', 'password')
            },
            'SIFIN': {
                'username': ('SIFIN', 'username'),
                'password': ('SIFIN', 'password')
            },
            'MOR': {
                'username': ('MOR', 'email'),
                'password': ('MOR', 'password')
            },
            'MF': {
                'username': ('MF', 'email'),
                'password': ('MF', 'password')
            },
            'NACO': {
                'username': ('NACO', 'username'),
                'password': ('NACO', 'password')
            },
            'JOTA': {
                'username': ('JOTA', 'username'),
                'password': ('JOTA', 'password')
            },
            'MAFE': {
                'username': ('MAFE', 'username'),
                'password': ('MAFE', 'password')
            },
            'ORCID': {
                'email': ('ORCID', 'email'),
                'password': ('ORCID', 'password')
            }
        }
        
        if journal in mappings:
            for key, (service, field) in mappings[journal].items():
                creds[key] = self.get(service, field)
        
        return creds
    
    def get_email_credentials(self) -> Dict[str, str]:
        """Get email/Gmail credentials"""
        return {
            'email': self.get('GMAIL', 'username') or self.get('EMAIL', 'user'),
            'password': self.get('GMAIL', 'app_password') or self.get('EMAIL', 'password'),
            'recipient': self.get('RECIPIENT', 'email') or self.get('GMAIL', 'username')
        }

# Singleton instance
_credential_manager = None

def get_credential_manager() -> SecureCredentialManager:
    """Get or create the credential manager singleton"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = SecureCredentialManager()
    return _credential_manager

# Convenience function
def get_credential(service: str, account: str = "password") -> Optional[str]:
    """Quick access to credentials"""
    return get_credential_manager().get(service, account)
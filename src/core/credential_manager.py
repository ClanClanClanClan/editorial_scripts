"""
Credential Manager for Editorial Scripts
Simplified interface for accessing journal credentials from various sources
"""

import os
import logging
import sys
from typing import Dict, Optional, Union
from pathlib import Path
from functools import lru_cache

# Add path for secure credential manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

class CredentialManager:
    """Simple credential manager that works with environment variables and settings"""
    
    def __init__(self):
        """Initialize credential manager"""
        self.settings = None
        self.secure_manager = None
        self._load_settings()
        self._init_secure_manager()
    
    def _load_settings(self):
        """Load settings if available"""
        try:
            from src.infrastructure.config import get_settings
            self.settings = get_settings()
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
            self.settings = None
    
    def _init_secure_manager(self):
        """Initialize secure credential manager"""
        try:
            from secure_credential_manager import SecureCredentialManager
            self.secure_manager = SecureCredentialManager()
            logger.debug("✅ Secure credential manager initialized")
        except Exception as e:
            logger.debug(f"Secure credential manager not available: {e}")
            self.secure_manager = None
    
    @lru_cache(maxsize=128)
    def get_credentials(self, journal: str) -> Optional[Dict[str, str]]:
        """
        Get credentials for a specific journal
        
        Args:
            journal: Journal code (sicon, sifin, mf, mor, etc.)
            
        Returns:
            Dict with username/email and password, or None if not found
        """
        journal_lower = journal.lower()
        
        # Map journal codes to credential sources
        journal_mappings = {
            'sicon': self._get_siam_credentials,
            'sifin': self._get_siam_credentials,
            'mf': self._get_scholarone_credentials,
            'mor': self._get_scholarone_credentials,
            'mafe': self._get_mafe_credentials,
            'naco': self._get_naco_credentials,
            'jota': self._get_jota_credentials,
            'fs': self._get_fs_credentials
        }
        
        if journal_lower in journal_mappings:
            return journal_mappings[journal_lower]()
        
        logger.warning(f"Unknown journal: {journal}")
        return None
    
    # 1Password support removed - using secure credential manager only
    
    def _get_siam_credentials(self) -> Optional[Dict[str, str]]:
        """Get SIAM (ORCID) credentials for SICON/SIFIN"""
        
        # Try environment variables FIRST for full automation
        username = os.getenv('ORCID_EMAIL')
        password = os.getenv('ORCID_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using ORCID credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username  # ORCID uses email as username
            }
        
        # Try settings second
        if self.settings:
            if hasattr(self.settings, 'orcid_email') and hasattr(self.settings, 'orcid_password'):
                if self.settings.orcid_email and self.settings.orcid_password:
                    logger.debug("✅ Using ORCID credentials from settings")
                    return {
                        'username': self.settings.orcid_email,
                        'password': self.settings.orcid_password,
                        'email': self.settings.orcid_email
                    }
        
        # Try secure credential manager LAST (requires master password)
        if self.secure_manager:
            try:
                # Only try if master password is available in environment
                if os.getenv('EDITORIAL_MASTER_PASSWORD'):
                    secure_creds = self.secure_manager.get_credentials('sicon')
                    if secure_creds:
                        logger.debug("✅ Found ORCID credentials in secure storage")
                        return secure_creds
                else:
                    logger.debug("⚠️ Secure storage available but no master password in environment")
            except Exception as e:
                logger.debug(f"Secure manager error: {e}")
        
        logger.warning("❌ No ORCID credentials found. Set ORCID_EMAIL and ORCID_PASSWORD environment variables for full automation.")
        return None
    
    def _get_scholarone_credentials(self) -> Optional[Dict[str, str]]:
        """Get ScholarOne credentials for MF/MOR"""
        
        # Try environment variables FIRST for full automation
        username = os.getenv('SCHOLARONE_EMAIL')
        password = os.getenv('SCHOLARONE_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using ScholarOne credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        # Try settings second
        if self.settings:
            if hasattr(self.settings, 'scholarone_email') and hasattr(self.settings, 'scholarone_password'):
                if self.settings.scholarone_email and self.settings.scholarone_password:
                    logger.debug("✅ Using ScholarOne credentials from settings")
                    return {
                        'username': self.settings.scholarone_email,
                        'password': self.settings.scholarone_password,
                        'email': self.settings.scholarone_email
                    }
        
        logger.warning("❌ No ScholarOne credentials found. Set SCHOLARONE_EMAIL and SCHOLARONE_PASSWORD environment variables for full automation.")
        return None
    
    def _get_mafe_credentials(self) -> Optional[Dict[str, str]]:
        """Get MAFE credentials"""
        username = None
        password = None
        
        # Try settings first
        if self.settings:
            username = getattr(self.settings, 'mafe_username', None)
            password = getattr(self.settings, 'mafe_password', None)
        
        # Try environment variables as fallback
        if not username:
            username = os.getenv('MAFE_USER') or os.getenv('MAFE_USERNAME')
        if not password:
            password = os.getenv('MAFE_PASS') or os.getenv('MAFE_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        
        return None
    
    def _get_naco_credentials(self) -> Optional[Dict[str, str]]:
        """Get NACO credentials"""
        username = None
        password = None
        
        # Try settings first
        if self.settings:
            username = getattr(self.settings, 'naco_username', None)
            password = getattr(self.settings, 'naco_password', None)
        
        # Try environment variables as fallback
        if not username:
            username = os.getenv('NACO_USER') or os.getenv('NACO_USERNAME')
        if not password:
            password = os.getenv('NACO_PASS') or os.getenv('NACO_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        
        return None
    
    def _get_jota_credentials(self) -> Optional[Dict[str, str]]:
        """Get JOTA credentials"""
        username = None
        password = None
        
        # Try environment variables
        username = os.getenv('JOTA_USER') or os.getenv('JOTA_USERNAME')
        password = os.getenv('JOTA_PASS') or os.getenv('JOTA_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        
        return None
    
    def _get_fs_credentials(self) -> Optional[Dict[str, str]]:
        """Get FS credentials"""
        username = None
        password = None
        
        # Try environment variables
        username = os.getenv('FS_USER') or os.getenv('FS_USERNAME')
        password = os.getenv('FS_PASS') or os.getenv('FS_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        
        return None
    
    def get_gmail_credentials(self) -> Optional[Dict[str, str]]:
        """Get Gmail API credentials paths"""
        credentials_path = None
        token_path = None
        
        # Try settings first
        if self.settings:
            credentials_path = self.settings.gmail_credentials_path
            token_path = self.settings.gmail_token_path
        
        # Try environment variables as fallback
        if not credentials_path:
            credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
        if not token_path:
            token_path = os.getenv('GMAIL_TOKEN_PATH', 'token.json')
        
        return {
            'credentials_path': credentials_path,
            'token_path': token_path
        }
    
    def get_openai_credentials(self) -> Optional[Dict[str, str]]:
        """Get OpenAI API credentials"""
        api_key = None
        
        # Try settings first
        if self.settings:
            api_key = self.settings.openai_api_key
        
        # Try environment variables as fallback
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key and api_key != 'test-api-key':
            return {
                'api_key': api_key,
                'model': getattr(self.settings, 'openai_model', 'gpt-4-turbo-preview') if self.settings else 'gpt-4-turbo-preview'
            }
        
        return None
    
    def has_credentials(self, journal: str) -> bool:
        """Check if credentials are available for a journal"""
        creds = self.get_credentials(journal)
        return creds is not None and len(creds) > 0
    
    def list_available_journals(self) -> list:
        """List journals with available credentials"""
        journals = ['sicon', 'sifin', 'mf', 'mor', 'mafe', 'naco', 'jota', 'fs']
        available = []
        
        for journal in journals:
            if self.has_credentials(journal):
                available.append(journal)
        
        return available


# Singleton instance for convenience
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """Get the singleton credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager

# Convenience functions
def get_credentials(journal: str) -> Optional[Dict[str, str]]:
    """Quick access to journal credentials"""
    return get_credential_manager().get_credentials(journal)

def has_credentials(journal: str) -> bool:
    """Quick check if journal credentials are available"""
    return get_credential_manager().has_credentials(journal)
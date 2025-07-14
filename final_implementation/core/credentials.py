"""
Credential Manager for Production Editorial Scripts
Simplified, reliable credential management
"""

import os
import logging
from typing import Dict, Optional, List
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


class CredentialManager:
    """Simple, reliable credential manager"""
    
    def __init__(self):
        """Initialize credential manager"""
        self._load_env_file()
    
    def _load_env_file(self):
        """Load .env file if it exists"""
        env_file = Path('.env')
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                logger.debug("✅ Loaded .env file")
            except Exception as e:
                logger.warning(f"Could not load .env file: {e}")
    
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
        
        # Map journal codes to credential methods
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
    
    def _get_siam_credentials(self) -> Optional[Dict[str, str]]:
        """Get SIAM (ORCID) credentials for SICON/SIFIN"""
        username = os.getenv('ORCID_EMAIL')
        password = os.getenv('ORCID_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using ORCID credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username  # ORCID uses email as username
            }
        
        logger.error("❌ ORCID credentials not found in environment")
        logger.error("Please set ORCID_EMAIL and ORCID_PASSWORD environment variables")
        return None
    
    def _get_scholarone_credentials(self) -> Optional[Dict[str, str]]:
        """Get ScholarOne credentials for MF/MOR"""
        username = os.getenv('SCHOLARONE_EMAIL')
        password = os.getenv('SCHOLARONE_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using ScholarOne credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        logger.error("❌ ScholarOne credentials not found in environment")
        logger.error("Please set SCHOLARONE_EMAIL and SCHOLARONE_PASSWORD environment variables")
        return None
    
    def _get_mafe_credentials(self) -> Optional[Dict[str, str]]:
        """Get MAFE credentials"""
        username = os.getenv('MAFE_EMAIL')
        password = os.getenv('MAFE_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using MAFE credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        logger.error("❌ MAFE credentials not found in environment")
        return None
    
    def _get_naco_credentials(self) -> Optional[Dict[str, str]]:
        """Get NACO credentials"""
        username = os.getenv('NACO_EMAIL')
        password = os.getenv('NACO_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using NACO credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        logger.error("❌ NACO credentials not found in environment")
        return None
    
    def _get_jota_credentials(self) -> Optional[Dict[str, str]]:
        """Get JOTA credentials"""
        username = os.getenv('JOTA_EMAIL')
        password = os.getenv('JOTA_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using JOTA credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        logger.error("❌ JOTA credentials not found in environment")
        return None
    
    def _get_fs_credentials(self) -> Optional[Dict[str, str]]:
        """Get FS credentials"""
        username = os.getenv('FS_EMAIL')
        password = os.getenv('FS_PASSWORD')
        
        if username and password:
            logger.debug("✅ Using FS credentials from environment")
            return {
                'username': username,
                'password': password,
                'email': username
            }
        
        logger.error("❌ FS credentials not found in environment")
        return None
    
    def list_available_journals(self) -> List[str]:
        """List journals for which credentials are available"""
        available = []
        
        # Check SIAM journals
        if os.getenv('ORCID_EMAIL') and os.getenv('ORCID_PASSWORD'):
            available.extend(['sicon', 'sifin'])
        
        # Check ScholarOne journals
        if os.getenv('SCHOLARONE_EMAIL') and os.getenv('SCHOLARONE_PASSWORD'):
            available.extend(['mf', 'mor'])
        
        # Check other journals
        for journal, env_prefix in [
            ('mafe', 'MAFE'),
            ('naco', 'NACO'),
            ('jota', 'JOTA'),
            ('fs', 'FS')
        ]:
            if os.getenv(f'{env_prefix}_EMAIL') and os.getenv(f'{env_prefix}_PASSWORD'):
                available.append(journal)
        
        return available
    
    def validate_credentials(self, journal: str) -> bool:
        """Validate that credentials exist for a journal"""
        return self.get_credentials(journal) is not None
    
    def get_setup_instructions(self, journal: str) -> str:
        """Get setup instructions for a journal"""
        journal_lower = journal.lower()
        
        instructions = {
            'sicon': """
SICON Setup Instructions:
1. Set environment variables:
   export ORCID_EMAIL="your.email@example.com"
   export ORCID_PASSWORD="your_orcid_password"

2. Or add to .env file:
   ORCID_EMAIL=your.email@example.com
   ORCID_PASSWORD=your_orcid_password
""",
            'sifin': """
SIFIN Setup Instructions:
1. Set environment variables:
   export ORCID_EMAIL="your.email@example.com"
   export ORCID_PASSWORD="your_orcid_password"

2. Or add to .env file:
   ORCID_EMAIL=your.email@example.com
   ORCID_PASSWORD=your_orcid_password
""",
            'mf': """
MF Setup Instructions:
1. Set environment variables:
   export SCHOLARONE_EMAIL="your.email@example.com"
   export SCHOLARONE_PASSWORD="your_scholarone_password"

2. Or add to .env file:
   SCHOLARONE_EMAIL=your.email@example.com
   SCHOLARONE_PASSWORD=your_scholarone_password
""",
            'mor': """
MOR Setup Instructions:
1. Set environment variables:
   export SCHOLARONE_EMAIL="your.email@example.com"
   export SCHOLARONE_PASSWORD="your_scholarone_password"

2. Or add to .env file:
   SCHOLARONE_EMAIL=your.email@example.com
   SCHOLARONE_PASSWORD=your_scholarone_password
"""
        }
        
        return instructions.get(journal_lower, f"No setup instructions available for {journal}")
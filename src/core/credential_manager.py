"""Secure credential management for journal access."""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any
import keyring
from dotenv import load_dotenv


class CredentialManager:
    """Manages credentials for journal access."""
    
    SERVICE_NAME = "editorial_scripts"
    
    def __init__(self, env_file: Optional[Path] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load environment variables
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            load_dotenv()
    
    def get_credentials(self, journal_code: str) -> Dict[str, str]:
        """Get credentials for a specific journal."""
        journal_code = journal_code.upper()
        
        # Try environment variables first (most common in production)
        creds = self._get_from_env(journal_code)
        if creds:
            self.logger.info(f"Loaded credentials from environment for {journal_code}")
            return creds
        
        # Try keychain
        creds = self._get_from_keychain(journal_code)
        if creds:
            self.logger.info(f"Loaded credentials from keychain for {journal_code}")
            return creds
        
        # Try config file
        creds = self._get_from_config(journal_code)
        if creds:
            self.logger.info(f"Loaded credentials from config for {journal_code}")
            return creds
        
        raise ValueError(f"No credentials found for {journal_code}")
    
    def _get_from_keychain(self, journal_code: str) -> Optional[Dict[str, str]]:
        """Get credentials from macOS keychain."""
        try:
            # Try different keychain formats
            
            # Format 1: As stored by store_all_credentials_secure.py
            # Service: editorial-scripts, Account: editorial-scripts-{journal}-{field}
            import subprocess
            
            email = None
            password = None
            
            # Get email
            try:
                result = subprocess.run([
                    'security', 'find-generic-password',
                    '-s', 'editorial-scripts',
                    '-a', f'editorial-scripts-{journal_code.lower()}-email',
                    '-w'
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    email = result.stdout.strip()
            except:
                pass
            
            # Get password
            try:
                result = subprocess.run([
                    'security', 'find-generic-password',
                    '-s', 'editorial-scripts',
                    '-a', f'editorial-scripts-{journal_code.lower()}-password',
                    '-w'
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    password = result.stdout.strip()
            except:
                pass
            
            if email and password:
                return {'email': email, 'password': password}
            
            # Format 2: Try the original format
            stored = keyring.get_password(self.SERVICE_NAME, f"{journal_code}_CREDENTIALS")
            if stored:
                return json.loads(stored)
            
            # Format 3: Try platform-based (for shared credentials)
            platform = self._get_journal_platform(journal_code)
            if platform:
                stored = keyring.get_password(self.SERVICE_NAME, f"{platform}_CREDENTIALS")
                if stored:
                    return json.loads(stored)
            
        except Exception as e:
            self.logger.debug(f"Keychain access failed: {e}")
        
        return None
    
    def _get_from_env(self, journal_code: str) -> Optional[Dict[str, str]]:
        """Get credentials from environment variables."""
        # Journal-specific pattern
        email_key = f"{journal_code}_EMAIL"
        password_key = f"{journal_code}_PASSWORD"
        
        email = os.getenv(email_key)
        password = os.getenv(password_key)
        
        if email and password:
            return {'email': email, 'password': password}
        
        # Platform-based pattern
        platform = self._get_journal_platform(journal_code)
        if platform == "scholarone":
            email = os.getenv("SCHOLARONE_EMAIL") or os.getenv("MF_EMAIL")
            password = os.getenv("SCHOLARONE_PASSWORD") or os.getenv("MF_PASSWORD")
        elif platform == "siam":
            email = os.getenv("ORCID_EMAIL")
            password = os.getenv("ORCID_PASSWORD")
        elif platform == "editorial_manager":
            email = os.getenv(f"{journal_code}_EMAIL")
            password = os.getenv(f"{journal_code}_PASSWORD")
        else:
            return None
        
        if email and password:
            return {'email': email, 'password': password}
        
        return None
    
    def _get_from_config(self, journal_code: str) -> Optional[Dict[str, str]]:
        """Get credentials from config file."""
        config_paths = [
            Path("config/credentials.json"),
            Path("config/credentials.yaml"),
            Path.home() / ".editorial_scripts/credentials.json"
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    if config_path.suffix == '.json':
                        with open(config_path) as f:
                            config = json.load(f)
                    else:
                        # Handle YAML if needed
                        continue
                    
                    if journal_code in config:
                        return config[journal_code]
                    
                    # Try platform-based
                    platform = self._get_journal_platform(journal_code)
                    if platform in config:
                        return config[platform]
                        
                except Exception as e:
                    self.logger.debug(f"Config read failed: {e}")
        
        return None
    
    def store_credentials(self, journal_code: str, email: str, password: str) -> bool:
        """Store credentials securely in keychain."""
        try:
            credentials = {'email': email, 'password': password}
            keyring.set_password(
                self.SERVICE_NAME,
                f"{journal_code.upper()}_CREDENTIALS",
                json.dumps(credentials)
            )
            self.logger.info(f"Stored credentials for {journal_code}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store credentials: {e}")
            return False
    
    def _get_journal_platform(self, journal_code: str) -> Optional[str]:
        """Get the platform for a journal."""
        platforms = {
            'MF': 'scholarone',
            'MOR': 'scholarone',
            'SICON': 'siam',
            'SIFIN': 'siam',
            'NACO': 'siam',
            'JOTA': 'editorial_manager',
            'MAFE': 'editorial_manager',
            'FS': 'email_based'
        }
        return platforms.get(journal_code.upper())
    
    def test_credentials(self, journal_code: str) -> bool:
        """Test if credentials exist for a journal."""
        try:
            creds = self.get_credentials(journal_code)
            return bool(creds.get('email') and creds.get('password'))
        except:
            return False
    
    def list_available_credentials(self) -> Dict[str, str]:
        """List all available credentials."""
        journals = ['MF', 'MOR', 'SICON', 'SIFIN', 'NACO', 'JOTA', 'MAFE', 'FS']
        available = {}
        
        for journal in journals:
            if self.test_credentials(journal):
                available[journal] = "✅ Available"
            else:
                available[journal] = "❌ Not configured"
        
        return available
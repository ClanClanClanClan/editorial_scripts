"""
Configuration loader for the Editorial Assistant system.

This module handles loading and validating configuration from YAML files.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

from ..core.data_models import Journal, Platform
from ..core.exceptions import ConfigurationError


class ConfigLoader:
    """Loads and manages system configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir or Path("config")
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration files
        self.journals_config = self._load_yaml("journals.yaml")
        self.settings = self._load_yaml("settings.yaml")
        self.credentials = self._load_credentials()
        
        # Cache for journal objects
        self._journal_cache = {}
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {filename}: {e}")
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from file or environment variables."""
        creds_file = self.config_dir / "credentials.yaml"
        
        if creds_file.exists():
            try:
                with open(creds_file, 'r') as f:
                    return yaml.safe_load(f)
            except:
                pass
        
        # Return empty dict if no credentials file
        return {}
    
    def get_journal(self, journal_code: str) -> Journal:
        """
        Get journal configuration.
        
        Args:
            journal_code: Journal code (e.g., 'MF', 'MOR')
            
        Returns:
            Journal object with configuration
        """
        journal_code = journal_code.upper()
        
        # Check cache
        if journal_code in self._journal_cache:
            return self._journal_cache[journal_code]
        
        # Load journal config
        if journal_code not in self.journals_config['journals']:
            raise ConfigurationError(f"Unknown journal: {journal_code}")
        
        config = self.journals_config['journals'][journal_code]
        
        # Get credentials
        credentials = self._get_journal_credentials(journal_code, config)
        
        # Create Journal object
        journal = Journal(
            code=journal_code,
            name=config['name'],
            platform=Platform(config['platform']),
            url=config['url'],
            categories=config.get('categories', []),
            patterns=config.get('patterns', {}),
            credentials=credentials
        )
        
        # Cache and return
        self._journal_cache[journal_code] = journal
        return journal
    
    def _get_journal_credentials(self, journal_code: str, config: Dict[str, Any]) -> Dict[str, str]:
        """Get credentials for a journal."""
        creds = {}
        
        # First try environment variables specified in config
        cred_config = config.get('credentials', {})
        
        # Username
        username_env = cred_config.get('username_env')
        if username_env:
            username = os.getenv(username_env)
            if not username and cred_config.get('fallback_username_env'):
                username = os.getenv(cred_config['fallback_username_env'])
        else:
            username = None
        
        # Password
        password_env = cred_config.get('password_env')
        if password_env:
            password = os.getenv(password_env)
            if not password and cred_config.get('fallback_password_env'):
                password = os.getenv(cred_config['fallback_password_env'])
        else:
            password = None
        
        # Fall back to credentials file
        if not username or not password:
            file_creds = self.credentials.get('journals', {}).get(journal_code, {})
            username = username or file_creds.get('username')
            password = password or file_creds.get('password')
        
        if username and password:
            creds['username'] = username
            creds['password'] = password
        
        return creds
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific configuration."""
        if platform not in self.journals_config.get('platforms', {}):
            raise ConfigurationError(f"Unknown platform: {platform}")
        
        return self.journals_config['platforms'][platform]
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value by dot-notation path.
        
        Args:
            path: Dot-separated path (e.g., 'browser.default_timeout')
            default: Default value if path not found
            
        Returns:
            Setting value or default
        """
        parts = path.split('.')
        value = self.settings
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def get_all_journal_codes(self) -> list:
        """Get list of all configured journal codes."""
        return list(self.journals_config['journals'].keys())
    
    def validate_configuration(self) -> Dict[str, list]:
        """
        Validate the configuration.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        # Check required files
        required_files = ['journals.yaml', 'settings.yaml']
        for file in required_files:
            if not (self.config_dir / file).exists():
                errors.append(f"Missing required configuration file: {file}")
        
        # Check journal credentials
        for journal_code in self.get_all_journal_codes():
            try:
                journal = self.get_journal(journal_code)
                if not journal.credentials:
                    warnings.append(f"No credentials configured for {journal_code}")
            except Exception as e:
                errors.append(f"Error loading {journal_code}: {str(e)}")
        
        # Check directories
        dirs_to_check = [
            self.get_setting('logging.log_directory', 'logs'),
            self.get_setting('browser.download_directory', 'data/downloads'),
        ]
        
        for dir_path in dirs_to_check:
            path = Path(dir_path)
            if not path.exists():
                warnings.append(f"Directory does not exist: {dir_path}")
        
        return {'errors': errors, 'warnings': warnings}
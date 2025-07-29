# Development Standards

*Coding conventions and best practices for the Editorial Scripts project*

## 📋 Code Style Guidelines

### Python Style (PEP 8 + Extensions)

#### Naming Conventions
```python
# Classes: PascalCase
class ComprehensiveMFExtractor:
    pass

# Functions/Methods: snake_case
def extract_referee_details():
    pass

# Variables: snake_case
manuscript_count = 0
referee_list = []

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Private methods: leading underscore
def _internal_helper_method():
    pass
```

#### File Organization
```python
#!/usr/bin/env python3
"""
Module docstring describing purpose and usage.

Example:
    Basic usage of this module:
    
    >>> from mf_extractor import ComprehensiveMFExtractor
    >>> extractor = ComprehensiveMFExtractor()
    >>> extractor.login()
"""

# Standard library imports
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Third-party imports
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

# Local imports
from ensure_credentials import load_credentials
```

### Documentation Standards

#### Class Documentation
```python
class ComprehensiveMFExtractor:
    """
    Production-ready extractor for Mathematical Finance journal.
    
    This extractor implements a multi-pass strategy for comprehensive
    manuscript data extraction including referees, authors, and documents.
    
    Attributes:
        driver (WebDriver): Selenium WebDriver instance
        config (dict): Configuration settings
        manuscripts (list): Extracted manuscript data
        
    Example:
        >>> extractor = ComprehensiveMFExtractor(debug=True)
        >>> extractor.login()
        >>> extractor.extract_from_category("Awaiting Reviewer Scores")
    """
```

#### Method Documentation
```python
def extract_referees_comprehensive(self, manuscript: dict) -> None:
    """
    Extract comprehensive referee information including emails.
    
    Performs the following steps:
    1. Locate referee table rows using XPath selectors
    2. Filter out editorial staff and manuscript authors
    3. Click referee names to open email composition popups
    4. Extract email addresses from EMAIL_TEMPLATE_TO fields
    5. Parse referee status and affiliation information
    
    Args:
        manuscript (dict): Manuscript data dictionary to update
        
    Raises:
        WebDriverException: If browser automation fails
        TimeoutException: If popups don't load within timeout
        
    Note:
        This method modifies the manuscript dictionary in-place,
        adding referee data to the 'referees' key.
    """
```

## 🏗️ Architecture Patterns

### Error Handling Pattern
```python
def safe_extraction_method(self, element_id: str) -> Optional[str]:
    """Standard error handling pattern for extraction methods."""
    try:
        element = self.driver.find_element(By.ID, element_id)
        return element.text.strip()
    except NoSuchElementException:
        print(f"   ⚠️ Element not found: {element_id}")
        return None
    except TimeoutException:
        print(f"   ⏱️ Timeout waiting for element: {element_id}")
        return None
    except WebDriverException as e:
        print(f"   🌐 WebDriver error for {element_id}: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error for {element_id}: {str(e)[:100]}")
        return None
```

### Retry Decorator Pattern
```python
def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Base delay between attempts (exponentially increased)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"   ❌ {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    else:
                        wait_time = delay * (2 ** attempt)
                        print(f"   ⚠️ {func.__name__} attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
            return None
        return wrapper
    return decorator
```

### Configuration Access Pattern
```python
class ConfigurableExtractor:
    """Base pattern for configuration-driven extractors."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration with fallback hierarchy."""
        default_config = self._get_default_config()
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
            # Merge configurations
            return {**default_config, **user_config}
        
        return default_config
        
    def get_selector(self, selector_name: str) -> str:
        """Get XPath selector with validation."""
        selector = self.config.get('selectors', {}).get(selector_name)
        if not selector:
            raise ValueError(f"Selector '{selector_name}' not found in configuration")
        return selector
```

## 🧪 Testing Standards

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch
from mf_extractor import ComprehensiveMFExtractor

class TestComprehensiveMFExtractor:
    """Test suite for MF extractor functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing."""
        return ComprehensiveMFExtractor(debug=True)
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock WebDriver for testing."""
        return Mock()
    
    def test_login_success(self, extractor, mock_driver):
        """Test successful login process."""
        # Arrange
        extractor.driver = mock_driver
        mock_driver.get.return_value = None
        mock_driver.find_element.return_value.send_keys.return_value = None
        
        # Act
        result = extractor.login()
        
        # Assert
        assert result is True
        mock_driver.get.assert_called_once()
    
    def test_referee_extraction_with_email(self, extractor):
        """Test referee extraction including email retrieval."""
        # Arrange
        manuscript = {"referees": []}
        
        with patch.object(extractor, 'driver') as mock_driver:
            mock_row = Mock()
            mock_row.find_element.return_value.text = "Prof. John Doe"
            mock_row.find_element.return_value.get_attribute.return_value = "javascript:popWindow()"
            mock_driver.find_elements.return_value = [mock_row]
            
            # Act
            extractor.extract_referees_comprehensive(manuscript)
            
            # Assert
            assert len(manuscript["referees"]) > 0
            assert manuscript["referees"][0]["name"] == "Prof. John Doe"
```

### Test Categories and Naming
```python
# Unit Tests (fast, isolated)
def test_parse_manuscript_id():
    """Unit test for ID parsing logic."""
    pass

def test_validate_email_format():
    """Unit test for email validation."""
    pass

# Integration Tests (slower, with dependencies)  
def test_login_with_real_credentials():
    """Integration test with actual authentication."""
    pass

def test_extraction_end_to_end():
    """Full extraction workflow test."""
    pass

# Edge Case Tests
def test_handle_missing_referee_table():
    """Test behavior when referee table is missing."""
    pass

def test_handle_popup_timeout():
    """Test behavior when popup doesn't open."""
    pass
```

## 📁 File Organization Standards

### Directory Structure
```
src/
├── extractors/          # Journal-specific extractors
│   ├── __init__.py
│   ├── base_extractor.py
│   ├── mf_extractor.py
│   ├── sicon_extractor.py
│   └── sifin_extractor.py
├── core/               # Core shared functionality  
│   ├── __init__.py
│   ├── secure_credentials.py
│   ├── browser_manager.py
│   └── config_loader.py
└── utils/              # Utility functions
    ├── __init__.py
    ├── email_validation.py
    ├── data_transformation.py
    └── file_handlers.py
```

### Naming Conventions
- **Extractors**: `{journal}_extractor.py`
- **Tests**: `test_{module_name}.py`
- **Configs**: `{journal}_config.json`
- **Utilities**: `{purpose}_{type}.py`
- **Documentation**: `{TOPIC}_{TYPE}.md`

## 🔧 Development Workflow

### Pre-commit Checklist
1. **Code Quality**
   - [ ] Follows PEP 8 style guidelines
   - [ ] All functions have docstrings
   - [ ] No hardcoded credentials or secrets
   - [ ] Error handling implemented

2. **Testing**
   - [ ] Unit tests pass
   - [ ] Integration tests pass (if applicable)
   - [ ] Test coverage maintained
   - [ ] Edge cases considered

3. **Documentation**
   - [ ] Code changes documented
   - [ ] API documentation updated
   - [ ] User guide updated (if needed)
   - [ ] Configuration changes documented

4. **Configuration**
   - [ ] Configuration files validated
   - [ ] Backwards compatibility maintained
   - [ ] Default values provided

### Code Review Standards

#### Required Reviews
- **Architecture Changes**: Senior developer review
- **Security Changes**: Security-focused review
- **API Changes**: Documentation team review
- **Configuration Changes**: Operations team review

#### Review Criteria
1. **Functionality**: Does it work as intended?
2. **Security**: No credential exposure or security vulnerabilities?
3. **Performance**: Reasonable resource usage?
4. **Maintainability**: Clear, readable, well-documented code?
5. **Testing**: Adequate test coverage?

## 🚀 Deployment Standards

### Environment Configuration
```python
# Environment-specific settings
ENVIRONMENTS = {
    'development': {
        'debug': True,
        'headless': False,
        'timeout': 60,
        'log_level': 'DEBUG'
    },
    'production': {
        'debug': False,
        'headless': True,
        'timeout': 30,
        'log_level': 'INFO'
    }
}
```

### Deployment Checklist
1. **Dependencies**
   - [ ] requirements.txt updated
   - [ ] Version compatibility verified
   - [ ] Browser drivers updated

2. **Configuration**
   - [ ] Production config validated
   - [ ] Credentials properly stored
   - [ ] Permissions configured

3. **Testing**
   - [ ] Full test suite passes
   - [ ] Production environment tested
   - [ ] Rollback plan prepared

## 📊 Monitoring and Logging

### Logging Standards
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage patterns
logger.info("🚀 Starting extraction for MF journal")
logger.warning("⚠️ Retrying failed operation")
logger.error("❌ Critical error in extraction", exc_info=True)
```

### Performance Monitoring
- **Execution Time**: Track extraction duration
- **Success Rate**: Monitor extraction completeness
- **Error Rate**: Track and categorize failures
- **Resource Usage**: Monitor memory and CPU usage

## 🔐 Security Standards

### Credential Handling
```python
# ✅ CORRECT: Use secure credential storage
credentials = SecureCredentialManager()
email, password = credentials.load_credentials()

# ❌ INCORRECT: Never hardcode credentials
email = "user@example.com"  # DON'T DO THIS
password = "secret123"      # DON'T DO THIS
```

### Data Privacy
- **No Sensitive Data in Logs**: Sanitize all log output
- **Secure File Permissions**: Restrict access to data files
- **Temporary File Cleanup**: Remove temporary files after use
- **Audit Trail**: Log access to sensitive operations

---

*Last Updated: January 25, 2025*  
*Standards Version: 3.0*
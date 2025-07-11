"""
Configuration for real integration tests

IMPORTANT: These tests use REAL credentials and services!
- They may send real emails (in dry-run mode)
- They will access real Gmail accounts
- They may create real database entries
- They require working credentials

To run these tests:
1. Ensure you have valid credentials set up
2. Use the --real flag: pytest tests/real --real
3. Monitor the output carefully
"""
import os
import pytest
from pathlib import Path

# Test configuration
TEST_CONFIG = {
    # Set to True to actually run real tests
    'RUN_REAL_TESTS': os.getenv('RUN_REAL_TESTS', 'false').lower() == 'true',
    
    # Gmail settings for tests
    'TEST_GMAIL_LABEL': 'EDITORIAL_TEST',  # Label to use for test emails
    'TEST_EMAIL_RECIPIENT': os.getenv('TEST_EMAIL_RECIPIENT', 'your-test-email@gmail.com'),
    
    # Journal to use for live tests (pick one that's safe to test)
    'TEST_JOURNAL': os.getenv('TEST_JOURNAL', 'JOTA'),  # JOTA is email-only, safest
    
    # Database for real tests
    'TEST_DB_PATH': 'data/test_real_referees.db',
    
    # Chrome profile for tests (separate from production)
    'TEST_CHROME_PROFILE': os.path.expanduser('~/test_chrome_profiles'),
    
    # Timeout settings
    'GMAIL_TIMEOUT': 30,
    'SELENIUM_TIMEOUT': 60,
    
    # Safety settings
    'MAX_EMAILS_TO_FETCH': 10,  # Limit email fetching in tests
    'DRY_RUN_ONLY': True,  # Never send actual emails in tests
}

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "real: mark test as requiring real credentials and services"
    )
    config.addinivalue_line(
        "markers", "gmail: mark test as requiring Gmail API access"
    )
    config.addinivalue_line(
        "markers", "selenium: mark test as requiring Selenium/browser"
    )
    config.addinivalue_line(
        "markers", "credential: mark test as requiring credential manager"
    )

def skip_unless_real():
    """Skip test unless running real tests"""
    return pytest.mark.skipif(
        not TEST_CONFIG['RUN_REAL_TESTS'],
        reason="Real tests not enabled. Set RUN_REAL_TESTS=true"
    )

# Decorators for real tests
real_test = skip_unless_real()
gmail_test = pytest.mark.gmail
selenium_test = pytest.mark.selenium
credential_test = pytest.mark.credential
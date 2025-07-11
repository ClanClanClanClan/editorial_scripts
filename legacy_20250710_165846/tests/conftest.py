"""
Pytest configuration and shared fixtures
"""
import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import json

# Add project root to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def temp_db_path():
    """Create a temporary database path"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_referees.db")
    yield db_path
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_credentials():
    """Mock credential manager"""
    from unittest.mock import Mock
    mock = Mock()
    mock.get.side_effect = lambda service, account: {
        ('SICON', 'username'): 'test_user',
        ('SICON', 'password'): 'test_pass',
        ('GMAIL', 'username'): 'test@gmail.com',
        ('GMAIL', 'app_password'): 'test_app_pass',
        ('ORCID', 'email'): '0000-0000-0000-0000',
        ('ORCID', 'password'): 'orcid_pass',
        ('JOTA', 'username'): 'jota_user',
        ('JOTA', 'password'): 'jota_pass',
    }.get((service, account), 'default_value')
    
    mock.get_journal_credentials.side_effect = lambda journal: {
        'SICON': {'username': 'test_user', 'password': 'test_pass'},
        'JOTA': {'username': 'jota_user', 'password': 'jota_pass'},
        'MOR': {'email': 'mor@test.com', 'password': 'mor_pass'},
    }.get(journal, {})
    
    return mock

@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service"""
    mock_service = MagicMock()
    
    # Mock message list response
    mock_service.users().messages().list.return_value.execute.return_value = {
        'messages': [
            {'id': 'msg1'},
            {'id': 'msg2'},
            {'id': 'msg3'}
        ]
    }
    
    # Mock list_next to return None (no more pages)
    mock_service.users().messages().list_next.return_value = None
    
    return mock_service

@pytest.fixture
def sample_manuscripts():
    """Sample manuscript data for testing"""
    return [
        {
            'Manuscript #': 'TEST-2024-001',
            'Title': 'A Novel Approach to Machine Learning',
            'Contact Author': 'John Doe',
            'Current Stage': 'Under Review',
            'Referees': [
                {
                    'Referee Name': 'Jane Smith',
                    'Status': 'Accepted',
                    'Referee Email': 'jane.smith@university.edu',
                    'Contacted Date': '2024-01-01T10:00:00',
                    'Accepted Date': '2024-01-03T14:00:00',
                    'Due Date': '2024-02-01T00:00:00'
                },
                {
                    'Referee Name': 'Bob Johnson',
                    'Status': 'Contacted',
                    'Referee Email': 'bob.j@college.edu',
                    'Contacted Date': '2024-01-05T09:00:00',
                    'Accepted Date': '',
                    'Due Date': ''
                }
            ]
        },
        {
            'Manuscript #': 'TEST-2024-002',
            'Title': 'Optimization Methods in Finance',
            'Contact Author': 'Alice Brown',
            'Current Stage': 'Pending Referee Assignment',
            'Referees': []
        }
    ]

@pytest.fixture
def sample_emails():
    """Sample email data for testing"""
    return [
        {
            'id': 'email1',
            'subject': 'SICON manuscript #2024-001',
            'from': 'editor@siam.org',
            'to': 'referee@university.edu',
            'date': 'Mon, 1 Jan 2024 10:00:00 -0500',
            'body': 'Dear Dr. Smith, You have been invited to review...'
        },
        {
            'id': 'email2',
            'subject': 'JOTA - Reviewer has agreed to review JOTA-D-24-00123',
            'from': 'em@editorialmanager.com',
            'to': 'editor@university.edu',
            'date': 'Wed, 3 Jan 2024 14:30:00 +0000',
            'body': 'Dear Editor, Jane Smith, Ph.D has agreed to review the manuscript...'
        }
    ]

@pytest.fixture
def mock_selenium_driver():
    """Mock Selenium WebDriver"""
    driver = MagicMock()
    driver.current_url = "https://test.com"
    driver.page_source = "<html><body>Test page</body></html>"
    
    # Mock find_element
    element = MagicMock()
    element.text = "Test element"
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    driver.find_element.return_value = element
    driver.find_elements.return_value = [element]
    
    return driver

@pytest.fixture
def test_env_vars(monkeypatch):
    """Set test environment variables"""
    test_vars = {
        'SICON_USERNAME': 'test_sicon_user',
        'SICON_PASSWORD': 'test_sicon_pass',
        'ORCID_EMAIL': '0000-0000-0000-0000',
        'ORCID_PASSWORD': 'test_orcid_pass',
        'GMAIL_USER': 'test@gmail.com',
        'GMAIL_APP_PASSWORD': 'test_gmail_pass',
        'RECIPIENT_EMAIL': 'recipient@test.com'
    }
    
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    
    return test_vars
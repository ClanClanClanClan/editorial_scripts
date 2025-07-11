# Real Integration Tests

This directory contains **real integration tests** that connect to actual services and systems. These tests are designed to verify that the editorial management system works correctly with real Gmail accounts, databases, and journal websites.

## ⚠️ IMPORTANT WARNINGS

**These tests use REAL credentials and may affect REAL systems:**

- They connect to your actual Gmail account
- They may create real database entries  
- They access real journal websites
- They are designed to run in **DRY RUN MODE** by default to prevent accidents

## 🚦 Safety Features

All real tests include multiple safety mechanisms:

1. **Dry Run Mode**: Tests simulate actions without actually sending emails or modifying production data
2. **Rate Limiting**: Strict limits on API calls and email fetching
3. **Isolated Test Data**: Uses separate test databases and Chrome profiles
4. **Credential Isolation**: Uses test credentials separate from production
5. **Explicit Confirmation**: Requires explicit flags to run live tests

## 📋 Test Categories

### 1. Gmail API Tests (`test_gmail_real.py`)
- Tests Gmail OAuth connection
- Verifies email parsing and filtering
- Tests JOTA email-based scraping
- **Markers**: `@gmail_test`

### 2. Credential Manager Tests (`test_credentials_real.py`)
- Tests 1Password CLI integration
- Verifies system keyring access
- Tests environment variable fallback
- **Markers**: `@credential_test`

### 3. Database Tests (`test_database_real.py`)
- Tests actual SQLite database operations
- Verifies referee tracking and metrics
- Tests performance with realistic data volumes
- **Markers**: `@real_test`

### 4. Journal Scraping Tests (`test_journal_scraping_real.py`)
- Tests Selenium-based journal scraping
- Verifies login procedures (without actual scraping)
- Tests email-based scraping for JOTA/MAFE
- **Markers**: `@selenium_test`

### 5. Email Sending Tests (`test_email_sending_real.py`)
- Tests email template generation
- Verifies recipient validation
- Tests draft email creation
- **Markers**: `@gmail_test`

## 🛠️ Setup Requirements

Before running real tests, ensure you have:

### 1. Gmail API Credentials
```bash
# Download credentials.json from Google Cloud Console
# Place in project root
cp ~/Downloads/credentials.json .

# Run initial OAuth flow
python -c "from core.email_utils import get_gmail_service; get_gmail_service()"
```

### 2. 1Password CLI (Optional)
```bash
# Install 1Password CLI
brew install --cask 1password-cli

# Sign in
op signin

# Create vault for editorial scripts
op vault create "Editorial Scripts"
```

### 3. Test Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Create test directories
mkdir -p data/test
mkdir -p ~/test_chrome_profiles
```

## 🚀 Running Tests

### Using the Test Runner (Recommended)
```bash
# Check environment setup
python run_real_tests.py --setup-check

# Run all tests in dry-run mode
python run_real_tests.py --all

# Run specific test category
python run_real_tests.py --gmail
python run_real_tests.py --credentials
python run_real_tests.py --database

# Run with verbose output
python run_real_tests.py --all --verbose

# Generate test report
python run_real_tests.py --all --report
```

### Using pytest directly
```bash
# Set environment variable
export RUN_REAL_TESTS=true

# Run all real tests
pytest tests/real/

# Run specific test file
pytest tests/real/test_gmail_real.py -v

# Run tests with specific markers
pytest tests/real/ -m "gmail and not selenium"
```

## 📊 Test Configuration

Tests are configured in `test_config.py`:

```python
TEST_CONFIG = {
    'RUN_REAL_TESTS': True,          # Enable real tests
    'DRY_RUN_ONLY': True,            # Prevent actual actions
    'MAX_EMAILS_TO_FETCH': 10,       # Limit API calls
    'TEST_JOURNAL': 'JOTA',          # Safest journal for testing
    'TEST_DB_PATH': 'data/test_real_referees.db'
}
```

## 🔍 Test Markers

Tests use pytest markers for organization:

- `@real_test`: All real integration tests
- `@gmail_test`: Tests requiring Gmail API
- `@selenium_test`: Tests requiring Selenium/Chrome
- `@credential_test`: Tests requiring credential manager

## 🎯 Example Test Runs

### Quick smoke test
```bash
python run_real_tests.py --smoke
```

### Full test suite with report
```bash
python run_real_tests.py --all --verbose --report
```

### Gmail-only tests
```bash
python run_real_tests.py --gmail
```

### Check if credentials work
```bash
python run_real_tests.py --credentials
```

## 🐛 Troubleshooting

### Common Issues

1. **Gmail API not authenticated**
   ```bash
   # Re-run OAuth flow
   rm token.json
   python -c "from core.email_utils import get_gmail_service; get_gmail_service()"
   ```

2. **1Password CLI not signed in**
   ```bash
   op signin
   ```

3. **Chrome driver issues**
   ```bash
   # Update Chrome driver
   pip install --upgrade undetected-chromedriver
   ```

4. **Permission denied on database**
   ```bash
   # Check directory permissions
   chmod 755 data/
   ```

### Debug Mode

Run tests with debug output:
```bash
pytest tests/real/ -v -s --tb=short
```

## 📈 Test Reports

Test reports include:
- Pass/fail status for each test category
- Execution time
- Any warnings or errors
- Credential status
- API rate limit usage

Reports are saved as JSON files with timestamps.

## 🔒 Security Notes

- Tests use separate test databases
- Gmail OAuth tokens are stored securely
- 1Password vault is separate from production
- Chrome profiles are isolated
- No credentials are logged or displayed

## 🚨 Emergency Procedures

If tests behave unexpectedly:

1. **Stop immediately**: `Ctrl+C`
2. **Check dry-run mode**: Verify `DRY_RUN_ONLY=True`
3. **Review logs**: Check test output for actual actions
4. **Verify credentials**: Ensure using test credentials only
5. **Report issues**: Document any unexpected behavior

## 🎉 Success Criteria

Tests are successful when:
- All authentication flows work
- No actual emails are sent (dry-run mode)
- Database operations complete without errors
- Web scraping respects rate limits
- No production data is modified

## 📚 Further Reading

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [1Password CLI Documentation](https://developer.1password.com/docs/cli)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
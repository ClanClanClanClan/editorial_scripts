# Editorial Scripts - Web Scrapers

**Web scrapers for extracting manuscript data from journal systems**

> ⚠️ **Current State**: These are working scrapers that need bug fixes and improvements. No V3 architecture exists yet.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up credentials
python src/core/secure_credentials.py

# Run extraction
python src/extractors/mf_extractor.py
```

## 📋 Overview

These are Selenium-based web scrapers that extract manuscript data from journal management systems.

### Current Extractors
- **Mathematical Finance (MF)** - 🟡 ~70% working (referee extraction broken)
- **SICON** - SIAM Journal on Control and Optimization (basic functionality)
- **SIFIN** - SIAM Journal on Financial Mathematics (basic functionality)

### Known Issues

- ❌ **Referee Email Extraction**: Popup handling broken in MF extractor
- ❌ **Login Reliability**: 2FA and session management issues
- ❌ **Error Recovery**: Missing proper retry logic
- ❌ **Infinite Loops**: Manuscript discovery can hang
- ⚠️ **Code Quality**: Monolithic scripts need refactoring

## 📁 Project Structure

```
production/
├── src/
│   ├── extractors/         # Web scrapers
│   │   ├── mf_extractor.py   # Mathematical Finance scraper
│   │   ├── sicon_extractor.py # SICON scraper
│   │   └── sifin_extractor.py # SIFIN scraper
│   ├── core/              # Utilities
│   │   └── secure_credentials.py # Credential management
│   └── utils/             # Helper functions
├── config/                # Configuration files
│   └── mf_config.json     # MF scraper settings
├── downloads/             # Downloaded PDFs and documents
├── tests/                 # Test scripts
└── docs/                  # Documentation
```

## 🔧 Components

### Core Extractors
- **`src/extractors/mf_extractor.py`** - Mathematical Finance extractor
- **`src/extractors/sicon_extractor.py`** - SICON extractor
- **`src/extractors/sifin_extractor.py`** - SIFIN extractor

### Support Systems
- **`src/core/secure_credentials.py`** - Credential management
- **`src/utils/email_audit_crosscheck.py`** - Email validation
- **`config/mf_config.json`** - Extraction configuration

## 📊 Data Output

Each extraction produces comprehensive manuscript data:

```json
{
  "id": "MAFI-2025-0166",
  "title": "Risk Management in Financial Markets",
  "authors": [
    {
      "name": "Dr. Jane Smith",
      "email": "jane.smith@university.edu",
      "affiliation": "University of Finance",
      "orcid": "0000-0000-0000-0000"
    }
  ],
  "referees": [
    {
      "name": "Prof. John Doe",
      "email": "john.doe@institute.org",
      "status": "Agreed",
      "affiliation": "Research Institute"
    }
  ],
  "submission_date": "2024-12-15",
  "status": "Under Review",
  "documents": {
    "pdf": "/downloads/manuscripts/MAFI-2025-0166.pdf",
    "cover_letter": "/downloads/cover_letters/MAFI-2025-0166.pdf"
  }
}
```

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Chrome browser
- macOS (for secure credential storage)

### Installation
1. **Clone and navigate:**
   ```bash
   cd /path/to/editorial_scripts/production
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials:**
   ```bash
   python src/core/secure_credentials.py store
   ```

4. **Test installation:**
   ```bash
   python tests/unit/test_simple_extraction.py
   ```

## 📖 Documentation

- **[User Guide](docs/user/HOW_TO_RUN_MF_EXTRACTOR.md)** - Complete setup and usage
- **[Architecture Guide](docs/architecture/REFACTORING_PLAN.md)** - System design
- **[API Reference](docs/api/)** - Function and class documentation

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test category
python -m pytest tests/unit/
python -m pytest tests/integration/

# Test specific extractor
python tests/unit/test_mf_extraction_logic.py
```

## 🚀 Usage Examples

### Extract from Mathematical Finance
```bash
python scripts/run_extraction.py --journal mf --category "Awaiting Reviewer Scores"
```

### Extract with custom configuration
```bash
python scripts/run_extraction.py --journal mf --config config/custom_config.json
```

### Debug mode
```bash
python scripts/run_extraction.py --journal mf --debug --headless false
```

## 📈 Production Metrics

- **Success Rate:** 98%+ extraction completeness
- **Processing Time:** ~5-10 minutes per journal
- **Data Accuracy:** Validated against manual review
- **Error Recovery:** Automatic retry mechanisms

## 🔒 Security

- **Credentials:** Stored securely in macOS Keychain
- **2FA Support:** Automatic verification code handling
- **Data Privacy:** No sensitive data logged
- **Access Control:** Role-based journal access

## 🤝 Contributing

1. **Testing:** Run full test suite before changes
2. **Documentation:** Update relevant docs
3. **Standards:** Follow existing code patterns
4. **Validation:** Ensure extraction accuracy

## 📝 License

Proprietary - Internal use only

## 🆘 Support

- **Issues:** Check existing test files for debugging patterns
- **Configuration:** Review `config/mf_config.json` for settings
- **Troubleshooting:** See [User Guide](docs/user/HOW_TO_RUN_MF_EXTRACTOR.md)

---

*Last Updated: January 25, 2025*
*Version: 3.0 (Post-Refactoring)*

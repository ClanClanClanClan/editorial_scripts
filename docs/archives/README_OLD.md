# Editorial Scripts - Complete Journal Extraction System

A comprehensive, organized system for extracting manuscript and referee data from academic journal management systems.

## 🚀 Quick Start

1. **Setup environment**:
   ```bash
   python3 -m venv venv_fresh
   source venv_fresh/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure credentials**:
   ```bash
   export EDITORIAL_MASTER_PASSWORD='your_password'
   python3 secure_credential_manager.py setup
   ```

3. **Run extractions**:
   ```bash
   # Any supported journal
   python3 run_all_journals.py --journal SICON
   python3 run_all_journals.py --journal MF
   python3 run_all_journals.py --journal JOTA
   ```

## 📂 Organized Project Structure

```
src/
├── infrastructure/
│   ├── scrapers/
│   │   ├── siam/                    # SIAM journals
│   │   │   ├── sicon_scraper.py     # SICON (working)
│   │   │   └── sifin_scraper.py     # SIFIN (needs fixes)
│   │   ├── scholarone/              # ScholarOne platform
│   │   │   ├── mf_scraper.py        # Mathematical Finance
│   │   │   └── mor_scraper.py       # Math Operations Research
│   │   ├── email_based/             # Email-based journals
│   │   │   ├── fs_scraper.py        # Finance & Stochastics
│   │   │   └── jota_scraper.py      # JOTA
│   │   ├── other/                   # Other journals
│   │   │   ├── mafe_scraper.py      # MAFE
│   │   │   └── naco_scraper.py      # NACO
│   │   ├── base_scraper.py          # Base scraper class
│   │   ├── enhanced_referee_extractor.py
│   │   ├── siam_orchestrator.py     # SIAM coordination
│   │   └── stealth_manager.py       # Anti-detection
│   ├── database/                    # Database models
│   ├── repositories/                # Data access layer
│   └── services/                    # External services
├── api/                            # FastAPI web interface
├── core/                           # Domain logic
└── ai/                             # AI analysis
```

## 🎯 Supported Journals

| Journal | Status | Platform | Notes |
|---------|--------|----------|-------|
| **SICON** | ✅ Working | SIAM | Advanced features, caching, email crosscheck |
| **SIFIN** | ⚠️ Needs fixes | SIAM | Basic extraction working |
| **MF** | 🔧 Ready to test | ScholarOne | Mathematical Finance |
| **MOR** | 🔧 Ready to test | ScholarOne | Math Operations Research |
| **FS** | 🔧 Ready to test | Email-based | Finance & Stochastics |
| **JOTA** | 🔧 Ready to test | Email-based | Journal of Theoretical Probability |

## 🔧 System Features

### Core Capabilities
- **Multi-platform support**: SIAM, ScholarOne, Email-based systems
- **Comprehensive data extraction**: Manuscripts, referees, PDFs, timelines
- **Smart caching**: Content-based change detection
- **Email integration**: Gmail API for communication timeline analysis
- **AI analysis**: Manuscript and referee insights
- **Secure credential management**: Encrypted storage with master password

### Advanced Features
- **Anti-detection**: Stealth browsing with randomized patterns
- **Parallel processing**: Concurrent manuscript processing
- **Document management**: PDF download, text extraction, metadata
- **Analytics**: Referee performance, timeline analysis, behavioral patterns
- **API interface**: REST API for programmatic access

## 🧹 Recent Cleanup (2025-07-14)

### What Was Cleaned Up
- **Consolidated 3 competing systems** into single organized structure
- **Removed duplicate implementations** (50+ redundant files)
- **Organized scrapers** by platform (SIAM, ScholarOne, Email-based)
- **Archived legacy code** while preserving working implementations
- **Created unified runner** supporting all journals

### What Was Archived
- `archive/legacy_implementations_20250714/` - Old competing systems
- `archive/legacy_journals/` - Legacy standalone implementations  
- `archive/old_test_files/` - Debug and test files
- `archive/screenshots/` - Debug screenshots

## 📊 Data Quality Standards

Each journal extractor provides:
- **Complete referee information**: Names, emails, institutions, statuses
- **Timeline data**: Invitation dates, response times, report submissions
- **Communication metrics**: Email counts, reminder frequencies, response quality
- **Document collection**: Manuscripts, reports, cover letters, supplements
- **Smart deduplication**: Unique referees per manuscript

## 🔍 Testing & Verification

```bash
# Test specific journal
python3 run_all_journals.py --journal SICON --verbose

# Check extraction results
ls -la output/sicon/

# Run integration tests
python3 -m pytest tests/integration/
```

## 🛠️ Development

### Adding New Journals
1. Create scraper in appropriate subfolder (`src/infrastructure/scrapers/`)
2. Inherit from `BaseScraper`
3. Implement required methods
4. Add to `run_all_journals.py`
5. Add tests

### Architecture Principles
- **Single responsibility**: One scraper per journal
- **Consistent interfaces**: All scrapers use same API
- **Proper error handling**: Graceful failures with detailed logging
- **Async throughout**: Non-blocking operations
- **Secure by default**: No credentials in code, encrypted storage

## 📞 Support

- **Issues**: Report at project repository
- **Documentation**: See `docs/` folder for detailed guides
- **Configuration**: Check `config/` for settings and examples

*Last updated: 2025-07-14 - Major cleanup and reorganization complete*
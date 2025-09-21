# Editorial Scripts

A comprehensive system for extracting manuscript and referee data from 8 academic journal editorial platforms.

## ⚠️ IMPORTANT: Credentials Already Stored!
**All journal credentials are permanently stored in macOS Keychain. Never ask for them again.**

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry 1.7+
- Chrome/Chromium browser
- macOS (for keychain storage)

### Installation
```bash
# Clone and setup
git clone <repository>
cd editorial_scripts

# Install dependencies with Poetry
poetry install

# Activate the venv for local runs
poetry shell
```

### Running ECC
```bash
# API (FastAPI)
uvicorn src.ecc.main:app --host 0.0.0.0 --port 8000 --reload

# CLI
ecc --help
```

Note: Legacy extractors under `production/` and `editorial_assistant/` are preserved for reference only. They are not security‑hardened and should not be used for new runs.

### Verify Credentials
```bash
# Check all credentials are properly stored
python3 verify_all_credentials.py

# Load credentials manually if needed
source ~/.editorial_scripts/load_all_credentials.sh
```

## 📁 Project Structure

```
editorial_scripts/
├── production/                   # WORKING extractors (messy but functional)
│   └── src/
│       └── extractors/
│           └── mf_extractor.py  # 3,698 lines, DO NOT BREAK
│
├── src/                         # NEW clean architecture (IN PROGRESS)
│   ├── core/                    # Base components
│   │   ├── base_extractor.py    # Abstract base
│   │   ├── browser_manager.py   # Selenium management
│   │   ├── credential_manager.py # Credential handling
│   │   ├── data_models.py       # Type-safe models
│   │   └── gmail_manager.py     # 2FA support
│   ├── platforms/               # Platform base classes
│   │   └── scholarone.py        # Base for MF, MOR
│   └── extractors/              # Journal implementations
│       └── mf.py                # Clean MF (418 lines!)
│
├── editorial_assistant/         # Legacy implementations
├── config/                      # Configuration files
├── scripts/                     # Utility scripts
├── tests/                       # Test suite
└── docs/                        # Documentation
```

## 🔑 Supported Journals

| Journal | Platform | Authentication | Status |
|---------|----------|----------------|--------|
| MF | ScholarOne | Email + 2FA | ✅ Production + New |
| MOR | ScholarOne | Email + 2FA | ✅ Production |
| SICON | SIAM | ORCID OAuth | ✅ Legacy |
| SIFIN | SIAM | ORCID OAuth | ✅ Legacy |
| NACO | SIAM | ORCID OAuth | ⚠️ Partial |
| JOTA | Editorial Manager | Username/Pass | ✅ Legacy |
| MAFE | Editorial Manager | Username/Pass | ✅ Legacy |
| FS | Email-based | Gmail API | ⚠️ Manual |

## 🏗️ Architecture

### Current State (Jan 2025)
- **Production**: Working but monolithic (3,698 lines per extractor)
- **New Architecture**: Clean, modular, 53% less code
- **Migration**: MF complete, others in progress

### Design Principles
```
BaseExtractor (abstract)
├── Platform Base (shared logic)
│   └── Journal Extractor (specific logic)
│
├── BrowserManager (Selenium handling)
├── CredentialManager (auth management)
└── GmailManager (2FA codes)
```

## 📊 Key Features

- **3-Pass Extraction**: Forward → Backward → Forward navigation
- **Popup Email Extraction**: Referee emails from popup windows
- **2FA Support**: Automatic Gmail verification codes
- **Document Downloads**: PDFs, cover letters, reports
- **Audit Trail**: Complete timeline extraction
- **Type Safety**: Dataclasses with enums
- **Error Recovery**: Automatic retry mechanisms

## 🛡️ Security

- ✅ Credentials stored in macOS Keychain (encrypted)
- ✅ No plaintext passwords in code or files
- ✅ Automatic loading from secure storage
- ✅ Git-ignored sensitive directories
- ✅ Masked password output in logs

See SECURITY.md for vulnerability reporting and deployment hardening guidance.

## 📖 Documentation

- `CLAUDE.md` - AI assistant guide
- `CREDENTIALS_STORED.md` - Credential documentation
- `.credentials_permanent_storage_record.md` - Storage record
- `docs/` - Technical specifications

## 🧪 Testing

```bash
# Verify setup
python3 verify_all_credentials.py

# Compare implementations
python3 compare_implementations.py

# Test specific journal
python3 production/src/extractors/mf_extractor.py
```

## 🤝 Contributing

1. **Never break production/** - It works, keep it working
2. **Test thoroughly** - Real journal access required
3. **Follow patterns** - Use platform inheritance
4. **Document changes** - Update CLAUDE.md

## ⚡ Troubleshooting

| Issue | Solution |
|-------|----------|
| "No credentials found" | Run `source ~/.editorial_scripts/load_all_credentials.sh` |
| 2FA timeout | Check Gmail API setup |
| Login fails | Verify credentials with `verify_all_credentials.py` |
| Popup blocked | Browser manager should handle automatically |

## 📝 License

Private repository - All rights reserved

---

**Remember**: Credentials are permanently stored. Never ask for them again!

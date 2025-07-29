# 🤖 CLAUDE.md - Editorial Scripts Project Guide

## 🚨 CRITICAL: CREDENTIALS ARE ALREADY STORED!
**DO NOT ASK FOR CREDENTIALS - They are permanently stored in macOS Keychain**

### ✅ Credential Status (as of 2025-01-26)
- **ALL 8 journal credentials stored in macOS Keychain**
- **Automatic loading via ~/.zshrc**
- **User NEVER needs to enter credentials again**
- **Test with:** `python3 verify_all_credentials.py`

---

## 📋 Project Overview

This is Dylan Possamaï's editorial manuscript extraction system for academic journals. The project extracts referee reports, manuscripts, and metadata from 8 different journal platforms.

### 🎯 Core Purpose
- Extract referee information, reports, and manuscript data
- Support 8 journals across 4 different platforms
- Automate editorial workflows
- Provide clean, structured data output

### 📁 Project Structure
```
editorial_scripts/
├── production/               # CANONICAL WORKING EXTRACTORS
│   └── src/
│       └── extractors/
│           └── mf_extractor.py  # 3,939 lines, SINGLE SOURCE OF TRUTH
├── dev/                     # 🚨 DEVELOPMENT ISOLATION - USE THIS!
│   ├── mf/                 # MF development environment
│   │   ├── run_mf_dev.py   # Development runner (NO POLLUTION)
│   │   ├── tests/          # All test files go here
│   │   ├── outputs/        # All results contained here
│   │   ├── logs/           # All debug logs here
│   │   └── debug/          # All debug files here
│   └── README.md           # Development guidelines
├── docs/                    # Essential documentation only
│   ├── workflows/          # How-to guides
│   └── specifications/     # System specs
├── config/                  # Configuration files
├── src/                     # NEW CLEAN ARCHITECTURE (IN PROGRESS)
│   ├── core/               # Base components
│   ├── platforms/          # Platform-specific base classes
│   └── extractors/         # Journal-specific implementations (FUTURE)
└── archive/                 # Historical backups (reference only)
```

---

## 🔑 Credentials & Authentication

### ⚠️ NEVER ASK FOR CREDENTIALS - They're Already Stored!

**Storage Locations:**
1. **macOS Keychain** (primary, encrypted)
   - Service names: `editorial-scripts-{journal}`
   - Persistent forever
   - Survives reboots

2. **Shell Environment** 
   - Auto-loads via: `~/.zshrc`
   - Script: `~/.editorial_scripts/load_all_credentials.sh`

**Verification Commands:**
```bash
# Check all credentials
python3 verify_all_credentials.py

# Test keychain storage
python3 production/src/core/secure_credentials.py load

# Load manually if needed
source ~/.editorial_scripts/load_all_credentials.sh
```

---

## 📚 Supported Journals & Platforms

### Platform Architecture
```
ScholarOne (Manuscript Central)
├── MF (Mathematical Finance)
└── MOR (Mathematics of Operations Research)

SIAM (ORCID Authentication)
├── SICON (Control and Optimization)
├── SIFIN (Financial Mathematics)
└── NACO (Numerical Algebra)

Editorial Manager
├── JOTA (Journal of Optimization Theory)
└── MAFE (Mathematical Finance - different from MF!)

Email-based
└── FS (Finance and Stochastics)
```

### Authentication Methods
- **ScholarOne**: Email/Password + 2FA via Gmail
- **SIAM**: ORCID OAuth (uses ORCID credentials)
- **Editorial Manager**: Username/Password
- **Email**: Gmail API

---

## 🏗️ Architecture Evolution

### Current State (2025-01-26)
1. **Production** (`production/src/extractors/`)
   - Working but messy (3,698 lines for MF)
   - Contains all functionality
   - 3-pass extraction system
   - Handle with care - IT WORKS!

2. **New Architecture** (`src/`)
   - Clean, modular design
   - 53% less code
   - Platform inheritance
   - Type-safe with dataclasses
   - IN PROGRESS - MF done, others TODO

### Key Design Patterns
```python
# Inheritance hierarchy
BaseExtractor (abstract)
└── ScholarOneExtractor (platform base)
    ├── MFExtractor (journal specific)
    └── MORExtractor (journal specific)

# Composition
- BrowserManager (Selenium handling)
- CredentialManager (auth management)  
- GmailManager (2FA codes)
```

---

## 🚀 Common Tasks

### 🚨 CRITICAL: Development vs Production

**⚠️ ALWAYS USE DEVELOPMENT ENVIRONMENT FOR TESTING:**

**🧪 Development (Isolated - NO POLLUTION):**
```bash
cd dev/mf
python3 run_mf_dev.py  # ALL outputs contained in dev/mf/
```
- All test files → `dev/mf/tests/`
- All results → `dev/mf/outputs/`  
- All logs → `dev/mf/logs/`
- All debug files → `dev/mf/debug/`
- **ZERO pollution of main codebase**

**🚀 Production (Live Use ONLY):**
```bash
cd production/src/extractors  
python3 mf_extractor.py  # When code is ready and tested
```

**❌ NEVER CREATE:**
- Test files in project root
- Result files in project root
- Debug files outside dev/
- Temporary scripts outside dev/

### Testing New Implementation
```bash
# ALL TESTING IN DEVELOPMENT ENVIRONMENT
cd dev/mf/tests
python3 test_whatever.py  # Outputs contained

# Credential verification (allowed in root)
python3 verify_all_credentials.py
```

### Adding New Journal
1. Identify platform (ScholarOne, SIAM, etc.)
2. Create platform base if needed
3. Inherit from platform base
4. Override journal-specific methods
5. Test with real credentials (already stored!)

---

## ⚡ Quick Reference

### Critical Files
- `production/src/extractors/mf_extractor.py` - **CANONICAL MF EXTRACTOR** (3,939 lines)
- `src/platforms/scholarone.py` - ScholarOne base class (for future clean architecture)
- `verify_all_credentials.py` - Credential verification
- `docs/workflows/MF_WORKFLOW.md` - How to run MF extractor
- `docs/specifications/PROJECT_SPECIFICATIONS.md` - Complete system specs

### Key Features
- **3-Pass Extraction System** (Forward → Backward → Forward)
- **Popup Email Extraction** (referee emails in popups)
- **2FA via Gmail** (automatic code retrieval)
- **Cover Letter Downloads** (PDF/DOCX)
- **Audit Trail Extraction** (timeline data)

### Common Issues & Solutions
1. **"No credentials found"** → Run `source ~/.editorial_scripts/load_all_credentials.sh`
2. **2FA timeout** → Gmail API needs setup, check `core/gmail_verification.py`
3. **Popup blocked** → Browser manager handles most cases
4. **Cookie banner** → Auto-dismissed in login flow

---

## 🧪 Testing Checklist

Before making changes:
- [ ] Run `python3 verify_all_credentials.py`
- [ ] Test production extractor still works
- [ ] Check Git status for uncommitted changes
- [ ] Backup before major refactoring

---

## 💡 Pro Tips for Claude

1. **🚨 DEVELOPMENT ISOLATION (CRITICAL)**
   - **ALWAYS use `dev/mf/` for testing/development**
   - **NEVER create files in project root during development**
   - Use `cd dev/mf && python3 run_mf_dev.py` for testing
   - All outputs must go to `dev/mf/outputs/`
   - This prevents codebase pollution!

2. **User Preferences**
   - Likes action over analysis
   - Wants clean, working code
   - Frustrated by over-explanation
   - Values bulletproof solutions

3. **Code Style**
   - NO comments unless requested
   - Concise responses
   - Show, don't tell
   - Test before claiming success

4. **Project Context**
   - Academic editorial system
   - Real journal platforms
   - Sensitive data (be careful!)
   - Production use (reliability matters)

---

## 🎯 Current Priorities

1. **MF Extractor Status**
   - ✅ **COMPLETE AND WORKING** - All fixes implemented
   - ✅ Single canonical version: `production/src/extractors/mf_extractor.py`
   - ✅ Author extraction fixed, email extraction fixed, title/status extraction added
   - ✅ Cleanup completed - duplicates removed

2. **Future Architecture**
   - ⬜ MOR extractor (use ScholarOne base)
   - ⬜ SIAM base class for SICON, SIFIN
   - ⬜ Editorial Manager base for JOTA, MAFE, NACO
   - ⬜ Migrate MF to clean architecture when ready

3. **Maintenance**
   - Keep `production/src/extractors/mf_extractor.py` working
   - Don't break existing functionality
   - Test thoroughly before changes

---

## 🔒 Security Notes

- **Credentials in Keychain** - Never in code
- **No Git commits of secrets** - Check before committing
- **Masked output** - Hide passwords in logs
- **Secure browser sessions** - Close properly
- **Download paths** - Use designated directories

---

## 📝 Session Handoff

For future Claude sessions:
1. **Read this file first**
2. **Check credential status**: `python3 verify_all_credentials.py`
3. **Review recent changes**: `git status` and `git log --oneline -10`
4. **Test production**: `python3 production/src/extractors/mf_extractor.py`
5. **Continue where left off** - Check TODOs above

---

**Last Updated**: 2025-07-28
**Session Context**: ULTRA-CLEANED project (615 → 53 files) + DEVELOPMENT ISOLATION setup to prevent pollution
**Next Steps**: Use `dev/mf/` for all MF testing, implement remaining extractors using new architecture
**CRITICAL**: Always use development environment - NEVER pollute main codebase!
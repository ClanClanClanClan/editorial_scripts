# CLAUDE.md - Editorial Scripts AI Assistant Guide

## CRITICAL: CREDENTIALS ARE ALREADY STORED
**DO NOT ASK FOR CREDENTIALS - They are permanently stored in macOS Keychain**
- **Test with:** `python3 verify_all_credentials.py`
- **Auto-loaded via:** `~/.zshrc` -> `~/.editorial_scripts/load_all_credentials.sh`

---

## Project Overview

Dylan Possamai's manuscript extraction system for 8 academic journals.
- **Purpose**: Extract referee reports, manuscripts, and metadata
- **Architecture**: Selenium WebDriver + Gmail API
- **Status**: 3 extractors working (MF, MOR, FS), 5 are skeletons in archive

### Project Structure
```
editorial_scripts/
├── production/src/extractors/     # ALL WORKING CODE HERE
│   ├── mf_extractor.py           # MF - ScholarOne (ComprehensiveMFExtractor)
│   ├── mor_extractor.py          # MOR - ScholarOne (MORExtractor)
│   ├── fs_extractor.py           # FS - Gmail API (ComprehensiveFSExtractor)
│   ├── generate_fs_timeline_report.py  # FS utility
│   ├── downloads/                # Downloaded documents
│   └── results/                  # Extraction outputs
├── production/src/core/           # Shared utilities
│   ├── cache_manager.py          # SQLite persistent cache
│   ├── cache_integration.py      # CachedExtractorMixin
│   ├── gmail_search.py           # Gmail timeline integration
│   └── gmail_verification.py     # 2FA code fetching
├── production/outputs/            # Extraction JSON results
├── production/cache/              # SQLite cache databases
├── config/                        # Gmail OAuth tokens, journal configs
├── archive/                       # Legacy code + skeleton extractors
├── dev/                           # Development/testing sandbox
├── src/ecc/                       # Abandoned new architecture (5% complete)
└── run_extractors.py              # Orchestrator for all extractors
```

---

## Credentials & Authentication

### NEVER ASK FOR CREDENTIALS - They're Already Stored!

**Storage Locations:**
1. **macOS Keychain** (primary, encrypted)
   - Service names: `editorial-scripts-{journal}`
   - Persistent forever, survives reboots

2. **Shell Environment**
   - Auto-loads via: `~/.zshrc` -> `~/.editorial_scripts/load_all_credentials.sh`

**Verification:**
```bash
python3 verify_all_credentials.py
source ~/.editorial_scripts/load_all_credentials.sh
```

---

## Supported Journals

| Journal | Code | Platform | Extractor Class | Status |
|---------|------|----------|-----------------|--------|
| **Mathematical Finance** | MF | ScholarOne | `ComprehensiveMFExtractor` | WORKING |
| **Mathematics of Operations Research** | MOR | ScholarOne | `MORExtractor` | WORKING |
| **Finance and Stochastics** | FS | Gmail API | `ComprehensiveFSExtractor` | WORKING |
| JOTA | JOTA | Editorial Manager | - | SKELETON (in archive) |
| MAFE | MAFE | Editorial Manager | - | SKELETON (in archive) |
| SICON | SICON | SIAM | - | SKELETON (in archive) |
| SIFIN | SIFIN | SIAM | - | SKELETON (in archive) |
| NACO | NACO | AIMS Sciences | - | SKELETON (in archive) |

---

## Quick Commands

```bash
# Verify credentials
python3 verify_all_credentials.py

# Run production extractors
cd production/src/extractors
python3 mf_extractor.py   # MF extraction
python3 mor_extractor.py  # MOR extraction
python3 fs_extractor.py   # FS extraction

# Orchestrator
python3 run_extractors.py --status      # Show all extractor status
python3 run_extractors.py --journal mf  # Run specific extractor
python3 run_extractors.py --all         # Run all working extractors

# Development testing (isolated)
cd dev/mf
python3 run_mf_dev.py  # All outputs in dev/mf/
```

---

## Development Rules

### ALWAYS USE dev/ FOR TESTING
```bash
cd dev/mf
python3 run_mf_dev.py  # All outputs contained in dev/mf/
```

**NEVER CREATE:**
- Test files in project root
- Debug files outside dev/
- Temporary scripts outside dev/

---

## Key Features

- **3-Pass Extraction** (MF): Forward -> Backward -> Forward
- **6-Pass Extraction** (MOR): Referees, authors, metadata, docs, history, audit
- **Gmail Integration**: 2FA codes + FS email extraction
- **SQLite Caching**: Persistent referee/manuscript cache across runs
- **Auto ChromeDriver**: webdriver-manager handles version matching

---

## Known Blockers

1. **Gmail OAuth token expired** - needs re-authentication via `python3 scripts/setup_gmail_oauth.py`
2. **MF extractor** blocked until Gmail OAuth is refreshed (needed for 2FA)
3. **MOR extractor** works but falls back to manual 2FA without Gmail OAuth

---

## AI Assistant Notes

- **User prefers**: Action over analysis, concise responses
- **Code style**: No comments unless requested
- **Testing**: Always use `dev/` directory
- **Production**: Handle with care - it works!

---

**Last Updated**: 2026-02-08

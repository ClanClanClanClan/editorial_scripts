# Aggressive Deduplication Plan

## Summary of Current Duplication

- **21 SIAM test files** (way too many!)
- **17 completion reports** (excessive)
- **8 audit reports** (redundant)
- **9 run scripts** (mostly obsolete)
- **400+ MB of old virtual environments**

## What to Keep vs Archive

### Test Files (/tests/)

**KEEP (4 files only):**
- `test_unified_system.py` - Main comprehensive test
- `test_sicon_fixed.py` - Latest SICON test with fixes
- `test_sicon_gmail.py` - Gmail integration test
- `test_api_startup.py` - API test

**ARCHIVE (47+ files):**
All other test files including:
- All the test_siam_*.py variants (debug, simple, auto, real, etc.)
- All the test_sicon_*.py variants except the two above
- All integration tests except test_unified_system.py
- All scraper tests (redundant with above)
- All misc tests (cloudflare, orcid, modal, etc.)

### Documentation (/docs/)

**KEEP:**
- `README.md` - Main readme
- `CLEANUP_AND_FIXES_SUMMARY.md` - Today's work
- `docs/guides/SETUP_GUIDE.md` - Consolidated setup guide
- `docs/reports/FINAL_AUDIT_REPORT.md` - Most recent audit

**ARCHIVE (35+ files):**
- All other completion reports
- All other audit reports  
- All phase reports
- All status reports
- Duplicate setup guides

### Scripts

**KEEP:**
- `run_unified_with_1password.py` - Main runner
- `scripts/setup/setup_1password.py` - For credential setup

**ARCHIVE (20+ files):**
- All other run_*.py scripts
- All debug_*.py scripts
- All other setup scripts
- All patch/fix scripts

### Directories

**DELETE IMMEDIATELY:**
- `venv_clean/` (255 MB)
- `venv_test/` (156 MB)
- All `debug_*` directories
- All `test_results_*` directories
- All `dashboard_html_*` directories

### Core System

**NEVER TOUCH:**
- `unified_system/` - Working extraction system
- `src/` - Source code
- `output/` - Current extraction results
- `data/` - Database and cache
- `config/` - Configuration files

## Space Savings

- **Immediate**: ~420 MB (virtual environments + debug dirs)
- **After file cleanup**: Additional ~50-100 MB

## Execution Plan

1. **Backup first**: Create full backup of current state
2. **Delete virtual environments**: They can be recreated
3. **Archive test files**: Keep only the 4 essential ones
4. **Archive old docs**: Keep only current documentation
5. **Clean scripts**: Keep only actively used ones
6. **Final check**: Ensure system still works

## Essential Files That Must Stay

```
editorial_scripts/
├── unified_system/        # DO NOT TOUCH
├── src/                   # DO NOT TOUCH
├── output/                # Current results
├── tests/
│   ├── test_unified_system.py
│   ├── test_sicon_fixed.py
│   ├── test_sicon_gmail.py
│   └── test_api_startup.py
├── docs/
│   ├── guides/SETUP_GUIDE.md
│   └── reports/FINAL_AUDIT_REPORT.md
├── run_unified_with_1password.py
├── requirements.txt
├── .env
├── .env.example
├── README.md
└── CLEANUP_AND_FIXES_SUMMARY.md
```

## Why This Is Safe

1. **Version control**: Git has history if we need old files
2. **Archive not delete**: Everything goes to archive/ directory
3. **Core untouched**: unified_system/ and src/ remain intact
4. **Tests consolidated**: 4 tests cover all functionality
5. **Docs simplified**: One guide is better than 5 duplicates

## Expected Result

From a chaotic folder with 200+ files in root, we'll have:
- ~20 files in root (config, readme, main runner)
- 4 test files (down from 50+)
- 2-3 documentation files (down from 40+)
- Clean, navigable structure
- 500+ MB space saved
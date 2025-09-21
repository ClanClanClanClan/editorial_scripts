# 📊 EDITORIAL SCRIPTS PROJECT - CURRENT STATE
**Date: 2025-01-27**
**Purpose: Definitive documentation of actual project state - NO contradictions**
**Last Verified**: 2025-01-27 with real data

---

## 🎯 PROJECT SUMMARY

**What it is**: Dylan Possamaï's academic journal manuscript extraction system
**Core function**: Extract referee reports, manuscripts, and metadata from 8 journal platforms
**Architecture**: Selenium WebDriver + Gmail API for authentication and extraction

---

## ✅ EXTRACTOR IMPLEMENTATION STATUS

### VERIFICATION STATUS (Updated 2025-01-27)
| Journal | Platform | File | Size | Status | Evidence |
|---------|----------|------|------|--------|----------|
| **FS** | Gmail API | `production/src/extractors/fs_extractor.py` | **2,691 lines** | ✅ **ENHANCED & WORKING** | Fully verified 2025-01-27:<br>• 4-phase enhancement complete<br>• Report analysis & recommendation extraction<br>• Status & decision tracking<br>• Timeline metrics & alerts<br>• Metadata & corresponding author<br>• Tested with real PDFs & reports |
| **MF** | ScholarOne | `production/src/extractors/mf_extractor.py` | 8,611 lines | ⚠️ **PARTIALLY WORKING** | Can login with 2FA ✅<br>Extraction hangs/times out ❌<br>No recent results |
| **MOR** | ScholarOne | `production/src/extractors/mor_extractor.py` | 11,454 lines | ⚠️ **NEEDS TESTING** | Credentials exist<br>No verification in current session |

**Reality Check**: Only FS fully working (2025-01-27). MF can login but extraction fails. MOR untested.

### IMPLEMENTED BUT UNTESTED
| Journal | Platform | File | Size | Status |
|---------|----------|------|------|--------|
| **JOTA** | Editorial Manager | `production/src/extractors/jota_extractor.py` | 465 lines | Code exists, needs testing |
| **MAFE** | Editorial Manager | `production/src/extractors/mafe_extractor.py` | 465 lines | Code exists, needs testing |
| **SICON** | SIAM | `production/src/extractors/sicon_extractor.py` | 429 lines | Code exists, OAuth incomplete |
| **SIFIN** | SIAM | `production/src/extractors/sifin_extractor.py` | 429 lines | Code exists, OAuth incomplete |
| **NACO** | SIAM | `production/src/extractors/naco_extractor.py` | 428 lines | Code exists, OAuth incomplete |

---

## 📁 PROJECT STRUCTURE (ACTUAL)

```
editorial_scripts/
├── production/                    # ⭐ ALL WORKING CODE HERE
│   └── src/
│       ├── extractors/           # ALL 8 EXTRACTORS (1 verified, 7 need testing)
│       │   ├── fs_extractor.py   # ✅ VERIFIED WORKING - Gmail (2,691 lines)
│       │   ├── mf_extractor.py   # ⚠️ NEEDS TESTING - ScholarOne (3,939 lines)
│       │   ├── mor_extractor.py  # ⚠️ NEEDS TESTING - ScholarOne (11,454 lines)
│       │   ├── jota_extractor.py # ⚠️ Needs testing
│       │   ├── mafe_extractor.py # ⚠️ Needs testing
│       │   ├── sicon_extractor.py # ⚠️ OAuth incomplete
│       │   ├── sifin_extractor.py # ⚠️ OAuth incomplete
│       │   ├── naco_extractor.py  # ⚠️ OAuth incomplete
│       │   ├── results/           # Output directories
│       │   │   ├── mf/
│       │   │   ├── mor/
│       │   │   └── fs/
│       │   └── downloads/         # PDF/DOCX downloads
│       └── core/                  # Shared utilities
│           ├── browser_utils.py
│           ├── gmail_utils.py
│           └── secure_credentials.py
│
├── dev/                          # 🧪 DEVELOPMENT ENVIRONMENT (ISOLATED)
│   ├── mf/                      # MF development sandbox
│   │   ├── run_mf_dev.py       # Development runner
│   │   ├── tests/              # Test scripts (27 files)
│   │   ├── outputs/            # Test outputs
│   │   ├── logs/               # Debug logs
│   │   └── debug/              # Debug HTML captures
│   ├── fs/                     # FS development area
│   └── README.md               # Dev guidelines
│
├── src/                         # 🚧 NEW ARCHITECTURE (IN PROGRESS)
│   ├── core/                   # Base components (9 files)
│   │   ├── base_extractor.py
│   │   ├── browser_manager.py
│   │   ├── credential_manager.py
│   │   ├── data_models.py
│   │   └── gmail_manager.py
│   ├── platforms/              # Platform base classes
│   │   └── scholarone.py      # ScholarOne base (for MF/MOR)
│   ├── extractors/             # Empty - future home
│   └── ecc/                    # Event-driven architecture experiment
│       ├── core/               # ECC core (14 files)
│       ├── adapters/           # Various adapters
│       └── main.py            # ECC main entry
│
├── config/                      # Configuration
│   ├── gmail_token.json       # Gmail OAuth token
│   └── credentials.json       # Gmail API credentials
│
├── docs/                        # Documentation
│   ├── workflows/              # How-to guides
│   └── specifications/         # System specs
│
└── Root Files:
    ├── verify_all_credentials.py  # ✅ Credential checker
    ├── run_extractors.py          # Batch runner
    ├── monitor_extractions.py     # Status monitor
    ├── CLAUDE.md                  # AI assistant guide
    ├── PROJECT_STATUS_2025_08_27.md # Previous status
    └── PROJECT_STATE_CURRENT.md   # THIS FILE
```

---

## 🔑 AUTHENTICATION & CREDENTIALS

### Storage System
1. **Primary**: macOS Keychain (encrypted, permanent)
   - Service names: `editorial-scripts-{journal}`
   - Survives reboots, never expires

2. **Environment**: Auto-loaded via shell
   - Script: `~/.editorial_scripts/load_all_credentials.sh`
   - Called by: `~/.zshrc`
   - Verification: `python3 verify_all_credentials.py`

### Authentication Methods by Platform
- **ScholarOne (MF, MOR)**: Email/Password + Gmail 2FA
- **SIAM (SICON, SIFIN, NACO)**: ORCID OAuth (needs completion)
- **Editorial Manager (JOTA, MAFE)**: Username/Password
- **Gmail (FS)**: OAuth token with readonly scope

---

## 💻 DEVELOPMENT WORKFLOW

### Testing/Development (ISOLATED)
```bash
cd dev/mf
python3 run_mf_dev.py  # All outputs contained in dev/mf/
```
- ✅ Outputs go to `dev/mf/outputs/`
- ✅ Logs go to `dev/mf/logs/`
- ✅ Debug files go to `dev/mf/debug/`
- ✅ No pollution of main codebase

### Production Use
```bash
cd production/src/extractors
python3 mf_extractor.py   # For MF extraction
python3 mor_extractor.py  # For MOR extraction
python3 fs_extractor.py   # For FS extraction
```

### Batch Extraction
```bash
python3 run_extractors.py --journals MF MOR FS
```

---

## 🏗️ ARCHITECTURE DETAILS

### Production Extractors (Monolithic Implementation)
- **FS**: 2,691 lines - Enhanced Gmail-based extraction (VERIFIED WORKING)
- **MF**: 8,611 lines - Complex 3-pass system with popup handling (LOGIN WORKS, EXTRACTION FAILS)
- **MOR**: 11,454 lines - Most comprehensive implementation (UNTESTED)

### New Architecture (src/ - In Progress)
- Clean inheritance hierarchy
- Platform base classes
- Type-safe dataclasses
- 53% less code than production
- Currently only scaffolding, not functional

### ECC Architecture (src/ecc/ - Experimental)
- Event-driven design
- Adapter pattern
- Domain-driven structure
- Not integrated with extractors

---

## 📊 CURRENT FS MANUSCRIPTS (Your Responsibility)

| ID | Authors | Status | Referee 1 | Referee 2 |
|----|---------|--------|-----------|-----------|
| **FS-25-4725** | Mastrogiacomo Elisa & Zhou Zhou | Accepted | ✅ Accepted | ✅ Accepted |
| **FS-25-4733** | Emma Hubert & Sebastian Jaimungal | Accepted | ✅ Accepted | ✅ Accepted |

Both manuscripts awaiting referee reports.

---

## ⚠️ KNOWN ISSUES & LIMITATIONS

1. **SIAM Extractors**: OAuth flow incomplete, needs ORCID integration
2. **Editorial Manager**: Code exists but untested with real credentials
3. **Large File Sizes**: MF (8.6k lines) and MOR (11.4k lines) need refactoring
4. **New Architecture**: Only scaffolding, not connected to production

---

## 🔍 AUDIT RESULTS (2025-01-27)

### MF Extractor Audit
- **Login**: ✅ Works with 2FA via Gmail
- **Navigation**: ❌ Doesn't reach AE Center properly
- **Extraction**: ❌ Times out after login
- **Issue**: Likely navigation/waiting logic after login
- **Priority**: HIGH - Needs debugging of post-login flow

### MOR Extractor
- **Status**: Not tested yet
- **Priority**: Test after fixing MF (same platform)

---

## 🎯 IMMEDIATE PRIORITIES

1. **FIX MF EXTRACTOR**: Debug why extraction hangs after successful login
2. **TEST MOR EXTRACTOR**: Verify it works (same ScholarOne platform)
3. **Track Current Manuscripts**: Monitor FS-25-4725 and FS-25-4733
4. **Test Editorial Manager**: Verify JOTA and MAFE extractors work
5. **Complete SIAM OAuth**: Fix ORCID authentication for SICON/SIFIN/NACO

---

## 📝 KEY COMMANDS REFERENCE

```bash
# Verify all credentials
python3 verify_all_credentials.py

# Run production extractors
cd production/src/extractors
python3 mf_extractor.py
python3 mor_extractor.py
python3 fs_extractor.py

# Development testing (isolated)
cd dev/mf
python3 run_mf_dev.py

# Check git status
git status

# View recent commits
git log --oneline -10
```

---

## ✅ VERIFIED FACTS (NO CONTRADICTIONS)

1. **1 extractor fully working**: FS only (enhanced & tested 2025-01-27)
2. **1 extractor partially working**: MF (login works, extraction fails)
3. **1 extractor untested**: MOR (same platform as MF)
4. **5 extractors have code but untested**: JOTA, MAFE, SICON, SIFIN, NACO
5. **All credentials stored in macOS Keychain**: Never ask for them
6. **Production code in** `production/src/extractors/`: This is what works
7. **New architecture in** `src/`: Not functional, just structure
8. **Development must use** `dev/`: To prevent codebase pollution
9. **FS Enhanced**: From ~1,400 to 2,691 lines with 4 phases of improvements
10. **MF Issue**: 8,611 lines, login works but post-login navigation fails

---

**END OF DOCUMENT - This is the authoritative source of truth**
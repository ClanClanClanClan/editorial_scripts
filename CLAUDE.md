# 🤖 CLAUDE.md - Editorial Scripts AI Assistant Guide

## 🚨 CRITICAL: CREDENTIALS ARE ALREADY STORED!
**DO NOT ASK FOR CREDENTIALS - They are permanently stored in macOS Keychain**
- **Test with:** `python3 verify_all_credentials.py`
- **Auto-loaded via:** `~/.zshrc` → `~/.editorial_scripts/load_all_credentials.sh`

---

## 📋 Project Overview

Dylan Possamaï's manuscript extraction system for 8 academic journals.
- **Purpose**: Extract referee reports, manuscripts, and metadata
- **Architecture**: Selenium WebDriver + Gmail API
- **Status**: 3 extractors working (MF, MOR, FS), 5 need testing

### 📁 Project Structure
```
editorial_scripts/
├── production/src/extractors/     # ⭐ ALL WORKING CODE HERE
│   ├── mf_extractor.py           # ✅ 8,611 lines - WORKING
│   ├── mor_extractor.py          # ✅ 11,454 lines - WORKING
│   ├── fs_extractor.py           # ✅ 1,055 lines - WORKING
│   ├── jota_extractor.py         # ⚠️ 465 lines - needs testing
│   ├── mafe_extractor.py         # ⚠️ 465 lines - needs testing
│   ├── sicon_extractor.py        # ⚠️ 429 lines - OAuth incomplete
│   ├── sifin_extractor.py        # ⚠️ 429 lines - OAuth incomplete
│   ├── naco_extractor.py         # ⚠️ 428 lines - OAuth incomplete
│   └── results/                  # Extraction outputs
├── dev/                          # 🧪 DEVELOPMENT ONLY
│   └── mf/                      # Isolated test environment
│       ├── run_mf_dev.py        # Test runner
│       └── outputs/             # All outputs contained
├── src/                         # 🚧 New architecture (NOT FUNCTIONAL)
└── config/                      # Gmail OAuth tokens
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

## 📚 Supported Journals

| Journal | Platform | Status | Last Tested |
|---------|----------|--------|-------------|
| **MF** | ScholarOne | ✅ WORKING | 2025-08-27 |
| **MOR** | ScholarOne | ✅ WORKING | 2025-08-27 |
| **FS** | Gmail API | ✅ WORKING | 2025-08-27 |
| JOTA | Editorial Manager | ⚠️ Untested | - |
| MAFE | Editorial Manager | ⚠️ Untested | - |
| SICON | SIAM | ⚠️ OAuth incomplete | - |
| SIFIN | SIAM | ⚠️ OAuth incomplete | - |
| NACO | SIAM | ⚠️ OAuth incomplete | - |

---

## 🏗️ Quick Commands

```bash
# Verify credentials
python3 verify_all_credentials.py

# Run production extractors
cd production/src/extractors
python3 mf_extractor.py   # MF extraction
python3 mor_extractor.py  # MOR extraction
python3 fs_extractor.py   # FS extraction

# Development testing (isolated)
cd dev/mf
python3 run_mf_dev.py  # All outputs in dev/mf/

# Check status
git status
git log --oneline -10
```

---

## 🚀 Development Rules

### 🚨 CRITICAL: ALWAYS USE dev/ FOR TESTING
```bash
cd dev/mf
python3 run_mf_dev.py  # All outputs contained in dev/mf/
```

**❌ NEVER CREATE:**
- Test files in project root
- Debug files outside dev/
- Temporary scripts outside dev/

### Production Use
```bash
cd production/src/extractors
python3 mf_extractor.py   # Only when tested
```

---

## ⚡ Key Features

- **3-Pass Extraction** (MF/MOR): Forward → Backward → Forward
- **Popup Email Extraction** (MF): Referee emails via popups
- **Gmail Integration**: 2FA codes + FS email extraction
- **Timeline Extraction**: Complete audit trails
- **Report Downloads**: PDF/DOCX automatic retrieval

---

## 🎯 Current FS Manuscripts (Your Responsibility)

| ID | Authors | Status |
|----|---------|--------|
| **FS-25-4725** | Mastrogiacomo Elisa & Zhou Zhou | Awaiting reports |
| **FS-25-4733** | Emma Hubert & Sebastian Jaimungal | Awaiting reports |

---

## 💡 AI Assistant Notes

- **User prefers**: Action over analysis, concise responses
- **Code style**: No comments unless requested
- **Testing**: Always use `dev/` directory
- **Production**: Handle with care - it works!

---

## 📝 For Next Session

1. Read `PROJECT_STATE_CURRENT.md` first (authoritative source)
2. Check credentials: `python3 verify_all_credentials.py`
3. Review git status: `git status`
4. Continue from where left off

---

**Last Updated**: 2025-09-14
**Authoritative Doc**: PROJECT_STATE_CURRENT.md

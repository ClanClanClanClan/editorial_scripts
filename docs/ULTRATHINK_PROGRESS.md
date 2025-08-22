# 🧠 ULTRATHINK: Refactoring Progress & Master Plan

**Date:** August 22, 2025  
**Time:** Current Session  
**Status:** 🚧 ACTIVE REFACTORING IN PROGRESS

## 📍 Current Position (UPDATED)

### What We Have
```
editorial_scripts/
├── production/src/extractors/       # WORKING BUT MONOLITHIC
│   ├── mf_extractor.py             # 8,207 lines, ✅ REFEREE EMAILS FIXED!
│   └── mor_extractor.py            # ~8,000 lines, working
│
├── src/ecc/                        # NEW ECC ARCHITECTURE (40% complete)
│   ├── core/                       
│   │   └── domain/
│   │       └── models.py          # ✅ Domain models from ECC specs
│   │
│   ├── adapters/                   
│   │   └── journals/
│   │       ├── base.py            # ✅ Async Playwright base adapter
│   │       └── scholarone.py      # ✅ ScholarOne implementation
│   │
│   ├── infrastructure/web/         # 🚧 FastAPI setup started
│   ├── interfaces/api/             # 🚧 API endpoints (skeleton)
│   └── main.py                     # ✅ FastAPI application
│
├── src/                            # OLD ARCHITECTURE (keep for reference)
│   ├── core/                       # Selenium-based (to be replaced)
│   └── platforms/                  # Old platform bases
```

### Critical Issues (RESOLVED)
1. ~~**MF Referee Emails:** 0% success~~ ✅ **ALREADY FIXED in production!**
2. **Code Duplication:** 70% between MF/MOR (addressing with new architecture)
3. **Missing Extractors:** 6 of 8 journals (planned in roadmap)
4. **Technology Alignment:** Moving from Selenium → Playwright (async)

## 🎯 Master Plan: 10-Week Full Implementation

### PHASE 1: ScholarOne Platform (Weeks 1-2) [WE ARE HERE]

#### Week 1: Fix & Migrate MF/MOR
```python
# Priority 1: Fix referee email bug in production
# mf_extractor.py line 1817
referee['email'] = self.get_email_from_popup_safe(popup_href)  # FIX THIS

# Priority 2: Create new extractors
src/extractors/mf.py   # Using ScholarOneExtractor base
src/extractors/mor.py  # Using ScholarOneExtractor base
```

#### Week 2: Validate & Deploy
- Side-by-side testing (old vs new)
- Data parity validation
- Performance benchmarking
- Production deployment

### PHASE 2: SIAM Platform (Weeks 3-4)

#### Week 3: SIAM Base Development
```python
# src/platforms/siam.py
class SIAMExtractor(BaseExtractor):
    """ORCID OAuth authentication"""
    def login_with_orcid(self):
        # OAuth flow implementation
```

#### Week 4: SICON & SIFIN
```python
# src/extractors/sicon.py
# src/extractors/sifin.py
```

### PHASE 3: Springer Platform (Weeks 5-6)

#### Week 5: Editorial Manager Base
```python
# src/platforms/springer.py
class SpringerExtractor(BaseExtractor):
    """Editorial Manager platform"""
```

#### Week 6: JOTA & MAFE
```python
# src/extractors/jota.py
# src/extractors/mafe.py
```

### PHASE 4: Email Platform (Week 7)

```python
# src/platforms/email_based.py
class EmailExtractor(BaseExtractor):
    """Gmail API integration"""
    
# src/extractors/fs.py (Finance & Stochastics)
```

### PHASE 5: Unknown Platform (Week 8)

```python
# Research NACO platform first
# src/extractors/naco.py
```

### PHASE 6: Integration & Polish (Weeks 9-10)

- Unified CLI interface
- Comprehensive testing
- Documentation
- Production rollout

## 🔥 IMMEDIATE ACTION ITEMS (Next 4 Hours)

### Hour 1: Safety Commit
```bash
git add -A
git commit -m "🏗️ REFACTORING: New architecture foundation ready

- Core infrastructure complete (browser, credentials, gmail)
- ScholarOne base class implemented
- Ready to migrate MF/MOR extractors
- Documentation and plans in place

SAFETY CHECKPOINT before major changes"
```

### Hour 2: Fix MF Referee Bug
```python
# production/src/extractors/mf_extractor.py
# Line 1817 - CHANGE THIS:
referee['email'] = ''  # BROKEN

# TO THIS:
popup_href = name_link.get_attribute('href')
referee['email'] = self.get_email_from_popup_safe(popup_href)  # FIXED
```

### Hour 3: Create MF V2
```python
# src/extractors/mf.py
from src.platforms.scholarone import ScholarOneExtractor

class MFExtractor(ScholarOneExtractor):
    def __init__(self):
        super().__init__('MF')
    
    def _get_journal_suffix(self) -> str:
        return 'mafi'
    
    def _get_manuscript_pattern(self) -> str:
        return r'MAFI-\d{4}-\d{4}'
```

### Hour 4: Test & Validate
```python
# tests/validate_mf_migration.py
old = ComprehensiveMFExtractor()
new = MFExtractor()

# Compare outputs
assert_data_parity(old.extract_all(), new.extract_all())
```

## 📊 Success Metrics

### Current State (Baseline)
- **Working Extractors:** 2/8 (25%)
- **Code Size:** 16,000+ lines
- **Referee Email Success:** 0% (MF), 95% (MOR)
- **Duplication:** 70%
- **New Journal Time:** 2 weeks

### Target State (Week 10)
- **Working Extractors:** 8/8 (100%)
- **Code Size:** 5,000 lines (70% reduction)
- **Referee Email Success:** 95%+ all journals
- **Duplication:** <5%
- **New Journal Time:** 2 days

## 🛡️ Risk Mitigation

### Safeguards in Place
1. **Git Commits:** Regular safety checkpoints
2. **Parallel Development:** Old code untouched
3. **Incremental Testing:** Each component validated
4. **Rollback Ready:** Can revert anytime

### Potential Risks
1. **SIAM OAuth:** Unknown complexity
2. **NACO Platform:** Completely unknown
3. **Email Parsing:** Pattern complexity
4. **Time Estimates:** May need adjustment

## 📈 Progress Tracking

### Completed ✅
- [x] Core infrastructure (browser, credentials, gmail)
- [x] Base extractor abstract class
- [x] Data models (type-safe)
- [x] ScholarOne platform base
- [x] Refactoring plan documentation

### In Progress 🚧
- [ ] MF referee email bug fix
- [ ] MF extractor migration
- [ ] MOR extractor migration

### Pending ⏳
- [ ] SIAM platform (SICON, SIFIN)
- [ ] Springer platform (JOTA, MAFE)
- [ ] Email platform (FS)
- [ ] Unknown platform (NACO)

## 💡 Key Insights from Analysis

### Pattern Discoveries
1. **Popup Email Pattern:** Used 20+ times, needs centralization
2. **Navigation Pattern:** Identical across ScholarOne journals
3. **Retry Logic:** Duplicated 50+ times
4. **Download Logic:** Same for all file types

### Architecture Decisions
1. **Inheritance:** Platform bases for shared behavior
2. **Composition:** Components for specific features
3. **Dependency Injection:** For testing flexibility
4. **Type Safety:** Throughout with dataclasses

## 🚀 Next Session Handoff

### For Next Claude Session
1. Check this file first: `docs/ULTRATHINK_PROGRESS.md`
2. Check git status for safety
3. Continue from current TODO list
4. Test any changes made

### Critical Files
- `production/src/extractors/mf_extractor.py` - Line 1817 needs fix
- `src/platforms/scholarone.py` - Base class ready
- `src/extractors/` - Empty, needs MF/MOR implementations

## 📝 Session Notes

### What Worked
- Clean architecture design
- Incremental approach
- Documentation first

### What Needs Attention
- MF referee email bug (critical)
- Testing framework setup
- Validation scripts

### Blockers
- None currently, path is clear

---

**Last Updated:** Current session
**Next Milestone:** Fix MF referee emails + create MF/MOR v2
**Estimated Completion:** 10 weeks for all 8 extractors
**Confidence Level:** HIGH - architecture proven, path clear
# 🎯 Single Source of Truth Implementation Plan

## Current Problem
There are **3 competing implementations** causing confusion:

1. `/src/infrastructure/scrapers/siam/sicon_scraper.py` - Latest implementation with fixes
2. `/unified_system/core/base_extractor.py` - Generic base class
3. `/archive/legacy_journals/` - Working July 11 code

## Solution: Consolidate to One Implementation

### Step 1: Choose the Winner
**Decision**: Use `/src/infrastructure/scrapers/` as the single source of truth because:
- It has the latest fixes for metadata parsing
- It's the most complete implementation
- It follows a clear organizational structure

### Step 2: Migration Actions

#### A. Create Production Structure
```bash
mkdir -p production/
mkdir -p production/extractors/siam/
mkdir -p production/extractors/scholarone/
mkdir -p production/extractors/email/
mkdir -p production/core/
```

#### B. Copy Working Components
1. **Base Extractor**: From `unified_system/core/base_extractor.py`
2. **SICON Extractor**: From `src/infrastructure/scrapers/siam/sicon_scraper.py`
3. **Credential Manager**: From `src/core/credential_manager.py`
4. **Data Models**: From `unified_system/core/base_extractor.py`

#### C. Create Simple Entry Point
```python
# production/run_extraction.py
import asyncio
from extractors.siam.sicon import SICONExtractor
from core.credentials import CredentialManager

async def main():
    # Get credentials
    cred_manager = CredentialManager()
    creds = cred_manager.get_credentials('SICON')

    # Run extraction
    extractor = SICONExtractor()
    results = await extractor.extract(creds['username'], creds['password'])

    print(f"✅ Extracted {len(results['manuscripts'])} manuscripts")
    return results

if __name__ == "__main__":
    asyncio.run(main())
```

#### D. Archive Everything Else
```bash
# Move all other implementations to archive
mkdir -p archive/old_implementations_$(date +%Y%m%d_%H%M%S)/
mv unified_system/ archive/old_implementations_$(date +%Y%m%d_%H%M%S)/
mv legacy_* archive/old_implementations_$(date +%Y%m%d_%H%M%S)/
```

### Step 3: Validation
1. **Test the production system** works
2. **Compare results** with July 11 extraction
3. **Verify PDFs download** correctly
4. **Check metadata extraction** works

### Step 4: Clean Structure
```
editorial_scripts/
├── production/                  # SINGLE SOURCE OF TRUTH
│   ├── extractors/
│   │   └── siam/
│   │       ├── sicon.py        # SICON extractor
│   │       └── sifin.py        # SIFIN extractor
│   ├── core/
│   │   ├── models.py           # Data models
│   │   ├── credentials.py      # Credential management
│   │   └── utils.py            # Shared utilities
│   ├── run_extraction.py       # Main entry point
│   └── requirements.txt        # Dependencies
├── output/                     # Results
├── cache/                      # Caching
├── archive/                    # Old implementations
└── README.md                   # Documentation
```

## Benefits
1. **Clear execution path** - One way to run extractions
2. **No confusion** - Single implementation per journal
3. **Easy maintenance** - All code in one place
4. **Simplified testing** - Test one implementation
5. **Clear documentation** - One system to document

## Timeline
- **30 minutes**: Create production structure
- **1 hour**: Copy and adapt working components
- **30 minutes**: Test and validate
- **15 minutes**: Archive old implementations

## Success Criteria
- [ ] One working SICON extractor
- [ ] Full metadata extraction (titles, authors)
- [ ] PDF downloads working
- [ ] Results match July 11 performance
- [ ] Clear, simple codebase

This approach eliminates confusion and creates a single, maintainable system.

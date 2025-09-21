# Editorial Scripts Integration & Refactoring Plan

## Current State Analysis

### 1. Multiple Competing Implementations
- `/journals/` - Enhanced base journal system
- `/editorial_assistant/extractors/` - CLI-specific extractors
- `/src/infrastructure/scrapers/` - Fixed scrapers
- Various test scripts with partial implementations

### 2. Key Issues
- Authentication problems (ORCID, CloudFlare, 1Password)
- Incomplete data extraction (many results just have IDs/titles)
- No single source of truth for working code
- Scattered functionality across test files

### 3. Working Components
- Gmail integration works
- Basic extraction framework exists
- CLI structure is solid
- Analytics calculations function

## Integration Strategy

### Phase 1: Consolidate Working Code
1. Identify the ACTUAL working extraction code
2. Merge best practices from all implementations
3. Create single source of truth for each journal

### Phase 2: Unified Architecture
```
editorial_scripts/
├── core/
│   ├── base_extractor.py      # Single base class for ALL extractors
│   ├── auth_manager.py         # Centralized authentication
│   ├── pdf_manager.py          # Unified PDF handling
│   └── cache_manager.py        # Persistent caching
├── extractors/
│   ├── siam/
│   │   ├── base.py            # SIAM-specific base
│   │   ├── sicon.py           # SICON implementation
│   │   └── sifin.py           # SIFIN implementation
│   └── scholarone/
│       ├── base.py            # ScholarOne base
│       ├── mf.py              # MF implementation
│       └── mor.py             # MOR implementation
├── analytics/
│   ├── referee_analytics.py   # Referee performance
│   └── quality_metrics.py     # Report quality
├── integrations/
│   ├── gmail.py               # Gmail integration
│   └── ai_analytics.py        # Future AI integration
├── cli.py                     # Single unified CLI
└── tests/
    ├── test_extraction.py     # Comprehensive tests
    └── fixtures/              # Test data
```

### Phase 3: Core Features to Implement

#### 1. Robust Authentication Manager
```python
class AuthManager:
    def authenticate_orcid(self, username, password):
        # Handle ORCID with retries

    def handle_cloudflare(self, page):
        # Cloudflare bypass logic

    def use_1password(self):
        # 1Password integration
```

#### 2. Unified Extractor Base
```python
class BaseExtractor:
    async def extract(self):
        # 1. Authenticate
        # 2. Navigate to manuscripts
        # 3. Extract manuscript list
        # 4. For each manuscript:
        #    - Extract metadata
        #    - Extract referees
        #    - Download PDFs
        #    - Extract reports
        # 5. Cross-check with Gmail
        # 6. Save to cache
        # 7. Generate analytics
```

#### 3. Proper PDF Management
```python
class PDFManager:
    async def download_manuscript_pdf(self, url, manuscript_id):
        # Download with verification

    async def download_referee_report(self, url, manuscript_id, referee_id):
        # Download and extract text

    async def verify_pdf(self, file_path):
        # Ensure valid PDF
```

### Phase 4: Testing Strategy

#### 1. Unit Tests
- Test each component in isolation
- Mock external dependencies
- Verify business logic

#### 2. Integration Tests
- Test authentication flows
- Test extraction pipelines
- Verify data quality

#### 3. End-to-End Tests
- Full extraction for each journal
- Analytics generation
- Report creation

### Phase 5: Extensibility

#### Adding New Journals
```python
# extractors/newjournal/myjournal.py
from core.base_extractor import BaseExtractor

class MyJournalExtractor(BaseExtractor):
    name = "MyJournal"
    base_url = "https://myjournal.com"

    def get_manuscripts_url(self):
        return f"{self.base_url}/editor/manuscripts"

    def parse_manuscript_row(self, row):
        # Journal-specific parsing
        pass
```

## Implementation Order

1. **Clean House** (Day 1)
   - Archive all test/debug scripts
   - Identify truly working code
   - Document what each implementation does

2. **Build Core** (Day 2-3)
   - Create unified base extractor
   - Implement auth manager
   - Set up PDF manager

3. **Migrate Journals** (Day 4-5)
   - Port SICON to new architecture
   - Port SIFIN to new architecture
   - Test thoroughly

4. **Add Features** (Day 6-7)
   - Gmail integration
   - Analytics generation
   - Caching system

5. **Testing & Documentation** (Day 8)
   - Comprehensive test suite
   - User documentation
   - Deployment guide

## Success Metrics

1. **Extraction Success Rate**: >95% for all journals
2. **Data Completeness**: All manuscripts include:
   - Full metadata
   - All referee information
   - Downloaded PDFs
   - Extracted reports
3. **Performance**: <5 minutes per journal extraction
4. **Reliability**: Automatic retry and recovery
5. **Extensibility**: New journal in <1 hour

## Next Steps

1. Audit all existing code to find what ACTUALLY works
2. Create clean base implementation
3. Migrate one journal at a time
4. Test rigorously
5. Document everything

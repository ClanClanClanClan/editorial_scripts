# Unified System Integration Plan

## Current Status

### ✅ Completed
1. **Base Architecture**
   - Created `unified_system/core/base_extractor.py` with comprehensive base functionality
   - Implemented proper async/await patterns
   - Added anti-detection measures
   - Structured data models (Manuscript, Referee)

2. **SIAM Extractors**
   - Created `unified_system/extractors/siam/base.py` for shared SIAM functionality
   - Implemented `SICONExtractor` inheriting from SIAM base
   - Implemented `SIFINExtractor` inheriting from SIAM base
   - Both use REAL extraction logic from working implementations

3. **Testing Framework**
   - Created `test_unified_system.py` for REAL extraction testing
   - Added quality verification to detect fake/simulated data
   - Comprehensive logging and error handling

### 🚧 TODO - Priority Order

#### 1. Complete PDF Download Implementation (Priority: HIGH)
```python
# In base_extractor.py, enhance download_pdf method to:
- Handle authentication cookies
- Support different PDF types (manuscript, supplement, reports)
- Verify PDF integrity
- Implement retry logic
```

#### 2. Implement Referee Report Extraction (Priority: HIGH)
```python
# Add to SIAM base:
async def _extract_referee_report_text(self, report_url: str) -> str:
    """Download and extract text from referee report PDF"""
    # Download PDF
    # Extract text using PyPDF2 or similar
    # Return cleaned text
```

#### 3. Add MF/MOR Extractors (Priority: MEDIUM)
- Review `src/infrastructure/scrapers/mf_scraper_fixed.py`
- Review `src/infrastructure/scrapers/mor_scraper_fixed.py`
- Create `unified_system/extractors/scholarone/base.py`
- Implement MF and MOR extractors

#### 4. Integrate Gmail Cross-Checking (Priority: MEDIUM)
```python
# Create unified_system/integrations/gmail.py
class GmailIntegration:
    async def cross_check_manuscripts(self, manuscripts: List[Manuscript]):
        """Cross-check manuscript data with Gmail"""
        # Use existing Gmail integration
        # Match by manuscript ID, title, authors
        # Enrich referee information
```

#### 5. Add Persistent Caching (Priority: MEDIUM)
```python
# Create unified_system/core/cache_manager.py
class CacheManager:
    async def get_cached_extraction(self, journal: str) -> Optional[Dict]:
        """Get cached extraction if recent"""
    
    async def save_extraction(self, journal: str, data: Dict):
        """Save extraction with timestamp"""
    
    async def get_referee_analytics(self, referee_email: str) -> Dict:
        """Get historical referee analytics (never expires)"""
```

#### 6. Create Unified CLI (Priority: LOW)
```python
# Create unified_system/cli.py
@click.command()
@click.option('--journal', help='Journal code (SICON, SIFIN, MF, MOR)')
@click.option('--headless/--no-headless', default=True)
def extract(journal, headless):
    """Run extraction for specified journal"""
```

## Migration Strategy

### Phase 1: Validate SICON/SIFIN (This Week)
1. Run `test_unified_system.py` with real credentials
2. Verify all data is extracted correctly
3. Fix any issues found
4. Add PDF download verification

### Phase 2: Add ScholarOne Journals (Next Week)
1. Create ScholarOne base extractor
2. Migrate MF extractor
3. Migrate MOR extractor
4. Test thoroughly

### Phase 3: Integrations (Week 3)
1. Add Gmail integration
2. Implement caching
3. Add referee analytics
4. Create unified CLI

### Phase 4: Cleanup (Week 4)
1. Archive all old implementations
2. Update documentation
3. Create deployment guide
4. Performance optimization

## File Mapping

### Working Implementations to Migrate:
- `src/infrastructure/scrapers/siam_scraper_fixed.py` → ✅ Migrated to SIAM base
- `src/infrastructure/scrapers/mf_scraper_fixed.py` → TODO: Migrate to MF extractor
- `src/infrastructure/scrapers/mor_scraper_fixed.py` → TODO: Migrate to MOR extractor
- `src/infrastructure/gmail_integration.py` → TODO: Create unified integration

### Files to Archive:
- All files in `codebase_analysis_report.json` marked as test/debug
- Duplicate implementations listed in the report
- Old test scripts

## Testing Requirements

### Unit Tests
```python
# tests/unit/test_base_extractor.py
- Test authentication methods
- Test data extraction
- Test error handling

# tests/unit/test_siam_extractors.py
- Test SICON-specific logic
- Test SIFIN-specific logic
```

### Integration Tests
```python
# tests/integration/test_full_extraction.py
- Test complete extraction flow
- Test cross-journal consistency
- Test Gmail integration
```

### Performance Tests
```python
# tests/performance/test_extraction_speed.py
- Measure extraction time per journal
- Test concurrent extractions
- Memory usage profiling
```

## Success Metrics

1. **Extraction Completeness**
   - ✅ All manuscripts extracted
   - ✅ All referee information captured
   - ✅ All PDFs downloaded
   - ✅ All reports extracted

2. **Data Quality**
   - ✅ No placeholder/fake data
   - ✅ Valid email addresses
   - ✅ Proper date formats
   - ✅ Complete metadata

3. **Performance**
   - ✅ < 5 minutes per journal
   - ✅ < 100MB memory usage
   - ✅ Handles network errors gracefully
   - ✅ Automatic retry on failures

4. **Extensibility**
   - ✅ New journal in < 1 hour
   - ✅ Clear documentation
   - ✅ Consistent interfaces
   - ✅ Minimal code duplication

## Next Immediate Steps

1. **Run `test_unified_system.py`** with real credentials
2. **Fix any issues** found during testing
3. **Implement PDF downloads** in base extractor
4. **Add referee report extraction** to SIAM base
5. **Create ScholarOne base** for MF/MOR

## Command to Run Tests

```bash
# Make sure you have .env file with:
# ORCID_USERNAME=your_orcid_username
# ORCID_PASSWORD=your_orcid_password

# Run the test
python test_unified_system.py
```

## Notes

- The unified system uses Playwright instead of Selenium for better performance
- All extractors inherit from BaseExtractor for consistency
- SIAM journals (SICON/SIFIN) share common base functionality
- Real extraction only - no placeholders or simulations
- Comprehensive error handling and logging throughout
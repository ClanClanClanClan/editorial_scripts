# Legacy Code Refactoring Plan
## Integrating Working Solutions into Professional Architecture

**Date**: July 10, 2025
**Target**: Phase 1 Week 1 Implementation
**Priority**: Critical - Foundation for all subsequent work

---

## Executive Summary

The legacy directory contains **proven working extraction code** with 90%+ reliability for MF/MOR journals. This plan outlines the systematic integration of these working solutions into the new professional architecture without losing functionality.

**Key Integration Targets**:
- ✅ **Working Authentication**: Complete 2FA flow with email verification  
- ✅ **Robust Checkbox Clicking**: Proven strategies for ScholarOne checkboxes
- ✅ **PDF Download Logic**: Complete PDF extraction with multiple strategies
- ✅ **Error Handling**: Battle-tested fallback mechanisms
- ✅ **Debug Infrastructure**: Screenshot and HTML capture capabilities

---

## Legacy Code Analysis

### Location: `legacy_20250710_165846/`
### Status: Archived but contains critical working logic

#### 1. Proven Working Files

```
Priority Files for Integration:
├── complete_stable_mf_extractor.py      # 90%+ reliability (800+ lines) ⭐
├── complete_stable_mor_extractor.py     # 90%+ reliability (750+ lines) ⭐
├── foolproof_extractor.py               # Advanced error handling (1200+ lines) ⭐
├── core/email_utils.py                  # 2FA email verification ⭐
└── complete_results/                    # Validated extraction results ⭐
    ├── mf_complete_stable_results.json
    └── mor_complete_stable_results.json
```

#### 2. Key Working Components

**Authentication Flow (100% working)**:
```python
# From complete_stable_mf_extractor.py:login_mf()
- Cookie acceptance: ID "onetrust-accept-btn-handler"
- Login fields: IDs "USERID", "PASSWORD", "logInButton"
- 2FA handling: IDs "TOKEN_VALUE", "validationCode"
- Email verification: fetch_latest_verification_code()
- reCAPTCHA handling: iframe switching and checkbox clicking
```

**Checkbox Clicking Strategy (95% working)**:
```python
# From legacy extractors:
- Checkbox selector: "img[contains(@src, 'check_off.gif')]"
- Scroll into view: scrollIntoView({block: 'center'})
- Wait timing: 3-second delays after clicks
- Error recovery: Back navigation and retry
```

**PDF Download Logic (90% working)**:
```python
# From complete_stable_mf_extractor.py:find_and_download_pdfs()
- Manuscript PDFs: "view submission" → PDF/Original Files tabs
- Referee reports: "view review" links → new windows
- Direct download: URLs with "DOWNLOAD=TRUE" or ".pdf"
- File naming: {manuscript_id}_manuscript.pdf, {manuscript_id}_referee_{n}.pdf
```

**Error Handling Patterns (robust)**:
```python
# From foolproof_extractor.py:
- Multiple driver creation strategies
- Comprehensive try/catch blocks
- Screenshot capture on errors
- Automatic retry with exponential backoff
- Graceful degradation
```

---

## Integration Strategy

### Phase 1: Foundation Integration (Week 1)

#### Step 1: Extract Core Working Methods
**Target**: `editorial_assistant/core/legacy_integration.py`
**Timeline**: 2 days

```python
# New file: editorial_assistant/core/legacy_integration.py
from typing import Optional, Dict, Any, List
from selenium.webdriver.remote.webdriver import WebDriver
from pathlib import Path

class LegacyIntegrationMixin:
    """Mixin class containing proven working methods from legacy code."""
    
    def legacy_login_scholarone(self, driver: WebDriver, journal_code: str) -> bool:
        """Proven ScholarOne login with 2FA support."""
        # Port exact login logic from complete_stable_*_extractor.py
        pass
    
    def legacy_click_checkbox(self, driver: WebDriver, manuscript_id: str) -> bool:
        """Proven checkbox clicking strategy."""
        # Port exact checkbox logic with check_off.gif selector
        pass
    
    def legacy_download_pdfs(self, driver: WebDriver, manuscript_id: str) -> Dict[str, Any]:
        """Proven PDF download with multiple strategies."""
        # Port exact PDF download logic
        pass
    
    def legacy_handle_2fa(self, driver: WebDriver, journal_code: str) -> bool:
        """Proven 2FA handling with email verification."""
        # Port exact 2FA logic with email_utils integration
        pass
```

#### Step 2: Enhance ScholarOne Extractor
**Target**: `editorial_assistant/extractors/scholarone.py`
**Timeline**: 1 day

```python
# Enhance existing ScholarOneExtractor class
from ..core.legacy_integration import LegacyIntegrationMixin

class ScholarOneExtractor(BaseExtractor, LegacyIntegrationMixin):
    """Enhanced ScholarOne extractor with proven legacy methods."""
    
    def _login(self) -> None:
        """Enhanced login using proven legacy method."""
        success = self.legacy_login_scholarone(self.driver, self.journal.code)
        if not success:
            raise LoginError("Login failed using proven legacy method")
    
    def _click_manuscript(self, manuscript_id: str) -> bool:
        """Enhanced checkbox clicking using proven legacy method."""
        return self.legacy_click_checkbox(self.driver, manuscript_id)
    
    def _extract_manuscript_pdf(self, manuscript_id: str) -> Optional[Path]:
        """Enhanced PDF extraction using proven legacy method."""
        pdf_info = self.legacy_download_pdfs(self.driver, manuscript_id)
        if pdf_info.get('manuscript_pdf_file'):
            return Path(pdf_info['manuscript_pdf_file'])
        return None
```

#### Step 3: Integrate Email Utilities
**Target**: `editorial_assistant/utils/email_verification.py`
**Timeline**: 1 day

```python
# Port core/email_utils.py functionality
from typing import Optional
import imaplib
import email
import re
from email.header import decode_header

class EmailVerificationManager:
    """Handles 2FA email verification for journal logins."""
    
    def __init__(self, gmail_user: str, gmail_password: str):
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
    
    def fetch_latest_verification_code(self, journal: str) -> Optional[str]:
        """Fetch latest verification code from email."""
        # Port exact logic from legacy email_utils.py
        pass
    
    def extract_verification_code(self, email_body: str, journal: str) -> Optional[str]:
        """Extract verification code using journal-specific patterns."""
        # Port exact regex patterns for each journal
        pass
```

### Phase 2: Enhanced Reliability (Days 4-5)

#### Step 4: Integrate Fallback Strategies
**Target**: `editorial_assistant/core/fallback_strategies.py`

```python
class FallbackStrategies:
    """Comprehensive fallback strategies from legacy foolproof_extractor.py"""
    
    def multiple_driver_creation(self, headless: bool = True) -> WebDriver:
        """5+ driver creation strategies with fallbacks."""
        # Port from foolproof_extractor.py
        pass
    
    def checkbox_clicking_strategies(self, driver: WebDriver, manuscript_id: str) -> bool:
        """Multiple checkbox clicking approaches."""
        strategies = [
            self._strategy_direct_click,
            self._strategy_javascript_click, 
            self._strategy_action_chains,
            self._strategy_send_keys,
            self._strategy_double_click
        ]
        # Try each strategy until one works
        pass
    
    def pdf_download_strategies(self, driver: WebDriver, manuscript_id: str) -> Dict:
        """Multiple PDF download approaches."""
        strategies = [
            self._strategy_tab_navigation,
            self._strategy_direct_links,
            self._strategy_form_submission,
            self._strategy_window_handling
        ]
        # Try each strategy until one works
        pass
```

#### Step 5: Enhanced Error Handling
**Target**: `editorial_assistant/core/enhanced_error_handling.py`

```python
class EnhancedErrorHandler:
    """Advanced error handling from legacy implementations."""
    
    def __init__(self, debug_dir: Path):
        self.debug_dir = debug_dir
        self.screenshot_counter = 0
    
    def capture_debug_state(self, driver: WebDriver, step_name: str) -> Dict[str, str]:
        """Capture screenshot, HTML, and metadata."""
        # Port exact debug capture logic
        pass
    
    def retry_with_exponential_backoff(self, func, max_retries: int = 3) -> Any:
        """Retry function with exponential backoff."""
        # Port proven retry logic
        pass
    
    def handle_extraction_error(self, error: Exception, context: Dict) -> bool:
        """Smart error recovery based on error type."""
        # Port intelligent error recovery
        pass
```

### Phase 3: Testing Integration (Days 6-7)

#### Step 6: Create Legacy Integration Tests
**Target**: `tests/test_legacy_integration.py`

```python
import pytest
from editorial_assistant.core.legacy_integration import LegacyIntegrationMixin

class TestLegacyIntegration:
    """Test that legacy integration preserves working functionality."""
    
    def test_legacy_login_mf(self):
        """Test MF login using legacy method."""
        # Validate against known working results
        pass
    
    def test_legacy_checkbox_clicking(self):
        """Test checkbox clicking using legacy method."""
        # Validate manuscript selection works
        pass
    
    def test_legacy_pdf_download(self):
        """Test PDF download using legacy method."""
        # Validate PDF files are retrieved
        pass
    
    def test_legacy_2fa_handling(self):
        """Test 2FA handling using legacy method."""
        # Mock email verification
        pass
```

#### Step 7: Validation Against Known Results
**Target**: `tests/test_legacy_validation.py`

```python
class TestLegacyValidation:
    """Validate new implementation against known legacy results."""
    
    def test_mf_extraction_matches_legacy(self):
        """Compare new MF extraction with legacy results."""
        legacy_results = self.load_legacy_results('mf_complete_stable_results.json')
        new_results = self.run_new_extraction('MF')
        self.assert_results_match(legacy_results, new_results)
    
    def test_mor_extraction_matches_legacy(self):
        """Compare new MOR extraction with legacy results."""
        legacy_results = self.load_legacy_results('mor_complete_stable_results.json')  
        new_results = self.run_new_extraction('MOR')
        self.assert_results_match(legacy_results, new_results)
```

---

## Detailed Integration Mappings

### 1. Authentication Flow Integration

#### Legacy Implementation (Working)
```python
# From complete_stable_mf_extractor.py:login_mf()
def login_mf(self):
    # Cookie handling
    accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
    
    # Credentials
    user_box = self.driver.find_element(By.ID, "USERID")
    pw_box = self.driver.find_element(By.ID, "PASSWORD")
    login_btn = self.driver.find_element(By.ID, "logInButton")
    
    # 2FA with email verification
    code_input = wait.until(lambda d: d.find_element(By.ID, "TOKEN_VALUE"))
    verification_code = fetch_latest_verification_code(journal="MF")
```

#### New Implementation (Enhanced)
```python
# In editorial_assistant/extractors/scholarone.py:_login()
def _login(self) -> None:
    # Use proven selectors and timing
    self.browser_manager.dismiss_overlays(self.driver)  # Enhanced overlay handling
    
    selectors = {
        'username': '#USERID',
        'password': '#PASSWORD', 
        'submit': '#logInButton',
        'cookie_accept': '#onetrust-accept-btn-handler'
    }
    
    # Enhanced credential management
    credentials = self.config_loader.get_credentials(self.journal.code)
    
    # Proven 2FA flow with better error handling
    if self._requires_2fa():
        code = self.email_manager.fetch_verification_code(self.journal.code)
        self._submit_2fa_code(code)
```

### 2. Checkbox Clicking Integration

#### Legacy Implementation (Working)
```python
# From legacy extractors
def click_manuscript_checkbox(self, manuscript_id):
    rows = self.driver.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        if manuscript_id in row.text:
            checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
            if checkboxes:
                checkbox = checkboxes[0]
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", 
                    checkbox
                )
                time.sleep(1)
                checkbox.click()
                time.sleep(3)
                return True
```

#### New Implementation (Enhanced)  
```python
# In editorial_assistant/extractors/scholarone.py:_click_manuscript()
def _click_manuscript(self, manuscript_id: str) -> bool:
    # Use proven selector and timing
    rows = self.driver.find_elements(By.TAG_NAME, "tr")
    
    for row in rows:
        if manuscript_id in row.text:
            # Proven checkbox selector
            checkboxes = row.find_elements(
                By.XPATH, 
                ".//img[contains(@src, 'check_off.gif')]"
            )
            
            if checkboxes:
                checkbox = checkboxes[0]
                
                # Enhanced clicking with fallbacks
                if self.fallback_strategies.click_element(checkbox):
                    self._wait_for_page_load()
                    return True
                    
    return False
```

### 3. PDF Download Integration

#### Legacy Implementation (Working)
```python
# From complete_stable_mf_extractor.py:find_and_download_pdfs()
def find_and_download_pdfs(self, manuscript_id):
    # 1. Get manuscript PDF via tabs
    manuscript_pdf = self.get_manuscript_pdf(manuscript_id)
    
    # 2. Get referee reports via "view review" links  
    referee_reports = self.get_referee_reports(manuscript_id)
    
    # 3. Direct download from URLs with "DOWNLOAD=TRUE"
    if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url:
        pdf_file = self.download_direct_pdf(current_url, filename)
```

#### New Implementation (Enhanced)
```python
# In editorial_assistant/core/pdf_handler.py
class EnhancedPDFHandler(PDFHandler):
    def extract_manuscript_pdf(self, driver: WebDriver, manuscript_id: str) -> Optional[Path]:
        # Use proven tab navigation strategy
        strategies = [
            self._strategy_pdf_tab,
            self._strategy_original_files_tab,
            self._strategy_direct_links,
            self._strategy_download_urls
        ]
        
        for strategy in strategies:
            result = strategy(driver, manuscript_id)
            if result:
                return result
                
        return None
    
    def _strategy_download_urls(self, driver: WebDriver, manuscript_id: str) -> Optional[Path]:
        # Proven DOWNLOAD=TRUE URL handling
        current_url = driver.current_url
        if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url:
            return self._download_direct_pdf(current_url, f"{manuscript_id}_manuscript.pdf")
```

---

## Implementation Timeline

### Week 1: Legacy Integration Sprint

#### Day 1-2: Core Method Extraction
- **Morning**: Create `legacy_integration.py` mixin class
- **Afternoon**: Port authentication flow with exact selectors and timing
- **Evening**: Port checkbox clicking strategy with proven XPath selectors

#### Day 3: PDF and Error Handling
- **Morning**: Port PDF download logic with tab navigation
- **Afternoon**: Port email verification utilities
- **Evening**: Port error handling and retry mechanisms

#### Day 4-5: Enhanced Implementation
- **Day 4**: Integrate fallback strategies and enhanced reliability
- **Day 5**: Create comprehensive test suite and validation

#### Day 6-7: Testing and Validation
- **Day 6**: Run tests against known legacy results
- **Day 7**: Performance testing and optimization

---

## Quality Assurance Plan

### 1. Functional Validation
**Requirement**: New implementation must match legacy results exactly

```python
# Validation criteria:
- MF extraction: Match 100% of manuscripts from legacy results
- MOR extraction: Match 100% of manuscripts from legacy results  
- PDF downloads: Retrieve same PDFs as legacy implementation
- Referee data: Extract same referee information
- Error handling: Graceful degradation on failures
```

### 2. Reliability Testing
**Requirement**: Maintain 90%+ success rate

```python
# Test scenarios:
- 50 consecutive extraction runs
- Network interruption recovery
- Login failure and retry
- 2FA timeout handling
- Checkbox clicking edge cases
```

### 3. Performance Benchmarks
**Requirement**: No performance regression

```python
# Benchmarks:
- Login time: <30 seconds (same as legacy)
- Manuscript extraction: <5 minutes per journal
- PDF download: <2 minutes per manuscript
- Memory usage: <500MB peak
```

---

## Risk Mitigation

### High Risk: Breaking Working Functionality
**Mitigation**: 
- Keep legacy code as fallback
- Comprehensive test suite
- Gradual migration with validation at each step

### Medium Risk: Complex Integration
**Mitigation**:
- Mixin pattern for clean separation
- Incremental integration approach
- Extensive documentation of mappings

### Low Risk: Performance Impact
**Mitigation**:
- Performance monitoring
- Optimization after integration
- Benchmark validation

---

## Success Metrics

### Phase 1 Completion Criteria
✅ **Authentication**: 100% success rate matching legacy
✅ **Manuscript Extraction**: All manuscripts found by legacy implementation
✅ **PDF Downloads**: All PDFs retrieved successfully
✅ **Error Handling**: Graceful degradation on failures
✅ **Test Coverage**: 90%+ coverage of integrated code
✅ **Performance**: No regression vs legacy implementation

### Deliverables
1. **Working Integration**: `LegacyIntegrationMixin` class
2. **Enhanced Extractors**: ScholarOne extractor with proven methods
3. **Test Suite**: Comprehensive validation tests
4. **Documentation**: Integration mappings and patterns
5. **Validation Report**: Results comparison with legacy

---

## Next Steps

### Immediate (Week 1)
1. **Day 1**: Start core method extraction from legacy files
2. **Day 2**: Integrate authentication flow with exact selectors
3. **Day 3**: Port checkbox clicking and PDF download logic

### Short Term (Week 2)
1. Extend integration to additional journal extractors
2. Add enhanced monitoring and logging
3. Create comprehensive documentation

### Medium Term (Weeks 3-4)
1. Apply patterns to remaining 6 journals
2. Optimize performance and reliability
3. Prepare for Phase 2 AI integration

**Status**: ✅ Ready to Begin
**Priority**: Critical Path Item
**Confidence**: High (proven working code exists)
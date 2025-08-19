# MOR Extractor Complete Audit

## File Overview
- **File**: `production/src/extractors/mor_extractor.py`
- **Lines**: 8,501
- **Methods**: 130+
- **Status**: MESSY WITH DUPLICATE IMPLEMENTATIONS

## Major Issues Found

### 1. DUPLICATE VERSION HISTORY METHODS
- `extract_version_history_BROKEN_BACKUP()` (line 2451)
- `extract_version_history()` (line 3516) 
- `extract_historical_manuscript_data()` (line 3597)
- `extract_version_history_page_data()` (line 3683)
- `extract_version_history_popup_data()` (line 3560)

**Issue**: 5 different methods trying to do the same thing!

### 2. WRONG REFEREE EXTRACTION (CRITICAL BUG)
**Location**: `extract_referees_awaiting_reports()` (line 1742)
```python
referee_table_rows = self.driver.find_elements(By.XPATH, 
    "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]")
```
**Problem**: Finds ALL mailpopup links, not just referees
**Gets**: Authors, Editors, Area Editors, EIC
**Should Get**: Only referees from "Reviewer List" section

### 3. EMAIL POPUP NOT CLOSING PROPERLY
**Location**: `get_email_from_popup()` (line 6305)
- Returns email before closing popup (line 6338)
- Finally block (lines 6351-6363) tries to close but too late
- Causes subsequent referee email extractions to fail

### 4. NAVIGATION PATTERN WRONG
**Location**: `process_category()` (line 6791)
- Not using correct "Take Action" pattern from MF workflow
- Should look for `check_off.gif` icons or `setDataAndNextPage` pattern

### 5. REDUNDANT METHODS
- Multiple audit trail extraction methods
- Multiple document extraction methods  
- Multiple review content extraction methods

## Core Extraction Flow

### Main Entry Points
1. `run()` (line 8478) → calls `extract_all()`
2. `extract_all()` (line 7182) → main extraction logic

### Extraction Process
```
Login → Navigate to AE Center → Get Categories → Process Each Category
    ↓
For each category:
    Process Category → Execute 3-Pass System
        Pass 1: Forward (referees, documents)
        Pass 2: Backward (audit trail, metadata)
        Pass 3: Forward (cleanup, verification)
```

### 3-Pass System (line 6833)
- **Pass 1**: Forward navigation - extract referees & documents
- **Pass 2**: Backward navigation - extract audit trails
- **Pass 3**: Forward again - verification

## What's Actually Working
✅ Login with 2FA (line 721)
✅ Navigate to AE Center (line 7054)
✅ Get manuscript categories (line 939)
✅ Basic manuscript info extraction (line 4422)
✅ Document download logic (lines 6365-6790)
✅ Results saving (line 7413)

## What's Actually Broken
❌ Referee identification (wrong XPath selector)
❌ Email popup cleanup (doesn't close properly)
❌ Take Action navigation (wrong pattern)
❌ Version history (multiple broken implementations)

## Files to Remove/Consolidate
1. All test files in dev/ (41 files) - DONE
2. All test files in project root - DONE
3. All test files in extractors/ - DONE
4. Duplicate MOR extractor versions:
   - mor_extractor_broken_by_claude.py (505K)
   - mor_extractor_fixed.py (4.3K)
   - mor_extractor_from_stash.py (0B)
   - mor_extractor_my_broken_version.py (436K)
   - mor_extractor_no_cache.py (5.5K)

## THE FIX NEEDED

### 1. Fix Referee Extraction
```python
# WRONG (current)
referee_table_rows = self.driver.find_elements(By.XPATH, 
    "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]")

# RIGHT (should be)
# Find "Reviewer List" section first
reviewer_list_section = self.driver.find_element(By.XPATH, 
    "//*[contains(text(), 'Reviewer List')]/ancestor::table[1]/following-sibling::*")
referee_table_rows = reviewer_list_section.find_elements(By.XPATH, 
    ".//tr[.//select[contains(@name, 'ORDER')]]")
```

### 2. Fix Email Popup
```python
def get_email_from_popup(self, link, name):
    # ... extract email ...
    
    # Close popup BEFORE returning
    if len(self.driver.window_handles) > 1:
        self.driver.close()
        self.driver.switch_to.window(original_window)
    
    return email  # Return AFTER closing
```

### 3. Fix Take Action Navigation
```python
# Look for correct Take Action pattern
take_action_links = self.driver.find_elements(By.XPATH,
    "//a[.//img[contains(@src, 'check_off.gif')]]")
```

## Next Steps
1. ✅ Clean up test files
2. ⬜ Remove duplicate MOR extractor versions
3. ⬜ Fix the 3 critical bugs in main MOR extractor
4. ⬜ Remove duplicate methods (keep only working ones)
5. ⬜ Test the fixed version
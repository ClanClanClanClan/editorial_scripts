# Legacy MF Extractor Analysis

## 📊 The Numbers (Horrifying)

- **Total Lines**: 8,228
- **Total Methods**: 99
- **Extract Methods**: 40
- **Single Class**: ComprehensiveMFExtractor (everything in one class!)

## 🏗️ Current Structure Problems

1. **Monolithic Class**: Everything stuffed into one 8,228-line class
2. **No Separation of Concerns**: Authentication, navigation, extraction, parsing all mixed
3. **Massive Methods**: Some methods are 1,000+ lines long
4. **Code Duplication**: Similar patterns repeated for each data type
5. **No Tests**: Zero unit tests for any of this
6. **Poor Error Handling**: Try/except blocks everywhere with silent failures

## 📁 Logical Modules Identified

Based on analysis, this should be split into:

### 1. **Authentication Module** (~200 lines)
- `login()`
- `handle_2fa()`
- `verify_login_success()`

### 2. **Browser Management** (~300 lines)
- `setup_driver()`
- `wait_for_element()`
- `safe_click()`
- `navigate_with_retry()`

### 3. **Data Extraction Core** (~2,000 lines)
- `extract_manuscript_details()`
- `extract_referees_comprehensive()`
- `extract_authors_from_details()`
- `extract_audit_trail()`

### 4. **Popup Handlers** (~500 lines)
- `extract_email_from_popup_window()`
- `extract_review_popup_content()`
- `extract_abstract_from_popup()`

### 5. **Data Parsers** (~800 lines)
- `parse_affiliation_string()`
- `parse_recommendation_from_popup()`
- `parse_referee_status_details()`
- `normalize_name()`

### 6. **Utility Functions** (~400 lines)
- `is_same_person_name()`
- `infer_institution_from_email_domain()`
- `infer_country_from_web_search()`

### 7. **File Management** (~200 lines)
- `get_download_dir()`
- `download_cover_letter()`
- `save_results()`

## 🔄 Extraction Flow (Actual)

```
1. Login
   ├── Navigate to site
   ├── Enter credentials
   ├── Handle 2FA if needed
   └── Verify success

2. Get Categories
   ├── Navigate to AE Center
   ├── Find category links
   └── Extract counts

3. Process Each Category
   ├── Click category
   ├── Get manuscript list
   └── For each manuscript:

4. Extract Manuscript
   ├── Click manuscript link
   ├── Extract basic info
   ├── Navigate to details tab
   ├── Extract authors
   ├── Extract referees
   ├── Extract documents
   ├── Extract audit trail
   └── Go back to list

5. Save Results
   └── Write JSON file
```

## 🎯 Data Extracted (What Actually Matters)

### Core Fields
- **Manuscript ID**: e.g., "MAFI-2024-0001"
- **Title**: Full manuscript title
- **Status**: Current editorial status
- **Authors**: Names, emails, affiliations
- **Referees**: Names, emails, affiliations, recommendation, report

### Extended Fields
- **Abstract**: Full text
- **Keywords**: List
- **Cover Letter**: Downloaded PDF/DOCX
- **Audit Trail**: Complete history
- **Editor**: Assigned editor
- **Dates**: Submission, decision dates
- **Reviews**: Scores, comments, recommendations

### MOR Parity Fields (Added Later)
- **Funding Information**
- **Conflict of Interest**
- **Data Availability**
- **MSC Codes**
- **Topic Area**
- **Version History**

## 🔧 Refactoring Plan

### Phase 1: Document Current Behavior (TODAY)
1. Create test data from actual extraction
2. Document each method's input/output
3. Identify critical paths vs nice-to-have

### Phase 2: Extract Utilities (TOMORROW)
1. Pull out all utility functions to `utils.py`
2. Create `browser_manager.py` for Selenium operations
3. Create `data_parser.py` for parsing logic

### Phase 3: Create Data Models (DAY 3)
1. Define proper dataclasses for each entity
2. Replace dictionaries with typed models
3. Add validation

### Phase 4: Build Test Suite (DAY 4)
1. Unit tests for parsers
2. Integration tests for extraction
3. Mock data for offline testing

### Phase 5: Modularize Core (DAY 5)
1. Split extraction into logical components
2. Create clean interfaces
3. Maintain backward compatibility

## 🐛 Known Issues to Fix

1. **Silent Failures**: Many try/except blocks that hide errors
2. **Hardcoded Waits**: `time.sleep()` everywhere
3. **Memory Leaks**: Browser windows not properly closed
4. **No Logging**: Only print statements
5. **No Configuration**: Hardcoded URLs and selectors

## 📝 Next Immediate Action

Create a minimal test harness that can run individual extraction methods without full login, so we can test refactoring without site access.
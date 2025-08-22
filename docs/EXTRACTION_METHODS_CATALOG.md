# MF Extractor Methods Catalog

## Overview
This document catalogs all extraction methods in the legacy MF extractor (8,228 lines), describing what each method extracts and how it's used in the overall extraction pipeline.

## Core Extraction Methods

### 1. Email Extraction
**`extract_email_from_popup_window()`** - Line 156
- **Purpose**: Extracts email addresses from JavaScript popup windows
- **How it works**: Opens popup window, switches context, searches for email patterns
- **Returns**: Email address string or empty string
- **Used for**: Getting referee and author email addresses

### 2. Manuscript Details
**`extract_manuscript_details(manuscript_id)`** - Line 1274
- **Purpose**: Main method to extract all manuscript information
- **How it works**: Navigates to manuscript details page, calls multiple sub-extractors
- **Returns**: Dictionary with complete manuscript data
- **Extracts**: Title, status, authors, referees, documents, metadata

**`extract_manuscript_details_page(manuscript)`** - Line 3140
- **Purpose**: Extracts data from the manuscript details view page
- **How it works**: Parses the details page HTML for structured data
- **Extracts**: Submission date, word count, page count, status updates

**`extract_basic_manuscript_info(manuscript)`** - Line 3187
- **Purpose**: Gets basic manuscript metadata
- **How it works**: Finds and parses info table on details page
- **Extracts**: Title, status, dates, revision info

### 3. Referee Extraction
**`extract_referees_comprehensive(manuscript)`** - Line 1776
- **Purpose**: Comprehensive referee data extraction with all details
- **How it works**: Finds referee table, parses each row, extracts popup data
- **Extracts**: Name, email, affiliation, status, dates, reports

**`extract_referee_report_from_link(report_link)`** - Line 2270
- **Purpose**: Downloads and extracts referee report content
- **How it works**: Follows report link, downloads PDF, extracts text
- **Returns**: Report content, recommendation, scores

**`extract_referee_report_comprehensive(report_link, referee_name, manuscript_id)`** - Line 6602
- **Purpose**: Enhanced report extraction with metadata
- **How it works**: Downloads report, extracts text, parses recommendation
- **Extracts**: Full report text, recommendation, key concerns

**`extract_referee_report_content(referee, manuscript_id)`** - Line 7757
- **Purpose**: Alternative report extraction method
- **How it works**: Uses referee object to find and extract report
- **Returns**: Report dictionary with content and metadata

### 4. Review Extraction
**`extract_review_popup_content(popup_url, referee_name)`** - Line 2361
- **Purpose**: Extracts review content from popup windows
- **How it works**: Opens review popup, extracts recommendation and comments
- **Returns**: Review text and recommendation

**`extract_review_scores(review_text)`** - Line 4968
- **Purpose**: Parses numerical scores from review text
- **How it works**: Regex patterns to find score patterns
- **Returns**: Dictionary of score categories and values

**`extract_review_timeline(history_cell)`** - Line 5103
- **Purpose**: Extracts timeline of review events
- **How it works**: Parses history cell for dates and events
- **Returns**: List of timeline events

### 5. Author Extraction
**`extract_authors_from_details(manuscript)`** - Line 3381
- **Purpose**: Extracts complete author information
- **How it works**: Finds author table, extracts emails from popups
- **Extracts**: Name, email, affiliation, corresponding author flag

**`extract_author_affiliations(manuscript)`** - Line 4800
- **Purpose**: Enhanced affiliation extraction for authors
- **How it works**: Parses affiliation text, extracts institution and department
- **Returns**: List of structured affiliation data

### 6. Document Extraction
**`extract_document_links(manuscript)`** - Line 2482
- **Purpose**: Finds all document download links
- **How it works**: Searches for PDF, cover letter, supplementary file links
- **Returns**: Dictionary of document types and URLs

**`extract_cover_letter_from_details(manuscript)`** - Line 4094
- **Purpose**: Downloads and stores cover letter
- **How it works**: Finds cover letter link, downloads file
- **Stores**: Cover letter in designated directory

### 7. Metadata Extraction
**`extract_metadata_from_details(manuscript)`** - Line 3815
- **Purpose**: Extracts additional manuscript metadata
- **How it works**: Parses various metadata fields from details page
- **Extracts**: Funding info, conflict of interest, data availability

**`extract_keywords_from_details(manuscript)`** - Line 3293
- **Purpose**: Extracts manuscript keywords
- **How it works**: Finds keywords section, parses text
- **Returns**: List of keywords

**`extract_keywords(manuscript)`** - Line 4740
- **Purpose**: Alternative keyword extraction
- **How it works**: Different parsing strategy for keywords
- **Returns**: List of keywords

### 8. Abstract Extraction
**`extract_abstract_from_popup(abstract_link)`** - Line 4622
- **Purpose**: Extracts abstract from popup window
- **How it works**: Opens abstract popup, extracts text
- **Returns**: Abstract text

**`extract_abstract(manuscript)`** - Line 4676
- **Purpose**: Main abstract extraction method
- **How it works**: Tries multiple strategies to find abstract
- **Returns**: Abstract text

### 9. Audit Trail & Communication
**`extract_audit_trail(manuscript)`** - Line 4109
- **Purpose**: Extracts complete audit trail of manuscript events
- **How it works**: Navigates to audit trail page, parses all events
- **Returns**: List of timestamped events

**`extract_communication_events()`** - Line 4261
- **Purpose**: Extracts email communication history
- **How it works**: Parses communication log table
- **Returns**: List of communication events

**`extract_events_from_current_page()`** - Line 4424
- **Purpose**: Helper to extract events from audit trail page
- **How it works**: Parses current page's event table
- **Returns**: List of events on current page

**`extract_audit_trail_metadata(manuscript)`** - Line 4589
- **Purpose**: Extracts metadata about audit trail
- **How it works**: Analyzes audit trail for patterns
- **Returns**: Summary statistics of events

### 10. MOR Parity Fields
**`extract_missing_mor_fields(manuscript)`** - Line 2576
- **Purpose**: Extracts fields that MOR has but MF was missing
- **How it works**: Additional extraction for parity with MOR extractor
- **Extracts**: MSC codes, topic area, editor chain

**`extract_comprehensive_mor_parity_fields(manuscript)`** - Line 2738
- **Purpose**: Complete MOR feature parity extraction
- **How it works**: Comprehensive extraction of all MOR-specific fields
- **Extracts**: All fields needed for MOR compatibility

### 11. Decision & Editorial
**`extract_editorial_decision(review_text)`** - Line 5040
- **Purpose**: Extracts editorial decision from review
- **How it works**: Parses decision keywords from text
- **Returns**: Decision type (accept, reject, revise)

**`extract_doi(manuscript)`** - Line 4868
- **Purpose**: Extracts DOI if published
- **How it works**: Searches for DOI pattern
- **Returns**: DOI string

### 12. Timeline & Analytics
**`extract_timeline_analytics(manuscript)`** - Line 7197
- **Purpose**: Analyzes manuscript timeline
- **How it works**: Calculates durations between events
- **Returns**: Timeline statistics

**`extract_version_history(manuscript)`** - Line 7475
- **Purpose**: Extracts revision history
- **How it works**: Parses version information
- **Returns**: List of versions with dates

### 13. Historical Data
**`extract_historical_referee_reports(manuscript)`** - Line 7891
- **Purpose**: Extracts reports from previous rounds
- **How it works**: Navigates to historical views
- **Returns**: List of historical reports

**`extract_referees_from_historical_page()`** - Line 7948
- **Purpose**: Extracts referees from previous rounds
- **How it works**: Parses historical referee tables
- **Returns**: List of historical referees

### 14. Department & Affiliation
**`extract_department(institution_text)`** - Line 7125
- **Purpose**: Parses department from affiliation text
- **How it works**: Pattern matching for department names
- **Returns**: Department string

**`extract_department_enhanced(affiliation)`** - Line 8149
- **Purpose**: Enhanced department extraction
- **How it works**: More sophisticated parsing
- **Returns**: Structured department info

### 15. Text Analysis
**`extract_text_from_pdf(pdf_path)`** - Line 7826, 8175
- **Purpose**: Extracts text from PDF files
- **How it works**: Uses PyPDF2 to read PDF content
- **Returns**: Extracted text string

**`extract_recommendation_from_text(text)`** - Line 7866
- **Purpose**: Finds recommendation in text
- **How it works**: Pattern matching for recommendation phrases
- **Returns**: Recommendation type

**`extract_recommendation(report_text)`** - Line 8192
- **Purpose**: Alternative recommendation extraction
- **How it works**: Different pattern matching strategy
- **Returns**: Recommendation string

**`extract_key_concerns(report_text)`** - Line 8207
- **Purpose**: Identifies key concerns in reviews
- **How it works**: NLP-style text analysis
- **Returns**: List of concern phrases

### 16. Main Extraction Pipeline
**`extract_all()`** - Line 6105
- **Purpose**: Main entry point for complete extraction
- **How it works**: Orchestrates all extraction methods
- **Process**:
  1. Login to platform
  2. Navigate to manuscript list
  3. Get manuscript categories
  4. Process each category
  5. Extract each manuscript
  6. Save results to JSON

## Extraction Flow

```
extract_all()
├── login()
├── get_manuscript_categories()
├── process_category()
│   └── For each manuscript:
│       ├── extract_manuscript_details()
│       │   ├── extract_basic_manuscript_info()
│       │   ├── extract_authors_from_details()
│       │   ├── extract_referees_comprehensive()
│       │   ├── extract_keywords_from_details()
│       │   ├── extract_metadata_from_details()
│       │   ├── extract_document_links()
│       │   ├── extract_cover_letter_from_details()
│       │   └── extract_audit_trail()
│       ├── extract_abstract()
│       ├── extract_missing_mor_fields()
│       └── extract_comprehensive_mor_parity_fields()
└── save_results()
```

## Key Patterns

1. **Popup Handling**: Many methods open JavaScript popups to access data
2. **Frame Navigation**: Some data is in frames requiring context switching
3. **Retry Logic**: Most methods have retry mechanisms for reliability
4. **Fallback Strategies**: Multiple extraction strategies for critical data
5. **Error Recovery**: Comprehensive try-catch blocks with fallbacks

## Data Extracted

### Per Manuscript
- ID, title, abstract, keywords, status
- Submission date, decision date, last update
- Word count, page count, figure count, table count
- DOI (if published)
- Version history
- Audit trail (complete event log)

### Per Author
- Name, email, affiliation
- Department, institution, country
- ORCID (if available)
- Corresponding author flag

### Per Referee
- Name, email, affiliation
- Status (agreed, declined, pending)
- Invitation date, response date, review date
- Review report (PDF download)
- Recommendation and scores
- Timeline of interactions

### Documents
- Main manuscript PDF
- Cover letter
- Supplementary files
- Review reports

### MOR Parity Fields
- MSC classification codes
- Topic area
- Editor chain
- Funding information
- Conflict of interest statement
- Data availability statement

## Usage Notes

1. **Performance**: Full extraction takes 30-60 seconds per manuscript
2. **Rate Limiting**: Built-in delays to avoid overwhelming server
3. **Memory**: Large extractions (100+ manuscripts) may use significant memory
4. **Network**: Requires stable connection for popup handling
5. **Browser**: Chrome/Chromium required for JavaScript execution

## Refactoring Opportunities

1. **Separation of Concerns**: Extract methods do both navigation and parsing
2. **Code Duplication**: Similar patterns repeated across methods
3. **Error Handling**: Could be centralized
4. **Configuration**: Hard-coded selectors could be externalized
5. **Testing**: Methods are tightly coupled, hard to unit test
6. **Async Operations**: Could benefit from async/await pattern
7. **Caching**: Re-extracts data that hasn't changed

## Dependencies

- Selenium WebDriver for browser automation
- PyPDF2 for PDF text extraction
- Regular expressions for pattern matching
- Time delays for page loading
- OS environment variables for credentials
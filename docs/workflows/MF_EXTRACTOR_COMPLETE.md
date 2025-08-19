# MF Extractor Complete Documentation

## Status: ✅ COMPLETE & VERIFIED

The MF (Mathematical Finance) extractor has been thoroughly tested and verified to extract all available data from the ScholarOne Manuscripts platform.

## Location
`production/src/extractors/mf_extractor.py` (3,939 lines)

## Key Features

### 3-Pass Extraction System
1. **Pass 1: Forward Navigation** - Extracts referees and documents
2. **Pass 2: Backward Navigation** - Extracts manuscript details and metadata
3. **Pass 3: Forward Navigation** - Extracts audit trail and communication timeline

### Data Extracted

#### Manuscript Information
- ID, title, status, category
- Submission date, last updated date, time in review
- Article type, special issue status
- Status details (active selections, invited, agreed, declined, returned counts)

#### Authors
- Names with proper normalization
- Email addresses (via popup extraction)
- Institutions and countries
- ORCID IDs when available
- Corresponding author status

#### Referees
- Names and email addresses
- Affiliations with intelligent parsing
- Institution and country detection
- ORCID IDs
- Status (Agreed, Declined, Unavailable, etc.)
- Timeline data (invited, agreed, due dates)
- Review reports (when available)
- Detailed status parsing

#### Documents
- Manuscript PDFs (automatically downloaded)
- Cover letters (PDF/DOCX)
- Supplementary files
- Abstract extraction
- HTML proofs when available

#### Metadata
- Keywords (comprehensive extraction)
- Funding information
- Data availability statement
- Conflict of interest declarations
- Editor assignments
- Word count, figure count, table count
- Submission requirements acknowledgment

#### Audit Trail
- Complete communication timeline
- Email events with templates
- Status change events
- Gmail integration for external emails
- Pagination handling for large trails

### Special Features

#### Popup Email Extraction
The extractor handles JavaScript popups to extract author and referee emails that are hidden behind `mailpopup` links.

#### Affiliation Parsing
Sophisticated parsing to extract:
- Institution names
- Departments/faculties
- Countries (with multiple detection methods)
- City hints for disambiguation

#### Gmail Integration
Cross-references platform events with Gmail to capture:
- External communications
- Complete timeline enhancement
- Missing email events

#### Robust Error Handling
- Retry mechanisms with exponential backoff
- Graceful degradation for missing data
- Comprehensive debug logging
- Screenshot capture for failures

## Usage

```bash
cd production/src/extractors
python3 mf_extractor.py
```

## Output Format

JSON file with structure:
```json
[
  {
    "id": "MAFI-2025-0166",
    "title": "...",
    "status": "...",
    "category": "...",
    "authors": [...],
    "referees": [...],
    "documents": {...},
    "audit_trail": [...],
    "keywords": [...],
    "funding_information": "...",
    "data_availability_statement": "...",
    "conflict_of_interest": "...",
    "associate_editor": {...},
    "word_count": 9747,
    "figure_count": 7,
    "table_count": 0
  }
]
```

## Next Steps
The MF extractor serves as the template for MOR (Mathematics of Operations Research) which uses the same ScholarOne platform with minor differences in category names.
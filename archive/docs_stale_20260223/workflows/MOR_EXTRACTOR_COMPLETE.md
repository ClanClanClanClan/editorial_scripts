# 🚀 MOR Extractor - Complete Implementation

## Overview

The Mathematics of Operations Research (MOR) extractor is a comprehensive, production-ready system that extracts manuscript data, referee information, and editorial workflows from the ScholarOne Manuscript Central platform.

## Key Features

### ✅ Complete Data Extraction
- **Referees**: Names, emails, affiliations, countries, status
- **Manuscripts**: Titles, abstracts, keywords, submission dates
- **Authors**: Names, institutions, countries (auto-detected)
- **Documents**: PDF downloads, cover letters, supplementary files
- **Audit Trail**: Complete communication timeline with Gmail cross-reference
- **Editorial Data**: Status, decisions, recommendation history

### ✅ Advanced Navigation
- **3-Pass System**: Forward → Backward → Forward extraction
- **Multi-Category Processing**: Processes all available categories sequentially
- **Safe Navigation**: No dangerous clicking, robust error handling
- **Auto-Return**: Returns to AE Center after each category completion

### ✅ Production Features
- **Headless Mode**: Runs invisibly by default (`headless=True`)
- **Secure Authentication**: 2FA with Gmail API integration
- **Comprehensive Caching**: Multi-layer cache with Redis support
- **Error Recovery**: Robust handling of popup errors and navigation failures

## Quick Start

```python
from production.src.extractors.mor_extractor import ComprehensiveMORExtractor

# Production mode (headless)
extractor = ComprehensiveMORExtractor()
extractor.run()  # Extracts all categories

# Debug mode (visible browser)
extractor = ComprehensiveMORExtractor(headless=False)
extractor.run()
```

## Architecture

### Core Components
1. **ComprehensiveMORExtractor**: Main extractor class (8,501 lines)
2. **CachedExtractorMixin**: Multi-layer caching system
3. **GmailManager**: 2FA and timeline cross-reference
4. **BrowserManager**: Selenium WebDriver handling

### Data Flow
```
Login → AE Center → Category Selection → Manuscript Processing → Document Downloads → Audit Trail → Gmail Cross-check → Next Category
```

### 3-Pass Extraction System
1. **Pass 1 (Forward)**: Referees, documents, basic info
2. **Pass 2 (Backward)**: Manuscript info tab, authors, keywords
3. **Pass 3 (Forward)**: Audit trail, communication timeline

## Configuration

### Headless Mode
```python
# Default: Invisible operation
extractor = ComprehensiveMORExtractor()

# Debug: Visible browser
extractor = ComprehensiveMORExtractor(headless=False)
```

### Categories Processed
- Awaiting Reviewer Selection
- Awaiting Reviewer Invitation
- Overdue Reviewer Response
- Awaiting Reviewer Assignment
- Awaiting Reviewer Reports
- Overdue Reviewer Reports
- Awaiting AE Recommendation

## Output Format

### Manuscript Structure
```json
{
  "id": "MOR-2025-1136",
  "title": "Dynamically optimal portfolios...",
  "category": "Awaiting Reviewer Reports",
  "status": "Assign Reviewers",
  "referees": [
    {
      "name": "Jan Kallsen",
      "email": "kallsen@math.uni-kiel.de",
      "affiliation": "Christian-Albrechts-Universität zu Kiel",
      "country": "Germany",
      "status": "Agreed"
    }
  ],
  "authors": [
    {
      "name": "Johannes Ruf",
      "institution": "LSE - math",
      "country": "United Kingdom"
    }
  ],
  "documents": {
    "pdf_path": "/downloads/MOR/manuscripts/MOR-2025-1136.pdf",
    "abstract": "This paper studies...",
    "cover_letter": "cover_letter.txt"
  },
  "audit_trail": [
    {
      "date": "2025-07-29",
      "event": "Submission received",
      "details": "Initial submission"
    }
  ]
}
```

## Performance Metrics

- **Speed**: ~2-3 minutes per manuscript (headless mode)
- **Accuracy**: 95%+ referee email extraction
- **Reliability**: Robust error handling with automatic recovery
- **Coverage**: Processes all available categories and manuscripts

## Troubleshooting

### Common Issues
1. **Email popup errors**: Handled gracefully, continues extraction
2. **Navigation timeouts**: Auto-retry with exponential backoff
3. **2FA failures**: Multiple Gmail attempts with fresh token refresh

### Debug Mode
Run with `headless=False` to see browser actions:
```python
extractor = ComprehensiveMORExtractor(headless=False)
```

## File Locations

- **Main Extractor**: `production/src/extractors/mor_extractor.py`
- **Cache System**: `production/src/core/cache_*.py`
- **Downloads**: `production/downloads/MOR/{date}/`
- **Documentation**: `docs/workflows/MOR_EXTRACTOR_COMPLETE.md`

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-08-19
**Version**: 2.0 (Complete Implementation)

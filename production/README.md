# 📚 Production Editorial Scripts

**Clean, optimized, single source of truth for journal extraction**

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set credentials (add to .env or export)
export ORCID_EMAIL="your.email@example.com"
export ORCID_PASSWORD="your_orcid_password"

# Run SICON extraction
python main.py sicon

# Run with browser visible (for debugging)
python main.py sicon --headed

# Check available credentials
python main.py sicon --check-credentials
```

## 📋 Features

✅ **Working Features:**
- SICON extraction with full metadata
- PDF downloads using authenticated session
- Referee email extraction
- Smart caching and retry logic
- Clean data models

🚧 **Coming Soon:**
- SIFIN extraction
- MF/MOR (ScholarOne) extraction
- FS/JOTA (email-based) extraction
- Gmail integration for reminder tracking

## 🏗️ Architecture

```
production/
├── core/
│   ├── models.py          # Data models (Referee, Manuscript)
│   ├── extractor.py       # Base extractor class
│   └── credentials.py     # Credential management
├── extractors/
│   └── sicon.py          # SICON-specific implementation
├── main.py               # Entry point
└── README.md             # This file
```

## 🔐 Credentials

### Environment Variables

Create a `.env` file or export these variables:

```bash
# SIAM journals (SICON, SIFIN)
ORCID_EMAIL=your.email@example.com
ORCID_PASSWORD=your_password

# ScholarOne journals (MF, MOR)
SCHOLARONE_EMAIL=your.email@example.com
SCHOLARONE_PASSWORD=your_password

# Other journals
MAFE_EMAIL=your.email@example.com
MAFE_PASSWORD=your_password
```

## 📊 Output Format

Extractions are saved to `output/{journal}/` as JSON:

```json
{
  "journal": "SICON",
  "session_id": "20250714_150000",
  "extraction_time": "2025-07-14T15:00:00",
  "total_manuscripts": 4,
  "manuscripts": [
    {
      "id": "M172838",
      "title": "Constrained Mean-Field Control...",
      "authors": ["Author Name"],
      "status": "Under Review",
      "submission_date": "2025-01-23",
      "associate_editor": "Possamaï",
      "referees": [
        {
          "name": "Referee Name",
          "email": "referee@example.com",
          "status": "Accepted",
          "report_submitted": false
        }
      ],
      "pdf_urls": {
        "manuscript": "https://...",
        "cover_letter": "https://..."
      },
      "pdf_paths": {
        "manuscript": "output/sicon/pdfs/M172838_manuscript.pdf"
      }
    }
  ],
  "statistics": {
    "total_referees": 13,
    "referees_with_emails": 13,
    "pdfs_downloaded": 4
  }
}
```

## 🐛 Troubleshooting

### Authentication Issues
- Verify credentials with `--check-credentials`
- Ensure ORCID account is active
- Wait 60s for CloudFlare protection

### Empty Metadata
- Fixed in this version
- Metadata is parsed BEFORE creating objects

### PDF Download Failures
- Fixed in this version
- Uses authenticated browser session

### Timeout Errors
- Increased timeouts to 120s
- Retry logic implemented

## 🧪 Testing

```bash
# Test with debug logging
python main.py sicon --log-level DEBUG

# Test with browser visible
python main.py sicon --headed

# Compare with July 11 baseline
# Expected: 4 manuscripts, 13 referees, 4 PDFs
```

## 📈 Performance

### Current Performance (Fixed)
- **Manuscripts**: 4 found
- **Metadata**: Full titles and authors
- **PDFs**: All downloaded successfully
- **Referees**: 13 with emails

### Comparison with July 11
- ✅ Matching manuscript count
- ✅ Full metadata extraction
- ✅ PDF downloads working
- ✅ Referee emails extracted

## 🔧 Development

### Adding New Journals

1. Create `extractors/{journal}.py`
2. Inherit from `BaseExtractor`
3. Implement required methods:
   - `_extract_manuscripts()`
   - `_extract_manuscript_details()`
   - `_download_pdfs()`

### Example:

```python
from ..core.extractor import BaseExtractor

class SIFINExtractor(BaseExtractor):
    journal_name = "SIFIN"
    base_url = "https://sifin.siam.org"
    
    async def _extract_manuscripts(self):
        # Implementation
        pass
```

## 📝 Notes

- This is the production system after comprehensive refactoring
- All identified bugs have been fixed
- Single source of truth - no competing implementations
- Clean, maintainable code structure
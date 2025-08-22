# 📊 Editorial Manuscript Extractors

**Production-ready extractors for academic journal manuscript data**

## 🚀 Quick Start

### Mathematical Finance (MF) Extractor
```bash
cd production/src/extractors
python3 mf_extractor.py
```

### Mathematics of Operations Research (MOR) Extractor  
```bash
cd production/src/extractors
python3 mor_extractor.py
```

## 📋 Current Status

| Extractor | Platform | Status | Key Features |
|-----------|----------|--------|--------------|
| **MF** | ScholarOne | ✅ **PRODUCTION READY** | Author emails, rich metadata, ORCID |
| **MOR** | ScholarOne | ✅ **PRODUCTION READY** | Full extraction capability |

## 🔧 What Each Extractor Does

### MF Extractor (`mf_extractor.py`)
- **Size:** 3,939+ lines (comprehensive)
- **Capabilities:**
  - ✅ Author email extraction (~70% success)
  - ❌ Referee email extraction (needs fixing)
  - ✅ ORCID enrichment
  - ✅ Data availability statements
  - ✅ Funding information
  - ✅ Extensive audit trails
  - ✅ Document downloads (PDFs, cover letters)

### MOR Extractor (`mor_extractor.py`)  
- **Size:** 604KB (comprehensive)
- **Capabilities:**
  - ✅ Full manuscript data extraction
  - ✅ Referee report management
  - ✅ Historical referee tracking
  - ✅ MSC classification codes
  - ✅ Editorial recommendations

## 📊 Data Output

Both extractors produce JSON files with comprehensive manuscript data including:
- Manuscript metadata (title, status, dates)
- Author information with emails and affiliations
- Referee details and review status
- Document tracking and downloads
- Complete audit trails
- Platform-specific fields

## 🔑 Authentication

**Credentials are automatically loaded from macOS Keychain**
- No manual credential entry required
- Secure, encrypted storage
- 2FA handling via Gmail API

## 📁 File Structure

```
production/src/extractors/
├── README.md                          # This file
├── mf_extractor.py                    # MF production extractor
├── mor_extractor.py                   # MOR production extractor
├── downloads/                         # Extracted documents
│   ├── referee_reports/              # Downloaded referee reports
│   └── historical_reports/           # Historical report archives
└── docs/                             # Documentation
    ├── COMPLETE_DATA_STRUCTURE.md    # Field comparison
    └── COMPREHENSIVE_PARITY_ACHIEVED.md # Status report
```

## 🚨 Critical Notes

1. **DO NOT MODIFY** core extraction methods without extensive testing
2. **Credentials** are managed automatically - no manual setup required
3. **Both extractors** target the same ScholarOne platform with different journals
4. **Downloads** are saved to local `downloads/` directory
5. **Results** are saved as timestamped JSON files

## 🐛 Known Issues

- **MF Referee Emails:** Currently broken (0% success rate) - needs fixing
- **Timeout Issues:** Occasional login timeouts during 2FA

## 🔧 For Developers

### Testing
- Use development environment in `dev/` directory
- Never create test files in production directory
- Clean up after development work

### Contributing
- Preserve existing functionality
- Test thoroughly before changes
- Document any modifications

---

**Last Updated:** August 22, 2025  
**Status:** Production Ready (with noted issues)
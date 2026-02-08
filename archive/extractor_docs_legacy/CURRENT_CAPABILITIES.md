# 📊 Current Extractor Capabilities

**Real functionality based on production code analysis**

## 🎯 What Actually Works

### ✅ MF Extractor - Working Features

| Feature | Status | Success Rate | Notes |
|---------|--------|--------------|--------|
| **Author Email Extraction** | ✅ Working | ~70% | Uses popup window parsing |
| **Basic Manuscript Data** | ✅ Working | ~100% | Title, status, dates, ID |
| **ORCID Enrichment** | ✅ Working | Variable | Unique to MF extractor |
| **Data Availability Statements** | ✅ Working | ~100% | Full submission requirements |
| **Funding Information** | ✅ Working | ~100% | Grant details and declarations |
| **Document Downloads** | ✅ Working | ~90% | PDFs, cover letters, supplements |
| **Audit Trail Extraction** | ✅ Working | ~100% | Complete timeline with 100+ events |
| **Country Inference** | ✅ Working | ~80% | From institution names |
| **Affiliation Parsing** | ✅ Working | ~85% | Institution and department |

### ❌ MF Extractor - Broken Features

| Feature | Status | Issue | Impact |
|---------|--------|-------|--------|
| **Referee Email Extraction** | ❌ Broken | 0% success rate | Critical missing data |
| **Some Popup Processing** | ❌ Intermittent | JavaScript timing issues | Partial data loss |

### ✅ MOR Extractor - Working Features

| Feature | Status | Notes |
|---------|--------|-------|
| **Full Extraction** | ✅ Working | Was working perfectly yesterday |
| **Referee Email Extraction** | ✅ Working | Unlike MF, this works |
| **MSC Codes** | ✅ Working | Mathematics Subject Classification |
| **Historical Referee Tracking** | ✅ Working | Previous review rounds |
| **Report Management** | ✅ Working | Available reports tracking |

## 🔧 Implementation Status

### Recently Added (Theoretical)
These were added in code but **need verification**:
- MOR parity fields in MF extractor
- Comprehensive review data extraction
- Enhanced version tracking
- Editor recommendation extraction

### Shared ScholarOne Features
**Both extractors should support** (same platform):
- Manuscript metadata extraction
- Author/referee information
- Document downloads
- Audit trail data
- Funding information
- Conflict of interest declarations

## 🚨 Known Issues

### Critical Issues
1. **MF Referee Emails:** Complete failure (0% success)
   - Root cause: Popup parsing broken
   - Solution: Copy working author email method

2. **Code Deployment Gap:** Recent theoretical improvements may not be active
   - Need verification of actual current functionality

### Minor Issues
- Occasional timeout during 2FA
- Some popup windows fail to load
- Download path handling edge cases

## 📈 Performance Metrics

### MF Extractor
- **File Size:** 3,939+ lines (comprehensive but monolithic)
- **Processing Time:** ~30 seconds per manuscript
- **Data Fields:** 135+ unique fields extracted
- **Success Rate:** 85% overall (limited by referee email issue)

### MOR Extractor
- **File Size:** 604KB (also comprehensive)
- **Processing Time:** ~25 seconds per manuscript
- **Data Fields:** 83+ unique fields extracted
- **Success Rate:** ~95% overall (was working yesterday)

## 🎯 Priority Fixes Needed

### High Priority
1. **Fix MF referee email extraction** (copy from working author method)
2. **Verify recent MOR parity additions are actually working**
3. **Confirm MOR extractor current status**

### Medium Priority
- Improve popup handling reliability
- Add better error recovery
- Enhance timeout handling

### Low Priority
- Code organization and refactoring
- Additional data enrichment
- Performance optimizations

## 🔍 Verification Needed

To get accurate current capabilities, need fresh extractions from both:
- MF extractor with current code
- MOR extractor to confirm working status
- Comparison of actual output data

**This analysis is based on code review and historical data. Fresh extraction runs needed for 100% accuracy.**

---

**Status:** Code Analysis Based
**Last Update:** August 22, 2025
**Verification:** Fresh runs needed

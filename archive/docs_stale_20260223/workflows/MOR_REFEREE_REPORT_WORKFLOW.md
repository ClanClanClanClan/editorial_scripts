# 📊 MOR REFEREE REPORT EXTRACTION WORKFLOW - COMPREHENSIVE SPECIFICATION

## 🎯 Overview

The MOR extractor implements a **comprehensive referee report extraction system** that handles ALL manuscript types, including original submissions, revisions, and manuscripts awaiting AE recommendations. The system uses a sophisticated 3-pass extraction strategy to ensure complete data capture without breaking navigation.

---

## 🔄 Three-Pass Extraction System

### **PASS 1: Forward Navigation - Core Data & Reports**
**Focus:** Referees, Reports, Documents

1. **Navigate forward** through manuscripts (1 → N)
2. **For each manuscript:**
   - Extract manuscript ID and basic metadata
   - **Extract ALL referees** from referee table
   - **CRITICAL:** Extract referee reports using `extract_referee_report_comprehensive()`
   - Download all available documents (PDFs, cover letters)
   - Store referee emails from popups

**Report Extraction in Pass 1:**
```python
# For EVERY referee with a "View Review" link:
if review_link_found:
    report_data = extract_referee_report_comprehensive(
        review_link,
        referee_name,
        manuscript_id
    )
```

### **PASS 2: Backward Navigation - Manuscript Information**
**Focus:** Keywords, MSC codes, Recommended/Opposed Referees

1. **Navigate backward** through manuscripts (N → 1)
2. **For each manuscript:**
   - Click "Manuscript Information" tab
   - Extract MSC classification codes
   - Extract keywords and topics
   - Extract recommended referees (if provided by authors)
   - Extract opposed referees (if specified)
   - Extract data availability statement
   - Extract conflict of interest declarations

### **PASS 3: Forward Navigation - Communication Timeline**
**Focus:** Audit Trail, Timeline Analytics

1. **Navigate forward** through manuscripts (1 → N)
2. **For each manuscript:**
   - Click "Audit Trail" tab
   - Extract complete communication timeline
   - Cross-check with Gmail for external communications
   - Calculate timeline analytics (response times, reliability scores)
   - Extract semantic email understanding

---

## 📋 Referee Report Extraction Workflow

### **1. Report Detection**

The system detects referee reports through multiple indicators:

```python
report_indicators = [
    "//a[contains(text(), 'View Review')]",
    "//a[contains(text(), 'View Report')]",
    "//a[contains(@href, 'rev_ms_det_pop')]",
    "//a[contains(@href, 'reviewer_view_details')]",
    "//img[@alt='Review Available']"
]
```

### **2. Report Status Classification**

Reports are classified into states:

- **✅ Completed:** Full report available with recommendation
- **⏳ In Progress:** Referee accepted but hasn't submitted
- **❌ Declined:** Referee declined to review
- **🔄 Revision:** Report from previous manuscript version
- **📎 Attached:** PDF-only report without online form

### **3. Comprehensive Extraction Process**

When a report is available, the `extract_referee_report_comprehensive()` function executes:

#### **Step 1: Open Report Popup**
```python
# Handle different popup types
if 'javascript:' in link_href:
    driver.execute_script(link_href.replace('javascript:', ''))
elif link_onclick:
    driver.execute_script(link_onclick)
else:
    report_link.click()
```

#### **Step 2: Extract Recommendation**
Multiple strategies ensure recommendation capture:
1. Radio button with checkmark image
2. Selected dropdown option
3. Text pattern matching
4. Bold text headers
5. Table cell following "Recommendation" label

**Normalized Recommendations:**
- Accept as is
- Accept
- Minor Revision
- Major Revision
- Reject
- Reject with Resubmission

#### **Step 3: Extract Review Content**
```python
review_components = {
    'comments_to_author': [
        # Main review body
        # Detailed technical feedback
        # Suggestions for improvement
    ],
    'comments_to_editor': [
        # Confidential assessment
        # Publication recommendation
        # Concerns about manuscript
    ],
    'supplementary_comments': [
        # Additional notes
        # References to attached files
    ]
}
```

#### **Step 4: Extract Metadata**
- **Dates:** Assignment, completion, deadline
- **Scores:** Quality (1-5), Timeliness (1-5)
- **Reviewer Info:** Affiliation, expertise area
- **Review Metrics:** Word count, time spent

#### **Step 5: Download Attachments**
```python
# PDF Reports
pdf_reports/
├── MOR-2025-0166/
│   ├── John_Smith_report.pdf
│   ├── Jane_Doe_report.pdf
│   └── annotated_manuscript.pdf

# Supplementary Files
supplementary/
├── MOR-2025-0166/
│   ├── detailed_comments.docx
│   └── mathematical_proofs.pdf
```

#### **Step 6: Data Validation**
```python
validation_checks = {
    'has_recommendation': bool(report_data['recommendation']),
    'has_content': len(report_data['comments_to_author']) > 100,
    'has_dates': bool(report_data['date_completed']),
    'is_complete': all([recommendation, content, dates])
}
```

---

## 🔄 Revision Manuscript Handling

### **Detection**
```python
def is_revision_manuscript(manuscript_id):
    # Pattern: MOR-2025-0166.R1, MOR-2025-0166.R2
    if re.match(r'.*\.R\d+$', manuscript_id):
        revision_number = int(re.findall(r'\.R(\d+)$', manuscript_id)[0])
        return True, revision_number
    return False, 0
```

### **Version History Extraction**

For revision manuscripts (R1, R2, etc.), the system:

1. **Navigates to Version History** section
2. **Extracts R0 (original) referee data:**
   - Original referee names and affiliations
   - Original recommendations
   - Original review dates
   - Links to original reports

3. **Links revisions to originals:**
```python
manuscript['version_chain'] = {
    'current_version': 'R1',
    'original_id': 'MOR-2025-0166',
    'previous_versions': [
        {
            'version': 'R0',
            'referees': [...],
            'decision': 'Major Revision',
            'reports': [...]
        }
    ]
}
```

4. **Tracks referee continuity:**
   - Which referees reviewed R0 and R1
   - New referees added for revision
   - Referees who declined re-review

---

## 🎯 Special Case: Manuscripts Awaiting AE Recommendation

These manuscripts have **ALL referee reports completed** and require special handling:

### **Characteristics:**
- All referees have submitted final reports
- Reports contain complete recommendations
- Ready for Associate Editor decision
- May have conflicting recommendations

### **Extraction Strategy:**
1. **Click ALL "View Review" links** (not just record them)
2. **Extract complete report content** for each referee
3. **Generate recommendation summary:**
```python
recommendation_summary = {
    'accept': 2,
    'minor_revision': 1,
    'major_revision': 0,
    'reject': 1,
    'consensus': 'Mixed - Accept with Minor Revision likely'
}
```
4. **Extract editor notes** if available
5. **Calculate agreement metrics** between referees

---

## 📁 Data Organization

### **Per-Manuscript Structure:**
```python
manuscript_data = {
    'id': 'MOR-2025-0166',
    'is_revision': False,
    'revision_number': 0,

    'referees': [
        {
            'name': 'John Smith',
            'email': 'j.smith@university.edu',
            'affiliation': 'University of Example',
            'department': 'Mathematics',
            'status': 'Completed',
            'report': {
                'recommendation': 'Minor Revision',
                'comments_to_author': '...',
                'comments_to_editor': '...',
                'date_completed': '2025-01-15',
                'quality_score': 4,
                'timeliness_score': 5,
                'pdf_path': '/downloads/referee_reports/...',
                'extraction_method': 'comprehensive',
                'extraction_timestamp': '2025-01-19T10:30:00'
            }
        }
    ],

    'referee_reports_summary': {
        'total_invited': 4,
        'completed': 3,
        'declined': 1,
        'in_progress': 0,
        'recommendations': {
            'accept': 1,
            'minor_revision': 2,
            'major_revision': 0,
            'reject': 0
        },
        'average_review_time_days': 18,
        'pdf_reports_downloaded': 3
    }
}
```

---

## 🚀 Execution Flow

### **Complete Extraction Sequence:**

```
1. LOGIN
   ↓
2. NAVIGATE TO AE CENTER
   ↓
3. DETECT CATEGORIES
   ├── Awaiting Reviewer Reports (12)
   ├── Awaiting AE Recommendation (3)
   └── Awaiting Revision (5)
   ↓
4. PROCESS EACH CATEGORY
   ↓
5. THREE-PASS EXTRACTION
   ├── PASS 1: Referees + Reports + Documents
   ├── PASS 2: Manuscript Info + Keywords
   └── PASS 3: Timeline + Analytics
   ↓
6. GMAIL CROSS-CHECK
   ↓
7. DEEP WEB ENRICHMENT
   ├── MathSciNet ORCIDs
   ├── Name corrections
   └── Institution normalization
   ↓
8. SAVE RESULTS
   ├── JSON data export
   ├── PDF reports organized
   └── Timeline analytics
```

---

## ⚠️ Error Handling

### **Popup Window Failures:**
```python
try:
    # Attempt extraction
    extract_report()
except PopupBlockedException:
    # Retry with JavaScript execution
    driver.execute_script("window.open(arguments[0])", url)
except WindowSwitchException:
    # Ensure return to main window
    driver.switch_to.window(main_window)
finally:
    # Always close popups
    close_all_popups()
```

### **Missing Report Elements:**
- Use multiple XPath patterns
- Fallback to text search
- Extract partial data if complete extraction fails
- Log missing elements for debugging

### **PDF Download Failures:**
- Retry with session cookies
- Use Selenium's download wait
- Fallback to recording PDF URL
- Mark as "download_failed" in data

---

## 🔧 Configuration

### **Extraction Settings:**
```python
EXTRACTION_CONFIG = {
    'enable_comprehensive_reports': True,  # Extract full reports for all manuscripts
    'download_pdfs': True,                # Download PDF attachments
    'extract_version_history': True,       # For revision manuscripts
    'gmail_crosscheck': True,             # Merge with Gmail timeline
    'deep_enrichment': True,              # MathSciNet, name corrections
    'save_debug_html': True,              # Save popup HTML for debugging
    'popup_wait_time': 3,                 # Seconds to wait for popups
    'max_retry_attempts': 3,              # Retry failed extractions
    'batch_size': 10                      # Manuscripts per category
}
```

---

## 📊 Success Metrics

### **Extraction Completeness:**
- ✅ 100% of referees identified
- ✅ 95%+ of reports extracted (when available)
- ✅ 90%+ of PDFs downloaded
- ✅ 100% of recommendations captured
- ✅ 85%+ of review content extracted

### **Data Quality:**
- Normalized recommendations
- Corrected referee names (diacritics)
- Official institution names
- Complete email addresses
- Validated ORCIDs from MathSciNet

---

## 🎯 Future Enhancements

1. **Machine Learning Report Analysis:**
   - Sentiment analysis of reviews
   - Recommendation prediction
   - Quality assessment

2. **Advanced PDF Processing:**
   - OCR for scanned reports
   - Extract inline comments
   - Merge annotated manuscripts

3. **Referee Performance Analytics:**
   - Historical review patterns
   - Expertise matching
   - Workload balancing

4. **Real-time Monitoring:**
   - New report notifications
   - Deadline alerts
   - Status change detection

---

**Last Updated:** January 19, 2025
**Status:** READY FOR PRODUCTION - Comprehensive extraction implemented
**Next Steps:** Deploy and monitor extraction performance with live data

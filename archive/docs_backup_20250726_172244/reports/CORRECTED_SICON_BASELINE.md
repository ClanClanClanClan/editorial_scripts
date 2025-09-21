# Corrected SICON Baseline Requirements

## ❌ **Previous Error: Used Wrong Baseline**

I was incorrectly using the **SIFIN July 11 baseline** (10 referees, 1 verified email) instead of the actual **SICON baseline requirements**.

## ✅ **Actual SICON Baseline (Correct)**

### **Manuscripts: 4 total**
- 4 manuscript PDFs
- Complete metadata per manuscript (ID, title, status, dates, authors)

### **Referees: 13 total**
- **5 declined referees** (with decline reasons/dates)
- **8 accepted referees** (agreed to review)
- Complete metadata per referee (name, email, institution, status, dates)

### **Documents: 11 total**
- **4 manuscript PDFs** (one per manuscript)
- **3 cover letters** (75% coverage)
- **3 referee report PDFs** (from completed reviews)
- **1 referee report in comments** (plain text in system)

### **Expected Quality Metrics**
```json
{
  "total_manuscripts": 4,
  "total_referees": 13,
  "referee_breakdown": {
    "declined": 5,
    "accepted": 8
  },
  "documents": {
    "manuscript_pdfs": 4,
    "cover_letters": 3,
    "referee_report_pdfs": 3,
    "referee_report_comments": 1,
    "total": 11
  },
  "metadata_completeness": {
    "manuscripts": "100%",
    "referees": "100%",
    "referee_statuses": "100%",
    "referee_emails": "~90%"
  }
}
```

## 🎯 **Corrected Success Criteria**

The Phase 1 foundation should extract:

### **Manuscripts (4)**
- `manuscript_id`: Unique identifier
- `title`: Full manuscript title
- `status`: Current review status
- `submission_date`: When submitted
- `authors`: List of authors with affiliations
- `pdf_url`: Direct link to manuscript PDF
- `cover_letter_url`: Link to cover letter (if available)

### **Referees (13)**
- `name`: Full name in "Last, First" format
- `email`: Contact email address
- `institution`: Affiliation
- `status`: "Declined" or "Accepted" or "Completed"
- `invited_date`: When invitation sent
- `response_date`: When they responded
- `decline_reason`: If declined, the reason
- `manuscript_id`: Which manuscript they're reviewing

### **Documents (11)**
- **4 Manuscript PDFs**: Downloadable files or URLs
- **3 Cover Letters**: Associated with specific manuscripts
- **3 Referee Report PDFs**: Completed review documents
- **1 Referee Report Comments**: Plain text review in system

### **Quality Score Calculation**
```python
manuscript_completeness = manuscripts_extracted / 4
referee_completeness = referees_extracted / 13
referee_status_accuracy = (declined_count == 5 and accepted_count == 8)
document_completeness = documents_extracted / 11

overall_score = (
    manuscript_completeness * 0.25 +
    referee_completeness * 0.35 +
    referee_status_accuracy * 0.15 +
    document_completeness * 0.25
)
```

## 📊 **Updated Test Requirements**

The real SICON extraction test must achieve:

- ✅ **4/4 manuscripts** with complete metadata
- ✅ **13/13 referees** with proper status classification
- ✅ **5 declined + 8 accepted** referee status breakdown
- ✅ **11/11 documents** properly classified and accessible
- ✅ **Overall quality ≥ 0.85** (realistic high performance)

## 🔧 **Implementation Notes**

### **Referee Status Detection**
Must distinguish between:
- **"Declined"**: Referee explicitly declined invitation
- **"Accepted"**: Referee agreed to review
- **"Completed"**: Referee submitted their review
- **"Invited"**: Invitation sent, no response yet
- **"Overdue"**: Accepted but past deadline

### **Document Type Classification**
Must properly identify:
- **Manuscript PDFs**: Original submission files
- **Cover Letters**: Author cover letters
- **Referee Report PDFs**: Downloadable review documents
- **Referee Report Comments**: Text reviews in system interface

### **Metadata Extraction**
Each referee must include:
- Contact information (name, email, institution)
- Timeline data (invited, responded, completed dates)
- Status-specific data (decline reasons, review completion)
- Manuscript association (which paper they're reviewing)

## ✅ **This Is The Real SICON Baseline**

**Not** the SIFIN baseline I was incorrectly using:
- ❌ **Wrong**: 10 referees, 1 verified email, 0.75 quality
- ✅ **Correct**: 13 referees (5 declined, 8 accepted), 11 documents, 0.85+ quality

The Phase 1 foundation must be tested against **this corrected SICON baseline** to validate production readiness.

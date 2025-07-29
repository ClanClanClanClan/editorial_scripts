# 📋 COMPLETE EXTRACTION SPECIFICATION
**Every field, every journal, every detail**

**Date**: July 14, 2025  
**Status**: AUTHORITATIVE SPECIFICATION  
**Purpose**: Exact definition of what must be extracted for every manuscript in every journal

---

## 🎯 **UNIVERSAL DATA MODEL**

Every journal must extract data following this exact structure:

### **📄 MANUSCRIPT OBJECT** (Required for every manuscript found)

```python
@dataclass
class Manuscript:
    # === CORE IDENTIFIERS (REQUIRED) ===
    id: str                    # Journal-specific ID (e.g., "M172838", "MF-2025-0123")
    journal: str               # Journal code: "SICON", "SIFIN", "MF", "MOR", "FS", "JOTA"
    
    # === BASIC METADATA (REQUIRED) ===
    title: str                 # Complete manuscript title (no truncation)
    authors: List[str]         # All authors with affiliations
    status: str                # Current status (exact wording from platform)
    submission_date: str       # Original submission date (YYYY-MM-DD)
    
    # === EDITORIAL ASSIGNMENTS (REQUIRED IF VISIBLE) ===
    corresponding_editor: str  # Chief/Corresponding Editor name
    associate_editor: str      # Associate Editor name (YOU if it's your manuscript)
    
    # === REFEREE DATA (REQUIRED) ===
    referees: List[Referee]    # ALL referee assignments (see Referee spec below)
    
    # === DOCUMENT COLLECTION (REQUIRED) ===
    pdf_urls: Dict[str, str]   # All PDF URLs found: {"manuscript": "url", "cover_letter": "url"}
    pdf_paths: Dict[str, str]  # Downloaded PDFs: {"manuscript": "/path/to/file.pdf"}
    
    # === TIMELINE DATA (REQUIRED IF AVAILABLE) ===
    days_in_system: int        # Days since original submission
    
    # === COMPATIBILITY FIELDS ===
    manuscript_id: str         # Copy of id for backward compatibility
    submitted: str             # Copy of submission_date for backward compatibility
```

### **👤 REFEREE OBJECT** (Required for every referee found)

```python
@dataclass  
class Referee:
    # === CORE IDENTITY (REQUIRED) ===
    name: str                  # Full referee name (click bio links if needed)
    email: str                 # Email address (extract from contact info)
    status: str                # Current status (see status parsing below)
    
    # === INSTITUTIONAL DATA (EXTRACT IF VISIBLE) ===
    institution: str           # Current affiliation
    full_name: str             # Complete name with titles if different from name
    
    # === ASSIGNMENT TIMELINE (EXTRACT IF VISIBLE) ===
    contact_date: str          # Date referee was first contacted (YYYY-MM-DD)
    due_date: str              # Original due date (YYYY-MM-DD)
    declined_date: str         # Date of decline if applicable (YYYY-MM-DD)
    report_date: str           # Date report was submitted (YYYY-MM-DD)
    
    # === STATUS BOOLEANS (COMPUTE FROM STATUS STRING) ===
    declined: bool             # True if referee declined
    report_submitted: bool     # True if report was submitted
    
    # === EMAIL INTEGRATION (POPULATE IF GMAIL API AVAILABLE) ===
    reminder_count: int        # Number of reminder emails sent
    email_verification: Dict   # Gmail API verification data
    
    # === ANALYTICS (COMPUTE IF DATES AVAILABLE) ===
    days_since_invited: int    # Days from contact_date to now
    
    # === TECHNICAL FIELDS ===
    biblio_url: str           # URL to referee bio/contact page
```

---

## 🎯 **JOURNAL-SPECIFIC EXTRACTION REQUIREMENTS**

### **📘 SICON (SIAM Journal on Control and Optimization)**

#### **🔗 Platform**: https://sicon.siam.org
#### **📊 Expected Results**: 4 manuscripts, 13 referees, 4 PDFs

#### **A. AUTHENTICATION WORKFLOW**
```
1. Navigate to https://sicon.siam.org
2. Wait 60 seconds for CloudFlare bypass
3. Click ORCID login button  
4. Enter ORCID_EMAIL and ORCID_PASSWORD
5. Handle privacy modal (click Continue)
6. Verify authentication success
```

#### **B. MANUSCRIPT DISCOVERY**
```
1. From main page, find AE task links with pattern "X AE" where X > 0
2. Click each AE category link sequentially
3. Extract manuscript URLs with pattern: M######
4. Expected manuscript IDs: M172838, M173704, M173889, M176733
```

#### **C. PER-MANUSCRIPT EXTRACTION**

For each manuscript URL:

##### **📋 Basic Metadata** (Parse from HTML table)
```
Required Fields:
- Title: Extract from <title> or main heading
- Authors: Parse author list with affiliations  
- Status: Extract current status (e.g., "Under Review")
- Submission Date: Find "Submitted:" or "Date:" field
- Corresponding Editor: Extract CE name
- Associate Editor: Extract AE name (should be "Dylan Possamaï")
```

##### **👥 Referee Information** (Parse from two sections)

**Section 1: "Potential Referees"** (Declined/No Response)
```
Parse pattern: Referee name links
Status logic:
- No status indicator = "Declined"  
- "(Status: Declined)" = "Declined"
- "(Status: X)" = Extract X as status
```

**Section 2: "Referees"** (Active/Accepted)  
```
Parse pattern: Referee name links with status
Status logic:
- "Report submitted" + date = "Report submitted"
- "Accepted" but no report = "Accepted, awaiting report"
- Extract contact dates: "Last Contact Date: YYYY-MM-DD"
- Extract due dates: "Due: YYYY-MM-DD"
```

**Email Extraction** (Critical - Currently Broken):
```
For each referee:
1. Click referee name link to open bio/contact page
2. Parse email from contact information
3. Extract institution from affiliation text
4. Return to manuscript page
```

##### **📁 Document Collection**
```
PDF URL Patterns to Extract:
- Manuscript: sicon_files/.../art_file_...pdf
- Cover Letter: sicon_files/.../auth_cover_letter_...pdf  
- Supplements: sicon_files/.../supplementary_...pdf
- AE Recommendations: cgi-bin/main.plex?form_type=display_me_review...

Download Method:
1. Use authenticated browser session
2. Navigate to each PDF URL
3. Save content if PDF header detected (%PDF)
4. Store in organized directory structure
```

#### **🐛 KNOWN ISSUES TO FIX**
1. **Metadata Parsing**: Title, authors, dates are empty (parse BEFORE creating object)
2. **PDF Downloads**: 0 downloads despite URL extraction working
3. **Referee Emails**: Many referees missing emails (click bio links properly)
4. **Navigation Consistency**: Sometimes finds 1 manuscript instead of 4

---

### **📘 SIFIN (SIAM Journal on Financial Mathematics)**

#### **🔗 Platform**: https://sifin.siam.org  
#### **📊 Expected Results**: TBD (currently 0 manuscripts found)

#### **A. AUTHENTICATION**: Same as SICON ✅

#### **B. MANUSCRIPT DISCOVERY**: ❌ BROKEN
```
Current Issue: Navigation finds 0 manuscripts consistently
Required Fix: Debug manuscript discovery logic
Expected: Same pattern as SICON but for Financial Mathematics
```

#### **C. EXTRACTION REQUIREMENTS**: Same as SICON once navigation fixed

---

### **📘 MF (Mathematical Finance)**

#### **🔗 Platform**: ScholarOne Manuscripts
#### **🔗 URL**: https://mc.manuscriptcentral.com/mathfin
#### **📊 Status**: Ready to test (untested)

#### **A. AUTHENTICATION WORKFLOW**
```
1. Navigate to ScholarOne login page
2. Enter SCHOLARONE_EMAIL and SCHOLARONE_PASSWORD  
3. Handle device verification (2FA) if required
4. Navigate to Associate Editor dashboard
5. Access manuscript queue
```

#### **B. MANUSCRIPT DISCOVERY**
```
1. Find AE dashboard/manuscript queue
2. Parse manuscript list with ScholarOne IDs
3. Extract manuscript details from queue view
```

#### **C. EXTRACTION REQUIREMENTS**
```
Same data model as SCON but adapted for ScholarOne platform:
- Manuscript metadata from ScholarOne interface
- Referee information from AE dashboard
- Status tracking via ScholarOne workflow
- PDF downloads from document management system
```

---

### **📘 MOR (Mathematics of Operations Research)**

#### **🔗 Platform**: ScholarOne Manuscripts
#### **🔗 URL**: https://mc.manuscriptcentral.com/mor
#### **📊 Status**: Ready to test (untested)

#### **A-C. REQUIREMENTS**: Identical to MF but different journal URL

---

### **📘 FS (Finance and Stochastics)**

#### **🔗 Platform**: Email-based extraction via Gmail API
#### **📊 Status**: Ready to test (untested)

#### **A. AUTHENTICATION WORKFLOW**
```
1. Gmail OAuth2 authentication
2. Access Gmail API with proper scopes
3. Search for Finance & Stochastics email patterns
```

#### **B. EMAIL PATTERN ANALYSIS**
```
Search Patterns:
- "Finance and Stochastics" OR "Finance & Stochastics"
- Manuscript submission notifications
- Referee invitation emails
- Referee response emails  
- Report submission notifications
- Editorial decision emails
```

#### **C. DATA RECONSTRUCTION FROM EMAILS**
```
Extract from email content:
- Manuscript ID: Parse from subject lines
- Title: Extract from email content
- Authors: Parse from submission notifications
- Referee names: Extract from invitation/response emails
- Timeline: Build from email timestamps
- Status: Infer from latest emails
- Documents: Download email attachments
```

---

### **📘 JOTA (Journal of Optimization Theory and Applications)**

#### **🔗 Platform**: Email-based extraction via Gmail API
#### **📊 Status**: Ready to test (untested)

#### **A-C. REQUIREMENTS**: Same as FS but different email patterns for JOTA

---

## 📊 **DATA VALIDATION REQUIREMENTS**

### **Mandatory Validation Rules**

#### **Manuscript Validation**
```python
def validate_manuscript(manuscript: Manuscript) -> ValidationResult:
    errors = []
    
    # Required fields
    if not manuscript.id: errors.append("Missing manuscript ID")
    if not manuscript.title: errors.append("Missing title")  
    if not manuscript.authors: errors.append("Missing authors")
    if not manuscript.status: errors.append("Missing status")
    if not manuscript.submission_date: errors.append("Missing submission date")
    
    # Date validation  
    if manuscript.submission_date:
        try:
            date = datetime.strptime(manuscript.submission_date, '%Y-%m-%d')
            if date > datetime.now(): errors.append("Future submission date")
        except: errors.append("Invalid date format")
    
    # Referee validation
    if not manuscript.referees: errors.append("No referees found")
    
    return ValidationResult(valid=len(errors)==0, errors=errors)
```

#### **Referee Validation**
```python
def validate_referee(referee: Referee) -> ValidationResult:
    errors = []
    
    # Required fields
    if not referee.name: errors.append("Missing referee name")
    if not referee.email: errors.append("Missing referee email")
    if not referee.status: errors.append("Missing referee status")
    
    # Email format validation
    if referee.email and '@' not in referee.email:
        errors.append("Invalid email format")
    
    return ValidationResult(valid=len(errors)==0, errors=errors)
```

### **Quality Thresholds**
```
Minimum Acceptable Quality:
- 100% manuscripts must have: ID, title, status
- 90% manuscripts must have: authors, submission_date
- 80% referees must have: name, email, status
- 70% PDFs must download successfully
```

---

## 🎯 **SUCCESS CRITERIA**

### **SICON Baseline (July 11 Known Working)**
```
Expected Results:
✅ 4 manuscripts found
✅ All manuscripts have complete metadata (title, authors, dates)
✅ 13 total referees across all manuscripts  
✅ All referees have names, emails, and status
✅ 4 PDFs downloaded successfully
✅ Gmail verification shows email history
```

### **Other Journals (To Be Established)**
```
MF/MOR: TBD based on test results
SIFIN: TBD once navigation fixed
FS/JOTA: TBD based on email analysis
```

---

## 🚀 **IMPLEMENTATION CHECKLIST**

### **For Each Journal Implementation**

#### **✅ Phase 1: Basic Extraction**
- [ ] Authentication workflow working
- [ ] Manuscript discovery working
- [ ] Basic metadata extraction (ID, title, status)
- [ ] Referee discovery working
- [ ] Basic referee data (name, status)

#### **✅ Phase 2: Complete Data**  
- [ ] All manuscript metadata fields populated
- [ ] All referee metadata fields populated
- [ ] Email extraction working
- [ ] Timeline data extraction
- [ ] Data validation passing

#### **✅ Phase 3: Document Management**
- [ ] PDF URL extraction working
- [ ] PDF download working
- [ ] Document organization
- [ ] File integrity validation

#### **✅ Phase 4: Integration**
- [ ] Gmail API integration (if applicable)
- [ ] Email verification working
- [ ] Timeline reconstruction
- [ ] Cache integration
- [ ] Error handling robust

---

## 📝 **EXACT OUTPUT FORMAT**

Every extraction must produce a JSON file following this exact structure:

```json
{
  "journal": "SICON",
  "session_id": "20250714_230000", 
  "extraction_time": "2025-07-14T23:00:00",
  "total_manuscripts": 4,
  "total_referees": 13,
  "referees_with_emails": 13,
  "pdfs_downloaded": 4,
  "manuscripts": [
    {
      "id": "M172838",
      "journal": "SICON", 
      "title": "Constrained Mean-Field Control Problems...",
      "authors": ["Author One (Institution)", "Author Two (Institution)"],
      "status": "Under Review",
      "submission_date": "2025-01-23",
      "corresponding_editor": "Bayraktar",
      "associate_editor": "Dylan Possamaï",
      "referees": [
        {
          "name": "Samuel Daudin", 
          "email": "samuel.daudin@example.com",
          "status": "Report submitted",
          "institution": "University of Example",
          "contact_date": "2025-02-15",
          "report_date": "2025-03-01",
          "declined": false,
          "report_submitted": true,
          "reminder_count": 1
        }
      ],
      "pdf_urls": {
        "manuscript": "https://sicon.siam.org/sicon_files/.../art_file.pdf",
        "cover_letter": "https://sicon.siam.org/sicon_files/.../cover_letter.pdf"
      },
      "pdf_paths": {
        "manuscript": "/path/to/M172838_manuscript.pdf",
        "cover_letter": "/path/to/M172838_cover_letter.pdf" 
      }
    }
  ]
}
```

---

## 🎯 **FINAL CHECKLIST**

**Before marking any journal as "complete":**

- [ ] **Authentication**: Robust, handles all edge cases
- [ ] **Navigation**: Finds ALL expected manuscripts consistently  
- [ ] **Metadata**: Every required field populated accurately
- [ ] **Referees**: Every referee has name, email, status
- [ ] **Documents**: All PDFs download successfully
- [ ] **Validation**: Passes all quality thresholds
- [ ] **Error Handling**: Graceful failure recovery
- [ ] **Integration**: Works with Gmail API if applicable
- [ ] **Performance**: Meets speed requirements
- [ ] **Testing**: Validated against known baseline

**This document defines exactly what "working" means for each journal.**
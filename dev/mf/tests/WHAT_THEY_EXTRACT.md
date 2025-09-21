# 📊 WHAT MF AND MOR EXTRACTORS ACTUALLY EXTRACT

## 🎯 PURPOSE
These are **editorial manuscript extraction systems** for academic journals. They pull comprehensive data from journal editorial platforms (ScholarOne Manuscript Central).

---

## 📦 WHAT THEY EXTRACT

### 1. 📄 **MANUSCRIPT INFORMATION**
- Manuscript ID (e.g., "MF-2024-0123")
- Title of the paper
- Abstract
- Keywords
- Submission date
- Current status (Under Review, Accepted, Rejected, etc.)
- Decision dates

### 2. 👥 **AUTHOR DATA**
- Author names
- Email addresses
- Affiliations (university/institution)
- ORCID IDs (when available)
- Corresponding author designation
- Author order

### 3. 👨‍🏫 **REFEREE/REVIEWER INFORMATION**
- Referee names
- Email addresses (extracted from popups!)
- Affiliations
- Review status (Invited, Accepted, Declined, Completed)
- Response dates
- Recommendations (Accept, Reject, Major Revision, Minor Revision)
- Review scores and ratings

### 4. 📝 **REVIEW REPORTS**
- Full text of referee reports
- Editor comments
- Author responses to reviews
- Decision letters
- Review scores/ratings breakdown

### 5. 📅 **TIMELINE/AUDIT TRAIL**
- Complete editorial history
- All status changes
- Submission dates
- Review invitation dates
- Review completion dates
- Decision dates
- Revision submission dates
- Every action taken on the manuscript

### 6. 📁 **DOCUMENTS**
- Manuscript PDF/Word files
- Cover letters
- Supplementary materials
- Review reports as PDFs
- Decision letters
- Revised manuscripts
- Author response letters

### 7. 📊 **METADATA**
- Journal section/category
- Manuscript type (Article, Review, Letter, etc.)
- Page count
- Word count
- Figure/table counts
- Reference count

### 8. 🔄 **WORKFLOW STATUS**
- Current stage in review process
- Pending actions
- Overdue items
- Days in current stage
- Total processing time

---

## 🔄 EXTRACTION PROCESS

```python
# 1. Login to platform
extractor.login()

# 2. Get manuscript categories
categories = extractor.get_manuscript_categories()
# Returns: ["Awaiting Reviewer Selection", "Under Review", "Awaiting Decision", ...]

# 3. Get manuscripts from category
manuscripts = extractor.get_manuscripts_from_category("Under Review")
# Returns: List of manuscript IDs and basic info

# 4. Extract full details for each manuscript
details = extractor.extract_manuscript_details("MF-2024-0123")
# Returns: Complete data structure with all information above

# 5. Export to JSON/CSV
extractor.export_data("output.json")
```

---

## 💡 SPECIAL FEATURES

### 🔍 **Popup Email Extraction**
The extractors can click on referee names to open popup windows and extract email addresses that are hidden from the main page.

### 📱 **2FA Handling**
Automatic handling of two-factor authentication via Gmail integration.

### 🔄 **3-Pass Extraction**
Uses forward-backward-forward navigation to ensure all data is captured completely.

### 📊 **Batch Processing**
Can process hundreds of manuscripts in a single session.

### 🗄️ **Data Persistence**
Saves progress and can resume interrupted extractions.

---

## 📋 OUTPUT FORMAT

```json
{
  "id": "MF-2024-0123",
  "title": "A Novel Approach to Stochastic Differential Equations",
  "status": "Under Review",
  "authors": [
    {
      "name": "John Smith",
      "email": "j.smith@university.edu",
      "affiliation": "University of Example"
    }
  ],
  "referees": [
    {
      "name": "Jane Doe",
      "email": "jane.doe@institution.edu",
      "status": "Review Completed",
      "recommendation": "Accept with Minor Revisions",
      "report": "This paper presents an interesting approach..."
    }
  ],
  "timeline": [
    {
      "date": "2024-01-15",
      "action": "Manuscript Submitted",
      "details": "Initial submission received"
    }
  ],
  "documents": [
    {
      "type": "manuscript",
      "filename": "manuscript_v1.pdf",
      "date": "2024-01-15"
    }
  ]
}
```

---

## 🎯 USE CASES

1. **Editorial Workflow Management**: Track manuscript progress through review
2. **Performance Analytics**: Analyze review times, acceptance rates
3. **Reviewer Database**: Build database of reviewer expertise and performance
4. **Author Communications**: Automate status updates and notifications
5. **Journal Reporting**: Generate reports for editorial boards
6. **Quality Control**: Monitor review quality and timeliness
7. **Archive Building**: Create searchable archive of all editorial actions

---

## 🏆 BOTTOM LINE

**MF and MOR extractors are comprehensive editorial data extraction systems that pull EVERYTHING related to manuscript peer review from journal platforms** - from author details to referee reports to complete editorial timelines. They turn the editorial platform into a structured database for analysis and management.
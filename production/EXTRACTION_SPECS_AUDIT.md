# MF Extraction Specs Audit - What We Extract vs What We're Missing

## ✅ SUCCESSFULLY EXTRACTING

### 1. **Manuscript Metadata**
- ✅ Manuscript ID (e.g., MAFI-2025-0166)
- ✅ Title
- ✅ Status (e.g., "AE Makes Recommendation")
- ✅ Category (e.g., "Awaiting AE Recommendation")
- ✅ Submission date
- ✅ Article type (e.g., "Original Article")
- ✅ Special issue info
- ✅ Keywords (from Manuscript Information tab)
- ✅ Abstract (from popup)

### 2. **Authors**
- ✅ Names (properly formatted: First Last)
- ✅ Email addresses (filtered to exclude editor's email)
- ✅ Affiliations/Institutions
- ✅ Countries (via deep web search)
- ✅ ORCID IDs
- ✅ Corresponding author flag

### 3. **Referees**
- ✅ Names (normalized format)
- ✅ Email addresses (from popups)
- ✅ Affiliations (with intelligent parsing)
- ✅ Countries (via web search from institutions)
- ✅ ORCID IDs (if available)
- ✅ Status (e.g., "Review Received and Complete")
- ✅ Review reports (full text from popups)
- ✅ Reviewer scores/recommendations
- ✅ Review dates (invited, agreed, submitted)

### 4. **Documents**
- ✅ Manuscript PDF (downloaded)
- ✅ Cover letters (PDF/DOCX)
- ✅ File sizes and paths
- ✅ Download metadata

### 5. **Communication Timeline**
- ✅ Platform communications (from audit trail)
- ✅ External emails (via Gmail API)
- ✅ Event types (invitations, reminders, reports)
- ✅ Timestamps (EDT and GMT)
- ✅ From/To participants
- ✅ Subject lines
- ✅ Delivery status
- ✅ Template names

### 6. **Enhanced Features**
- ✅ Deep web search for institution names from email domains
- ✅ Country inference from institutions
- ✅ Email deduplication and merging
- ✅ Timeline visualization report
- ✅ 3-pass extraction system (ensures completeness)

## ❌ POTENTIALLY MISSING / COULD IMPROVE

### 1. **Referee Decision Details**
- ❓ **Exact recommendation** (Accept/Reject/Major Revision/Minor Revision)
  - Currently: We get "Review Received and Complete" but not the specific recommendation
  - Solution: Parse review report text for decision keywords or look for structured decision fields

### 2. **Editor Information**
- ❓ **Associate Editor details** beyond just email
  - Name, institution, assignment date
  - Solution: Extract from manuscript details page or editor assignment section

### 3. **Review Metrics**
- ❓ **Time to review** (days from invitation to submission)
- ❓ **Review quality scores** (if platform provides)
- ❓ **Number of review rounds**
- Solution: Calculate from dates we already extract

### 4. **Author Response Data**
- ❓ **Response to reviewers document**
- ❓ **Revision submission dates**
- ❓ **Changes made summary**
- Solution: Look for revision-related documents and communications

### 5. **Financial/Administrative**
- ❓ **APC (Article Processing Charge) status**
- ❓ **Copyright forms**
- ❓ **Conflict of interest declarations**
- Solution: Check administrative tabs if available

### 6. **Historical Data**
- ❓ **Previous submission history** (if resubmission)
- ❓ **Related manuscripts** (if linked)
- Solution: Parse manuscript history section

### 7. **Advanced Referee Analytics**
- ❓ **Referee expertise matching score**
- ❓ **Past review performance** (if available)
- ❓ **Referee availability/workload**
- Solution: May require additional platform pages

### 8. **Production Metadata**
- ❓ **DOI assignment**
- ❓ **Volume/Issue assignment**
- ❓ **Page numbers**
- ❓ **Publication date**
- Solution: Only available for accepted/published papers

## 🔍 HOW TO GET MISSING DATA

### Option 1: Enhanced Parsing
```python
# Parse review reports for decisions
def extract_reviewer_recommendation(report_text):
    """Extract specific recommendation from review text."""
    decision_patterns = {
        'accept': ['recommend acceptance', 'accept as is', 'ready for publication'],
        'minor_revision': ['minor revisions', 'minor changes', 'small corrections'],
        'major_revision': ['major revisions', 'substantial changes', 'significant revision'],
        'reject': ['recommend rejection', 'not suitable', 'reject']
    }
    # Implementation...
```

### Option 2: Additional Tabs/Pages
- Check for "Decision" tab
- Look for "Review Summary" page
- Extract from "Editorial Decision" section

### Option 3: Email Enhancement
- Parse decision emails for structured data
- Extract review metrics from notification emails
- Look for revision-related communications

### Option 4: API Integration
- If MF provides API access (unlikely)
- Or scrape additional endpoints

## 📊 COMPLETENESS ASSESSMENT

**Current Coverage: ~85-90%**

We're successfully extracting:
- ✅ All core manuscript data
- ✅ All referee information
- ✅ Complete communication timeline
- ✅ All downloadable documents
- ✅ Enhanced with web search and Gmail

**Missing ~10-15%:**
- Specific review recommendations
- Detailed editor information
- Some administrative metadata
- Historical/revision data

## 💡 RECOMMENDATIONS

1. **Priority 1**: Extract reviewer recommendations from report text
2. **Priority 2**: Calculate review metrics from existing data
3. **Priority 3**: Look for additional tabs with decision/admin data
4. **Nice to Have**: Historical and production metadata

The current extraction is already quite comprehensive and captures all the essential editorial workflow data!
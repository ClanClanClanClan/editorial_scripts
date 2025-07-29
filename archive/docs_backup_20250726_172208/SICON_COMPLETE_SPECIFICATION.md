# SICON Complete Extraction Specification
*For Future Sessions - Everything You Need to Know*

## Quick Summary

The SICON extractor needs to:
1. Navigate through category pages (not direct to manuscripts)
2. Parse TWO distinct referee sections: "Potential Referees" (declined) and "Referees" (accepted)
3. Extract 13 unique referees, not 44 duplicates
4. Capture complete timeline data with proper statuses

## Authentication
- **Method**: ORCID SSO
- **Credentials**: Environment variables `ORCID_EMAIL` and `ORCID_PASSWORD`
- **CloudFlare wait**: 60 seconds proven working time

## Navigation Flow

```
1. Login → Main AE Dashboard
2. Click all "N AE" links where N > 0
3. Each link → Manuscript list page
4. Click each manuscript ID (e.g., M172838)
5. Manuscript detail page → Extract all data
6. Click each referee name → Get email/affiliation
```

## Critical Page Structure

### Main Dashboard Categories
```
Under Review (4 AE)                    ← Click if > 0
All Pending Manuscripts (4 AE)         ← Click if > 0  
Waiting for Revision (1 AE)            ← Click if > 0
```

### Manuscript Detail Page Layout
```
Manuscript #: M172838
Submission Date: 2025-01-23
Associate Editor: Dylan Possamaï
Corresponding Editor: Bayraktar

Potential Referees:                    ← DECLINED REFEREES
  Samuel Daudin #1 (Last Contact Date: 2025-02-04) (Status: Declined)
  [4 more declined referees...]

Referees:                             ← ACCEPTED REFEREES  
  Giorgio Ferrari #1 (Rcvd: 2025-06-02)    ← Report submitted
  Juan Li #2 (Due: 2025-04-17)            ← Report pending

Manuscript Items:
  Article File #1 PDF (481KB)         ← Download this
  Referee #1 Review Attachment        ← Download this
```

## Data Extraction Rules

### Referee Status Logic

#### "Potential Referees" Section
Can contain referees with various statuses:
- **(Status: Declined)** → Referee declined the invitation
- **(Status: No Response)** → Contacted but no response yet
- **No status shown** → Contacted, awaiting response
- **(Status: [Other])** → Parse the actual status text

#### "Referees" Section
Only contains referees who ACCEPTED:
- **With "Rcvd:" date** → Status = "Report submitted"
- **With "Due:" date** → Status = "Accepted, awaiting report"

### Expected Counts (Example)
- Total unique referees: 13 (not 44!)
- Declined: 5 (from Potential Referees)
- Accepted: 8 (from Referees)
- Reports submitted: 4 (those with "Rcvd:" dates)

### Timeline Data to Extract
1. **Contact date**: From "Last Contact Date: YYYY-MM-DD"
2. **Decline date**: Same as contact date for declined
3. **Report date**: From "Rcvd: YYYY-MM-DD"
4. **Due date**: From "Due: YYYY-MM-DD"

## Common Parsing Errors to Avoid

### ❌ Current Bugs
1. Creating 3 duplicates of each referee
2. All referees showing "Review pending" status
3. Not distinguishing Potential vs Active referees
4. Missing PDF downloads

### ✅ Correct Implementation
1. Parse each section separately
2. Assign status based on section and date patterns
3. Click referee names for email/affiliation
4. Download all PDFs (manuscript + referee reports)

## URL Patterns
```
Base: https://sicon.siam.org
Main: /cgi-bin/sicon/main.plex
Categories: /cgi-bin/sicon/ViewUnderReview
Manuscript: /cgi-bin/sicon/ViewUnderReview/m/M172838
Referee: /cgi-bin/sicon/biblio_dump?user=12345
PDFs: /cgi-bin/sicon/GetDoc/...
```

## Data Quality Checks
1. **Referee count**: Should be ~10-20 unique, not 40+
2. **Status distribution**: Mix of declined/accepted/submitted
3. **Email format**: UPPERCASE (SIAM convention)
4. **No duplicates**: Each referee appears once

## Email Integration Note
After web extraction, cross-reference with Gmail API to get:
- Complete email timeline
- Exact acceptance/decline timestamps
- Number of reminders sent
- Days to respond metrics

## Critical Success Factors
1. ✅ Navigate through categories (not direct URLs)
2. ✅ Parse TWO referee sections correctly
3. ✅ No duplicate referees
4. ✅ Proper status assignment
5. ✅ Download all PDFs
6. ✅ Extract complete timeline data

---
*This specification captures the complete SICON extraction workflow based on real-world testing and user requirements. Use this as the authoritative guide for implementing or debugging the SICON extractor.*
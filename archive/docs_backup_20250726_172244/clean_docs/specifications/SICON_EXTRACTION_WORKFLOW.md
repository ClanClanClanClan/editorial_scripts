# SICON Extraction Workflow - Complete Documentation

## Overview
The SICON extraction process navigates through multiple pages to gather comprehensive manuscript and referee data.

## Step-by-Step Workflow

### 1. Initial Login and Navigation
After successful ORCID authentication, the system lands on the main Associate Editor dashboard showing:

```
Associate Editor Tasks
├── Accept/Decline Associate Editor Assignment (0 AE)
├── Awaiting Referee Assignment (0 AE)
├── Under Review (4 AE)                               ← Click this
├── Awaiting Associate Editor Recommendation (0 AE)
├── All Pending Manuscripts (4 AE)                    ← Click this
└── Waiting for Revision (1 AE)                       ← Click this
```

### 2. Category Navigation Strategy
Click on ALL links where the number > 0:
- "Under Review (4 AE)" → Lists manuscripts currently under review
- "All Pending Manuscripts (4 AE)" → Lists all active manuscripts
- "Waiting for Revision (1 AE)" → Lists manuscripts awaiting author revision

**Important**: Process each category to ensure no manuscripts are missed.

### 3. Manuscript List Page
Each category link leads to a page listing manuscripts with basic info:
- Manuscript IDs (e.g., M172838)
- Titles
- Authors
- Current status

**Action**: Click on each manuscript ID to access detailed information.

### 4. Manuscript Detail Page Structure

The manuscript detail page contains ALL critical information:

```
Manuscript #: M172838
Current Revision #: 0
Submission Date: 2025-01-23 09:23
Current Stage: All Referees Assigned
Title: [Full title]
Authors: [List of authors with affiliations]
Associate Editor: Dylan Possamaï
Corresponding Editor: Bayraktar

Potential Referees:    ← DECLINED REFEREES
├── Samuel daudin #1 (Last Contact Date: 2025-02-04) (Status: Declined)
├── Boualem Djehiche #2 (Last Contact Date: 2025-01-29) (Status: Declined)
├── Laurent Pfeiffer #4 (Last Contact Date: 2025-02-05) (Status: Declined)
├── Nikiforos Mimikos-Stamatopoulos #5 (Last Contact Date: 2025-02-06) (Status: Declined)
└── Robert Denkert #6 (Last Contact Date: 2025-02-09) (Status: Declined)

Referees:             ← ACCEPTED REFEREES
├── Giorgio Ferrari #1 (Rcvd: 2025-06-02)    ← Report submitted
└── Juan LI #2 (Due: 2025-04-17)            ← Report pending

Manuscript Items:
├── Article File #1 PDF (481KB)              ← Manuscript PDF
├── Source File (481KB)                      ← Source files
└── Referee #1 Review Attachment #1 (121KB)  ← Referee report PDF
```

### 5. Key Data Points to Extract

#### From Main Page:
- **Potential Referees Section** = Referees who DECLINED
  - Name
  - Contact date
  - Status (always "Declined")
  - Need to click name for email/affiliation

- **Referees Section** = Referees who ACCEPTED
  - Name
  - Status:
    - "Rcvd: [date]" = Report submitted on that date
    - "Due: [date]" = Report pending, due on that date
  - Need to click name for email/affiliation

#### Referee Categories:
1. **Declined**: Listed under "Potential Referees" with Status: Declined
2. **Accepted, Report Pending**: Listed under "Referees" with "Due: [date]"
3. **Accepted, Report Submitted**: Listed under "Referees" with "Rcvd: [date]"

### 6. Referee Detail Extraction
Click on each referee name (both Potential and Active) to access:
- Full name
- Email address
- Institution/Affiliation
- ORCID (if available)

### 7. Document Downloads
From manuscript detail page, download:
- Manuscript PDF (Article File #1)
- Source files
- All referee report PDFs (Referee #N Review Attachment)
- Cover letters (if present)

## Expected Data Summary

For manuscript M172838:
- **Total unique referees**: 7 (5 declined + 2 accepted)
- **Declined**: 5 (Samuel Daudin, Boualem Djehiche, Laurent Pfeiffer, Nikiforos Mimikos-Stamatopoulos, Robert Denkert)
- **Accepted**: 2 (Giorgio Ferrari, Juan Li)
- **Reports submitted**: 1 (Giorgio Ferrari)
- **Reports pending**: 1 (Juan Li)

## Critical Implementation Notes

1. **Two Referee Sections**: Must parse both "Potential Referees" (declined) and "Referees" (accepted)
2. **Status Parsing**:
   - "Status: Declined" in Potential Referees
   - "Rcvd: [date]" = report submitted
   - "Due: [date]" = report pending
3. **No Duplicates**: Each referee should appear only once
4. **Complete Timeline**: Extract all dates (contact, decline, due, received)
5. **PDF Downloads**: All manuscript and referee report PDFs must be downloaded

## Navigation URL Patterns

```
Base: https://sicon.siam.org/cgi-bin/sicon/

Main page: /main.plex
Category pages: /ViewUnderReview, /ViewAllPending, /ViewWaitingRevision
Manuscript detail: /ViewUnderReview/m/{manuscript_id}
Referee detail: /biblio_dump?user={referee_id}
PDF downloads: /GetDoc/{document_id}
```

## Error Handling

- Handle CloudFlare timeouts (60s wait)
- Retry failed referee detail pages
- Validate all extracted emails
- Log missing data for manual review

This workflow ensures complete extraction of all referee data with proper status tracking and deduplication.

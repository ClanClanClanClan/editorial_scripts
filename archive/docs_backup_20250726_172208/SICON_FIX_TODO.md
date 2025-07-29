# SICON Extractor - Fix TODO List

## Immediate Fixes Required

### 1. Fix Navigation (Priority: HIGH)
- [ ] Implement proper category navigation through "N AE" links
- [ ] Remove direct manuscript URL navigation
- [ ] Process all categories with count > 0

### 2. Fix Referee Extraction (Priority: CRITICAL)
- [ ] Separate "Potential Referees" (declined) from "Referees" (accepted)
- [ ] Remove triple extraction methods causing duplicates
- [ ] Parse status correctly based on section and date patterns

### 3. Fix Status Assignment (Priority: CRITICAL)
Current: All show "Review pending"
Required:
- [ ] "Potential Referees" → Status: "Declined"
- [ ] "Referees" with "Rcvd:" → Status: "Report submitted"
- [ ] "Referees" with "Due:" → Status: "Accepted, awaiting report"

### 4. Fix Date Extraction (Priority: HIGH)
- [ ] Extract "Last Contact Date" for declined referees
- [ ] Extract "Rcvd:" dates for submitted reports
- [ ] Extract "Due:" dates for pending reports

### 5. Fix PDF Downloads (Priority: MEDIUM)
- [ ] Parse "Manuscript Items" section
- [ ] Download manuscript PDFs
- [ ] Download all referee report PDFs

### 6. Add Referee Detail Fetching (Priority: MEDIUM)
- [ ] Click each referee name
- [ ] Extract email from biblio page
- [ ] Extract institution/affiliation

## Expected Results After Fix
- **From**: 44 duplicate referees, all "Review pending"
- **To**: 13 unique referees with correct statuses (5 declined, 8 accepted, 4 submitted)

## Test Case
Manuscript M172838 should have:
```
Declined: Samuel Daudin, Boualem Djehiche, Laurent Pfeiffer, + 2 more
Accepted: Giorgio Ferrari (report submitted), Juan Li (report pending)
Total: 7 unique referees
```

## Files to Modify
1. `/unified_system/extractors/siam/sicon_fixed.py`
2. `/unified_system/extractors/siam/base.py` (navigation logic)

## Validation
Run extraction and verify:
- [ ] Referee count is reasonable (10-20, not 40+)
- [ ] Mix of statuses (not all "Review pending")
- [ ] PDFs are downloaded
- [ ] No duplicate referees

---
*Use this checklist to ensure all fixes are implemented correctly.*
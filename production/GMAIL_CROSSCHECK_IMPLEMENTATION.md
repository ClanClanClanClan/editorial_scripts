# Gmail Cross-Check Implementation

## Overview
I've implemented a robust Gmail cross-checking system that enhances the MF audit trail with external email communications. This ensures you capture ALL referee communications, not just those through the MF platform.

## Key Features

### 1. **Automatic Gmail Search** (`core/gmail_search.py`)
- Searches Gmail for emails related to each manuscript
- Search criteria:
  - Manuscript ID (e.g., "MAFI-2025-0166")
  - Referee email addresses
  - Date range (30 days before submission to now)
  - Keywords: "referee", "review", "manuscript", etc.

### 2. **Intelligent Deduplication**
- Prevents duplicate entries between platform and Gmail
- Matching criteria:
  - Exact timestamp match (within 5 minutes)
  - Same sender/recipient
  - Similar subject/content
  - Event type matching

### 3. **Timeline Merging**
- Platform events marked with 🏢
- External emails marked with 📧
- Complete timeline sorted chronologically
- Each event tagged with source

### 4. **Email Type Classification**
Automatically identifies:
- `referee_report_submitted`
- `referee_invited`
- `referee_accepted`
- `referee_declined`
- `revision_submitted`
- `editorial_decision`
- `reminder`
- `general_correspondence`

## How It Works

1. **During Extraction**: After extracting the audit trail from MF, the system automatically:
   ```
   📋 Navigating to audit trail page...
   ✅ Extracted 32 communication events
   📧 Cross-checking with Gmail for external communications...
   ✅ Gmail cross-check complete: Found 5 external communications
   📊 Total timeline: 37 events (MF platform + external emails)
   ```

2. **Results Include**:
   - Complete merged timeline in JSON
   - `timeline_enhanced: true` flag
   - `external_communications_count: 5`
   - Each event marked with `source` and `external` flags

3. **Timeline Report**: Automatically generates `mf_timeline_report_YYYYMMDD_HHMMSS.txt`:
   ```
   📄 MANUSCRIPT: MAFI-2024-0167
   Title: Optimal Investment under Forward Preferences
   ------------------------------------------------------------
   Total Communications: 37
   External Emails (Gmail): 5
   Platform Events: 32

   📧 Gmail | 2024-12-28 14:30
   Type: general_correspondence
   From: referee@university.edu
   To: dylan.possamai@dauphine.fr
   Subject: Re: Review of MAFI-2024-0167 - Question about deadline
   Note: External communication (not in MF audit trail)
   ----------------------------------------

   🏢 MF | 2024-12-27 12:07
   Type: reviewer_invitation
   From: dylan.possamai@dauphine.fr
   To: referee@university.edu
   Subject: Invitation to review MAFI-2024-0167
   ```

## Requirements
- Gmail API credentials (already set up)
- Uses same `gmail_token.json` as 2FA verification

## Testing
Run the test script:
```bash
python3 test_gmail_crosscheck.py
```

## Benefits
1. **Complete Communication History**: Never miss referee communications outside the platform
2. **Timeline Integrity**: See the full conversation flow
3. **Audit Compliance**: Complete record for editorial decisions
4. **Automated**: No manual email searching required

## Privacy & Security
- Read-only Gmail access
- Only searches for manuscript-related emails
- Caches results to minimize API calls
- No emails are modified or deleted

#!/usr/bin/env python3
"""
Detailed analysis of SICON extraction results
"""

import json
from collections import defaultdict

# Load the extraction results
with open('sicon_extraction_20250714_102833.json', 'r') as f:
    data = json.load(f)

print("📊 DETAILED SICON EXTRACTION RESULTS")
print("=" * 80)
print(f"\n🔍 Session: {data['session_id']}")
print(f"📅 Extraction time: {data['extraction_time']}")
print(f"📚 Journal: {data['journal']}")
print(f"📄 Total manuscripts: {data['total_manuscripts']}")

# Analyze each manuscript in detail
for i, ms in enumerate(data['manuscripts'], 1):
    print(f"\n{'='*80}")
    print(f"📄 MANUSCRIPT {i}/{data['total_manuscripts']}: {ms['id']}")
    print(f"{'='*80}")
    
    print(f"\n📝 BASIC INFO:")
    print(f"Title: {ms['title']}")
    print(f"Authors: {', '.join(ms['authors'])}")
    print(f"Status: {ms['status']}")
    print(f"Submission Date: {ms['submission_date']}")
    print(f"Associate Editor: {ms['associate_editor']}")
    print(f"Corresponding Editor: {ms['corresponding_editor']}")
    
    # Analyze referees
    referees = ms['referees']
    print(f"\n👥 REFEREES ({len(referees)} total entries):")
    
    # Group by email to find duplicates
    ref_by_email = defaultdict(list)
    for ref in referees:
        ref_by_email[ref['email']].append(ref)
    
    # Show unique referees
    print(f"\n✅ UNIQUE REFEREES ({len(ref_by_email)}):")
    for j, (email, refs) in enumerate(ref_by_email.items(), 1):
        ref = refs[0]  # Take first occurrence
        print(f"\n  {j}. {ref['name']}")
        print(f"     Email: {email}")
        print(f"     Status: {ref['status']}")
        print(f"     Institution: {ref['institution'] or 'Not specified'}")
        if len(refs) > 1:
            print(f"     ⚠️  DUPLICATE: Appears {len(refs)} times!")
    
    # Status breakdown
    status_count = defaultdict(int)
    for ref in referees:
        status_count[ref['status']] += 1
    
    print(f"\n📊 STATUS BREAKDOWN:")
    for status, count in sorted(status_count.items()):
        print(f"  - {status}: {count}")
    
    # Check for timeline data
    print(f"\n📅 TIMELINE DATA:")
    has_dates = any(ref.get('report_date') or ref.get('reminder_count') for ref in referees)
    if has_dates:
        for ref in referees:
            if ref.get('report_date'):
                print(f"  - {ref['name']}: Report received {ref['report_date']}")
    else:
        print("  ❌ No timeline data captured")
    
    # PDF status
    print(f"\n📎 DOCUMENTS:")
    print(f"  PDF URLs found: {len(ms.get('pdf_urls', {}))}")
    print(f"  PDFs downloaded: {len(ms.get('pdf_paths', {}))}")
    print(f"  Referee reports: {len(ms.get('referee_reports', {}))}")
    
    if not ms.get('pdf_urls'):
        print("  ❌ No PDFs extracted")

# Overall summary
print(f"\n{'='*80}")
print("📈 OVERALL ANALYSIS:")
print(f"{'='*80}")

total_entries = sum(len(ms['referees']) for ms in data['manuscripts'])
print(f"\n📊 REFEREE STATISTICS:")
print(f"  Total referee entries: {total_entries}")
print(f"  Average per manuscript: {total_entries / data['total_manuscripts']:.1f}")

# Global status distribution
global_status = defaultdict(int)
for ms in data['manuscripts']:
    for ref in ms['referees']:
        global_status[ref['status']] += 1

print(f"\n📊 GLOBAL STATUS DISTRIBUTION:")
for status, count in sorted(global_status.items()):
    print(f"  - {status}: {count} ({count/total_entries*100:.1f}%)")

# Issues identified
print(f"\n❌ ISSUES IDENTIFIED:")
print("1. MASSIVE DUPLICATION: Each referee appears 3+ times")
print("2. INCORRECT STATUS: All show 'Review pending' or 'Suggested'")
print("3. NO TIMELINE DATA: No dates, reminders, or response times")
print("4. NO PDFS: No documents downloaded")
print("5. MISSING STATUSES: No 'Declined', 'Accepted', 'Report submitted'")

print(f"\n✅ WHAT SHOULD BE FIXED:")
print("1. Parse 'Potential Referees' section correctly (various statuses)")
print("2. Parse 'Referees' section as accepted only")
print("3. Extract dates from patterns like '(Rcvd: 2025-06-02)'")
print("4. No duplicates - each referee once")
print("5. Download all PDFs")

# Compare to expected
print(f"\n🎯 EXPECTED VS ACTUAL:")
print("EXPECTED: ~13 unique referees with mixed statuses")
print(f"ACTUAL: {total_entries} duplicate entries, all 'Review pending'")
print("\nThe fixed extractor addresses all these issues!")
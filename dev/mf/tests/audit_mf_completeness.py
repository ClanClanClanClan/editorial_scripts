#!/usr/bin/env python3
"""Comprehensive audit of MF extractor to identify missing functionality."""

import sys
import os
import re
from collections import defaultdict

def audit_mf_extractor():
    """Audit MF extractor for missing or incomplete functionality."""

    print("🔍 COMPREHENSIVE MF EXTRACTOR AUDIT")
    print("=" * 80)

    # Read the MF extractor code
    mf_path = '../../../production/src/extractors/mf_extractor.py'
    with open(mf_path, 'r') as f:
        code = f.read()

    lines = code.split('\n')

    # Track what's being extracted
    extracted_fields = defaultdict(list)
    potential_issues = []

    # 1. REFEREE DATA EXTRACTION
    print("\n1️⃣ REFEREE DATA EXTRACTION:")
    print("-" * 60)

    referee_fields = [
        'recommendation',
        'report',
        'report_text',
        'report_pdf',
        'decision',
        'rating',
        'confidence',
        'review_date',
        'report_length',
        'report_quality'
    ]

    for field in referee_fields:
        pattern = f"referee\\['{field}'\\]|referee\\.get\\('{field}'|'{field}':"
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                matches.append(i)

        if matches:
            print(f"   ✅ {field}: Found at lines {matches[:3]}...")
            extracted_fields['referee'].append(field)
        else:
            print(f"   ❌ {field}: NOT FOUND")
            potential_issues.append(f"Referee {field} not extracted")

    # Check for recommendation extraction specifically
    print("\n   📌 Recommendation Extraction Deep Dive:")
    rec_patterns = [
        'recommendation',
        'decision',
        'accept',
        'reject',
        'revise',
        'minor revision',
        'major revision'
    ]
    for pattern in rec_patterns:
        count = sum(1 for line in lines if pattern.lower() in line.lower() and 'referee' in line.lower())
        if count > 0:
            print(f"      • '{pattern}' mentioned {count} times in referee context")

    # 2. DOCUMENT EXTRACTION
    print("\n2️⃣ DOCUMENT EXTRACTION:")
    print("-" * 60)

    document_types = [
        'manuscript_pdf',
        'cover_letter',
        'supplementary',
        'response_to_reviewers',
        'revised_manuscript',
        'track_changes',
        'latex_source',
        'figures'
    ]

    for doc_type in document_types:
        pattern = f"{doc_type}|'{doc_type}'|\"{doc_type}\""
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                matches.append(i)

        if matches:
            print(f"   ✅ {doc_type}: Found at lines {matches[:3]}...")
            extracted_fields['documents'].append(doc_type)
        else:
            print(f"   ❌ {doc_type}: NOT FOUND")
            potential_issues.append(f"Document type {doc_type} not extracted")

    # 3. TIMELINE/AUDIT TRAIL
    print("\n3️⃣ TIMELINE/AUDIT TRAIL:")
    print("-" * 60)

    timeline_fields = [
        'submission_date',
        'revision_date',
        'decision_date',
        'review_requested',
        'review_completed',
        'status_history',
        'audit_trail',
        'timeline',
        'events'
    ]

    for field in timeline_fields:
        pattern = f"{field}|'{field}'|\"{field}\""
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                matches.append(i)

        if matches:
            print(f"   ✅ {field}: Found at lines {matches[:3]}...")
            extracted_fields['timeline'].append(field)
        else:
            print(f"   ❌ {field}: NOT FOUND")
            potential_issues.append(f"Timeline field {field} not extracted")

    # 4. EMAIL EXTRACTION
    print("\n4️⃣ EMAIL EXTRACTION:")
    print("-" * 60)

    email_patterns = [
        'mailpopup',
        'email_popup',
        'extract_email',
        'click.*email',
        'popup.*email'
    ]

    for pattern in email_patterns:
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                matches.append(i)

        if matches:
            print(f"   ✅ {pattern}: Found at lines {matches[:3]}...")
        else:
            print(f"   ⚠️ {pattern}: Not found")

    # 5. METADATA EXTRACTION
    print("\n5️⃣ METADATA EXTRACTION:")
    print("-" * 60)

    metadata_fields = [
        'abstract',
        'keywords',
        'subject_areas',
        'classifications',
        'special_issue',
        'funding',
        'conflicts_of_interest',
        'data_availability'
    ]

    for field in metadata_fields:
        pattern = f"{field}|'{field}'|\"{field}\""
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                matches.append(i)

        if matches:
            print(f"   ✅ {field}: Found at lines {matches[:3]}...")
            extracted_fields['metadata'].append(field)
        else:
            print(f"   ❌ {field}: NOT FOUND")
            potential_issues.append(f"Metadata field {field} not extracted")

    # 6. ERROR HANDLING
    print("\n6️⃣ ERROR HANDLING & RECOVERY:")
    print("-" * 60)

    error_patterns = [
        'try:',
        'except',
        'timeout',
        'retry',
        'fallback'
    ]

    for pattern in error_patterns:
        count = sum(1 for line in lines if pattern in line)
        print(f"   • {pattern}: {count} occurrences")

    # 7. POPUP HANDLING
    print("\n7️⃣ POPUP HANDLING:")
    print("-" * 60)

    popup_patterns = [
        'switch_to.window',
        'window_handles',
        'close()',
        'popup',
        'new_window'
    ]

    for pattern in popup_patterns:
        count = sum(1 for line in lines if pattern in line.lower())
        print(f"   • {pattern}: {count} occurrences")

    # 8. DOWNLOADS
    print("\n8️⃣ FILE DOWNLOADS:")
    print("-" * 60)

    download_patterns = [
        'download',
        'pdf',
        'save',
        'write',
        'file'
    ]

    for pattern in download_patterns:
        count = sum(1 for line in lines if pattern in line.lower())
        print(f"   • {pattern}: {count} occurrences")

    # SUMMARY
    print("\n" + "=" * 80)
    print("📊 AUDIT SUMMARY")
    print("=" * 80)

    print(f"\n✅ EXTRACTED FIELDS:")
    for category, fields in extracted_fields.items():
        if fields:
            print(f"   {category}: {', '.join(fields)}")

    print(f"\n❌ POTENTIAL MISSING FUNCTIONALITY ({len(potential_issues)} issues):")
    for issue in potential_issues[:10]:  # Show top 10
        print(f"   • {issue}")

    # Specific checks
    print("\n🎯 CRITICAL CHECKS:")

    # Check if referee recommendations are extracted
    rec_extraction = any('recommendation' in line.lower() and 'referee' in line.lower() for line in lines)
    if rec_extraction:
        print("   ✅ Referee recommendations appear to be extracted")
    else:
        print("   ❌ CRITICAL: Referee recommendations NOT being extracted!")

    # Check if reports are downloaded
    report_download = any('download' in line.lower() and 'report' in line.lower() for line in lines)
    if report_download:
        print("   ✅ Referee reports appear to be downloaded")
    else:
        print("   ⚠️ WARNING: Referee report downloads may be incomplete")

    # Check if timeline is extracted
    timeline_extraction = any('timeline' in line.lower() or 'audit' in line.lower() for line in lines)
    if timeline_extraction:
        print("   ✅ Timeline/audit trail appears to be extracted")
    else:
        print("   ❌ CRITICAL: Timeline/audit trail NOT being extracted!")

    # Check if emails are extracted from popups
    email_popup_extraction = any('mailpopup' in line.lower() for line in lines)
    if email_popup_extraction:
        print("   ✅ Email popup extraction implemented")
    else:
        print("   ❌ CRITICAL: Email popup extraction NOT implemented!")

    # Check for abstract extraction
    abstract_extraction = any('abstract' in line.lower() for line in lines)
    if abstract_extraction:
        print("   ✅ Abstract extraction implemented")
    else:
        print("   ❌ CRITICAL: Abstract NOT being extracted!")

    print("\n🔥 TOP PRIORITIES TO FIX:")
    priorities = []

    if not rec_extraction:
        priorities.append("1. Implement referee recommendation extraction")
    if not timeline_extraction:
        priorities.append("2. Implement timeline/audit trail extraction")
    if not abstract_extraction:
        priorities.append("3. Implement abstract extraction")
    if 'supplementary' not in str(extracted_fields['documents']):
        priorities.append("4. Implement supplementary file downloads")
    if 'response_to_reviewers' not in str(extracted_fields['documents']):
        priorities.append("5. Implement response to reviewers extraction")

    for priority in priorities:
        print(f"   {priority}")

    if not priorities:
        print("   ✅ All major components appear to be implemented!")

    return potential_issues

if __name__ == "__main__":
    issues = audit_mf_extractor()
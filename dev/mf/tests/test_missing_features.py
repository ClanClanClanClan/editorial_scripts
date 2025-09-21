#!/usr/bin/env python3
"""Test for missing features in MF extractor based on audit."""

import sys
import os
import json
from datetime import datetime

def analyze_missing_features():
    """Analyze what's missing or potentially broken in MF extractor."""

    print("🔍 MF EXTRACTOR - MISSING FEATURES ANALYSIS")
    print("=" * 80)

    # Read the MF extractor code for deeper analysis
    mf_path = '../../../production/src/extractors/mf_extractor.py'
    with open(mf_path, 'r') as f:
        code = f.read()

    lines = code.split('\n')

    print("\n📊 CRITICAL FEATURE ANALYSIS:")
    print("=" * 80)

    # 1. REFEREE REPORT RECOMMENDATIONS
    print("\n1️⃣ REFEREE REPORT RECOMMENDATIONS:")
    print("-" * 60)

    # Check where recommendations are stored
    rec_storage_locations = []
    for i, line in enumerate(lines, 1):
        if "['recommendation']" in line or "['recommendation']" in line:
            context = lines[i-2:i+2] if i > 2 else lines[:i+2]
            rec_storage_locations.append({
                'line': i,
                'code': line.strip(),
                'context': '\n'.join(context)
            })

    print(f"   Found {len(rec_storage_locations)} recommendation storage locations")

    # Check extraction methods
    rec_extraction_methods = [
        'extract_recommendation_from_text',
        'parse_recommendation_from_popup',
        'normalize_recommendation',
        'is_valid_recommendation'
    ]

    for method in rec_extraction_methods:
        found = any(method in line for line in lines)
        status = "✅" if found else "❌"
        print(f"   {status} Method: {method}")

    # Check if recommendations are extracted from popups
    popup_rec_extraction = False
    for i, line in enumerate(lines, 1):
        if 'popup' in line.lower() and 'recommendation' in line.lower():
            popup_rec_extraction = True
            break

    if popup_rec_extraction:
        print("   ✅ Popup recommendation extraction implemented")
    else:
        print("   ❌ Popup recommendation extraction NOT implemented")

    # 2. REFEREE REPORT FULL TEXT
    print("\n2️⃣ REFEREE REPORT FULL TEXT EXTRACTION:")
    print("-" * 60)

    # Check for text extraction methods
    text_extraction_methods = [
        'extract_text_from_pdf',
        'comments_to_author',
        'comments_to_editor',
        'review_text'
    ]

    for method in text_extraction_methods:
        count = sum(1 for line in lines if method in line)
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {method}: {count} occurrences")

    # 3. DOCUMENT DOWNLOADS
    print("\n3️⃣ DOCUMENT DOWNLOADS:")
    print("-" * 60)

    document_types = {
        'manuscript_pdf': 'Main manuscript PDF',
        'cover_letter': 'Cover letter',
        'supplementary': 'Supplementary materials',
        'referee_report': 'Referee reports',
        'response_to_reviewers': 'Response to reviewers',
        'revised_manuscript': 'Revised manuscripts'
    }

    for doc_type, description in document_types.items():
        # Check if download is implemented
        download_implemented = any(f"download.*{doc_type}" in line.lower() or f"{doc_type}.*download" in line.lower() for line in lines)
        # Check if it's mentioned at all
        mentioned = any(doc_type in line.lower() for line in lines)

        if download_implemented:
            print(f"   ✅ {description}: Download implemented")
        elif mentioned:
            print(f"   ⚠️ {description}: Mentioned but download unclear")
        else:
            print(f"   ❌ {description}: Not implemented")

    # 4. TIMELINE/AUDIT TRAIL
    print("\n4️⃣ TIMELINE/AUDIT TRAIL:")
    print("-" * 60)

    timeline_features = [
        'extract_timeline',
        'extract_audit_trail',
        'timeline_data',
        'status_history',
        'events'
    ]

    for feature in timeline_features:
        count = sum(1 for line in lines if feature in line.lower())
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {feature}: {count} occurrences")

    # 5. EMAIL EXTRACTION FROM POPUPS
    print("\n5️⃣ EMAIL EXTRACTION FROM POPUPS:")
    print("-" * 60)

    # Check mailpopup handling
    mailpopup_count = sum(1 for line in lines if 'mailpopup' in line.lower())
    email_extraction_count = sum(1 for line in lines if 'extract_email' in line.lower())
    popup_email_count = sum(1 for line in lines if 'popup' in line.lower() and 'email' in line.lower())

    print(f"   • Mailpopup references: {mailpopup_count}")
    print(f"   • Extract email functions: {email_extraction_count}")
    print(f"   • Popup email handling: {popup_email_count}")

    if mailpopup_count > 10:
        print("   ✅ Email popup extraction appears implemented")
    else:
        print("   ⚠️ Email popup extraction may be incomplete")

    # 6. ABSTRACT AND KEYWORDS
    print("\n6️⃣ ABSTRACT AND KEYWORDS:")
    print("-" * 60)

    abstract_count = sum(1 for line in lines if 'abstract' in line.lower())
    keywords_count = sum(1 for line in lines if 'keywords' in line.lower())

    print(f"   • Abstract extraction: {abstract_count} references")
    print(f"   • Keywords extraction: {keywords_count} references")

    if abstract_count > 5:
        print("   ✅ Abstract extraction implemented")
    else:
        print("   ❌ Abstract extraction NOT implemented")

    if keywords_count > 5:
        print("   ✅ Keywords extraction implemented")
    else:
        print("   ❌ Keywords extraction NOT implemented")

    # SUMMARY OF MISSING FEATURES
    print("\n" + "=" * 80)
    print("🔥 CRITICAL MISSING/BROKEN FEATURES:")
    print("=" * 80)

    missing_features = []

    # Check specific critical features
    if not any("referee['report']['recommendation']" in line or "report_data['recommendation']" in line for line in lines):
        missing_features.append("❌ Referee recommendations not properly stored in referee objects")

    if not any("response_to_reviewers" in line.lower() for line in lines):
        missing_features.append("❌ Response to reviewers document not extracted")

    if not any("revised_manuscript" in line.lower() for line in lines):
        missing_features.append("❌ Revised manuscript versions not tracked")

    if not any("track_changes" in line.lower() for line in lines):
        missing_features.append("❌ Track changes documents not extracted")

    if not any("latex" in line.lower() and "source" in line.lower() for line in lines):
        missing_features.append("❌ LaTeX source files not extracted")

    if abstract_count < 5:
        missing_features.append("❌ Abstract extraction not properly implemented")

    if not any("report_text" in line or "review_text" in line for line in lines):
        missing_features.append("⚠️ Full referee report text may not be extracted")

    # Check if timeline is properly extracted
    timeline_extraction = any('extract_timeline' in line for line in lines)
    if not timeline_extraction:
        missing_features.append("⚠️ Timeline extraction method not found")

    if missing_features:
        for feature in missing_features:
            print(f"   {feature}")
    else:
        print("   ✅ All critical features appear to be implemented!")

    # RECOMMENDATIONS
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS FOR IMPROVEMENT:")
    print("=" * 80)

    recommendations = [
        "1. Verify referee recommendations are being stored in referee['report']['recommendation']",
        "2. Implement extraction of response to reviewers documents",
        "3. Track revised manuscript versions and changes",
        "4. Extract LaTeX source files when available",
        "5. Ensure abstract is extracted and stored properly",
        "6. Verify full referee report text is captured (not just PDFs)",
        "7. Test timeline/audit trail extraction thoroughly"
    ]

    for rec in recommendations:
        print(f"   {rec}")

    return missing_features

if __name__ == "__main__":
    missing = analyze_missing_features()
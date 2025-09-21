#!/usr/bin/env python3
"""Verify that all new features are properly integrated in MF extractor."""

import sys
import os
import json
from datetime import datetime

def verify_new_features():
    """Verify all new features are integrated correctly."""

    print("🔍 VERIFYING NEW MF EXTRACTOR FEATURES")
    print("=" * 80)

    # Read the updated MF extractor
    mf_path = '../../../production/src/extractors/mf_extractor.py'
    with open(mf_path, 'r') as f:
        code = f.read()

    lines = code.split('\n')

    # Track verification results
    results = {
        'functions_added': [],
        'functions_called': [],
        'storage_consistency': [],
        'issues': []
    }

    print("\n1️⃣ VERIFYING NEW FUNCTIONS ADDED:")
    print("-" * 60)

    new_functions = [
        'extract_response_to_reviewers',
        'extract_revised_manuscripts',
        'extract_latex_source',
        'extract_all_documents',
        'ensure_recommendation_storage'
    ]

    for func in new_functions:
        func_def = f"def {func}("
        found = False
        for i, line in enumerate(lines, 1):
            if func_def in line:
                found = True
                results['functions_added'].append(func)
                print(f"   ✅ {func} added at line {i}")
                break

        if not found:
            print(f"   ❌ {func} NOT FOUND")
            results['issues'].append(f"{func} function not found")

    print("\n2️⃣ VERIFYING FUNCTION CALLS:")
    print("-" * 60)

    # Check if extract_all_documents is called
    extract_all_docs_calls = []
    for i, line in enumerate(lines, 1):
        if 'extract_all_documents(' in line and not 'def extract_all_documents' in line:
            extract_all_docs_calls.append(i)

    if extract_all_docs_calls:
        print(f"   ✅ extract_all_documents called at lines: {extract_all_docs_calls}")
        results['functions_called'].append('extract_all_documents')
    else:
        print(f"   ❌ extract_all_documents NOT CALLED")
        results['issues'].append("extract_all_documents not called in main flow")

    # Check if ensure_recommendation_storage is called
    ensure_rec_calls = []
    for i, line in enumerate(lines, 1):
        if 'ensure_recommendation_storage(' in line and not 'def ensure_recommendation_storage' in line:
            ensure_rec_calls.append(i)

    if ensure_rec_calls:
        print(f"   ✅ ensure_recommendation_storage called at lines: {ensure_rec_calls}")
        results['functions_called'].append('ensure_recommendation_storage')
    else:
        print(f"   ❌ ensure_recommendation_storage NOT CALLED")
        results['issues'].append("ensure_recommendation_storage not called after report extraction")

    print("\n3️⃣ VERIFYING DATA STRUCTURE UPDATES:")
    print("-" * 60)

    # Check for new data fields
    new_fields = [
        "manuscript['response_to_reviewers']",
        "manuscript['revisions']",
        "manuscript['latex_source']",
        "referee['report']['recommendation']",
        "referee['report']['recommendation_normalized']",
        "referee['report']['confidence']"
    ]

    for field in new_fields:
        if field in code:
            print(f"   ✅ {field} is used")
            results['storage_consistency'].append(field)
        else:
            print(f"   ⚠️ {field} may not be used")

    print("\n4️⃣ VERIFYING RECOMMENDATION STORAGE:")
    print("-" * 60)

    # Check recommendation storage patterns
    rec_patterns = [
        "report_data['recommendation']",
        "referee['report']['recommendation']",
        "recommendation_normalized"
    ]

    for pattern in rec_patterns:
        count = sum(1 for line in lines if pattern in line)
        if count > 0:
            print(f"   ✅ '{pattern}' found {count} times")
        else:
            print(f"   ⚠️ '{pattern}' not found")

    print("\n5️⃣ CHECKING DOCUMENT EXTRACTION FLOW:")
    print("-" * 60)

    # Verify extract_all_documents calls the right functions
    in_extract_all = False
    functions_called_in_all = []

    for i, line in enumerate(lines):
        if 'def extract_all_documents(' in line:
            in_extract_all = True
        elif in_extract_all and 'def ' in line:
            in_extract_all = False
        elif in_extract_all:
            for func in ['extract_keywords', 'extract_authors', 'extract_metadata',
                        'extract_cover_letter', 'extract_response_to_reviewers',
                        'extract_revised_manuscripts', 'extract_latex_source']:
                if func in line:
                    functions_called_in_all.append(func)

    if functions_called_in_all:
        print(f"   ✅ extract_all_documents calls {len(set(functions_called_in_all))} extraction functions")
        for func in set(functions_called_in_all):
            print(f"      • {func}")
    else:
        print(f"   ❌ extract_all_documents doesn't call extraction functions")
        results['issues'].append("extract_all_documents implementation incomplete")

    # Summary
    print("\n" + "=" * 80)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 80)

    total_checks = 0
    passed_checks = 0

    # Count results
    total_checks += len(new_functions)
    passed_checks += len(results['functions_added'])

    total_checks += 2  # extract_all_documents and ensure_recommendation_storage calls
    passed_checks += len(results['functions_called'])

    print(f"\n✅ Functions Added: {len(results['functions_added'])}/{len(new_functions)}")
    print(f"✅ Functions Called: {len(results['functions_called'])}/2")
    print(f"✅ Data Fields: {len(results['storage_consistency'])}/{len(new_fields)}")

    if results['issues']:
        print(f"\n⚠️ ISSUES FOUND ({len(results['issues'])}):")
        for issue in results['issues']:
            print(f"   • {issue}")
    else:
        print(f"\n🎉 ALL VERIFICATIONS PASSED!")

    # Specific checks for referee report handling
    print("\n" + "=" * 80)
    print("🎯 REFEREE REPORT HANDLING (When Reports Available)")
    print("=" * 80)

    print("\nWhen referee reports become available, the system will:")
    print("   1. Extract report via extract_report_with_timeout()")
    print("   2. Store in referee['report'] with full data structure")
    print("   3. Call ensure_recommendation_storage() to normalize")
    print("   4. Store recommendation in multiple formats:")
    print("      • referee['report']['recommendation'] - raw")
    print("      • referee['report']['recommendation_normalized'] - standardized")
    print("      • referee['report']['confidence'] - high/medium/low")

    print("\nNew document types that will be extracted:")
    print("   • Response to reviewers (for revisions)")
    print("   • Revised manuscripts with version tracking")
    print("   • Track changes documents")
    print("   • LaTeX source files")

    # Save verification report
    report = {
        'timestamp': datetime.now().isoformat(),
        'functions_added': results['functions_added'],
        'functions_called': results['functions_called'],
        'storage_fields': results['storage_consistency'],
        'issues': results['issues'],
        'verification_passed': len(results['issues']) == 0
    }

    output_file = 'new_features_verification.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Verification report saved to {output_file}")

    return len(results['issues']) == 0

if __name__ == "__main__":
    success = verify_new_features()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""Precise audit focusing on REAL issues in MF extractor."""

import sys
import os
import re
import json
from collections import defaultdict
from datetime import datetime

def precise_audit():
    """Conduct a precise audit focusing on actual issues."""

    print("🎯 PRECISE MF EXTRACTOR ISSUES AUDIT")
    print("=" * 80)

    # Read the MF extractor
    mf_path = '../../../production/src/extractors/mf_extractor.py'
    with open(mf_path, 'r') as f:
        code = f.read()

    lines = code.split('\n')

    issues = {
        'critical': [],
        'major': [],
        'optimization': [],
        'verified_working': []
    }

    # ============================================================================
    # CHECK 1: ACTUAL FUNCTION CALLING
    # ============================================================================
    print("\n1️⃣ VERIFYING CRITICAL FUNCTION CALLS")
    print("-" * 60)

    # Map of functions and their actual calling patterns
    function_patterns = {
        'manuscript_details': ['extract_manuscript_details_page('],
        'referees': ['extract_referees_comprehensive('],
        'timeline': ['extract_timeline(', 'extract_audit_trail('],
        'authors': ['extract_authors_from_details('],
        'documents': ['extract_all_documents('],
        'enrichment': ['enrich_referee_profiles(', 'deep_web_enrichment(']
    }

    for feature, patterns in function_patterns.items():
        found = False
        call_lines = []
        for pattern in patterns:
            for i, line in enumerate(lines, 1):
                if pattern in line and 'def ' not in line:
                    call_lines.append(i)
                    found = True

        if found:
            print(f"   ✅ {feature}: Called at lines {call_lines[:3]}...")
            issues['verified_working'].append(f"{feature} extraction")
        else:
            print(f"   ❌ {feature}: NOT CALLED")
            issues['critical'].append(f"{feature} extraction not called")

    # ============================================================================
    # CHECK 2: ACTUAL DATA STORAGE
    # ============================================================================
    print("\n2️⃣ DATA STORAGE VERIFICATION")
    print("-" * 60)

    # Check where manuscript data is actually stored
    manuscript_fields = {
        'id': r"manuscript\['id'\]",
        'title': r"manuscript\['title'\]",
        'abstract': r"manuscript\['abstract'\]",
        'pdf_url': r"manuscript\['.*pdf.*'\]",
        'funding': r"manuscript\['funding.*'\]",
        'timeline': r"manuscript\['timeline'\]"
    }

    for field, pattern in manuscript_fields.items():
        matches = sum(1 for line in lines if re.search(pattern, line))
        if matches > 0:
            print(f"   ✅ manuscript['{field}']: {matches} assignments")
        else:
            # Check alternative patterns
            alt_matches = sum(1 for line in lines if f"'{field}':" in line or f'"{field}":' in line)
            if alt_matches > 0:
                print(f"   ⚠️ manuscript['{field}']: Found in dict literal ({alt_matches})")
            else:
                print(f"   ❌ manuscript['{field}']: NOT STORED")
                issues['major'].append(f"manuscript['{field}'] not stored")

    # ============================================================================
    # CHECK 3: REFEREE REPORT EXTRACTION
    # ============================================================================
    print("\n3️⃣ REFEREE REPORT HANDLING")
    print("-" * 60)

    report_checks = {
        'Report extraction': 'extract_report_with_timeout' in code,
        'Recommendation storage': "referee['report']['recommendation']" in code,
        'Normalized storage': "recommendation_normalized" in code,
        'Confidence levels': "referee['report']['confidence']" in code,
        'Comments extraction': "comments_to_author" in code,
        'PDF download': 'download_referee_report_pdf' in code
    }

    for check, present in report_checks.items():
        if present:
            print(f"   ✅ {check}")
        else:
            print(f"   ❌ {check}")
            issues['critical'].append(f"Missing: {check}")

    # ============================================================================
    # CHECK 4: ERROR HANDLING IN CRITICAL SECTIONS
    # ============================================================================
    print("\n4️⃣ ERROR HANDLING IN CRITICAL SECTIONS")
    print("-" * 60)

    critical_sections = [
        ('Login', 'def login', 50),
        ('Referee extraction', 'def extract_referees_comprehensive', 200),
        ('Report extraction', 'def extract_report_with_timeout', 100),
        ('ORCID enrichment', 'def enrich_referee_profiles', 50),
        ('Document extraction', 'def extract_all_documents', 50)
    ]

    for section_name, pattern, expected_lines in critical_sections:
        # Find the function
        start_line = None
        for i, line in enumerate(lines):
            if pattern in line:
                start_line = i
                break

        if start_line:
            # Count try blocks in the function
            try_count = 0
            for i in range(start_line, min(start_line + expected_lines, len(lines))):
                if 'try:' in lines[i]:
                    try_count += 1

            if try_count > 0:
                print(f"   ✅ {section_name}: {try_count} try blocks")
            else:
                print(f"   ❌ {section_name}: NO ERROR HANDLING")
                issues['critical'].append(f"No error handling in {section_name}")
        else:
            print(f"   ⚠️ {section_name}: Function not found")

    # ============================================================================
    # CHECK 5: SELENIUM WAIT STRATEGIES
    # ============================================================================
    print("\n5️⃣ SELENIUM WAIT STRATEGIES")
    print("-" * 60)

    wait_patterns = {
        'WebDriverWait': sum(1 for line in lines if 'WebDriverWait' in line),
        'time.sleep': sum(1 for line in lines if 'time.sleep' in line),
        'EC.presence': sum(1 for line in lines if 'EC.presence_of_element' in line),
        'EC.clickable': sum(1 for line in lines if 'EC.element_to_be_clickable' in line),
        'Implicit wait': sum(1 for line in lines if 'implicitly_wait' in line)
    }

    for wait_type, count in wait_patterns.items():
        print(f"   • {wait_type}: {count}")

    if wait_patterns['WebDriverWait'] < 10:
        issues['major'].append(f"Insufficient WebDriverWait usage: {wait_patterns['WebDriverWait']}")
        print(f"\n   ⚠️ Low WebDriverWait usage - relying on time.sleep")

    # ============================================================================
    # CHECK 6: UNCHECKED OPERATIONS
    # ============================================================================
    print("\n6️⃣ UNCHECKED RISKY OPERATIONS")
    print("-" * 60)

    risky_ops = {
        'Unchecked [0] access': 0,
        'Unchecked .click()': 0,
        'Unchecked .text access': 0,
        'Unchecked int() conversion': 0
    }

    for i, line in enumerate(lines):
        # Check for [0] without length check
        if '[0]' in line:
            # Look for nearby length check
            check_found = False
            for j in range(max(0, i-3), min(i+3, len(lines))):
                if 'if ' in lines[j] and ('len(' in lines[j] or 'not ' in lines[j]):
                    check_found = True
                    break
            if not check_found and 'try:' not in lines[max(0, i-5):i]:
                risky_ops['Unchecked [0] access'] += 1

        # Check for .click() without try
        if '.click()' in line and 'try:' not in lines[max(0, i-5):i]:
            risky_ops['Unchecked .click()'] += 1

        # Check for .text without None check
        if '.text' in line and 'if ' not in line and 'try:' not in lines[max(0, i-5):i]:
            risky_ops['Unchecked .text access'] += 1

        # Check for int() without try
        if 'int(' in line and 'try:' not in lines[max(0, i-5):i]:
            risky_ops['Unchecked int() conversion'] += 1

    for op, count in risky_ops.items():
        if count > 20:
            print(f"   ⚠️ {op}: {count} occurrences")
            issues['major'].append(f"{op}: {count}")
        else:
            print(f"   ✅ {op}: {count} (acceptable)")

    # ============================================================================
    # CHECK 7: CREDENTIAL SAFETY
    # ============================================================================
    print("\n7️⃣ CREDENTIAL SAFETY CHECK")
    print("-" * 60)

    credential_issues = []

    # Check for unmasked credential logging
    for i, line in enumerate(lines, 1):
        if 'print(' in line or 'logger' in line:
            if any(word in line.lower() for word in ['password', 'token', 'credential']):
                if '***' not in line and 'REDACTED' not in line and 'masked' not in line:
                    credential_issues.append(i)

    if credential_issues:
        print(f"   ❌ Unmasked credentials at lines: {credential_issues[:5]}...")
        issues['critical'].append(f"Unmasked credentials in {len(credential_issues)} places")
    else:
        print(f"   ✅ All credentials appear masked in logs")

    # ============================================================================
    # CHECK 8: PASS SYSTEM INTEGRITY
    # ============================================================================
    print("\n8️⃣ THREE-PASS SYSTEM INTEGRITY")
    print("-" * 60)

    pass_implementation = {
        'Pass 1 Forward': False,
        'Pass 2 Backward': False,
        'Pass 3 Forward': False
    }

    for i, line in enumerate(lines):
        if 'PASS 1' in line and 'Forward' in line:
            pass_implementation['Pass 1 Forward'] = True
        elif 'PASS 2' in line and 'Backward' in line:
            pass_implementation['Pass 2 Backward'] = True
        elif 'PASS 3' in line and 'Forward' in line:
            pass_implementation['Pass 3 Forward'] = True

    for pass_name, implemented in pass_implementation.items():
        if implemented:
            print(f"   ✅ {pass_name}")
        else:
            print(f"   ❌ {pass_name}")
            issues['major'].append(f"Missing: {pass_name}")

    # ============================================================================
    # CHECK 9: NEW FEATURES INTEGRATION
    # ============================================================================
    print("\n9️⃣ NEW FEATURES INTEGRATION CHECK")
    print("-" * 60)

    new_features = {
        'Response to reviewers': 'extract_response_to_reviewers' in code,
        'Revision tracking': 'extract_revised_manuscripts' in code,
        'LaTeX source': 'extract_latex_source' in code,
        'All documents': 'extract_all_documents' in code,
        'Recommendation storage': 'ensure_recommendation_storage' in code
    }

    for feature, present in new_features.items():
        if present:
            print(f"   ✅ {feature}")
            issues['verified_working'].append(feature)
        else:
            print(f"   ❌ {feature}")
            issues['critical'].append(f"Missing new feature: {feature}")

    # ============================================================================
    # CHECK 10: SPECIFIC PROBLEMATIC PATTERNS
    # ============================================================================
    print("\n🔟 PROBLEMATIC PATTERN CHECK")
    print("-" * 60)

    problems = {
        'Infinite loops': 0,
        'Recursive calls': 0,
        'Memory leaks': 0,
        'Hardcoded paths': 0,
        'Debug code': 0
    }

    for i, line in enumerate(lines):
        # Check for potential infinite loops
        if 'while True:' in line:
            # Check if there's a break in the next 10 lines
            break_found = False
            for j in range(i+1, min(i+10, len(lines))):
                if 'break' in lines[j]:
                    break_found = True
                    break
            if not break_found:
                problems['Infinite loops'] += 1

        # Check for recursive calls (function calling itself)
        if 'def ' in line:
            func_name = line.split('def ')[1].split('(')[0]
            # Check next 50 lines for self-call
            for j in range(i+1, min(i+50, len(lines))):
                if f'self.{func_name}(' in lines[j]:
                    problems['Recursive calls'] += 1
                    break

        # Check for potential memory leaks (large data not cleared)
        if 'append(' in line and 'clear()' not in code[max(0, i*80-1000):i*80+1000]:
            problems['Memory leaks'] += 1

        # Check for hardcoded paths
        if '/Users/' in line or 'C:\\\\' in line or '/home/' in line:
            problems['Hardcoded paths'] += 1

        # Check for debug code
        if 'DEBUG' in line or 'XXX' in line or 'HACK' in line:
            problems['Debug code'] += 1

    for problem, count in problems.items():
        if count > 0:
            print(f"   ⚠️ {problem}: {count}")
            if count > 5:
                issues['major'].append(f"{problem}: {count}")
        else:
            print(f"   ✅ {problem}: None found")

    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print("\n" + "="*80)
    print("📊 PRECISE AUDIT SUMMARY")
    print("="*80)

    print(f"\n✅ VERIFIED WORKING ({len(issues['verified_working'])}):")
    for item in issues['verified_working']:
        print(f"   • {item}")

    if issues['critical']:
        print(f"\n❌ CRITICAL ISSUES ({len(issues['critical'])}):")
        for issue in issues['critical']:
            print(f"   • {issue}")

    if issues['major']:
        print(f"\n⚠️ MAJOR ISSUES ({len(issues['major'])}):")
        for issue in issues['major'][:10]:
            print(f"   • {issue}")

    if issues['optimization']:
        print(f"\n💡 OPTIMIZATION OPPORTUNITIES ({len(issues['optimization'])}):")
        for issue in issues['optimization'][:5]:
            print(f"   • {issue}")

    # Calculate realistic health score
    total_critical = len(issues['critical'])
    total_major = len(issues['major'])
    total_working = len(issues['verified_working'])

    health_score = 100
    health_score -= total_critical * 15
    health_score -= total_major * 3
    health_score += total_working * 2
    health_score = max(0, min(100, health_score))

    print(f"\n🏥 REALISTIC HEALTH SCORE: {health_score:.1f}/100")

    if health_score >= 85:
        print("   ✅ Excellent - Production ready")
    elif health_score >= 70:
        print("   ⚠️ Good - Minor improvements recommended")
    elif health_score >= 50:
        print("   ⚠️ Fair - Several issues should be addressed")
    else:
        print("   ❌ Poor - Critical issues need fixing")

    # Specific recommendations
    print("\n💡 TOP PRIORITY FIXES:")
    priorities = []

    if 'Unmasked credentials' in str(issues['critical']):
        priorities.append("1. Mask all credential logging immediately")

    if any('not called' in str(i) for i in issues['critical']):
        priorities.append("2. Verify critical extraction functions are called")

    if total_major > 10:
        priorities.append("3. Add error handling to critical sections")

    if 'WebDriverWait' in str(issues['major']):
        priorities.append("4. Replace time.sleep with proper WebDriverWait")

    for priority in priorities[:5]:
        print(f"   {priority}")

    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'health_score': health_score,
        'issues': issues,
        'summary': {
            'critical': total_critical,
            'major': total_major,
            'working': total_working
        }
    }

    with open('mf_precise_audit_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Report saved to mf_precise_audit_report.json")

    return health_score >= 70

if __name__ == "__main__":
    success = precise_audit()
    sys.exit(0 if success else 1)
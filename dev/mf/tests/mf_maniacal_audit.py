#!/usr/bin/env python3
"""Maniacally precise audit of MF extractor - checking EVERYTHING."""

import sys
import os
import re
import ast
import json
from collections import defaultdict, Counter
from datetime import datetime

def maniacal_audit():
    """Conduct an extremely thorough audit of the MF extractor."""

    print("🔬 MANIACALLY PRECISE MF EXTRACTOR AUDIT")
    print("=" * 80)
    print("⚠️ This audit will check EVERYTHING with obsessive precision")
    print("=" * 80)

    # Read the MF extractor
    mf_path = '../../../production/src/extractors/mf_extractor.py'
    with open(mf_path, 'r') as f:
        code = f.read()

    lines = code.split('\n')

    # Initialize audit report
    audit_report = {
        'timestamp': datetime.now().isoformat(),
        'total_lines': len(lines),
        'issues': {
            'critical': [],
            'major': [],
            'minor': [],
            'optimization': []
        },
        'statistics': {},
        'data_fields': defaultdict(list),
        'function_calls': defaultdict(int),
        'error_handling': defaultdict(list)
    }

    print(f"\n📏 Code Statistics:")
    print(f"   • Total lines: {len(lines)}")
    print(f"   • Non-empty lines: {len([l for l in lines if l.strip()])}")
    print(f"   • Comment lines: {len([l for l in lines if l.strip().startswith('#')])}")

    # Parse AST for deep analysis
    tree = ast.parse(code)

    # ============================================================================
    # SECTION 1: FUNCTION ANALYSIS
    # ============================================================================
    print("\n" + "="*80)
    print("1️⃣ FUNCTION ANALYSIS")
    print("="*80)

    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = {
                'line': node.lineno,
                'args': len(node.args.args),
                'returns': any(isinstance(n, ast.Return) for n in ast.walk(node)),
                'try_blocks': sum(1 for n in ast.walk(node) if isinstance(n, ast.Try)),
                'lines': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
            }

    print(f"\n📊 Found {len(functions)} functions")

    # Check for missing return statements
    no_return_funcs = [name for name, info in functions.items()
                       if not info['returns'] and not name.startswith('__')]
    if no_return_funcs:
        print(f"\n⚠️ Functions without return statements ({len(no_return_funcs)}):")
        for func in no_return_funcs[:5]:
            print(f"   • {func}")
        audit_report['issues']['minor'].extend([f"No return: {f}" for f in no_return_funcs])

    # Check for functions without error handling
    no_try_funcs = [name for name, info in functions.items()
                    if info['try_blocks'] == 0 and info['lines'] > 10]
    if no_try_funcs:
        print(f"\n⚠️ Large functions without try blocks ({len(no_try_funcs)}):")
        for func in no_try_funcs[:5]:
            print(f"   • {func} ({functions[func]['lines']} lines)")
        audit_report['issues']['major'].extend([f"No error handling: {f}" for f in no_try_funcs[:10]])

    # ============================================================================
    # SECTION 2: DATA EXTRACTION COMPLETENESS
    # ============================================================================
    print("\n" + "="*80)
    print("2️⃣ DATA EXTRACTION COMPLETENESS AUDIT")
    print("="*80)

    expected_fields = {
        'manuscript': [
            'id', 'title', 'abstract', 'keywords', 'status', 'submission_date',
            'authors', 'referees', 'editor', 'special_issue', 'funding',
            'data_availability', 'cover_letter_url', 'manuscript_pdf',
            'supplementary_files', 'timeline', 'audit_trail', 'decision',
            'response_to_reviewers', 'revisions', 'latex_source',
            'referee_recommendations', 'editor_recommendations'
        ],
        'referee': [
            'name', 'email', 'institution', 'department', 'role', 'country',
            'orcid', 'status', 'dates', 'report', 'affiliation',
            'publications', 'research_interests', 'publication_metrics'
        ],
        'author': [
            'name', 'email', 'institution', 'department', 'role', 'country',
            'orcid', 'is_corresponding', 'affiliation', 'publications'
        ],
        'report': [
            'recommendation', 'recommendation_normalized', 'confidence',
            'comments_to_author', 'comments_to_editor', 'pdf_files',
            'review_date', 'review_scores', 'text_content'
        ]
    }

    for entity, fields in expected_fields.items():
        print(f"\n📋 {entity.upper()} fields:")
        for field in fields:
            # Check different patterns for field assignment
            patterns = [
                f"{entity}['{field}']",
                f"{entity}['{field}']",
                f"{entity}.get('{field}'",
                f"'{field}':",
                f'"{field}":'
            ]

            found = False
            count = 0
            for pattern in patterns:
                count += sum(1 for line in lines if pattern in line)
                if count > 0:
                    found = True

            if found:
                print(f"   ✅ {field}: {count} references")
                audit_report['data_fields'][entity].append(field)
            else:
                print(f"   ❌ {field}: NOT FOUND")
                audit_report['issues']['major'].append(f"{entity}.{field} not extracted")

    # ============================================================================
    # SECTION 3: CRITICAL FUNCTION EXECUTION FLOW
    # ============================================================================
    print("\n" + "="*80)
    print("3️⃣ FUNCTION EXECUTION FLOW AUDIT")
    print("="*80)

    critical_functions = [
        'extract_manuscript_details',
        'extract_referees',
        'extract_authors_from_details',
        'extract_timeline',
        'extract_audit_trail',
        'extract_all_documents',
        'enrich_referee_profiles',
        'deep_web_enrichment',
        'extract_report_with_timeout',
        'ensure_recommendation_storage'
    ]

    print("\n🔍 Checking critical function calls:")
    for func in critical_functions:
        # Count how many times each function is called
        call_pattern = f"{func}\\("
        calls = []
        for i, line in enumerate(lines, 1):
            if re.search(call_pattern, line) and 'def ' not in line:
                calls.append(i)

        if calls:
            print(f"   ✅ {func}: Called {len(calls)} times at lines {calls[:3]}...")
            audit_report['function_calls'][func] = len(calls)
        else:
            print(f"   ❌ {func}: NEVER CALLED!")
            audit_report['issues']['critical'].append(f"{func} is never called")

    # ============================================================================
    # SECTION 4: ERROR HANDLING AUDIT
    # ============================================================================
    print("\n" + "="*80)
    print("4️⃣ ERROR HANDLING COVERAGE AUDIT")
    print("="*80)

    try_blocks = 0
    except_blocks = 0
    bare_excepts = 0
    finally_blocks = 0

    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*try:', line):
            try_blocks += 1
        elif re.match(r'^\s*except:', line):
            except_blocks += 1
            bare_excepts += 1
            audit_report['issues']['minor'].append(f"Bare except at line {i}")
        elif re.match(r'^\s*except\s+\w+', line):
            except_blocks += 1
        elif re.match(r'^\s*finally:', line):
            finally_blocks += 1

    print(f"   • Try blocks: {try_blocks}")
    print(f"   • Except blocks: {except_blocks}")
    print(f"   • Bare excepts: {bare_excepts} ⚠️")
    print(f"   • Finally blocks: {finally_blocks}")
    print(f"   • Try/Except ratio: {except_blocks/try_blocks if try_blocks else 0:.2f}")

    if bare_excepts > 50:
        audit_report['issues']['major'].append(f"Too many bare except blocks: {bare_excepts}")

    # ============================================================================
    # SECTION 5: SELENIUM OPERATIONS AUDIT
    # ============================================================================
    print("\n" + "="*80)
    print("5️⃣ SELENIUM OPERATIONS AUDIT")
    print("="*80)

    selenium_ops = {
        'find_element': 0,
        'find_elements': 0,
        'click()': 0,
        'send_keys': 0,
        'switch_to.window': 0,
        'switch_to.frame': 0,
        'execute_script': 0,
        'WebDriverWait': 0,
        'time.sleep': 0
    }

    for op in selenium_ops:
        selenium_ops[op] = sum(1 for line in lines if op in line)

    print("\n📊 Selenium operations count:")
    for op, count in selenium_ops.items():
        print(f"   • {op}: {count}")
        if op == 'time.sleep' and count > 100:
            audit_report['issues']['optimization'].append(f"Excessive time.sleep calls: {count}")

    # Check for missing waits
    elements_without_wait = 0
    for i, line in enumerate(lines):
        if 'find_element' in line:
            # Check if there's a wait in the previous 5 lines
            wait_found = False
            for j in range(max(0, i-5), i):
                if 'WebDriverWait' in lines[j] or 'time.sleep' in lines[j]:
                    wait_found = True
                    break
            if not wait_found:
                elements_without_wait += 1

    if elements_without_wait > 50:
        print(f"\n⚠️ {elements_without_wait} element searches without explicit waits")
        audit_report['issues']['major'].append(f"Missing waits: {elements_without_wait} elements")

    # ============================================================================
    # SECTION 6: DATA STORAGE CONSISTENCY
    # ============================================================================
    print("\n" + "="*80)
    print("6️⃣ DATA STORAGE CONSISTENCY AUDIT")
    print("="*80)

    # Check for inconsistent data storage patterns
    storage_patterns = {
        'referee_report': [],
        'author_data': [],
        'manuscript_data': []
    }

    for i, line in enumerate(lines, 1):
        if "referee['report']" in line:
            storage_patterns['referee_report'].append(i)
        if "author[" in line and '=' in line:
            storage_patterns['author_data'].append(i)
        if "manuscript[" in line and '=' in line:
            storage_patterns['manuscript_data'].append(i)

    print("\n📦 Data storage locations:")
    print(f"   • Referee report data: {len(storage_patterns['referee_report'])} locations")
    print(f"   • Author data: {len(storage_patterns['author_data'])} locations")
    print(f"   • Manuscript data: {len(storage_patterns['manuscript_data'])} locations")

    # Check for recommendation storage consistency
    rec_storage = []
    for i, line in enumerate(lines, 1):
        if "['recommendation']" in line or "['recommendation_normalized']" in line:
            rec_storage.append((i, line.strip()[:80]))

    print(f"\n🎯 Recommendation storage: {len(rec_storage)} locations")
    if len(rec_storage) < 5:
        audit_report['issues']['critical'].append("Insufficient recommendation storage points")

    # ============================================================================
    # SECTION 7: PERFORMANCE BOTTLENECKS
    # ============================================================================
    print("\n" + "="*80)
    print("7️⃣ PERFORMANCE BOTTLENECK ANALYSIS")
    print("="*80)

    # Check for nested loops
    nested_loops = 0
    for i in range(len(lines)):
        if 'for ' in lines[i]:
            # Check next 20 lines for another for loop
            for j in range(i+1, min(i+20, len(lines))):
                if 'for ' in lines[j] and lines[j].count(' ') > lines[i].count(' '):
                    nested_loops += 1
                    break

    print(f"   • Nested loops found: {nested_loops}")
    if nested_loops > 20:
        audit_report['issues']['optimization'].append(f"Too many nested loops: {nested_loops}")

    # Check for repeated operations
    repeated_ops = Counter()
    for line in lines:
        if 'self.driver.find_element' in line:
            # Extract the selector
            match = re.search(r'By\.\w+,\s*["\']([^"\']+)', line)
            if match:
                repeated_ops[match.group(1)] += 1

    most_repeated = repeated_ops.most_common(5)
    if most_repeated:
        print("\n🔁 Most repeated element searches:")
        for selector, count in most_repeated:
            print(f"   • '{selector[:50]}...': {count} times")
            if count > 10:
                audit_report['issues']['optimization'].append(f"Repeated search: {selector[:30]}")

    # ============================================================================
    # SECTION 8: SECURITY AND CREDENTIALS
    # ============================================================================
    print("\n" + "="*80)
    print("8️⃣ SECURITY AND CREDENTIALS AUDIT")
    print("="*80)

    security_issues = []

    # Check for hardcoded credentials
    credential_patterns = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']'
    ]

    for i, line in enumerate(lines, 1):
        for pattern in credential_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                security_issues.append(f"Line {i}: Potential hardcoded credential")
                audit_report['issues']['critical'].append(f"Security: Line {i} credential")

    print(f"   • Potential credential leaks: {len(security_issues)}")
    if security_issues:
        for issue in security_issues[:3]:
            print(f"      ⚠️ {issue}")

    # Check for credential masking in logs
    log_patterns = ['print(', 'logger.', 'log(']
    unmasked_logs = 0

    for i, line in enumerate(lines, 1):
        if any(p in line for p in log_patterns):
            if any(word in line.lower() for word in ['password', 'token', 'secret', 'credential']):
                if '***' not in line and 'REDACTED' not in line:
                    unmasked_logs += 1

    if unmasked_logs > 0:
        print(f"   • ⚠️ Unmasked credential logs: {unmasked_logs}")
        audit_report['issues']['critical'].append(f"Unmasked credentials in logs: {unmasked_logs}")
    else:
        print(f"   • ✅ All credential logs appear masked")

    # ============================================================================
    # SECTION 9: EDGE CASES AND FAILURE MODES
    # ============================================================================
    print("\n" + "="*80)
    print("9️⃣ EDGE CASE HANDLING AUDIT")
    print("="*80)

    edge_case_checks = {
        'None checks': sum(1 for line in lines if 'if ' in line and 'None' in line),
        'Empty checks': sum(1 for line in lines if 'if not ' in line or 'if len(' in line),
        'Type checks': sum(1 for line in lines if 'isinstance(' in line),
        'Try/except': try_blocks,
        'Default values': sum(1 for line in lines if '.get(' in line),
        'Fallback logic': sum(1 for line in lines if 'else:' in line)
    }

    print("\n🛡️ Defensive programming metrics:")
    for check, count in edge_case_checks.items():
        print(f"   • {check}: {count}")

    # Check for unchecked array access
    unchecked_access = 0
    for i, line in enumerate(lines, 1):
        if '[0]' in line or '[1]' in line or '[-1]' in line:
            # Check if there's a length check nearby
            check_found = False
            for j in range(max(0, i-3), min(i+3, len(lines))):
                if 'if ' in lines[j] and ('len(' in lines[j] or 'not ' in lines[j]):
                    check_found = True
                    break
            if not check_found:
                unchecked_access += 1

    if unchecked_access > 20:
        print(f"\n⚠️ {unchecked_access} unchecked array accesses")
        audit_report['issues']['major'].append(f"Unchecked array access: {unchecked_access}")

    # ============================================================================
    # SECTION 10: DEAD CODE AND DUPLICATION
    # ============================================================================
    print("\n" + "="*80)
    print("🔟 CODE QUALITY AUDIT")
    print("="*80)

    # Check for commented out code
    commented_code = sum(1 for line in lines if line.strip().startswith('#') and
                         any(keyword in line for keyword in ['def ', 'class ', 'import ', 'if ', 'for ']))

    print(f"   • Commented code lines: {commented_code}")
    if commented_code > 100:
        audit_report['issues']['minor'].append(f"Excessive commented code: {commented_code} lines")

    # Check for TODO/FIXME comments
    todos = sum(1 for line in lines if 'TODO' in line or 'FIXME' in line)
    print(f"   • TODO/FIXME comments: {todos}")
    if todos > 10:
        audit_report['issues']['minor'].append(f"Unresolved TODOs: {todos}")

    # Check for duplicate code blocks
    code_blocks = defaultdict(list)
    for i in range(len(lines) - 5):
        block = '\n'.join(lines[i:i+5])
        if len(block) > 100 and not block.startswith('#'):
            code_blocks[block].append(i+1)

    duplicates = [(block, locs) for block, locs in code_blocks.items() if len(locs) > 1]
    if duplicates:
        print(f"   • Duplicate code blocks: {len(duplicates)}")
        audit_report['issues']['optimization'].append(f"Code duplication: {len(duplicates)} blocks")

    # ============================================================================
    # SECTION 11: SPECIFIC MF EXTRACTOR CHECKS
    # ============================================================================
    print("\n" + "="*80)
    print("1️⃣1️⃣ MF-SPECIFIC FUNCTIONALITY AUDIT")
    print("="*80)

    mf_specific = {
        'Referee extraction': 'extract_referees' in code,
        'Report popup handling': 'rev_ms_det_pop' in code,
        'Email popup extraction': 'mailpopup' in code,
        'ORCID enrichment': 'orcid_client' in code,
        'Timeline extraction': 'extract_timeline' in code or 'extract_audit_trail' in code,
        'Cover letter extraction': 'cover_letter' in code,
        'Abstract extraction': 'abstract' in code.lower(),
        'Keywords extraction': 'keywords' in code.lower(),
        'Response to reviewers': 'response_to_reviewers' in code,
        'Revision tracking': 'revisions' in code and 'manuscript' in code,
        'LaTeX source': 'latex_source' in code,
        'Recommendation storage': 'ensure_recommendation_storage' in code
    }

    print("\n🎯 MF-specific features:")
    for feature, present in mf_specific.items():
        if present:
            print(f"   ✅ {feature}")
        else:
            print(f"   ❌ {feature}")
            audit_report['issues']['critical'].append(f"Missing feature: {feature}")

    # ============================================================================
    # SECTION 12: PASS SYSTEM VERIFICATION
    # ============================================================================
    print("\n" + "="*80)
    print("1️⃣2️⃣ THREE-PASS SYSTEM VERIFICATION")
    print("="*80)

    pass_mentions = {
        'PASS 1': sum(1 for line in lines if 'PASS 1' in line),
        'PASS 2': sum(1 for line in lines if 'PASS 2' in line),
        'PASS 3': sum(1 for line in lines if 'PASS 3' in line),
        'Forward': sum(1 for line in lines if 'forward' in line.lower()),
        'Backward': sum(1 for line in lines if 'backward' in line.lower())
    }

    print("\n🔄 Pass system implementation:")
    for pass_type, count in pass_mentions.items():
        print(f"   • {pass_type}: {count} mentions")

    if pass_mentions['PASS 3'] < 2:
        audit_report['issues']['major'].append("Three-pass system may be incomplete")

    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print("\n" + "="*80)
    print("📊 AUDIT SUMMARY")
    print("="*80)

    total_issues = sum(len(issues) for issues in audit_report['issues'].values())

    print(f"\n🚨 Total Issues Found: {total_issues}")
    print(f"   • Critical: {len(audit_report['issues']['critical'])}")
    print(f"   • Major: {len(audit_report['issues']['major'])}")
    print(f"   • Minor: {len(audit_report['issues']['minor'])}")
    print(f"   • Optimization: {len(audit_report['issues']['optimization'])}")

    if audit_report['issues']['critical']:
        print(f"\n❌ CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
        for issue in audit_report['issues']['critical'][:10]:
            print(f"   • {issue}")

    if audit_report['issues']['major']:
        print(f"\n⚠️ MAJOR ISSUES TO ADDRESS:")
        for issue in audit_report['issues']['major'][:10]:
            print(f"   • {issue}")

    # Calculate health score
    health_score = 100
    health_score -= len(audit_report['issues']['critical']) * 10
    health_score -= len(audit_report['issues']['major']) * 5
    health_score -= len(audit_report['issues']['minor']) * 1
    health_score -= len(audit_report['issues']['optimization']) * 0.5
    health_score = max(0, min(100, health_score))

    print(f"\n🏥 EXTRACTOR HEALTH SCORE: {health_score:.1f}/100")

    if health_score >= 90:
        print("   ✅ Excellent - Production ready")
    elif health_score >= 75:
        print("   ⚠️ Good - Minor improvements needed")
    elif health_score >= 60:
        print("   ⚠️ Fair - Several issues to address")
    else:
        print("   ❌ Poor - Significant work required")

    # Save detailed report
    report_file = 'mf_maniacal_audit_report.json'
    with open(report_file, 'w') as f:
        json.dump(audit_report, f, indent=2)

    print(f"\n💾 Detailed audit report saved to {report_file}")

    return audit_report

if __name__ == "__main__":
    audit_report = maniacal_audit()

    # Exit with error code if critical issues found
    sys.exit(1 if audit_report['issues']['critical'] else 0)
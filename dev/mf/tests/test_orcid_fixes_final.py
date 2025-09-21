#!/usr/bin/env python3
"""Final verification that all ORCID fixes are working."""

import sys
import os
import json
from datetime import datetime

# Add path for imports
sys.path.insert(0, os.path.abspath('../../../src/core'))

from orcid_client import ORCIDClient

def test_all_orcid_fixes():
    """Verify all ORCID fixes are working correctly."""
    print("🧪 FINAL ORCID FIXES VERIFICATION")
    print("=" * 80)

    client = ORCIDClient()

    # Test case: Gechun Liang - known profile with all data
    test_person = {
        'name': 'Gechun Liang',
        'institution': 'University of Warwick'  # Optional hint
    }

    print(f"\n📝 Test Subject: {test_person['name']}")
    print("=" * 60)

    # Run enrichment
    print("\n🔍 Running ORCID enrichment...")
    enriched = client.enrich_person_profile(test_person)

    # Display results
    print("\n📊 ENRICHMENT RESULTS:")
    print("-" * 40)

    # Check each critical field
    checks = []

    # 1. ORCID ID
    orcid = enriched.get('orcid')
    expected_orcid = '0000-0003-0752-0773'
    checks.append({
        'field': 'ORCID ID',
        'expected': expected_orcid,
        'actual': orcid,
        'passed': orcid == expected_orcid
    })

    # 2. Institution
    institution = enriched.get('institution')
    expected_institution = 'University of Warwick'
    checks.append({
        'field': 'Institution',
        'expected': expected_institution,
        'actual': institution,
        'passed': institution == expected_institution
    })

    # 3. Department
    department = enriched.get('department')
    expected_department = 'Department of Statistics'
    checks.append({
        'field': 'Department',
        'expected': expected_department,
        'actual': department,
        'passed': department == expected_department
    })

    # 4. Role
    role = enriched.get('role')
    expected_role = 'Reader'
    checks.append({
        'field': 'Role',
        'expected': expected_role,
        'actual': role,
        'passed': role == expected_role
    })

    # 5. Country
    country = enriched.get('country')
    expected_country = 'United Kingdom'
    checks.append({
        'field': 'Country',
        'expected': expected_country,
        'actual': country,
        'passed': country == expected_country
    })

    # 6. Current Affiliation
    current_affil = enriched.get('current_affiliation', {})
    has_current = bool(current_affil and current_affil.get('organization'))
    checks.append({
        'field': 'Current Affiliation',
        'expected': 'Present',
        'actual': 'Present' if has_current else 'Missing',
        'passed': has_current
    })

    # 7. Affiliation History
    affil_history = enriched.get('affiliation_history', [])
    expected_affil_count = 7  # Based on test data
    actual_affil_count = len(affil_history)
    checks.append({
        'field': 'Affiliation History Count',
        'expected': f'{expected_affil_count} affiliations',
        'actual': f'{actual_affil_count} affiliations',
        'passed': actual_affil_count >= expected_affil_count
    })

    # 8. Research Interests
    research_interests = enriched.get('research_interests', [])
    has_interests = len(research_interests) > 0
    checks.append({
        'field': 'Research Interests',
        'expected': 'Present',
        'actual': f'{len(research_interests)} found' if has_interests else 'Missing',
        'passed': has_interests
    })

    # Print detailed results
    for check in checks:
        status = "✅" if check['passed'] else "❌"
        print(f"\n{status} {check['field']}:")
        print(f"   Expected: {check['expected']}")
        print(f"   Actual: {check['actual']}")

    # Summary
    passed_count = sum(1 for c in checks if c['passed'])
    total_count = len(checks)

    print("\n" + "=" * 80)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"\n✅ Passed: {passed_count}/{total_count}")
    print(f"❌ Failed: {total_count - passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n🎉 ALL ORCID FIXES VERIFIED SUCCESSFULLY!")
        print("\nThe following features are now working:")
        print("  ✅ ORCID ID discovery and extraction")
        print("  ✅ Institution extraction from current affiliation")
        print("  ✅ Department extraction from employment details")
        print("  ✅ Role/title extraction from employment")
        print("  ✅ Country extraction with code mapping (GB → United Kingdom)")
        print("  ✅ Current affiliation identification")
        print("  ✅ Complete affiliation history extraction")
        print("  ✅ Research interests extraction from publications")
    else:
        print("\n⚠️ Some features are not working correctly:")
        for check in checks:
            if not check['passed']:
                print(f"  ❌ {check['field']}: Expected '{check['expected']}', got '{check['actual']}'")

    # Save detailed results
    results = {
        'timestamp': datetime.now().isoformat(),
        'test_subject': test_person,
        'enriched_profile': enriched,
        'verification_checks': checks,
        'summary': {
            'passed': passed_count,
            'failed': total_count - passed_count,
            'total': total_count,
            'success_rate': f"{(passed_count/total_count)*100:.1f}%"
        }
    }

    output_file = 'orcid_fixes_verification.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed results saved to {output_file}")

    return passed_count == total_count

if __name__ == "__main__":
    success = test_all_orcid_fixes()
    sys.exit(0 if success else 1)
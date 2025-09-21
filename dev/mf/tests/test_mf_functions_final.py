#!/usr/bin/env python3
"""Test MF extractor functions with all ORCID fixes."""

import sys
import os
import json
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.abspath('../../../production/src/extractors'))
sys.path.insert(0, os.path.abspath('../../../production/src/core'))
sys.path.insert(0, os.path.abspath('../../../src/core'))

def test_mf_functions():
    """Test MF extractor functions directly."""
    print("🧪 MF EXTRACTOR FUNCTIONS TEST - ALL FIXES")
    print("=" * 80)

    # Import functions from mf_extractor
    import mf_extractor

    # Test referee enrichment function
    print("\n1️⃣ Testing enrich_referee_profiles function...")
    test_referees = [
        {
            'name': 'Gechun Liang',
            'email': 'g.liang@warwick.ac.uk',
            'institution': None,
            'department': None,
            'country': None
        }
    ]

    print("\n   Before enrichment:")
    for referee in test_referees:
        print(f"   • {referee['name']}:")
        print(f"     - Institution: {referee.get('institution', 'NONE')}")
        print(f"     - Department: {referee.get('department', 'NONE')}")
        print(f"     - Country: {referee.get('country', 'NONE')}")

    # Call the enrichment function
    enriched = mf_extractor.enrich_referee_profiles(test_referees)

    print("\n   After enrichment:")
    for referee in enriched:
        print(f"   • {referee['name']}:")
        print(f"     - Institution: {referee.get('institution', 'NOT FOUND')}")
        print(f"     - Department: {referee.get('department', 'NOT FOUND')}")
        print(f"     - Role: {referee.get('role', 'NOT FOUND')}")
        print(f"     - Country: {referee.get('country', 'NOT FOUND')}")
        print(f"     - ORCID: {referee.get('orcid', 'NOT FOUND')}")

    # Test deep web enrichment function
    print("\n2️⃣ Testing deep_web_enrichment function...")
    test_person = {
        'name': 'Gechun Liang',
        'email': 'g.liang@warwick.ac.uk'
    }

    print("\n   Before enrichment:")
    print(f"   • {test_person['name']}:")
    print(f"     - Institution: {test_person.get('institution', 'NONE')}")
    print(f"     - Department: {test_person.get('department', 'NONE')}")

    # Call the deep web enrichment function
    enriched_person = mf_extractor.deep_web_enrichment(test_person)

    print("\n   After enrichment:")
    print(f"   • {enriched_person['name']}:")
    print(f"     - Institution: {enriched_person.get('institution', 'NOT FOUND')}")
    print(f"     - Department: {enriched_person.get('department', 'NOT FOUND')}")
    print(f"     - Role: {enriched_person.get('role', 'NOT FOUND')}")
    print(f"     - Country: {enriched_person.get('country', 'NOT FOUND')}")
    print(f"     - ORCID: {enriched_person.get('orcid', 'NOT FOUND')}")

    # Verification
    print("\n" + "="*80)
    print("📊 TEST RESULTS")
    print("="*80)

    checks = []

    # Check referee enrichment
    if enriched and enriched[0]['name'] == 'Gechun Liang':
        referee = enriched[0]

        checks.append(('Referee institution',
                      referee.get('institution') == 'University of Warwick',
                      referee.get('institution')))

        checks.append(('Referee department',
                      referee.get('department') == 'Department of Statistics',
                      referee.get('department')))

        checks.append(('Referee role',
                      referee.get('role') == 'Reader',
                      referee.get('role')))

        checks.append(('Referee country',
                      referee.get('country') == 'United Kingdom',
                      referee.get('country')))

        checks.append(('Referee ORCID',
                      referee.get('orcid') == '0000-0003-0752-0773',
                      referee.get('orcid')))

    # Check author enrichment
    if enriched_person['name'] == 'Gechun Liang':

        checks.append(('Author institution',
                      enriched_person.get('institution') == 'University of Warwick',
                      enriched_person.get('institution')))

        checks.append(('Author department',
                      enriched_person.get('department') == 'Department of Statistics',
                      enriched_person.get('department')))

        checks.append(('Author role',
                      enriched_person.get('role') == 'Reader',
                      enriched_person.get('role')))

        checks.append(('Author ORCID',
                      enriched_person.get('orcid') == '0000-0003-0752-0773',
                      enriched_person.get('orcid')))

    # Print results
    passed = 0
    for check_name, success, value in checks:
        if success:
            print(f"  ✅ {check_name}: {value}")
            passed += 1
        else:
            print(f"  ❌ {check_name}: {value or 'NOT FOUND'}")

    print(f"\n📊 Final Score: {passed}/{len(checks)} checks passed")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'referee_enriched': enriched[0] if enriched else None,
        'author_enriched': enriched_person,
        'checks': [{'name': c[0], 'passed': c[1], 'value': c[2]} for c in checks],
        'success_rate': f"{passed}/{len(checks)}"
    }

    output_file = 'mf_functions_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to {output_file}")

    if passed == len(checks):
        print("\n✅ ALL FUNCTION TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ Some tests failed ({len(checks) - passed} failures)")
        return False

if __name__ == "__main__":
    success = test_mf_functions()
    sys.exit(0 if success else 1)
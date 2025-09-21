#!/usr/bin/env python3
"""Comprehensive test of affiliation extraction with all fields."""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath('../../../src/core'))
sys.path.insert(0, os.path.abspath('../../../production/src/extractors'))

from orcid_client import ORCIDClient

def test_comprehensive_affiliations():
    """Test all aspects of affiliation extraction."""
    print("🧪 COMPREHENSIVE AFFILIATION EXTRACTION TEST")
    print("=" * 80)

    client = ORCIDClient()

    # Test cases with known ORCID profiles
    test_cases = [
        {
            'orcid': '0000-0003-0752-0773',
            'name': 'Gechun Liang',
            'expected_institution': 'University of Warwick'
        },
        {
            'orcid': '0000-0002-1825-0097',  # Another test case if available
            'name': 'Test Person',
            'expected_institution': None  # Will check what we get
        }
    ]

    results = []

    for test_case in test_cases:
        orcid_id = test_case['orcid']
        print(f"\n{'='*60}")
        print(f"Testing ORCID: {orcid_id}")
        print(f"Name: {test_case['name']}")
        print(f"{'='*60}")

        # 1. Get detailed affiliations
        print(f"\n1️⃣ Getting detailed affiliations...")
        affiliations = client.get_affiliations(orcid_id)

        if affiliations:
            print(f"   ✅ Found {len(affiliations)} affiliations")

            # Show all affiliations with full details
            for i, affil in enumerate(affiliations, 1):
                print(f"\n   Affiliation {i}:")
                print(f"   • Organization: {affil.get('organization', 'N/A')}")
                print(f"   • Department: {affil.get('department', 'N/A')}")
                print(f"   • Role: {affil.get('role', 'N/A')}")
                print(f"   • Type: {affil.get('type', 'N/A')}")
                print(f"   • Current: {'✅ YES' if affil.get('current') else '❌ NO'}")
                print(f"   • Start: {affil.get('start_date', 'N/A')}")
                print(f"   • End: {affil.get('end_date', 'N/A')}")
                print(f"   • City: {affil.get('city', 'N/A')}")
                print(f"   • Country: {affil.get('country', 'N/A')}")
        else:
            print(f"   ❌ No affiliations found")

        # 2. Test enrichment to see top-level fields
        print(f"\n2️⃣ Testing full enrichment...")
        person_data = {
            'name': test_case['name'],
            'institution': test_case.get('expected_institution', '')
        }

        enriched = client.enrich_person_profile(person_data)

        print(f"\n   Top-level fields:")
        print(f"   • ORCID: {enriched.get('orcid', 'NOT FOUND')}")
        print(f"   • Institution: {enriched.get('institution', 'NOT FOUND')}")
        print(f"   • Department: {enriched.get('department', 'NOT FOUND')}")
        print(f"   • Role: {enriched.get('role', 'NOT FOUND')}")
        print(f"   • Country: {enriched.get('country', 'NOT FOUND')}")

        print(f"\n   Current affiliation:")
        current_affil = enriched.get('current_affiliation', {})
        if current_affil:
            print(f"   • Organization: {current_affil.get('organization', 'N/A')}")
            print(f"   • Department: {current_affil.get('department', 'N/A')}")
            print(f"   • Role: {current_affil.get('role', 'N/A')}")
            print(f"   • Since: {current_affil.get('start_date', 'N/A')}")
        else:
            print(f"   • No current affiliation found")

        print(f"\n   Research interests ({len(enriched.get('research_interests', []))} found):")
        for interest in enriched.get('research_interests', [])[:5]:
            print(f"   • {interest}")

        # Store result
        results.append({
            'orcid': orcid_id,
            'name': test_case['name'],
            'institution_found': enriched.get('institution'),
            'department_found': enriched.get('department'),
            'role_found': enriched.get('role'),
            'country_found': enriched.get('country'),
            'affiliations_count': len(affiliations) if affiliations else 0,
            'current_affiliation': current_affil
        })

    # 3. Summary
    print(f"\n\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")

    for result in results:
        print(f"\n{result['name']} ({result['orcid']}):")
        print(f"  ✅ Institution: {result['institution_found'] or '❌ NOT FOUND'}")
        print(f"  ✅ Department: {result['department_found'] or '❌ NOT FOUND'}")
        print(f"  ✅ Role: {result['role_found'] or '❌ NOT FOUND'}")
        print(f"  ✅ Country: {result['country_found'] or '❌ NOT FOUND'}")
        print(f"  📊 Total affiliations: {result['affiliations_count']}")

    # 4. Test specific extraction methods
    print(f"\n\n{'='*80}")
    print(f"🔬 TESTING SPECIFIC EXTRACTION METHODS")
    print(f"{'='*80}")

    test_orcid = '0000-0003-0752-0773'

    # Test country extraction
    print(f"\n Testing _extract_country_from_profile...")
    profile = client.get_full_profile(test_orcid)
    if profile:
        country = client._extract_country_from_profile(profile)
        print(f"  Country extracted: {country or 'NOT FOUND'}")

    # Save results to file
    output_file = 'affiliation_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {output_file}")

    print(f"\n✅ COMPREHENSIVE TEST COMPLETE")

    # Return success indicator
    return all(r['institution_found'] for r in results if r['name'] == 'Gechun Liang')

if __name__ == "__main__":
    success = test_comprehensive_affiliations()
    sys.exit(0 if success else 1)
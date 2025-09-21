#!/usr/bin/env python3
"""Final integration test for MF extractor with all fixes."""

import sys
import os
import json
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.abspath('../../../production/src/extractors'))
sys.path.insert(0, os.path.abspath('../../../production/src/core'))
sys.path.insert(0, os.path.abspath('../../../src/core'))

def test_mf_integration():
    """Test MF extractor with all ORCID enrichment fixes."""
    print("🧪 MF EXTRACTOR INTEGRATION TEST - ALL FIXES")
    print("=" * 80)

    # Import MF extractor
    from mf_extractor import MFExtractor

    # Initialize extractor
    print("\n1️⃣ Initializing MF Extractor...")
    extractor = MFExtractor()

    # Test referee enrichment
    print("\n2️⃣ Testing Referee Enrichment...")
    test_referees = [
        {
            'name': 'Gechun Liang',
            'email': 'g.liang@warwick.ac.uk',
            'institution': None,  # Should be filled by ORCID
            'department': None,   # Should be filled by ORCID
            'country': None      # Should be filled by ORCID
        },
        {
            'name': 'Martin Schweizer',
            'email': 'martin.schweizer@math.ethz.ch',
            'institution': 'ETH Zurich',
            'department': None,   # Should be filled if found
            'country': None      # Should be filled if found
        }
    ]

    print("\n   Before enrichment:")
    for referee in test_referees:
        print(f"   • {referee['name']}: {referee.get('institution', 'NO INST')} | {referee.get('department', 'NO DEPT')} | {referee.get('country', 'NO COUNTRY')}")

    # Run enrichment
    enriched_referees = extractor.enrich_referee_profiles(test_referees)

    print("\n   After enrichment:")
    for referee in enriched_referees:
        print(f"   • {referee['name']}:")
        print(f"     - Institution: {referee.get('institution', 'NOT FOUND')}")
        print(f"     - Department: {referee.get('department', 'NOT FOUND')}")
        print(f"     - Role: {referee.get('role', 'NOT FOUND')}")
        print(f"     - Country: {referee.get('country', 'NOT FOUND')}")
        print(f"     - ORCID: {referee.get('orcid', 'NOT FOUND')}")

    # Test author enrichment
    print("\n3️⃣ Testing Author Enrichment...")
    test_authors = [
        {
            'name': 'Gechun Liang',
            'email': 'g.liang@warwick.ac.uk'
        },
        {
            'name': 'Johannes Muhle-Karbe',
            'email': 'johannes.muhle-karbe@imperial.ac.uk'
        }
    ]

    print("\n   Before enrichment:")
    for author in test_authors:
        print(f"   • {author['name']}: {author.get('institution', 'NO INST')} | {author.get('orcid', 'NO ORCID')}")

    # Run deep web enrichment
    enriched_authors = []
    for author in test_authors:
        enriched = extractor.deep_web_enrichment(author)
        enriched_authors.append(enriched)

    print("\n   After enrichment:")
    for author in enriched_authors:
        print(f"   • {author['name']}:")
        print(f"     - Institution: {author.get('institution', 'NOT FOUND')}")
        print(f"     - Department: {author.get('department', 'NOT FOUND')}")
        print(f"     - Role: {author.get('role', 'NOT FOUND')}")
        print(f"     - Country: {author.get('country', 'NOT FOUND')}")
        print(f"     - ORCID: {author.get('orcid', 'NOT FOUND')}")

    # Summary
    print("\n" + "="*80)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*80)

    success_count = 0
    total_checks = 0

    # Check referee enrichment
    for referee in enriched_referees:
        if referee['name'] == 'Gechun Liang':
            total_checks += 4
            if referee.get('institution') == 'University of Warwick':
                success_count += 1
                print("  ✅ Referee institution extracted")
            else:
                print(f"  ❌ Referee institution not extracted (got: {referee.get('institution')})")

            if referee.get('department') == 'Department of Statistics':
                success_count += 1
                print("  ✅ Referee department extracted")
            else:
                print(f"  ❌ Referee department not extracted (got: {referee.get('department')})")

            if referee.get('role') == 'Reader':
                success_count += 1
                print("  ✅ Referee role extracted")
            else:
                print(f"  ❌ Referee role not extracted (got: {referee.get('role')})")

            if referee.get('country') == 'United Kingdom':
                success_count += 1
                print("  ✅ Referee country extracted")
            else:
                print(f"  ❌ Referee country not extracted (got: {referee.get('country')})")

    # Check author enrichment
    for author in enriched_authors:
        if author['name'] == 'Gechun Liang':
            total_checks += 4
            if author.get('institution') == 'University of Warwick':
                success_count += 1
                print("  ✅ Author institution extracted")
            else:
                print(f"  ❌ Author institution not extracted (got: {author.get('institution')})")

            if author.get('department') == 'Department of Statistics':
                success_count += 1
                print("  ✅ Author department extracted")
            else:
                print(f"  ❌ Author department not extracted (got: {author.get('department')})")

            if author.get('role') == 'Reader':
                success_count += 1
                print("  ✅ Author role extracted")
            else:
                print(f"  ❌ Author role not extracted (got: {author.get('role')})")

            if author.get('orcid') == '0000-0003-0752-0773':
                success_count += 1
                print("  ✅ Author ORCID extracted")
            else:
                print(f"  ❌ Author ORCID not extracted (got: {author.get('orcid')})")

    print(f"\n📊 Final Score: {success_count}/{total_checks} checks passed")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'referees': enriched_referees,
        'authors': enriched_authors,
        'success_rate': f"{success_count}/{total_checks}"
    }

    output_file = 'integration_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to {output_file}")

    if success_count == total_checks:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ Some tests failed ({total_checks - success_count} failures)")
        return False

if __name__ == "__main__":
    success = test_mf_integration()
    sys.exit(0 if success else 1)
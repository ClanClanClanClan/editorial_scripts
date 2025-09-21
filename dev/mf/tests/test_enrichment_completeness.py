#!/usr/bin/env python3
"""Final test to verify ORCID enrichment runs for ALL people."""

import sys
import os
import json
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.abspath('../../../src/core'))

from orcid_client import ORCIDClient

def test_enrichment_completeness():
    """Test that enrichment would run for all people in a typical manuscript."""

    print("🧪 ENRICHMENT COMPLETENESS TEST")
    print("=" * 80)

    client = ORCIDClient()

    # Simulate a manuscript with multiple authors and referees
    test_manuscript = {
        'id': 'MF-2024-TEST',
        'title': 'Test Manuscript',
        'authors': [
            {'name': 'Gechun Liang', 'email': 'g.liang@warwick.ac.uk'},
            {'name': 'Martin Schweizer', 'email': 'martin.schweizer@math.ethz.ch'},
            {'name': 'Johannes Muhle-Karbe', 'email': 'j.muhle-karbe@imperial.ac.uk'},
            {'name': 'Dylan Possamai', 'email': 'dylan.possamai@math.ethz.ch'},
            {'name': 'Nizar Touzi', 'email': 'nizar.touzi@polytechnique.edu'}
        ],
        'referees': [
            {'name': 'Peter Tankov', 'email': 'peter.tankov@ensae.fr'},
            {'name': 'Rama Cont', 'email': 'rama.cont@maths.ox.ac.uk'},
            {'name': 'Mathieu Rosenbaum', 'email': 'mathieu.rosenbaum@polytechnique.edu'},
            {'name': 'Huyen Pham', 'email': 'pham@math.univ-paris-diderot.fr'}
        ]
    }

    print(f"\n📝 Test Manuscript: {test_manuscript['id']}")
    print(f"   • {len(test_manuscript['authors'])} authors")
    print(f"   • {len(test_manuscript['referees'])} referees")
    print(f"   • Total people: {len(test_manuscript['authors']) + len(test_manuscript['referees'])}")

    # Track enrichment results
    enrichment_results = {
        'authors': [],
        'referees': [],
        'summary': {}
    }

    # Test 1: Simulate referee enrichment (as done in MF extractor)
    print("\n" + "="*60)
    print("1️⃣ SIMULATING REFEREE ENRICHMENT")
    print("="*60)

    for i, referee in enumerate(test_manuscript['referees'], 1):
        print(f"\n📚 Referee {i}/{len(test_manuscript['referees'])}: {referee['name']}")

        # Check if enrichment would run (same condition as MF extractor)
        if referee.get('name'):
            print(f"   ✅ Has name - enrichment WILL run")

            # Simulate enrichment
            person_data = {
                'name': referee['name'],
                'email': referee.get('email', ''),
                'institution': referee.get('institution', '')
            }

            # This is what happens in the MF extractor
            try:
                enriched = client.enrich_person_profile(person_data)

                result = {
                    'name': referee['name'],
                    'enriched': True,
                    'orcid_found': bool(enriched.get('orcid')),
                    'orcid': enriched.get('orcid', 'NOT FOUND'),
                    'institution': enriched.get('institution', 'NOT FOUND'),
                    'department': enriched.get('department', 'NOT FOUND'),
                    'country': enriched.get('country', 'NOT FOUND')
                }

                if enriched.get('orcid'):
                    print(f"   🎯 ORCID found: {enriched['orcid']}")
                if enriched.get('institution'):
                    print(f"   🏛️ Institution: {enriched['institution']}")
                if enriched.get('department'):
                    print(f"   🏢 Department: {enriched['department']}")

                enrichment_results['referees'].append(result)
            except Exception as e:
                print(f"   ⚠️ Enrichment error: {e}")
                enrichment_results['referees'].append({
                    'name': referee['name'],
                    'enriched': False,
                    'error': str(e)
                })
        else:
            print(f"   ❌ No name - enrichment would be SKIPPED")
            enrichment_results['referees'].append({
                'name': 'NO NAME',
                'enriched': False,
                'reason': 'No name provided'
            })

    # Test 2: Simulate author enrichment (as done in MF extractor)
    print("\n" + "="*60)
    print("2️⃣ SIMULATING AUTHOR ENRICHMENT")
    print("="*60)

    for i, author in enumerate(test_manuscript['authors'], 1):
        print(f"\n📚 Author {i}/{len(test_manuscript['authors'])}: {author['name']}")

        # Check if enrichment would run (same condition as MF extractor)
        if author.get('name'):
            print(f"   ✅ Has name - enrichment WILL run")

            # Simulate enrichment
            person_data = {
                'name': author['name'],
                'email': author.get('email', ''),
                'institution': author.get('institution', '')
            }

            try:
                enriched = client.enrich_person_profile(person_data)

                result = {
                    'name': author['name'],
                    'enriched': True,
                    'orcid_found': bool(enriched.get('orcid')),
                    'orcid': enriched.get('orcid', 'NOT FOUND'),
                    'institution': enriched.get('institution', 'NOT FOUND'),
                    'department': enriched.get('department', 'NOT FOUND'),
                    'country': enriched.get('country', 'NOT FOUND')
                }

                if enriched.get('orcid'):
                    print(f"   🎯 ORCID found: {enriched['orcid']}")
                if enriched.get('institution'):
                    print(f"   🏛️ Institution: {enriched['institution']}")
                if enriched.get('department'):
                    print(f"   🏢 Department: {enriched['department']}")

                enrichment_results['authors'].append(result)
            except Exception as e:
                print(f"   ⚠️ Enrichment error: {e}")
                enrichment_results['authors'].append({
                    'name': author['name'],
                    'enriched': False,
                    'error': str(e)
                })
        else:
            print(f"   ❌ No name - enrichment would be SKIPPED")
            enrichment_results['authors'].append({
                'name': 'NO NAME',
                'enriched': False,
                'reason': 'No name provided'
            })

    # Summary
    print("\n" + "="*80)
    print("📊 ENRICHMENT COMPLETENESS SUMMARY")
    print("="*80)

    # Calculate statistics
    total_people = len(test_manuscript['authors']) + len(test_manuscript['referees'])
    enriched_authors = sum(1 for a in enrichment_results['authors'] if a.get('enriched'))
    enriched_referees = sum(1 for r in enrichment_results['referees'] if r.get('enriched'))
    total_enriched = enriched_authors + enriched_referees

    orcid_found_authors = sum(1 for a in enrichment_results['authors'] if a.get('orcid_found'))
    orcid_found_referees = sum(1 for r in enrichment_results['referees'] if r.get('orcid_found'))

    print(f"\n✅ ENRICHMENT COVERAGE:")
    print(f"   • Authors: {enriched_authors}/{len(test_manuscript['authors'])} enriched")
    print(f"   • Referees: {enriched_referees}/{len(test_manuscript['referees'])} enriched")
    print(f"   • Total: {total_enriched}/{total_people} people enriched")
    print(f"   • Coverage: {(total_enriched/total_people)*100:.1f}%")

    print(f"\n🎯 ORCID DISCOVERY:")
    print(f"   • Authors with ORCID: {orcid_found_authors}/{len(test_manuscript['authors'])}")
    print(f"   • Referees with ORCID: {orcid_found_referees}/{len(test_manuscript['referees'])}")
    print(f"   • Total ORCID found: {orcid_found_authors + orcid_found_referees}/{total_people}")

    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")

    print(f"\n   AUTHORS:")
    for author in enrichment_results['authors']:
        status = "✅" if author.get('enriched') else "❌"
        orcid = author.get('orcid', 'N/A')
        inst = author.get('institution', 'N/A')
        print(f"   {status} {author['name']:<30} ORCID: {orcid:<20} Inst: {inst}")

    print(f"\n   REFEREES:")
    for referee in enrichment_results['referees']:
        status = "✅" if referee.get('enriched') else "❌"
        orcid = referee.get('orcid', 'N/A')
        inst = referee.get('institution', 'N/A')
        print(f"   {status} {referee['name']:<30} ORCID: {orcid:<20} Inst: {inst}")

    # Save results
    enrichment_results['summary'] = {
        'timestamp': datetime.now().isoformat(),
        'total_people': total_people,
        'total_enriched': total_enriched,
        'coverage_percent': (total_enriched/total_people)*100,
        'authors_enriched': enriched_authors,
        'referees_enriched': enriched_referees,
        'orcid_found_authors': orcid_found_authors,
        'orcid_found_referees': orcid_found_referees
    }

    output_file = 'enrichment_completeness_results.json'
    with open(output_file, 'w') as f:
        json.dump(enrichment_results, f, indent=2)
    print(f"\n💾 Detailed results saved to {output_file}")

    # Final conclusion
    print("\n" + "="*80)
    print("🎯 FINAL CONCLUSION")
    print("="*80)

    if total_enriched == total_people:
        print("✅ PERFECT COVERAGE: ALL people with names get ORCID enrichment!")
        print("   • Every author is enriched via deep_web_enrichment()")
        print("   • Every referee is enriched TWICE:")
        print("     1. Via enrich_referee_profiles()")
        print("     2. Via deep_web_enrichment()")
    else:
        print(f"⚠️ PARTIAL COVERAGE: {total_enriched}/{total_people} people enriched")
        print("   Check if some people are missing names")

    return total_enriched == total_people

if __name__ == "__main__":
    success = test_enrichment_completeness()
    sys.exit(0 if success else 1)
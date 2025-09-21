#!/usr/bin/env python3
"""Test MF extraction with ALL fixes applied."""

import json
import sys
import os
from datetime import datetime

# Add paths
sys.path.insert(0, 'production/src/extractors')
sys.path.insert(0, 'src/core')

print("🎯 TESTING MF EXTRACTION WITH ALL FIXES")
print("=" * 80)

# First test ORCID client
print("\n📋 TESTING ORCID CLIENT")
print("-" * 60)

try:
    from orcid_client import ORCIDClient
    client = ORCIDClient()

    # Test with a known ORCID
    test_person = {
        'name': 'Gechun Liang',
        'orcid': 'https://orcid.org/0000-0003-0752-0773',
        'institution': 'University of Warwick'
    }

    result = client.enrich_person_profile(test_person)

    print(f"✅ ORCID client working")
    print(f"   • Publications: {result.get('publication_count', 0)}")
    print(f"   • Research Interests: {result.get('research_interests', [])[:3]}")

    # Test ORCID search
    test_search = {
        'name': 'Moris Strub',
        'institution': 'Warwick Business School'
    }

    result2 = client.enrich_person_profile(test_search)
    if result2.get('orcid_discovered'):
        print(f"✅ ORCID search working - found: {result2.get('orcid')}")
    else:
        print(f"⚠️ ORCID search returned no results")

except Exception as e:
    print(f"❌ ORCID client error: {e}")
    import traceback
    traceback.print_exc()

# Now run extraction
print("\n" + "=" * 80)
print("🚀 RUNNING MF EXTRACTION WITH ALL FIXES")
print("=" * 80)

try:
    from mf_extractor import ComprehensiveMFExtractor

    extractor = ComprehensiveMFExtractor()

    # Verify components
    print("\n📋 Component status:")
    print(f"   • ORCID Client: {'✅' if extractor.orcid_client else '❌'}")
    print(f"   • Gmail Manager: {'✅' if hasattr(extractor, 'gmail_manager') else '❌'}")

    # Run extraction
    print("\n🔄 Starting extraction...")
    result_data = extractor.extract_all()

    # Get manuscripts
    if isinstance(result_data, dict) and 'manuscripts' in result_data:
        manuscripts = list(result_data['manuscripts'].values())
    else:
        manuscripts = extractor.manuscripts

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'mf_all_fixes_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(manuscripts, f, indent=2, default=str)

    print(f"\n✅ Extraction complete - saved to: {output_file}")

    # Analyze results
    print("\n" + "=" * 80)
    print("📊 EXTRACTION RESULTS ANALYSIS")
    print("=" * 80)

    total_ms = len(manuscripts)
    total_authors = sum(len(ms.get('authors', [])) for ms in manuscripts)
    total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)

    print(f"\n📈 COUNTS:")
    print(f"   • Manuscripts: {total_ms}")
    print(f"   • Authors: {total_authors}")
    print(f"   • Referees: {total_referees}")

    # Check ORCID coverage
    authors_with_orcid = sum(1 for ms in manuscripts for a in ms.get('authors', []) if a.get('orcid'))
    referees_with_orcid = sum(1 for ms in manuscripts for r in ms.get('referees', []) if r.get('orcid'))

    authors_discovered = sum(1 for ms in manuscripts for a in ms.get('authors', []) if a.get('orcid_discovered'))
    referees_discovered = sum(1 for ms in manuscripts for r in ms.get('referees', []) if r.get('orcid_discovered'))

    print(f"\n🆔 ORCID COVERAGE:")
    print(f"   AUTHORS: {authors_with_orcid}/{total_authors} ({authors_with_orcid/max(1,total_authors)*100:.0f}%)")
    print(f"      • From journal: {authors_with_orcid - authors_discovered}")
    print(f"      • Discovered via API: {authors_discovered}")
    print(f"   REFEREES: {referees_with_orcid}/{total_referees} ({referees_with_orcid/max(1,total_referees)*100:.0f}%)")
    print(f"      • From journal: {referees_with_orcid - referees_discovered}")
    print(f"      • Discovered via API: {referees_discovered}")

    # Check country coverage
    authors_with_country = sum(1 for ms in manuscripts for a in ms.get('authors', []) if a.get('country'))
    referees_with_country = sum(1 for ms in manuscripts for r in ms.get('referees', []) if r.get('country'))

    print(f"\n🌍 COUNTRY COVERAGE:")
    print(f"   Authors: {authors_with_country}/{total_authors} ({authors_with_country/max(1,total_authors)*100:.0f}%)")
    print(f"   Referees: {referees_with_country}/{total_referees} ({referees_with_country/max(1,total_referees)*100:.0f}%)")

    # Check research interests
    refs_with_interests = sum(1 for ms in manuscripts for r in ms.get('referees', []) if r.get('research_interests'))
    print(f"\n🔬 RESEARCH INTERESTS:")
    print(f"   Referees with interests: {refs_with_interests}/{total_referees}")

    # Check publications
    total_pubs = sum(r.get('publication_count', 0) for ms in manuscripts for r in ms.get('referees', []))
    refs_with_pubs = sum(1 for ms in manuscripts for r in ms.get('referees', []) if r.get('publication_count', 0) > 0)
    print(f"\n📚 PUBLICATIONS:")
    print(f"   Referees with publications: {refs_with_pubs}/{total_referees}")
    print(f"   Total publications found: {total_pubs}")

    # Check funding
    ms_with_funding = sum(1 for ms in manuscripts
                         if ms.get('funding_information') and
                         'no funders' not in ms['funding_information'].lower())
    print(f"\n💰 FUNDING:")
    print(f"   Manuscripts with funding: {ms_with_funding}/{total_ms}")

    # Check recommendations
    ms_with_recs = sum(1 for ms in manuscripts
                      if ms.get('referee_recommendations') and
                      (ms['referee_recommendations'].get('recommended_referees') or
                       ms['referee_recommendations'].get('opposed_referees')))
    print(f"\n👥 REVIEWER RECOMMENDATIONS:")
    print(f"   Manuscripts with recommendations: {ms_with_recs}/{total_ms}")

    # Sample output
    if manuscripts:
        print(f"\n📄 SAMPLE DATA (First manuscript):")
        print("-" * 60)
        ms = manuscripts[0]
        print(f"ID: {ms.get('id')}")
        print(f"Title: {ms.get('title', 'N/A')[:60]}...")

        if ms.get('authors'):
            print(f"\nAUTHORS ({len(ms['authors'])}):")
            for i, author in enumerate(ms['authors'][:2], 1):
                print(f"  {i}. {author.get('name')}")
                print(f"     • Country: {author.get('country', 'NOT FOUND')}")
                print(f"     • ORCID: {'✅' if author.get('orcid') else '❌'}")
                if author.get('orcid_discovered'):
                    print(f"       (discovered via API)")

        if ms.get('referees'):
            print(f"\nREFEREES ({len(ms['referees'])}):")
            for i, referee in enumerate(ms['referees'][:2], 1):
                print(f"  {i}. {referee.get('name')} - {referee.get('status')}")
                print(f"     • Country: {referee.get('country', 'NOT FOUND')}")
                print(f"     • ORCID: {'✅' if referee.get('orcid') else '❌'}")
                if referee.get('orcid_discovered'):
                    print(f"       (discovered via API)")
                if referee.get('publication_count'):
                    print(f"     • Publications: {referee['publication_count']}")
                if referee.get('research_interests'):
                    print(f"     • Research: {', '.join(referee['research_interests'][:3])}")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETE")
    print(f"📁 Results saved to: {output_file}")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Extraction failed: {e}")
    import traceback
    traceback.print_exc()
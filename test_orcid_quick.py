#!/usr/bin/env python3
"""Quick ORCID test to show enrichment working."""

import sys
import os
sys.path.append('src/core')

from orcid_client import ORCIDClient

def test_orcid_enrichment():
    """Test ORCID enrichment with real API."""
    print("🧪 TESTING ORCID API ENRICHMENT")
    print("=" * 80)

    client = ORCIDClient()

    # Test cases - real researchers
    test_cases = [
        {
            'name': 'Dylan Possamai',
            'institution': 'ETH Zurich',
            'expected_orcid': '0000-0002-3777-5593'  # Your ORCID
        },
        {
            'name': 'Gechun Liang',
            'institution': 'University of Warwick',
            'expected_orcid': None  # Will search
        },
        {
            'name': 'Moris Strub',
            'institution': 'Warwick Business School',
            'expected_orcid': None  # Will search
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"TEST {i}: {test_case['name']}")
        print("=" * 60)

        # Enrich profile
        enriched = client.enrich_person_profile(test_case)

        # Display results
        if enriched.get('orcid'):
            print(f"✅ ORCID: https://orcid.org/{enriched['orcid']}")
            if enriched.get('orcid_discovered'):
                print(f"   → Discovered via API (confidence: {enriched.get('orcid_confidence', 0):.0%})")

        if enriched.get('publication_count'):
            print(f"📚 Publications: {enriched['publication_count']} found")
            if enriched.get('publications'):
                print("📝 Recent publications:")
                for pub in enriched['publications'][:3]:
                    year = pub.get('year', 'N/A')
                    title = pub.get('title', 'Unknown')
                    journal = pub.get('journal', '')
                    print(f"   • {year}: {title[:60]}...")
                    if journal:
                        print(f"     Journal: {journal}")

        if enriched.get('affiliation_history'):
            current = [a for a in enriched['affiliation_history'] if a.get('current')]
            if current:
                curr = current[0]
                print(f"🏛️ Current: {curr.get('role', 'Unknown')} at {curr.get('organization', 'Unknown')}")

        if enriched.get('research_interests'):
            interests = enriched['research_interests'][:5]
            print(f"🔬 Research interests: {', '.join(interests)}")

        if enriched.get('other_ids'):
            print("🆔 Other IDs:")
            for id_type, id_value in list(enriched['other_ids'].items())[:3]:
                print(f"   • {id_type}: {id_value}")

        if enriched.get('metrics'):
            metrics = enriched['metrics']
            if metrics.get('total_publications'):
                print(f"📊 Metrics: {metrics['total_publications']} publications")
                print(f"   • Years active: {metrics.get('years_active', 0)}")
                print(f"   • First publication: {metrics.get('first_publication', 'N/A')}")
                print(f"   • Latest publication: {metrics.get('latest_publication', 'N/A')}")

    print("\n" + "=" * 80)
    print("✅ ORCID API TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_orcid_enrichment()
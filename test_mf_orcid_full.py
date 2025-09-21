#!/usr/bin/env python3
"""Run MF extraction with ORCID enrichment and display all results."""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, 'production/src/extractors')
sys.path.insert(0, 'src/core')

def run_extraction():
    """Run MF extraction with ORCID."""
    print("🚀 RUNNING MF EXTRACTION WITH ORCID ENRICHMENT")
    print("=" * 80)

    # Import and run extractor
    from mf_extractor import ComprehensiveMFExtractor

    extractor = ComprehensiveMFExtractor()
    results = extractor.extract_all()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'mf_orcid_full_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✅ Results saved to: {output_file}")
    return results, output_file

def display_results(results):
    """Display comprehensive extraction results."""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE EXTRACTION RESULTS")
    print("=" * 80)

    # Overall stats
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"   • Total manuscripts: {len(results.get('manuscripts', {}))}")
    print(f"   • Total referees: {len(results.get('referees', {}))}")
    print(f"   • Total documents: {len(results.get('documents', {}))}")
    print(f"   • Total authors: {len(results.get('authors', {}))}")

    # Referee details with ORCID
    referees = results.get('referees', {})
    if referees:
        print(f"\n👥 REFEREE PROFILES ({len(referees)} total):")
        for ref_id, ref_data in list(referees.items())[:5]:  # Show first 5
            print(f"\n   🔹 {ref_data.get('name', 'Unknown')}")
            print(f"      Email: {ref_data.get('email', 'N/A')}")
            print(f"      Institution: {ref_data.get('institution', 'N/A')}")

            # ORCID data
            if ref_data.get('orcid'):
                print(f"      ORCID: https://orcid.org/{ref_data['orcid']}")
                if ref_data.get('orcid_discovered'):
                    print(f"         → Discovered via API (confidence: {ref_data.get('orcid_confidence', 0):.0%})")

            if ref_data.get('publication_count'):
                print(f"      📚 Publications: {ref_data['publication_count']} found")
                if ref_data.get('publications'):
                    print("      Recent publications:")
                    for pub in ref_data['publications'][:2]:
                        year = pub.get('year', 'N/A')
                        title = pub.get('title', 'Unknown')[:60]
                        print(f"         • {year}: {title}...")

            if ref_data.get('research_interests'):
                interests = ', '.join(ref_data['research_interests'][:3])
                print(f"      🔬 Research: {interests}")

    # Manuscript details
    manuscripts = results.get('manuscripts', {})
    if manuscripts:
        print(f"\n📄 MANUSCRIPTS ({len(manuscripts)} total):")
        for ms_id, ms_data in list(manuscripts.items())[:3]:  # Show first 3
            print(f"\n   📑 {ms_id}")
            print(f"      Title: {ms_data.get('title', 'N/A')[:80]}...")
            print(f"      Category: {ms_data.get('category', 'N/A')}")
            print(f"      Status: {ms_data.get('status', 'N/A')}")

            # Authors with ORCID
            authors = ms_data.get('authors', [])
            if authors:
                print(f"      Authors ({len(authors)}):")
                for author in authors[:2]:
                    print(f"         • {author.get('name', 'Unknown')}")
                    if author.get('email'):
                        print(f"           Email: {author['email']}")
                    if author.get('orcid'):
                        print(f"           ORCID: https://orcid.org/{author['orcid']}")
                        if author.get('orcid_discovered'):
                            print(f"           → Discovered via API")

            # Referees
            referee_ids = ms_data.get('referee_ids', [])
            if referee_ids:
                print(f"      Referees ({len(referee_ids)}):")
                for ref_id in referee_ids[:2]:
                    ref = referees.get(ref_id, {})
                    name = ref.get('name', ref_id)
                    status = ref.get('status', 'N/A')
                    print(f"         • {name} - {status}")
                    if ref.get('orcid'):
                        print(f"           ORCID: https://orcid.org/{ref['orcid']}")

    # ORCID enrichment summary
    print(f"\n🔬 ORCID ENRICHMENT SUMMARY:")

    # Count ORCID IDs
    referee_orcids = sum(1 for r in referees.values() if r.get('orcid'))
    referee_discovered = sum(1 for r in referees.values() if r.get('orcid_discovered'))

    print(f"   Referees with ORCID: {referee_orcids}/{len(referees)}")
    print(f"   • From journal: {referee_orcids - referee_discovered}")
    print(f"   • Discovered via API: {referee_discovered}")

    # Author ORCID count
    all_authors = {}
    for ms in manuscripts.values():
        for author in ms.get('authors', []):
            if author.get('name'):
                all_authors[author['name']] = author

    author_orcids = sum(1 for a in all_authors.values() if a.get('orcid'))
    author_discovered = sum(1 for a in all_authors.values() if a.get('orcid_discovered'))

    print(f"   Authors with ORCID: {author_orcids}/{len(all_authors)}")
    print(f"   • From journal: {author_orcids - author_discovered}")
    print(f"   • Discovered via API: {author_discovered}")

    # Publication data
    total_pubs = sum(r.get('publication_count', 0) for r in referees.values())
    referees_with_pubs = sum(1 for r in referees.values() if r.get('publication_count', 0) > 0)

    print(f"\n   📚 Publication Data:")
    print(f"   • Referees with publications: {referees_with_pubs}/{len(referees)}")
    print(f"   • Total publications found: {total_pubs}")

    print("\n" + "=" * 80)
    print("✅ EXTRACTION COMPLETE WITH FULL ORCID ENRICHMENT")
    print("=" * 80)

if __name__ == "__main__":
    # Run extraction
    results, output_file = run_extraction()

    # Display results
    display_results(results)

    print(f"\n📁 Full results saved to: {output_file}")
    print("   Use 'jq' or Python to explore the JSON data in detail")
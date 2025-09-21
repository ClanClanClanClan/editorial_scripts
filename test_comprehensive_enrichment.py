#!/usr/bin/env python3
"""Test comprehensive MF extraction with FULL ORCID enrichment for ALL entities."""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, 'production/src/extractors')
sys.path.insert(0, 'src/core')

def analyze_extraction_completeness(results):
    """Analyze the completeness of extraction."""
    print("\n" + "=" * 80)
    print("📊 EXTRACTION COMPLETENESS ANALYSIS")
    print("=" * 80)

    # Check each manuscript
    for ms in results:
        print(f"\n📄 MANUSCRIPT: {ms.get('id', 'Unknown')}")
        print("-" * 60)

        # Check funding
        funding = ms.get('funding_information', ms.get('funding'))
        if funding and funding != "Not specified" and funding != "There are no funders to report for this submission":
            print(f"✅ FUNDING: Found {len(funding.split('\\n'))} funding sources")
            # Parse funding details
            funding_lines = [l.strip() for l in funding.split('\n') if l.strip()]
            for line in funding_lines[:3]:
                print(f"   • {line[:80]}...")
        else:
            print("❌ FUNDING: Not extracted")

        # Check data availability
        data_avail = ms.get('data_availability', '')
        if data_avail and 'Files' in data_avail:
            print(f"✅ DATA AVAILABILITY: {data_avail.split('\\n')[0]}")
        else:
            print("❌ DATA AVAILABILITY: Not extracted")

        # Check conflict of interest
        coi = ms.get('conflict_of_interest', '')
        if coi:
            print(f"✅ CONFLICT OF INTEREST: {coi}")
        else:
            print("❌ CONFLICT OF INTEREST: Not extracted")

        # Check recommended/rejected reviewers
        rec_refs = ms.get('referee_recommendations', {})
        if rec_refs:
            rec_count = len(rec_refs.get('recommended_referees', []))
            opp_count = len(rec_refs.get('opposed_referees', []))
            if rec_count > 0 or opp_count > 0:
                print(f"✅ REVIEWER RECOMMENDATIONS: {rec_count} recommended, {opp_count} opposed")
                for rec in rec_refs.get('recommended_referees', [])[:2]:
                    print(f"   • Recommended: {rec.get('name', 'Unknown')} ({rec.get('institution', 'N/A')})")
                for opp in rec_refs.get('opposed_referees', [])[:2]:
                    print(f"   • Opposed: {opp.get('name', 'Unknown')} ({opp.get('institution', 'N/A')})")
            else:
                print("❌ REVIEWER RECOMMENDATIONS: None found")
        else:
            print("❌ REVIEWER RECOMMENDATIONS: Not extracted")

        # Check authors
        authors = ms.get('authors', [])
        print(f"\n👥 AUTHORS ({len(authors)}):")
        for i, author in enumerate(authors, 1):
            print(f"   {i}. {author.get('name', 'Unknown')}")
            print(f"      • Email: {author.get('email', 'Not found')}")
            print(f"      • Institution: {author.get('institution', 'Not found')}")
            print(f"      • Country: {author.get('country', 'Not found')}")
            print(f"      • ORCID: {author.get('orcid', 'Not found')}")
            if author.get('orcid_discovered'):
                print(f"        → Discovered via API")
            if author.get('publication_count'):
                print(f"      • Publications: {author['publication_count']} found")

        # Check referees
        referees = ms.get('referees', [])
        print(f"\n🔍 REFEREES ({len(referees)}):")
        for i, referee in enumerate(referees, 1):
            print(f"   {i}. {referee.get('name', 'Unknown')} - {referee.get('status', 'Unknown')}")
            print(f"      • Email: {'✅' if referee.get('email') else '❌ Not found'}")
            print(f"      • Institution: {referee.get('institution_parsed', referee.get('affiliation', 'Not found'))}")
            print(f"      • Country: {referee.get('country', 'Not found')}")
            print(f"      • ORCID: {referee.get('orcid', 'Not found')}")
            if referee.get('orcid_discovered'):
                print(f"        → Discovered via API")
            if referee.get('publication_count'):
                print(f"      • Publications: {referee['publication_count']} found")
            if referee.get('research_interests'):
                print(f"      • Research: {', '.join(referee['research_interests'][:3])}")

    # Overall statistics
    print("\n" + "=" * 80)
    print("📈 OVERALL STATISTICS")
    print("=" * 80)

    total_manuscripts = len(results)
    total_authors = sum(len(ms.get('authors', [])) for ms in results)
    total_referees = sum(len(ms.get('referees', [])) for ms in results)

    # Count ORCID coverage
    authors_with_orcid = sum(
        1 for ms in results
        for a in ms.get('authors', [])
        if a.get('orcid')
    )
    referees_with_orcid = sum(
        1 for ms in results
        for r in ms.get('referees', [])
        if r.get('orcid')
    )

    # Count discovered ORCIDs
    authors_discovered = sum(
        1 for ms in results
        for a in ms.get('authors', [])
        if a.get('orcid_discovered')
    )
    referees_discovered = sum(
        1 for ms in results
        for r in ms.get('referees', [])
        if r.get('orcid_discovered')
    )

    # Count countries
    authors_with_country = sum(
        1 for ms in results
        for a in ms.get('authors', [])
        if a.get('country')
    )
    referees_with_country = sum(
        1 for ms in results
        for r in ms.get('referees', [])
        if r.get('country')
    )

    print(f"\n📊 COVERAGE METRICS:")
    print(f"   • Total Manuscripts: {total_manuscripts}")
    print(f"   • Total Authors: {total_authors}")
    print(f"   • Total Referees: {total_referees}")
    print(f"\n🆔 ORCID COVERAGE:")
    print(f"   • Authors with ORCID: {authors_with_orcid}/{total_authors} ({authors_with_orcid/total_authors*100:.0f}%)")
    print(f"     - From journal: {authors_with_orcid - authors_discovered}")
    print(f"     - Discovered via API: {authors_discovered}")
    print(f"   • Referees with ORCID: {referees_with_orcid}/{total_referees} ({referees_with_orcid/total_referees*100:.0f}%)")
    print(f"     - From journal: {referees_with_orcid - referees_discovered}")
    print(f"     - Discovered via API: {referees_discovered}")
    print(f"\n🌍 COUNTRY COVERAGE:")
    print(f"   • Authors with country: {authors_with_country}/{total_authors} ({authors_with_country/total_authors*100:.0f}%)")
    print(f"   • Referees with country: {referees_with_country}/{total_referees} ({referees_with_country/total_referees*100:.0f}%)")

    # Count funding
    ms_with_funding = sum(
        1 for ms in results
        if ms.get('funding_information') and
        ms['funding_information'] not in ["Not specified", "There are no funders to report for this submission"]
    )
    print(f"\n💰 FUNDING:")
    print(f"   • Manuscripts with funding: {ms_with_funding}/{total_manuscripts}")

    # Count recommendations
    ms_with_recommendations = sum(
        1 for ms in results
        if ms.get('referee_recommendations') and
        (ms['referee_recommendations'].get('recommended_referees') or
         ms['referee_recommendations'].get('opposed_referees'))
    )
    print(f"\n👥 REVIEWER RECOMMENDATIONS:")
    print(f"   • Manuscripts with recommendations: {ms_with_recommendations}/{total_manuscripts}")

def run_comprehensive_extraction():
    """Run MF extraction with comprehensive enrichment."""
    print("🚀 RUNNING COMPREHENSIVE MF EXTRACTION WITH FULL ENRICHMENT")
    print("=" * 80)

    # Import and run extractor
    from mf_extractor import ComprehensiveMFExtractor

    extractor = ComprehensiveMFExtractor()

    # Ensure ORCID client is active
    if hasattr(extractor, 'orcid_client') and extractor.orcid_client:
        print("✅ ORCID client active - will search for ALL people without ORCIDs")
    else:
        print("⚠️ ORCID client not available - limited enrichment")

    # Run extraction
    result_data = extractor.extract_all()

    # Get the manuscripts list
    if isinstance(result_data, dict) and 'manuscripts' in result_data:
        # Convert manuscripts dict to list
        manuscripts = list(result_data['manuscripts'].values())
    else:
        # Assume it's the direct manuscripts list
        manuscripts = extractor.manuscripts

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'mf_comprehensive_enriched_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(manuscripts, f, indent=2, default=str)

    print(f"\n✅ Results saved to: {output_file}")

    return manuscripts, output_file

if __name__ == "__main__":
    # Run extraction
    results, output_file = run_comprehensive_extraction()

    # Analyze completeness
    analyze_extraction_completeness(results)

    print(f"\n📁 Full enriched results saved to: {output_file}")
    print("   Use 'jq' to explore the comprehensive data")
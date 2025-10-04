#!/usr/bin/env python3
"""Final comprehensive test with all fixes implemented."""

import json
import sys
import os
from datetime import datetime

# Add paths
sys.path.insert(0, "production/src/extractors")
sys.path.insert(0, "src/core")


def test_orcid_client():
    """Test ORCID client independently."""
    print("🧪 TESTING ORCID CLIENT")
    print("=" * 60)

    try:
        from orcid_client import ORCIDClient

        client = ORCIDClient()
        print("✅ ORCID client initialized")

        # Test with a referee that has ORCID
        test_person = {
            "name": "Gechun Liang",
            "orcid": "https://orcid.org/0000-0003-0752-0773",
            "institution": "University of Warwick",
        }

        print(f"\nTesting enrichment for: {test_person['name']}")
        enriched = client.enrich_person_profile(test_person)

        print(f"  • ORCID: {enriched.get('orcid', 'NOT FOUND')}")
        print(f"  • Publications: {enriched.get('publication_count', 0)}")
        print(f"  • Research Interests: {enriched.get('research_interests', [])[:3]}")
        print(f"  • Affiliations: {len(enriched.get('affiliation_history', []))}")
        print(f"  • Biography: {'YES' if enriched.get('biography') else 'NO'}")
        print(f"  • Other IDs: {list(enriched.get('other_ids', {}).keys())[:3]}")

        # Test without ORCID (should search)
        test_person2 = {"name": "Moris Strub", "institution": "Warwick Business School"}

        print(f"\nTesting search for: {test_person2['name']}")
        enriched2 = client.enrich_person_profile(test_person2)
        print(f"  • ORCID found: {'YES' if enriched2.get('orcid') else 'NO'}")
        if enriched2.get("orcid_discovered"):
            print(
                f"    → Discovered via API (confidence: {enriched2.get('orcid_confidence', 0):.0%})"
            )

        return True

    except Exception as e:
        print(f"❌ ORCID client test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_full_extraction():
    """Run full MF extraction with all enhancements."""
    print("\n" + "=" * 60)
    print("🚀 RUNNING FULL MF EXTRACTION WITH ALL FIXES")
    print("=" * 60)

    from mf_extractor import ComprehensiveMFExtractor

    extractor = ComprehensiveMFExtractor()

    # Check critical components
    print("\n📋 COMPONENT STATUS:")
    print(
        f"  • ORCID Client: {'✅' if hasattr(extractor, 'orcid_client') and extractor.orcid_client else '❌'}"
    )
    print(f"  • Gmail Manager: {'✅' if hasattr(extractor, 'gmail_manager') else '❌'}")
    print(f"  • Cache Manager: {'✅' if hasattr(extractor, 'cache_manager') else '❌'}")

    # Run extraction
    print("\n🔄 Starting extraction...")
    result_data = extractor.extract_all()

    # Get manuscripts
    if isinstance(result_data, dict) and "manuscripts" in result_data:
        manuscripts = list(result_data["manuscripts"].values())
    else:
        manuscripts = extractor.manuscripts

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"mf_final_comprehensive_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(manuscripts, f, indent=2, default=str)

    print(f"\n✅ Results saved to: {output_file}")

    return manuscripts, output_file


def analyze_results(manuscripts):
    """Analyze extraction results comprehensively."""
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE RESULTS ANALYSIS")
    print("=" * 60)

    # Overall counts
    total_ms = len(manuscripts)
    total_authors = sum(len(ms.get("authors", [])) for ms in manuscripts)
    total_referees = sum(len(ms.get("referees", [])) for ms in manuscripts)

    print(f"\n📈 OVERALL COUNTS:")
    print(f"  • Manuscripts: {total_ms}")
    print(f"  • Authors: {total_authors}")
    print(f"  • Referees: {total_referees}")

    # ORCID Coverage
    authors_with_orcid = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("orcid")
    )
    authors_discovered = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("orcid_discovered")
    )

    referees_with_orcid = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("orcid")
    )
    referees_discovered = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("orcid_discovered")
    )

    print(f"\n🆔 ORCID COVERAGE:")
    print(f"  AUTHORS:")
    print(
        f"    • With ORCID: {authors_with_orcid}/{total_authors} ({authors_with_orcid/max(total_authors,1)*100:.0f}%)"
    )
    print(f"    • From journal: {authors_with_orcid - authors_discovered}")
    print(f"    • Discovered via API: {authors_discovered}")
    print(f"  REFEREES:")
    print(
        f"    • With ORCID: {referees_with_orcid}/{total_referees} ({referees_with_orcid/max(total_referees,1)*100:.0f}%)"
    )
    print(f"    • From journal: {referees_with_orcid - referees_discovered}")
    print(f"    • Discovered via API: {referees_discovered}")

    # Country Coverage
    authors_with_country = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("country")
    )
    referees_with_country = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("country")
    )

    print(f"\n🌍 COUNTRY DATA:")
    print(
        f"  • Authors with country: {authors_with_country}/{total_authors} ({authors_with_country/max(total_authors,1)*100:.0f}%)"
    )
    print(
        f"  • Referees with country: {referees_with_country}/{total_referees} ({referees_with_country/max(total_referees,1)*100:.0f}%)"
    )

    # Publication Data
    total_publications = sum(
        r.get("publication_count", 0) for ms in manuscripts for r in ms.get("referees", [])
    )
    referees_with_pubs = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("publication_count", 0) > 0
    )

    print(f"\n📚 PUBLICATION DATA:")
    print(f"  • Referees with publications: {referees_with_pubs}/{total_referees}")
    print(f"  • Total publications found: {total_publications}")

    # Research Interests
    referees_with_interests = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("research_interests")
    )

    print(f"\n🔬 RESEARCH INTERESTS:")
    print(f"  • Referees with interests: {referees_with_interests}/{total_referees}")

    # Funding
    ms_with_funding = sum(
        1
        for ms in manuscripts
        if ms.get("funding_information") and "no funders" not in ms["funding_information"].lower()
    )

    print(f"\n💰 FUNDING:")
    print(f"  • Manuscripts with funding: {ms_with_funding}/{total_ms}")

    # Recommendations
    ms_with_recs = sum(
        1
        for ms in manuscripts
        if ms.get("referee_recommendations")
        and (
            ms["referee_recommendations"].get("recommended_referees")
            or ms["referee_recommendations"].get("opposed_referees")
        )
    )

    print(f"\n👥 REVIEWER RECOMMENDATIONS:")
    print(f"  • Manuscripts with recommendations: {ms_with_recs}/{total_ms}")

    # Sample detailed output
    if manuscripts:
        print(f"\n📄 SAMPLE MANUSCRIPT DETAIL:")
        ms = manuscripts[0]
        print(f"  ID: {ms.get('id')}")
        print(f"  Title: {ms.get('title', 'N/A')[:60]}...")

        if ms.get("authors"):
            print(f"\n  AUTHORS:")
            for i, author in enumerate(ms["authors"][:2], 1):
                print(f"    {i}. {author.get('name', 'Unknown')}")
                print(f"       • Email: {author.get('email', 'NOT FOUND')}")
                print(f"       • Country: {author.get('country', 'NOT FOUND')}")
                print(f"       • ORCID: {'YES' if author.get('orcid') else 'NO'}")
                if author.get("orcid_discovered"):
                    print(f"         → Discovered via API")
                if author.get("publication_count"):
                    print(f"       • Publications: {author['publication_count']}")

        if ms.get("referees"):
            print(f"\n  REFEREES:")
            for i, referee in enumerate(ms["referees"][:2], 1):
                print(
                    f"    {i}. {referee.get('name', 'Unknown')} ({referee.get('status', 'Unknown')})"
                )
                print(f"       • Country: {referee.get('country', 'NOT FOUND')}")
                print(f"       • ORCID: {'YES' if referee.get('orcid') else 'NO'}")
                if referee.get("orcid_discovered"):
                    print(f"         → Discovered via API")
                if referee.get("publication_count"):
                    print(f"       • Publications: {referee['publication_count']}")
                if referee.get("research_interests"):
                    print(f"       • Research: {', '.join(referee['research_interests'][:3])}")

        if ms.get("referee_recommendations"):
            recs = ms["referee_recommendations"]
            if recs.get("recommended_referees"):
                print(f"\n  RECOMMENDED REVIEWERS: {len(recs['recommended_referees'])}")
                for rec in recs["recommended_referees"][:2]:
                    print(f"    • {rec.get('name', 'Unknown')}")
            if recs.get("opposed_referees"):
                print(f"\n  OPPOSED REVIEWERS: {len(recs['opposed_referees'])}")
                for opp in recs["opposed_referees"][:2]:
                    print(f"    • {opp.get('name', 'Unknown')}")


if __name__ == "__main__":
    print("🎯 FINAL COMPREHENSIVE TEST WITH ALL FIXES")
    print("=" * 60)

    # Test ORCID client first
    orcid_ok = test_orcid_client()

    if orcid_ok:
        print("\n✅ ORCID client test passed - proceeding with extraction")
    else:
        print("\n⚠️ ORCID client has issues but continuing anyway")

    # Run full extraction
    try:
        manuscripts, output_file = run_full_extraction()

        # Analyze results
        analyze_results(manuscripts)

        print("\n" + "=" * 60)
        print("✅ EXTRACTION COMPLETE")
        print(f"📁 Full results saved to: {output_file}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback

        traceback.print_exc()

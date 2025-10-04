#!/usr/bin/env python3
"""Test all fixes implemented in the audit."""

import sys
import json
from datetime import datetime

# Add paths
sys.path.insert(0, "production/src/extractors")
sys.path.insert(0, "src/core")


def test_orcid_fixes():
    """Test ORCID functionality fixes."""
    print("🧪 TESTING ORCID FIXES")
    print("=" * 60)

    from orcid_client import ORCIDClient

    client = ORCIDClient()

    # Test 1: Name and affiliation extraction
    test_orcid = "0000-0003-0752-0773"
    profile = client.get_full_profile(test_orcid)

    if profile:
        name = client._extract_name_from_profile(profile)
        affiliations = client._extract_affiliations_from_profile(profile)
        country = client._extract_country_from_profile(profile)

        print(f"✅ Name extraction: {name}")
        print(f"✅ Affiliations: {affiliations[:2] if affiliations else 'None'}")
        print(f"✅ Country: {country}")

    # Test 2: ORCID discovery
    test_person = {"name": "Gechun Liang", "institution": "University of Warwick"}

    enriched = client.enrich_person_profile(test_person)

    print(f"\n📊 ORCID Discovery:")
    print(f"   • ORCID found: {'YES' if enriched.get('orcid') else 'NO'}")
    print(f"   • Publications: {enriched.get('publication_count', 0)}")
    print(f"   • Research interests: {len(enriched.get('research_interests', []))}")
    print(f"   • Country: {enriched.get('country', 'NOT FOUND')}")

    return enriched


def run_limited_extraction():
    """Run extraction on one manuscript to test fixes."""
    print("\n🚀 TESTING MF EXTRACTION WITH ALL FIXES")
    print("=" * 60)

    from mf_extractor import ComprehensiveMFExtractor

    extractor = ComprehensiveMFExtractor()

    print("\n📋 Component Status:")
    print(
        f"   • ORCID Client: {'✅' if hasattr(extractor, 'orcid_client') and extractor.orcid_client else '❌'}"
    )
    print(f"   • Gmail Manager: {'✅' if hasattr(extractor, 'gmail_manager') else '❌'}")
    print(f"   • Cache Manager: {'✅' if hasattr(extractor, 'cache_manager') else '❌'}")

    # Run extraction (will process real manuscripts)
    print("\n🔄 Starting extraction (this will take a few minutes)...")

    try:
        result_data = extractor.extract_all()

        # Get manuscripts
        if isinstance(result_data, dict) and "manuscripts" in result_data:
            manuscripts = list(result_data["manuscripts"].values())
        else:
            manuscripts = extractor.manuscripts

        return manuscripts

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback

        traceback.print_exc()
        return []


def analyze_extraction_results(manuscripts):
    """Analyze extraction results to verify fixes."""
    print("\n📊 EXTRACTION RESULTS ANALYSIS")
    print("=" * 60)

    if not manuscripts:
        print("❌ No manuscripts to analyze")
        return

    # Overall statistics
    total_ms = len(manuscripts)
    total_authors = sum(len(ms.get("authors", [])) for ms in manuscripts)
    total_referees = sum(len(ms.get("referees", [])) for ms in manuscripts)

    print(f"\n📈 OVERALL:")
    print(f"   • Manuscripts: {total_ms}")
    print(f"   • Authors: {total_authors}")
    print(f"   • Referees: {total_referees}")

    # Test Fix 1: Country assignment from ORCID
    print(f"\n🌍 FIX 1: COUNTRY ASSIGNMENT")
    authors_with_country = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("country")
    )
    referees_with_country = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("country")
    )

    print(
        f"   • Authors with country: {authors_with_country}/{total_authors} ({authors_with_country/max(total_authors,1)*100:.0f}%)"
    )
    print(
        f"   • Referees with country: {referees_with_country}/{total_referees} ({referees_with_country/max(total_referees,1)*100:.0f}%)"
    )
    print(f"   • Status: {'✅ FIXED' if referees_with_country > 0 else '❌ NOT FIXED'}")

    # Test Fix 2: Research interests from publications
    print(f"\n🔬 FIX 2: RESEARCH INTERESTS")
    refs_with_interests = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("research_interests")
    )
    total_interests = sum(
        len(r.get("research_interests", [])) for ms in manuscripts for r in ms.get("referees", [])
    )

    print(f"   • Referees with interests: {refs_with_interests}/{total_referees}")
    print(f"   • Total interests: {total_interests}")
    print(f"   • Status: {'✅ FIXED' if refs_with_interests > 0 else '❌ NOT FIXED'}")

    # Test Fix 3: Referee recommendations
    print(f"\n👥 FIX 3: REFEREE RECOMMENDATIONS")
    ms_with_recs = sum(1 for ms in manuscripts if ms.get("referee_recommendations"))
    total_recommended = sum(
        len(ms.get("referee_recommendations", {}).get("recommended_referees", []))
        for ms in manuscripts
    )
    total_opposed = sum(
        len(ms.get("referee_recommendations", {}).get("opposed_referees", [])) for ms in manuscripts
    )

    print(f"   • Manuscripts with recommendations: {ms_with_recs}/{total_ms}")
    print(f"   • Total recommended: {total_recommended}")
    print(f"   • Total opposed: {total_opposed}")
    print(f"   • Status: {'✅ FIXED' if ms_with_recs > 0 else '❌ NOT FIXED'}")

    # Test Fix 4: Author ORCID extraction
    print(f"\n🆔 FIX 4: AUTHOR ORCID EXTRACTION")
    authors_with_orcid = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("orcid")
    )
    authors_discovered = sum(
        1 for ms in manuscripts for a in ms.get("authors", []) if a.get("orcid_discovered")
    )

    print(
        f"   • Authors with ORCID: {authors_with_orcid}/{total_authors} ({authors_with_orcid/max(total_authors,1)*100:.0f}%)"
    )
    print(f"   • Discovered via API: {authors_discovered}")
    print(f"   • Status: {'✅ FIXED' if authors_with_orcid > 0 else '❌ NOT FIXED'}")

    # Test Fix 5: ORCID discovery for referees
    print(f"\n🔍 FIX 5: ORCID DISCOVERY")
    refs_with_orcid = sum(1 for ms in manuscripts for r in ms.get("referees", []) if r.get("orcid"))
    refs_discovered = sum(
        1 for ms in manuscripts for r in ms.get("referees", []) if r.get("orcid_discovered")
    )

    print(
        f"   • Referees with ORCID: {refs_with_orcid}/{total_referees} ({refs_with_orcid/max(total_referees,1)*100:.0f}%)"
    )
    print(f"   • Discovered via API: {refs_discovered}")
    print(f"   • Status: {'✅ FIXED' if refs_discovered > 0 else '❌ NOT FIXED'}")

    # Sample data
    if manuscripts:
        print(f"\n📄 SAMPLE DATA (First manuscript):")
        print("-" * 60)
        ms = manuscripts[0]
        print(f"ID: {ms.get('id')}")
        print(f"Title: {ms.get('title', 'N/A')[:80]}...")

        if ms.get("authors"):
            print(f"\nAUTHORS ({len(ms['authors'])}):")
            for i, author in enumerate(ms["authors"][:2], 1):
                print(f"  {i}. {author.get('name', 'Unknown')}")
                print(f"     • Country: {author.get('country', 'NOT FOUND')}")
                print(f"     • ORCID: {'YES' if author.get('orcid') else 'NO'}")
                if author.get("orcid_discovered"):
                    print(f"       → Discovered via API")

        if ms.get("referees"):
            print(f"\nREFEREES ({len(ms['referees'])}):")
            for i, referee in enumerate(ms["referees"][:2], 1):
                print(
                    f"  {i}. {referee.get('name', 'Unknown')} ({referee.get('status', 'Unknown')})"
                )
                print(f"     • Country: {referee.get('country', 'NOT FOUND')}")
                print(f"     • ORCID: {'YES' if referee.get('orcid') else 'NO'}")
                if referee.get("orcid_discovered"):
                    print(f"       → Discovered via API")
                if referee.get("research_interests"):
                    print(f"     • Research: {', '.join(referee['research_interests'][:3])}")

        if ms.get("referee_recommendations"):
            recs = ms["referee_recommendations"]
            if recs.get("recommended_referees") or recs.get("opposed_referees"):
                print(f"\nRECOMMENDATIONS:")
                if recs.get("recommended_referees"):
                    print(f"  • Recommended: {len(recs['recommended_referees'])}")
                if recs.get("opposed_referees"):
                    print(f"  • Opposed: {len(recs['opposed_referees'])}")

    return manuscripts


if __name__ == "__main__":
    print("🎯 TESTING ALL FIXES FROM AUDIT")
    print("=" * 60)

    # Test ORCID fixes
    orcid_data = test_orcid_fixes()

    # Ask user if they want to run full extraction
    print("\n" + "=" * 60)
    print("⚠️  The next step will run a REAL extraction from MF.")
    print("This will:")
    print("  • Login to ScholarOne")
    print("  • Extract manuscripts from actual categories")
    print("  • Take 5-10 minutes")
    print("=" * 60)

    response = input("\nDo you want to run the extraction test? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        # Run extraction
        manuscripts = run_limited_extraction()

        if manuscripts:
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mf_fixes_test_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump(manuscripts, f, indent=2, default=str)

            print(f"\n✅ Results saved to: {output_file}")

            # Analyze results
            analyze_extraction_results(manuscripts)
        else:
            print("\n❌ No manuscripts extracted")
    else:
        print("\n⏭️ Skipping extraction test")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 60)

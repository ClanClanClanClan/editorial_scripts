#!/usr/bin/env python3
"""Test MF extraction with ORCID enrichment - shows EVERYTHING extracted."""

import sys
import os
import time
import json
from datetime import datetime

sys.path.append("production/src/extractors")

from mf_extractor import ComprehensiveMFExtractor


def display_referee_data(referee):
    """Display comprehensive referee data."""
    print(f"\n      📌 REFEREE: {referee.get('name', 'Unknown')}")
    print(f"         Status: {referee.get('status', 'Unknown')}")

    # Basic info
    if referee.get("email"):
        print(f"         📧 Email: {referee['email']}")

    if referee.get("institution_parsed"):
        print(f"         🏛️ Institution: {referee['institution_parsed']}")
    elif referee.get("affiliation"):
        print(f"         🏛️ Affiliation: {referee['affiliation']}")

    if referee.get("department"):
        print(f"         🏢 Department: {referee['department']}")

    if referee.get("country"):
        print(f"         🌍 Country: {referee['country']}")

    # ORCID data
    if referee.get("orcid"):
        print(f"         🔗 ORCID: https://orcid.org/{referee['orcid']}")
        if referee.get("orcid_discovered"):
            print(
                f"            → Discovered via ORCID API (confidence: {referee.get('orcid_confidence', 0):.0%})"
            )

    # Publications
    if referee.get("publication_count"):
        print(f"         📚 Publications: {referee['publication_count']} found")
        if referee.get("publications"):
            print(f"         📝 Recent publications:")
            for pub in referee["publications"][:3]:
                year = pub.get("year", "N/A")
                title = pub.get("title", "Unknown")[:60]
                journal = pub.get("journal", "")
                print(f"            • {year}: {title}...")
                if journal:
                    print(f"              Journal: {journal}")

    # Publication metrics
    if referee.get("publication_metrics"):
        metrics = referee["publication_metrics"]
        print(f"         📊 Publication metrics:")
        print(f"            • Years active: {metrics.get('years_active', 0)}")
        print(f"            • First publication: {metrics.get('first_publication', 'N/A')}")
        print(f"            • Latest publication: {metrics.get('latest_publication', 'N/A')}")
        print(f"            • Unique journals: {metrics.get('unique_journals', 0)}")

    # Research interests
    if referee.get("research_interests"):
        interests = referee["research_interests"][:5]
        print(f"         🔬 Research interests: {', '.join(interests)}")

    # Affiliation history
    if referee.get("affiliation_history"):
        current = [a for a in referee["affiliation_history"] if a.get("current")]
        if current:
            curr = current[0]
            print(
                f"         🏛️ Current position: {curr.get('role', 'Unknown')} at {curr.get('organization', 'Unknown')}"
            )

    # External IDs
    if referee.get("external_ids"):
        print(f"         🆔 Other IDs:")
        for id_type, id_value in referee["external_ids"].items():
            print(f"            • {id_type}: {id_value}")

    # Report info
    if referee.get("report"):
        report = referee["report"]
        if report.get("pdf_downloaded"):
            print(f"         📄 Report: Downloaded ({report.get('pdf_path', 'path unknown')})")
            if report.get("recommendation"):
                print(f"            Recommendation: {report['recommendation']}")


def display_author_data(author):
    """Display comprehensive author data."""
    print(f"\n      ✍️ AUTHOR: {author.get('name', 'Unknown')}")

    if author.get("email"):
        print(f"         📧 Email: {author['email']}")

    if author.get("institution"):
        print(f"         🏛️ Institution: {author['institution']}")

    if author.get("country"):
        print(f"         🌍 Country: {author['country']}")

    # ORCID data
    if author.get("orcid"):
        print(f"         🔗 ORCID: https://orcid.org/{author['orcid']}")
        if author.get("orcid_discovered"):
            print(
                f"            → Discovered via ORCID API (confidence: {author.get('orcid_confidence', 0):.0%})"
            )

    # Publications
    if author.get("publication_count"):
        print(f"         📚 Publications: {author['publication_count']} found")
        if author.get("publications"):
            for pub in author["publications"][:2]:
                year = pub.get("year", "N/A")
                title = pub.get("title", "Unknown")[:50]
                print(f"            • {year}: {title}...")

    # Research interests
    if author.get("research_interests"):
        interests = author["research_interests"][:3]
        print(f"         🔬 Research interests: {', '.join(interests)}")


def display_manuscript_data(manuscript):
    """Display ALL manuscript data."""
    print("\n" + "=" * 80)
    print(f"📄 MANUSCRIPT: {manuscript.get('id', 'Unknown')}")
    print("=" * 80)

    # Basic info
    print(f"\n   📋 BASIC INFORMATION:")
    print(f"      Title: {manuscript.get('title', 'Unknown')[:70]}...")
    print(f"      Category: {manuscript.get('category', 'Unknown')}")
    print(f"      Status: {manuscript.get('status', 'Unknown')}")
    print(f"      Submitted: {manuscript.get('submission_date', 'Unknown')}")
    print(f"      In Review: {manuscript.get('in_review_time', 'Unknown')}")
    print(f"      Article Type: {manuscript.get('article_type', 'Unknown')}")

    # Keywords
    if manuscript.get("keywords"):
        print(f"\n   🏷️ KEYWORDS:")
        for kw in manuscript["keywords"][:10]:
            print(f"      • {kw}")

    # Abstract
    if manuscript.get("abstract"):
        print(f"\n   📝 ABSTRACT:")
        abstract = manuscript["abstract"][:200]
        print(f"      {abstract}...")

    # Authors
    if manuscript.get("authors"):
        print(f"\n   ✍️ AUTHORS ({len(manuscript['authors'])} total):")
        for author in manuscript["authors"]:
            display_author_data(author)

    # Referees
    if manuscript.get("referees"):
        print(f"\n   👥 REFEREES ({len(manuscript['referees'])} total):")
        for referee in manuscript["referees"]:
            display_referee_data(referee)

    # Documents
    if manuscript.get("documents"):
        docs = manuscript["documents"]
        print(f"\n   📁 DOCUMENTS:")
        if docs.get("pdf_url"):
            print(f"      • Main PDF: Available")
        if docs.get("cover_letter_url"):
            print(f"      • Cover Letter: Available")
        if docs.get("supplementary_files"):
            print(f"      • Supplementary Files: {len(docs['supplementary_files'])}")

    # Metadata
    if manuscript.get("metadata"):
        meta = manuscript["metadata"]
        print(f"\n   ℹ️ METADATA:")
        if meta.get("word_count"):
            print(f"      • Word Count: {meta['word_count']}")
        if meta.get("figure_count"):
            print(f"      • Figures: {meta['figure_count']}")
        if meta.get("table_count"):
            print(f"      • Tables: {meta['table_count']}")
        if meta.get("funding_info"):
            print(f"      • Funding: {meta['funding_info'][:100]}...")

    # Timeline
    if manuscript.get("timeline"):
        timeline = manuscript["timeline"]
        if timeline.get("events"):
            print(f"\n   📅 TIMELINE ({len(timeline['events'])} events):")
            # Show first and last 2 events
            events = timeline["events"]
            for event in events[:2]:
                print(f"      • {event.get('date', 'N/A')}: {event.get('action', 'Unknown')}")
            if len(events) > 4:
                print(f"      ... ({len(events) - 4} more events) ...")
            for event in events[-2:]:
                print(f"      • {event.get('date', 'N/A')}: {event.get('action', 'Unknown')}")


def test_mf_with_orcid():
    """Run comprehensive MF extraction with ORCID enrichment."""
    print("🚀 COMPREHENSIVE MF EXTRACTION WITH ORCID ENRICHMENT")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    extractor = None
    start_time = time.time()

    try:
        # Initialize
        print("\n⚙️ Initializing MF extractor with ORCID...")
        extractor = ComprehensiveMFExtractor()
        print("✅ Initialized successfully")

        # Run extraction
        print("\n📊 Starting extraction...")
        extractor.extract_all()

        elapsed = time.time() - start_time

        # Display results
        if extractor.manuscripts:
            print(f"\n{'=' * 80}")
            print(f"✅ EXTRACTION COMPLETE")
            print(f"{'=' * 80}")
            print(f"⏱️ Time taken: {elapsed:.1f} seconds")
            print(f"📊 Total manuscripts: {len(extractor.manuscripts)}")

            # Group by category
            by_category = {}
            for ms in extractor.manuscripts:
                cat = ms.get("category", "Unknown")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(ms)

            print(f"\n📦 Manuscripts by category:")
            for cat, manuscripts in by_category.items():
                print(f"   {cat}: {len(manuscripts)} manuscripts")

            # Display each manuscript in detail
            print(f"\n{'=' * 80}")
            print("📋 DETAILED EXTRACTION RESULTS")
            print("=" * 80)

            for ms in extractor.manuscripts:
                display_manuscript_data(ms)

            # Save comprehensive results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mf_orcid_results_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump(
                    {
                        "extraction_date": datetime.now().isoformat(),
                        "duration_seconds": elapsed,
                        "total_manuscripts": len(extractor.manuscripts),
                        "categories": list(by_category.keys()),
                        "manuscripts": extractor.manuscripts,
                    },
                    f,
                    indent=2,
                    default=str,
                )

            print(f"\n💾 Complete results saved to: {output_file}")

            # Summary statistics
            print(f"\n📊 ENRICHMENT STATISTICS:")

            total_referees = sum(len(ms.get("referees", [])) for ms in extractor.manuscripts)
            referees_with_orcid = sum(
                1
                for ms in extractor.manuscripts
                for ref in ms.get("referees", [])
                if ref.get("orcid")
            )
            discovered_orcids = sum(
                1
                for ms in extractor.manuscripts
                for ref in ms.get("referees", [])
                if ref.get("orcid_discovered")
            )

            total_authors = sum(len(ms.get("authors", [])) for ms in extractor.manuscripts)
            authors_with_orcid = sum(
                1
                for ms in extractor.manuscripts
                for auth in ms.get("authors", [])
                if auth.get("orcid")
            )

            total_publications = sum(
                ref.get("publication_count", 0)
                for ms in extractor.manuscripts
                for ref in ms.get("referees", [])
            )

            print(f"   Referees: {total_referees} total")
            print(f"      • With ORCID: {referees_with_orcid}")
            print(f"      • ORCID discovered: {discovered_orcids}")
            print(f"   Authors: {total_authors} total")
            print(f"      • With ORCID: {authors_with_orcid}")
            print(f"   Publications found: {total_publications} total")

            return True
        else:
            print("\n⚠️ No manuscripts extracted")
            return False

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️ Interrupted after {elapsed:.1f}s")
        if extractor and extractor.manuscripts:
            print(f"   Partial: {len(extractor.manuscripts)} manuscripts")
            with open("mf_orcid_partial.json", "w") as f:
                json.dump(extractor.manuscripts, f, indent=2, default=str)
            print("   💾 Partial results saved to mf_orcid_partial.json")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if extractor:
            try:
                print("\n🧹 Cleaning up...")
                extractor.cleanup()
                print("✅ Cleanup done")
            except:
                pass


if __name__ == "__main__":
    success = test_mf_with_orcid()
    sys.exit(0 if success else 1)

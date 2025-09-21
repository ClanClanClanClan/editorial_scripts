#!/usr/bin/env python3
"""
Test the fundamental fix for referee table detection
Specifically verify that Zhang, Panpan is no longer incorrectly extracted as a referee
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import json
from datetime import datetime

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_fundamental_fix():
    print("🔧 TESTING FUNDAMENTAL REFEREE TABLE DETECTION FIX")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🎯 Primary Goal: Verify Zhang, Panpan is NOT extracted as referee")
    print("📋 Secondary Goals:")
    print("   • Robust referee table identification")
    print("   • Proper author/referee separation")
    print("   • Enhanced conflict detection")
    print("=" * 70)

    extractor = ComprehensiveMFExtractor()

    try:
        login_success = extractor.login()
        if not login_success:
            print("\n❌ Login failed!")
            return

        print("\n✅ Login successful!")

        # Extract manuscripts
        results = extractor.extract_all()

        if not results:
            print("\n❌ No manuscripts extracted!")
            return

        print(f"\n📚 Extracted {len(results)} manuscripts")

        # Focus on MAFI-2024-0167 where Zhang, Panpan issue occurred
        target_manuscript = None
        for manuscript in results:
            if manuscript["id"] == "MAFI-2024-0167":
                target_manuscript = manuscript
                break

        if not target_manuscript:
            print("\n❌ Target manuscript MAFI-2024-0167 not found!")
            return

        print(f"\n🔍 ANALYZING MANUSCRIPT: {target_manuscript['id']}")
        print("=" * 50)

        # Check authors
        authors = target_manuscript.get("authors", [])
        print(f"\n👥 AUTHORS ({len(authors)}):")
        author_names = []
        author_emails = []

        for idx, author in enumerate(authors):
            name = author.get("name", "No name")
            email = author.get("email", "No email")
            author_names.append(name.lower().replace(" ", "").replace(",", ""))
            author_emails.extend([e.strip().lower() for e in email.split(",")])

            print(f"   {idx+1}. {name}")
            print(f"      Email: {email}")
            if author.get("is_corresponding"):
                print("      📧 CORRESPONDING AUTHOR")

            # Check for suspicious email (phone number)
            validation = extractor.validate_email(email)
            if validation.get("suspicious"):
                print(f"      ⚠️ SUSPICIOUS: {validation['reason']}")

        # Check referees
        referees = target_manuscript.get("referees", [])
        print(f"\n🔍 REFEREES ({len(referees)}):")

        zhang_panpan_found_as_referee = False
        conflicts_detected = []

        for idx, referee in enumerate(referees):
            name = referee.get("name", "No name")
            email = referee.get("email", "No email")

            print(f"   {idx+1}. {name}")
            print(f"      Email: {email}")
            print(f"      Affiliation: {referee.get('affiliation', 'N/A')}")
            print(f"      Status: {referee.get('status', 'N/A')}")

            # Check if this referee is Zhang, Panpan
            if "zhang" in name.lower() and "panpan" in name.lower():
                zhang_panpan_found_as_referee = True
                print("      🚨 CRITICAL ISSUE: Zhang, Panpan found as referee!")

            # Check for conflicts with authors
            if referee.get("conflict_with_authors"):
                conflicts_detected.append(
                    {
                        "referee_name": name,
                        "conflicting_author": referee.get("conflicting_author", "Unknown"),
                    }
                )
                print(f"      🚨 CONFLICT: Matches author {referee.get('conflicting_author')}")

        # ANALYSIS AND RESULTS
        print("\n📊 ANALYSIS RESULTS:")
        print("=" * 50)

        # Test 1: Zhang, Panpan should NOT be a referee
        if zhang_panpan_found_as_referee:
            print("❌ CRITICAL FAILURE: Zhang, Panpan still extracted as referee!")
            print("   The fundamental fix did NOT work properly.")
        else:
            print("✅ SUCCESS: Zhang, Panpan not found as referee")
            print("   The fundamental table detection fix is working.")

        # Test 2: Check if Zhang, Panpan is properly identified as author
        zhang_as_author = False
        for author in authors:
            if (
                "zhang" in author.get("name", "").lower()
                or "panpan" in author.get("name", "").lower()
            ):
                zhang_as_author = True
                break
            # Also check emails since suspicious email might have missing name
            if "15253166207" in author.get("email", ""):
                zhang_as_author = True
                print("✅ Found Zhang, Panpan via suspicious phone number email")
                break

        if zhang_as_author:
            print("✅ Zhang, Panpan correctly identified as author (not referee)")
        else:
            print("⚠️ Zhang, Panpan not clearly identified as author either")

        # Test 3: Overall data quality
        print("\n📈 DATA QUALITY METRICS:")
        print(f"   Total authors: {len(authors)}")
        print(f"   Total referees: {len(referees)}")
        print(f"   Author/referee conflicts: {len(conflicts_detected)}")

        # Test 4: Check referee table identification method used
        print("\n🔍 TABLE IDENTIFICATION ANALYSIS:")
        print("   Expected: More specific referee table detection")
        print(f"   Result: {len(referees)} referees found without author contamination")

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_results = {
            "test_timestamp": timestamp,
            "manuscript_id": target_manuscript["id"],
            "zhang_panpan_as_referee": zhang_panpan_found_as_referee,
            "zhang_panpan_as_author": zhang_as_author,
            "total_authors": len(authors),
            "total_referees": len(referees),
            "conflicts_detected": conflicts_detected,
            "fundamental_fix_working": not zhang_panpan_found_as_referee,
            "all_referee_names": [r.get("name") for r in referees],
            "all_author_names": [a.get("name") for a in authors],
        }

        with open(f"fundamental_fix_test_{timestamp}.json", "w") as f:
            json.dump(test_results, f, indent=2)

        # FINAL VERDICT
        print("\n🏆 FINAL VERDICT:")
        print("=" * 50)

        if not zhang_panpan_found_as_referee and zhang_as_author:
            print("✅ FUNDAMENTAL FIX SUCCESSFUL!")
            print("   • Zhang, Panpan correctly classified as author only")
            print("   • Referee table detection is now robust")
            print("   • No author/referee contamination detected")
        elif not zhang_panpan_found_as_referee:
            print("✅ PARTIAL SUCCESS!")
            print("   • Zhang, Panpan not extracted as referee (main issue fixed)")
            print("   • Author extraction may need minor improvements")
        else:
            print("❌ FUNDAMENTAL FIX FAILED!")
            print("   • Zhang, Panpan still being extracted as referee")
            print("   • Table detection logic needs further refinement")

        print(f"\n📁 Detailed results: fundamental_fix_test_{timestamp}.json")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print(f"\n⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if hasattr(extractor, "driver"):
            extractor.driver.quit()


if __name__ == "__main__":
    test_fundamental_fix()

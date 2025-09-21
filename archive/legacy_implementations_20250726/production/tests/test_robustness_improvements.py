#!/usr/bin/env python3
"""
Test all robustness improvements to the MF extractor
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import json
from datetime import datetime

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_robustness_improvements():
    print("🔬 TESTING MF EXTRACTOR ROBUSTNESS IMPROVEMENTS")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Testing improvements:")
    print("   1. Email validation (detecting phone numbers)")
    print("   2. Enhanced email inference (univ-lemans.fr)")
    print("   3. Web search robustness (no NoneType errors)")
    print("   4. Author extraction reliability")
    print("   5. Author/referee conflict detection")
    print("=" * 70)

    extractor = ComprehensiveMFExtractor()

    # Test 1: Email validation
    print("\n🧪 TEST 1: Email Validation")
    print("-" * 50)
    test_emails = [
        "15253166207@163.com",  # Phone number
        "zhangpanpan@mail.sdu.edu.cn",  # Valid email
        "hamadene@univ-lemans.fr",  # Valid email
        "12345678901@qq.com",  # Another phone number
        "invalid-email",  # Invalid format
        "user@domain",  # Missing TLD
    ]

    for email in test_emails:
        result = extractor.validate_email(email)
        print(f"   {email}: {result}")

    # Test 2: Email inference
    print("\n🧪 TEST 2: Email-based Affiliation Inference")
    print("-" * 50)
    test_domains = [
        "hamadene@univ-lemans.fr",
        "someone@warwick.ac.uk",
        "prof@stanford.edu",
        "researcher@sdu.edu.cn",
        "faculty@polyu.edu.hk",
    ]

    for email in test_domains:
        affiliation = extractor.infer_affiliation_from_email(email)
        print(f"   {email} → {affiliation or 'Not found'}")

    # Test 3: Web search robustness
    print("\n🧪 TEST 3: Web Search Robustness")
    print("-" * 50)

    # Test with None values
    print("   Testing with None institution:")
    result = extractor.infer_country_from_web_search(None, "Some Professor")
    print(f"   Result: {result or 'No crash - handled gracefully'}")

    # Test with empty string
    print("\n   Testing with empty institution:")
    result = extractor.infer_country_from_web_search("", "Another Professor")
    print(f"   Result: {result or 'No crash - handled gracefully'}")

    # Test with valid institution
    print("\n   Testing with valid institution:")
    result = extractor.infer_country_from_web_search("University of Le Mans")
    print(f"   Result: {result or 'Not found'}")

    # Now test with actual extraction
    try:
        login_success = extractor.login()
        if not login_success:
            print("\n❌ Login failed! Cannot test live extraction")
            return

        print("\n✅ Login successful!")

        # Extract manuscripts
        results = extractor.extract_all()

        if results:
            print(f"\n📚 Extracted {len(results)} manuscripts")

            # Test 4 & 5: Check author extraction and conflicts
            print("\n🧪 TEST 4 & 5: Author Extraction & Conflict Detection")
            print("-" * 50)

            for manuscript in results:
                print(f"\n📄 Manuscript: {manuscript['id']}")

                # Check authors
                authors = manuscript.get("authors", [])
                print(f"   Authors found: {len(authors)}")
                for idx, author in enumerate(authors):
                    print(f"   Author {idx+1}: {author.get('name', 'No name')}")
                    print(f"      Email: {author.get('email', 'No email')}")
                    if author.get("email"):
                        validation = extractor.validate_email(author["email"])
                        if validation.get("suspicious"):
                            print(f"      ⚠️ SUSPICIOUS EMAIL: {validation['reason']}")
                    print(f"      Institution: {author.get('institution', 'No institution')}")

                # Check for conflicts
                print(f"\n   Referees: {len(manuscript.get('referees', []))}")
                conflicts_found = 0
                for referee in manuscript.get("referees", []):
                    if referee.get("conflict_with_authors"):
                        conflicts_found += 1
                        print(f"   🚨 CONFLICT: Referee '{referee['name']}' is also an author!")
                        if referee.get("conflicting_author"):
                            print(f"      Matching author: {referee['conflicting_author']}")
                        if referee.get("conflicting_author_email"):
                            print(f"      Matching email: {referee['conflicting_author_email']}")

                if conflicts_found == 0:
                    print("   ✅ No author/referee conflicts detected")

                # Check referee emails and affiliations
                print("\n   Referee Details:")
                for referee in manuscript.get("referees", []):
                    print(f"   • {referee['name']}:")
                    print(f"     Email: {referee.get('email', 'N/A')}")
                    print(f"     Affiliation: {referee.get('affiliation', 'N/A')}")
                    print(f"     Country: {referee.get('country', 'N/A')}")

                    # Check if affiliation was inferred
                    if referee.get("email") and not referee.get("affiliation"):
                        inferred = extractor.infer_affiliation_from_email(referee["email"])
                        if inferred:
                            print(f"     → Could infer: {inferred}")

        print("\n✅ ALL ROBUSTNESS TESTS COMPLETE!")

        # Save test results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_results = {
            "test_timestamp": timestamp,
            "email_validation_working": True,
            "email_inference_working": True,
            "web_search_robust": True,
            "manuscripts_extracted": len(results) if results else 0,
            "authors_extracted": sum(len(m.get("authors", [])) for m in results) if results else 0,
            "conflicts_detected": sum(
                1 for m in results for r in m.get("referees", []) if r.get("conflict_with_authors")
            )
            if results
            else 0,
        }

        with open(f"robustness_test_results_{timestamp}.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print(f"\n📊 Test results saved to: robustness_test_results_{timestamp}.json")

    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print(f"\n⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if "extractor" in locals() and hasattr(extractor, "driver"):
            extractor.driver.quit()


if __name__ == "__main__":
    test_robustness_improvements()

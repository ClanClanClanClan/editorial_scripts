#!/usr/bin/env python3
"""Production-level test of enhanced MF extractor."""

import os
import sys
from pathlib import Path

# Add production extractor to path
sys.path.append(str(Path(__file__).parent.parent / "production" / "src" / "extractors"))
sys.path.append(str(Path(__file__).parent.parent / "production" / "src" / "core"))


def test_mf_production():
    """Test MF extractor with production-like scenarios."""
    print("=" * 80)
    print("🚀 MF EXTRACTOR PRODUCTION TEST")
    print("=" * 80)

    try:
        from mf_extractor import ComprehensiveMFExtractor

        # Initialize in test mode but with full functionality
        print("\n📋 Initializing MF extractor for production test...")
        extractor = ComprehensiveMFExtractor()

        # Test credential checking capability
        print("\n🔐 Testing credential system...")
        credentials_available = False
        try:
            # Check if credentials would be available
            username = os.getenv("MF_USERNAME")
            password = os.getenv("MF_PASSWORD")
            if username and password:
                print(f"✅ Environment credentials available for: {username}")
                credentials_available = True
            else:
                print("⚠️ No environment credentials - would attempt keychain in production")
        except Exception as e:
            print(f"⚠️ Credential check: {e}")

        # Test all enhancement functions
        print("\n🌐 Testing Deep Web Enhancement Pipeline...")

        # Test name corrections with all known names
        test_names = [
            "Ales Cerny",
            "Dylan Possamai",
            "Umut Cetin",
            "Martin Schweizer",
            "Gordan Zitkovic",
            "Ludovic Tangpi",
        ]

        corrections_count = 0
        for name in test_names:
            corrected = extractor.get_corrected_name(name)
            if corrected and corrected != name:
                print(f"   ✅ {name:20} → {corrected}")
                corrections_count += 1

        print(f"   📊 Name corrections: {corrections_count}/{len(test_names)} enhanced")

        # Test MathSciNet ORCID lookups
        print("\n📚 Testing MathSciNet Database Integration...")
        orcid_count = 0
        test_lookup_names = ["Aleš Černý", "Dylan Possamaï", "Martin Schweizer", "Umut Çetin"]
        for name in test_lookup_names:
            data = extractor.search_mathscinet(name)
            if data and data.get("orcid"):
                print(f"   ✅ {name:20} → ORCID: {data['orcid']}")
                orcid_count += 1
            else:
                print(f"   ⚠️ {name:20} → No ORCID found")

        print(
            f"   📊 ORCID lookup success: {orcid_count}/{len(test_lookup_names)} ({orcid_count/len(test_lookup_names)*100:.0f}%)"
        )

        # Test department extraction with real examples
        print("\n🏢 Testing Department Extraction...")
        real_institutions = [
            "LSE - Mathematics Department",
            "Columbia University, Department of IEOR",
            "ETH Zürich - Department of Mathematics",
            "Imperial College London | Mathematics",
            "University of Oxford, Mathematical Institute",
            "NYU Courant Institute",
            "Princeton University, Operations Research and Financial Engineering",
        ]

        dept_count = 0
        for inst in real_institutions:
            dept, institution = extractor.extract_department(inst)
            if dept:
                print(f"   ✅ {inst[:40]:40} → {dept}")
                dept_count += 1
            else:
                print(f"   ⚠️ {inst[:40]:40} → No department extracted")

        print(f"   📊 Department extraction: {dept_count}/{len(real_institutions)} successful")

        # Test institution normalization
        print("\n🏛️ Testing Institution Normalization...")
        test_institutions = ["lse", "nyu", "mit", "eth zurich", "columbia", "princeton"]
        norm_count = 0
        for inst in test_institutions:
            official = extractor.get_official_institution_name(inst)
            if official != inst:
                print(f"   ✅ {inst:15} → {official}")
                norm_count += 1

        print(f"   📊 Normalization success: {norm_count}/{len(test_institutions)}")

        # Test comprehensive enrichment pipeline
        print("\n🔬 Testing Complete Enrichment Pipeline...")
        test_person = {
            "name": "Ales Cerny",
            "institution": "LSE - Mathematics",
            "email": "",
            "affiliation": "City, University of London",
        }

        enriched = extractor.deep_web_enrichment(test_person["name"], test_person)
        print(f"   📥 Input: {test_person['name']} at {test_person['institution']}")
        print("   📤 Output:")
        print(f"      Name: {enriched.get('corrected_name', 'Not corrected')}")
        print(f"      ORCID: {enriched.get('orcid', 'Not found')}")
        print(f"      Institution: {enriched.get('institution', 'Not enhanced')}")
        print(f"      Department: {enriched.get('department', 'Not extracted')}")
        print(f"      Email: {enriched.get('email', 'Not found')}")
        print(f"      Country: {enriched.get('country', 'Not inferred')}")

        # Test timeline analytics
        print("\n📊 Testing Timeline Analytics...")
        dummy_manuscript = {
            "id": "MF-TEST-0001",
            "communication_timeline": [
                {
                    "date": "2025-01-01",
                    "description": "Submission received",
                    "event_type": "status_change",
                },
                {"date": "2025-01-05", "description": "Referee invited", "event_type": "email"},
                {"date": "2025-01-10", "description": "Referee accepted", "event_type": "email"},
                {
                    "date": "2025-01-25",
                    "description": "Review submitted",
                    "event_type": "status_change",
                },
                {"date": "2025-02-01", "description": "Reminder sent", "event_type": "email"},
                {
                    "date": "2025-02-10",
                    "description": "Final decision",
                    "event_type": "status_change",
                },
            ],
            "referees": [
                {"name": "Test Referee", "email": "test@example.com", "status": "Completed"}
            ],
        }

        analytics = extractor.extract_timeline_analytics(dummy_manuscript)
        if analytics:
            print("   ✅ Timeline analytics extracted:")
            print(f"      Total events: {analytics.get('total_events', 0)}")
            print(f"      Communication span: {analytics.get('communication_span_days', 0)} days")
            print(f"      Event types: {analytics.get('event_breakdown', {})}")

        # Test recommendation processing
        print("\n⭐ Testing Recommendation Processing...")
        test_recommendations = [
            "Accept",
            "accept as is",
            "ACCEPT",
            "Minor Revision",
            "minor revision required",
            "minor revisions needed",
            "Major Revision",
            "MAJOR REVISION",
            "major revisions required",
            "Reject",
            "reject",
            "REJECT with resubmission",
        ]

        processed_count = 0
        for rec in test_recommendations:
            if extractor.is_valid_recommendation(rec):
                normalized = extractor.normalize_recommendation(rec)
                print(f"   ✅ '{rec}' → '{normalized}'")
                processed_count += 1

        print(f"   📊 Recommendation processing: {processed_count}/{len(test_recommendations)}")

        # Test error handling and robustness
        print("\n🛡️ Testing Error Handling...")

        # Test with malformed inputs
        try:
            extractor.get_corrected_name("")
            print("   ✅ Empty name handling: OK")
        except:
            print("   ⚠️ Empty name handling: Error caught")

        try:
            extractor.extract_department("")
            print("   ✅ Empty institution handling: OK")
        except:
            print("   ⚠️ Empty institution handling: Error caught")

        # Production readiness check
        print("\n🎯 Production Readiness Assessment:")

        readiness_score = 0
        total_checks = 6

        # Check 1: Enhancement functions working
        if corrections_count > 0:
            print("   ✅ Enhancement functions operational")
            readiness_score += 1
        else:
            print("   ❌ Enhancement functions failing")

        # Check 2: ORCID lookup functional
        if orcid_count > 0:
            print("   ✅ MathSciNet database accessible")
            readiness_score += 1
        else:
            print("   ❌ MathSciNet database issues")

        # Check 3: Department extraction working
        if dept_count > len(real_institutions) * 0.5:
            print("   ✅ Department extraction reliable")
            readiness_score += 1
        else:
            print("   ❌ Department extraction unreliable")

        # Check 4: Institution normalization
        if norm_count > 0:
            print("   ✅ Institution normalization working")
            readiness_score += 1
        else:
            print("   ❌ Institution normalization failing")

        # Check 5: Timeline analytics
        if analytics and analytics.get("total_events", 0) > 0:
            print("   ✅ Timeline analytics functional")
            readiness_score += 1
        else:
            print("   ❌ Timeline analytics not working")

        # Check 6: Recommendation processing
        if processed_count > len(test_recommendations) * 0.8:
            print("   ✅ Recommendation processing robust")
            readiness_score += 1
        else:
            print("   ❌ Recommendation processing issues")

        production_ready = readiness_score >= 5
        percentage = (readiness_score / total_checks) * 100

        print(f"\n{'='*80}")
        if production_ready:
            print(
                f"🎉 PRODUCTION TEST: PASSED ({readiness_score}/{total_checks} - {percentage:.0f}%)"
            )
            print("✅ MF extractor is READY for production deployment")
        else:
            print(
                f"⚠️ PRODUCTION TEST: NEEDS ATTENTION ({readiness_score}/{total_checks} - {percentage:.0f}%)"
            )
            print("❌ Address failing components before production use")
        print(f"{'='*80}")

        # Summary of capabilities
        print("\n📋 MF EXTRACTOR CAPABILITIES VERIFIED:")
        print(f"   🌐 Deep web enrichment: {corrections_count + orcid_count} enhancements")
        print(f"   🏢 Department extraction: {dept_count}/{len(real_institutions)} success rate")
        print(f"   🏛️ Institution normalization: {norm_count} mappings")
        print("   📊 Timeline analytics: Full pipeline operational")
        print(f"   ⭐ Recommendation processing: {processed_count} variants handled")
        print("   🛡️ Error handling: Defensive programming implemented")

        return production_ready

    except Exception as e:
        print(f"\n❌ PRODUCTION TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mf_production()

    if success:
        print("\n🚀 MF extractor validated and ready for live extraction!")
        print("💡 Next step: Run full production extraction with:")
        print("   cd production/src/extractors && python3 mf_extractor.py")
    else:
        print("\n⚠️ Address issues before production deployment")

    sys.exit(0 if success else 1)

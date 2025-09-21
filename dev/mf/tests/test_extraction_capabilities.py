#!/usr/bin/env python3
"""
TEST EXTRACTION CAPABILITIES - What do MF and MOR actually extract?
===================================================================

After successful login, test what data these extractors actually pull.
"""

import sys
import json
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

def test_mf_extraction():
    """Test what MF extractor actually extracts."""
    print("🔍 TESTING MF EXTRACTION CAPABILITIES")
    print("=" * 70)

    try:
        from mf_extractor import ComprehensiveMFExtractor

        print("📝 Creating MF extractor and logging in...")
        mf = ComprehensiveMFExtractor()

        # Login first
        if not mf.login():
            print("❌ Login failed, cannot test extraction")
            mf.cleanup()
            return

        print("✅ Login successful, testing extraction capabilities...")

        # 1. Get manuscript categories
        print("\n📊 1. Getting manuscript categories...")
        try:
            categories = mf.get_manuscript_categories()
            print(f"   Found {len(categories)} categories:")
            for cat in categories[:3]:  # Show first 3
                print(f"   • {cat}")
        except Exception as e:
            print(f"   ❌ Error getting categories: {e}")

        # 2. Get manuscripts from a category
        print("\n📋 2. Getting manuscripts from category...")
        try:
            # Try to get manuscripts from first available category
            if categories and len(categories) > 0:
                first_category = categories[0]
                print(f"   Testing category: {first_category['name']}")
                manuscripts = mf.get_manuscripts_from_category(first_category['name'])
                print(f"   Found {len(manuscripts)} manuscripts")

                # 3. Extract details from first manuscript
                if manuscripts and len(manuscripts) > 0:
                    first_manuscript = manuscripts[0]
                    print(f"\n📄 3. Extracting details for manuscript: {first_manuscript.get('id', 'unknown')}")

                    details = mf.extract_manuscript_details(first_manuscript['id'])

                    print("\n   📊 EXTRACTED DATA:")
                    print(f"   • ID: {details.get('id')}")
                    print(f"   • Title: {details.get('title', 'N/A')[:50]}...")
                    print(f"   • Status: {details.get('status')}")
                    print(f"   • Authors: {len(details.get('authors', []))} authors")
                    print(f"   • Referees: {len(details.get('referees', []))} referees")

                    # Show referee details
                    if details.get('referees'):
                        print("\n   👥 REFEREE INFORMATION:")
                        for i, ref in enumerate(details['referees'][:2], 1):  # Show first 2
                            print(f"      Referee {i}:")
                            print(f"      • Name: {ref.get('name')}")
                            print(f"      • Email: {ref.get('email')}")
                            print(f"      • Status: {ref.get('status')}")
                            print(f"      • Recommendation: {ref.get('recommendation')}")

                    # Show timeline
                    if details.get('timeline'):
                        print(f"\n   📅 TIMELINE: {len(details['timeline'])} events")
                        for event in details['timeline'][:3]:  # Show first 3 events
                            print(f"      • {event.get('date')}: {event.get('action')}")

                    # Show documents
                    if details.get('documents'):
                        print(f"\n   📁 DOCUMENTS: {len(details['documents'])} files")
                        for doc in details['documents'][:3]:  # Show first 3
                            print(f"      • {doc.get('type')}: {doc.get('filename')}")

        except Exception as e:
            print(f"   ❌ Error extracting manuscripts: {e}")
            import traceback
            traceback.print_exc()

        print("\n✅ MF extraction test complete")
        mf.cleanup()

    except Exception as e:
        print(f"❌ Error testing MF extraction: {e}")
        import traceback
        traceback.print_exc()

def test_mor_extraction():
    """Test what MOR extractor actually extracts."""
    print("\n\n🔍 TESTING MOR EXTRACTION CAPABILITIES")
    print("=" * 70)

    try:
        from mor_extractor import ComprehensiveMORExtractor

        print("📝 Creating MOR extractor and logging in...")
        mor = ComprehensiveMORExtractor()

        # Login first
        if not mor.login():
            print("❌ Login failed, cannot test extraction")
            mor.cleanup()
            return

        print("✅ Login successful, testing extraction capabilities...")

        # Similar extraction tests for MOR
        print("\n📊 1. Getting manuscript categories...")
        try:
            categories = mor.get_manuscript_categories()
            print(f"   Found {len(categories)} categories:")
            for cat in categories[:3]:
                print(f"   • {cat}")
        except Exception as e:
            print(f"   ❌ Error getting categories: {e}")

        print("\n✅ MOR extraction test complete")
        mor.cleanup()

    except Exception as e:
        print(f"❌ Error testing MOR extraction: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test both extractors' capabilities."""
    print("🚀 TESTING EXTRACTION CAPABILITIES OF MF AND MOR")
    print("=" * 70)
    print("These extractors pull manuscript data from editorial platforms:")
    print("• Manuscript IDs, titles, and statuses")
    print("• Author information and affiliations")
    print("• Referee details (names, emails, recommendations)")
    print("• Review reports and decisions")
    print("• Timeline of all editorial events")
    print("• Associated documents (PDFs, cover letters, etc.)")
    print("=" * 70)

    # Test MF
    test_mf_extraction()

    # Test MOR
    # test_mor_extraction()  # Uncomment to test MOR too

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Test that MF processes ALL categories sequentially."""

import sys
import os
import time
import json
sys.path.append('production/src/extractors')

from mf_extractor import ComprehensiveMFExtractor

def test_categories():
    """Test multi-category processing."""
    print("🚀 Testing MF Multi-Category Processing")
    print("=" * 60)

    extractor = None
    categories_processed = []

    try:
        # Create instance
        print("⚙️ Initializing...")
        extractor = ComprehensiveMFExtractor()
        print("✅ Initialized")

        # Patch extract_all to track categories
        original_process = extractor.process_category

        def track_category(category):
            category_name = category.get('name', 'Unknown') if isinstance(category, dict) else str(category)
            print(f"\n🎯 TRACKING: Processing {category_name}")
            categories_processed.append(category_name)
            return original_process(category)

        extractor.process_category = track_category

        # Run extraction
        print("\n📊 Starting extraction...")
        extractor.extract_all()

        # Report results
        print("\n" + "=" * 60)
        print("📊 CATEGORY PROCESSING SUMMARY")
        print("=" * 60)

        if categories_processed:
            print(f"✅ Processed {len(categories_processed)} categories:")
            for i, cat in enumerate(categories_processed, 1):
                print(f"   {i}. {cat}")
        else:
            print("❌ No categories were processed")

        # Check manuscripts
        if extractor.manuscripts:
            print(f"\n📋 Total manuscripts extracted: {len(extractor.manuscripts)}")

            # Group by category
            by_category = {}
            for ms in extractor.manuscripts:
                cat = ms.get('category', 'Unknown')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(ms['id'])

            print("\n📦 Manuscripts by category:")
            for cat, ids in by_category.items():
                print(f"   {cat}: {len(ids)} manuscripts")
                for id in ids[:3]:  # Show first 3
                    print(f"      - {id}")

        # Save summary
        summary = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'categories_processed': categories_processed,
            'total_manuscripts': len(extractor.manuscripts),
            'by_category': {
                cat: len([m for m in extractor.manuscripts if m.get('category') == cat])
                for cat in set(m.get('category', 'Unknown') for m in extractor.manuscripts)
            }
        }

        with open('mf_category_test_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Summary saved to: mf_category_test_summary.json")

        # Success if we processed more than 1 category
        success = len(categories_processed) > 1

        if success:
            print("\n✨ SUCCESS: Multiple categories processed!")
        else:
            print(f"\n⚠️ Only {len(categories_processed)} category processed")

        return success

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
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
    success = test_categories()
    sys.exit(0 if success else 1)
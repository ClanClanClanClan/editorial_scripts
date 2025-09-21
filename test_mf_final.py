#!/usr/bin/env python3
"""Test MF extraction with minimal popup fix."""

import sys
import os
import time
import json
sys.path.append('production/src/extractors')

from mf_extractor import ComprehensiveMFExtractor

def test_mf():
    """Test MF extraction."""
    print("🚀 Testing MF Extraction with Minimal Popup Fix")
    print("=" * 60)

    extractor = None
    start_time = time.time()

    try:
        # Create instance
        print("⚙️ Initializing...")
        extractor = ComprehensiveMFExtractor()
        print("✅ Initialized")

        # Run extraction
        print("\n📊 Starting extraction...")
        print("   - Popup handling: MINIMAL (no frame switching)")
        print("   - Expected behavior: Skip complex email extraction")
        print("   - Focus: Complete extraction without hanging")
        print()

        extractor.extract_all()

        elapsed = time.time() - start_time
        print(f"\n✅ Completed in {elapsed:.1f}s")

        # Show results
        if extractor.manuscripts:
            print(f"\n📊 RESULTS: {len(extractor.manuscripts)} manuscripts")

            for i, ms in enumerate(extractor.manuscripts[:3], 1):
                print(f"\n{i}. {ms.get('id', 'Unknown')}")
                print(f"   Title: {ms.get('title', 'N/A')[:50]}...")
                print(f"   Category: {ms.get('category', 'N/A')}")
                print(f"   Referees: {len(ms.get('referees', []))}")

                # Check if we got any emails
                emails_found = 0
                for ref in ms.get('referees', []):
                    if ref.get('email'):
                        emails_found += 1

                print(f"   Emails extracted: {emails_found}/{len(ms.get('referees', []))}")

            # Save results
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_file = f"mf_results_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'elapsed': elapsed,
                    'total': len(extractor.manuscripts),
                    'manuscripts': extractor.manuscripts
                }, f, indent=2, default=str)

            print(f"\n💾 Saved to: {output_file}")

            # Save to production dir too
            os.makedirs("production/src/extractors/results/mf", exist_ok=True)
            prod_file = f"production/src/extractors/results/mf/mf_{timestamp}.json"

            with open(prod_file, 'w') as f:
                json.dump(extractor.manuscripts, f, indent=2, default=str)

            print(f"💾 Also saved to: {prod_file}")

            return True
        else:
            print("\n⚠️ No manuscripts extracted")
            return False

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️ Interrupted after {elapsed:.1f}s")

        if extractor and extractor.manuscripts:
            print(f"   Partial: {len(extractor.manuscripts)} manuscripts")

            # Save partial results
            with open("mf_partial.json", 'w') as f:
                json.dump(extractor.manuscripts, f, indent=2, default=str)
            print("   💾 Partial results saved to mf_partial.json")

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
    success = test_mf()

    if success:
        print("\n✨ SUCCESS!")
    else:
        print("\n❌ Failed")

    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""Test MF extraction with popup fixes."""

import sys
import os
import time
import json
sys.path.append('production/src/extractors')

from mf_extractor import ComprehensiveMFExtractor

def test_mf_fixed():
    """Test MF extraction with all fixes."""
    print("🚀 Testing MF Extraction with Popup Fixes")
    print("=" * 60)

    extractor = None
    start_time = time.time()

    try:
        # Create instance
        print("⚙️ Initializing MF extractor...")
        extractor = ComprehensiveMFExtractor()
        print("✅ Extractor initialized")

        # Run full extraction
        print("\n📊 Starting extraction...")
        print("   This will:")
        print("   1. Login with 2FA")
        print("   2. Navigate to AE Center")
        print("   3. Process categories with manuscripts")
        print("   4. Handle popup windows safely")
        print("   5. Execute 3-pass extraction")
        print()

        # Call extract_all which handles everything
        extractor.extract_all()

        # Check results
        elapsed = time.time() - start_time
        print(f"\n✅ Extraction completed in {elapsed:.1f} seconds")

        if extractor.manuscripts:
            print(f"\n📊 RESULTS:")
            print(f"   Total manuscripts: {len(extractor.manuscripts)}")

            # Show manuscripts
            for i, ms in enumerate(extractor.manuscripts, 1):
                print(f"\n   {i}. {ms.get('id', 'Unknown')}")
                print(f"      Title: {ms.get('title', 'Unknown')[:60]}...")
                print(f"      Category: {ms.get('category', 'Unknown')}")
                print(f"      Status: {ms.get('status', 'Unknown')}")
                print(f"      Referees: {len(ms.get('referees', []))}")

                # Show referee details
                for ref in ms.get('referees', [])[:2]:  # First 2 referees
                    name = ref.get('name', 'Unknown')
                    email = ref.get('email', 'No email')
                    print(f"        - {name}: {email}")

            # Save results
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_file = f"mf_test_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump({
                    'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'elapsed_seconds': elapsed,
                    'total_manuscripts': len(extractor.manuscripts),
                    'manuscripts': extractor.manuscripts
                }, f, indent=2, default=str)

            print(f"\n💾 Results saved to: {output_file}")

            # Also save to production results directory
            prod_file = f"production/src/extractors/results/mf/mf_test_{timestamp}.json"
            os.makedirs(os.path.dirname(prod_file), exist_ok=True)

            with open(prod_file, 'w') as f:
                json.dump({
                    'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'elapsed_seconds': elapsed,
                    'total_manuscripts': len(extractor.manuscripts),
                    'manuscripts': extractor.manuscripts
                }, f, indent=2, default=str)

            print(f"💾 Also saved to: {prod_file}")

            return True
        else:
            print("\n⚠️ No manuscripts extracted")
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        elapsed = time.time() - start_time
        print(f"   Ran for {elapsed:.1f} seconds")
        if extractor and extractor.manuscripts:
            print(f"   Partial results: {len(extractor.manuscripts)} manuscripts")
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
                print("✅ Cleanup complete")
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")


if __name__ == "__main__":
    success = test_mf_fixed()
    sys.exit(0 if success else 1)
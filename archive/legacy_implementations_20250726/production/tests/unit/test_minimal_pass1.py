#!/usr/bin/env python3
"""
Minimal test to verify Pass 1 referee extraction
"""

import sys
from pathlib import Path

# Add path to import the MF extractor
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials

    load_credentials()
except ImportError:
    from dotenv import load_dotenv

    load_dotenv(".env.production")


# Use the actual extractor but run it step by step
from mf_extractor import ComprehensiveMFExtractor


def test_minimal():
    """Minimal test of Pass 1"""
    print("🧪 Minimal Pass 1 test...")

    extractor = ComprehensiveMFExtractor()

    # Run the full extraction but with detailed logging
    try:
        success = extractor.extract_all()

        print("\n" + "=" * 60)
        print("📊 EXTRACTION RESULTS:")
        print("=" * 60)

        if not extractor.manuscripts:
            print("❌ No manuscripts extracted")
            return

        # Check first 2 manuscripts
        total_referees = 0
        for i, manuscript in enumerate(extractor.manuscripts[:2]):
            referee_count = len(manuscript.get("referees", []))
            total_referees += referee_count

            print(f"\n📄 Manuscript {i+1}: {manuscript.get('id')}")
            print(f"   Referees: {referee_count}")

            if referee_count == 0:
                print("   ❌ NO REFEREES!")
            else:
                for j, ref in enumerate(manuscript["referees"]):
                    print(f"   {j+1}. {ref.get('name')} - {ref.get('status')}")

        print(f"\n📊 TOTAL: {total_referees} referees")

        if total_referees == 6:
            print("✅ SUCCESS!")
        else:
            print(f"❌ FAIL: Expected 6, got {total_referees}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    test_minimal()

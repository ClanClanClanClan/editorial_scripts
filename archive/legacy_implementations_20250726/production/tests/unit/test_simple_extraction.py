#!/usr/bin/env python3
"""
Simple test of full extraction
"""

import json
import sys
from datetime import datetime
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

from mf_extractor import ComprehensiveMFExtractor


def test_simple():
    """Run simple extraction test"""
    print("🚀 Running simple extraction test...")

    extractor = ComprehensiveMFExtractor()

    try:
        # Run full extraction
        success = extractor.extract_all()

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mf_test_simple_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(extractor.manuscripts, f, indent=2, default=str)

        print(f"\n✅ Saved results to {output_file}")

        # Show summary
        print("\n📊 Extraction Summary:")
        print(f"Total manuscripts: {len(extractor.manuscripts)}")

        for i, manuscript in enumerate(extractor.manuscripts):
            print(f"\nManuscript {i+1}: {manuscript.get('id')}")
            print(f"  Referees: {len(manuscript.get('referees', []))}")
            print(f"  PDF: {'Yes' if manuscript.get('documents', {}).get('pdf') else 'No'}")
            print(f"  Abstract: {'Yes' if manuscript.get('abstract') else 'No'}")
            print(
                f"  Cover Letter: {'Yes' if manuscript.get('documents', {}).get('cover_letter') else 'No'}"
            )

            if len(manuscript.get("referees", [])) == 0:
                print("  ⚠️ NO REFEREES FOUND!")

        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    test_simple()

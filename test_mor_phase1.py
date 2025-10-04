#!/usr/bin/env python3
"""
Test MOR Extractor - Phase 1
Tests extract_manuscript_details() with basic field extraction.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add production src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

# Verify credentials are loaded
required_env_vars = ["MOR_EMAIL", "MOR_PASSWORD"]
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

if missing_vars:
    print("❌ Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\n📝 Load credentials first:")
    print("   source ~/.editorial_scripts/load_all_credentials.sh")
    sys.exit(1)

print("✅ Credentials loaded")
print(f"   MOR_EMAIL: {os.environ.get('MOR_EMAIL')}")

# Import the extractor
from extractors.mor_extractor_enhanced import MORExtractor


def main():
    print("\n" + "=" * 60)
    print("🧪 MOR EXTRACTOR - PHASE 1 TEST")
    print("   Testing: extract_manuscript_details() basic fields")
    print("=" * 60)

    # Create extractor instance
    extractor = MORExtractor()

    try:
        # Run the extractor
        result = extractor.run()

        # Check what we got
        if result:
            # Handle both dict and list formats
            if isinstance(result, dict) and "manuscripts" in result:
                manuscripts = result["manuscripts"]
                # Convert dict to list if needed
                if isinstance(manuscripts, dict):
                    manuscripts = list(manuscripts.values())
            elif isinstance(result, list):
                manuscripts = result
            else:
                manuscripts = []

            print(f"\n✅ Extraction completed!")
            print(f"   Manuscripts found: {len(manuscripts)}")

            # Show details for each manuscript
            for manuscript_data in manuscripts:
                manuscript_id = manuscript_data.get("id", "UNKNOWN")
                print(f"\n📄 Manuscript: {manuscript_id}")
                print(f"   Title: {manuscript_data.get('title', 'NOT EXTRACTED')[:80]}...")
                print(f"   Authors: {len(manuscript_data.get('authors', []))} found")
                print(
                    f"   Submission date: {manuscript_data.get('submission_date', 'NOT EXTRACTED')}"
                )
                print(f"   Status: {manuscript_data.get('status', 'NOT EXTRACTED')}")
                print(f"   Article type: {manuscript_data.get('article_type', 'NOT EXTRACTED')}")
                print(f"   Editors: {len(manuscript_data.get('editors', {}))} roles found")
                print(f"   Referees: {len(manuscript_data.get('referees', []))} found")

                # Show first author
                if manuscript_data.get("authors"):
                    first_author = manuscript_data["authors"][0]
                    print(f"\n   First author:")
                    print(f"      Name: {first_author.get('name')}")
                    print(f"      Corresponding: {first_author.get('is_corresponding')}")

            # Save to JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = project_root / f"mor_phase1_test_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

            print(f"\n💾 Results saved to: {output_file}")
            print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")

        else:
            print("\n❌ No manuscripts extracted")
            print("   Result:", result)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        try:
            if extractor.driver:
                extractor.driver.quit()
        except:
            pass

    print("\n" + "=" * 60)
    print("✅ Phase 1 Test Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

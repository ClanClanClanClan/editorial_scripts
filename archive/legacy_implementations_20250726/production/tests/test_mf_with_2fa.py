#!/usr/bin/env python3
"""
Test MF extraction with automatic 2FA handling
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the actual MF extractor
from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_mf_with_2fa():
    """Test MF extraction with automatic 2FA"""

    print("🚀 Testing MF Extraction with 2FA")
    print("=" * 60)

    # Create extractor instance
    extractor = ComprehensiveMFExtractor()

    try:
        # The extractor should handle everything including 2FA
        print("\n📊 Starting extraction (this will handle 2FA automatically)...")

        # Run extraction
        success = extractor.extract_all()

        if success:
            print("\n✅ Extraction completed successfully!")
            print(f"   Extracted {len(extractor.manuscripts)} manuscripts")

            # Show summary
            for i, ms in enumerate(extractor.manuscripts):
                print(f"\n📄 Manuscript {i+1}: {ms.get('id', 'Unknown')}")
                print(f"   Title: {ms.get('title', 'Unknown')[:60]}...")
                print(f"   Referees: {len(ms.get('referees', []))}")
                print(f"   Authors: {len(ms.get('authors', []))}")
        else:
            print("\n❌ Extraction failed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            print("\n🧹 Cleaning up...")
            extractor.driver.quit()


if __name__ == "__main__":
    test_mf_with_2fa()

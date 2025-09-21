#!/usr/bin/env python3
"""
Test MOR login with FIXED Gmail verification
"""

import sys
import os
import time

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor

print("="*60)
print("🚀 MOR LOGIN TEST WITH FIXED GMAIL")
print("="*60)

try:
    # Create MOR instance
    print("\n1. Creating MOR extractor...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Created")

    print("\n2. Running full extraction (includes login with 2FA)...")
    print("   This will:")
    print("   - Navigate to MOR")
    print("   - Enter credentials")
    print("   - Fetch 2FA code from Gmail automatically")
    print("   - Complete login")
    print("   - Extract manuscripts")

    # Run the extractor
    results = mor.run()

    # Check results
    if results:
        print("\n✅ EXTRACTION SUCCESSFUL!")
        print(f"   Manuscripts extracted: {len(results.get('manuscripts', []))}")

        # Show first manuscript if available
        if results.get('manuscripts'):
            ms = results['manuscripts'][0]
            print(f"\n   First manuscript:")
            print(f"      ID: {ms.get('manuscript_id', 'Unknown')}")
            print(f"      Referees: {len(ms.get('referees', []))}")

            # Show referee details
            for i, ref in enumerate(ms.get('referees', [])[:3], 1):
                print(f"      Referee {i}: {ref.get('name', 'Unknown')} - {ref.get('status', 'Unknown')}")

        if results.get('errors'):
            print(f"\n   Errors: {len(results['errors'])}")
            for err in results['errors'][:3]:
                print(f"      - {err[:100]}")

    else:
        print("\n❌ Extraction failed - no results")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
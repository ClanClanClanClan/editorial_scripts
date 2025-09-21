#!/usr/bin/env python3
"""
FINAL WORKING MOR TEST - All fixes applied
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("="*60)
print("🚀 FINAL MOR TEST WITH ALL FIXES")
print("="*60)

from extractors.mor_extractor import MORExtractor

try:
    print("\n1. Creating MOR extractor...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Created")

    print("\n2. Running extraction...")
    print("   This will:")
    print("   - Login with credentials")
    print("   - Wait for NEW 2FA email")
    print("   - Submit fresh code")
    print("   - Navigate and extract manuscripts")

    results = mor.run()

    if results:
        print("\n" + "="*60)
        print("✅ EXTRACTION SUCCESSFUL!")
        print("="*60)

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_final_{timestamp}.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Results saved to: {output_file.name}")

        # Display results
        if 'manuscripts' in results:
            manuscripts = results.get('manuscripts', [])
            print(f"\n📊 Manuscripts extracted: {len(manuscripts)}")

            for i, ms in enumerate(manuscripts[:3], 1):
                print(f"\n{i}. {ms.get('manuscript_id', 'Unknown')}")
                print(f"   Title: {ms.get('title', 'N/A')[:60]}...")
                print(f"   Authors: {len(ms.get('authors', []))}")
                print(f"   Referees: {len(ms.get('referees', []))}")

                # Show referee details
                for j, ref in enumerate(ms.get('referees', [])[:3], 1):
                    print(f"      {j}. {ref.get('name', 'Unknown')}")
                    print(f"         Status: {ref.get('status', 'N/A')}")
                    if ref.get('email'):
                        print(f"         Email: {ref['email']}")

        if 'summary' in results:
            summary = results['summary']
            print("\n" + "="*60)
            print("📈 OVERALL STATISTICS")
            print("="*60)
            print(f"Total manuscripts: {summary.get('total_manuscripts', 0)}")
            print(f"Total referees: {summary.get('total_referees', 0)}")
            print(f"Referees with emails: {summary.get('referees_with_email', 0)}")

    else:
        print("\n❌ No results returned")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
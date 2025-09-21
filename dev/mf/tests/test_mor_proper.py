#!/usr/bin/env python3
"""
Proper MOR test with working 2FA and navigation
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor

print("="*60)
print("🚀 PROPER MOR EXTRACTOR TEST")
print("="*60)

results = {
    'timestamp': datetime.now().isoformat(),
    'manuscripts': [],
    'errors': []
}

try:
    # Use the actual MOR extractor's run method
    print("\n1. Creating MOR extractor...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Created")

    print("\n2. Running extraction...")
    print("   This will handle login, 2FA, navigation automatically")

    # Run the actual extraction
    extraction_results = mor.run()

    # Save results
    if extraction_results:
        print("\n3. Extraction completed!")

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_proper_test_{timestamp}.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(extraction_results, f, indent=2, default=str)

        print(f"\n📄 Results saved to: {output_file.name}")

        # Display summary
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)

        if 'manuscripts' in extraction_results:
            manuscripts = extraction_results['manuscripts']
            print(f"\n✅ Total manuscripts: {len(manuscripts)}")

            for i, ms in enumerate(manuscripts[:5], 1):
                print(f"\n{i}. {ms.get('manuscript_id', 'Unknown')}")
                print(f"   Title: {ms.get('title', 'N/A')[:50]}...")
                print(f"   Authors: {len(ms.get('authors', []))}")
                print(f"   Referees: {len(ms.get('referees', []))}")

                # Show referee details
                referees = ms.get('referees', [])
                for j, ref in enumerate(referees[:3], 1):
                    print(f"      {j}. {ref.get('name', 'Unknown')}")
                    print(f"         Status: {ref.get('status', 'Unknown')}")
                    if ref.get('email'):
                        print(f"         Email: {ref.get('email')}")
                    if ref.get('institution'):
                        print(f"         Institution: {ref.get('institution')}")

        if 'errors' in extraction_results and extraction_results['errors']:
            print(f"\n⚠️ Errors: {len(extraction_results['errors'])}")
            for err in extraction_results['errors'][:3]:
                print(f"   - {err[:100]}")

        if 'summary' in extraction_results:
            summary = extraction_results['summary']
            print("\n" + "="*60)
            print("📈 STATISTICS")
            print("="*60)
            print(f"Total manuscripts: {summary.get('total_manuscripts', 0)}")
            print(f"Total referees: {summary.get('total_referees', 0)}")
            print(f"Referees with emails: {summary.get('referees_with_email', 0)}")

    else:
        print("\n❌ No results returned")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
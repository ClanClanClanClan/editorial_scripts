#!/usr/bin/env python3
"""
Final test of MOR extractor with all fixes
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("="*60)
print("🚀 FINAL MOR EXTRACTOR TEST")
print("="*60)

try:
    from extractors.mor_extractor import MORExtractor
    print("✅ MOR imported successfully")

    # Create instance
    mor = MORExtractor(use_cache=False)
    print("✅ Instance created")

    # Run extraction
    print("\n⏳ Starting extraction...")
    print("   This will:")
    print("   1. Login with 2FA")
    print("   2. Navigate to AE Center")
    print("   3. Process all manuscript categories")
    print("   4. Extract referee details")
    print("   5. Generate summary\n")

    results = mor.run()

    # Save results
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_test_{timestamp}.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Results saved to: {output_file.name}")

        # Print summary
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)

        if 'manuscripts' in results:
            print(f"\nTotal manuscripts extracted: {len(results['manuscripts'])}")

            for i, ms in enumerate(results['manuscripts'][:5], 1):  # Show first 5
                print(f"\n{i}. {ms.get('manuscript_id', 'Unknown')}")
                print(f"   Title: {ms.get('title', 'N/A')[:60]}...")
                print(f"   Authors: {len(ms.get('authors', []))}")
                print(f"   Referees: {len(ms.get('referees', []))}")

                # Show referee details
                for j, ref in enumerate(ms.get('referees', [])[:3], 1):  # First 3 referees
                    print(f"      {j}. {ref.get('name', 'Unknown')} - {ref.get('status', 'Unknown')}")
                    if ref.get('email'):
                        print(f"         Email: {ref['email']}")
                    if ref.get('institution'):
                        print(f"         Institution: {ref['institution']}")

                print(f"   Documents: {len(ms.get('documents', {}))}")
                print(f"   Audit events: {len(ms.get('audit_trail', []))}")

        if 'errors' in results and results['errors']:
            print(f"\n⚠️ Errors encountered: {len(results['errors'])}")
            for error in results['errors'][:3]:
                print(f"   - {error[:100]}")

        if 'summary' in results:
            summary = results['summary']
            print("\n" + "="*60)
            print("📈 OVERALL STATISTICS")
            print("="*60)
            print(f"Total manuscripts: {summary.get('total_manuscripts', 0)}")
            print(f"Total referees: {summary.get('total_referees', 0)}")
            print(f"Referees with emails: {summary.get('referees_with_email', 0)}")
            print(f"Average referees per manuscript: {summary.get('avg_referees_per_manuscript', 0):.1f}")

    else:
        print("\n❌ No results returned")

except KeyboardInterrupt:
    print("\n⚠️ Test interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
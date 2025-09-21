#!/usr/bin/env python3
"""
Quick test of MOR extraction with timeout handling
"""

import sys
import signal
import time
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

# Set signal handler
signal.signal(signal.SIGALRM, timeout_handler)

print("Starting MOR quick test...")

try:
    # Set 30 second timeout
    signal.alarm(30)

    from extractors.mor_extractor import MORExtractor
    print("✅ MOR imported")

    # Create instance
    mor = MORExtractor(use_cache=False)
    print("✅ Instance created")

    # Run with internal timeout
    print("\n🚀 Starting extraction (30s timeout)...")
    results = mor.run()

    # Cancel alarm
    signal.alarm(0)

    print(f"\n✅ Extraction completed!")
    if results:
        print(f"   Manuscripts: {len(results.get('manuscripts', []))}")
        print(f"   Errors: {len(results.get('errors', []))}")

        # Show first manuscript details
        if results.get('manuscripts'):
            ms = results['manuscripts'][0]
            print(f"\n   First manuscript: {ms.get('manuscript_id', 'Unknown')}")
            print(f"   Referees: {len(ms.get('referees', []))}")

            for i, ref in enumerate(ms.get('referees', [])[:3], 1):
                print(f"   Referee {i}: {ref.get('name', 'Unknown')} - {ref.get('status', 'Unknown')}")

except TimeoutError:
    print("\n⚠️ Extraction timed out after 30 seconds")
    print("   This suggests the extractor is stuck somewhere")
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    signal.alarm(0)  # Cancel any pending alarm
    print("\nTest complete")
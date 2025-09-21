#!/usr/bin/env python3
"""
Simple test to see if MOR extractor runs at all
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("Starting MOR test...")

try:
    from extractors.mor_extractor import MORExtractor
    print("✅ MOR imported")
    
    # Create instance
    mor = MORExtractor(use_cache=False)
    print("✅ MOR instance created")
    
    # Try to run
    print("\n🚀 Starting extraction...")
    results = mor.run()
    
    print(f"\n✅ Extraction completed!")
    if results:
        print(f"   Manuscripts: {len(results.get('manuscripts', []))}")
        print(f"   Errors: {len(results.get('errors', []))}")
        
except KeyboardInterrupt:
    print("\n⚠️  Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
finally:
    print("\nTest complete")
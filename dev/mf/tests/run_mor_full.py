#!/usr/bin/env python3
"""
Run the FULL MOR extractor and see what happens
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor

print("="*60)
print("🚀 RUNNING FULL MOR EXTRACTOR")
print("="*60)

try:
    # Create and run
    mor = MORExtractor(use_cache=False)
    results = mor.run()
    
    # Save results
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_full_test_{timestamp}.json')
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Results saved to: {output_file.name}")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)
        
        if 'manuscripts' in results:
            print(f"Manuscripts extracted: {len(results['manuscripts'])}")
            
            for i, ms in enumerate(results['manuscripts'], 1):
                print(f"\n{i}. {ms.get('manuscript_id', 'Unknown')}")
                print(f"   Authors: {len(ms.get('authors', []))}")
                print(f"   Referees: {len(ms.get('referees', []))}")
                print(f"   Referee emails: {sum(1 for r in ms.get('referees', []) if r.get('email'))}")
                print(f"   Documents: {len(ms.get('documents', {}))}")
                print(f"   Audit events: {len(ms.get('audit_trail', []))}")
        
        if 'errors' in results:
            print(f"\n⚠️ Errors: {len(results['errors'])}")
            for error in results['errors'][:5]:
                print(f"   - {error[:100]}")
                
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
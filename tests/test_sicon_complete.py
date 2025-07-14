#!/usr/bin/env python3
"""
Complete test of the fixed SICON extractor
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.append('.')

from unified_system.extractors.siam.sicon_fixed_proper import SICONExtractorProper
from src.core.credential_manager import get_credential_manager

async def run_complete_sicon_test():
    """Run complete SICON extraction test"""
    print("🚀 COMPLETE SICON EXTRACTION TEST")
    print("=" * 50)
    
    # Get credentials
    creds = get_credential_manager().get_credentials('SICON')
    if not creds:
        print("❌ No credentials found")
        return None
    
    print(f"✅ Credentials loaded for: {creds['email']}")
    print("\n📋 Expected behavior:")
    print("1. Navigate through category pages (Under Review, etc.)")
    print("2. Extract manuscripts from each category")
    print("3. Parse Potential Referees (various statuses)")
    print("4. Parse Active Referees (accepted only)")
    print("5. No duplicates, proper status assignment")
    print()
    
    # Initialize extractor
    extractor = SICONExtractorProper()
    
    try:
        # Run extraction
        print("🔄 Starting extraction (this may take a few minutes)...")
        results = await extractor.extract(
            username=creds['username'],
            password=creds['password'],
            headless=True
        )
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"sicon_complete_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_file}")
        
        # Analyze results
        print("\n📊 EXTRACTION RESULTS:")
        print(f"Total manuscripts: {results.get('total_manuscripts', 0)}")
        
        # Detailed analysis
        total_referees = 0
        status_counts = {
            'Declined': 0,
            'No Response': 0,
            'Contacted, awaiting response': 0,
            'Report submitted': 0,
            'Accepted, awaiting report': 0,
            'Other': 0
        }
        
        print("\n📄 Manuscripts:")
        for ms in results.get('manuscripts', []):
            print(f"\n{ms['id']}: {ms['title'][:50]}...")
            print(f"  Status: {ms['status']}")
            print(f"  AE: {ms['associate_editor']}")
            print(f"  CE: {ms['corresponding_editor']}")
            
            # Count unique referees
            referees = ms.get('referees', [])
            total_referees += len(referees)
            
            # Group by status
            ms_status_counts = {}
            for ref in referees:
                status = ref.get('status', 'Unknown')
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts['Other'] += 1
                
                ms_status_counts[status] = ms_status_counts.get(status, 0) + 1
            
            print(f"\n  Referee breakdown ({len(referees)} total):")
            for status, count in sorted(ms_status_counts.items()):
                print(f"    - {status}: {count}")
            
            # Show some referee details
            if referees:
                print("\n  Sample referees:")
                for ref in referees[:3]:
                    print(f"    • {ref['name']} ({ref.get('status', 'Unknown')})")
                    if ref.get('email'):
                        print(f"      Email: {ref['email']}")
                    if ref.get('contact_date'):
                        print(f"      Contact: {ref['contact_date']}")
                    if ref.get('report_date'):
                        print(f"      Report: {ref['report_date']}")
                    if ref.get('due_date'):
                        print(f"      Due: {ref['due_date']}")
        
        # Overall summary
        print("\n" + "=" * 50)
        print("📈 OVERALL SUMMARY:")
        print(f"Total unique referees: {total_referees}")
        print("\nReferee status distribution:")
        for status, count in sorted(status_counts.items()):
            if count > 0:
                print(f"  - {status}: {count}")
        
        # Validation
        print("\n✅ VALIDATION:")
        if total_referees < 40:
            print("✓ Referee count reasonable (no massive duplication)")
        else:
            print("✗ Too many referees - possible duplication issue")
        
        if status_counts['Declined'] > 0 and any(status_counts[s] > 0 for s in ['Report submitted', 'Accepted, awaiting report']):
            print("✓ Mix of statuses found (not all 'Review pending')")
        else:
            print("✗ Status variety issue - check parsing logic")
        
        pdfs_found = sum(len(ms.get('pdf_urls', {})) for ms in results.get('manuscripts', []))
        if pdfs_found > 0:
            print(f"✓ PDFs found: {pdfs_found}")
        else:
            print("✗ No PDFs found")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = asyncio.run(run_complete_sicon_test())
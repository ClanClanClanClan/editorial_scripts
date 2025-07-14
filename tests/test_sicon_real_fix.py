#!/usr/bin/env python3
"""
Test the REAL SICON fix
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_real_sicon_fix():
    """Test the real SICON fix implementation"""
    
    print("🧪 TESTING REAL SICON FIX")
    print("=" * 50)
    
    try:
        # Import the real fix
        from unified_system.extractors.siam.sicon_real_fix import SICONRealExtractor
        
        print("✅ Successfully imported SICONRealExtractor")
        
        # Initialize extractor
        extractor = SICONRealExtractor()
        print("✅ Extractor initialized")
        
        # Run extraction (credentials come from environment)
        print("\n🚀 Starting extraction...")
        # The credentials are loaded from environment variables via credential manager
        result = await extractor.extract("", "")
        
        if result and result.get('manuscripts'):
            manuscripts = result['manuscripts']
            
            print(f"\n📊 EXTRACTION RESULTS:")
            print(f"Total manuscripts: {len(manuscripts)}")
            
            for i, ms in enumerate(manuscripts, 1):
                print(f"\n📄 Manuscript {i}: {ms.id}")
                print(f"   Title: {ms.title}")
                print(f"   Referees: {len(ms.referees)}")
                
                # Show referee details
                for j, ref in enumerate(ms.referees, 1):
                    print(f"     {j}. {ref.name}")
                    print(f"        Email: {ref.email}")
                    print(f"        Status: {ref.status}")
                    if hasattr(ref, 'contact_date') and ref.contact_date:
                        print(f"        Contact Date: {ref.contact_date}")
                    if hasattr(ref, 'report_date') and ref.report_date:
                        print(f"        Report Date: {ref.report_date}")
                    if hasattr(ref, 'due_date') and ref.due_date:
                        print(f"        Due Date: {ref.due_date}")
                
                # Status breakdown
                statuses = {}
                for ref in ms.referees:
                    statuses[ref.status] = statuses.get(ref.status, 0) + 1
                
                print(f"   Status breakdown:")
                for status, count in statuses.items():
                    print(f"     - {status}: {count}")
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"sicon_real_fix_test_{timestamp}.json"
            
            # Convert to serializable format
            serializable_result = {
                "extraction_time": timestamp,
                "journal": "SICON",
                "total_manuscripts": len(manuscripts),
                "manuscripts": []
            }
            
            for ms in manuscripts:
                ms_data = {
                    "id": ms.id,
                    "title": ms.title,
                    "authors": ms.authors,
                    "status": ms.status,
                    "submission_date": getattr(ms, 'submission_date', ''),
                    "associate_editor": getattr(ms, 'associate_editor', ''),
                    "corresponding_editor": getattr(ms, 'corresponding_editor', ''),
                    "referees": []
                }
                
                for ref in ms.referees:
                    ref_data = {
                        "name": ref.name,
                        "email": ref.email,
                        "status": ref.status,
                        "institution": getattr(ref, 'institution', ''),
                        "contact_date": getattr(ref, 'contact_date', ''),
                        "report_date": getattr(ref, 'report_date', ''),
                        "due_date": getattr(ref, 'due_date', ''),
                        "declined": getattr(ref, 'declined', False),
                        "report_submitted": getattr(ref, 'report_submitted', False)
                    }
                    ms_data["referees"].append(ref_data)
                
                serializable_result["manuscripts"].append(ms_data)
            
            with open(output_file, 'w') as f:
                json.dump(serializable_result, f, indent=2)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            # Compare with expected
            total_refs = sum(len(ms.referees) for ms in manuscripts)
            print(f"\n🎯 COMPARISON:")
            print(f"Expected: ~13 unique referees with proper statuses")
            print(f"Actual: {total_refs} referees")
            
            if total_refs < 20:  # Much better than 44!
                print("✅ MAJOR IMPROVEMENT: Reduced duplicates!")
            else:
                print("❌ Still too many referees")
                
        else:
            print("❌ No manuscripts extracted")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_sicon_fix())
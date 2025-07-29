#!/usr/bin/env python3
"""
Test that referee extraction works for both manuscripts in Pass 1
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add path to import the MF extractor  
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials
    load_credentials()
except ImportError:
    from dotenv import load_dotenv
    load_dotenv('.env.production')

from mf_extractor import ComprehensiveMFExtractor

def test_referee_extraction():
    """Test that referees are extracted from both manuscripts"""
    print("🔍 Testing referee extraction fix...")
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Run extraction
        success = extractor.extract_all()
        
        if not success:
            print("❌ Extraction failed")
            return False
            
        # Check results
        if len(extractor.manuscripts) < 2:
            print(f"❌ Expected at least 2 manuscripts, got {len(extractor.manuscripts)}")
            return False
            
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'mf_test_referee_fix_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump(extractor.manuscripts, f, indent=2, default=str)
            
        print(f"\n✅ Saved results to {output_file}")
        
        # Analyze referee counts
        print("\n📊 Referee extraction summary:")
        total_referees = 0
        
        for i, manuscript in enumerate(extractor.manuscripts[:2]):  # Check first 2
            referee_count = len(manuscript.get('referees', []))
            total_referees += referee_count
            
            print(f"\nManuscript {i+1}: {manuscript.get('id')}")
            print(f"  Title: {manuscript.get('title', 'Unknown')[:60]}...")
            print(f"  Status: {manuscript.get('status')}")
            print(f"  Referees: {referee_count}")
            
            if referee_count > 0:
                for j, referee in enumerate(manuscript['referees']):
                    print(f"    {j+1}. {referee.get('name')} - {referee.get('status')}")
            else:
                print(f"    ⚠️ NO REFEREES FOUND!")
                
        print(f"\n📊 Total referees across first 2 manuscripts: {total_referees}")
        
        if total_referees == 6:
            print("✅ SUCCESS: All 6 referees extracted (4 + 2)!")
            return True
        else:
            print(f"❌ FAIL: Expected 6 referees, got {total_referees}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if hasattr(extractor, 'driver') and extractor.driver:
            extractor.driver.quit()

if __name__ == "__main__":
    success = test_referee_extraction()
    sys.exit(0 if success else 1)
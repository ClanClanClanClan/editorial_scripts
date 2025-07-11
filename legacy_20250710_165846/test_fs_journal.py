#!/usr/bin/env python3
"""
Test FS journal functionality (no authentication required)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from journals.fs import FSJournal

def test_fs_journal():
    """Test FS journal functionality"""
    print("Testing FS journal...")
    
    try:
        # FS journal doesn't need a driver
        fs_journal = FSJournal(driver=None)
        print(f"✅ FS journal created: {type(fs_journal).__name__}")
        
        # Test the scraping method
        print("🔄 Testing FS journal scraping...")
        manuscripts = fs_journal.scrape_manuscripts_and_emails()
        
        print(f"✅ FS journal scraping completed")
        print(f"   Found {len(manuscripts)} manuscripts")
        
        if manuscripts:
            print(f"   Sample manuscript keys: {list(manuscripts[0].keys())}")
            
            # Check if downloads were added
            if 'downloads' in manuscripts[0]:
                print(f"   Downloads functionality: ✅ Integrated")
            else:
                print(f"   Downloads functionality: ❌ Not integrated")
        
        return True
        
    except Exception as e:
        print(f"❌ FS journal test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fs_journal()
    if success:
        print("\n✅ FS journal tests completed")
    else:
        print("\n❌ FS journal tests failed")
        sys.exit(1)
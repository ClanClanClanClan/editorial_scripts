#!/usr/bin/env python3
"""
Test JOTA hybrid approach functionality
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from journals.jota_hybrid import JOTAHybridScraper, JOTAJournal

def test_jota_hybrid():
    """Test JOTA hybrid approach"""
    print("Testing JOTA hybrid approach...")
    
    try:
        # Test the hybrid scraper initialization
        scraper = JOTAHybridScraper(debug=True)
        print(f"✅ JOTA hybrid scraper created: {type(scraper).__name__}")
        
        # Test the compatibility wrapper
        journal = JOTAJournal(debug=True)
        print(f"✅ JOTA journal wrapper created: {type(journal).__name__}")
        
        # Test credentials
        print(f"✅ JOTA credentials: username={'Yes' if scraper.username else 'No'}, password={'Yes' if scraper.password else 'No'}")
        
        # Test URLs
        print(f"✅ JOTA URLs configured:")
        print(f"   Base: {scraper.base_url}")
        print(f"   Login: {scraper.login_url}")
        print(f"   Main: {scraper.main_url}")
        
        # Test paper downloader integration
        print(f"✅ Paper downloader: {'Yes' if hasattr(scraper, 'paper_downloader') else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ JOTA hybrid test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jota_hybrid()
    if success:
        print("\n✅ JOTA hybrid tests completed")
    else:
        print("\n❌ JOTA hybrid tests failed")
        sys.exit(1)
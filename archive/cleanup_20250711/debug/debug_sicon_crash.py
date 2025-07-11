#!/usr/bin/env python3
"""
Debug SICON crash issue
"""

from journals.sicon import SICON
import time
import traceback

def debug_sicon_crash():
    """Debug SICON crash step by step"""
    print("🔍 DEBUGGING SICON CRASH")
    
    sicon = SICON()
    
    try:
        print("1. Setting up driver...")
        sicon.setup_driver(headless=True)
        print("   ✅ Driver setup successful")
        
        print("2. Authenticating...")
        if sicon.authenticate():
            print("   ✅ Authentication successful")
        else:
            print("   ❌ Authentication failed")
            return
        
        print("3. Navigating to manuscripts...")
        sicon._navigate_to_manuscripts()
        print("   ✅ Navigation successful")
        
        print("4. Parsing manuscripts table...")
        manuscripts = sicon._parse_manuscripts_table()
        print(f"   ✅ Found {len(manuscripts)} manuscripts")
        
        if manuscripts:
            print("5. Testing referee extraction on first manuscript...")
            sicon._extract_referee_details(manuscripts[0])
            print("   ✅ Referee extraction successful")
        
        print("✅ SICON debugging completed successfully")
        
    except Exception as e:
        print(f"❌ SICON crashed at step: {e}")
        traceback.print_exc()
        
        # Save page source for debugging
        try:
            with open("sicon_crash_debug.html", "w") as f:
                f.write(sicon.driver.page_source)
            print("💾 Saved page source to sicon_crash_debug.html")
        except:
            pass
    
    finally:
        try:
            sicon.driver.quit()
        except:
            pass

if __name__ == "__main__":
    debug_sicon_crash()
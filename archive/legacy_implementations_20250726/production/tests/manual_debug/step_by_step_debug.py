#!/usr/bin/env python3
"""
Step by step debug to find where the hang occurs
"""

import sys
import time
import os
from pathlib import Path

# Add path to import the MF extractor  
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials
    load_credentials()
except ImportError:
    from dotenv import load_dotenv
    load_dotenv('.env.production')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from mf_extractor import ComprehensiveMFExtractor

def step_by_step_debug():
    """Debug each step to find where it hangs"""
    print("🔍 Step-by-step debugging...")
    
    try:
        print("\n1️⃣ Creating extractor...")
        extractor = ComprehensiveMFExtractor()
        print("   ✅ Extractor created")
        
        print("\n2️⃣ Starting login...")
        login_start = time.time()
        login_success = extractor.login()
        login_time = time.time() - login_start
        print(f"   ✅ Login completed in {login_time:.1f}s: {login_success}")
        
        if not login_success:
            print("   ❌ Login failed - stopping")
            return
            
        print("\n3️⃣ Navigating to AE Center...")
        nav_start = time.time()
        nav_success = extractor.navigate_to_ae_center()
        nav_time = time.time() - nav_start
        print(f"   ✅ Navigation completed in {nav_time:.1f}s: {nav_success}")
        
        if not nav_success:
            print("   ❌ Navigation failed - stopping")
            return
            
        print("\n4️⃣ Getting categories...")
        cat_start = time.time()
        categories = extractor.get_manuscript_categories()
        cat_time = time.time() - cat_start
        print(f"   ✅ Categories retrieved in {cat_time:.1f}s: {len(categories)} found")
        
        print("\n5️⃣ Finding target category...")
        target_category = None
        for category in categories:
            if "Awaiting Reviewer Scores" in category['name']:
                target_category = category
                print(f"   ✅ Found target: {category['name']} ({category['count']} manuscripts)")
                break
                
        if not target_category:
            print("   ❌ No target category - stopping")
            return
            
        print("\n6️⃣ Clicking category...")
        click_start = time.time()
        target_category['link'].click()
        time.sleep(3)
        click_time = time.time() - click_start
        print(f"   ✅ Category clicked in {click_time:.1f}s")
        
        print("\n7️⃣ Finding Take Action links...")
        take_action_links = extractor.driver.find_elements(By.XPATH, 
            "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
        print(f"   ✅ Found {len(take_action_links)} Take Action links")
        
        if len(take_action_links) < 1:
            print("   ❌ No Take Action links - stopping")
            return
            
        print("\n8️⃣ Clicking first Take Action...")
        action_start = time.time()
        take_action_links[0].click()
        time.sleep(5)
        action_time = time.time() - action_start
        print(f"   ✅ Take Action clicked in {action_time:.1f}s")
        
        print("\n9️⃣ Getting manuscript info...")
        info_start = time.time()
        manuscript_count, manuscript_data, manuscript_order = extractor.extract_basic_manuscript_info()
        info_time = time.time() - info_start
        print(f"   ✅ Manuscript info extracted in {info_time:.1f}s")
        print(f"      Found {manuscript_count} manuscripts: {manuscript_order}")
        
        print("\n🔟 Testing simple page elements...")
        current_id = extractor.get_current_manuscript_id()
        print(f"   Current manuscript ID: {current_id}")
        
        # Test finding referee rows without processing
        referee_rows = extractor.driver.find_elements(By.XPATH, 
            "//td[@class='tablelines']//tr[.//a[contains(@href,'mailpopup')]]")
        print(f"   Found {len(referee_rows)} rows with mailpopup links")
        
        print("\n✅ ALL STEPS COMPLETED SUCCESSFULLY!")
        print("   The hang must be in the actual referee processing, not navigation")
        
    except Exception as e:
        print(f"\n❌ Error at current step: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n⏰ Closing browser...")
        if 'extractor' in locals() and hasattr(extractor, 'driver') and extractor.driver:
            extractor.driver.quit()

if __name__ == "__main__":
    step_by_step_debug()
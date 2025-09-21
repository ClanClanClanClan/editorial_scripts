#!/usr/bin/env python3
"""
REAL test of MOR extractor - actually run it and fix issues
"""

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium.common.exceptions import TimeoutException

print("="*60)
print("🔬 REAL MOR EXTRACTOR TEST")
print("="*60)

try:
    # Create instance
    print("\n1️⃣ Creating MOR instance...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Instance created")
    
    # Initialize driver
    print("\n2️⃣ Initializing Chrome driver...")
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Driver initialized")
    
    # Test login
    print("\n3️⃣ Testing login...")
    login_success = mor.login()
    
    if login_success:
        print("   ✅ Login successful!")
        
        # Test navigation
        print("\n4️⃣ Testing navigation to AE Center...")
        if mor.navigate_to_ae_center():
            print("   ✅ Navigated to AE Center")
            
            # Try to find manuscripts
            print("\n5️⃣ Looking for manuscripts...")
            
            # Check what's on the page
            from selenium.webdriver.common.by import By
            links = mor.driver.find_elements(By.TAG_NAME, "a")
            link_texts = [mor.safe_get_text(link) for link in links if mor.safe_get_text(link)]
            
            manuscript_related = [t for t in link_texts if any(word in t.lower() for word in ['manuscript', 'await', 'review', 'overdue'])]
            
            if manuscript_related:
                print(f"   Found {len(manuscript_related)} manuscript-related links:")
                for i, text in enumerate(manuscript_related[:5]):
                    print(f"      {i+1}. {text}")
            
            # Try to click on a category
            print("\n6️⃣ Testing category navigation...")
            category = "Awaiting Reviewer Reports"
            
            try:
                category_link = mor.driver.find_element(By.LINK_TEXT, category)
                mor.safe_click(category_link)
                mor.smart_wait(3)
                print(f"   ✅ Clicked on '{category}'")
                
                # Check for manuscripts
                manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                print(f"   Found {len(manuscript_rows)} manuscript rows")
                
                if manuscript_rows:
                    # Try to process first manuscript
                    print("\n7️⃣ Testing manuscript extraction...")
                    
                    row = manuscript_rows[0]
                    row_text = mor.safe_get_text(row)
                    print(f"   First manuscript: {row_text[:100]}")
                    
                    # Click on it
                    check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
                    if check_icon:
                        parent_link = check_icon.find_element(By.XPATH, "./parent::*")
                        mor.safe_click(parent_link)
                        mor.smart_wait(3)
                        print("   ✅ Clicked on manuscript")
                        
                        # Check what tab we're on
                        print("\n8️⃣ Checking current page...")
                        page_title = mor.driver.title
                        print(f"   Page title: {page_title}")
                        
                        # Look for tabs
                        tabs = mor.driver.find_elements(By.XPATH, "//a[contains(@href, 'TAB')]")
                        tab_texts = [mor.safe_get_text(tab) for tab in tabs]
                        print(f"   Available tabs: {tab_texts}")
                        
                        # Test referee extraction
                        print("\n9️⃣ Testing referee extraction...")
                        referee_tabs = mor.driver.find_elements(By.XPATH,
                            "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")
                        
                        if referee_tabs:
                            print(f"   Found referee tab: {mor.safe_get_text(referee_tabs[0])}")
                            mor.safe_click(referee_tabs[0])
                            mor.smart_wait(2)
                            print("   ✅ Clicked referee tab")
                            
                            # Check for referee rows
                            referee_indicators = mor.driver.find_elements(By.XPATH,
                                "//*[contains(text(), 'Declined') or contains(text(), 'Agreed') or contains(text(), 'Invited')]")
                            
                            print(f"   Found {len(referee_indicators)} referee status indicators")
                        else:
                            print("   ❌ No referee tab found")
                            
                else:
                    print("   ❌ No manuscripts found")
                    
            except Exception as e:
                print(f"   ❌ Category navigation failed: {e}")
                
        else:
            print("   ❌ Failed to navigate to AE Center")
    else:
        print("   ❌ Login failed")
        
except KeyboardInterrupt:
    print("\n⚠️ Test interrupted by user")
except TimeoutException as e:
    print(f"\n⚠️ Timeout: {e}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
finally:
    # Cleanup
    if 'mor' in locals() and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
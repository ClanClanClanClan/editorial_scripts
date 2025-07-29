#!/usr/bin/env python3
"""
Simple test to debug tab clicking
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_simple_tab_click():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Quick login and navigation
        login_success = extractor.login()
        if not login_success:
            return
        
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = extractor.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1
        
        time.sleep(3)
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(5)
        
        categories = extractor.get_manuscript_categories()
        if categories:
            for category in categories:
                if category['count'] > 0:
                    category['link'].click()
                    time.sleep(3)
                    
                    take_action_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                    if take_action_links:
                        take_action_links[0].click()
                        time.sleep(5)
                        
                        manuscript_id = extractor.get_current_manuscript_id()
                        print(f"🧪 SIMPLE TAB CLICK TEST FOR {manuscript_id}")
                        print("="*70)
                        
                        # Find the manuscript info tab image and ALL its parents
                        print("\n🔍 FINDING MANUSCRIPT INFO TAB STRUCTURE:")
                        info_img = extractor.driver.find_element(By.XPATH, "//img[contains(@src, 'lefttabs_mss_info')]")
                        print(f"   Image found: {info_img.get_attribute('src').split('/')[-1]}")
                        
                        # Try different parent levels
                        current_element = info_img
                        parents = []
                        for i in range(5):
                            try:
                                parent = current_element.find_element(By.XPATH, "..")
                                tag = parent.tag_name
                                onclick = parent.get_attribute('onclick')
                                href = parent.get_attribute('href')
                                print(f"   Parent {i+1}: <{tag}> onclick='{onclick}' href='{href}'")
                                parents.append(parent)
                                current_element = parent
                            except:
                                break
                        
                        # Try clicking different elements
                        print("\n🖱️ TRYING DIFFERENT CLICK APPROACHES:")
                        
                        # Method 1: Click the anchor directly if it exists
                        try:
                            anchor = extractor.driver.find_element(By.XPATH, "//a[.//img[contains(@src, 'lefttabs_mss_info')]]")
                            print(f"\n   Method 1: Found anchor tag with href: {anchor.get_attribute('href')}")
                            print(f"   Clicking anchor...")
                            anchor.click()
                            time.sleep(3)
                            
                            # Check if anything changed
                            new_text = extractor.driver.find_element(By.TAG_NAME, "body").text[:200]
                            print(f"   Page text after click: {new_text}")
                            
                        except Exception as e:
                            print(f"   Method 1 failed: {e}")
                        
                        # Method 2: JavaScript click on the image
                        try:
                            print(f"\n   Method 2: JavaScript click on image...")
                            extractor.driver.execute_script("arguments[0].click();", info_img)
                            time.sleep(3)
                            
                            new_text = extractor.driver.find_element(By.TAG_NAME, "body").text[:200]
                            print(f"   Page text after click: {new_text}")
                            
                        except Exception as e:
                            print(f"   Method 2 failed: {e}")
                        
                        # Method 3: Find any onclick handler
                        try:
                            print(f"\n   Method 3: Looking for onclick handlers...")
                            clickable = extractor.driver.find_element(By.XPATH, 
                                "//img[contains(@src, 'lefttabs_mss_info')]/ancestor::*[@onclick][1]")
                            onclick = clickable.get_attribute('onclick')
                            print(f"   Found element with onclick: {onclick}")
                            print(f"   Executing onclick...")
                            extractor.driver.execute_script(onclick)
                            time.sleep(3)
                            
                            new_text = extractor.driver.find_element(By.TAG_NAME, "body").text[:200]
                            print(f"   Page text after click: {new_text}")
                            
                        except Exception as e:
                            print(f"   Method 3 failed: {e}")
                        
                        print("\n✅ Tab click test complete!")
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser in 10 seconds...")
        time.sleep(10)
        extractor.driver.quit()

if __name__ == "__main__":
    test_simple_tab_click()
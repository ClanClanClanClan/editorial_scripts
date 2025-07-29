#!/usr/bin/env python3
"""
Diagnostic test for tab navigation - check what actually happens when we click tabs
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_tab_diagnostic():
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
                        print(f"🧪 DIAGNOSTIC TEST FOR {manuscript_id}")
                        print("="*70)
                        
                        # Before clicking any tab
                        print("\n📍 INITIAL STATE:")
                        print(f"   URL: {extractor.driver.current_url}")
                        print(f"   Current tab detection: {extractor.get_current_tab()}")
                        
                        # Find all tab images
                        print("\n🔍 FINDING ALL TAB IMAGES:")
                        tab_images = extractor.driver.find_elements(By.XPATH, "//img[contains(@src, 'lefttabs_')]")
                        for img in tab_images:
                            src = img.get_attribute('src')
                            print(f"   - {src.split('/')[-1]}")
                        
                        # Test Manuscript Information tab
                        print("\n📋 CLICKING MANUSCRIPT INFORMATION TAB:")
                        try:
                            # Find the image element
                            info_img = extractor.driver.find_element(By.XPATH, "//img[contains(@src, 'lefttabs_mss_info')]")
                            print(f"   Found image: {info_img.get_attribute('src').split('/')[-1]}")
                            
                            # Get the clickable parent (usually an anchor tag)
                            info_tab = info_img.find_element(By.XPATH, "../..")
                            print(f"   Parent element tag: {info_tab.tag_name}")
                            
                            # Click
                            info_tab.click()
                            time.sleep(3)
                            
                            print(f"\n   AFTER CLICK:")
                            print(f"   URL: {extractor.driver.current_url}")
                            print(f"   Current tab detection: {extractor.get_current_tab()}")
                            
                            # Check page content
                            page_text = extractor.driver.find_element(By.TAG_NAME, "body").text[:500]
                            print(f"   Page content preview: {page_text[:200]}...")
                            
                            # Check for specific elements that should be on manuscript info page
                            author_elements = extractor.driver.find_elements(By.XPATH, 
                                "//*[contains(text(), 'Author') or contains(text(), 'Corresponding')]")
                            print(f"   Author-related elements found: {len(author_elements)}")
                            
                        except Exception as e:
                            print(f"   ❌ Error: {e}")
                        
                        # Navigate back (if needed)
                        print("\n🔙 GOING BACK TO MAIN PAGE:")
                        extractor.navigate_to_main_page(manuscript_id)
                        
                        # Test Audit Trail tab
                        print("\n📊 CLICKING AUDIT TRAIL TAB:")
                        try:
                            # Find the image element
                            audit_img = extractor.driver.find_element(By.XPATH, "//img[contains(@src, 'lefttabs_audit_trail')]")
                            print(f"   Found image: {audit_img.get_attribute('src').split('/')[-1]}")
                            
                            # Get the clickable parent
                            audit_tab = audit_img.find_element(By.XPATH, "../..")
                            print(f"   Parent element tag: {audit_tab.tag_name}")
                            
                            # Click
                            audit_tab.click()
                            time.sleep(3)
                            
                            print(f"\n   AFTER CLICK:")
                            print(f"   URL: {extractor.driver.current_url}")
                            print(f"   Current tab detection: {extractor.get_current_tab()}")
                            
                            # Check page content
                            page_text = extractor.driver.find_element(By.TAG_NAME, "body").text[:500]
                            print(f"   Page content preview: {page_text[:200]}...")
                            
                            # Check for specific elements
                            audit_elements = extractor.driver.find_elements(By.XPATH, 
                                "//*[contains(text(), 'Date') or contains(text(), 'Action') or contains(text(), 'Email')]")
                            print(f"   Audit-related elements found: {len(audit_elements)}")
                            
                        except Exception as e:
                            print(f"   ❌ Error: {e}")
                        
                        print("\n✅ Diagnostic test complete!")
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
    test_tab_diagnostic()
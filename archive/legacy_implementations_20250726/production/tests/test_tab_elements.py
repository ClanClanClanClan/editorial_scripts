#!/usr/bin/env python3
"""
Test to find unique elements on the manuscript info tab
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By

def test_tab_elements():
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
                        print(f"🔍 FINDING UNIQUE ELEMENTS FOR {manuscript_id}")
                        print("="*70)
                        
                        # Click Manuscript Information tab
                        print("\n📋 CLICKING MANUSCRIPT INFORMATION TAB...")
                        try:
                            info_img = extractor.driver.find_element(By.XPATH, "//img[contains(@src, 'lefttabs_mss_info')]")
                            info_tab = info_img.find_element(By.XPATH, "../..")
                            info_tab.click()
                            time.sleep(3)
                            
                            print("\n🔍 SEARCHING FOR UNIQUE ELEMENTS ON THIS PAGE:")
                            
                            # Get page text to understand what we're looking at
                            page_text = extractor.driver.find_element(By.TAG_NAME, "body").text
                            
                            print("\n📌 First 1000 characters of page:")
                            print(page_text[:1000])
                            print("\n" + "="*50 + "\n")
                            
                            # Look for all td elements with text
                            all_tds = extractor.driver.find_elements(By.XPATH, "//td")
                            
                            print(f"\n📌 Total TD elements found: {len(all_tds)}")
                            
                            # Find TDs with interesting text
                            interesting_tds = []
                            for td in all_tds:
                                text = td.text.strip()
                                if text and len(text) > 3 and len(text) < 100:
                                    interesting_tds.append(text)
                            
                            print(f"\n📌 First 20 interesting TD texts:")
                            for i, text in enumerate(interesting_tds[:20]):
                                print(f"   {i+1}. {text}")
                            
                            # Look for specific patterns
                            print("\n📌 Checking for specific patterns:")
                            
                            patterns = [
                                ("Author elements", "//td[contains(text(), 'Author')]"),
                                ("Title elements", "//td[contains(text(), 'Title:')]"),
                                ("Manuscript ID elements", "//td[contains(text(), 'Manuscript ID:')]"),
                                ("Submission Date elements", "//td[contains(text(), 'Submission Date:')]"),
                                ("Running Head elements", "//td[contains(text(), 'Running Head:')]"),
                                ("Article Type elements", "//td[contains(text(), 'Article Type:')]"),
                                ("Special Issue elements", "//td[contains(text(), 'Special Issue:')]"),
                                ("Page Count elements", "//td[contains(text(), 'Page Count:')]")
                            ]
                            
                            for name, xpath in patterns:
                                elements = extractor.driver.find_elements(By.XPATH, xpath)
                                if elements:
                                    print(f"   ✅ {name}: {len(elements)} found")
                                    if elements:
                                        print(f"      First text: '{elements[0].text.strip()}'")
                            
                            # Check page structure
                            print("\n📌 Checking page structure:")
                            forms = extractor.driver.find_elements(By.TAG_NAME, "form")
                            print(f"   Forms on page: {len(forms)}")
                            
                            tables = extractor.driver.find_elements(By.TAG_NAME, "table")
                            print(f"   Tables on page: {len(tables)}")
                            
                            # Look for manuscript info specific table
                            info_tables = extractor.driver.find_elements(By.XPATH, 
                                "//table[.//td[contains(text(), 'Running Head:') or contains(text(), 'Article Type:')]]")
                            print(f"   Manuscript info tables: {len(info_tables)}")
                            
                        except Exception as e:
                            print(f"❌ Error: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        print("\n✅ Element search complete!")
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
    test_tab_elements()
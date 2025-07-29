#!/usr/bin/env python3
"""
Debug the actual HTML table structure to find referee vs author tables
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By

def debug_tables():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Quick login and navigation (reusing previous logic)
        login_success = extractor.login()
        if not login_success:
            return
        
        # Navigate to manuscript page
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
                        
                        print("🔍 ANALYZING HTML TABLE STRUCTURE")
                        print("="*60)
                        
                        # Find ALL tables on the page
                        all_tables = extractor.driver.find_elements(By.TAG_NAME, "table")
                        print(f"Found {len(all_tables)} tables on the page")
                        
                        # Analyze each table
                        for i, table in enumerate(all_tables):
                            print(f"\n📊 TABLE {i+1}:")
                            print("-" * 30)
                            
                            # Get table text preview
                            table_text = table.text[:200]
                            print(f"Text preview: {table_text}...")
                            
                            # Look for mailpopup links in this table
                            mailpopup_links = table.find_elements(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                            if mailpopup_links:
                                print(f"✅ FOUND {len(mailpopup_links)} mailpopup links in this table:")
                                for j, link in enumerate(mailpopup_links[:10]):  # Show first 10
                                    name = link.text.strip()
                                    print(f"   {j+1}. {name}")
                                
                                # Check what's around this table (parent elements, headers, etc.)
                                try:
                                    parent = table.find_element(By.XPATH, "./..")
                                    parent_text = parent.text[:100]
                                    print(f"Parent context: {parent_text}...")
                                except:
                                    pass
                                
                                # Look for table headers or nearby text that indicates what this table is
                                try:
                                    # Look for preceding text/headers
                                    preceding_elements = extractor.driver.find_elements(By.XPATH, 
                                        f"//table[{i+1}]/preceding::*[contains(text(), 'Referee') or contains(text(), 'Author') or contains(text(), 'Review')]")
                                    if preceding_elements:
                                        for elem in preceding_elements[-3:]:  # Last 3 preceding elements
                                            elem_text = elem.text.strip()
                                            if elem_text and len(elem_text) < 100:
                                                print(f"Preceding: {elem_text}")
                                except:
                                    pass
                            
                        print("\n" + "="*60)
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n⏸️ Closing browser in 15 seconds...")
        time.sleep(15)
        extractor.driver.quit()

if __name__ == "__main__":
    debug_tables()
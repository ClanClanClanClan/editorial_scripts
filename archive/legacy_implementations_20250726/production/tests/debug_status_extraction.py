#!/usr/bin/env python3
"""
Debug status extraction from referee table
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By

def debug_status_extraction():
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
                        print(f"🔍 DEBUGGING STATUS EXTRACTION FOR {manuscript_id}")
                        print("="*70)
                        
                        # Find the referee table
                        all_tables = extractor.driver.find_elements(By.TAG_NAME, "table")
                        referee_table = None
                        
                        for i, table in enumerate(all_tables):
                            try:
                                mailpopup_links = table.find_elements(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                                if len(mailpopup_links) == 4:
                                    table_text = table.text
                                    if 'Reviewer List' in table_text:
                                        referee_table = table
                                        print(f"✅ Found referee table {i+1}")
                                        break
                            except:
                                continue
                        
                        if referee_table:
                            # Get all rows with mailpopup links
                            rows_with_links = referee_table.find_elements(By.XPATH, ".//tr[.//a[contains(@href,'mailpopup')]]")
                            print(f"📊 Found {len(rows_with_links)} referee rows")
                            
                            for row_idx, row in enumerate(rows_with_links, 1):
                                # Get referee name
                                name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                                referee_name = name_link.text.strip()
                                
                                print(f"\n👤 REFEREE {row_idx}: {referee_name}")
                                print("-" * 40)
                                
                                # Debug: Show all cells in this row
                                all_cells = row.find_elements(By.TAG_NAME, "td")
                                print(f"📊 Row has {len(all_cells)} cells:")
                                
                                for cell_idx, cell in enumerate(all_cells):
                                    cell_text = cell.text.strip()
                                    print(f"   Cell {cell_idx}: '{cell_text[:100]}{'...' if len(cell_text) > 100 else ''}'")
                                
                                # Look for status in the row HTML
                                row_html = row.get_attribute('outerHTML')
                                print(f"\n🔍 Looking for status in row HTML...")
                                
                                # Check for status keywords
                                status_keywords = ['Agreed', 'Declined', 'Unavailable', 'Invited', 'Returned']
                                found_status = None
                                for keyword in status_keywords:
                                    if keyword in row_html:
                                        found_status = keyword
                                        print(f"   ✅ Found '{keyword}' in row HTML")
                                        break
                                
                                if not found_status:
                                    print(f"   ❌ No status keywords found in row")
                                
                                # Also check if there are review links in status area
                                review_links = row.find_elements(By.XPATH, ".//a[contains(@href, 'REVIEW') or contains(text(), 'review') or contains(text(), 'Review')]")
                                if review_links:
                                    print(f"   🔗 Found {len(review_links)} potential review links:")
                                    for link in review_links:
                                        link_text = link.text.strip()
                                        link_href = link.get_attribute('href')
                                        print(f"      - '{link_text}' -> {link_href[:60]}...")
                                else:
                                    print(f"   📝 No review links found in this row")
                        
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser in 15 seconds...")
        time.sleep(15)
        extractor.driver.quit()

if __name__ == "__main__":
    debug_status_extraction()
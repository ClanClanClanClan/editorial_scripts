#!/usr/bin/env python3
"""Find where the View Review links actually are."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print("🔍 FINDING VIEW REVIEW LINKS")
print("=" * 60)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print("✅ Login successful\n")
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)
        
        # Get first category
        categories = extractor.get_manuscript_categories()
        if categories:
            test_category = categories[0]
            
            # Click category
            category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, test_category['name'])
            if category_links:
                category_links[0].click()
                time.sleep(3)
                
                # Click first manuscript
                manuscript_links = extractor.driver.find_elements(By.XPATH, 
                    "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                if manuscript_links:
                    manuscript_links[0].click()
                    time.sleep(5)
                    
                    print("🔍 SEARCHING FOR ALL LINKS ON PAGE:")
                    print("=" * 50)
                    
                    # Find ALL links on the page
                    all_links = extractor.driver.find_elements(By.XPATH, "//a")
                    
                    review_related_links = []
                    
                    for link in all_links:
                        link_text = link.text.strip()
                        href = link.get_attribute('href') or ''
                        
                        # Look for review-related text
                        if any(word in link_text.lower() for word in ['review', 'report', 'view', 'submitted', 'recommendation']) or \
                           any(word in href.lower() for word in ['review', 'report', 'rev_ms_det', 'popup']):
                            review_related_links.append((link_text, href))
                    
                    print(f"Found {len(review_related_links)} review-related links:")
                    for i, (text, href) in enumerate(review_related_links):
                        print(f"  {i+1}. Text: \"{text}\" -> {href[:80]}...")
                    
                    print("\n🔍 EXAMINING REFEREE TABLE STRUCTURE:")
                    print("=" * 50)
                    
                    # Look at the actual table structure
                    referee_table = extractor.driver.find_element(By.XPATH, "//table[.//select[contains(@name, 'ORDER')]]")
                    
                    # Get all rows in the referee table
                    table_rows = referee_table.find_elements(By.XPATH, ".//tr")
                    
                    print(f"Found {len(table_rows)} rows in referee table\n")
                    
                    # Look at header row first
                    if table_rows:
                        header_row = table_rows[0]
                        header_cells = header_row.find_elements(By.XPATH, ".//th | .//td")
                        print("HEADER ROW:")
                        for i, cell in enumerate(header_cells):
                            cell_text = cell.text.strip()
                            print(f"  Column {i}: \"{cell_text}\"")
                        print()
                    
                    # Now look at referee data rows
                    referee_data_rows = [row for row in table_rows if row.find_elements(By.XPATH, ".//select[contains(@name, 'ORDER')]")]
                    
                    for i, row in enumerate(referee_data_rows):
                        print(f"REFEREE ROW {i+1}:")
                        cells = row.find_elements(By.XPATH, ".//td")
                        
                        for j, cell in enumerate(cells):
                            cell_text = cell.text.strip()
                            cell_links = cell.find_elements(By.XPATH, ".//a")
                            
                            print(f"  Cell {j}: \"{cell_text[:50]}{'...' if len(cell_text) > 50 else ''}\"")
                            
                            if cell_links:
                                for k, link in enumerate(cell_links):
                                    link_text = link.text.strip()
                                    href = link.get_attribute('href') or ''
                                    print(f"    Link {k+1}: \"{link_text}\" -> {href[:60]}...")
                        print()
                    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
    print("\n🏁 Debug complete")
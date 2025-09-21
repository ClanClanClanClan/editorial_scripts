#!/usr/bin/env python3
"""Check the Overdue Reviewer Scores category for submitted reports."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print("🔍 CHECKING OVERDUE REVIEWER SCORES CATEGORY")
print("=" * 60)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print("✅ Login successful\n")
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)
        
        # Get categories
        categories = extractor.get_manuscript_categories()
        if categories and len(categories) > 1:
            # Click on "Overdue Reviewer Scores" category
            overdue_category = categories[1]  # Should be Overdue
            print(f"📂 Clicking category: {overdue_category['name']} ({overdue_category['count']} manuscripts)")
            
            # Click category
            category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, overdue_category['name'])
            if category_links:
                category_links[0].click()
                time.sleep(3)
                
                # Click first manuscript
                manuscript_links = extractor.driver.find_elements(By.XPATH, 
                    "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                if manuscript_links:
                    print(f"📄 Found {len(manuscript_links)} manuscripts, clicking first one...")
                    manuscript_links[0].click()
                    time.sleep(5)
                    
                    # Look for referee status with different text
                    print("\n🧑‍⚖️ CHECKING REFEREE STATUS FOR SUBMITTED REPORTS:")
                    print("=" * 60)
                    
                    # Find referee table
                    referee_rows = extractor.driver.find_elements(By.XPATH, 
                        "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                    
                    for i, row in enumerate(referee_rows):
                        print(f"\nREFEREE {i+1}:")
                        cells = row.find_elements(By.XPATH, ".//td")
                        
                        for j, cell in enumerate(cells):
                            cell_text = cell.text.strip()
                            print(f"  Cell {j}: {cell_text[:100]}{'...' if len(cell_text) > 100 else ''}")
                            
                            # Look for any links in this cell
                            cell_links = cell.find_elements(By.XPATH, ".//a")
                            for k, link in enumerate(cell_links):
                                link_text = link.text.strip()
                                href = link.get_attribute('href') or ''
                                
                                # Check for report-related links
                                if any(word in link_text.lower() for word in ['view', 'review', 'report', 'submitted']):
                                    print(f"    🎯 POTENTIAL REPORT LINK: \"{link_text}\" -> {href[:80]}...")
                                
                                # Check for specific href patterns
                                if 'rev_ms_det_pop' in href:
                                    print(f"    ✅ FOUND rev_ms_det_pop LINK: \"{link_text}\" -> {href[:80]}...")
                    
                    # Also search entire page for report-related links
                    print("\n🔍 SEARCHING ENTIRE PAGE FOR REPORT LINKS:")
                    print("=" * 50)
                    
                    all_links = extractor.driver.find_elements(By.XPATH, "//a")
                    report_links = []
                    
                    for link in all_links:
                        link_text = link.text.strip()
                        href = link.get_attribute('href') or ''
                        
                        if 'rev_ms_det_pop' in href or any(word in link_text.lower() for word in ['view review', 'submitted', 'returned']):
                            report_links.append((link_text, href))
                    
                    if report_links:
                        print(f"Found {len(report_links)} potential report links:")
                        for text, href in report_links:
                            print(f"  - \"{text}\" -> {href[:80]}...")
                    else:
                        print("❌ No report links found on this page")
                    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
    print("\n🏁 Check complete")
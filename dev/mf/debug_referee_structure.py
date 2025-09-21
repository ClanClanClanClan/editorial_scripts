#!/usr/bin/env python3
"""Debug referee structure to see all referee emails and report links."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print("🔍 DEBUGGING REFEREE STRUCTURE")
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
                    
                    # Find ALL referee rows
                    referee_rows = extractor.driver.find_elements(By.XPATH, 
                        "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                    
                    print(f"📊 Found {len(referee_rows)} referee rows\n")
                    
                    for i, row in enumerate(referee_rows):
                        print(f"🧑‍⚖️ REFEREE {i+1}:")
                        print("=" * 30)
                        
                        # Get all cells in the row
                        cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                        print(f"   Cells found: {len(cells)}")
                        
                        if len(cells) >= 4:  # Should have name, affiliation, status, etc.
                            # Cell 1: Name
                            name_cell = cells[1]
                            name_links = name_cell.find_elements(By.XPATH, './/a')
                            
                            referee_name = "Unknown"
                            has_email_link = False
                            
                            print(f"   Name cell links: {len(name_links)}")
                            for j, link in enumerate(name_links):
                                link_text = link.text.strip()
                                href = link.get_attribute('href') or ''
                                onclick = link.get_attribute('onclick') or ''
                                
                                if link_text:
                                    referee_name = link_text
                                    print(f"      Link {j+1}: \"{link_text}\"")
                                
                                if 'mailpopup' in href or 'mailpopup' in onclick:
                                    has_email_link = True
                                    print(f"      ✅ Has email popup link")
                                    
                                    # Test email extraction
                                    email = extractor.get_email_from_popup_safe(link)
                                    if email:
                                        print(f"      📧 EMAIL EXTRACTED: {email}")
                                    else:
                                        print(f"      ❌ EMAIL NOT EXTRACTED")
                            
                            # Status cell (usually last cell) - look for View Review
                            status_cell = cells[-1]  # Last cell is usually status
                            status_text = status_cell.text.strip()
                            print(f"   Status: {status_text}")
                            
                            # Look for View Review link
                            review_links = status_cell.find_elements(By.XPATH, ".//a")
                            view_review_found = False
                            
                            for link in review_links:
                                link_text = link.text.strip()
                                href = link.get_attribute('href') or ''
                                
                                if 'View Review' in link_text or 'rev_ms_det_pop' in href:
                                    view_review_found = True
                                    print(f"   ✅ View Review link found: \"{link_text}\"")
                                    print(f"      Href: {href[:100]}...")
                            
                            if not view_review_found:
                                print(f"   ❌ No View Review link found")
                                # Show all links in status cell
                                print(f"   Status cell links:")
                                for link in review_links:
                                    link_text = link.text.strip()
                                    href = link.get_attribute('href') or ''
                                    print(f"      - \"{link_text}\" -> {href[:50]}...")
                            
                            print(f"   Summary: {referee_name} - Email Link: {'✅' if has_email_link else '❌'} - View Review: {'✅' if view_review_found else '❌'}")
                        
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
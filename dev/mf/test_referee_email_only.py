#!/usr/bin/env python3
"""Test just referee email extraction to debug the issue."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print("🧪 TESTING REFEREE EMAIL EXTRACTION ONLY")
print("=" * 60)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print("✅ Login successful")
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)
        
        # Get categories and limit to 1 manuscript
        categories = extractor.get_manuscript_categories()
        if categories:
            test_category = categories[0]
            test_category['count'] = 1  # Process only 1 manuscript
            print(f"📂 Processing: {test_category['name']} (1 manuscript)")
            
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
                    
                    # Find referee table using ORDER selector
                    referee_rows = extractor.driver.find_elements(By.XPATH, 
                        "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                    
                    print(f"\n📊 Found {len(referee_rows)} referee rows")
                    
                    for i, row in enumerate(referee_rows[:1]):  # Just test first referee
                        print(f"\n🧑‍⚖️ Testing referee {i+1}:")
                        
                        # Get all cells in the row
                        cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                        print(f"   Cells found: {len(cells)}")
                        
                        if len(cells) > 1:
                            # Second cell should have the name
                            name_cell = cells[1]
                            
                            # Find ALL links in name cell
                            all_links = name_cell.find_elements(By.XPATH, './/a')
                            print(f"   Links in name cell: {len(all_links)}")
                            
                            for j, link in enumerate(all_links):
                                link_text = link.text.strip()
                                href = link.get_attribute('href') or ''
                                onclick = link.get_attribute('onclick') or ''
                                
                                print(f"\n   Link {j+1}:")
                                print(f"      Text: \"{link_text}\"")
                                
                                # Check if it's a mailpopup
                                if 'mailpopup' in href or 'mailpopup' in onclick:
                                    print(f"      ✅ THIS IS A MAILPOPUP LINK!")
                                    
                                    # Try the enhanced extraction method
                                    print("      🔧 Testing get_email_from_popup_safe...")
                                    email = extractor.get_email_from_popup_safe(link)
                                    
                                    if email:
                                        print(f"      🎉 SUCCESS! Email extracted: {email}")
                                    else:
                                        print(f"      ❌ FAILED! No email extracted")
                                        
                                        # Try manual debugging
                                        print("      🔍 Trying manual popup inspection...")
                                        original_window = extractor.driver.current_window_handle
                                        
                                        # Click the link
                                        link.click()
                                        time.sleep(3)
                                        
                                        # Check if popup opened
                                        windows = extractor.driver.window_handles
                                        if len(windows) > 1:
                                            print(f"      ✅ Popup opened ({len(windows)} windows)")
                                            extractor.driver.switch_to.window(windows[-1])
                                            
                                            # Check for frames
                                            frames = extractor.driver.find_elements(By.TAG_NAME, "frame")
                                            iframes = extractor.driver.find_elements(By.TAG_NAME, "iframe")
                                            
                                            print(f"      📋 Frames: {len(frames)}, IFrames: {len(iframes)}")
                                            
                                            # Try to get page source
                                            try:
                                                page_source = extractor.driver.page_source
                                                if 'EMAIL_TEMPLATE_TO=' in page_source:
                                                    print("      ✅ EMAIL_TEMPLATE_TO found in source!")
                                                else:
                                                    print("      ❌ EMAIL_TEMPLATE_TO not in source")
                                                    
                                                # Check current URL
                                                current_url = extractor.driver.current_url
                                                print(f"      📍 Popup URL: {current_url[:100]}...")
                                                
                                                if 'EMAIL_TEMPLATE_TO=' in current_url:
                                                    print("      ✅ EMAIL_TEMPLATE_TO in URL!")
                                                    import re
                                                    from urllib.parse import unquote
                                                    match = re.search(r'EMAIL_TEMPLATE_TO=([^&]+)', current_url)
                                                    if match:
                                                        email = unquote(match.group(1))
                                                        print(f"      📧 Email from URL: {email}")
                                            except Exception as e:
                                                print(f"      ❌ Error inspecting popup: {e}")
                                            
                                            # Close popup
                                            extractor.driver.close()
                                            extractor.driver.switch_to.window(original_window)
                                        else:
                                            print(f"      ❌ No popup opened")
                                    
                                    break  # Only test first mailpopup link
                    
                else:
                    print("❌ No manuscript links found")
            else:
                print("❌ Could not click category")
        else:
            print("❌ No categories found")
    else:
        print("❌ Login failed")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
    print("\n🏁 Test complete")
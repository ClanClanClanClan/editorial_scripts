#!/usr/bin/env python3
"""Debug popup structure to understand what's in the frames."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import re
from urllib.parse import unquote

print("🔍 DEBUGGING POPUP STRUCTURE")
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
                    
                    # Find first referee with mailpopup
                    referee_rows = extractor.driver.find_elements(By.XPATH, 
                        "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                    
                    for row in referee_rows[:1]:  # Just first referee
                        cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                        if len(cells) > 1:
                            name_cell = cells[1]
                            all_links = name_cell.find_elements(By.XPATH, './/a')
                            
                            for link in all_links:
                                href = link.get_attribute('href') or ''
                                onclick = link.get_attribute('onclick') or ''
                                
                                if 'mailpopup' in href or 'mailpopup' in onclick:
                                    print("📧 Found mailpopup link, clicking...")
                                    original_window = extractor.driver.current_window_handle
                                    
                                    # Click the link
                                    link.click()
                                    time.sleep(5)  # Give more time for popup to load
                                    
                                    # Switch to popup
                                    windows = extractor.driver.window_handles
                                    if len(windows) > 1:
                                        extractor.driver.switch_to.window(windows[-1])
                                        print("✅ Switched to popup window\n")
                                        
                                        # Get popup info
                                        popup_url = extractor.driver.current_url
                                        print(f"📍 Popup URL: {popup_url[:150]}...")
                                        
                                        # Check for EMAIL_TEMPLATE_TO in URL
                                        if 'EMAIL_TEMPLATE_TO=' in popup_url:
                                            match = re.search(r'EMAIL_TEMPLATE_TO=([^&]+)', popup_url)
                                            if match:
                                                email = unquote(match.group(1))
                                                print(f"✅ EMAIL_TEMPLATE_TO in URL: {email}\n")
                                        else:
                                            print("❌ EMAIL_TEMPLATE_TO not in URL\n")
                                        
                                        # Get page source snippet
                                        page_source = extractor.driver.page_source
                                        print(f"📄 Page source length: {len(page_source)} chars")
                                        print(f"📄 Page source snippet: {page_source[:500]}...\n")
                                        
                                        # Check for frames
                                        frames = extractor.driver.find_elements(By.TAG_NAME, "frame")
                                        framesets = extractor.driver.find_elements(By.TAG_NAME, "frameset")
                                        iframes = extractor.driver.find_elements(By.TAG_NAME, "iframe")
                                        
                                        print(f"🖼️ Framesets: {len(framesets)}")
                                        print(f"🖼️ Frames: {len(frames)}")
                                        print(f"🖼️ IFrames: {len(iframes)}\n")
                                        
                                        # If there are frames, check each one
                                        if frames:
                                            for i, frame in enumerate(frames):
                                                try:
                                                    # Get frame attributes
                                                    frame_name = frame.get_attribute('name')
                                                    frame_src = frame.get_attribute('src')
                                                    print(f"Frame {i}:")
                                                    print(f"  Name: {frame_name}")
                                                    print(f"  Src: {frame_src[:100] if frame_src else 'None'}...")
                                                    
                                                    # Switch to frame
                                                    extractor.driver.switch_to.frame(i)
                                                    
                                                    # Get frame URL and source
                                                    frame_url = extractor.driver.current_url
                                                    frame_source = extractor.driver.page_source
                                                    
                                                    print(f"  Frame URL: {frame_url[:100]}...")
                                                    print(f"  Frame source length: {len(frame_source)} chars")
                                                    
                                                    # Check for EMAIL_TEMPLATE_TO
                                                    if 'EMAIL_TEMPLATE_TO=' in frame_url:
                                                        match = re.search(r'EMAIL_TEMPLATE_TO=([^&]+)', frame_url)
                                                        if match:
                                                            email = unquote(match.group(1))
                                                            print(f"  ✅ EMAIL_TEMPLATE_TO in frame URL: {email}")
                                                    
                                                    if 'EMAIL_TEMPLATE_TO=' in frame_source:
                                                        print(f"  ✅ EMAIL_TEMPLATE_TO found in frame source!")
                                                        # Try to extract it
                                                        match = re.search(r'EMAIL_TEMPLATE_TO=([^&"\'\s]+)', frame_source)
                                                        if match:
                                                            email = unquote(match.group(1))
                                                            print(f"  ✅ Extracted email: {email}")
                                                    
                                                    # Look for any email addresses
                                                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                                    emails = re.findall(email_pattern, frame_source)
                                                    if emails:
                                                        print(f"  📧 Emails found in frame: {emails[:3]}")
                                                    
                                                    # Switch back to popup window
                                                    extractor.driver.switch_to.window(windows[-1])
                                                    
                                                except Exception as e:
                                                    print(f"  ❌ Error checking frame {i}: {e}")
                                                    extractor.driver.switch_to.window(windows[-1])
                                                
                                                print()
                                        
                                        # Close popup and return
                                        extractor.driver.close()
                                        extractor.driver.switch_to.window(original_window)
                                        break
                    
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
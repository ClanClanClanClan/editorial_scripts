#!/usr/bin/env python3
"""Minimal test to extract email from referee popup content."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import re

print('🔍 MINIMAL REFEREE EMAIL CONTENT TEST')
print('=' * 50)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')  
        ae_link.click()
        time.sleep(3)
        
        categories = extractor.get_manuscript_categories()
        category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, categories[0]['name'])
        category_links[0].click()
        time.sleep(3)
        
        manuscript_links = extractor.driver.find_elements(By.XPATH, 
            "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
        manuscript_links[0].click()
        time.sleep(5)
        
        # Get first referee
        referee_rows = extractor.driver.find_elements(By.XPATH, 
            "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
        
        row = referee_rows[0]
        cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
        name_cell = cells[1]
        name_links = name_cell.find_elements(By.XPATH, './/a')
        
        for link in name_links:
            href = link.get_attribute('href') or ''
            if 'mailpopup' in href:
                referee_name = link.text.strip()
                print(f'🧑‍⚖️ Testing referee: {referee_name}')
                
                # Click popup
                original = extractor.driver.current_window_handle
                link.click()
                time.sleep(3)
                
                # Switch to popup  
                popup = [w for w in extractor.driver.window_handles if w != original][0]
                extractor.driver.switch_to.window(popup)
                
                print('📄 POPUP CONTENT ANALYSIS:')
                
                # Get full page source
                page_source = extractor.driver.page_source
                print(f'   Page source length: {len(page_source)}')
                
                # Look for email patterns in content
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found_emails = re.findall(email_pattern, page_source)
                print(f'   📧 Emails found in content: {found_emails}')
                
                # Look for input fields
                inputs = extractor.driver.find_elements(By.TAG_NAME, 'input')
                print(f'   📝 Input fields: {len(inputs)}')
                for i, inp in enumerate(inputs):
                    inp_type = inp.get_attribute('type')
                    inp_name = inp.get_attribute('name') or 'no-name'
                    inp_value = inp.get_attribute('value') or ''
                    print(f'      Input {i+1}: {inp_type} name="{inp_name}" value="{inp_value[:50]}..."')
                    if '@' in inp_value:
                        print(f'         🎉 FOUND EMAIL IN INPUT: {inp_value}')
                
                # Look for textarea fields
                textareas = extractor.driver.find_elements(By.TAG_NAME, 'textarea')
                print(f'   📝 Textarea fields: {len(textareas)}')
                for i, ta in enumerate(textareas):
                    ta_name = ta.get_attribute('name') or 'no-name'
                    ta_value = ta.get_attribute('value') or ta.text or ''
                    print(f'      Textarea {i+1}: name="{ta_name}" value="{ta_value[:50]}..."')
                
                # Check frames if any
                frames = extractor.driver.find_elements(By.TAG_NAME, 'frame')
                if frames:
                    print(f'   🖼️ Frames found: {len(frames)}')
                    for i, frame in enumerate(frames):
                        try:
                            extractor.driver.switch_to.frame(i)
                            frame_source = extractor.driver.page_source
                            frame_emails = re.findall(email_pattern, frame_source)
                            print(f'      Frame {i}: {len(frame_emails)} emails found')
                            if frame_emails:
                                print(f'         📧 Frame emails: {frame_emails}')
                            extractor.driver.switch_to.window(popup)
                        except:
                            print(f'      Frame {i}: Cannot access')
                
                # Close popup
                extractor.driver.close()
                extractor.driver.switch_to.window(original)
                break
                
    else:
        print('❌ Login failed')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
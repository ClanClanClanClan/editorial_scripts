#!/usr/bin/env python3
"""Test extraction of just ONE referee email with timeout protection."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import signal
import sys

def timeout_handler(signum, frame):
    print('\n⏰ TIMEOUT - Test stopped after 90 seconds')
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(90)  # 90 second timeout

print('🧪 TESTING ONE REFEREE EMAIL EXTRACTION')
print('=' * 50)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get first category
        categories = extractor.get_manuscript_categories()
        if categories:
            # Click first category
            category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, categories[0]['name'])
            category_links[0].click()
            time.sleep(3)
            
            # Click first manuscript
            manuscript_links = extractor.driver.find_elements(By.XPATH, 
                "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
            manuscript_links[0].click()
            time.sleep(5)
            
            print('📄 On manuscript page')
            
            # Find FIRST referee ONLY
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            if referee_rows:
                print(f'🧑‍⚖️ Testing first referee only:')
                row = referee_rows[0]
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                
                if len(cells) > 1:
                    name_cell = cells[1]
                    name_links = name_cell.find_elements(By.XPATH, './/a')
                    
                    referee_name = 'Unknown'
                    for link in name_links:
                        link_text = link.text.strip()
                        if link_text and ',' in link_text:
                            referee_name = link_text
                        
                        href = link.get_attribute('href') or ''
                        onclick = link.get_attribute('onclick') or ''
                        
                        if 'mailpopup' in href or 'mailpopup' in onclick:
                            print(f'  Name: {referee_name}')
                            print(f'  📧 Testing email extraction...')
                            
                            try:
                                email = extractor.get_email_from_popup_safe(link)
                                if email:
                                    print(f'  ✅ SUCCESS! Email extracted: {email}')
                                else:
                                    print(f'  ❌ FAILED: No email extracted')
                            except Exception as e:
                                print(f'  ❌ ERROR: {e}')
                            
                            break  # Only test first email link
            else:
                print('❌ No referee rows found')
                
    else:
        print('❌ Login failed')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    signal.alarm(0)  # Cancel timeout
    try:
        extractor.cleanup()
    except:
        pass
    print('\n🏁 Test complete')
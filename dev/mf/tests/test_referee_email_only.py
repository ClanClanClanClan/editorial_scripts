#!/usr/bin/env python3
"""Test ONLY the referee email extraction with timeout protection."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import signal
import sys

def timeout_handler(signum, frame):
    print('\n⏰ TIMEOUT - Stopping test')
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(90)  # 90 second timeout

print('🧪 TESTING REFEREE EMAIL EXTRACTION FIX')
print('=' * 50)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        # Navigate to manuscript page directly
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')  
        ae_link.click()
        time.sleep(3)
        
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
            
            # Test referee emails ONLY
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            print(f'🧑‍⚖️ Testing {len(referee_rows)} referees:')
            referee_emails = []
            
            for i, row in enumerate(referee_rows):
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                if len(cells) > 1:
                    name_cell = cells[1]
                    name_links = name_cell.find_elements(By.XPATH, './/a')
                    
                    referee_name = 'Unknown'
                    for link in name_links:
                        if link.text.strip():
                            referee_name = link.text.strip()
                            
                        href = link.get_attribute('href') or ''
                        onclick = link.get_attribute('onclick') or ''
                        
                        # CRITICAL TEST: Check if history_popup is now detected
                        if 'mailpopup' in href or 'mailpopup' in onclick:
                            print(f'  {i+1}. {referee_name}: Found MAILPOPUP')
                            break
                        elif 'history_popup' in href or 'history_popup' in onclick:
                            print(f'  {i+1}. {referee_name}: Found HISTORY_POPUP (THIS IS THE FIX!)')
                            
                            try:
                                email = extractor.get_email_from_popup_safe(link)
                                if email:
                                    print(f'     ✅ EMAIL: {email}')
                                    referee_emails.append(email)
                                else:
                                    print(f'     ❌ NO EMAIL')
                            except Exception as e:
                                print(f'     ❌ ERROR: {e}')
                            break
            
            print(f'\n📊 RESULTS:')
            print(f'Total referee emails extracted: {len(referee_emails)}')
            for i, email in enumerate(referee_emails):
                print(f'  {i+1}. {email}')
                
            if len(referee_emails) >= 2:
                print('\n🎉 SUCCESS: History_popup email extraction working!')
            elif len(referee_emails) > 0:
                print('\n✅ PARTIAL: Some referee emails extracted')
            else:
                print('\n❌ FAILED: No referee emails extracted')
                
    else:
        print('❌ Login failed')
        
except Exception as e:
    print(f'❌ Error: {e}')
finally:
    signal.alarm(0)
    try:
        extractor.cleanup()
    except:
        pass
    print('\n🏁 Test complete')
#!/usr/bin/env python3
"""Simple test to see what happens when we click a referee mailpopup link."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print('🧪 SIMPLE REFEREE MAILPOPUP CLICK TEST')
print('=' * 50)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')  
        ae_link.click()
        time.sleep(3)
        
        categories = extractor.get_manuscript_categories()
        if categories:
            category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, categories[0]['name'])
            category_links[0].click()
            time.sleep(3)
            
            manuscript_links = extractor.driver.find_elements(By.XPATH, 
                "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
            manuscript_links[0].click()
            time.sleep(5)
            
            # Find first referee row
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            if referee_rows:
                row = referee_rows[0]
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                if len(cells) > 1:
                    name_cell = cells[1]
                    name_links = name_cell.find_elements(By.XPATH, './/a')
                    
                    for link in name_links:
                        href = link.get_attribute('href') or ''
                        onclick = link.get_attribute('onclick') or ''
                        
                        if 'mailpopup' in href or 'mailpopup' in onclick:
                            referee_name = link.text.strip()
                            print(f'🧑‍⚖️ Testing referee: {referee_name}')
                            print(f'   Href: {href[:100]}...')
                            print(f'   OnClick: {onclick[:100]}...')
                            
                            # MANUAL POPUP TEST
                            print('   🔧 Clicking popup manually...')
                            try:
                                # Store initial window count
                                initial_windows = len(extractor.driver.window_handles)
                                print(f'   Initial windows: {initial_windows}')
                                
                                # Click the link
                                link.click()
                                time.sleep(3)
                                
                                # Check window count
                                after_windows = len(extractor.driver.window_handles)
                                print(f'   After click windows: {after_windows}')
                                
                                if after_windows > initial_windows:
                                    print('   ✅ Popup opened!')
                                    # Switch to popup
                                    original = extractor.driver.current_window_handle
                                    popup = [w for w in extractor.driver.window_handles if w != original][0]
                                    extractor.driver.switch_to.window(popup)
                                    
                                    # Get popup info
                                    popup_url = extractor.driver.current_url
                                    popup_title = extractor.driver.title
                                    print(f'   📄 Popup URL: {popup_url[:100]}...')
                                    print(f'   📄 Popup Title: {popup_title}')
                                    
                                    # Look for email in URL
                                    if 'EMAIL_TO=' in popup_url:
                                        import re
                                        from urllib.parse import unquote
                                        match = re.search(r'EMAIL_TO=([^&"\'\s]+)', popup_url)
                                        if match:
                                            email = unquote(match.group(1))
                                            print(f'   📧 FOUND EMAIL IN URL: {email}')
                                    
                                    # Close popup
                                    extractor.driver.close()
                                    extractor.driver.switch_to.window(original)
                                    print('   🔙 Returned to main window')
                                else:
                                    print('   ❌ No popup opened')
                                    
                            except Exception as e:
                                print(f'   ❌ Click failed: {e}')
                            
                            break  # Only test first referee
                
    else:
        print('❌ Login failed')
        
except Exception as e:
    print(f'❌ Error: {e}')
finally:
    try:
        extractor.cleanup()
    except:
        pass
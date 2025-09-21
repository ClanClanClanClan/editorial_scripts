from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

print('🔍 EXAMINING REFEREE POPUP STRUCTURE')
extractor = ComprehensiveMFExtractor()

try:
    if extractor.login():
        print('✅ Login successful')
        
        # Navigate to first manuscript
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
            
            # Find first referee with mailpopup
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            if referee_rows:
                for row in referee_rows:
                    cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                    if len(cells) > 1:
                        name_cell = cells[1]
                        links = name_cell.find_elements(By.XPATH, ".//a")
                        
                        for link in links:
                            href = link.get_attribute('href') or ''
                            if 'mailpopup' in href:
                                print(f'\\n📧 Testing popup for: {link.text.strip()}')
                                
                                original_window = extractor.driver.current_window_handle
                                link.click()
                                time.sleep(2)
                                
                                all_windows = extractor.driver.window_handles
                                if len(all_windows) > 1:
                                    popup_window = [w for w in all_windows if w != original_window][-1]
                                    extractor.driver.switch_to.window(popup_window)
                                    
                                    print('\\n📋 POPUP FIELDS:')
                                    
                                    # Check all input fields
                                    inputs = extractor.driver.find_elements(By.TAG_NAME, 'input')
                                    for inp in inputs:
                                        inp_name = inp.get_attribute('name') or 'unnamed'
                                        inp_value = inp.get_attribute('value') or ''
                                        inp_type = inp.get_attribute('type') or 'text'
                                        if inp_value and inp_type != 'hidden':
                                            print(f'   Input[{inp_name}]: "{inp_value[:50]}..."')
                                    
                                    # Check textareas
                                    textareas = extractor.driver.find_elements(By.TAG_NAME, 'textarea')
                                    for ta in textareas:
                                        ta_name = ta.get_attribute('name') or 'unnamed'
                                        ta_value = ta.get_attribute('value') or ta.text or ''
                                        if ta_value:
                                            print(f'   Textarea[{ta_name}]: "{ta_value[:50]}..."')
                                    
                                    # Check for email patterns in page text
                                    page_text = extractor.driver.find_element(By.TAG_NAME, 'body').text
                                    import re
                                    emails = re.findall(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', page_text)
                                    if emails:
                                        print(f'\\n   📧 EMAILS FOUND IN PAGE: {emails}')
                                    
                                    # Close popup
                                    extractor.driver.close()
                                    extractor.driver.switch_to.window(original_window)
                                    
                                    # Just test first referee
                                    break
                        
                        # Just test first row with mailpopup
                        if any('mailpopup' in (l.get_attribute('href') or '') for l in links):
                            break
                            
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass

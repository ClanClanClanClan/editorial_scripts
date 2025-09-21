from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

print('🔍 TESTING REFEREE EMAIL EXTRACTION BY CLICKING')
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
            
            # Find first referee row
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            if referee_rows:
                print(f'\n📊 Testing first referee row')
                row = referee_rows[0]
                
                # Get name cell
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                if len(cells) > 1:
                    name_cell = cells[1]
                    
                    # Find mailpopup link
                    links = name_cell.find_elements(By.XPATH, ".//a")
                    mailpopup_link = None
                    
                    for link in links:
                        href = link.get_attribute('href') or ''
                        if 'mailpopup' in href:
                            mailpopup_link = link
                            print(f'✅ Found mailpopup link!')
                            print(f'   Text: "{link.text.strip()}"')
                            print(f'   Href: {href[:100]}...')
                            break
                    
                    if mailpopup_link:
                        # Try clicking with timeout
                        original_window = extractor.driver.current_window_handle
                        
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(5)  # 5 second timeout
                        
                        try:
                            print('\n🖱️ Clicking mailpopup link...')
                            mailpopup_link.click()
                            time.sleep(2)
                            
                            # Check for popup window
                            all_windows = extractor.driver.window_handles
                            if len(all_windows) > 1:
                                popup_window = [w for w in all_windows if w != original_window][-1]
                                extractor.driver.switch_to.window(popup_window)
                                
                                print('✅ Popup opened!')
                                
                                # Look for email input
                                email_inputs = extractor.driver.find_elements(By.NAME, 'EMAIL_TEMPLATE_TO')
                                if email_inputs:
                                    email_value = email_inputs[0].get_attribute('value')
                                    print(f'📧 FOUND EMAIL: {email_value}')
                                else:
                                    print('❌ No EMAIL_TEMPLATE_TO field found')
                                
                                # Close popup
                                extractor.driver.close()
                                extractor.driver.switch_to.window(original_window)
                            else:
                                print('❌ No popup window opened')
                                
                        except TimeoutError:
                            print('⏰ Clicking timed out')
                        finally:
                            signal.alarm(0)
                            # Ensure we're back on main window
                            try:
                                extractor.driver.switch_to.window(original_window)
                            except:
                                pass
                    else:
                        print('❌ No mailpopup link found in referee row')
                        
except Exception as e:
    print(f'❌ Error: {e}')
finally:
    try:
        extractor.cleanup()
    except:
        pass

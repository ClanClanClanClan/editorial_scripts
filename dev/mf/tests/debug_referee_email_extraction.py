#!/usr/bin/env python3
"""Debug exactly why referee email extraction is failing."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import re
from urllib.parse import unquote

print('🔍 DEBUGGING REFEREE EMAIL EXTRACTION FAILURE')
print('=' * 60)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get first category and click it
        categories = extractor.get_manuscript_categories()
        if categories:
            first_category = categories[0]
            print(f'📂 Testing category: {first_category["name"]}')
            
            # Click category
            category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, first_category['name'])
            category_links[0].click()
            time.sleep(3)
            
            # Click first manuscript
            manuscript_links = extractor.driver.find_elements(By.XPATH, 
                "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
            manuscript_links[0].click()
            time.sleep(5)
            
            print('\n🧑‍⚖️ DEBUGGING REFEREE EMAIL EXTRACTION:')
            print('=' * 50)
            
            # Find referee rows using ORDER selector
            referee_rows = extractor.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            print(f'Found {len(referee_rows)} referee rows')
            
            for i, row in enumerate(referee_rows[:2]):  # Debug first 2 referees
                print(f'\n🔍 REFEREE {i+1} DEBUG:')
                print('-' * 30)
                
                # Get name cell
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                if len(cells) > 1:
                    name_cell = cells[1]
                    print(f'Name cell text: {name_cell.text.strip()}')
                    
                    # Find ALL links in name cell
                    all_links = name_cell.find_elements(By.XPATH, './/a')
                    print(f'Links found in name cell: {len(all_links)}')
                    
                    for j, link in enumerate(all_links):
                        link_text = link.text.strip()
                        href = link.get_attribute('href') or ''
                        onclick = link.get_attribute('onclick') or ''
                        
                        print(f'\n  Link {j+1}:')
                        print(f'    Text: "{link_text}"')
                        print(f'    Href: {href[:100]}...' if href else '    Href: None')
                        print(f'    OnClick: {onclick[:100]}...' if onclick else '    OnClick: None')
                        
                        # Check if it's a mailpopup
                        if 'mailpopup' in href or 'mailpopup' in onclick:
                            print(f'    ✅ FOUND MAILPOPUP LINK!')
                            
                            # Try manual email extraction from URL
                            combined = href + ' ' + onclick
                            print(f'    🔍 Combined URL/onClick: {combined[:200]}...')
                            
                            # Look for EMAIL_TO parameter
                            email_match = re.search(r'EMAIL_TO=([^&\'"]+)', combined)
                            if email_match:
                                email = unquote(email_match.group(1))
                                print(f'    📧 REGEX EXTRACTED EMAIL: {email}')
                            else:
                                print(f'    ❌ NO EMAIL_TO FOUND IN URL')
                            
                            # Test the actual popup method
                            print(f'    🧪 Testing get_email_from_popup_safe...')
                            try:
                                extracted_email = extractor.get_email_from_popup_safe(link)
                                print(f'    📧 METHOD RESULT: "{extracted_email}"')
                                if not extracted_email:
                                    print(f'    ❌ METHOD RETURNED EMPTY STRING')
                            except Exception as e:
                                print(f'    ❌ METHOD ERROR: {e}')
                            
                            break  # Only test first email link per referee
                        else:
                            print(f'    ℹ️ Not a mailpopup link')
            
            print('\n🎯 DIAGNOSIS COMPLETE')
            
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
#!/usr/bin/env python3

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

def debug_referee_structure():
    """Debug the actual referee table structure on MF manuscript pages."""
    print('🔍 DEBUGGING MF REFEREE TABLE STRUCTURE')
    print('=' * 60)
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        if extractor.login():
            print('✅ Login successful')
            
            # Navigate to AE Center
            ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
            ae_link.click()
            time.sleep(3)
            
            # Get first category and navigate to first manuscript  
            categories = extractor.get_manuscript_categories()
            if categories:
                test_category = categories[0]
                print(f'\n📂 Using category: {test_category["name"]} ({test_category["count"]} manuscripts)')
                
                # Navigate to category
                category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, test_category['name'])
                if category_links:
                    category_links[0].click()
                    time.sleep(3)
                    
                    # Find and click first manuscript
                    manuscript_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href, 'REVIEWER_MANUSCRIPTMANAGEMENTDETAILS')]")
                        
                    if manuscript_links:
                        manuscript_id = manuscript_links[0].text.strip()
                        print(f'\n📄 Opening manuscript: {manuscript_id}')
                        manuscript_links[0].click()
                        time.sleep(5)
                        
                        # ANALYZE PAGE STRUCTURE
                        print('\n' + '=' * 60)
                        print('🔍 ANALYZING PAGE STRUCTURE')
                        print('=' * 60)
                        
                        # 1. Find ALL mailpopup links
                        all_mailpopup_links = extractor.driver.find_elements(By.XPATH, "//a[contains(@href, 'mailpopup')]")
                        print(f'\n📧 FOUND {len(all_mailpopup_links)} MAILPOPUP LINKS:')
                        print('-' * 40)
                        
                        for i, link in enumerate(all_mailpopup_links):
                            try:
                                link_text = link.text.strip()
                                link_href = link.get_attribute('href')
                                
                                # Get row context
                                try:
                                    row = link.find_element(By.XPATH, './ancestor::tr[1]')
                                    row_text = ' | '.join([cell.text.strip() for cell in row.find_elements(By.TAG_NAME, 'td')])[:150]
                                except:
                                    row_text = "Could not find row"
                                
                                print(f'   {i+1}. NAME: "{link_text}"')
                                print(f'      HREF: {link_href}')
                                print(f'      ROW:  {row_text}')
                                print()
                            except Exception as e:
                                print(f'   {i+1}. Error analyzing link: {e}')
                        
                        # 2. Check current XPath selector being used
                        print('\n🎯 TESTING CURRENT XPATH SELECTOR:')
                        print('-' * 40)
                        current_selector = "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]"
                        current_matches = extractor.driver.find_elements(By.XPATH, current_selector)
                        
                        print(f'Current selector: {current_selector}')
                        print(f'Matches found: {len(current_matches)}')
                        
                        for i, row in enumerate(current_matches):
                            try:
                                mailpopup_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                                link_text = mailpopup_link.text.strip()
                                print(f'   {i+1}. "{link_text}"')
                            except:
                                print(f'   {i+1}. Could not extract name from row')
                        
                        # 3. Test simpler selector
                        print('\n🧪 TESTING SIMPLER SELECTOR:')
                        print('-' * 40)
                        simple_selector = "//tr[.//a[contains(@href, 'mailpopup')]]"
                        simple_matches = extractor.driver.find_elements(By.XPATH, simple_selector)
                        
                        print(f'Simple selector: {simple_selector}')
                        print(f'Matches found: {len(simple_matches)}')
                        
                        for i, row in enumerate(simple_matches):
                            try:
                                mailpopup_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                                link_text = mailpopup_link.text.strip()
                                
                                # Get full row text for context
                                row_cells = row.find_elements(By.TAG_NAME, 'td')
                                row_data = [cell.text.strip() for cell in row_cells if cell.text.strip()]
                                
                                print(f'   {i+1}. NAME: "{link_text}"')
                                print(f'       DATA: {" | ".join(row_data[:5])}')  # First 5 cells
                                print()
                            except Exception as e:
                                print(f'   {i+1}. Error extracting from row: {e}')
                        
                        # 4. Save page for manual inspection
                        with open('debug_mf_referee_structure.html', 'w', encoding='utf-8') as f:
                            f.write(extractor.driver.page_source)
                        print('💾 Full page saved to debug_mf_referee_structure.html')
                        
                        # 5. Check if we can identify the correct referee section
                        print('\n🎯 TRYING TO IDENTIFY ACTUAL REFEREES:')
                        print('-' * 40)
                        
                        # Look for section headers that might identify referee tables
                        section_headers = extractor.driver.find_elements(By.XPATH, "//td[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")
                        for header in section_headers:
                            header_text = header.text.strip()
                            print(f'Found section header: "{header_text}"')
                        
                        print('\n✅ DEBUG COMPLETE')
                        
                    else:
                        print('❌ No manuscript links found')
                else:
                    print('❌ Could not navigate to category')
            else:
                print('❌ No categories found')
        else:
            print('❌ Login failed')
            
    except Exception as e:
        print(f'❌ Debug failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        try:
            extractor.cleanup()
        except:
            pass

if __name__ == "__main__":
    debug_referee_structure()
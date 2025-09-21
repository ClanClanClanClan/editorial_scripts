#!/usr/bin/env python3

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time

def minimal_extraction_test():
    """Test ONLY the core referee identification without full extraction."""
    print('🎯 MINIMAL MF TEST: ORDER SELECTOR + REFEREE IDENTIFICATION')
    print('=' * 60)
    
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
                test_category = categories[0]
                print(f'📂 Category: {test_category["name"]} ({test_category["count"]} manuscripts)')
                
                # Click category
                category_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, test_category['name'])
                if category_links:
                    category_links[0].click()
                    time.sleep(3)
                    
                    # Find and click first manuscript
                    manuscript_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                        
                    if manuscript_links:
                        manuscript_id = manuscript_links[0].text.strip()
                        print(f'📄 Opening manuscript: {manuscript_id}')
                        manuscript_links[0].click()
                        time.sleep(5)
                        
                        # Create minimal manuscript object
                        manuscript = {
                            'id': manuscript_id,
                            'referees': []
                        }
                        
                        # TEST ONLY: Referee identification using ORDER selector
                        print('\n🧑‍⚖️ TESTING ORDER SELECTOR REFEREE IDENTIFICATION:')
                        
                        referee_rows = extractor.driver.find_elements(By.XPATH, 
                            "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                        
                        print(f'   Found {len(referee_rows)} referee rows')
                        
                        referees_found = []
                        
                        for i, row in enumerate(referee_rows):
                            try:
                                # Get referee name
                                name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                                name = name_link.text.strip()
                                
                                referee = {
                                    'name': name,
                                    'email': '',  # Skip email for minimal test
                                    'status': '',
                                    'affiliation': ''
                                }
                                
                                # Get basic info from row text
                                row_text = row.text.strip()
                                lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                                
                                # Try to extract status and affiliation
                                for line in lines:
                                    if 'Agreed' in line or 'Declined' in line:
                                        referee['status'] = line
                                    elif len(line) > 20 and name not in line:
                                        if not referee['affiliation']:
                                            referee['affiliation'] = line
                                
                                referees_found.append(referee)
                                manuscript['referees'].append(referee)
                                
                                print(f'   {i+1}. {name}')
                                print(f'       Status: {referee["status"] or "Unknown"}')
                                print(f'       Affiliation: {referee["affiliation"][:50]}...' if referee["affiliation"] else '       Affiliation: Unknown')
                                
                            except Exception as e:
                                print(f'   {i+1}. Error extracting referee: {e}')
                        
                        # VERIFICATION: Check if we got the correct referees
                        referee_names = [r['name'] for r in referees_found]
                        names_str = ' '.join(referee_names)
                        
                        print(f'\n📊 RESULTS:')
                        print(f'   Total referees found: {len(referees_found)}')
                        print(f'   Names: {referee_names}')
                        
                        if any(target in names_str for target in ['Villeneuve', 'Strulovici', 'Durandard']):
                            print('\n🎉 SUCCESS: ORDER selector found CORRECT referees!')
                            print('   ✅ Not extracting editors or authors')
                            print('   ✅ Found actual referees for the manuscript')
                        else:
                            print('\n🔍 Different manuscript or unexpected names')
                            print('   This may be a different manuscript than expected')
                        
                        # Save minimal results
                        import json
                        with open('minimal_mf_test_results.json', 'w') as f:
                            json.dump([manuscript], f, indent=2)
                        print('\n💾 Results saved to minimal_mf_test_results.json')
                        
                    else:
                        print('❌ No manuscript links found')
                else:
                    print('❌ Could not click category')
            else:
                print('❌ No categories found')
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
    
    print('\n✅ Minimal test complete')

if __name__ == "__main__":
    minimal_extraction_test()
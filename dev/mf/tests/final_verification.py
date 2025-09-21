#!/usr/bin/env python3
"""Final verification that referee email extraction now works."""

from mf_extractor import ComprehensiveMFExtractor
import json
from datetime import datetime

print('🚀 FINAL VERIFICATION: REFEREE EMAIL EXTRACTION')
print('=' * 60)

extractor = ComprehensiveMFExtractor()
try:
    # Login and test with first category limited to 1 manuscript
    if extractor.login():
        from selenium.webdriver.common.by import By
        import time
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get first category and limit to 1 manuscript
        categories = extractor.get_manuscript_categories()
        if categories:
            first_category = categories[0]
            first_category['count'] = 1  # Limit to 1 manuscript
            print(f'📂 Testing with: {first_category["name"]} (1 manuscript)')
            
            # Process the category
            extractor.process_category(first_category)
    else:
        print('❌ Login failed')
        extractor.cleanup()
        exit(1)
    
    # Check results
    if extractor.manuscripts:
        ms = extractor.manuscripts[0]
        print(f'\n📊 RESULTS FOR {ms.get("id", "UNKNOWN")}:')
        
        # Check referee emails
        referees = ms.get('referees', [])
        emails_found = sum(1 for r in referees if r.get('email', ''))
        
        print(f'🧑‍⚖️ Referees: {len(referees)} total, {emails_found} with emails')
        print(f'📧 Emails extracted: {emails_found}/{len(referees)} ({100*emails_found/len(referees) if referees else 0:.0f}%)')
        
        for r in referees:
            name = r.get('name', 'Unknown')
            email = r.get('email', '')
            status = '✅' if email else '❌'
            print(f'  {status} {name}: {email or "NO EMAIL"}')
            
        if emails_found > 0:
            print(f'\n🎉 SUCCESS! Frame-based email extraction is working!')
            print(f'📧 Extracted {emails_found} referee emails successfully')
        else:
            print(f'\n⚠️ Still no emails extracted')
            
        # Save results
        import json
        with open('final_verification_results.json', 'w') as f:
            json.dump([ms], f, indent=2)
        print(f'\n💾 Results saved to final_verification_results.json')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
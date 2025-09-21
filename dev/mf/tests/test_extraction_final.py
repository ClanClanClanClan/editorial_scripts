#!/usr/bin/env python3
"""Test if referee email extraction works with the fix."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import json
from datetime import datetime

print('🧪 TESTING IF REFEREE EMAIL EXTRACTION FIX WORKS')
print('=' * 60)
print(f'Test started at: {datetime.now().strftime("%H:%M:%S")}')

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print('✅ Login successful')
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get all categories
        categories = extractor.get_manuscript_categories()
        print(f'📂 Found {len(categories)} categories')
        
        # Process all categories to get all manuscripts
        for cat in categories:
            if cat['count'] > 0:
                print(f'\n📂 Processing: {cat["name"]} ({cat["count"]} manuscripts)')
                extractor.process_category(cat)
        
        # Check results
        if extractor.manuscripts:
            print(f'\n📊 EXTRACTION RESULTS:')
            print('=' * 60)
            print(f'Total manuscripts extracted: {len(extractor.manuscripts)}')
            
            total_referees = 0
            total_referee_emails = 0
            total_authors = 0
            total_author_emails = 0
            
            for i, ms in enumerate(extractor.manuscripts):
                manuscript_id = ms.get('id', 'UNKNOWN')
                
                # Check referee emails
                referees = ms.get('referees', [])
                referee_emails = sum(1 for r in referees if r.get('email', ''))
                
                total_referees += len(referees)
                total_referee_emails += referee_emails
                
                # Check author emails
                authors = ms.get('authors', [])
                author_emails = sum(1 for a in authors if a.get('email', ''))
                
                total_authors += len(authors)
                total_author_emails += author_emails
                
                print(f'\nManuscript {i+1}: {manuscript_id}')
                print(f'  🧑‍⚖️ Referees: {len(referees)} total, {referee_emails} with emails')
                print(f'  ✍️ Authors: {len(authors)} total, {author_emails} with emails')
                
                # Show referee details
                for j, r in enumerate(referees):
                    name = r.get('name', 'Unknown')
                    email = r.get('email', '')
                    status = '✅' if email else '❌'
                    print(f'    Referee {j+1}: {status} {name}: {email or "NO EMAIL"}')
            
            # Overall summary
            print(f'\n📊 OVERALL SUMMARY:')
            print('=' * 60)
            print(f'📄 Total manuscripts: {len(extractor.manuscripts)}')
            print(f'🧑‍⚖️ Total referees: {total_referees}')
            print(f'📧 Referee emails extracted: {total_referee_emails}/{total_referees} ({100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%)')
            print(f'✍️ Total authors: {total_authors}')
            print(f'📧 Author emails extracted: {total_author_emails}/{total_authors} ({100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%)')
            print(f'📧 TOTAL EMAILS EXTRACTED: {total_referee_emails + total_author_emails}')
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'test_results_{timestamp}.json'
            with open(filename, 'w') as f:
                json.dump(extractor.manuscripts, f, indent=2, default=str)
            print(f'\n💾 Results saved to: {filename}')
            
            # Final verdict
            if total_referee_emails > 0:
                print('\n🎉 SUCCESS: REFEREE EMAIL EXTRACTION IS WORKING!')
                print(f'✅ Successfully extracted {total_referee_emails} referee emails')
            else:
                print('\n❌ FAILURE: NO REFEREE EMAILS EXTRACTED')
                print('The fix did not work as expected')
                
        else:
            print('❌ No manuscripts extracted')
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
    print(f'\nTest completed at: {datetime.now().strftime("%H:%M:%S")}')
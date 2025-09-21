#!/usr/bin/env python3
"""Live verification of all extracted details - no trust, just facts."""

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import json
from datetime import datetime

print('🔍 LIVE VERIFICATION: SHOWING ACTUAL EXTRACTED DETAILS')
print('=' * 70)
print('This will show exactly what gets extracted, step by step')
print('No claims, just raw data as it happens...')
print()

extractor = ComprehensiveMFExtractor()
try:
    # Login
    print('🔐 STEP 1: Logging in...')
    if not extractor.login():
        print('❌ LOGIN FAILED')
        exit(1)
    print('✅ Login successful')
    
    # Navigate
    print('\n📍 STEP 2: Navigating to Associate Editor Center...')
    ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
    ae_link.click()
    time.sleep(3)
    print('✅ Navigation complete')
    
    # Get categories
    print('\n📂 STEP 3: Finding manuscript categories...')
    categories = extractor.get_manuscript_categories()
    print(f'Found categories:')
    for cat in categories:
        print(f'  - {cat["name"]}: {cat["count"]} manuscripts')
    
    all_extracted = []
    
    # Process each category
    for cat_idx, category in enumerate(categories):
        if category['count'] == 0:
            continue
            
        print(f'\n🔍 STEP 4.{cat_idx+1}: Processing category "{category["name"]}"')
        print(f'Expected manuscripts: {category["count"]}')
        
        # Process this category
        extractor.process_category(category)
        
        # Show what was actually extracted
        new_manuscripts = [ms for ms in extractor.manuscripts if ms not in all_extracted]
        all_extracted.extend(new_manuscripts)
        
        print(f'✅ Extracted {len(new_manuscripts)} manuscripts from this category')
    
    # Show detailed results
    print(f'\n📊 DETAILED EXTRACTION RESULTS:')
    print(f'Total manuscripts extracted: {len(extractor.manuscripts)}')
    print('=' * 60)
    
    for i, ms in enumerate(extractor.manuscripts):
        manuscript_id = ms.get('id', 'NO_ID')
        print(f'\n📄 MANUSCRIPT {i+1}: {manuscript_id}')
        print('-' * 50)
        
        # Basic info
        print(f'Title: {ms.get("title", "N/A")}')
        print(f'Status: {ms.get("status", "N/A")}')
        print(f'Submission Date: {ms.get("submission_date", "N/A")}')
        
        # Referee details with emails
        referees = ms.get('referees', [])
        print(f'\nReferees ({len(referees)} found):')
        referee_emails_found = 0
        
        for j, r in enumerate(referees):
            name = r.get('name', 'No Name')
            email = r.get('email', '')
            affiliation = r.get('affiliation', 'No Affiliation')
            status = r.get('status', 'No Status')
            
            if email:
                referee_emails_found += 1
                
            print(f'  Referee {j+1}:')
            print(f'    Name: {name}')
            print(f'    Email: {email if email else "NOT EXTRACTED"}')
            print(f'    Affiliation: {affiliation}')
            print(f'    Status: {status}')
        
        print(f'  >>> Referee email success: {referee_emails_found}/{len(referees)}')
        
        # Author details with emails
        authors = ms.get('authors', [])
        print(f'\nAuthors ({len(authors)} found):')
        author_emails_found = 0
        
        for j, a in enumerate(authors):
            name = a.get('name', 'No Name')
            email = a.get('email', '')
            institution = a.get('institution', 'No Institution')
            
            if email:
                author_emails_found += 1
                
            print(f'  Author {j+1}:')
            print(f'    Name: {name}')
            print(f'    Email: {email if email else "NOT EXTRACTED"}')
            print(f'    Institution: {institution}')
        
        print(f'  >>> Author email success: {author_emails_found}/{len(authors)}')
        
        # Other details
        keywords = ms.get('keywords', [])
        if keywords:
            print(f'\nKeywords: {keywords}')
        
        documents = ms.get('documents', {})
        if documents:
            print(f'Documents: {list(documents.keys())}')
    
    # Final summary
    total_referees = sum(len(ms.get('referees', [])) for ms in extractor.manuscripts)
    total_referee_emails = sum(sum(1 for r in ms.get('referees', []) if r.get('email')) for ms in extractor.manuscripts)
    total_authors = sum(len(ms.get('authors', [])) for ms in extractor.manuscripts)
    total_author_emails = sum(sum(1 for a in ms.get('authors', []) if a.get('email')) for ms in extractor.manuscripts)
    
    print('\n' + '=' * 60)
    print('FINAL VERIFICATION SUMMARY:')
    print('=' * 60)
    print(f'Manuscripts processed: {len(extractor.manuscripts)}')
    print(f'Total referees found: {total_referees}')
    print(f'Referee emails extracted: {total_referee_emails}')
    print(f'Referee email success rate: {100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%')
    print(f'Total authors found: {total_authors}')
    print(f'Author emails extracted: {total_author_emails}')
    print(f'Author email success rate: {100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%')
    print(f'Total emails extracted: {total_referee_emails + total_author_emails}')
    
    # Save the results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'live_verification_{timestamp}.json'
    with open(filename, 'w') as f:
        json.dump(extractor.manuscripts, f, indent=2, default=str)
    print(f'\n💾 Raw data saved to: {filename}')
    
    if total_referee_emails + total_author_emails > 0:
        print('\n🎉 VERIFICATION: Email extraction is working!')
    else:
        print('\n❌ VERIFICATION: No emails extracted')

except Exception as e:
    print(f'\n❌ ERROR during verification: {e}')
    import traceback
    traceback.print_exc()

finally:
    try:
        extractor.cleanup()
    except:
        pass
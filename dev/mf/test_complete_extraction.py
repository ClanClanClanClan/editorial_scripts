#!/usr/bin/env python3
"""Test complete MF extraction with all fixes for email and report extraction."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By
import time
import json

print("🚀 TESTING COMPLETE MF EXTRACTION WITH ALL FIXES")
print("=" * 60)

extractor = ComprehensiveMFExtractor()
try:
    if extractor.login():
        print("✅ Login successful")
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)
        
        # Get categories and limit to 1 manuscript
        categories = extractor.get_manuscript_categories()
        if categories:
            test_category = categories[0]
            test_category['count'] = 1  # Process only 1 manuscript
            print(f"📂 Processing: {test_category['name']} (1 manuscript)")
            
            # Process the category
            extractor.process_category(test_category)
            
            if extractor.manuscripts:
                ms = extractor.manuscripts[0]
                
                print(f"\n📊 RESULTS FOR {ms.get('id', 'UNKNOWN')}:")
                print("=" * 50)
                
                # Check referee extraction and emails
                referees = ms.get('referees', [])
                referee_emails = sum(1 for r in referees if r.get('email', ''))
                
                print(f"\n🧑‍⚖️ REFEREES: {len(referees)} total")
                for i, r in enumerate(referees):
                    name = r.get('name', 'Unknown')
                    email = r.get('email', '')
                    status = '✅' if email else '❌'
                    print(f"  {i+1}. {status} {name}: {email or 'NO EMAIL'}")
                    
                    # Check if report was extracted
                    if r.get('report'):
                        report = r['report']
                        if report.get('recommendation'):
                            print(f"      📄 Report: {report['recommendation']}")
                        if report.get('pdf_downloaded'):
                            print(f"      📎 PDF downloaded: {report.get('pdf_path', 'YES')}")
                
                # Check author extraction and emails
                authors = ms.get('authors', [])
                author_emails = sum(1 for a in authors if a.get('email', ''))
                
                print(f"\n✍️ AUTHORS: {len(authors)} total")
                for i, a in enumerate(authors):
                    name = a.get('name', 'Unknown')
                    email = a.get('email', '')
                    institution = a.get('institution', 'Unknown')
                    status = '✅' if email else '❌'
                    print(f"  {i+1}. {status} {name} ({institution}): {email or 'NO EMAIL'}")
                
                # Summary
                print(f"\n📊 EXTRACTION SUMMARY:")
                print(f"  ✅ Referee identification: {len(referees)} referees found")
                print(f"  {'✅' if referee_emails > 0 else '❌'} Referee emails: {referee_emails}/{len(referees)} extracted")
                print(f"  {'✅' if len(authors) > 0 else '❌'} Author identification: {len(authors)} authors found")
                print(f"  {'✅' if author_emails > 0 else '❌'} Author emails: {author_emails}/{len(authors)} extracted")
                
                # Check report extraction
                reports_extracted = sum(1 for r in referees if r.get('report'))
                print(f"  {'✅' if reports_extracted > 0 else '❌'} Reports: {reports_extracted}/{len(referees)} extracted")
                
                # Save results
                output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, 'test_complete_extraction.json')
                with open(output_file, 'w') as f:
                    json.dump([ms], f, indent=2)
                print(f"\n💾 Results saved to {output_file}")
                
                # Final assessment
                if referee_emails > 0 and author_emails > 0:
                    print("\n🎉 SUCCESS! ALL DATA EXTRACTION WORKING!")
                elif referee_emails > 0 or author_emails > 0:
                    print("\n⚠️ PARTIAL SUCCESS: Some emails extracted")
                else:
                    print("\n❌ EMAIL EXTRACTION STILL NOT WORKING")
                    
            else:
                print("❌ No manuscripts extracted")
        else:
            print("❌ No categories found")
    else:
        print("❌ Login failed")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass
    print("\n🏁 Test complete")
#!/usr/bin/env python3
"""Quick test to verify MF referee email extraction is working."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'production', 'src', 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

def test_referee_emails():
    print("🧪 Testing MF Referee Email Extraction")
    print("=" * 60)
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login and get categories
        if not extractor.login():
            print("❌ Login failed")
            return False
            
        from selenium.webdriver.common.by import By
        import time
        
        # Navigate to AE Center
        ae_link = extractor.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get categories and limit to 1 manuscript
        categories = extractor.get_manuscript_categories()
        if not categories:
            print("❌ No categories found")
            return False
            
        # Process just 1 manuscript from first category
        first_category = categories[0]
        first_category['count'] = 1  # Limit to 1 manuscript
        print(f"📂 Testing with: {first_category['name']} (limited to 1 manuscript)")
        
        extractor.process_category(first_category)
        
        if extractor.manuscripts:
            ms = extractor.manuscripts[0]
            print(f"\n📄 Manuscript: {ms.get('id', 'UNKNOWN')}")
            
            # Check referee emails
            referees = ms.get('referees', [])
            emails_found = sum(1 for r in referees if r.get('email', ''))
            
            print(f"\n🧑‍⚖️ Referees: {len(referees)} total")
            print(f"📧 Emails extracted: {emails_found}/{len(referees)} ({100*emails_found/len(referees) if referees else 0:.0f}%)")
            
            for i, r in enumerate(referees[:5]):  # Show first 5
                name = r.get('name', 'Unknown')
                email = r.get('email', '')
                status = '✅' if email else '❌'
                print(f"  {i+1}. {status} {name}: {email if email else 'NO EMAIL'}")
            
            print("\n" + "=" * 60)
            if emails_found > 0:
                print("✅ REFEREE EMAIL EXTRACTION IS WORKING!")
                return True
            else:
                print("❌ REFEREE EMAIL EXTRACTION IS BROKEN (0% success)")
                return False
        else:
            print("❌ No manuscripts extracted")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            extractor.cleanup()
        except:
            pass

if __name__ == "__main__":
    success = test_referee_emails()
    sys.exit(0 if success else 1)
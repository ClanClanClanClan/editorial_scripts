#!/usr/bin/env python3
"""
Test the enhanced MF extraction - just show first manuscript
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor

def test_enhanced():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login
        print("🔐 Testing enhanced extraction...")
        login_success = extractor.login()
        if not login_success:
            print("❌ Login failed")
            return
        
        print("✅ Login successful!")
        
        # Navigate to AE Center and get first category
        print("\n📊 Navigating to AE Center...")
        
        # The extract_all navigation logic but stop after first manuscript
        import time
        from selenium.webdriver.common.by import By
        
        # Navigate to AE center (simplified)
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = extractor.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1
        
        print(f"✅ On main page: {extractor.driver.current_url}")
        time.sleep(3)
        
        # Find AE Center link
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(5)
        print("✅ In AE Center")
        
        # Get categories  
        categories = extractor.get_manuscript_categories()
        
        if categories:
            # Process first category with manuscripts
            for category in categories:
                if category['count'] > 0:
                    print(f"\n🚀 Testing with category: {category['name']} ({category['count']} manuscripts)")
                    
                    # Click category
                    category['link'].click()
                    time.sleep(3)
                    
                    # Find first Take Action
                    take_action_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                    if take_action_links:
                        print(f"✅ Found {len(take_action_links)} manuscripts")
                        
                        # Click first one
                        take_action_links[0].click()
                        time.sleep(5)
                        print("✅ On first manuscript page")
                        
                        # Get manuscript ID
                        manuscript_id = extractor.get_current_manuscript_id()
                        print(f"📄 Processing manuscript: {manuscript_id}")
                        
                        # Create manuscript object
                        manuscript = {
                            'id': manuscript_id,
                            'title': '',
                            'referees': []
                        }
                        
                        # TEST THE ENHANCED EXTRACTION
                        print(f"\n🧪 TESTING ENHANCED REFEREE EXTRACTION...")
                        print("="*60)
                        
                        extractor.extract_referees_comprehensive(manuscript)
                        
                        print("\n📊 EXTRACTION RESULTS:")
                        print("="*60)
                        print(f"Manuscript ID: {manuscript['id']}")
                        print(f"Total referees found: {len(manuscript['referees'])}")
                        
                        for i, referee in enumerate(manuscript['referees'], 1):
                            print(f"\n👤 REFEREE {i}:")
                            print(f"  Name: {referee['name']}")
                            print(f"  Email: {referee['email']}")
                            print(f"  Affiliation: {referee['affiliation']}")
                            print(f"  Country: {referee['country']}")
                            print(f"  Status: {referee['status']}")
                            print(f"  Dates: {referee['dates']}")
                            print(f"  Review Links: {len(referee['review_links'])} found")
                            if referee['review_links']:
                                for link in referee['review_links']:
                                    print(f"    - {link['text']}")
                        
                        print("\n✅ Enhanced extraction test complete!")
                        break
                    else:
                        print("❌ No Take Action links found")
                        continue
        else:
            print("❌ No categories found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n⏸️ Closing browser in 10 seconds...")
        time.sleep(10)
        extractor.driver.quit()

if __name__ == "__main__":
    test_enhanced()
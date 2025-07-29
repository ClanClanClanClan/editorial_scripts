#!/usr/bin/env python3
"""
PROPER TEST: Verify the referee table fix actually works
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By

def test_referee_table_fix():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Quick login
        print("🔐 Testing referee table fix...")
        login_success = extractor.login()
        if not login_success:
            print("❌ Login failed")
            return
        
        # Navigate to manuscript page (streamlined)
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = extractor.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1
        
        time.sleep(3)
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(5)
        
        categories = extractor.get_manuscript_categories()
        if categories:
            for category in categories:
                if category['count'] > 0:
                    category['link'].click()
                    time.sleep(3)
                    
                    take_action_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                    if take_action_links:
                        take_action_links[0].click()
                        time.sleep(5)
                        
                        manuscript_id = extractor.get_current_manuscript_id()
                        print(f"📄 Testing manuscript: {manuscript_id}")
                        
                        # Create test manuscript
                        manuscript = {
                            'id': manuscript_id,
                            'referees': []
                        }
                        
                        print(f"\n🧪 TESTING CORRECTED REFEREE EXTRACTION")
                        print("="*60)
                        
                        # Run the extraction
                        extractor.extract_referees_comprehensive(manuscript)
                        
                        print(f"\n📊 FINAL TEST RESULTS:")
                        print("="*60)
                        
                        referees = manuscript.get('referees', [])
                        print(f"🎯 Total referees extracted: {len(referees)}")
                        
                        if len(referees) == 4:
                            print("✅ CORRECT: Found exactly 4 referees (no authors included)")
                        else:
                            print(f"❌ WRONG: Expected 4 referees, got {len(referees)}")
                        
                        print(f"\n👥 REFEREE LIST:")
                        for i, referee in enumerate(referees, 1):
                            name = referee['name']
                            email = referee['email']
                            affiliation = referee['affiliation']
                            status = referee['status']
                            
                            # Check if this looks like an author (should NOT be present)
                            is_likely_author = name in ['Matoussi, Anis', 'Possamai, Dylan']
                            
                            if is_likely_author:
                                print(f"❌ REFEREE {i}: {name} - THIS IS AN AUTHOR! (FAIL)")
                            else:
                                print(f"✅ REFEREE {i}: {name} - {status} - {affiliation[:50]}...")
                            
                            print(f"   Email: {email}")
                        
                        # Final verdict
                        print(f"\n🏆 FINAL VERDICT:")
                        authors_found = any(r['name'] in ['Matoussi, Anis', 'Possamai, Dylan'] for r in referees)
                        
                        if len(referees) == 4 and not authors_found:
                            print("✅ SUCCESS: Referee table targeting fix works correctly!")
                            print("   - Found exactly 4 referees")
                            print("   - No authors included")
                            print("   - Proper table parsing implemented")
                        else:
                            print("❌ FAILURE: Fix did not work properly")
                            if len(referees) != 4:
                                print(f"   - Wrong count: {len(referees)} instead of 4")
                            if authors_found:
                                print("   - Authors still included in referee list")
                        
                        break
                    break
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser in 5 seconds...")
        time.sleep(5)
        extractor.driver.quit()

if __name__ == "__main__":
    test_referee_table_fix()
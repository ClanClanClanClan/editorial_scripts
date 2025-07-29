#!/usr/bin/env python3
"""
Quick test to show all extraction data details
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By
import json

def show_extraction_data():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Quick login and navigation
        login_success = extractor.login()
        if not login_success:
            return
        
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
                        # Just get first manuscript
                        take_action_links[0].click()
                        time.sleep(5)
                        
                        # Run the actual extract_manuscript_details method
                        manuscript_id = extractor.get_current_manuscript_id()
                        manuscript = extractor.extract_manuscript_details(manuscript_id)
                        
                        print("\n" + "="*80)
                        print("📊 COMPLETE EXTRACTION DATA - ALL DETAILS")
                        print("="*80)
                        
                        # Pretty print all data
                        print(json.dumps(manuscript, indent=2))
                        
                        print("\n" + "="*80)
                        print("📋 COVER LETTER FILES ON DISK:")
                        print("="*80)
                        
                        # Show actual files
                        cover_files = list(Path("downloads").glob(f"*cover_letter*"))
                        for f in cover_files:
                            print(f"📄 {f}")
                            print(f"   Extension: {f.suffix}")
                            print(f"   Size: {f.stat().st_size:,} bytes")
                            print()
                        
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser...")
        extractor.driver.quit()

if __name__ == "__main__":
    show_extraction_data()
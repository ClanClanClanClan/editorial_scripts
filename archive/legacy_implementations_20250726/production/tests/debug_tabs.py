#!/usr/bin/env python3
"""
Debug what tabs are actually available on the manuscript page
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By

def debug_tabs():
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
                        take_action_links[0].click()
                        time.sleep(5)
                        
                        manuscript_id = extractor.get_current_manuscript_id()
                        print(f"🔍 DEBUGGING TABS FOR {manuscript_id}")
                        print("="*60)
                        
                        # Find all links on the page
                        all_links = extractor.driver.find_elements(By.TAG_NAME, "a")
                        print(f"📊 Total links on page: {len(all_links)}")
                        
                        # Look for tab-like links
                        potential_tabs = []
                        for link in all_links:
                            text = link.text.strip()
                            href = link.get_attribute('href') or ''
                            class_attr = link.get_attribute('class') or ''
                            
                            # Look for potential tab indicators
                            if (text and len(text) > 3 and 
                                ('tab' in class_attr.lower() or 
                                 'manuscript' in text.lower() or 
                                 'information' in text.lower() or
                                 'audit' in text.lower() or
                                 'trail' in text.lower() or
                                 'author' in text.lower() or
                                 'review' in text.lower() or
                                 'details' in text.lower())):
                                potential_tabs.append({
                                    'text': text,
                                    'href': href[:80] + '...' if len(href) > 80 else href,
                                    'class': class_attr
                                })
                        
                        print(f"\n🎯 POTENTIAL TABS FOUND: {len(potential_tabs)}")
                        print("-"*60)
                        for i, tab in enumerate(potential_tabs, 1):
                            print(f"{i:2d}. Text: '{tab['text']}'")
                            print(f"    Class: '{tab['class']}'")
                            print(f"    Href: {tab['href']}")
                            print()
                        
                        # Also look at page structure - any div/td elements that might contain tabs
                        print(f"\n🔍 LOOKING FOR TAB-LIKE STRUCTURES...")
                        print("-"*60)
                        
                        # Look for elements with text containing key terms
                        key_terms = ['Manuscript Information', 'Audit Trail', 'Author', 'Timeline', 'Correspondence']
                        for term in key_terms:
                            elements = extractor.driver.find_elements(By.XPATH, 
                                f"//*[contains(text(), '{term}')]")
                            if elements:
                                print(f"✅ Found '{term}': {len(elements)} elements")
                                for elem in elements[:3]:  # Show first 3
                                    tag = elem.tag_name
                                    text = elem.text[:50] + '...' if len(elem.text) > 50 else elem.text
                                    print(f"   {tag}: {text}")
                            else:
                                print(f"❌ Not found: '{term}'")
                        
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser in 20 seconds...")
        time.sleep(20)
        extractor.driver.quit()

if __name__ == "__main__":
    debug_tabs()
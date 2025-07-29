#!/usr/bin/env python3
"""
Debug what happens immediately after login
"""

import sys
import time
import os
from pathlib import Path

# Add path to import the MF extractor  
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials
    load_credentials()
except ImportError:
    from dotenv import load_dotenv
    load_dotenv('.env.production')

from selenium.webdriver.common.by import By
from mf_extractor import ComprehensiveMFExtractor

def debug_post_login():
    """Debug state after login"""
    print("🔍 Debugging post-login state...")
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login
        print("\n📝 Logging in...")
        login_success = extractor.login()
        
        print(f"\n✅ Login returned: {login_success}")
        print(f"   Current URL: {extractor.driver.current_url}")
        print(f"   Page title: {extractor.driver.title}")
        
        # Wait a bit for page to stabilize
        time.sleep(3)
        
        # Check current page state
        print("\n📄 Analyzing current page...")
        
        # Check URL
        current_url = extractor.driver.current_url
        print(f"   URL: {current_url}")
        
        if "ASSOCIATE_EDITOR" in current_url.upper():
            print("   ✅ Already in Associate Editor section!")
        elif "AUTHOR" in current_url.upper():
            print("   📝 In Author section")
        elif "REVIEWER" in current_url.upper():
            print("   👀 In Reviewer section")
        else:
            print("   ❓ Unknown section")
            
        # Find all navigation links
        print("\n🔗 Available navigation links:")
        nav_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, "Center")
        for i, link in enumerate(nav_links):
            text = link.text.strip()
            href = link.get_attribute('href')
            print(f"   {i+1}. '{text}' -> {href}")
            
        # Check for role selection
        print("\n👤 Checking for role selection...")
        role_links = extractor.driver.find_elements(By.XPATH, "//a[contains(@href, 'ROLE_ID')]")
        if role_links:
            print(f"   Found {len(role_links)} role links:")
            for i, link in enumerate(role_links[:5]):
                text = link.text.strip()
                href = link.get_attribute('href')
                print(f"   {i+1}. '{text}' -> {href}")
        else:
            print("   No role selection links found")
            
        # Try to find AE Center link
        print("\n🔍 Looking for Associate Editor Center link...")
        
        # Method 1: Exact text
        try:
            ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            print("   ✅ Found AE Center link with exact text!")
            print(f"      Text: '{ae_link.text}'")
            print(f"      Href: {ae_link.get_attribute('href')}")
            print(f"      Visible: {ae_link.is_displayed()}")
            
            # Click it
            print("\n   👆 Clicking AE Center link...")
            ae_link.click()
            time.sleep(5)
            
            print(f"\n   📍 After click:")
            print(f"      New URL: {extractor.driver.current_url}")
            print(f"      Page title: {extractor.driver.title}")
            
        except Exception as e:
            print(f"   ❌ No exact text link found: {e}")
            
            # Method 2: Partial text
            try:
                ae_links = extractor.driver.find_elements(By.PARTIAL_LINK_TEXT, "Associate Editor")
                if ae_links:
                    print(f"\n   Found {len(ae_links)} links with 'Associate Editor':")
                    for i, link in enumerate(ae_links):
                        print(f"   {i+1}. '{link.text}' -> {link.get_attribute('href')}")
                        
                    # Try clicking the first one
                    print("\n   👆 Clicking first AE link...")
                    ae_links[0].click()
                    time.sleep(5)
                    
                    print(f"\n   📍 After click:")
                    print(f"      New URL: {extractor.driver.current_url}")
                    print(f"      Page title: {extractor.driver.title}")
            except Exception as e2:
                print(f"   ❌ Error with partial text: {e2}")
                
        # Save page source
        print("\n💾 Saving page source...")
        with open("debug_post_login_page.html", "w") as f:
            f.write(extractor.driver.page_source)
        print("   ✅ Saved to debug_post_login_page.html")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔚 Debug complete. Browser will stay open for 15 seconds...")
        time.sleep(15)
        if hasattr(extractor, 'driver') and extractor.driver:
            extractor.driver.quit()

if __name__ == "__main__":
    debug_post_login()
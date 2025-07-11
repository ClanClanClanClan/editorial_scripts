#!/usr/bin/env python3
"""
Debug SIAM authentication with screenshots at each step
"""

import os
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def debug_siam_authentication():
    """Debug SIAM authentication with detailed screenshots."""
    
    # Create screenshots directory
    screenshots_dir = Path('./debug_screenshots_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
    screenshots_dir.mkdir(exist_ok=True)
    
    print(f"📸 Screenshots will be saved to: {screenshots_dir}")
    
    # Setup browser
    chrome_options = Options()
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    screenshot_counter = 0
    
    def take_screenshot(name):
        nonlocal screenshot_counter
        screenshot_counter += 1
        filename = screenshots_dir / f"{screenshot_counter:02d}_{name}.png"
        driver.save_screenshot(str(filename))
        print(f"   📸 Screenshot: {filename.name}")
    
    try:
        print("\n🔐 Testing SICON Authentication...")
        
        # Navigate to SICON
        print("1️⃣ Navigating to SICON...")
        driver.get("http://sicon.siam.org")
        time.sleep(3)
        take_screenshot("sicon_initial")
        
        # Remove cookie banners
        print("2️⃣ Removing cookie banners...")
        driver.execute_script("""
            var cookieElements = document.querySelectorAll('#cookie-policy-layer-bg, #cookie-policy-layer');
            cookieElements.forEach(function(el) { el.remove(); });
        """)
        time.sleep(1)
        take_screenshot("after_cookie_removal")
        
        # Find ORCID link
        print("3️⃣ Looking for ORCID link...")
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        print(f"   Found: {orcid_link.get_attribute('href')}")
        
        # Click ORCID link
        print("4️⃣ Clicking ORCID link...")
        driver.execute_script("arguments[0].click();", orcid_link)
        time.sleep(5)
        take_screenshot("after_orcid_click")
        
        # Check if we're on ORCID page
        print("5️⃣ Checking ORCID page...")
        print(f"   Current URL: {driver.current_url}")
        
        if 'orcid.org' in driver.current_url:
            print("   ✅ On ORCID page")
            
            # Wait a bit more for page to fully load
            time.sleep(3)
            take_screenshot("orcid_page_loaded")
            
            # Try to find any input fields
            print("6️⃣ Looking for input fields...")
            all_inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"   Found {len(all_inputs)} input elements")
            
            for i, input_elem in enumerate(all_inputs):
                try:
                    input_type = input_elem.get_attribute("type")
                    input_id = input_elem.get_attribute("id")
                    input_name = input_elem.get_attribute("name")
                    input_placeholder = input_elem.get_attribute("placeholder")
                    is_displayed = input_elem.is_displayed()
                    
                    print(f"   Input {i+1}:")
                    print(f"     Type: {input_type}")
                    print(f"     ID: {input_id}")
                    print(f"     Name: {input_name}")
                    print(f"     Placeholder: {input_placeholder}")
                    print(f"     Displayed: {is_displayed}")
                except:
                    pass
            
            # Get page source for analysis
            page_source = driver.page_source
            if "username" in page_source.lower():
                print("   ✅ Found 'username' in page source")
            if "userId" in page_source.lower():
                print("   ✅ Found 'userId' in page source")
            if "email" in page_source.lower():
                print("   ✅ Found 'email' in page source")
            
            # Try specific selectors
            print("\n7️⃣ Trying specific selectors...")
            selectors_to_try = [
                "#username", "#userId", "#user-id", "#email",
                "input[name='userId']", "input[name='username']", 
                "input[type='text']", "input[type='email']",
                "input[placeholder*='email' i]", "input[placeholder*='username' i]"
            ]
            
            for selector in selectors_to_try:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        print(f"   ✅ Found element with selector: {selector}")
                        print(f"      Tag: {element.tag_name}")
                        print(f"      Type: {element.get_attribute('type')}")
                        print(f"      Displayed: {element.is_displayed()}")
                        
                        # Try to fill it
                        try:
                            element.send_keys("test")
                            print(f"      ✅ Can interact with element")
                            element.clear()
                        except Exception as e:
                            print(f"      ❌ Cannot interact: {e}")
                except:
                    pass
            
            # Take final screenshot
            take_screenshot("orcid_field_analysis")
            
        else:
            print("   ❌ Not redirected to ORCID")
            take_screenshot("not_on_orcid")
        
        print(f"\n📁 All screenshots saved to: {screenshots_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        take_screenshot("error_state")
        import traceback
        traceback.print_exc()
    
    finally:
        input("\n⏸️  Press Enter to close browser...")
        driver.quit()


if __name__ == "__main__":
    # Check credentials first
    orcid_user = os.getenv("ORCID_USER")
    orcid_pass = os.getenv("ORCID_PASS")
    
    if not orcid_user or not orcid_pass:
        print("❌ ORCID credentials not found in environment")
    else:
        print(f"✅ ORCID credentials available: {orcid_user}")
    
    debug_siam_authentication()
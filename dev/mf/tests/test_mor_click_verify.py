#!/usr/bin/env python3
"""
MOR - ACTUALLY CLICK THE VERIFY BUTTON
"""

import sys
import os
import time

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

print("="*80)
print("🎯 MOR - CLICK VERIFY BUTTON")
print("="*80)

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies handled")
    except:
        pass

    # Login
    print("\n3. Login")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Credentials submitted")

    # Wait for 2FA dialog
    time.sleep(5)

    # Handle 2FA
    print("\n4. 2FA - CLICK THE VERIFY BUTTON")
    print("-"*40)

    # Enter code
    code = "817599"  # Latest code from 01:14:15
    print(f"   Code to use: {code}")

    # Set code
    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
    print("   ✅ Code entered")

    # NOW CLICK THE VERIFY BUTTON - THE BLUE ONE!
    print("   Looking for Verify button...")

    # Find all buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"   Found {len(buttons)} buttons total")

    for i, btn in enumerate(buttons):
        btn_text = btn.text.strip()
        btn_classes = btn.get_attribute("class") or ""
        btn_style = btn.get_attribute("style") or ""

        print(f"   Button {i}: text='{btn_text}', classes='{btn_classes}'")

        # Look for the Verify button
        if "verify" in btn_text.lower() or ">" in btn_text:
            print(f"   ✅ FOUND VERIFY BUTTON: '{btn_text}'")

            # Try different click methods
            try:
                # Method 1: Regular click
                btn.click()
                print("   ✅ Clicked with regular click!")
                break
            except:
                try:
                    # Method 2: JavaScript click
                    driver.execute_script("arguments[0].click();", btn)
                    print("   ✅ Clicked with JavaScript!")
                    break
                except:
                    try:
                        # Method 3: Action chains
                        actions = ActionChains(driver)
                        actions.move_to_element(btn).click().perform()
                        print("   ✅ Clicked with action chains!")
                        break
                    except Exception as e:
                        print(f"   Failed to click: {e}")

    # Alternative: Click by exact text
    if "verify" not in driver.current_url.lower():
        print("   Alternative: Clicking by XPath...")
        try:
            # Look for button with text containing "Verify"
            verify_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Verify')]")
            driver.execute_script("arguments[0].click();", verify_btn)
            print("   ✅ Clicked Verify button via XPath!")
        except:
            pass

    # Wait for result
    print("   Waiting for login to complete...")
    time.sleep(10)

    # Check status
    print("\n5. CHECK RESULTS")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title
    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    # Check if we're logged in
    try:
        # Check if 2FA dialog is gone
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ❌ 2FA dialog still visible!")

            # Last resort - submit the form
            print("   Trying to submit the form directly...")
            driver.execute_script("""
                var forms = document.getElementsByTagName('form');
                for (var i = 0; i < forms.length; i++) {
                    if (forms[i].innerHTML.includes('TOKEN_VALUE')) {
                        forms[i].submit();
                        console.log('Submitted form!');
                        break;
                    }
                }
            """)
            time.sleep(5)
    except:
        print("   ✅ 2FA dialog not visible - might be logged in!")

    # Final check
    print("\n6. FINAL CHECK")
    print("-"*40)

    all_links = driver.find_elements(By.TAG_NAME, "a")
    for link in all_links:
        text = link.text.strip()
        if text and "editor" in text.lower():
            print(f"   ✅ FOUND EDITOR LINK: {text}")
            link.click()
            time.sleep(5)

            # Now we should be in AE Center
            print("\n7. IN ASSOCIATE EDITOR CENTER")
            print("-"*40)

            # Look for manuscripts
            page_text = driver.page_source
            if "MOR-" in page_text:
                import re
                mor_ids = re.findall(r'MOR-\d{4}-\d{4}', page_text)
                print(f"   ✅ Found {len(set(mor_ids))} manuscripts!")
                for ms_id in set(mor_ids):
                    print(f"      - {ms_id}")

            break
    else:
        print("   ❌ No editor links found")
        print("   Available links:")
        for i, link in enumerate(all_links[:20], 1):
            if link.text.strip():
                print(f"   {i}. {link.text}")

    # Save screenshot
    driver.save_screenshot("/tmp/mor_click_verify_result.png")
    print("\n📸 Screenshot: /tmp/mor_click_verify_result.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_click_verify_error.png")

finally:
    if driver:
        print("\nKeeping browser open for 20 seconds...")
        time.sleep(20)
        driver.quit()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
#!/usr/bin/env python3
"""
MOR EXTRACTION - FIX THE VERIFY BUTTON CLICK
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("="*80)
print("🎯 MOR EXTRACTION - FIXING VERIFY BUTTON")
print("="*80)

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
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
    print("\n4. 2FA Handling")
    if "verification" in driver.page_source.lower():
        print("   ✅ 2FA dialog detected")

        # Enter code
        code = "489890"  # Latest fresh code
        print(f"   Using code: {code}")

        # Enter code in field
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            token_field.clear()
            token_field.send_keys(code)
            print("   ✅ Code entered")
        except:
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            print("   ✅ Code set via JS")

        # Now click the Verify button - try multiple selectors
        print("   Attempting to click Verify button...")

        clicked = False

        # Method 1: Click button containing "Verify" text
        if not clicked:
            try:
                verify_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Verify')]")
                for btn in verify_btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        print(f"   ✅ Clicked Verify button (text: {btn.text})")
                        break
            except Exception as e:
                print(f"   Method 1 failed: {e}")

        # Method 2: Click any button with class 'btn-primary' or similar
        if not clicked:
            try:
                primary_btns = driver.find_elements(By.CSS_SELECTOR, "button.btn-primary, button[type='submit'], .modal-footer button")
                for btn in primary_btns:
                    if "verify" in btn.text.lower() or ">" in btn.text:
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        print(f"   ✅ Clicked button: {btn.text}")
                        break
            except Exception as e:
                print(f"   Method 2 failed: {e}")

        # Method 3: Find and click the visible Verify button in modal
        if not clicked:
            try:
                # Find the modal dialog
                modal = driver.find_element(By.CLASS_NAME, "modal-dialog")
                # Find the Verify button within the modal
                verify_btn = modal.find_element(By.XPATH, ".//button[contains(text(), 'Verify')]")
                driver.execute_script("arguments[0].click();", verify_btn)
                clicked = True
                print("   ✅ Clicked Verify button in modal")
            except Exception as e:
                print(f"   Method 3 failed: {e}")

        # Method 4: Direct JavaScript execution on the button
        if not clicked:
            try:
                driver.execute_script("""
                    // Find all buttons
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.includes('Verify')) {
                            buttons[i].click();
                            console.log('Clicked Verify button: ' + buttons[i].textContent);
                            break;
                        }
                    }
                """)
                print("   ✅ Clicked via JavaScript search")
            except Exception as e:
                print(f"   Method 4 failed: {e}")

        print("   Waiting for login to complete...")
        time.sleep(10)

    # Check if logged in
    print("\n5. Verify Login")
    current_url = driver.current_url
    page_title = driver.title
    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    # Wait for page to load
    time.sleep(5)

    # Check for editor links
    print("\n6. Check for Editor Links")
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"   Found {len(all_links)} links")

    editor_found = False
    for link in all_links:
        text = link.text.strip()
        if text:
            if "editor" in text.lower():
                print(f"   ✅ FOUND EDITOR LINK: {text}")
                editor_found = True
                link.click()
                time.sleep(5)
                break

    if not editor_found:
        print("   Links found:")
        for i, link in enumerate(all_links[:30], 1):
            if link.text.strip():
                print(f"   {i}. {link.text}")

    # Check final state
    print("\n7. Final State")
    print(f"   URL: {driver.current_url}")
    print(f"   Title: {driver.title}")

    # Save screenshot
    driver.save_screenshot("/tmp/mor_verify_fix.png")
    print("   Screenshot: /tmp/mor_verify_fix.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_verify_error.png")

finally:
    if driver:
        print("\nBrowser closing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
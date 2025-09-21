#!/usr/bin/env python3
"""
MOR FINAL 2FA SOLUTION - ACTUALLY CLICK THE VERIFY BUTTON
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

print("="*80)
print("🎯 MOR FINAL 2FA SOLUTION")
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

    # Wait for 2FA
    time.sleep(5)

    # Handle 2FA
    print("\n4. 2FA HANDLING - FINAL SOLUTION")
    print("-"*40)

    # Enter code
    code = "904075"  # Latest fresh code
    print(f"   Using code: {code}")

    # Set code using JavaScript to ensure it's in the field
    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
    print("   ✅ Code entered")

    # Now the critical part - actually click the Verify button
    print("   Finding and clicking Verify button...")

    # Method 1: Find button by text "Verify"
    try:
        # Wait for button to be present
        verify_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Verify')]")))
        print(f"   Found button with text: {verify_btn.text}")

        # Scroll into view
        driver.execute_script("arguments[0].scrollIntoView(true);", verify_btn)
        time.sleep(1)

        # Try regular click
        try:
            verify_btn.click()
            print("   ✅ Clicked with regular click")
        except:
            # Force click with JavaScript
            driver.execute_script("arguments[0].click();", verify_btn)
            print("   ✅ Clicked with JavaScript")
    except Exception as e:
        print(f"   Method 1 failed: {e}")

        # Method 2: Find ANY button containing "Verify" and click ALL of them
        try:
            buttons = driver.find_elements(By.XPATH, "//button")
            for btn in buttons:
                if "verify" in btn.text.lower() or ">" in btn.text:
                    print(f"   Found button: {btn.text}")
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"   ✅ Clicked button: {btn.text}")
                    break
        except Exception as e:
            print(f"   Method 2 failed: {e}")

    # Wait for result
    print("   Waiting for login to complete...")
    time.sleep(10)

    # Check result
    print("\n5. CHECK LOGIN STATUS")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title

    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    # Check if 2FA dialog is still visible
    try:
        dialog_still_visible = driver.find_element(By.ID, "TOKEN_VALUE")
        if dialog_still_visible.is_displayed():
            print("   ❌ 2FA dialog still visible - button click failed!")

            # Try one more time with a different approach
            print("   Final attempt - looking for the blue Verify button...")
            verify_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-primary, button[style*='blue'], button[class*='primary']")
            for btn in verify_buttons:
                if btn.is_displayed():
                    print(f"   Found primary button: {btn.text}")
                    driver.execute_script("arguments[0].click();", btn)
                    print("   ✅ Clicked primary button")
                    time.sleep(5)
                    break
    except:
        print("   ✅ 2FA dialog not visible - login might be complete")

    # Final check
    time.sleep(5)

    print("\n6. FINAL STATUS")
    print("-"*40)
    print(f"   Final URL: {driver.current_url}")
    print(f"   Final Title: {driver.title}")

    # Look for editor links
    editor_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Editor")
    if editor_links:
        print(f"   ✅ FOUND {len(editor_links)} Editor links!")
        for link in editor_links:
            print(f"      - {link.text}")
    else:
        print("   ❌ No Editor links found")

        # Show all available links
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"   Available links ({len(all_links)} total):")
        for i, link in enumerate(all_links[:15], 1):
            if link.text.strip():
                print(f"   {i}. {link.text}")

    # Save screenshot
    driver.save_screenshot("/tmp/mor_final_2fa_result.png")
    print("\n   📸 Screenshot saved: /tmp/mor_final_2fa_result.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_final_2fa_error.png")

finally:
    if driver:
        print("\nKeeping browser open for 20 seconds to observe...")
        time.sleep(20)
        driver.quit()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
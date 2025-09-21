#!/usr/bin/env python3
"""
Manual Device Verification for MOR - Step by step debugging
"""

import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


def debug_device_verification():
    """Debug device verification step by step."""

    # Setup Chrome - visible for debugging
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # Step 1: Login
        print("🔐 Step 1: Login...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        # Enter credentials
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)

        print(f"   📍 After login: {driver.current_url}")

        # Step 2: Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("🔐 Step 2: 2FA verification...")
            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )
            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)
                print(f"   📍 After 2FA: {driver.current_url}")

        # Step 3: Check for device verification
        current_page = driver.page_source
        if "Unrecognized Device" in current_page:
            print("🔐 Step 3: Device verification detected!")

            # Save current page for analysis
            with open("device_verification_page.html", "w") as f:
                f.write(current_page)
            print("   💾 Saved device verification page")

            # Find all input fields
            input_fields = driver.find_elements(By.TAG_NAME, "input")
            print(f"   🔍 Found {len(input_fields)} input fields:")

            for i, field in enumerate(input_fields):
                try:
                    field_type = field.get_attribute("type")
                    field_name = field.get_attribute("name")
                    field_id = field.get_attribute("id")
                    field_placeholder = field.get_attribute("placeholder")
                    is_visible = field.is_displayed()
                    is_enabled = field.is_enabled()

                    print(f"      [{i}] Type: {field_type}, Name: {field_name}, ID: {field_id}")
                    print(
                        f"          Placeholder: {field_placeholder}, Visible: {is_visible}, Enabled: {is_enabled}"
                    )
                except Exception as e:
                    print(f"      [{i}] Error getting field info: {e}")

            # Find all buttons/links
            buttons = driver.find_elements(
                By.XPATH, "//button | //a[contains(@class, 'button')] | //input[@type='submit']"
            )
            print(f"   🔘 Found {len(buttons)} potential submit buttons:")

            for i, btn in enumerate(buttons):
                try:
                    btn_text = btn.text.strip()
                    btn_onclick = btn.get_attribute("onclick")
                    is_visible = btn.is_displayed()

                    print(
                        f"      [{i}] Text: '{btn_text}', OnClick: {btn_onclick}, Visible: {is_visible}"
                    )
                except Exception as e:
                    print(f"      [{i}] Error getting button info: {e}")

            # Get device verification code
            print("   📱 Getting device verification code...")
            device_time = datetime.now()
            device_code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=device_time
            )

            if device_code:
                print(f"   ✅ Got device code: {device_code}")

                # Find the best text input field
                text_inputs = [
                    f
                    for f in input_fields
                    if f.get_attribute("type") == "text" and f.is_displayed() and f.is_enabled()
                ]

                if text_inputs:
                    print(
                        f"   🎯 Using text input field: {text_inputs[0].get_attribute('name')} / {text_inputs[0].get_attribute('id')}"
                    )

                    # Enter the code
                    text_inputs[0].clear()
                    text_inputs[0].send_keys(device_code)
                    print("   ✅ Entered device code")

                    # Find submit button
                    verify_buttons = [
                        b
                        for b in buttons
                        if b.is_displayed()
                        and ("verify" in b.text.lower() or "submit" in b.text.lower())
                    ]

                    if verify_buttons:
                        print(f"   🎯 Clicking verify button: '{verify_buttons[0].text}'")
                        verify_buttons[0].click()
                        time.sleep(10)  # Wait longer for processing

                        print(f"   📍 After device verification: {driver.current_url}")

                        # Check if we're logged in now
                        if "login" not in driver.current_url.lower():
                            print("   ✅ Device verification successful!")

                            # Try to navigate to AE Center
                            print("\n📋 Attempting AE Center navigation...")
                            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
                            driver.get(ae_url)
                            time.sleep(5)

                            final_url = driver.current_url
                            final_page = driver.find_element(By.TAG_NAME, "body").text[:200]

                            print(f"   📍 Final URL: {final_url}")
                            print(f"   📄 Final page: {final_page[:100]}...")

                            # Save final page
                            with open("mor_post_verification.html", "w") as f:
                                f.write(driver.page_source)
                            print("   💾 Saved post-verification page")

                        else:
                            print("   ❌ Device verification failed - still on login page")

                    else:
                        print("   ⚠️ No verify button found, trying Enter key")
                        text_inputs[0].send_keys("\n")
                        time.sleep(10)

                        print(f"   📍 After Enter key: {driver.current_url}")

                else:
                    print("   ❌ No suitable text input field found")
            else:
                print("   ❌ No device code received")
        else:
            print("🎉 No device verification required!")
            print(f"   📍 Current URL: {driver.current_url}")

            # Try direct navigation
            print("\n📋 Attempting direct AE navigation...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(5)

            final_url = driver.current_url
            final_page = driver.find_element(By.TAG_NAME, "body").text[:200]

            print(f"   📍 Final URL: {final_url}")
            print(f"   📄 Final page: {final_page[:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        input("\n⏸️ Press Enter to close...")
        driver.quit()


if __name__ == "__main__":
    debug_device_verification()

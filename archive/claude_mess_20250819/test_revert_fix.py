#!/usr/bin/env python3
"""
Test if reverting to original device verification approach fixes login
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


def test_revert_login():
    """Test original device verification approach."""

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        print("🔐 Testing ORIGINAL device verification approach...")

        # Login
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(1)
        except:
            pass

        # Credentials
        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)

        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)

        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("   ✅ Login submitted")
        time.sleep(8)

        # Handle 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )

            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
                print("   ✅ 2FA submitted")

        # ORIGINAL APPROACH: Just close device verification modal
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   📱 ORIGINAL APPROACH: Just dismissing device verification modal...")
                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                time.sleep(3)
                print("   ✅ Device verification modal dismissed")
        except:
            print("   ✅ No device verification modal")
            pass

        # Check login status
        current_url = driver.current_url
        page_content = driver.page_source

        print(f"\n📍 Current URL: {current_url}")

        # Check for logout indicators
        logout_indicators = [
            "logged out" in page_content.lower(),
            "inactivity" in page_content.lower(),
            "login" in current_url.lower() and "NEXT_PAGE" not in current_url,
        ]

        if any(logout_indicators):
            print("   ❌ STILL LOGGED OUT - Original approach doesn't work either")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"   📄 Page: {page_preview}...")
        else:
            print("   🎉 LOGIN SUCCESSFUL with original approach!")

            # Try navigation
            print("\n📋 Testing navigation...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(5)

            nav_url = driver.current_url
            nav_content = driver.page_source

            print(f"   📍 Navigation URL: {nav_url}")

            if "Associate Editor" in nav_content:
                print("   ✅ Successfully reached AE Center!")

                # Look for manuscripts quickly
                take_actions = driver.find_elements(
                    By.XPATH, "//img[contains(@src, 'check_off.gif')]"
                )
                print(f"   📄 Found {len(take_actions)} Take Action buttons")

                if len(take_actions) > 0:
                    print("   🎉 MANUSCRIPTS FOUND! Original approach works!")
                else:
                    print("   📂 No manuscripts visible, but navigation worked")

            else:
                print("   ⚠️ Navigation failed")
                nav_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
                print(f"   📄 Nav page: {nav_preview}...")

        print("\n📊 RESULT: Original approach test complete")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        input("\n⏸️ Press Enter to close...")
        driver.quit()


if __name__ == "__main__":
    test_revert_login()

#!/usr/bin/env python3
"""
Final MOR Test - No input() hang, comprehensive logging
"""

import json
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


def final_mor_test():
    """Final MOR test with no hanging."""

    options = webdriver.ChromeOptions()
    # Smaller window
    options.add_argument("--window-size=1200,800")
    options.add_argument("--window-position=100,100")
    # Stealth
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    manuscripts = []

    try:
        print("🔐 FINAL MOR TEST - With device verification fix...")

        # Login
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        print(f"   📍 Step 1 - Page loaded: {driver.current_url}")

        # Handle cookies
        try:
            cookie_btn = driver.find_element(By.ID, "onetrust-reject-all-handler")
            cookie_btn.click()
            time.sleep(2)
            print("   🍪 Step 2 - Cookies rejected")
        except:
            print("   🍪 Step 2 - No cookies")

        # Credentials
        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        print(f"   📧 Step 3 - Email: {email}")

        # Login form
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)

        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)

        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()

        print("   🚀 Step 4 - Login submitted")
        time.sleep(8)

        print(f"   📍 Step 5 - After login: {driver.current_url}")

        # Handle 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 Step 6 - 2FA required")

            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )

            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
                print(f"   📍 Step 7 - After 2FA: {driver.current_url}")

        # Device verification
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   🔐 Step 8 - Device verification required")

                device_time = datetime.now()
                device_code = fetch_latest_verification_code(
                    "MOR", max_wait=30, poll_interval=2, start_timestamp=device_time
                )

                if device_code:
                    print(f"   ✅ Got device code: {device_code[:3]}***")

                    # Enter code
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(device_code)

                    # Remember device
                    try:
                        remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                    except:
                        pass

                    # Submit
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(12)

                    print(f"   📍 Step 9 - After device verification: {driver.current_url}")

                else:
                    print("   ❌ No device code - trying to dismiss modal")
                    close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                    close_btn.click()
                    time.sleep(5)

        except NoSuchElementException:
            print("   ✅ Step 8 - No device verification needed")

        # Final login check
        current_url = driver.current_url
        page_content = driver.page_source

        print(f"   📍 Step 10 - Final URL: {current_url}")

        # Check for success/failure indicators
        success_indicators = [
            "Dylan Possamaï" in page_content,
            "Associate Editor" in page_content,
            "ASSOCIATE_EDITOR" in current_url,
            "logout" in page_content.lower() and "inactivity" not in page_content.lower(),
        ]

        failure_indicators = [
            "logged out" in page_content.lower(),
            "inactivity" in page_content.lower(),
            "Log In" in page_content and current_url == "https://mc.manuscriptcentral.com/mathor",
        ]

        if any(success_indicators):
            print("   🎉 LOGIN SUCCESSFUL!")

            # Test navigation
            print("   📋 Step 11 - Testing navigation...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(5)

            if "Associate Editor" in driver.page_source:
                print("   ✅ Navigation successful!")

                # Look for manuscripts
                category_links = driver.find_elements(
                    By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports"
                )
                if category_links:
                    category_links[0].click()
                    time.sleep(5)

                take_actions = driver.find_elements(
                    By.XPATH, "//img[contains(@src, 'check_off.gif')]"
                )
                print(f"   📄 Found {len(take_actions)} manuscripts")

                # Get manuscript IDs
                for img in take_actions:
                    try:
                        row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            manuscript_id = cells[0].text.strip()
                            if manuscript_id and "MOR-" in manuscript_id:
                                manuscripts.append(
                                    {"id": manuscript_id, "found_at": datetime.now().isoformat()}
                                )
                                print(f"   ✅ Found: {manuscript_id}")
                    except:
                        continue
            else:
                print("   ❌ Navigation failed")

        elif any(failure_indicators):
            print("   ❌ LOGIN FAILED")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:300]
            print(f"   📄 Page preview: {page_preview[:150]}...")

        else:
            print("   ⚠️ LOGIN STATUS UNCLEAR")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:300]
            print(f"   📄 Page preview: {page_preview[:150]}...")

        # Save results without input() hang
        results = {
            "test_time": datetime.now().isoformat(),
            "final_test": True,
            "manuscripts_found": len(manuscripts),
            "manuscripts": manuscripts,
            "final_url": current_url,
        }

        output_file = f"mor_final_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print("\n📊 FINAL TEST COMPLETE - NO HANGING")
        print(f"   📊 Manuscripts found: {len(manuscripts)}")
        print(f"   💾 Results saved to: {output_file}")

        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # NO input() - just close after delay
        print("\n⏰ Closing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("🔒 Browser closed")

    return manuscripts


if __name__ == "__main__":
    results = final_mor_test()
    print(f"\n🏁 TEST COMPLETE: {len(results)} manuscripts found")

    # Show results summary
    if results:
        print("📋 MANUSCRIPT SUMMARY:")
        for r in results:
            print(f"   - {r['id']}")
    else:
        print("⚠️ NO MANUSCRIPTS FOUND - Check login/navigation issues")

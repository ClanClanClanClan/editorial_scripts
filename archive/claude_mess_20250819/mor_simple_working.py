#!/usr/bin/env python3
"""
Simple Working MOR Extractor - Back to basics
Focus on getting login working first
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


def simple_mor_extraction():
    """Simple MOR extraction - focus on getting it working."""

    # Simple Chrome setup
    options = webdriver.ChromeOptions()
    # Less intrusive - smaller window
    options.add_argument("--window-size=1200,800")
    options.add_argument("--window-position=100,100")
    # Basic stealth
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    manuscripts = []
    processed_ids = set()

    try:
        print("🔐 SIMPLE MOR EXTRACTOR - Basic login test...")

        # Go to login page
        print("   📍 Navigating to login page...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        # Check if page loaded
        print(f"   📍 Current URL: {driver.current_url}")
        page_title = driver.title
        print(f"   📄 Page title: {page_title}")

        # Handle cookies
        try:
            cookie_btn = driver.find_element(By.ID, "onetrust-reject-all-handler")
            cookie_btn.click()
            print("   🍪 Rejected cookies")
            time.sleep(2)
        except:
            print("   🍪 No cookies to reject")

        # Find login fields
        print("   🔍 Looking for login fields...")
        try:
            email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
            print("   ✅ Found email field")

            password_field = driver.find_element(By.ID, "PASSWORD")
            print("   ✅ Found password field")

            login_button = driver.find_element(By.ID, "logInButton")
            print("   ✅ Found login button")

        except Exception as e:
            print(f"   ❌ Could not find login fields: {e}")
            return manuscripts

        # Get credentials
        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        if not email or not password:
            print("   ❌ Missing credentials")
            return manuscripts

        print(f"   📧 Using email: {email}")

        # Enter credentials
        print("   ⌨️ Entering credentials...")
        email_field.clear()
        email_field.send_keys(email)

        password_field.clear()
        password_field.send_keys(password)

        # Submit login
        print("   🚀 Submitting login...")
        login_button.click()
        time.sleep(8)

        print(f"   📍 After login submit: {driver.current_url}")

        # Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")

            try:
                login_time = datetime.now()
                code = fetch_latest_verification_code(
                    "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
                )

                if code:
                    print(f"   ✅ Got 2FA code: {code[:3]}***")

                    code_field = driver.find_element(By.NAME, "verificationCode")
                    code_field.send_keys(code)

                    submit_btn = driver.find_element(By.ID, "submitButton")
                    submit_btn.click()
                    time.sleep(8)

                    print(f"   📍 After 2FA: {driver.current_url}")
                else:
                    print("   ❌ No 2FA code received")

            except Exception as e:
                print(f"   ❌ 2FA error: {e}")

        # Handle device verification - PROPER approach
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   🔐 Device verification modal found - handling properly...")

                # Get device verification code from Gmail
                device_time = datetime.now()
                device_code = fetch_latest_verification_code(
                    "MOR", max_wait=30, poll_interval=2, start_timestamp=device_time
                )

                if device_code:
                    print(f"   ✅ Got device code: {device_code[:3]}***")

                    # Enter verification code
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(device_code)
                    print("   ✅ Entered device code")

                    # Check remember device
                    try:
                        remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                            print("   ✅ Checked remember device")
                    except:
                        pass

                    # Submit verification
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    print("   🚀 Device verification submitted")
                    time.sleep(10)  # Wait for processing

                    print(f"   📍 After device verification: {driver.current_url}")

                else:
                    print("   ❌ No device verification code received")
                    # Try dismissing as fallback
                    try:
                        close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                        close_btn.click()
                        print("   ⚠️ Device verification dismissed as fallback")
                        time.sleep(5)
                    except:
                        pass

        except NoSuchElementException:
            print("   ✅ No device verification modal")

        # Check login status
        current_url = driver.current_url
        page_content = driver.page_source

        print(f"   📍 Final URL: {current_url}")

        # Simple login check
        if "logged out" in page_content.lower() or "inactivity" in page_content.lower():
            print("   ❌ Login failed - logged out detected")

            # Save page for debugging
            with open("simple_login_debug.html", "w") as f:
                f.write(page_content)
            print("   💾 Saved debug page")

        elif "Dylan Possamaï" in page_content or "Associate Editor" in page_content:
            print("   🎉 Login successful!")

            # Try simple navigation
            print("\n   📋 Testing simple navigation...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(5)

            nav_url = driver.current_url
            nav_content = driver.page_source

            print(f"   📍 Navigation URL: {nav_url}")

            if "Associate Editor" in nav_content:
                print("   ✅ Reached AE Center!")

                # Look for category
                category_links = driver.find_elements(
                    By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports"
                )
                if category_links:
                    print("   📂 Found category")
                    category_links[0].click()
                    time.sleep(5)
                else:
                    print("   📂 No category found")

                # Look for manuscripts
                take_actions = driver.find_elements(
                    By.XPATH, "//img[contains(@src, 'check_off.gif')]"
                )
                print(f"   📄 Found {len(take_actions)} manuscripts")

                # Quick manuscript ID extraction
                for img in take_actions:
                    try:
                        row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            manuscript_id = cells[0].text.strip()
                            if manuscript_id and "MOR-" in manuscript_id:
                                manuscripts.append(
                                    {
                                        "id": manuscript_id,
                                        "title": "Quick extraction test",
                                        "extraction_time": datetime.now().isoformat(),
                                    }
                                )
                                print(f"   📋 {manuscript_id}")
                    except:
                        continue

            else:
                print("   ❌ Could not reach AE Center")
                nav_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
                print(f"   📄 Nav page: {nav_preview}...")

        else:
            print("   ⚠️ Login status unclear")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"   📄 Current page: {page_preview}...")

        # Save results
        results = {
            "extraction_time": datetime.now().isoformat(),
            "simple_test": True,
            "manuscripts_found": len(manuscripts),
            "manuscripts": manuscripts,
        }

        output_file = f"mor_simple_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print("\n📊 SIMPLE TEST COMPLETE")
        print(f"   📊 Found {len(manuscripts)} manuscripts")
        print(f"   💾 Results: {output_file}")

        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        input("\n⏸️ Press Enter to close (smaller window)...")
        driver.quit()

    return manuscripts


if __name__ == "__main__":
    results = simple_mor_extraction()
    print(f"\n📊 FINAL: {len(results)} manuscripts found")

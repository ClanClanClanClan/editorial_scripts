#!/usr/bin/env python3
"""
Test ORIGINAL approach - just dismiss device verification modal
This was working BEFORE I "fixed" it
"""

import json
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


def test_original_working_approach():
    """Test the ORIGINAL approach that was actually working."""

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1400,900")
    driver = webdriver.Chrome(options=options)

    try:
        print("🔐 TESTING ORIGINAL APPROACH (that was working)...")
        print("=" * 60)

        # Step 1: Login
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

        email_field = driver.find_element(By.ID, "USERID")
        email_field.clear()
        email_field.send_keys(email)

        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)

        # Submit login
        login_timestamp = datetime.now()
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(8)

        print(f"✓ Login submitted at: {login_timestamp.strftime('%H:%M:%S')}")

        # Handle 2FA (this part was working)
        if "twoFactorAuthForm" in driver.page_source:
            print("📱 2FA required...")
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_timestamp
            )

            if code:
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
                print(f"✓ 2FA completed with code: {code}")

        # ORIGINAL APPROACH: Just dismiss device verification modal
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("🔐 Device verification modal found...")
                print("📱 ORIGINAL APPROACH: Just dismissing modal (not entering code)")

                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                time.sleep(5)

                print("✓ Modal dismissed - testing if this prevents logout...")

        except:
            print("✓ No device verification modal")

        # Check login status after original approach
        current_url = driver.current_url
        page_content = driver.page_source

        print("\nSTATUS CHECK:")
        print(f"URL: {current_url}")

        # Check for logout indicators
        if "logged out" in page_content.lower() or "inactivity" in page_content.lower():
            print("❌ LOGGED OUT detected - original approach also fails now")

            # Save debug page
            with open("original_approach_debug.html", "w") as f:
                f.write(page_content)
            print("💾 Saved debug page")
            return False

        elif "Dylan Possamaï" in page_content or (
            "logout" in page_content.lower() and "inactivity" not in page_content.lower()
        ):
            print("✅ LOGIN SUCCESSFUL with original approach!")

            # Test navigation immediately
            print("\nTesting navigation immediately after login...")
            driver.get(
                "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            )
            time.sleep(5)

            if "Associate Editor" in driver.page_source:
                print("✅ Navigation successful!")

                # Quick manuscript check
                category_links = driver.find_elements(
                    By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports"
                )
                if category_links:
                    category_links[0].click()
                    time.sleep(5)

                    take_actions = driver.find_elements(
                        By.XPATH, "//img[contains(@src, 'check_off.gif')]"
                    )
                    print(f"✅ Found {len(take_actions)} manuscripts!")

                    # Get IDs
                    manuscripts = []
                    for img in take_actions:
                        try:
                            row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if cells:
                                manuscript_id = cells[0].text.strip()
                                if "MOR-" in manuscript_id:
                                    manuscripts.append(manuscript_id)
                                    print(f"   📋 {manuscript_id}")
                        except:
                            continue

                    # Save success proof
                    proof = {
                        "approach": "original_dismiss_modal",
                        "timestamp": datetime.now().isoformat(),
                        "login_successful": True,
                        "navigation_successful": True,
                        "manuscripts_found": len(manuscripts),
                        "manuscript_ids": manuscripts,
                    }

                    with open("original_approach_success.json", "w") as f:
                        json.dump(proof, f, indent=2)

                    print("\n🎉 ORIGINAL APPROACH WORKS!")
                    print(f"   📊 Found {len(manuscripts)} manuscripts")
                    print("   💾 Success proof saved")
                    return True

            else:
                print("❌ Navigation failed even with original approach")
                nav_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
                print(f"📄 Nav page: {nav_preview}...")
                return False
        else:
            print("❌ Login status unclear with original approach")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"📄 Page: {page_preview}...")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    finally:
        print("\n⏰ Closing in 5 seconds...")
        time.sleep(5)
        driver.quit()


if __name__ == "__main__":
    print("Testing if ORIGINAL approach (dismiss modal) still works...")
    success = test_original_working_approach()

    if success:
        print("\n✅ ORIGINAL APPROACH STILL WORKS - My 'fix' broke it")
    else:
        print("\n❌ ORIGINAL APPROACH ALSO BROKEN - Something else changed")

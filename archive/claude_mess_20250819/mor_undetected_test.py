#!/usr/bin/env python3

import json
import os
import sys
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


def run_extraction():
    """Test MOR extraction with undetected-chromedriver."""

    # Setup undetected Chrome
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options, version_main=None)
    driver.set_window_size(1920, 1080)

    manuscripts = []
    try:
        # Login
        print("🔐 Logging in to MOR with UNDETECTED Chrome...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)  # Let page fully load

        # Enter credentials
        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        print("   📧 Entering credentials...")
        email_field = driver.find_element(By.ID, "USERID")
        email_field.clear()
        email_field.send_keys(email)

        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)

        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        time.sleep(5)

        # Check for 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required, getting code from Gmail...")
            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )
            if code:
                print(f"   ✅ Got code: {code[:3]}***")
                code_field = driver.find_element(By.NAME, "verificationCode")
                code_field.send_keys(code)
                submit_btn = driver.find_element(By.ID, "submitButton")
                submit_btn.click()
                time.sleep(5)

        # Check if logged in
        current_url = driver.current_url
        print(f"   📍 Current URL: {current_url}")

        if "login" not in current_url.lower():
            print("   ✅ Login successful!")

            # Try direct navigation to AE dashboard
            print("\n📋 Navigating directly to AE Dashboard...")
            driver.get(
                "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            )
            time.sleep(5)

            current_url = driver.current_url
            print(f"   📍 Dashboard URL: {current_url}")

            # Save page for debugging
            with open("undetected_page.html", "w") as f:
                f.write(driver.page_source)
            print("   💾 Saved page HTML for debugging")

            # Check what page we're on
            page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            print(f"   📄 Page preview: {page_text[:200]}...")

            # Look for journal link first
            print("\n🔍 Looking for journal link...")
            journal_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Mathematics")
            if journal_links:
                print("   ✅ Found journal link, clicking...")
                journal_links[0].click()
                time.sleep(5)

                # Now look for AE Center
                ae_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Associate Editor")
                if ae_links:
                    print("   ✅ Found AE Center link, clicking...")
                    ae_links[0].click()
                    time.sleep(5)

            # Look for manuscripts
            print("\n🔍 Looking for manuscripts...")

            # Try to find any tables with manuscripts
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"   Found {len(tables)} tables")

            # Look for Take Action links
            take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            print(f"   Found {len(take_actions)} Take Action icons")

            if take_actions:
                print("\n📄 Found manuscripts! Processing...")
                # Get manuscript rows
                manuscript_rows = driver.find_elements(
                    By.XPATH, "//img[contains(@src, 'check_off.gif')]/ancestor::tr[1]"
                )

                for row in manuscript_rows[:2]:  # Process first 2
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            manuscript_id = cells[0].text.strip()
                            title = cells[1].text.strip() if len(cells) > 1 else "Unknown"

                            manuscripts.append(
                                {"id": manuscript_id, "title": title, "row_text": row.text[:200]}
                            )
                            print(f"   ✅ Found manuscript: {manuscript_id}")
                    except Exception as e:
                        print(f"   ⚠️ Error processing row: {e}")
            else:
                # Try category links
                print("\n📂 Looking for category links...")
                category_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Awaiting')]")
                print(f"   Found {len(category_links)} category links")

                if category_links:
                    # Click first category
                    category_links[0].click()
                    time.sleep(3)

                    # Now look for manuscripts
                    take_actions = driver.find_elements(
                        By.XPATH, "//img[contains(@src, 'check_off.gif')]"
                    )
                    print(f"   Found {len(take_actions)} manuscripts in category")
        else:
            print("   ❌ Login failed - still on login page")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Save results
        output = {
            "extraction_time": datetime.now().isoformat(),
            "manuscripts": manuscripts,
            "total": len(manuscripts),
        }

        with open("mor_undetected_results.json", "w") as f:
            json.dump(output, f, indent=2)

        print("\n📊 RESULTS:")
        print(f"   Total manuscripts found: {len(manuscripts)}")
        for ms in manuscripts:
            print(f"   - {ms['id']}: {ms.get('title', 'Unknown')[:50]}...")

        driver.quit()

    return manuscripts


if __name__ == "__main__":
    results = run_extraction()
    print(f"\n✅ Complete: {len(results)} manuscripts")

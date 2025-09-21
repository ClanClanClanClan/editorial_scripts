#!/usr/bin/env python3
"""
Test MF navigation flow to ensure proper sequence
"""

import os

# Add parent directory to path
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

sys.path.append(str(Path(__file__).parent.parent))

from src.core.secure_credentials import SecureCredentialManager


def test_navigation():
    """Test navigation to manuscript page"""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    try:
        # Load credentials
        print("🔐 Loading credentials...")
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()
        os.environ["MF_EMAIL"] = email
        os.environ["MF_PASSWORD"] = password

        # Login
        print("\n🔐 Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)

        # Reject cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        except:
            pass

        # Login
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.execute_script("document.getElementById('logInButton').click();")
        time.sleep(5)

        # Handle 2FA
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("   📱 2FA required...")
            time.sleep(10)

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from core.gmail_verification_wrapper import fetch_latest_verification_code

            code = fetch_latest_verification_code("MF", max_wait=45)

            if code:
                print(f"   ✅ Got code: {code}")
                token_field.send_keys(code)
                driver.find_element(By.ID, "VERIFY_BTN").click()
                time.sleep(8)
        except Exception as e:
            print(f"   ℹ️ No 2FA or error: {e}")

        # Wait for main page
        print("\n⏳ Waiting for main page...")
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1

        print(f"   ✅ On main page: {driver.current_url}")

        # Navigate to AE Center
        print("\n📊 Step 1: Navigate to Associate Editor Center...")
        ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)
        print("   ✅ In AE Center")

        # Find categories
        print("\n📋 Step 2: Looking for manuscript categories...")
        category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting")
        print(f"   Found {len(category_links)} categories")
        for link in category_links:
            print(f"     - {link.text}")

        # Click on Awaiting Reviewer Scores
        print("\n📋 Step 3: Click on 'Awaiting Reviewer Scores'...")
        category_link = driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Scores")
        category_link.click()
        time.sleep(3)
        print("   ✅ In manuscript list")

        # Find Take Action links
        print("\n📄 Step 4: Find manuscripts...")
        take_action_links = driver.find_elements(By.LINK_TEXT, "Take Action")
        print(f"   Found {len(take_action_links)} manuscripts")

        if take_action_links:
            print("\n📄 Step 5: Click 'Take Action' for first manuscript...")
            take_action_links[0].click()
            time.sleep(3)
            print("   ✅ On manuscript page")

            # Check current location
            print(f"\n📍 Current URL: {driver.current_url}")
            print(f"   Page title: {driver.title}")

            # Look for referee table
            print("\n👥 Step 6: Looking for referee information...")

            # Check for referee table
            try:
                referee_table = driver.find_element(By.XPATH, "//td[@class='tablelines']//table")
                print("   ✅ Found referee table")

                # Count referee rows
                referee_rows = referee_table.find_elements(
                    By.XPATH, ".//tr[.//a[contains(@href,'mailpopup')]]"
                )
                print(f"   Found {len(referee_rows)} total rows with mailpopup links")

                # Filter actual referees
                actual_referees = []
                for row in referee_rows:
                    row_text = row.text.lower()
                    if (
                        "associate editor" not in row_text
                        and "author" not in row_text
                        and "editor" not in row_text
                    ):
                        actual_referees.append(row)
                        # Get referee name
                        name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                        print(f"     - Referee: {name_link.text}")

                print(f"   ✅ Found {len(actual_referees)} actual referees")

            except Exception as e:
                print(f"   ❌ Could not find referee table: {e}")

        print("\n✅ Navigation test complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n⏸️  Browser will close in 10 seconds...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    test_navigation()

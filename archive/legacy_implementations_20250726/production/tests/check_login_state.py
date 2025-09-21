#!/usr/bin/env python3
"""
Check what happens after login and find the correct navigation
"""

# Add parent directory to path
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

sys.path.append(str(Path(__file__).parent.parent))

from src.core.secure_credentials import SecureCredentialManager


def check_login_state():
    """Check post-login state and available links"""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    try:
        # Load credentials
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()

        # Login
        print("🔐 Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)

        # Check if we need to handle device authentication
        device_auth_elements = driver.find_elements(
            By.XPATH, "//h2[contains(text(), 'Device Authentication Required')]"
        )
        if device_auth_elements:
            print("⚠️ Device authentication required - handling...")
            # Look for "This is a private computer" option
            private_radio = driver.find_element(
                By.XPATH, "//input[@type='radio' and @value='private']"
            )
            private_radio.click()
            time.sleep(1)

            # Click Continue
            continue_btn = driver.find_element(
                By.XPATH, "//input[@type='submit' and @value='Continue']"
            )
            continue_btn.click()
            time.sleep(3)

        # Login
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.execute_script("document.getElementById('logInButton').click();")
        time.sleep(5)

        # Save page after login
        with open("post_login_page.html", "w") as f:
            f.write(driver.page_source)
        print("✅ Saved post-login page to post_login_page.html")

        # Check current URL
        print(f"\n📍 Current URL: {driver.current_url}")

        # Look for all links that might be the AE center
        print("\n🔍 Looking for navigation links...")

        # Try different patterns
        patterns = [
            "//a[contains(text(), 'Associate Editor')]",
            "//a[contains(text(), 'Associate Editor Center')]",
            "//a[contains(text(), 'AE Center')]",
            "//a[contains(@href, 'ASSOCIATE_EDITOR')]",
            "//a[contains(@href, 'AE_')]",
            "//td[@class='navtab']//a",
            "//div[@class='nav']//a",
        ]

        for pattern in patterns:
            links = driver.find_elements(By.XPATH, pattern)
            if links:
                print(f"\n✅ Found {len(links)} links with pattern: {pattern}")
                for i, link in enumerate(links[:5]):  # Show first 5
                    try:
                        text = link.text.strip()
                        href = link.get_attribute("href")
                        print(f"   Link {i+1}: '{text}' -> {href[:80]}...")
                    except:
                        pass

        # Also check for role selection
        print("\n🔍 Checking for role selection...")
        role_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ROLE')]")
        if role_links:
            print(f"Found {len(role_links)} role links:")
            for link in role_links:
                print(f"   - {link.text}")

        # Check page title
        print(f"\n📄 Page title: {driver.title}")

        # Check if we're on a dashboard
        dashboard_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Dashboard')]")
        if dashboard_elements:
            print("\n✅ Found dashboard elements")

        # Look for manuscript-related links
        print("\n🔍 Looking for manuscript links...")
        manuscript_links = driver.find_elements(
            By.XPATH, "//a[contains(@href, 'manuscript') or contains(@href, 'MANUSCRIPT')]"
        )
        if manuscript_links:
            print(f"Found {len(manuscript_links)} manuscript-related links")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n⏸️  Browser will close in 10 seconds...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    check_login_state()

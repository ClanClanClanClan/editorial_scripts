#!/usr/bin/env python3
"""
Debug what page we're on after login
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


def debug_post_login():
    """Debug the post-login state"""

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

        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        except:
            pass

        # Login
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.execute_script("document.getElementById('logInButton').click();")

        # Wait for navigation
        print("⏳ Waiting for login...")
        time.sleep(8)

        # Debug current state
        print(f"\n📍 Current URL: {driver.current_url}")
        print(f"📄 Page title: {driver.title}")

        # Check for various indicators
        indicators = {
            "Login page": ["Log In", "Sign In", "Password", "USERID"],
            "2FA page": ["Verification", "TOKEN", "code", "verify"],
            "Dashboard": ["Dashboard", "Welcome", "Manuscripts"],
            "Role selection": ["Select Role", "Choose Role", "Associate Editor", "Author"],
        }

        page_text = driver.page_source.lower()
        for page_type, keywords in indicators.items():
            if any(keyword.lower() in page_text for keyword in keywords):
                print(f"✅ Detected: {page_type}")

        # List all visible links
        print("\n🔗 Visible links (first 20):")
        links = driver.find_elements(By.TAG_NAME, "a")
        visible_links = []
        for link in links:
            text = link.text.strip()
            href = link.get_attribute("href")
            if text and link.is_displayed():
                visible_links.append((text, href))

        for i, (text, href) in enumerate(visible_links[:20]):
            print(f"   {i+1}. '{text}' -> {href[:80] if href else 'None'}...")

        # Look specifically for manuscript/role links
        print("\n🎯 Looking for key navigation:")
        key_patterns = [
            ("Associate Editor", "//a[contains(text(), 'Associate Editor')]"),
            ("Manuscripts", "//a[contains(text(), 'Manuscript')]"),
            ("Submissions", "//a[contains(text(), 'Submission')]"),
            ("Dashboard", "//a[contains(text(), 'Dashboard')]"),
            ("Role", "//a[contains(@href, 'ROLE')]"),
        ]

        for name, xpath in key_patterns:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                print(f"   ✅ Found {len(elements)} '{name}' links")
                for elem in elements[:2]:
                    print(f"      - '{elem.text.strip()}'")

        # Save page
        with open("debug_after_login.html", "w") as f:
            f.write(driver.page_source)
        print("\n💾 Saved page to debug_after_login.html")

        # Check if we need to handle 2FA
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("\n⚠️ 2FA Required! Need to enter verification code.")
            print("   The extractor should handle this automatically with Gmail integration.")
        except:
            pass

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n⏸️  Press Enter to close...")
        input()
        driver.quit()


if __name__ == "__main__":
    debug_post_login()

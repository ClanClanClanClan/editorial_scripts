#!/usr/bin/env python3
"""
Debug the navigation flow to see where it breaks
"""

import os
import sys
import time
from pathlib import Path

# Add path to import the MF extractor
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials

    load_credentials()
except ImportError:
    from dotenv import load_dotenv

    load_dotenv(".env.production")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def debug_navigation():
    """Debug navigation step by step"""
    print("🔍 Debugging navigation flow...")

    # Create Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # Step 1: Initial page load
        print("\n1️⃣ Loading MF site...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        print(f"   Current URL: {driver.current_url}")
        print(f"   Page title: {driver.title}")

        # Step 2: Handle cookie banner
        print("\n2️⃣ Handling cookie banner...")
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            print("   ✅ Cookie banner rejected")
        except:
            print("   ℹ️ No cookie banner found")

        # Step 3: Clear and fill login fields
        print("\n3️⃣ Filling login credentials...")
        try:
            userid_field = driver.find_element(By.ID, "USERID")
            password_field = driver.find_element(By.ID, "PASSWORD")

            userid_field.clear()
            password_field.clear()
            time.sleep(0.5)

            email = os.getenv("MF_EMAIL")
            password = os.getenv("MF_PASSWORD")

            if not email or not password:
                print("   ❌ Environment variables not loaded properly")
                print(f"   MF_EMAIL: {'Set' if email else 'Not set'}")
                print(f"   MF_PASSWORD: {'Set' if password else 'Not set'}")
                return

            userid_field.send_keys(email)
            password_field.send_keys(password)
            print("   ✅ Credentials entered")
        except Exception as e:
            print(f"   ❌ Error entering credentials: {e}")
            return

        # Step 4: Click login
        print("\n4️⃣ Clicking login button...")
        try:
            driver.execute_script("document.getElementById('logInButton').click();")
            time.sleep(3)
            print(f"   Current URL: {driver.current_url}")
        except Exception as e:
            print(f"   ❌ Error clicking login: {e}")
            return

        # Step 5: Handle 2FA (skipping the actual code entry for debugging)
        print("\n5️⃣ Checking for 2FA...")
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("   📱 2FA page detected - skipping for debug")
            print(f"   Current URL: {driver.current_url}")
            # Would normally handle 2FA here
            return
        except:
            print("   ℹ️ No 2FA required or already passed")

        # Step 6: Check current page after login
        print("\n6️⃣ Checking post-login page...")
        print(f"   Current URL: {driver.current_url}")
        print(f"   Page title: {driver.title}")

        # Look for key elements that should be present
        print("\n   Looking for navigation elements:")

        # Check for Associate Editor link
        ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
        print(f"   Associate Editor links found: {len(ae_links)}")
        for i, link in enumerate(ae_links[:3]):
            print(f"      {i+1}. Text: '{link.text}' | Href: {link.get_attribute('href')}")

        # Check for Author Center link
        author_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Author Center')]")
        print(f"   Author Center links found: {len(author_links)}")

        # Check for any role selection
        role_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ROLE_ID')]")
        print(f"   Role selection links found: {len(role_links)}")
        for i, link in enumerate(role_links[:3]):
            print(f"      {i+1}. Text: '{link.text}' | Href: {link.get_attribute('href')}")

        # Check for frames
        frames = driver.find_elements(By.TAG_NAME, "frame")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"   Frames found: {len(frames)}")
        print(f"   IFrames found: {len(iframes)}")

        # Save page source for analysis
        print("\n7️⃣ Saving page source...")
        with open("debug_navigation_page.html", "w") as f:
            f.write(driver.page_source)
        print("   ✅ Saved to debug_navigation_page.html")

        # Try the actual navigation
        print("\n8️⃣ Attempting to navigate to AE Center...")

        # Method 1: Direct link
        try:
            ae_link = driver.find_element(
                By.XPATH, "//a[contains(text(), 'Associate Editor Center')]"
            )
            print(f"   Found AE Center link: {ae_link.text}")
            ae_link.click()
            time.sleep(3)
            print("   ✅ Clicked AE Center link")
            print(f"   New URL: {driver.current_url}")
        except Exception as e:
            print(f"   ❌ Method 1 failed: {e}")

            # Method 2: Role selection
            try:
                print("\n   Trying role selection method...")
                role_link = driver.find_element(
                    By.XPATH,
                    "//a[contains(@href, 'ROLE_ID=') and contains(@href, 'ASSOCIATE_EDITOR')]",
                )
                print(f"   Found role link: {role_link.get_attribute('href')}")
                role_link.click()
                time.sleep(3)
                print("   ✅ Clicked role selection link")
                print(f"   New URL: {driver.current_url}")
            except Exception as e2:
                print(f"   ❌ Method 2 failed: {e2}")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🔚 Debug complete. Browser will stay open for 10 seconds...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    debug_navigation()

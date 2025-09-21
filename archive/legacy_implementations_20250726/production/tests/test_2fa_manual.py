#!/usr/bin/env python3
"""
Test 2FA manually by entering code
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


def test_2fa_manual():
    """Test 2FA with manual code entry"""

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
        print("🔐 Step 1: Logging in...")
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

        # Wait for 2FA page
        print("⏳ Waiting for 2FA page...")
        time.sleep(5)

        # Check if we're on 2FA page
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("\n✅ 2FA page detected!")
            print("📧 Check your email for the verification code")

            # Manual code entry
            code = input("\n🔢 Enter the 6-digit code from your email: ").strip()

            if len(code) == 6 and code.isdigit():
                print(f"   Entering code: {code}")
                token_field.clear()
                token_field.send_keys(code)

                # Click verify
                verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                verify_btn.click()

                print("   ✅ Clicked verify, waiting...")
                time.sleep(5)

                # Check if we got past 2FA
                current_url = driver.current_url
                print(f"\n📍 Current URL: {current_url}")

                # Look for AE Center
                print("\n🔍 Looking for Associate Editor Center...")
                ae_links = driver.find_elements(
                    By.XPATH, "//a[contains(text(), 'Associate Editor')]"
                )
                if ae_links:
                    print(f"   ✅ Found {len(ae_links)} AE links!")
                    for link in ae_links:
                        print(f"      - {link.text}")

                    # Click first one
                    ae_links[0].click()
                    time.sleep(3)

                    # Look for manuscripts
                    print("\n📄 Looking for manuscripts...")
                    manuscript_links = driver.find_elements(
                        By.XPATH, "//a[contains(@href, 'CURRENT_STAGE_ID=')]"
                    )
                    print(f"   Found {len(manuscript_links)} manuscripts")

                    if manuscript_links:
                        print("   ✅ SUCCESS! We can see manuscripts!")
                        for i, link in enumerate(manuscript_links[:3]):
                            print(f"      {i+1}. {link.text}")
                else:
                    print("   ❌ No AE Center link found")

                    # Debug what's on the page
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    text_links = [l.text.strip() for l in all_links if l.text.strip()]
                    print(f"\n   Available links: {text_links[:15]}")

            else:
                print("❌ Invalid code format")

        except Exception as e:
            print(f"❌ Not on 2FA page or error: {e}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        input("\n⏸️  Press Enter to close...")
        driver.quit()


if __name__ == "__main__":
    test_2fa_manual()

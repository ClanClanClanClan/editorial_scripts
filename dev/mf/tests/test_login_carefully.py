#!/usr/bin/env python3
"""
TEST LOGIN CAREFULLY - More careful verification of login success
================================================================
"""

import sys
import time
import os
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoAlertPresentException

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

def handle_alert(driver):
    """Handle any alert that might be present."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"   ⚠️ Alert: {alert_text}")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False

print("🔍 TESTING MF LOGIN CAREFULLY")
print("=" * 70)

# Create debug directory
debug_dir = Path(__file__).parent.parent / 'debug'
debug_dir.mkdir(exist_ok=True)

mf = ComprehensiveMFExtractor()

print("\n📍 Navigating to MF...")
mf.driver.get("https://mc.manuscriptcentral.com/mafi")
time.sleep(5)

# Handle cookie banner
try:
    reject_btn = mf.driver.find_element(By.ID, "onetrust-reject-all-handler")
    reject_btn.click()
    print("✅ Cookie banner dismissed")
    time.sleep(1)
except:
    print("ℹ️ No cookie banner")

# Enter credentials
email = os.getenv('MF_EMAIL')
password = os.getenv('MF_PASSWORD')

print(f"\n📝 Entering credentials...")
userid_field = mf.driver.find_element(By.ID, "USERID")
password_field = mf.driver.find_element(By.ID, "PASSWORD")

userid_field.clear()
userid_field.send_keys(email)
password_field.clear()
password_field.send_keys(password)

# Click login
login_start_time = time.time()
print(f"🔐 Clicking login at: {datetime.fromtimestamp(login_start_time).strftime('%H:%M:%S')}")

login_button = mf.driver.find_element(By.ID, "logInButton")
login_button.click()

# Wait and handle any alerts
time.sleep(3)
handle_alert(mf.driver)

# Check for 2FA
print("\n🔍 Checking for 2FA...")
try:
    token_field = mf.driver.find_element(By.ID, "TOKEN_VALUE")
    print("📱 2FA required!")

    # Get code
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src'))
    from core.gmail_verification_wrapper import fetch_latest_verification_code

    time.sleep(10)
    code = fetch_latest_verification_code('MF', max_wait=30, poll_interval=2, start_timestamp=login_start_time)

    if code:
        print(f"✅ Got code: {code[:3]}***")
        token_field.send_keys(code)

        # Find verify button - check multiple possibilities
        verify_clicked = False

        # Try VERIFY_BTN
        try:
            verify_btn = mf.driver.find_element(By.ID, "VERIFY_BTN")
            print("   Found VERIFY_BTN, clicking...")
            verify_btn.click()
            verify_clicked = True
        except:
            print("   No VERIFY_BTN found")

        # Try submitButton
        if not verify_clicked:
            try:
                submit_btn = mf.driver.find_element(By.ID, "submitButton")
                print("   Found submitButton, clicking...")
                submit_btn.click()
                verify_clicked = True
            except:
                print("   No submitButton found")

        # Try any button with Verify text
        if not verify_clicked:
            try:
                verify_btn = mf.driver.find_element(By.XPATH, "//button[contains(text(), 'Verify')]")
                print("   Found Verify button by text, clicking...")
                verify_btn.click()
                verify_clicked = True
            except:
                print("   No Verify button found by text")

        # As last resort, press Enter
        if not verify_clicked:
            print("   Pressing Enter to submit...")
            token_field.send_keys(Keys.RETURN)

        print("⏳ Waiting for 2FA to complete...")
        time.sleep(10)

        # Handle any alerts after 2FA
        for _ in range(3):
            if handle_alert(mf.driver):
                time.sleep(2)

except Exception as e:
    print(f"ℹ️ No 2FA or different flow: {e}")

# Now check actual login status
print("\n🔍 VERIFYING LOGIN STATUS...")
current_url = mf.driver.current_url
print(f"   URL: {current_url}")

# Take screenshot
screenshot = debug_dir / 'login_status.png'
mf.driver.save_screenshot(str(screenshot))
print(f"   📸 Screenshot: {screenshot}")

# Check for login page elements (should NOT be present if logged in)
login_indicators = {
    "USERID field": (By.ID, "USERID"),
    "PASSWORD field": (By.ID, "PASSWORD"),
    "logInButton": (By.ID, "logInButton"),
    "Create Account link": (By.LINK_TEXT, "Create An Account")
}

still_on_login = False
for name, locator in login_indicators.items():
    try:
        elem = mf.driver.find_element(*locator)
        if elem.is_displayed():
            print(f"   ❌ Still on login page - found {name}")
            still_on_login = True
    except:
        pass

if still_on_login:
    print("\n❌ LOGIN FAILED - Still on login page!")
else:
    print("\n✅ No login elements found")

# Check for logged-in indicators
logged_in_indicators = {
    "Log Out link": (By.PARTIAL_LINK_TEXT, "Log Out"),
    "Logout link": (By.PARTIAL_LINK_TEXT, "Logout"),
    "Associate Editor": (By.PARTIAL_LINK_TEXT, "Associate Editor"),
    "Manuscripts link": (By.PARTIAL_LINK_TEXT, "Manuscripts"),
    "Author Dashboard": (By.PARTIAL_LINK_TEXT, "Author"),
    "Welcome message": (By.XPATH, "//*[contains(text(), 'Welcome')]")
}

logged_in = False
for name, locator in logged_in_indicators.items():
    try:
        elem = mf.driver.find_element(*locator)
        print(f"   ✅ Found logged-in indicator: {name}")
        logged_in = True
        break
    except:
        pass

if logged_in:
    print("\n✅ LOGIN SUCCESSFUL!")

    # Find all links to see what's available
    print("\n📋 Available links:")
    all_links = mf.driver.find_elements(By.TAG_NAME, "a")
    for link in all_links[:30]:
        text = link.text.strip()
        if text and len(text) > 2:
            print(f"   • {text}")
else:
    print("\n❌ No logged-in indicators found")

# Save page source
with open(debug_dir / 'login_status.html', 'w') as f:
    f.write(mf.driver.page_source)
print(f"\n💾 Page source saved: {debug_dir / 'login_status.html'}")

print("\n🧹 Cleaning up...")
mf.cleanup()
print("✅ Test complete")
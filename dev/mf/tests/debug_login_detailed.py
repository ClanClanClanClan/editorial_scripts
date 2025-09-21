#!/usr/bin/env python3
"""
DEBUG LOGIN DETAILED - See exactly what happens during login
===========================================================
"""

import sys
import time
import os
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

print("🔍 DEBUGGING MF LOGIN IN DETAIL")
print("=" * 70)

# Create debug directory
debug_dir = Path(__file__).parent.parent / 'debug'
debug_dir.mkdir(exist_ok=True)

mf = ComprehensiveMFExtractor()

print("\n📍 Initial navigation to MF...")
mf.driver.get("https://mc.manuscriptcentral.com/mafi")
time.sleep(5)

# Take screenshot of initial page
screenshot_path = debug_dir / 'login_1_initial.png'
mf.driver.save_screenshot(str(screenshot_path))
print(f"📸 Screenshot 1: {screenshot_path}")
print(f"   URL: {mf.driver.current_url}")
print(f"   Title: {mf.driver.title}")

# Handle cookie banner
try:
    reject_btn = mf.driver.find_element(By.ID, "onetrust-reject-all-handler")
    reject_btn.click()
    print("✅ Cookie banner dismissed")
    time.sleep(1)
except:
    print("ℹ️ No cookie banner found")

# Check if login form is present
try:
    userid_field = mf.driver.find_element(By.ID, "USERID")
    password_field = mf.driver.find_element(By.ID, "PASSWORD")
    login_button = mf.driver.find_element(By.ID, "logInButton")
    print("✅ Found login form elements")
except Exception as e:
    print(f"❌ Login form not found: {e}")
    # Save page source for debugging
    with open(debug_dir / 'login_page_source.html', 'w') as f:
        f.write(mf.driver.page_source)
    mf.cleanup()
    exit(1)

# Enter credentials
email = os.getenv('MF_EMAIL')
password = os.getenv('MF_PASSWORD')

if not email or not password:
    print("❌ Missing credentials in environment")
    mf.cleanup()
    exit(1)

print(f"\n📝 Entering credentials...")
print(f"   Email: {email[:5]}...@{email.split('@')[1]}")

userid_field.clear()
userid_field.send_keys(email)
password_field.clear()
password_field.send_keys(password)

# Take screenshot with credentials filled
screenshot_path = debug_dir / 'login_2_credentials.png'
mf.driver.save_screenshot(str(screenshot_path))
print(f"📸 Screenshot 2: {screenshot_path}")

# Record timestamp for 2FA
login_start_time = time.time()
print(f"\n🔐 Clicking login at: {datetime.fromtimestamp(login_start_time).strftime('%H:%M:%S')}")

# Click login
try:
    login_button.click()
    print("✅ Login button clicked")
except:
    print("⚠️ Regular click failed, trying JavaScript...")
    mf.driver.execute_script("document.getElementById('logInButton').click();")
    print("✅ JavaScript click executed")

# Wait for page to load
print("⏳ Waiting for response...")
time.sleep(5)

# Check what happened
screenshot_path = debug_dir / 'login_3_after_click.png'
mf.driver.save_screenshot(str(screenshot_path))
print(f"\n📸 Screenshot 3: {screenshot_path}")
print(f"   URL: {mf.driver.current_url}")
print(f"   Title: {mf.driver.title}")

# Check for 2FA
try:
    token_field = mf.driver.find_element(By.ID, "TOKEN_VALUE")
    print("\n📱 2FA detected! TOKEN_VALUE field found")

    # Try to get verification code
    print("📧 Attempting to fetch verification code from Gmail...")

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src'))
    from core.gmail_verification_wrapper import fetch_latest_verification_code

    # Wait for email to arrive
    time.sleep(10)

    code = fetch_latest_verification_code('MF', max_wait=30, poll_interval=2, start_timestamp=login_start_time)

    if code:
        print(f"✅ Got code: {code[:3]}***")
        token_field.send_keys(code)

        # Take screenshot with code entered
        screenshot_path = debug_dir / 'login_4_2fa_code.png'
        mf.driver.save_screenshot(str(screenshot_path))
        print(f"📸 Screenshot 4: {screenshot_path}")

        # Find and click verify button
        try:
            verify_btn = mf.driver.find_element(By.ID, "VERIFY_BTN")
            print("✅ Found VERIFY_BTN")
            verify_btn.click()
            print("✅ Clicked verify button")
        except Exception as e:
            print(f"❌ Could not find/click VERIFY_BTN: {e}")
            # Try alternative approaches
            try:
                token_field.submit()
                print("✅ Submitted form via token field")
            except:
                print("❌ Could not submit 2FA form")

        # Wait for verification
        print("⏳ Waiting for 2FA verification...")
        time.sleep(8)

        # Check result
        screenshot_path = debug_dir / 'login_5_after_2fa.png'
        mf.driver.save_screenshot(str(screenshot_path))
        print(f"\n📸 Screenshot 5: {screenshot_path}")
        print(f"   URL: {mf.driver.current_url}")
        print(f"   Title: {mf.driver.title}")
    else:
        print("❌ Could not fetch verification code")

except Exception as e:
    print(f"\nℹ️ No 2FA required or different flow: {e}")

# Final check for login success
print("\n🔍 Checking for login success indicators...")

# Check URL
current_url = mf.driver.current_url
if "login" not in current_url.lower() and "mafi" in current_url:
    print(f"✅ URL indicates success: {current_url}")
else:
    print(f"❌ URL still contains login: {current_url}")

# Check for logout link
logout_found = False
for text in ["Log Out", "Logout", "Sign Out"]:
    try:
        element = mf.driver.find_element(By.PARTIAL_LINK_TEXT, text)
        print(f"✅ Found logout link: {text}")
        logout_found = True
        break
    except:
        pass

if not logout_found:
    print("❌ No logout link found")

# Check for navigation elements
nav_elements = [
    "Associate Editor",
    "Editor Center",
    "Manuscripts",
    "All Manuscripts",
    "Dashboard"
]

print("\n🔍 Looking for navigation elements...")
for nav_text in nav_elements:
    try:
        element = mf.driver.find_element(By.PARTIAL_LINK_TEXT, nav_text)
        print(f"   ✅ Found: {nav_text}")
    except:
        print(f"   ❌ Not found: {nav_text}")

# Save final page source
with open(debug_dir / 'login_final_page.html', 'w') as f:
    f.write(mf.driver.page_source)
print(f"\n💾 Saved final page source to: {debug_dir / 'login_final_page.html'}")

# Take final screenshot
screenshot_path = debug_dir / 'login_6_final.png'
mf.driver.save_screenshot(str(screenshot_path))
print(f"📸 Final screenshot: {screenshot_path}")

print("\n🧹 Cleaning up...")
mf.cleanup()
print("✅ Debug complete")
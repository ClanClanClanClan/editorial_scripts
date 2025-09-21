#!/usr/bin/env python3
"""
MOR DIRECT VERIFY - CLICK THE BLUE VERIFY BUTTON
"""

import sys
import os
import time
import re
import json

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR DIRECT VERIFY - CLICK THE ACTUAL BLUE BUTTON")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "login_successful": False,
    "categories_found": [],
    "total_manuscripts": 0
}

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(5)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        pass

    # Login
    print("\n3. Login")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Credentials submitted")

    # Handle 2FA
    print("\n4. 2FA Handling - DIRECT BUTTON CLICK")
    print("-"*40)

    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   ✅ 2FA dialog detected")

        # Get fresh code
        print("   Fetching verification code...")
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   ✅ Got code: {code}")

            # Enter code
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            print("   ✅ Code entered")

            # DIRECT BUTTON CLICK METHODS
            print("\n   🎯 Finding and clicking Verify button...")

            # Method 1: Click button by class and text
            try:
                verify_button = driver.find_element(By.CSS_SELECTOR, "button.btn-primary")
                print(f"      Found button: '{verify_button.text}'")
                verify_button.click()
                print("      ✅ Clicked primary button!")
            except Exception as e:
                print(f"      Method 1 failed: {e}")

                # Method 2: Click any button with Verify text
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "verify" in btn.text.lower():
                            print(f"      Found button with text: '{btn.text}'")
                            btn.click()
                            print("      ✅ Clicked Verify button!")
                            break
                except Exception as e2:
                    print(f"      Method 2 failed: {e2}")

                    # Method 3: JavaScript click on visible button
                    try:
                        driver.execute_script("""
                            var buttons = document.querySelectorAll('button');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent !== null && btn.innerText.toLowerCase().includes('verify')) {
                                    console.log('Clicking button:', btn.innerText);
                                    btn.click();
                                    return 'clicked: ' + btn.innerText;
                                }
                            }
                            return 'no verify button found';
                        """)
                        print("      ✅ JavaScript clicked Verify!")
                    except Exception as e3:
                        print(f"      Method 3 failed: {e3}")

                        # Method 4: Submit via Enter key
                        try:
                            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                            token_field.send_keys(Keys.RETURN)
                            print("      ✅ Pressed Enter in field")
                        except:
                            pass

            time.sleep(15)  # Wait longer for login to complete

    # Check login success
    print("\n5. Login Verification")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title
    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    # Check if 2FA is gone
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ❌ 2FA still visible - trying to find AE link anyway...")
    except:
        print("   ✅ 2FA dialog closed")
        RESULTS["login_successful"] = True

    # Navigate to AE Center
    print("\n6. Find Associate Editor Center")
    print("-"*40)

    # Refresh if needed
    if not RESULTS["login_successful"]:
        print("   Refreshing page...")
        driver.refresh()
        time.sleep(5)

    # Find AE link
    all_links = driver.find_elements(By.TAG_NAME, "a")
    ae_link = None

    print(f"   Found {len(all_links)} total links")

    for link in all_links:
        try:
            text = link.text.strip()
            href = link.get_attribute("href")
            if text:
                if "editor" in text.lower():
                    print(f"   ✅ Found editor link: {text}")
                    ae_link = link
                    break
        except:
            pass

    if ae_link:
        ae_link.click()
        time.sleep(5)
        print("   ✅ Navigated to Editor Center")

        # Find categories
        print("\n7. Find Categories")
        categories = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            text = link.text.strip()
            if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment']):
                categories.append({
                    "text": text,
                    "href": link.get_attribute("href")
                })
                print(f"   Found: {text}")

        RESULTS["categories_found"] = [c["text"] for c in categories]

        # Extract manuscripts
        print("\n8. Extract Manuscripts")
        print("-"*40)

        for cat in categories[:2]:
            print(f"\n📁 Category: {cat['text']}")

            driver.get(cat["href"])
            time.sleep(5)

            # Find manuscripts
            rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            print(f"   Found {len(rows)} manuscripts")

            for row in rows:
                ms_data = {"category": cat["text"]}

                # Extract ID
                mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                if mor_match:
                    ms_data["manuscript_id"] = mor_match.group()
                    print(f"\n   📄 {ms_data['manuscript_id']}")

                # Extract cells
                cells = row.find_elements(By.TAG_NAME, "td")
                for i, cell in enumerate(cells[:6]):
                    text = cell.text.strip()
                    if text:
                        if i == 2:  # Title
                            ms_data["title"] = text[:200]
                            print(f"      Title: {text[:80]}...")
                        elif "@" in text:
                            ms_data["author"] = text
                            print(f"      Author: {text[:50]}...")

                # Try popup
                try:
                    ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                    ms_link.click()
                    time.sleep(3)

                    if len(driver.window_handles) > 1:
                        original = driver.current_window_handle
                        driver.switch_to.window(driver.window_handles[-1])

                        popup_text = driver.find_element(By.TAG_NAME, "body").text

                        # Extract emails
                        emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', popup_text, re.IGNORECASE)
                        if emails:
                            ms_data["referee_emails"] = list(set(emails))
                            print(f"      Emails: {len(ms_data['referee_emails'])}")

                        # Close popup
                        driver.close()
                        driver.switch_to.window(original)
                except:
                    pass

                RESULTS["manuscripts"].append(ms_data)
                RESULTS["total_manuscripts"] += 1

            # Return to AE Center
            driver.back()
            time.sleep(3)

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    print(f"✅ Total manuscripts: {RESULTS['total_manuscripts']}")

    for ms in RESULTS["manuscripts"]:
        print(f"\n📄 {ms.get('manuscript_id', 'Unknown')}")
        print(f"   Category: {ms.get('category')}")
        if "title" in ms:
            print(f"   Title: {ms['title'][:100]}...")
        if "author" in ms:
            print(f"   Author: {ms['author'][:80]}...")
        if "referee_emails" in ms:
            print(f"   Referee emails: {len(ms['referee_emails'])}")
            for email in ms["referee_emails"][:3]:
                print(f"      - {email}")

    # Save results
    output_file = f"/tmp/mor_direct_verify_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_direct_verify_error.png")

finally:
    if driver:
        print("\nClosing in 20 seconds...")
        time.sleep(20)
        driver.quit()

print("\n" + "="*80)
print("DIRECT VERIFY COMPLETE")
print("="*80)
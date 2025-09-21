#!/usr/bin/env python3
"""
MOR CLICK BLUE VERIFY - SPECIFICALLY CLICK THE BLUE VERIFY BUTTON
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

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR CLICK BLUE VERIFY BUTTON")
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
    print("\n4. 2FA - CLICK THE BLUE VERIFY BUTTON")
    print("-"*40)

    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected")

        # Get code
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            print("   ✅ Code entered")

            # FIND AND CLICK THE BLUE VERIFY BUTTON
            print("\n   🎯 FINDING THE BLUE VERIFY BUTTON...")

            # Method 1: Click by CSS selector for primary button
            try:
                verify_btn = driver.find_element(By.CSS_SELECTOR, "button[type='button'].btn-primary")
                print(f"      Found button with text: '{verify_btn.text}'")
                driver.execute_script("arguments[0].click();", verify_btn)
                print("      ✅ CLICKED PRIMARY BUTTON!")
                time.sleep(10)
            except Exception as e:
                print(f"      Method 1 failed: {e}")

                # Method 2: Find button containing "Verify"
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        btn_text = btn.text.strip()
                        print(f"      Checking button: '{btn_text}'")
                        if "verify" in btn_text.lower():
                            print(f"      ✅ FOUND VERIFY BUTTON: '{btn_text}'")
                            driver.execute_script("arguments[0].click();", btn)
                            print("      ✅ CLICKED!")
                            time.sleep(10)
                            break
                except Exception as e2:
                    print(f"      Method 2 failed: {e2}")

                    # Method 3: Click any blue button
                    try:
                        blue_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-primary, button.btn-blue, button[style*='blue']")
                        print(f"      Found blue button: '{blue_btn.text}'")
                        blue_btn.click()
                        print("      ✅ CLICKED BLUE BUTTON!")
                        time.sleep(10)
                    except Exception as e3:
                        print(f"      Method 3 failed: {e3}")

                        # Method 4: Force click with JavaScript
                        try:
                            driver.execute_script("""
                                var allButtons = document.querySelectorAll('button');
                                for (var i = 0; i < allButtons.length; i++) {
                                    var btn = allButtons[i];
                                    if (btn.offsetParent !== null) {  // Is visible
                                        console.log('Button ' + i + ': ' + btn.textContent);
                                        if (btn.textContent.toLowerCase().includes('verify') ||
                                            btn.className.includes('primary')) {
                                            btn.click();
                                            return 'Clicked: ' + btn.textContent;
                                        }
                                    }
                                }
                                // If no verify button, click the last visible button (often submit)
                                for (var i = allButtons.length - 1; i >= 0; i--) {
                                    var btn = allButtons[i];
                                    if (btn.offsetParent !== null && btn.type !== 'button') {
                                        btn.click();
                                        return 'Clicked last: ' + btn.textContent;
                                    }
                                }
                                return 'No button clicked';
                            """)
                            print("      ✅ JavaScript forced click!")
                            time.sleep(10)
                        except Exception as e4:
                            print(f"      Method 4 failed: {e4}")

    # Wait and check login
    time.sleep(5)

    print("\n5. Check Login Status")
    current_url = driver.current_url
    print(f"   URL: {current_url}")

    # Check if 2FA is gone
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ❌ 2FA still visible")

            # Take screenshot to debug
            driver.save_screenshot("/tmp/mor_verify_button_debug.png")
            print("   📸 Debug screenshot: /tmp/mor_verify_button_debug.png")

            # List all buttons
            print("\n   ALL BUTTONS ON PAGE:")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for i, btn in enumerate(buttons):
                try:
                    print(f"   Button {i}: text='{btn.text}', class='{btn.get_attribute('class')}', visible={btn.is_displayed()}")
                except:
                    pass
    except:
        print("   ✅ 2FA gone - login successful!")
        RESULTS["login_successful"] = True

        # Navigate to AE Center
        print("\n6. Navigate to Associate Editor Center")

        all_links = driver.find_elements(By.TAG_NAME, "a")
        ae_link = None

        for link in all_links:
            text = link.text.strip()
            if text and "associate editor" in text.lower():
                ae_link = link
                print(f"   Found: {text}")
                break

        if ae_link:
            ae_link.click()
            time.sleep(5)
            print("   ✅ In AE Center")

            # Find categories
            categories = []
            for link in driver.find_elements(By.TAG_NAME, "a"):
                text = link.text.strip()
                if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment']):
                    categories.append(text)
                    RESULTS["categories_found"].append(text)
                    print(f"   Found category: {text}")

            # Extract manuscripts
            print("\n7. Extract Manuscripts")

            for cat in categories[:2]:  # First 2 categories
                print(f"\n📁 Category: {cat}")

                try:
                    link = driver.find_element(By.PARTIAL_LINK_TEXT, cat)
                    link.click()
                    time.sleep(5)

                    # Find manuscripts
                    page_source = driver.page_source
                    mor_ids = re.findall(r'MOR-\d{4}-\d{4}', page_source)

                    if mor_ids:
                        unique_ids = list(set(mor_ids))
                        print(f"   Found {len(unique_ids)} manuscripts")

                        for ms_id in unique_ids:
                            RESULTS["manuscripts"].append({
                                "id": ms_id,
                                "category": cat
                            })
                            RESULTS["total_manuscripts"] += 1
                            print(f"      📄 {ms_id}")

                    # Return to AE Center
                    driver.back()
                    time.sleep(3)

                except Exception as e:
                    print(f"   Error: {e}")

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    print(f"✅ Total manuscripts: {RESULTS['total_manuscripts']}")

    for ms in RESULTS["manuscripts"]:
        print(f"\n📄 {ms['id']}")
        print(f"   Category: {ms['category']}")

    # Save results
    output_file = f"/tmp/mor_blue_verify_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_blue_verify_error.png")

finally:
    if driver:
        print("\nClosing in 20 seconds...")
        time.sleep(20)
        driver.quit()

print("\n" + "="*80)
print("BLUE VERIFY CLICK COMPLETE")
print("="*80)
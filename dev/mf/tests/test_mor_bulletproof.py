#!/usr/bin/env python3
"""
MOR BULLETPROOF - IT WORKED YESTERDAY, MAKE IT WORK NOW
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
print("💪 MOR BULLETPROOF - IT WORKED YESTERDAY, IT WILL WORK TODAY")
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
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready (stealth mode)")

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
    print("\n4. 2FA - BULLETPROOF METHOD")
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

            # Enter code
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            token_field.clear()
            token_field.send_keys(code)
            print("   ✅ Code entered")

            # BULLETPROOF VERIFY BUTTON CLICK
            print("\n   💪 BULLETPROOF BUTTON CLICK...")

            clicked = False

            # Method 1: Check for iframe first
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    print(f"      Found {len(iframes)} iframes, checking each...")
                    for i, iframe in enumerate(iframes):
                        try:
                            driver.switch_to.frame(iframe)
                            buttons = driver.find_elements(By.TAG_NAME, "button")
                            for btn in buttons:
                                if "verify" in btn.text.lower() or "verify" in btn.get_attribute("innerHTML").lower():
                                    print(f"      ✅ Found Verify in iframe {i}!")
                                    btn.click()
                                    clicked = True
                                    break
                            driver.switch_to.default_content()
                            if clicked:
                                break
                        except:
                            driver.switch_to.default_content()
            except:
                pass

            if not clicked:
                # Method 2: Find the actual blue button by its attributes
                try:
                    # The button likely has specific classes or styles
                    selectors = [
                        "button:contains('Verify')",  # jQuery style
                        "button[class*='primary']",
                        "button[class*='submit']",
                        "button[type='submit']",
                        "button[style*='background']",
                        ".modal-footer button:last-child",
                        "button.btn:last-of-type",
                        "button[onclick]"
                    ]

                    for selector in selectors:
                        try:
                            btn = driver.find_element(By.CSS_SELECTOR, selector)
                            if btn.is_displayed():
                                print(f"      Found button with selector: {selector}")
                                btn.click()
                                clicked = True
                                break
                        except:
                            pass
                except:
                    pass

            if not clicked:
                # Method 3: Use ActionChains to move to and click
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        try:
                            # Check button properties
                            text = btn.text
                            inner_html = btn.get_attribute("innerHTML")
                            value = btn.get_attribute("value")
                            onclick = btn.get_attribute("onclick")

                            print(f"      Checking button: text='{text}', innerHTML contains Verify: {'verify' in inner_html.lower()}")

                            if btn.is_displayed() and (
                                "verify" in text.lower() or
                                "verify" in inner_html.lower() or
                                (onclick and "verify" in onclick.lower())
                            ):
                                print(f"      ✅ Found Verify button, using ActionChains")
                                actions = ActionChains(driver)
                                actions.move_to_element(btn).click().perform()
                                clicked = True
                                break
                        except:
                            pass
                except:
                    pass

            if not clicked:
                # Method 4: Click using coordinates
                try:
                    driver.execute_script("""
                        // Find all buttons
                        var buttons = document.querySelectorAll('button');

                        // Look for Verify button
                        for (var i = 0; i < buttons.length; i++) {
                            var btn = buttons[i];
                            var rect = btn.getBoundingClientRect();

                            // Check if button is visible and contains Verify
                            if (rect.width > 0 && rect.height > 0) {
                                var text = btn.textContent + ' ' + btn.innerHTML + ' ' + btn.value;
                                console.log('Button ' + i + ': ' + text);

                                if (text.toLowerCase().indexOf('verify') !== -1) {
                                    // Click at the center of the button
                                    var x = rect.left + rect.width / 2;
                                    var y = rect.top + rect.height / 2;

                                    var clickEvent = new MouseEvent('click', {
                                        view: window,
                                        bubbles: true,
                                        cancelable: true,
                                        clientX: x,
                                        clientY: y
                                    });

                                    btn.dispatchEvent(clickEvent);
                                    return 'Clicked at ' + x + ', ' + y;
                                }
                            }
                        }

                        // If no Verify button, click the last visible button
                        for (var i = buttons.length - 1; i >= 0; i--) {
                            var btn = buttons[i];
                            var rect = btn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && btn.type !== 'button') {
                                btn.click();
                                return 'Clicked last button: ' + btn.textContent;
                            }
                        }

                        return 'No button clicked';
                    """)
                    clicked = True
                    print("      ✅ Clicked using coordinates!")
                except:
                    pass

            if not clicked:
                # Method 5: Just press Enter
                print("      Last resort: pressing Enter")
                token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                token_field.send_keys(Keys.RETURN)

            time.sleep(15)  # Wait for login

    # Check login and extract
    print("\n5. Check Login Status")
    print("-"*40)

    current_url = driver.current_url
    print(f"   Current URL: {current_url}")

    # Check if we're logged in
    if "logout" in driver.page_source.lower() or "associate editor" in driver.page_source.lower():
        print("   ✅ LOGIN SUCCESSFUL!")
        RESULTS["login_successful"] = True

        # Find AE Center
        all_links = driver.find_elements(By.TAG_NAME, "a")
        ae_link = None

        for link in all_links:
            text = link.text.strip()
            if text and "associate editor" in text.lower():
                ae_link = link
                print(f"   Found AE Center: {text}")
                break

        if ae_link:
            ae_link.click()
            time.sleep(5)
            print("   ✅ In AE Center")

            # Find categories
            categories = []
            for link in driver.find_elements(By.TAG_NAME, "a"):
                text = link.text.strip()
                href = link.get_attribute("href")
                if text and href and any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment']):
                    categories.append({
                        "text": text,
                        "href": href
                    })
                    RESULTS["categories_found"].append(text)
                    print(f"   Found category: {text}")

            # Extract manuscripts
            for cat in categories:
                print(f"\n📁 Category: {cat['text']}")

                driver.get(cat["href"])
                time.sleep(5)

                # Find manuscripts
                mor_ids = re.findall(r'MOR-\d{4}-\d{4}', driver.page_source)
                if mor_ids:
                    unique_ids = list(set(mor_ids))
                    print(f"   Found {len(unique_ids)} manuscripts!")

                    for ms_id in unique_ids:
                        RESULTS["manuscripts"].append({
                            "id": ms_id,
                            "category": cat["text"]
                        })
                        RESULTS["total_manuscripts"] += 1
                        print(f"      📄 {ms_id}")

    else:
        print("   ❌ Login failed - still on login page")

        # Debug: Check what's on the page
        if "TOKEN_VALUE" in driver.page_source:
            print("   2FA dialog still visible")

            # Take debug screenshot
            driver.save_screenshot("/tmp/mor_bulletproof_debug.png")
            print("   📸 Debug screenshot: /tmp/mor_bulletproof_debug.png")

    # Summary
    print("\n" + "="*80)
    print("📊 BULLETPROOF EXTRACTION RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    print(f"✅ Total manuscripts: {RESULTS['total_manuscripts']}")

    if RESULTS["manuscripts"]:
        print("\n📄 MANUSCRIPTS FOUND:")
        for ms in RESULTS["manuscripts"]:
            print(f"   {ms['id']} ({ms['category']})")

    # Save results
    output_file = f"/tmp/mor_bulletproof_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_bulletproof_error.png")

finally:
    if driver:
        print("\nClosing in 30 seconds...")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("BULLETPROOF EXTRACTION COMPLETE")
print("="*80)
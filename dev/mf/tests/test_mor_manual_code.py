#!/usr/bin/env python3
"""
MOR EXTRACTION WITH MANUAL CODE ENTRY
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
from selenium.common.exceptions import TimeoutException

print("="*80)
print("🎯 MOR EXTRACTION WITH MANUAL CODE")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "login_successful": False,
    "categories_found": []
}

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies handled")
    except:
        pass

    # Login
    print("\n3. Login")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))

    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Credentials submitted")

    # Wait for 2FA page
    time.sleep(5)

    # Handle 2FA with manual code
    print("\n4. 2FA Handling")
    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   ✅ 2FA page detected")

        # Use the most recent code we found
        code = "820758"  # Latest fresh code
        print(f"   Using code: {code}")

        # Try multiple methods to enter and submit
        try:
            # Method 1: Direct field entry
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            token_field.clear()
            token_field.send_keys(code)
            print("   ✅ Code entered in field")
        except:
            # Method 2: JavaScript
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            print("   ✅ Code set via JavaScript")

        # Click verify button - try multiple methods
        clicked = False

        # Try normal click
        try:
            verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
            verify_btn.click()
            clicked = True
            print("   ✅ Clicked VERIFY_BTN normally")
        except:
            pass

        # Try JavaScript click
        if not clicked:
            try:
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                clicked = True
                print("   ✅ Clicked via JavaScript")
            except:
                pass

        # Try clicking Verify button by xpath
        if not clicked:
            try:
                verify_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Verify')]")
                verify_btn.click()
                clicked = True
                print("   ✅ Clicked Verify button by text")
            except:
                pass

        # Try form submit
        if not clicked:
            try:
                driver.execute_script("document.forms[0].submit();")
                print("   ✅ Submitted form")
            except:
                pass

        print("   Waiting for login to complete...")
        time.sleep(10)

    # Check if logged in
    print("\n5. Verify Login")
    current_url = driver.current_url
    page_title = driver.title

    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    if "login" in current_url.lower():
        print("   ❌ Still on login page!")
        driver.save_screenshot("/tmp/mor_still_login.png")
        raise Exception("Login failed")

    print("   ✅ Logged in successfully!")
    RESULTS["login_successful"] = True

    # Wait for page to fully load
    print("   Waiting for page content to load...")
    time.sleep(5)

    # Try refreshing if page is blank
    if not driver.find_elements(By.TAG_NAME, "a") or len(driver.find_elements(By.TAG_NAME, "a")) < 5:
        print("   Page appears empty, refreshing...")
        driver.refresh()
        time.sleep(5)

    # Navigate to AE Center
    print("\n6. Navigate to Associate Editor Center")

    # Find all links and display them
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"   Found {len(all_links)} links on page")

    # Print first 20 links to see what's available
    print("   Available links:")
    for i, link in enumerate(all_links[:20], 1):
        link_text = link.text.strip()
        if link_text:
            print(f"   {i}. {link_text}")

    # Find AE link
    ae_link = None
    for link in all_links:
        link_text = link.text.strip().lower()
        # Look for various editor-related keywords
        if any(kw in link_text for kw in ["associate editor", "editor center", "ae center", "editor"]):
            ae_link = link
            print(f"\n   ✅ Found editor link: {link.text}")
            break

    if ae_link:
        ae_link.click()
        time.sleep(5)
        print("   ✅ Navigated to Editor Center")
    else:
        print("   ❌ No Editor link found")
        driver.save_screenshot("/tmp/mor_no_editor_link.png")
        raise Exception("Cannot find Editor Center")

    # Find categories
    print("\n7. Find Categories")
    categories = []

    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
            if 'Report' not in text or 'Reviewer' in text:
                categories.append({
                    "text": text,
                    "element": link,
                    "href": link.get_attribute("href")
                })
                print(f"   Found: {text}")

    RESULTS["categories_found"] = [c["text"] for c in categories]

    # Extract manuscripts
    print("\n8. Extract Manuscripts")
    print("-"*40)

    for i, cat in enumerate(categories[:2], 1):  # Process first 2 categories
        print(f"\nCategory {i}: {cat['text']}")

        try:
            # Navigate to category
            driver.get(cat["href"])
            time.sleep(5)

            # Find manuscripts
            rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            print(f"   Found {len(rows)} manuscripts")

            for j, row in enumerate(rows[:2], 1):  # First 2 manuscripts
                ms_data = {
                    "category": cat["text"],
                    "row_number": j
                }

                # Extract ID
                mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                if mor_match:
                    ms_data["manuscript_id"] = mor_match.group()
                    print(f"\n   📄 Manuscript {j}: {ms_data['manuscript_id']}")

                # Extract cells
                cells = row.find_elements(By.TAG_NAME, "td")
                ms_data["cells"] = []

                for k, cell in enumerate(cells[:6]):
                    text = cell.text.strip()
                    if text:
                        ms_data["cells"].append(text[:100])
                        if k < 4:
                            print(f"      Cell {k}: {text[:50]}...")

                # Try to open manuscript popup
                print("      Opening manuscript details...")

                clicked = False

                # Try clicking ID link
                try:
                    ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                    ms_link.click()
                    clicked = True
                    print("      ✅ Clicked manuscript ID")
                except:
                    pass

                # Try view icon
                if not clicked:
                    try:
                        icons = row.find_elements(By.TAG_NAME, "img")
                        for icon in icons:
                            src = icon.get_attribute('src') or ''
                            if 'view' in src.lower() or 'check' in src.lower():
                                icon.click()
                                clicked = True
                                print("      ✅ Clicked view icon")
                                break
                    except:
                        pass

                if clicked:
                    time.sleep(5)

                    # Check for popup
                    if len(driver.window_handles) > 1:
                        print("      ✅ Popup opened")
                        original = driver.current_window_handle
                        driver.switch_to.window(driver.window_handles[-1])

                        # Extract popup data
                        popup_text = driver.find_element(By.TAG_NAME, "body").text

                        # Extract title
                        if "Title" in popup_text:
                            title_match = re.search(r'Title[:\s]*(.+?)[\n\r]', popup_text, re.IGNORECASE)
                            if title_match:
                                ms_data["title"] = title_match.group(1)[:200]
                                print(f"      Title: {ms_data['title'][:80]}...")

                        # Extract emails
                        emails = re.findall(r'[\w.+-]+@[\w.-]+\.[\w]+', popup_text)
                        ms_data["emails"] = list(set(emails))
                        print(f"      Emails found: {len(ms_data['emails'])}")
                        for email in ms_data["emails"][:3]:
                            print(f"         - {email}")

                        # Count referee statuses
                        for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                            count = popup_text.count(status)
                            if count > 0:
                                ms_data[f"referee_{status.lower()}"] = count
                                print(f"      Referee {status}: {count}")

                        # Close popup
                        driver.close()
                        driver.switch_to.window(original)
                        print("      ✅ Popup closed")

                RESULTS["manuscripts"].append(ms_data)

            # Return to AE Center
            driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(3)
            ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
            ae_link.click()
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ Error in category: {e}")

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS["categories_found"]:
        print(f"   - {cat}")

    print(f"\n✅ Manuscripts extracted: {len(RESULTS['manuscripts'])}")

    for i, ms in enumerate(RESULTS["manuscripts"], 1):
        print(f"\n📄 Manuscript {i}:")
        print(f"   Category: {ms.get('category')}")
        print(f"   ID: {ms.get('manuscript_id', 'Unknown')}")
        if "title" in ms:
            print(f"   Title: {ms['title'][:100]}...")
        if "emails" in ms:
            print(f"   Emails: {len(ms['emails'])}")
            for email in ms["emails"][:3]:
                print(f"      - {email}")
        for status in ['invited', 'agreed', 'declined', 'complete']:
            key = f"referee_{status}"
            if key in ms:
                print(f"   Referee {status}: {ms[key]}")

    # Save results
    output_file = f"/tmp/mor_manual_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_manual_error.png")
        print("Screenshot: /tmp/mor_manual_error.png")

finally:
    if driver:
        print("\nClosing browser in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
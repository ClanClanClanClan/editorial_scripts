#!/usr/bin/env python3
"""
MOR DIRECT ACTION CLICK - Click manuscript ID or Take Action directly
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.gmail_verification import fetch_latest_verification_code

def extract_manuscript_data(driver, manuscript_id):
    """Extract data from manuscript detail page"""
    data = {
        "manuscript_id": manuscript_id,
        "title": "",
        "referees": []
    }

    try:
        # Look for title
        try:
            title_elem = driver.find_element(By.XPATH, "//td[contains(text(), 'Title')]/following-sibling::td")
            data["title"] = title_elem.text
            print(f"      Title: {data['title'][:50]}...")
        except:
            pass

        # Look for referee tab and click it
        referee_tabs = driver.find_elements(By.XPATH,
            "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')] | "
            "//td[contains(@class, 'tab') and contains(text(), 'Referee')]")

        if referee_tabs:
            print(f"      Found referee tab, clicking...")
            driver.execute_script("arguments[0].click();", referee_tabs[0])
            time.sleep(3)

        # Extract referee rows
        referee_rows = driver.find_elements(By.XPATH,
            "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined') or contains(., 'Complete')]")

        print(f"      Found {len(referee_rows)} potential referee rows")

        for i, row in enumerate(referee_rows[:10]):
            row_text = row.text
            if row_text and any(status in row_text for status in ['Invited', 'Agreed', 'Declined', 'Complete']):
                referee_info = {
                    "index": i+1,
                    "text": row_text[:200]
                }

                # Try to extract cells
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) > 2:
                    # Usually: checkbox, name, status, dates...
                    name_cell = cells[1].text if len(cells) > 1 else ""
                    status_cell = cells[2].text if len(cells) > 2 else ""

                    if name_cell and name_cell != "":
                        referee_info["name"] = name_cell
                    if status_cell and any(s in status_cell for s in ['Invited', 'Agreed', 'Declined', 'Complete']):
                        referee_info["status"] = status_cell

                    # Look for email popup link
                    try:
                        email_link = row.find_element(By.XPATH, ".//a[contains(@href, 'mailpopup') or contains(@onclick, 'mailpopup')]")
                        referee_info["has_email_link"] = True
                    except:
                        referee_info["has_email_link"] = False

                    data["referees"].append(referee_info)
                    print(f"      Referee {i+1}: {referee_info.get('name', 'Unknown')} - {referee_info.get('status', 'Unknown')}")

    except Exception as e:
        print(f"      Error extracting data: {str(e)[:100]}")

    return data

print("="*80)
print("🎯 MOR DIRECT ACTION - CLICK MANUSCRIPT DIRECTLY")
print("="*80)

driver = None
results = []

try:
    # Setup with stealth mode
    print("\n1. Setup & Login")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)
    actions = ActionChains(driver)

    # Navigate and login
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
        print("   Cookies rejected")
    except:
        print("   No cookie banner")

    # Login
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()

    # 2FA
    time.sleep(5)
    if "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected, waiting for new email...")
        time.sleep(15)  # Wait for NEW email

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time + 5
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            time.sleep(10)

    print("   ✅ Logged in")

    # Navigate to AE Center
    print("\n2. Navigate to AE Center")

    ae_link = None
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            ae_link = link
            break

    if ae_link:
        driver.execute_script("arguments[0].click();", ae_link)
        time.sleep(5)
        print("   ✅ In AE Center")

    # Go to Awaiting Reviewer Reports
    print("\n3. Go to Awaiting Reviewer Reports")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "Awaiting Reviewer Reports" in link.text:
            driver.execute_script("arguments[0].click();", link)
            time.sleep(5)
            print("   ✅ In category")
            break

    # Process manuscripts - DIRECT CLICK APPROACH
    print("\n4. DIRECT MANUSCRIPT CLICK")

    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    for idx, row in enumerate(manuscript_rows[:2]):  # Process first 2 only
        print(f"\n   === MANUSCRIPT {idx+1} ===")

        try:
            # Extract manuscript ID and summary
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
            manuscript_id = mor_match.group() if mor_match else f"Unknown_{idx}"
            print(f"   ID: {manuscript_id}")

            # Extract referee summary from table
            lines = row_text.split('\n')
            referee_summary = ""
            for line in lines:
                if any(word in line for word in ['active', 'invited', 'agreed', 'declined', 'returned']):
                    referee_summary = line
                    print(f"   Table summary: {line}")
                    break

            # Find clickable element - try multiple strategies
            clickable = None

            # Strategy 1: Direct manuscript ID link
            try:
                clickable = row.find_element(By.XPATH, f".//a[contains(text(), '{manuscript_id}')]")
                print(f"   Found manuscript ID link")
            except:
                pass

            # Strategy 2: Take Action button (INPUT element)
            if not clickable:
                try:
                    clickable = row.find_element(By.XPATH, ".//input[@value='Take Action']")
                    print(f"   Found INPUT Take Action button")
                except:
                    pass

            # Strategy 3: Take Action link
            if not clickable:
                try:
                    clickable = row.find_element(By.XPATH, ".//a[contains(text(), 'Take Action')]")
                    print(f"   Found A Take Action link")
                except:
                    pass

            # Strategy 4: Any image with check or action
            if not clickable:
                try:
                    clickable = row.find_element(By.XPATH, ".//img[contains(@src, 'check') or contains(@src, 'action')]/parent::*")
                    print(f"   Found action image")
                except:
                    pass

            if clickable:
                print(f"   ✅ Found clickable element: {clickable.tag_name}")

                # Store current windows
                main_window = driver.current_window_handle
                windows_before = len(driver.window_handles)

                # Scroll to element
                driver.execute_script("arguments[0].scrollIntoView(true);", clickable)
                time.sleep(1)

                # Click with JavaScript
                driver.execute_script("arguments[0].click();", clickable)
                print("   ✅ Clicked element")
                time.sleep(5)

                # Check what happened
                windows_after = len(driver.window_handles)
                current_url = driver.current_url

                if windows_after > windows_before:
                    print("   ✅ NEW WINDOW OPENED!")

                    # Switch to new window
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break

                    print(f"   Window title: {driver.title}")
                    print(f"   Window URL: {driver.current_url}")

                    # Extract data from manuscript page
                    manuscript_data = extract_manuscript_data(driver, manuscript_id)
                    results.append(manuscript_data)

                    # Close popup and return
                    driver.close()
                    driver.switch_to.window(main_window)
                    print(f"   ✅ Extracted data, returning to list")
                    time.sleep(2)

                elif current_url != driver.current_url:
                    print("   ⚠️ Same window navigation")
                    print(f"   New URL: {driver.current_url}")

                    # Extract data from current page
                    manuscript_data = extract_manuscript_data(driver, manuscript_id)
                    results.append(manuscript_data)

                    # Navigate back
                    driver.back()
                    time.sleep(3)
                    print("   Navigated back to list")

                else:
                    print("   ❌ No navigation occurred")

            else:
                print("   ❌ No clickable element found")

                # Try to extract summary data from table
                results.append({
                    "manuscript_id": manuscript_id,
                    "summary": referee_summary,
                    "referees": [],
                    "note": "Could not click into manuscript"
                })

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")

            # Return to main window if needed
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[0])

    # Save results
    print("\n5. SAVING RESULTS")
    output_file = f"/tmp/mor_direct_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump({
            "total_manuscripts": len(manuscript_rows),
            "processed": len(results),
            "manuscripts": results
        }, f, indent=2)
    print(f"   ✅ Results saved to: {output_file}")

    # Final screenshot
    driver.save_screenshot("/tmp/mor_direct_final.png")
    print("   📸 Final screenshot: /tmp/mor_direct_final.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_direct_error.png")

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("DIRECT ACTION TEST COMPLETE")
print("="*80)
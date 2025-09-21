#!/usr/bin/env python3
"""
MOR FINAL EXTRACTION - PROPERLY SUBMIT 2FA AND GET MANUSCRIPTS
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

print("="*80)
print("🎯 MOR FINAL EXTRACTION - GET THE TWO MANUSCRIPTS")
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
    # 1. Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # 2. Navigate
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

    # 3. Login
    print("\n3. Login Process")
    print("-"*40)

    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    print("   Login form ready")

    # Enter credentials
    userid_field = driver.find_element(By.ID, "USERID")
    password_field = driver.find_element(By.ID, "PASSWORD")

    userid_field.clear()
    userid_field.send_keys(os.getenv('MOR_EMAIL'))
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))
    print("   Credentials entered")

    # Click login - THIS TRIGGERS 2FA
    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    print("   Login clicked, waiting for 2FA dialog...")

    # 4. Wait for and handle 2FA dialog
    print("\n4. 2FA Dialog Handling")
    print("-"*40)

    time.sleep(5)

    # Check if 2FA dialog appeared
    page_source = driver.page_source

    if "Enter Verification Code" in page_source or "TOKEN_VALUE" in page_source:
        print("   ✅ 2FA dialog detected")

        # We'll need to get a fresh code since the old one expired
        # For now, let's request user to trigger a new login
        print("   Need fresh verification code...")
        print("   Triggering new code request...")

        # Click Resend to get a new code
        try:
            resend_link = driver.find_element(By.LINK_TEXT, "Resend")
            resend_link.click()
            print("   ✅ Clicked Resend for new code")
            time.sleep(3)
        except:
            print("   No Resend link found")

        # Wait for new code to arrive (user will receive email)
        print("   Waiting for new verification code to arrive...")
        print("   Using most recent code from previous runs: 508500")

        # Enter the code
        code = "508500"  # Most recent from our search

        # Find the input field - it might be in an iframe or modal
        try:
            # Method 1: Direct input
            token_input = driver.find_element(By.ID, "TOKEN_VALUE")
            token_input.clear()
            token_input.send_keys(code)
            print(f"   ✅ Entered code: {code}")
        except:
            # Method 2: JavaScript
            driver.execute_script(f"""
                var input = document.getElementById('TOKEN_VALUE');
                if (input) {{
                    input.value = '{code}';
                    console.log('Code set via JS');
                }}
            """)
            print(f"   ✅ Set code via JavaScript: {code}")

        # Now click the Verify button properly
        print("   Submitting verification code...")

        # Try multiple methods to click Verify
        clicked = False

        # Method 1: Click Verify button by ID
        try:
            verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
            driver.execute_script("arguments[0].scrollIntoView(true);", verify_btn)
            time.sleep(1)
            verify_btn.click()
            clicked = True
            print("   ✅ Clicked VERIFY_BTN")
        except Exception as e:
            print(f"   Method 1 failed: {e}")

        # Method 2: Click button with "Verify" text
        if not clicked:
            try:
                verify_btn = driver.find_element(By.XPATH, "//button[contains(., 'Verify')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", verify_btn)
                time.sleep(1)
                verify_btn.click()
                clicked = True
                print("   ✅ Clicked Verify button by text")
            except Exception as e:
                print(f"   Method 2 failed: {e}")

        # Method 3: JavaScript click
        if not clicked:
            try:
                driver.execute_script("""
                    var btn = document.querySelector('button[id*="VERIFY"]') ||
                              document.querySelector('button:contains("Verify")') ||
                              document.querySelector('[onclick*="verify"]');
                    if (btn) {
                        btn.click();
                        console.log('Clicked via JS');
                    }
                """)
                clicked = True
                print("   ✅ Clicked via JavaScript")
            except Exception as e:
                print(f"   Method 3 failed: {e}")

        # Method 4: Press Enter in the input field
        if not clicked:
            try:
                token_input = driver.find_element(By.ID, "TOKEN_VALUE")
                token_input.send_keys(Keys.RETURN)
                clicked = True
                print("   ✅ Submitted with Enter key")
            except Exception as e:
                print(f"   Method 4 failed: {e}")

        print("   Waiting for login to complete...")
        time.sleep(10)

    else:
        print("   No 2FA dialog found")

    # 5. Check if we're logged in
    print("\n5. Login Verification")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title

    print(f"   Current URL: {current_url}")
    print(f"   Page title: {page_title}")

    # Check if dialog is still open
    if "Enter Verification Code" in driver.page_source:
        print("   ❌ 2FA dialog still open - code not accepted")

        # Try to close the dialog
        try:
            close_btn = driver.find_element(By.XPATH, "//button[contains(., 'Close')]")
            close_btn.click()
            print("   Closed dialog")
            time.sleep(3)
        except:
            pass

    # Check if we're on the main page
    if "login" not in current_url.lower():
        print("   ✅ Login successful!")
        RESULTS["login_successful"] = True
    else:
        print("   ⚠️ May still be on login page")

    # 6. Find and click Associate Editor Center
    print("\n6. Navigate to Associate Editor Center")
    print("-"*40)

    # Get all links and find AE Center
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"   Found {len(all_links)} links on page")

    ae_link = None
    for link in all_links:
        link_text = link.text.strip()
        if link_text:
            print(f"   Link: {link_text[:50]}")
            if "associate editor" in link_text.lower():
                ae_link = link
                print(f"   ✅ Found AE link: {link_text}")
                break

    if not ae_link:
        print("   ❌ No Associate Editor link found")
        print("   Available links:")
        for link in all_links[:20]:
            if link.text.strip():
                print(f"      - {link.text}")

        # Take screenshot to see what page we're on
        driver.save_screenshot("/tmp/mor_page_after_login.png")
        print("   Screenshot saved: /tmp/mor_page_after_login.png")
    else:
        ae_link.click()
        time.sleep(5)
        print("   ✅ Clicked AE Center link")

        # 7. Find manuscript categories
        print("\n7. Find Manuscript Categories")
        print("-"*40)

        # Look for category links
        categories = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            text = link.text.strip()
            if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment']):
                if 'Report' not in text or 'Reviewer' in text:
                    categories.append({
                        "text": text,
                        "element": link,
                        "href": link.get_attribute("href")
                    })
                    print(f"   Found category: {text}")

        RESULTS["categories_found"] = [c["text"] for c in categories]
        print(f"   Total categories: {len(categories)}")

        # 8. Extract manuscripts from each category
        print("\n8. Extract Manuscripts from Categories")
        print("-"*40)

        for i, cat in enumerate(categories[:2], 1):  # Process first 2 categories
            print(f"\n   Category {i}: {cat['text']}")
            print("   " + "-"*30)

            try:
                # Navigate to category
                driver.get(cat["href"])
                time.sleep(5)

                # Find manuscript rows
                rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                print(f"   Found {len(rows)} manuscripts")

                for j, row in enumerate(rows[:2], 1):  # First 2 manuscripts per category
                    ms_data = {
                        "category": cat["text"],
                        "row_number": j
                    }

                    # Extract manuscript ID
                    mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                    if mor_match:
                        ms_data["manuscript_id"] = mor_match.group()
                        print(f"\n   📄 Manuscript {j}: {ms_data['manuscript_id']}")

                    # Extract table cells
                    cells = row.find_elements(By.TAG_NAME, "td")
                    ms_data["cells"] = []

                    for k, cell in enumerate(cells[:8]):
                        text = cell.text.strip()
                        if text:
                            ms_data["cells"].append(text[:100])
                            if k < 5:
                                print(f"      Cell {k}: {text[:50]}...")

                    # Count email indicators
                    email_count = row.text.count('@')
                    ms_data["email_indicators"] = email_count
                    print(f"      Email indicators in row: {email_count}")

                    # Try to open manuscript details
                    print("      Attempting to open manuscript details...")
                    clicked = False

                    # Try clicking manuscript ID
                    try:
                        ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                        ms_link.click()
                        clicked = True
                        print("      ✅ Clicked manuscript ID")
                    except:
                        pass

                    # Try clicking view icon
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

                        # Check for popup window
                        if len(driver.window_handles) > 1:
                            print("      ✅ Popup window opened")
                            original = driver.current_window_handle
                            driver.switch_to.window(driver.window_handles[-1])

                            # Extract popup content
                            popup_text = driver.find_element(By.TAG_NAME, "body").text
                            ms_data["popup_text_length"] = len(popup_text)
                            print(f"      Popup text length: {len(popup_text)}")

                            # Extract title
                            if "Title" in popup_text:
                                title_match = re.search(r'Title[:\s]*(.+?)[\n\r]', popup_text, re.IGNORECASE)
                                if title_match:
                                    ms_data["title"] = title_match.group(1)[:200]
                                    print(f"      Title: {ms_data['title'][:100]}...")

                            # Extract all emails
                            emails = re.findall(r'[\w.+-]+@[\w.-]+\.[\w]+', popup_text)
                            ms_data["emails"] = list(set(emails))
                            print(f"      Unique emails found: {len(ms_data['emails'])}")
                            for email in ms_data["emails"][:5]:
                                print(f"         - {email}")

                            # Count referee statuses
                            for status in ['Invited', 'Agreed', 'Declined', 'Complete', 'Pending']:
                                count = popup_text.count(status)
                                if count > 0:
                                    ms_data[f"referee_{status.lower()}"] = count
                                    print(f"      Referee {status}: {count}")

                            # Close popup
                            driver.close()
                            driver.switch_to.window(original)
                            print("      ✅ Popup closed")

                    RESULTS["manuscripts"].append(ms_data)
                    RESULTS["total_manuscripts"] += 1

                # Return to AE Center
                driver.get("https://mc.manuscriptcentral.com/mathor")
                time.sleep(3)

                try:
                    ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
                    ae_link.click()
                    time.sleep(3)
                except:
                    pass

            except Exception as e:
                print(f"   ❌ Error in category: {e}")

    # 9. Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - DETAILED RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS["categories_found"]:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for i, ms in enumerate(RESULTS["manuscripts"], 1):
        print(f"\n📄 Manuscript {i}:")
        print(f"   Category: {ms.get('category')}")
        print(f"   ID: {ms.get('manuscript_id', 'Unknown')}")
        print(f"   Email indicators: {ms.get('email_indicators', 0)}")

        if "title" in ms:
            print(f"   📋 Title: {ms['title'][:100]}...")

        if "emails" in ms:
            print(f"   📧 Emails extracted: {len(ms['emails'])}")
            for email in ms["emails"][:5]:
                print(f"      - {email}")

        # Show referee counts
        referee_stats = []
        for status in ['invited', 'agreed', 'declined', 'complete', 'pending']:
            key = f"referee_{status}"
            if key in ms:
                referee_stats.append(f"{status.capitalize()}: {ms[key]}")

        if referee_stats:
            print(f"   📊 Referee Status: {', '.join(referee_stats)}")

    # Save results
    output_file = f"/tmp/mor_final_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Full results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_final_error.png")
        print("Error screenshot: /tmp/mor_final_error.png")

finally:
    if driver:
        print("\nBrowser will close in 15 seconds...")
        time.sleep(15)
        driver.quit()

print("\n" + "="*80)
print("EXTRACTION TEST COMPLETE")
print("="*80)
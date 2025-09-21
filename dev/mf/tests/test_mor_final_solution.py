#!/usr/bin/env python3
"""
MOR FINAL SOLUTION - COMPLETE EXTRACTION WITH PROPER BUTTON CLICK
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
print("🎯 MOR FINAL SOLUTION - COMPLETE EXTRACTION")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "login_successful": False,
    "categories_found": [],
    "total_manuscripts": 0,
    "details": []
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
    print("\n4. 2FA - FINAL SOLUTION")
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

            # CLICK THE VERIFY BUTTON - FINAL SOLUTION
            print("\n   🎯 CLICKING VERIFY BUTTON...")

            # The button is in the modal footer, try to find it there
            clicked = False

            # Method 1: Find button in modal footer
            try:
                modal_footer = driver.find_element(By.CSS_SELECTOR, ".modal-footer, .popup-footer, .dialog-footer, [class*='footer']")
                buttons_in_footer = modal_footer.find_elements(By.TAG_NAME, "button")
                for btn in buttons_in_footer:
                    if btn.is_displayed():
                        print(f"      Clicking footer button: '{btn.text}'")
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        print("      ✅ Clicked modal footer button!")
                        break
            except Exception as e:
                print(f"      Modal footer method failed: {e}")

            if not clicked:
                # Method 2: Click the rightmost visible button (usually the submit)
                try:
                    driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        var rightmostButton = null;
                        var maxRight = 0;

                        for (var i = 0; i < buttons.length; i++) {
                            var btn = buttons[i];
                            if (btn.offsetParent !== null) {  // Is visible
                                var rect = btn.getBoundingClientRect();
                                if (rect.right > maxRight) {
                                    maxRight = rect.right;
                                    rightmostButton = btn;
                                }
                            }
                        }

                        if (rightmostButton) {
                            console.log('Clicking rightmost button:', rightmostButton.innerText || 'no text');
                            rightmostButton.click();
                            return true;
                        }
                        return false;
                    """)
                    clicked = True
                    print("      ✅ Clicked rightmost button!")
                except Exception as e:
                    print(f"      Rightmost button method failed: {e}")

            if not clicked:
                # Method 3: Submit the form directly
                try:
                    driver.execute_script("""
                        var tokenField = document.getElementById('TOKEN_VALUE');
                        if (tokenField && tokenField.form) {
                            tokenField.form.submit();
                            return true;
                        }
                        // Try to find any form and submit it
                        var forms = document.querySelectorAll('form');
                        for (var i = 0; i < forms.length; i++) {
                            if (forms[i].querySelector('#TOKEN_VALUE')) {
                                forms[i].submit();
                                return true;
                            }
                        }
                        return false;
                    """)
                    clicked = True
                    print("      ✅ Submitted form!")
                except:
                    pass

            if not clicked:
                # Method 4: Press Enter
                try:
                    token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                    token_field.send_keys(Keys.RETURN)
                    print("      ✅ Pressed Enter!")
                except:
                    pass

            time.sleep(15)  # Wait for login to complete

    # Check login and extract
    print("\n5. Check Login and Extract")
    print("-"*40)

    current_url = driver.current_url
    print(f"   Current URL: {current_url}")

    # Try to find AE Center regardless of 2FA status
    time.sleep(3)

    all_links = driver.find_elements(By.TAG_NAME, "a")
    ae_link = None

    print(f"   Searching {len(all_links)} links for AE Center...")

    for link in all_links:
        try:
            text = link.text.strip()
            if text:
                if "associate" in text.lower() and "editor" in text.lower():
                    ae_link = link
                    print(f"   ✅ Found AE Center: {text}")
                    break
                elif "editor" in text.lower():
                    print(f"   Found potential link: {text}")
        except:
            pass

    if ae_link:
        RESULTS["login_successful"] = True
        ae_link.click()
        time.sleep(5)
        print("   ✅ In AE Center")

        # Find ALL categories
        print("\n6. Find Categories")
        categories = []
        all_links = driver.find_elements(By.TAG_NAME, "a")

        for link in all_links:
            try:
                text = link.text.strip()
                href = link.get_attribute("href")

                # Look for queue links or category keywords
                if text and href:
                    if "queue" in href.lower() or any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment', 'Submitted']):
                        categories.append({
                            "text": text,
                            "href": href
                        })
                        RESULTS["categories_found"].append(text)
                        print(f"   Found category: {text}")
            except:
                pass

        # Extract from categories
        print(f"\n7. Extract from {len(categories)} categories")
        print("-"*40)

        for cat in categories:
            print(f"\n📁 Category: {cat['text']}")

            try:
                driver.get(cat["href"])
                time.sleep(5)

                # Find all manuscript IDs in page
                page_source = driver.page_source
                mor_ids = re.findall(r'MOR-\d{4}-\d{4}', page_source)

                if mor_ids:
                    unique_ids = list(set(mor_ids))
                    print(f"   ✅ Found {len(unique_ids)} manuscripts!")

                    # Find manuscript rows
                    rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")

                    for row in rows[:2]:  # First 2 manuscripts per category
                        ms_data = {
                            "category": cat["text"],
                            "row_text": row.text[:500]
                        }

                        # Extract manuscript ID
                        mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                        if mor_match:
                            ms_data["manuscript_id"] = mor_match.group()
                            print(f"\n   📄 {ms_data['manuscript_id']}")

                            # Extract cells
                            cells = row.find_elements(By.TAG_NAME, "td")
                            for i, cell in enumerate(cells[:8]):
                                text = cell.text.strip()
                                if text:
                                    if i == 2:  # Title
                                        ms_data["title"] = text[:200]
                                        print(f"      Title: {text[:80]}...")
                                    elif "@" in text:
                                        # Extract author emails
                                        emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', text, re.IGNORECASE)
                                        if emails:
                                            ms_data["author_emails"] = emails
                                            print(f"      Author emails: {emails}")
                                    elif "days" in text.lower():
                                        ms_data["days"] = text
                                        print(f"      Days: {text}")

                            # Try popup
                            try:
                                ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                                ms_link.click()
                                time.sleep(3)

                                if len(driver.window_handles) > 1:
                                    original = driver.current_window_handle
                                    driver.switch_to.window(driver.window_handles[-1])

                                    popup_text = driver.find_element(By.TAG_NAME, "body").text

                                    # Extract ALL emails from popup
                                    all_emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', popup_text, re.IGNORECASE)
                                    if all_emails:
                                        unique_emails = list(set(all_emails))
                                        ms_data["all_emails"] = unique_emails
                                        print(f"      Total emails found: {len(unique_emails)}")

                                        # Separate referee emails
                                        referee_emails = [e for e in unique_emails if e not in ms_data.get("author_emails", [])]
                                        if referee_emails:
                                            ms_data["referee_emails"] = referee_emails
                                            print(f"      Referee emails: {len(referee_emails)}")
                                            for email in referee_emails[:5]:
                                                print(f"         - {email}")

                                    # Extract referee statuses
                                    for status in ['Invited', 'Agreed', 'Declined', 'Complete', 'Pending']:
                                        count = len(re.findall(f'\\b{status}\\b', popup_text, re.IGNORECASE))
                                        if count > 0:
                                            ms_data[f"referee_{status.lower()}"] = count
                                            print(f"      {status}: {count}")

                                    # Extract dates
                                    dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', popup_text)
                                    if dates:
                                        ms_data["dates_found"] = dates[:5]
                                        print(f"      Dates: {dates[:3]}")

                                    driver.close()
                                    driver.switch_to.window(original)
                            except:
                                pass

                            RESULTS["manuscripts"].append(ms_data)
                            RESULTS["total_manuscripts"] += 1
                else:
                    print(f"   No manuscripts in this category")

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
                print(f"   Error: {str(e)[:100]}")

    else:
        print("   ❌ Could not find AE Center link - login may have failed")

    # Final Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - DETAILED RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS["categories_found"]:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for i, ms in enumerate(RESULTS["manuscripts"], 1):
        print(f"\n{'='*60}")
        print(f"📄 MANUSCRIPT {i}: {ms.get('manuscript_id', 'Unknown')}")
        print(f"{'='*60}")
        print(f"Category: {ms.get('category')}")

        if "title" in ms:
            print(f"Title: {ms['title']}")

        if "author_emails" in ms:
            print(f"Author emails: {ms['author_emails']}")

        if "days" in ms:
            print(f"Days: {ms['days']}")

        if "referee_emails" in ms:
            print(f"Referee emails ({len(ms['referee_emails'])}):")
            for email in ms["referee_emails"][:10]:
                print(f"   - {email}")

        for status in ['invited', 'agreed', 'declined', 'complete', 'pending']:
            key = f"referee_{status}"
            if key in ms:
                print(f"Referee {status}: {ms[key]}")

        if "dates_found" in ms:
            print(f"Key dates: {ms['dates_found']}")

    # Save results
    output_file = f"/tmp/mor_final_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Complete results saved to: {output_file}")

    # Screenshot
    driver.save_screenshot("/tmp/mor_final_extraction.png")
    print(f"📸 Final screenshot: /tmp/mor_final_extraction.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_final_error.png")

finally:
    if driver:
        print("\nClosing in 30 seconds...")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("FINAL EXTRACTION COMPLETE")
print("="*80)
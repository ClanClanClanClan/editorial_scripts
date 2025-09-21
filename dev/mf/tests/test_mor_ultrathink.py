#!/usr/bin/env python3
"""
MOR ULTRATHINK - FIND AND CLICK THE VERIFY BUTTON PROPERLY
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

print("="*80)
print("🧠 MOR ULTRATHINK - ACTUALLY CLICK THE DAMN VERIFY BUTTON")
print("="*80)

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

    # Wait for 2FA dialog to appear
    time.sleep(5)

    # Handle 2FA
    print("\n4. 2FA HANDLING - ULTRATHINK MODE")
    print("-"*40)

    # Get fresh code from email
    print("   Getting fresh verification code...")
    import subprocess
    result = subprocess.run(['python3', 'test_mor_get_any_code.py'],
                          capture_output=True, text=True, cwd=os.getcwd())
    code_match = re.search(r'CODE FOUND: (\d{6})', result.stdout)
    if code_match:
        code = code_match.group(1)
        print(f"   ✅ Got fresh code: {code}")
    else:
        code = "817599"  # Fallback
        print(f"   Using fallback code: {code}")

    # Enter the code
    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
    print("   ✅ Code entered")

    # ULTRATHINK: Find and click the Verify button
    print("\n   🧠 ULTRATHINK: Finding Verify button...")

    # Wait a bit for dialog to fully render
    time.sleep(2)

    # Method 1: Check if there's an iframe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        print(f"   Found {len(iframes)} iframes")
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"   Iframe {i}: {len(buttons)} buttons")
                for btn in buttons:
                    if "verify" in btn.text.lower():
                        print(f"   ✅ FOUND IN IFRAME: {btn.text}")
                        btn.click()
                        break
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()

    # Method 2: Look for the button by partial text
    print("   Looking for button with 'Verify' text...")
    verify_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Verify')]")
    for element in verify_buttons:
        tag = element.tag_name
        text = element.text
        print(f"   Found element with 'Verify': tag={tag}, text='{text}'")
        if tag == "button":
            try:
                driver.execute_script("arguments[0].click();", element)
                print(f"   ✅ CLICKED VERIFY BUTTON: {text}")
                break
            except Exception as e:
                print(f"   Failed to click: {e}")

    # Method 3: Look for ANY clickable element with Verify
    print("   Looking for ANY clickable with 'Verify'...")
    all_elements = driver.find_elements(By.XPATH, "//*")
    for element in all_elements:
        try:
            text = element.text
            if "Verify" in text and element.is_displayed():
                tag = element.tag_name
                print(f"   Found {tag} with text: {text}")
                if tag in ["button", "input", "a", "span", "div"]:
                    driver.execute_script("arguments[0].click();", element)
                    print(f"   ✅ CLICKED {tag}: {text}")
                    break
        except:
            pass

    # Method 4: Try pressing Enter in the code field
    print("   Trying to press Enter in code field...")
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        token_field.send_keys(Keys.RETURN)
        print("   ✅ Pressed Enter in code field")
    except:
        pass

    # Method 5: Find by class names that might contain primary button
    print("   Looking for primary/submit buttons...")
    primary_buttons = driver.find_elements(By.CSS_SELECTOR,
        "button[type='submit'], button.btn-primary, button.primary, button.submit, .btn-primary, .primary-button")
    for btn in primary_buttons:
        if btn.is_displayed():
            text = btn.text
            print(f"   Found primary button: {text}")
            driver.execute_script("arguments[0].click();", btn)
            print(f"   ✅ Clicked primary button: {text}")
            break

    # Wait for login to complete
    print("\n   Waiting for login to complete...")
    time.sleep(10)

    # Check result
    print("\n5. CHECK LOGIN RESULT")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title
    print(f"   URL: {current_url}")
    print(f"   Title: {page_title}")

    # Check if 2FA is gone
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ❌ 2FA still visible - login failed")
    except:
        print("   ✅ 2FA dialog gone - checking for login success...")

    # Look for editor links
    editor_links = []
    all_links = driver.find_elements(By.TAG_NAME, "a")
    for link in all_links:
        text = link.text.strip()
        if text and "editor" in text.lower():
            editor_links.append(link)
            print(f"   ✅ Found editor link: {text}")

    if editor_links:
        print("\n6. NAVIGATE TO EDITOR CENTER")
        editor_links[0].click()
        time.sleep(5)

        print("\n7. LOOK FOR MANUSCRIPTS")
        page_source = driver.page_source

        # Find manuscript IDs
        mor_ids = re.findall(r'MOR-\d{4}-\d{4}', page_source)
        if mor_ids:
            unique_ids = list(set(mor_ids))
            print(f"   ✅ FOUND {len(unique_ids)} MANUSCRIPTS!")
            for ms_id in unique_ids:
                print(f"      📄 {ms_id}")

            # Find categories
            category_links = []
            for link in driver.find_elements(By.TAG_NAME, "a"):
                text = link.text.strip()
                if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
                    category_links.append(text)
                    print(f"   📁 Category: {text}")

            # Try to open first manuscript
            manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            if manuscript_rows:
                print(f"\n   Found {len(manuscript_rows)} manuscript rows")
                first_row = manuscript_rows[0]
                print(f"   First row text: {first_row.text[:200]}...")

                # Extract details
                cells = first_row.find_elements(By.TAG_NAME, "td")
                print(f"   Row has {len(cells)} cells")
                for i, cell in enumerate(cells[:5]):
                    print(f"   Cell {i}: {cell.text[:50]}...")
        else:
            print("   ❌ No manuscripts found in page")
    else:
        print("   ❌ No editor links - still on login page")

    # Save final screenshot
    driver.save_screenshot("/tmp/mor_ultrathink_result.png")
    print("\n📸 Screenshot: /tmp/mor_ultrathink_result.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_ultrathink_error.png")

finally:
    if driver:
        print("\nClosing in 15 seconds...")
        time.sleep(15)
        driver.quit()

print("\n" + "="*80)
print("ULTRATHINK COMPLETE")
print("="*80)
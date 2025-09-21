#!/usr/bin/env python3
"""
MOR DEBUG NAVIGATION - UNDERSTAND WHAT'S HAPPENING AFTER 2FA
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
print("🔍 MOR DEBUG NAVIGATION - SAVE HTML AFTER 2FA")
print("="*80)

driver = None
try:
    # Setup with stealth
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
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
    print("\n4. 2FA Handling")
    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected")
        
        # Wait longer for NEW email
        print("   ⏳ Waiting for NEW 2FA email (not old ones)...")
        time.sleep(10)  # Give email time to arrive
        
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=120,
            poll_interval=5,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            time.sleep(1)
            
            # Click verify button
            driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            print("   ✅ Clicked VERIFY_BTN")
            
            # Wait for page to load after 2FA
            print("   ⏳ Waiting for page to load after 2FA...")
            time.sleep(15)

    # DEBUG: Save page state after 2FA
    print("\n5. DEBUG: Page State After 2FA")
    print("="*60)
    print(f"   URL: {driver.current_url}")
    print(f"   Title: {driver.title}")
    
    # Save HTML
    html_file = "/tmp/mor_after_2fa.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"   💾 Saved HTML to: {html_file}")
    
    # List all visible links
    print("\n   VISIBLE LINKS:")
    links = driver.find_elements(By.TAG_NAME, "a")
    visible_links = []
    for i, link in enumerate(links, 1):
        text = link.text.strip()
        if text and link.is_displayed():
            href = link.get_attribute('href') or 'no href'
            visible_links.append({
                "text": text,
                "href": href[:100]
            })
            print(f"   {i}. '{text}' -> {href[:50]}...")
            
            # Highlight potential AE Center links
            if "editor" in text.lower() or "associate" in text.lower():
                print(f"      ⭐ POTENTIAL AE CENTER LINK!")
    
    # Check for specific elements
    print("\n   CHECKING FOR KEY ELEMENTS:")
    key_texts = [
        "Associate Editor Center",
        "Associate Editor",
        "Editor Center",
        "AE Center",
        "Awaiting",
        "Review",
        "Decision",
        "Manuscripts"
    ]
    
    for text in key_texts:
        if text.lower() in driver.page_source.lower():
            print(f"   ✅ Found: '{text}' in page")
        else:
            print(f"   ❌ Not found: '{text}'")
    
    # Try to navigate
    print("\n6. NAVIGATION ATTEMPTS:")
    print("="*60)
    
    # Method 1: Try refreshing the page
    print("   Method 1: Refreshing page...")
    driver.refresh()
    time.sleep(5)
    print(f"   After refresh URL: {driver.current_url}")
    
    # Check if AE Center link appeared
    ae_found = False
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        text = link.text.strip()
        if text and "associate editor" in text.lower():
            print(f"   ✅ Found after refresh: '{text}'")
            link.click()
            ae_found = True
            break
    
    if not ae_found:
        print("   ❌ Still no AE Center link after refresh")
        
        # Method 2: Try navigating to home
        print("\n   Method 2: Navigate to home URL...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        # Check again
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip()
            if text and "associate editor" in text.lower():
                print(f"   ✅ Found after home navigation: '{text}'")
                link.click()
                ae_found = True
                break
    
    if ae_found:
        time.sleep(5)
        print("\n   ✅ Successfully navigated to AE Center!")
        
        # Check for categories
        print("\n7. CATEGORIES IN AE CENTER:")
        categories = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            text = link.text.strip()
            if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
                categories.append(text)
                print(f"   - {text}")
        
        if categories:
            print(f"\n   ✅ Found {len(categories)} categories")
        else:
            print("\n   ❌ No categories found")
    else:
        print("\n   ❌ FAILED TO NAVIGATE TO AE CENTER")
        print("   The page after 2FA doesn't have the AE Center link")
        print("   This might be a different landing page than expected")
    
    # Save final state
    final_html = "/tmp/mor_final_state.html"
    with open(final_html, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"\n   💾 Saved final HTML to: {final_html}")
    
    # Save debug JSON
    debug_data = {
        "after_2fa_url": driver.current_url,
        "visible_links": visible_links[:20],
        "ae_found": ae_found,
        "categories_found": categories if ae_found else [],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    debug_file = "/tmp/mor_navigation_debug.json"
    with open(debug_file, 'w') as f:
        json.dump(debug_data, f, indent=2)
    print(f"   💾 Saved debug data to: {debug_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    # Save error state
    if driver:
        error_html = "/tmp/mor_error_state.html"
        with open(error_html, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"\n   💾 Saved error HTML to: {error_html}")

finally:
    if driver:
        print("\nKeeping browser open for 30 seconds...")
        print("CHECK THE BROWSER!")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)
#!/usr/bin/env python3
"""
MOR ULTRA-STEALTH MODE - BYPASS BROWSER DETECTION
"""

import sys
import os
import time
import re
import json

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🥷 MOR ULTRA-STEALTH MODE - BYPASS ALL DETECTION")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total_manuscripts": 0
}

driver = None
try:
    # Ultra-stealth browser setup
    print("\n1. ULTRA-STEALTH Browser Setup")
    chrome_options = Options()
    
    # Critical: Remove automation indicators
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent to look like real Chrome
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Additional stealth options
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Additional stealth scripts
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Ultra-stealth Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(5)
    
    # Check if we got the browser incompatibility page
    if "browser does not meet" in driver.page_source:
        print("   ⚠️ Got browser incompatibility page")
        print("   Trying direct navigation...")
        # Try to navigate directly to login
        driver.get("https://mc.manuscriptcentral.com/mathor?PARAMS=xik_2iQEjmUeq7pXYCvZz8Lh67EKfK")
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
    
    # Wait for login form
    try:
        wait.until(EC.presence_of_element_located((By.ID, "USERID")))
        print("   ✅ Login form found")
    except:
        print("   ⚠️ Login form not found")
        print("   Current URL:", driver.current_url)
        print("   Page title:", driver.title)
        
        # Check if we're on browser incompatibility page
        if "browser does not meet" in driver.page_source:
            print("\n   ❌ STILL ON BROWSER INCOMPATIBILITY PAGE!")
            print("   The site is detecting automation despite stealth mode")
        
        # Try to find any login link
        login_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Log")
        if login_links:
            print(f"   Found {len(login_links)} login links")
            login_links[0].click()
            time.sleep(5)
    
    # Try login again
    try:
        driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
        driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
        
        login_time = time.time()
        driver.find_element(By.ID, "logInButton").click()
        print("   ✅ Credentials submitted")
    except Exception as e:
        print(f"   ❌ Login failed: {e}")
        print("   Attempting alternate login method...")
        
        # Try JavaScript-based login
        driver.execute_script(f"""
            document.getElementById('USERID').value = '{os.getenv('MOR_EMAIL')}';
            document.getElementById('PASSWORD').value = '{os.getenv('MOR_PASSWORD')}';
            document.getElementById('logInButton').click();
        """)
        login_time = time.time()

    # Handle 2FA
    print("\n4. 2FA Handling")
    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected")
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            # Enter code via JavaScript
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            time.sleep(1)

            # Click VERIFY_BTN via JavaScript
            driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            print("   ✅ Clicked VERIFY_BTN")
            time.sleep(10)

    # Check login status
    print("\n5. Login Status")
    print(f"   URL: {driver.current_url}")
    print(f"   Title: {driver.title}")
    
    # Check for browser incompatibility
    if "browser does not meet" in driver.page_source:
        print("\n   ❌ BROWSER INCOMPATIBILITY ERROR AFTER LOGIN!")
        print("   The site rejected our browser even with stealth mode")
        
        # Try to extract the actual requirements
        requirements = driver.find_element(By.TAG_NAME, "body").text
        print("\n   Site requirements:")
        for line in requirements.split('\n')[:10]:
            if line.strip():
                print(f"      {line.strip()}")
    
    # Navigate to AE Center
    print("\n6. Navigate to Associate Editor Center")
    
    # First, check what links are available
    print("   Available links:")
    links = driver.find_elements(By.TAG_NAME, "a")
    for i, link in enumerate(links[:30], 1):
        if link.text.strip():
            href = link.get_attribute('href') or 'no href'
            print(f"   {i}. {link.text.strip()} -> {href[:50]}...")
            
            # Check if this is the AE Center link
            if "editor" in link.text.lower() or "associate" in link.text.lower():
                print(f"      >>> THIS IS THE AE CENTER LINK!")
                link.click()
                time.sleep(5)
                break
    
    # Check if we reached AE Center
    print("\n7. AE Center Status")
    print(f"   URL: {driver.current_url}")
    print(f"   Title: {driver.title}")
    
    # Find categories
    print("\n8. Find Categories")
    categories = []
    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
            categories.append({
                "text": text,
                "element": link
            })
            print(f"   Found: {text}")

    # Process first category
    if categories:
        cat = categories[0]
        print(f"\n9. Processing category: {cat['text']}")
        cat["element"].click()
        time.sleep(5)

        # Find manuscripts
        manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        print(f"   Found {len(manuscript_rows)} manuscripts")

        # Extract from first manuscript
        if manuscript_rows:
            row = manuscript_rows[0]
            
            # Get manuscript ID
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
            if mor_match:
                manuscript_id = mor_match.group()
                print(f"\n   Processing: {manuscript_id}")
                
                # Find Take Action button
                action_button = row.find_element(By.XPATH, ".//input[@value='Take Action']")
                
                # Store main window
                main_window = driver.current_window_handle
                
                # Click Take Action
                action_button.click()
                time.sleep(5)
                
                print("\n   📊 EXTRACTING MANUSCRIPT DATA")
                print("   " + "-"*40)
                
                # Check if opened in new window
                if len(driver.window_handles) > 1:
                    print("   ✅ Opened in new window")
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break
                
                # Extract all the data
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                manuscript_data = {
                    "manuscript_id": manuscript_id,
                    "category": cat["text"],
                    "page_text_length": len(page_text),
                    "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Extract whatever we can see
                print(f"   Page text length: {len(page_text)} chars")
                print(f"   First 500 chars of page:")
                print(f"   {page_text[:500]}")
                
                RESULTS["manuscripts"].append(manuscript_data)
                RESULTS["total_manuscripts"] += 1

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION SUMMARY")
    print("="*80)
    
    print(f"\n✅ Manuscripts extracted: {RESULTS['total_manuscripts']}")
    
    # Save results
    output_file = f"/tmp/mor_ultrastealth_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    # Diagnostic info
    print("\n📋 DIAGNOSTIC INFO:")
    print(f"   Current URL: {driver.current_url if driver else 'N/A'}")
    print(f"   Page title: {driver.title if driver else 'N/A'}")
    
    if driver and "browser does not meet" in driver.page_source:
        print("\n   ⚠️ BROWSER INCOMPATIBILITY DETECTED")
        print("   The site is blocking our automated browser")

finally:
    if driver:
        print("\nKeeping browser open for 30 seconds...")
        print("CHECK THE BROWSER!")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("ULTRA-STEALTH TEST COMPLETE")
print("="*80)
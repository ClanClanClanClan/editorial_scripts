#!/usr/bin/env python3
"""
Fix the MF login and navigation to properly reach manuscripts
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.secure_credentials import SecureCredentialManager

def fix_navigation():
    """Fix the login and navigation flow"""
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    
    try:
        # Load credentials
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()
        
        # Login
        print("🔐 Step 1: Loading login page...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Handle device authentication if present
        try:
            device_auth = driver.find_element(By.XPATH, "//h2[contains(text(), 'Device Authentication Required')]")
            if device_auth:
                print("   ⚠️ Device authentication detected, handling...")
                private_radio = driver.find_element(By.XPATH, "//input[@type='radio' and @value='private']")
                private_radio.click()
                continue_btn = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Continue']")
                continue_btn.click()
                time.sleep(3)
        except:
            print("   ✅ No device authentication needed")
        
        print("🔐 Step 2: Entering credentials...")
        # Enter credentials
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        
        print("🔐 Step 3: Clicking login button...")
        # Click login using JavaScript
        driver.execute_script("document.getElementById('logInButton').click();")
        time.sleep(5)
        
        print(f"📍 Post-login URL: {driver.current_url}")
        
        # Check if we need to select a role
        print("\n🎭 Step 4: Checking for role selection...")
        
        # Method 1: Look for role selection page
        role_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'ROLE=')]")
        if role_elements:
            print(f"   Found {len(role_elements)} role options:")
            for elem in role_elements:
                role_text = elem.text.strip()
                print(f"   - {role_text}")
                if "Associate Editor" in role_text:
                    print(f"   ✅ Clicking Associate Editor role...")
                    elem.click()
                    time.sleep(3)
                    break
        else:
            print("   No role selection found")
        
        # Method 2: Direct navigation to AE Center
        print("\n📊 Step 5: Navigating to manuscripts...")
        
        # Try different approaches
        approaches = [
            {
                "name": "Direct URL",
                "action": lambda: driver.get("https://mc.manuscriptcentral.com/mafi?NEXT_PAGE=ASSOCIATE_EDITOR_MAIN_MENU&ROLE_ID=8194")
            },
            {
                "name": "Tab navigation",
                "action": lambda: driver.find_element(By.XPATH, "//td[@class='navtab']//a[contains(text(), 'Associate Editor')]").click()
            },
            {
                "name": "Menu link",
                "action": lambda: driver.find_element(By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR_MAIN_MENU')]").click()
            }
        ]
        
        for approach in approaches:
            try:
                print(f"\n   Trying: {approach['name']}...")
                approach['action']()
                time.sleep(3)
                
                # Check if we found manuscripts
                manuscript_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'CURRENT_STAGE_ID=')]")
                if manuscript_links:
                    print(f"   ✅ Success! Found {len(manuscript_links)} manuscripts")
                    
                    # List first few manuscripts
                    print("\n📄 Manuscripts found:")
                    for i, link in enumerate(manuscript_links[:3]):
                        ms_id = link.text.strip()
                        print(f"   {i+1}. {ms_id}")
                    
                    return True
                    
            except Exception as e:
                print(f"   ❌ Failed: {str(e)[:100]}")
                continue
        
        # If we're here, we couldn't find manuscripts
        print("\n❌ Could not navigate to manuscripts")
        
        # Save current page for debugging
        with open("navigation_debug.html", "w") as f:
            f.write(driver.page_source)
        print("💾 Saved current page to navigation_debug.html")
        
        # Print all links on the page
        print("\n🔍 All links on current page:")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links[:20]:  # First 20 links
            text = link.text.strip()
            href = link.get_attribute('href')
            if text and href:
                print(f"   '{text}' -> {href[:80]}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n⏸️  Browser will close in 15 seconds...")
        time.sleep(15)
        driver.quit()

if __name__ == "__main__":
    fix_navigation()
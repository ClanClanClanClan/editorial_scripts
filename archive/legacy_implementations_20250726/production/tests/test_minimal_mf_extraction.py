#!/usr/bin/env python3
"""
Minimal test of MF extraction to debug login and referee issues
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Load credentials properly
from src.core.secure_credentials import SecureCredentialManager

def test_minimal_extraction():
    """Test minimal extraction flow"""
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Not headless for debugging
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    
    try:
        # Load credentials from secure storage
        print("🔐 Loading credentials...")
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()
        
        # Also set as env vars for MF extractor compatibility
        os.environ['MF_EMAIL'] = email
        os.environ['MF_PASSWORD'] = password
        print("✅ Credentials loaded")
        
        # Step 1: Login
        print("\n🔐 Step 1: Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Handle cookie banner
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            print("   ✅ Rejected cookies")
        except:
            print("   No cookie banner")
        
        # Clear and fill fields
        userid_field = driver.find_element(By.ID, "USERID")
        password_field = driver.find_element(By.ID, "PASSWORD")
        
        userid_field.clear()
        password_field.clear()
        time.sleep(0.5)
        
        userid_field.send_keys(email)
        password_field.send_keys(password)
        
        # Click login
        driver.execute_script("document.getElementById('logInButton').click();")
        print("   ✅ Clicked login")
        time.sleep(5)
        
        # Check if we're logged in
        if "Welcome" in driver.page_source and "Log Out" not in driver.page_source:
            print("   ❌ Still on login page!")
            # Save for debugging
            with open("login_failed_page.html", "w") as f:
                f.write(driver.page_source)
            return
            
        print("   ✅ Login successful!")
        
        # Step 2: Navigate to AE Center
        print("\n📊 Step 2: Navigating to AE Center...")
        
        # First check if we need to select a role
        role_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ROLE=') and contains(text(), 'Associate Editor')]")
        if role_links:
            print("   Found role selection, clicking Associate Editor...")
            role_links[0].click()
            time.sleep(3)
        
        # Try to find AE center link
        ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor Center')]")
        if ae_links:
            print("   ✅ Found AE Center link, clicking...")
            ae_links[0].click()
            time.sleep(3)
        else:
            # Try direct navigation
            print("   Trying direct navigation...")
            driver.get("https://mc.manuscriptcentral.com/mafi?NEXT_PAGE=ASSOCIATE_EDITOR_MAIN_MENU")
            time.sleep(3)
        
        # Step 3: Find manuscripts
        print("\n📄 Step 3: Finding manuscripts...")
        manuscript_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'CURRENT_STAGE_ID=')]")
        
        if not manuscript_links:
            print("   ❌ No manuscripts found!")
            # Try to find any manuscript table
            tables = driver.find_elements(By.XPATH, "//table[contains(@class, 'datatable')]")
            print(f"   Found {len(tables)} data tables")
            return
            
        print(f"   ✅ Found {len(manuscript_links)} manuscripts")
        
        # Click first manuscript
        manuscript_links[0].click()
        time.sleep(3)
        
        # Step 4: Look for referees
        print("\n👥 Step 4: Looking for referees...")
        
        # Find referee table
        referee_rows = driver.find_elements(By.XPATH, "//td[@class='tablelines']//tr[.//a[contains(@href,'mailpopup')]]")
        print(f"   Found {len(referee_rows)} referee rows")
        
        if referee_rows:
            # Test first referee
            row = referee_rows[0]
            name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
            referee_name = name_link.text.strip()
            print(f"   First referee: {referee_name}")
            
            # Get link info
            href = name_link.get_attribute('href')
            print(f"   Link href: {href[:100]}...")
            
            # Try to click and get email
            current_window = driver.current_window_handle
            windows_before = len(driver.window_handles)
            
            print("   Clicking referee name...")
            if href.startswith('javascript:'):
                js_code = href.replace('javascript:', '')
                driver.execute_script(js_code)
            else:
                name_link.click()
            
            time.sleep(3)
            
            # Check if popup opened
            windows_after = len(driver.window_handles)
            if windows_after > windows_before:
                print("   ✅ Popup opened!")
                driver.switch_to.window(driver.window_handles[-1])
                
                # Save popup HTML
                with open("referee_popup.html", "w") as f:
                    f.write(driver.page_source)
                print("   💾 Saved popup HTML")
                
                # Close popup
                driver.close()
                driver.switch_to.window(current_window)
            else:
                print("   ❌ No popup opened!")
        
        print("\n✅ Test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n⏸️  Browser will close in 10 seconds...")
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    test_minimal_extraction()
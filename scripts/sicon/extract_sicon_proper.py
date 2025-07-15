#!/usr/bin/env python3
"""
SICON Proper Extractor - Step by step, honest reporting
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Load environment variables
project_root = Path(__file__).parent
load_dotenv(project_root / ".env.production")

def remove_cookie_modal(driver):
    """Remove cookie/privacy modal."""
    try:
        # Try to remove the overlay background
        cookie_bg = driver.find_element(By.ID, "cookie-policy-layer-bg")
        driver.execute_script("arguments[0].remove();", cookie_bg)
        print("✅ Removed cookie overlay background")
        return True
    except:
        pass
    
    # Try to click accept buttons
    selectors = [
        "#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "button[class*='accept']",
        "//button[contains(text(), 'Accept')]",
        "//button[contains(text(), 'OK')]"
    ]
    
    for selector in selectors:
        try:
            if selector.startswith("//"):
                element = driver.find_element(By.XPATH, selector)
            else:
                element = driver.find_element(By.CSS_SELECTOR, selector)
            
            element.click()
            print(f"✅ Clicked accept button: {selector}")
            return True
        except:
            continue
    
    print("ℹ️ No cookie modal found")
    return False

def extract_sicon_data():
    """Extract SICON data step by step."""
    driver = None
    try:
        # Step 1: Create driver
        print("🚀 Step 1: Creating Chrome driver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 20)
        
        # Step 2: Navigate to SICON
        print("📍 Step 2: Navigating to SICON...")
        driver.get("https://sicon.siam.org/cgi-bin/main.plex")
        time.sleep(3)
        print(f"✅ Current URL: {driver.current_url}")
        
        # Step 3: Remove cookie modal
        print("🍪 Step 3: Removing privacy/cookie modal...")
        remove_cookie_modal(driver)
        time.sleep(1)
        
        # Step 4: Click ORCID button
        print("🔍 Step 4: Finding and clicking ORCID button...")
        try:
            orcid_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='orcid']")))
            orcid_url = orcid_link.get_attribute('href')
            print(f"✅ Found ORCID link: {orcid_url}")
            
            driver.execute_script("arguments[0].click();", orcid_link)
            time.sleep(5)
            print(f"✅ Clicked ORCID, current URL: {driver.current_url}")
            
            if "orcid.org" not in driver.current_url:
                print("❌ FAILED: Not redirected to ORCID")
                return False
                
        except Exception as e:
            print(f"❌ FAILED: Could not find ORCID button: {e}")
            return False
        
        # Step 5: Remove ORCID cookie modal
        print("🍪 Step 5: Removing ORCID cookie/privacy modal...")
        remove_cookie_modal(driver)
        time.sleep(2)
        
        # Step 6: Enter credentials
        print("🔑 Step 6: Entering credentials...")
        orcid_email = os.getenv("ORCID_EMAIL")
        orcid_password = os.getenv("ORCID_PASSWORD")
        
        if not orcid_email or not orcid_password:
            print("❌ FAILED: No ORCID credentials found")
            return False
        
        try:
            # Email field
            email_field = wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            email_field.clear()
            email_field.send_keys(orcid_email)
            print("✅ Email entered")
            
            # Password field
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(orcid_password)
            print("✅ Password entered")
            
            # Submit
            password_field.send_keys(Keys.RETURN)
            print("✅ Form submitted")
            
        except Exception as e:
            print(f"❌ FAILED: Could not enter credentials: {e}")
            return False
        
        # Step 7: Wait for authentication
        print("⏳ Step 7: Waiting for authentication...")
        time.sleep(10)
        
        current_url = driver.current_url
        print(f"Current URL after login: {current_url}")
        
        # Handle authorization if needed
        if "authorize" in current_url:
            print("🔓 Handling authorization...")
            try:
                auth_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
                auth_btn.click()
                print("✅ Authorization granted")
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ Authorization failed: {e}")
        
        # Step 8: Verify we're back on SICON
        print("🔍 Step 8: Verifying return to SICON...")
        final_url = driver.current_url
        print(f"Final URL: {final_url}")
        
        if "sicon" not in final_url.lower():
            print("❌ FAILED: Not returned to SICON")
            return False
        
        print("✅ SUCCESS: Back on SICON")
        
        # Step 9: Remove cookie modal again
        print("🍪 Step 9: Removing cookie modal again...")
        time.sleep(2)
        remove_cookie_modal(driver)
        
        # Step 10: Navigate to Associate Editor Tasks
        print("📂 Step 10: Looking for Associate Editor Tasks section...")
        
        # Look for the specific section
        try:
            assoc_ed_section = driver.find_element(By.CSS_SELECTOR, "tbody[role='assoc_ed']")
            print("✅ Found Associate Editor Tasks section")
            
            # Find the folder links
            folder_links = assoc_ed_section.find_elements(By.CSS_SELECTOR, "a.ndt_folder_link")
            print(f"✅ Found {len(folder_links)} folder links")
            
            # Process each folder
            for link in folder_links:
                try:
                    link_text = link.text.strip()
                    
                    # Find the folder name
                    parent_row = link.find_element(By.XPATH, "./../..")
                    folder_span = parent_row.find_element(By.CSS_SELECTOR, "span.ndt_title")
                    folder_name = folder_span.text.strip()
                    
                    print(f"📁 {folder_name}: {link_text}")
                    
                    # Click on folders with content
                    if "AE" in link_text and link_text != "0 AE":
                        print(f"🔍 Clicking on {folder_name} ({link_text})...")
                        
                        # Save current page
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_dir = project_root / "output" / f"proper_sicon_{timestamp}"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Click the folder
                        driver.execute_script("arguments[0].click();", link)
                        time.sleep(3)
                        
                        # Save the page
                        folder_file = output_dir / f"{folder_name.replace(' ', '_').lower()}.html"
                        with open(folder_file, 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        
                        print(f"✅ Saved {folder_name} page to {folder_file}")
                        
                        # Check what's in the page
                        page_text = driver.page_source
                        if "manuscript" in page_text.lower() or "MS-" in page_text:
                            print(f"✅ Found manuscript data in {folder_name}")
                        else:
                            print(f"⚠️ No manuscript data visible in {folder_name}")
                        
                        # Go back
                        driver.back()
                        time.sleep(2)
                        
                        # Re-find the section after navigation
                        assoc_ed_section = driver.find_element(By.CSS_SELECTOR, "tbody[role='assoc_ed']")
                        folder_links = assoc_ed_section.find_elements(By.CSS_SELECTOR, "a.ndt_folder_link")
                
                except Exception as e:
                    print(f"❌ Error processing folder: {e}")
                    continue
            
            print("✅ SUCCESS: Processed all folders")
            return True
            
        except Exception as e:
            print(f"❌ FAILED: Could not find Associate Editor Tasks section: {e}")
            return False
        
    except Exception as e:
        print(f"❌ FAILED: General error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            print("🔧 Keeping browser open for inspection...")
            time.sleep(15)
            driver.quit()

if __name__ == "__main__":
    print("🚀 SICON PROPER EXTRACTION")
    print("=" * 50)
    
    success = extract_sicon_data()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 EXTRACTION COMPLETED")
    else:
        print("❌ EXTRACTION FAILED")
    print("=" * 50)
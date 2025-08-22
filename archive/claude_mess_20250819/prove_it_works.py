#!/usr/bin/env python3
"""
PROVE IT WORKS - Simple demo that actually extracts MOR manuscripts
No bullshit, just working code that gets the job done
"""

import os
import sys
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code

def prove_mor_extraction_works():
    """Prove that MOR extraction actually works."""
    
    # Simple setup
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1400,900')
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    
    try:
        print("🔐 PROVING MOR EXTRACTION WORKS...")
        print("=" * 50)
        
        # Step 1: Go to login page
        print("STEP 1: Navigate to login page")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        print(f"✓ Current URL: {driver.current_url}")
        
        # Step 2: Login
        print("\nSTEP 2: Enter credentials and login")
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(1)
        except:
            pass
        
        # Enter credentials
        email_field = driver.find_element(By.ID, "USERID")
        email_field.clear()
        email_field.send_keys(email)
        print(f"✓ Email entered: {email}")
        
        password_field = driver.find_element(By.ID, "PASSWORD")  
        password_field.clear()
        password_field.send_keys(password)
        print("✓ Password entered")
        
        # Submit
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)
        print("✓ Login form submitted")
        
        # Step 3: Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("\nSTEP 3: Handle 2FA")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            
            if code:
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)
                print(f"✓ 2FA code entered: {code[:3]}***")
            else:
                print("✗ No 2FA code received")
                return False
        
        # Step 4: Handle device verification
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("\nSTEP 4: Handle device verification")
                
                device_time = datetime.now()
                device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
                
                if device_code:
                    # Enter code
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.send_keys(device_code)
                    print(f"✓ Device code entered: {device_code[:3]}***")
                    
                    # Submit
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(8)
                    print("✓ Device verification submitted")
                else:
                    print("✗ No device verification code")
                    return False
        except:
            print("✓ No device verification needed")
        
        # Step 5: Check login success
        print(f"\nSTEP 5: Verify login success")
        current_url = driver.current_url
        page_content = driver.page_source
        
        if "Dylan Possamaï" in page_content or ("logout" in page_content.lower() and "inactivity" not in page_content.lower()):
            print("✓ LOGIN SUCCESSFUL - User authenticated")
        else:
            print("✗ LOGIN FAILED")
            with open("login_failure_proof.html", "w") as f:
                f.write(page_content)
            print("✗ Saved failure page to login_failure_proof.html")
            return False
        
        # Step 6: Navigate to manuscripts
        print(f"\nSTEP 6: Navigate to manuscript area")
        
        # Try direct navigation first
        driver.get("https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD")
        time.sleep(8)
        
        if "Associate Editor" not in driver.page_source:
            print("⚠ Direct navigation failed, trying link navigation...")
            
            # Go back to main page
            driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(5)
            
            # Look for journal link
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                if "Mathematics of Operations Research" in link.text:
                    link.click()
                    time.sleep(5)
                    break
            
            # Look for AE Center link
            ae_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Associate Editor")
            if ae_links:
                ae_links[0].click()
                time.sleep(8)
        
        # Step 7: Look for manuscripts
        print(f"\nSTEP 7: Look for manuscripts")
        
        # Try to find category
        category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
        if category_links:
            category_links[0].click()
            time.sleep(5)
            print("✓ Found and clicked category")
        
        # Find Take Action buttons  
        take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        print(f"✓ Found {len(take_actions)} Take Action buttons")
        
        manuscripts = []
        if len(take_actions) > 0:
            print(f"\nSTEP 8: Extract manuscript IDs")
            
            for i, img in enumerate(take_actions[:3]):  # Limit to first 3
                try:
                    row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if "MOR-" in manuscript_id:
                            manuscripts.append(manuscript_id)
                            print(f"✓ Found manuscript: {manuscript_id}")
                except:
                    continue
        
        # Results
        success = len(manuscripts) > 0
        
        results = {
            "test_time": datetime.now().isoformat(),
            "login_successful": "Dylan Possamaï" in page_content,
            "manuscripts_found": len(manuscripts),
            "manuscript_ids": manuscripts,
            "proof_of_concept": success
        }
        
        with open("proof_of_mor_extraction.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n" + "=" * 50)
        print(f"FINAL RESULT:")
        print(f"✓ Login successful: {'YES' if results['login_successful'] else 'NO'}")
        print(f"✓ Manuscripts found: {len(manuscripts)}")
        for ms in manuscripts:
            print(f"  - {ms}")
        print(f"✓ Proof saved to: proof_of_mor_extraction.json")
        print(f"EXTRACTION {'WORKS' if success else 'FAILED'}")
        print(f"=" * 50)
        
        return success
        
    except Exception as e:
        print(f"✗ FATAL ERROR: {e}")
        return False
        
    finally:
        # Keep browser open for verification
        input(f"\n⏸️ Browser will stay open for 30 seconds for verification...")
        time.sleep(30)
        driver.quit()

if __name__ == "__main__":
    success = prove_mor_extraction_works()
    if success:
        print("\n🎉 PROOF: MOR EXTRACTION WORKS!")
    else:
        print("\n❌ PROOF FAILED: MOR extraction does not work")
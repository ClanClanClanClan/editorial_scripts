#!/usr/bin/env python3
"""
Simple test to debug SICON authentication
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()

# Setup driver
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    print("1. Going to SICON...")
    driver.get("http://sicon.siam.org")
    time.sleep(5)
    driver.save_screenshot("01_sicon_initial.png")
    
    # Handle privacy notification
    try:
        privacy_button = driver.find_element(By.XPATH, "//input[@value='Continue']")
        privacy_button.click()
        print("2. Clicked privacy notification")
        time.sleep(3)
        driver.save_screenshot("02_after_privacy.png")
    except:
        print("2. No privacy notification")
    
    # Check if already authenticated
    if 'associate editor tasks' in driver.page_source.lower():
        print("✅ Already authenticated!")
    else:
        # Find ORCID link
        print("3. Looking for ORCID link...")
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        print(f"   Found ORCID link: {orcid_link.get_attribute('href')}")
        
        # Click it
        driver.execute_script("arguments[0].click();", orcid_link)
        print("4. Clicked ORCID link")
        time.sleep(5)
        
        print(f"5. Current URL: {driver.current_url}")
        driver.save_screenshot("03_after_orcid_click.png")
        
        if 'orcid.org' in driver.current_url:
            print("6. On ORCID page")
            
            # Try to accept cookies first
            try:
                # Wait for cookie banner
                cookie_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]")))
                cookie_button.click()
                print("7. Accepted cookies")
                time.sleep(3)
                driver.save_screenshot("04_after_cookies.png")
            except:
                print("7. No cookie banner or already accepted")
            
            # Now look for login fields with explicit wait
            print("8. Looking for login fields...")
            
            # Try multiple strategies with waits
            username_field = None
            strategies = [
                (By.ID, "username"),
                (By.ID, "userId"),
                (By.NAME, "username"),
                (By.NAME, "userId"),
                (By.XPATH, "//input[@type='text'][@name='userId']"),
                (By.XPATH, "//input[@type='email']"),
                (By.XPATH, "//input[contains(@placeholder, 'Email')]"),
                (By.XPATH, "//input[contains(@placeholder, 'ORCID')]")
            ]
            
            for strategy, selector in strategies:
                try:
                    print(f"   Trying: {strategy} - {selector}")
                    username_field = wait.until(EC.presence_of_element_located((strategy, selector)))
                    print(f"   ✅ Found username field with: {strategy} - {selector}")
                    break
                except:
                    continue
            
            if username_field:
                print("9. Filling credentials...")
                username = os.getenv('ORCID_USER')
                password = os.getenv('ORCID_PASS')
                
                username_field.clear()
                username_field.send_keys(username)
                
                # Find password field
                password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                password_field.clear()
                password_field.send_keys(password)
                
                print("10. Credentials filled")
                driver.save_screenshot("05_credentials_filled.png")
                
                # Find sign in button
                signin_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')] | //button[@type='submit']")
                signin_button.click()
                print("11. Clicked sign in")
                
                time.sleep(8)
                driver.save_screenshot("06_after_signin.png")
                print(f"12. Final URL: {driver.current_url}")
            else:
                print("❌ Could not find username field!")
                # Save page source for debugging
                with open("orcid_page_source.html", "w") as f:
                    f.write(driver.page_source)
                print("   Saved page source to orcid_page_source.html")
        
except Exception as e:
    print(f"❌ Error: {e}")
    driver.save_screenshot("error_screenshot.png")
    with open("error_page_source.html", "w") as f:
        f.write(driver.page_source)
finally:
    input("Press Enter to close browser...")
    driver.quit()
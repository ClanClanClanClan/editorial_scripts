#!/usr/bin/env python3
"""
Test ORCID button identification
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
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    # Navigate directly to ORCID
    driver.get("https://orcid.org/signin")
    time.sleep(3)
    
    # Accept cookies
    try:
        cookie_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]")))
        cookie_button.click()
        print("✅ Accepted cookies")
        time.sleep(2)
    except:
        print("No cookie banner")
    
    # Find all buttons and print their text
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"\nFound {len(buttons)} buttons:")
    for i, button in enumerate(buttons):
        text = button.text
        if text:
            print(f"  Button {i}: '{text}'")
            # Also print any aria-label
            aria_label = button.get_attribute('aria-label')
            if aria_label:
                print(f"    aria-label: '{aria_label}'")
    
    # Also check for input type submit
    submits = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
    print(f"\nFound {len(submits)} submit inputs:")
    for i, submit in enumerate(submits):
        value = submit.get_attribute('value')
        print(f"  Submit {i}: value='{value}'")
    
    # Save page source for analysis
    with open("orcid_signin_page.html", "w") as f:
        f.write(driver.page_source)
    print("\nSaved page source to orcid_signin_page.html")
    
    driver.save_screenshot("orcid_signin_page.png")
    print("Saved screenshot to orcid_signin_page.png")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()
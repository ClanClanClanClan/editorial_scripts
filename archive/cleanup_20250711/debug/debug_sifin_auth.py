#!/usr/bin/env python3
"""
Debug SIFIN authentication
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os

def debug_sifin_auth():
    """Debug SIFIN authentication step by step"""
    
    print("SIFIN Authentication Debug")
    print("=" * 60)
    
    # Set up driver in visible mode
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # Step 1: Navigate to SIFIN
        print("\n1. Navigating to SIFIN...")
        driver.get("https://sifin.siam.org/cgi-bin/main.plex")
        time.sleep(3)
        
        # Save screenshot
        driver.save_screenshot("sifin_1_initial.png")
        print("   Screenshot saved: sifin_1_initial.png")
        
        # Step 2: Look for login options
        print("\n2. Looking for login options...")
        
        # Find all links and buttons
        links = driver.find_elements(By.TAG_NAME, "a")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        inputs = driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']")
        
        print(f"   Found {len(links)} links, {len(buttons)} buttons, {len(inputs)} input buttons")
        
        # Look for Author/Editor/Referee login
        author_login = None
        for link in links:
            text = link.text.strip()
            if "Author" in text and "Editor" in text and "Referee" in text:
                print(f"   Found login link: {text}")
                author_login = link
                break
        
        if author_login:
            print("\n3. Clicking Author/Editor/Referee Login...")
            author_login.click()
            time.sleep(3)
            
            driver.save_screenshot("sifin_2_after_login_click.png")
            print("   Screenshot saved: sifin_2_after_login_click.png")
        
        # Step 4: Look for ORCID option
        print("\n4. Looking for ORCID sign-in option...")
        
        # Check page source for ORCID
        page_source = driver.page_source.lower()
        print(f"   'orcid' in page: {'orcid' in page_source}")
        print(f"   'sign in with orcid' in page: {'sign in with orcid' in page_source}")
        
        # Try to find ORCID button/link
        orcid_element = None
        
        # Try different selectors
        selectors = [
            "//button[contains(., 'ORCID')]",
            "//a[contains(., 'ORCID')]",
            "//input[contains(@value, 'ORCID')]",
            "//button[contains(text(), 'Sign in')]",
            "//a[contains(text(), 'Sign in with ORCID')]",
            "//*[contains(text(), 'ORCID')]"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"   Found {len(elements)} elements with selector: {selector}")
                    for elem in elements:
                        print(f"     - Text: {elem.text}")
                        print(f"     - Tag: {elem.tag_name}")
                        if elem.tag_name in ['button', 'a', 'input'] and not orcid_element:
                            orcid_element = elem
            except:
                pass
        
        if orcid_element:
            print(f"\n5. Found ORCID element: {orcid_element.tag_name} - {orcid_element.text}")
            print("   Clicking ORCID sign-in...")
            orcid_element.click()
            time.sleep(3)
            
            driver.save_screenshot("sifin_3_after_orcid_click.png")
            print("   Screenshot saved: sifin_3_after_orcid_click.png")
            
            # Check if we're on ORCID page
            print(f"\n6. Current URL: {driver.current_url}")
            print(f"   On ORCID site: {'orcid.org' in driver.current_url}")
        else:
            print("\n❌ Could not find ORCID sign-in option!")
            print("   Page might have different authentication method")
        
        print("\n7. Current page title:", driver.title)
        
        # Wait for user input
        print("\nDebug complete. Press Enter to close browser...")
        input()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        driver.save_screenshot("sifin_error.png")
        print("   Error screenshot saved: sifin_error.png")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_sifin_auth()
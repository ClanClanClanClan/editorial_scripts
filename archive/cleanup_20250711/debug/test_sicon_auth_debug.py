#!/usr/bin/env python3
"""
Debug SICON authentication step by step
"""

from journals.sicon import SICON
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sicon_auth_debug():
    """Debug SICON authentication step by step"""
    print("=" * 60)
    print("DEBUGGING SICON AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Create and setup SICON
        sicon = SICON()
        sicon.setup_driver(headless=False)  # Use visible mode for debugging
        
        print("\n1. Navigating to SICON login page...")
        login_url = f"{sicon.config['base_url']}/cgi-bin/main.plex"
        print(f"URL: {login_url}")
        
        sicon.driver.get(login_url)
        time.sleep(3)
        
        print(f"Current URL: {sicon.driver.current_url}")
        print(f"Page title: {sicon.driver.title}")
        
        # Look for Author/Editor/Referee Login
        print("\n2. Looking for Author/Editor/Referee Login...")
        try:
            author_login_links = sicon.driver.find_elements(By.XPATH, "//a[contains(text(), 'Author/Editor/Referee Login')]")
            print(f"Found {len(author_login_links)} Author/Editor/Referee Login links")
            
            if author_login_links:
                author_login = author_login_links[0]
                print(f"Found login link: {author_login.get_attribute('href')}")
                print("Clicking Author/Editor/Referee Login...")
                author_login.click()
                time.sleep(3)
                
                print(f"After click - URL: {sicon.driver.current_url}")
                print(f"After click - Title: {sicon.driver.title}")
            else:
                print("❌ No Author/Editor/Referee Login link found")
                
                # Check what links are available
                all_links = sicon.driver.find_elements(By.TAG_NAME, "a")
                print(f"Available links on page:")
                for i, link in enumerate(all_links[:10]):  # Show first 10 links
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    if text:
                        print(f"  {i+1}. {text} -> {href}")
                return False
        except Exception as e:
            print(f"❌ Error finding Author/Editor/Referee Login: {e}")
            return False
        
        # Look for ORCID sign-in
        print("\n3. Looking for ORCID sign-in...")
        try:
            # Try different ORCID selectors
            orcid_selectors = [
                "//button[contains(., 'Sign in to ORCID')]",
                "//button[contains(., 'ORCID')]",
                "//input[@type='button' and contains(@value, 'ORCID')]",
                "//a[contains(text(), 'Sign in with ORCID')]",
                "//a[contains(@href, 'orcid')]"
            ]
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    elements = sicon.driver.find_elements(By.XPATH, selector)
                    if elements:
                        orcid_element = elements[0]
                        print(f"✅ Found ORCID element with selector: {selector}")
                        if orcid_element.get_attribute('href'):
                            print(f"   href: {orcid_element.get_attribute('href')}")
                        if orcid_element.get_attribute('value'):
                            print(f"   value: {orcid_element.get_attribute('value')}")
                        print(f"   text: {orcid_element.text}")
                        break
                except:
                    print(f"❌ Selector failed: {selector}")
                    continue
            
            if not orcid_element:
                print("❌ No ORCID sign-in element found")
                
                # Show all buttons and links
                buttons = sicon.driver.find_elements(By.TAG_NAME, "button")
                inputs = sicon.driver.find_elements(By.XPATH, "//input[@type='button']")
                links = sicon.driver.find_elements(By.TAG_NAME, "a")
                
                print(f"Available buttons:")
                for i, btn in enumerate(buttons):
                    text = btn.text.strip()
                    value = btn.get_attribute('value')
                    if text or value:
                        print(f"  {i+1}. {text} (value: {value})")
                
                print(f"Available input buttons:")
                for i, inp in enumerate(inputs):
                    value = inp.get_attribute('value')
                    if value:
                        print(f"  {i+1}. {value}")
                
                print(f"Available links containing 'orcid':")
                for i, link in enumerate(links):
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    if href and 'orcid' in href.lower():
                        print(f"  {i+1}. {text} -> {href}")
                
                return False
            
            print("4. Clicking ORCID sign-in...")
            sicon.driver.execute_script("arguments[0].click();", orcid_element)
            time.sleep(3)
            
            print(f"After ORCID click - URL: {sicon.driver.current_url}")
            print(f"After ORCID click - Title: {sicon.driver.title}")
            
            # Check if we're on ORCID login page
            if 'orcid.org' in sicon.driver.current_url:
                print("✅ Successfully redirected to ORCID")
                return True
            else:
                print("❌ Not redirected to ORCID")
                return False
            
        except Exception as e:
            print(f"❌ Error with ORCID sign-in: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        input("Press Enter to continue...")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            sicon.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_sicon_auth_debug()
    print(f"\nSICON Authentication Debug Result: {'SUCCESS' if success else 'FAILED'}")
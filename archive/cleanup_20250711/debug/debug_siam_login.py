#!/usr/bin/env python3
"""
SIAM Login Debug Script

This script provides detailed debugging of the ORCID login process
and manuscript discovery for SICON and SIFIN journals.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'siam_login_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SIAMLoginDebugger:
    """Debug SIAM ORCID login and manuscript discovery."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.screenshots_dir = Path('./debug_screenshots')
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def setup_driver(self, headless: bool = False):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 15)
        
        print("✅ Chrome WebDriver initialized")
    
    def take_screenshot(self, name: str):
        """Take a screenshot for debugging."""
        if self.driver:
            screenshot_path = self.screenshots_dir / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
            self.driver.save_screenshot(str(screenshot_path))
            print(f"📸 Screenshot saved: {screenshot_path.name}")
    
    def _remove_cookie_banners(self):
        """Remove cookie banners using JavaScript."""
        js_hide = """
        // Remove various cookie banners
        var selectors = [
            '#cookie-policy-layer-bg',
            '#cookie-policy-layer',
            '.cc_banner-wrapper',
            '#onetrust-banner-sdk',
            '.onetrust-pc-dark-filter',
            '.cookie-banner',
            '.gdpr-banner'
        ];
        
        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.remove();
            });
        });
        
        // Also try to click accept buttons
        var acceptButtons = [
            'button[id*="accept"]',
            'button[class*="accept"]',
            'button[class*="cookie"]',
            'a[id*="accept"]',
            'a[class*="accept"]'
        ];
        
        acceptButtons.forEach(function(selector) {
            var buttons = document.querySelectorAll(selector);
            buttons.forEach(function(btn) {
                if (btn.textContent.toLowerCase().includes('accept') || 
                    btn.textContent.toLowerCase().includes('agree') ||
                    btn.textContent.toLowerCase().includes('ok')) {
                    btn.click();
                }
            });
        });
        """
        
        try:
            self.driver.execute_script(js_hide)
            print("   🍪 Cookie banners removed")
        except Exception as e:
            print(f"   ⚠️ Cookie banner removal failed: {e}")
    
    def debug_sicon_login(self) -> bool:
        """Debug SICON login process with detailed steps."""
        print("\n" + "="*60)
        print("🔍 DEBUGGING SICON LOGIN PROCESS")
        print("="*60)
        
        try:
            # Step 1: Navigate to SICON
            print("\n1️⃣ Navigating to SICON...")
            self.driver.get("http://sicon.siam.org")
            time.sleep(3)
            self.take_screenshot("sicon_initial")
            
            print(f"   Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            
            # Step 2: Remove cookie banners FIRST
            print("\n2️⃣ Removing cookie banners...")
            self._remove_cookie_banners()
            time.sleep(1)
            self.take_screenshot("sicon_after_cookie_removal")
            
            # Step 3: Look for login elements
            print("\n3️⃣ Looking for login elements...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all links containing 'orcid'
            orcid_links = soup.find_all('a', href=lambda x: x and 'orcid' in x.lower())
            print(f"   Found {len(orcid_links)} ORCID links:")
            for i, link in enumerate(orcid_links):
                print(f"     {i+1}. {link.get('href')} - Text: '{link.get_text(strip=True)}'")
            
            # Find all elements with 'orcid' in text
            orcid_text_elements = soup.find_all(text=lambda x: x and 'orcid' in x.lower())
            print(f"   Found {len(orcid_text_elements)} elements with ORCID text")
            
            # Step 4: Try to click ORCID login
            print("\n4️⃣ Attempting ORCID login...")
            orcid_clicked = False
            
            # Method 1: Click via Selenium
            try:
                orcid_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
                print(f"   Found ORCID element: {orcid_element.get_attribute('href')}")
                
                # Ensure element is visible and clickable
                self.driver.execute_script("arguments[0].scrollIntoView(true);", orcid_element)
                time.sleep(1)
                
                orcid_element.click()
                orcid_clicked = True
                print("   ✅ Clicked ORCID login link")
                time.sleep(3)
                self.take_screenshot("sicon_after_orcid_click")
            except Exception as e:
                print(f"   ❌ Could not click ORCID link: {e}")
                
                # Try JavaScript click as fallback
                try:
                    orcid_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
                    self.driver.execute_script("arguments[0].click();", orcid_element)
                    orcid_clicked = True
                    print("   ✅ Clicked ORCID login link via JavaScript")
                    time.sleep(3)
                    self.take_screenshot("sicon_after_js_click")
                except Exception as e2:
                    print(f"   ❌ JavaScript click also failed: {e2}")
            
            if not orcid_clicked:
                print("   ⚠️ Could not initiate ORCID login")
                return False
            
            # Step 5: Handle ORCID authentication
            print("\n5️⃣ Handling ORCID authentication...")
            print(f"   Current URL: {self.driver.current_url}")
            
            if 'orcid.org' in self.driver.current_url:
                print("   📍 Redirected to ORCID.org - proceeding with authentication")
                
                # Fill in ORCID credentials
                orcid_user = os.getenv("ORCID_USER")
                orcid_pass = os.getenv("ORCID_PASS")
                
                if not orcid_user or not orcid_pass:
                    print("   ❌ ORCID credentials not available")
                    return False
                
                # Try multiple possible username field selectors
                username_field = None
                username_selectors = [
                    (By.ID, "username"),
                    (By.ID, "userId"), 
                    (By.NAME, "userId"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']")
                ]
                
                for selector_type, selector_value in username_selectors:
                    try:
                        username_field = self.wait.until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        print(f"   ✅ Found username field with selector: {selector_type}, {selector_value}")
                        break
                    except:
                        continue
                
                if not username_field:
                    print("   ❌ Could not find username field")
                    self.take_screenshot("sicon_orcid_username_error")
                    return False
                
                username_field.clear()
                username_field.send_keys(orcid_user)
                print("   ✅ Filled ORCID username")
                
                # Try multiple possible password field selectors
                password_field = None
                password_selectors = [
                    (By.ID, "password"),
                    (By.NAME, "password"),
                    (By.CSS_SELECTOR, "input[type='password']")
                ]
                
                for selector_type, selector_value in password_selectors:
                    try:
                        password_field = self.driver.find_element(selector_type, selector_value)
                        print(f"   ✅ Found password field with selector: {selector_type}, {selector_value}")
                        break
                    except:
                        continue
                
                if not password_field:
                    print("   ❌ Could not find password field")
                    self.take_screenshot("sicon_orcid_password_error")
                    return False
                
                password_field.clear()
                password_field.send_keys(orcid_pass)
                print("   ✅ Filled ORCID password")
                
                self.take_screenshot("sicon_orcid_filled")
                
                # Try multiple possible submit button selectors
                submit_button = None
                submit_selectors = [
                    (By.ID, "signin-button"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                    (By.XPATH, "//button[contains(text(), 'SIGN IN')]"),
                    (By.XPATH, "//input[@type='submit']")
                ]
                
                for selector_type, selector_value in submit_selectors:
                    try:
                        submit_button = self.driver.find_element(selector_type, selector_value)
                        print(f"   ✅ Found submit button with selector: {selector_type}, {selector_value}")
                        break
                    except:
                        continue
                
                if not submit_button:
                    print("   ❌ Could not find submit button")
                    return False
                
                submit_button.click()
                print("   ✅ Clicked ORCID signin button")
                time.sleep(3)
                self.take_screenshot("sicon_orcid_submitted")
                
                # Wait for redirect back to SICON
                print("   ⏳ Waiting for redirect back to SICON...")
                start_time = time.time()
                while time.time() - start_time < 30:
                    if 'sicon.siam.org' in self.driver.current_url:
                        print("   ✅ Successfully redirected back to SICON")
                        break
                    time.sleep(1)
                else:
                    print("   ❌ Timeout waiting for redirect to SICON")
                    return False
            
            # Step 6: Check if login was successful
            print("\n6️⃣ Verifying login success...")
            self.take_screenshot("sicon_after_login")
            print(f"   Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            
            # Look for dashboard elements
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Check for various dashboard indicators
            dashboard_indicators = [
                soup.find_all('tbody', attrs={'role': 'assoc_ed'}),
                soup.find_all('tr', class_='ndt_task'),
                soup.find_all('a', class_='ndt_task_link'),
                soup.find_all(text=lambda x: x and 'associate editor' in x.lower()),
                soup.find_all(text=lambda x: x and 'manuscript' in x.lower())
            ]
            
            print("   Dashboard elements found:")
            for i, elements in enumerate(dashboard_indicators):
                print(f"     Indicator {i+1}: {len(elements)} elements")
            
            # Look for manuscript information
            manuscript_elements = soup.find_all('a', href=lambda x: x and 'form_type=view_ms' in x)
            print(f"   Found {len(manuscript_elements)} manuscript links")
            
            for i, link in enumerate(manuscript_elements[:5]):  # Show first 5
                print(f"     {i+1}. {link.get_text(strip=True)} - {link.get('href')}")
            
            return len(manuscript_elements) > 0 or any(len(elements) > 0 for elements in dashboard_indicators)
            
        except Exception as e:
            print(f"❌ SICON login debugging failed: {e}")
            self.take_screenshot("sicon_error")
            return False
    
    def debug_sifin_login(self) -> bool:
        """Debug SIFIN login process with detailed steps."""
        print("\n" + "="*60)
        print("🔍 DEBUGGING SIFIN LOGIN PROCESS")
        print("="*60)
        
        try:
            # Step 1: Navigate to SIFIN
            print("\n1️⃣ Navigating to SIFIN...")
            self.driver.get("http://sifin.siam.org")
            time.sleep(3)
            self.take_screenshot("sifin_initial")
            
            print(f"   Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            
            # Step 2: Remove cookie banners FIRST
            print("\n2️⃣ Removing cookie banners...")
            self._remove_cookie_banners()
            time.sleep(1)
            self.take_screenshot("sifin_after_cookie_removal")
            
            # Step 3: Look for login elements
            print("\n3️⃣ Looking for login elements...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all links containing 'orcid'
            orcid_links = soup.find_all('a', href=lambda x: x and 'orcid' in x.lower())
            print(f"   Found {len(orcid_links)} ORCID links:")
            for i, link in enumerate(orcid_links):
                print(f"     {i+1}. {link.get('href')} - Text: '{link.get_text(strip=True)}'")
            
            # Step 4: Try to click ORCID login
            print("\n4️⃣ Attempting ORCID login...")
            orcid_clicked = False
            
            try:
                orcid_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
                print(f"   Found ORCID element: {orcid_element.get_attribute('href')}")
                
                # Ensure element is visible and clickable
                self.driver.execute_script("arguments[0].scrollIntoView(true);", orcid_element)
                time.sleep(1)
                
                orcid_element.click()
                orcid_clicked = True
                print("   ✅ Clicked ORCID login link")
                time.sleep(3)
                self.take_screenshot("sifin_after_orcid_click")
            except Exception as e:
                print(f"   ❌ Could not click ORCID link: {e}")
                
                # Try JavaScript click as fallback
                try:
                    orcid_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
                    self.driver.execute_script("arguments[0].click();", orcid_element)
                    orcid_clicked = True
                    print("   ✅ Clicked ORCID login link via JavaScript")
                    time.sleep(3)
                    self.take_screenshot("sifin_after_js_click")
                except Exception as e2:
                    print(f"   ❌ JavaScript click also failed: {e2}")
            
            if not orcid_clicked:
                print("   ⚠️ Could not initiate ORCID login")
                return False
            
            # Step 5: Handle ORCID authentication (similar to SICON)
            print("\n5️⃣ Handling ORCID authentication...")
            print(f"   Current URL: {self.driver.current_url}")
            
            if 'orcid.org' in self.driver.current_url:
                print("   📍 Redirected to ORCID.org - proceeding with authentication")
                
                orcid_user = os.getenv("ORCID_USER")
                orcid_pass = os.getenv("ORCID_PASS")
                
                if not orcid_user or not orcid_pass:
                    print("   ❌ ORCID credentials not available")
                    return False
                
                # Fill credentials and submit (similar process as SICON)
                try:
                    # Try multiple possible username field selectors
                    username_field = None
                    username_selectors = [
                        (By.ID, "username"),
                        (By.ID, "userId"), 
                        (By.NAME, "userId"),
                        (By.CSS_SELECTOR, "input[type='text']"),
                        (By.CSS_SELECTOR, "input[type='email']"),
                        (By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']")
                    ]
                    
                    for selector_type, selector_value in username_selectors:
                        try:
                            username_field = self.wait.until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            print(f"   ✅ Found username field with selector: {selector_type}, {selector_value}")
                            break
                        except:
                            continue
                    
                    if not username_field:
                        raise Exception("Could not find username field")
                    
                    username_field.clear()
                    username_field.send_keys(orcid_user)
                    print("   ✅ Filled username field")
                    
                    # Try multiple possible password field selectors
                    password_field = None
                    password_selectors = [
                        (By.ID, "password"),
                        (By.NAME, "password"),
                        (By.CSS_SELECTOR, "input[type='password']")
                    ]
                    
                    for selector_type, selector_value in password_selectors:
                        try:
                            password_field = self.driver.find_element(selector_type, selector_value)
                            print(f"   ✅ Found password field with selector: {selector_type}, {selector_value}")
                            break
                        except:
                            continue
                    
                    if not password_field:
                        raise Exception("Could not find password field")
                    
                    password_field.clear()
                    password_field.send_keys(orcid_pass)
                    print("   ✅ Filled password field")
                    
                    # Try multiple possible submit button selectors
                    submit_button = None
                    submit_selectors = [
                        (By.ID, "signin-button"),
                        (By.CSS_SELECTOR, "button[type='submit']"),
                        (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                        (By.XPATH, "//button[contains(text(), 'SIGN IN')]"),
                        (By.XPATH, "//input[@type='submit']")
                    ]
                    
                    for selector_type, selector_value in submit_selectors:
                        try:
                            submit_button = self.driver.find_element(selector_type, selector_value)
                            print(f"   ✅ Found submit button with selector: {selector_type}, {selector_value}")
                            break
                        except:
                            continue
                    
                    if not submit_button:
                        raise Exception("Could not find submit button")
                    
                    submit_button.click()
                    
                    print("   ✅ Submitted ORCID credentials")
                    time.sleep(3)
                    self.take_screenshot("sifin_orcid_submitted")
                    
                    # Wait for redirect
                    start_time = time.time()
                    while time.time() - start_time < 30:
                        if 'sifin.siam.org' in self.driver.current_url:
                            print("   ✅ Successfully redirected back to SIFIN")
                            break
                        time.sleep(1)
                    else:
                        print("   ❌ Timeout waiting for redirect to SIFIN")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ ORCID authentication failed: {e}")
                    return False
            
            # Step 6: Check if login was successful
            print("\n6️⃣ Verifying login success...")
            self.take_screenshot("sifin_after_login")
            print(f"   Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            
            # Look for dashboard elements
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            manuscript_elements = soup.find_all('a', href=lambda x: x and 'form_type=view_ms' in x)
            print(f"   Found {len(manuscript_elements)} manuscript links")
            
            return len(manuscript_elements) > 0
            
        except Exception as e:
            print(f"❌ SIFIN login debugging failed: {e}")
            self.take_screenshot("sifin_error")
            return False
    
    def run_debug_session(self, headless: bool = False):
        """Run complete debugging session."""
        print("🔬 SIAM Login Debug Session Started")
        print(f"📸 Screenshots will be saved to: {self.screenshots_dir}")
        
        try:
            self.setup_driver(headless=headless)
            
            # Check credentials
            orcid_user = os.getenv("ORCID_USER")
            orcid_pass = os.getenv("ORCID_PASS")
            
            if not orcid_user or not orcid_pass:
                print("❌ ORCID credentials not found in environment")
                return False
            
            print(f"✅ ORCID credentials available: {orcid_user}")
            
            # Debug SICON
            sicon_success = self.debug_sicon_login()
            
            # Debug SIFIN
            sifin_success = self.debug_sifin_login()
            
            print("\n" + "="*80)
            print("📊 DEBUG SESSION SUMMARY")
            print("="*80)
            print(f"✅ SICON Login: {'Success' if sicon_success else 'Failed'}")
            print(f"✅ SIFIN Login: {'Success' if sifin_success else 'Failed'}")
            print(f"📸 Screenshots saved to: {self.screenshots_dir}")
            
            return sicon_success and sifin_success
            
        except Exception as e:
            print(f"❌ Debug session failed: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔄 WebDriver closed")


def main():
    """Main debug entry point."""
    debugger = SIAMLoginDebugger()
    
    # Run debug session (set headless=False to see browser actions)
    success = debugger.run_debug_session(headless=False)
    
    if success:
        print("\n✅ Debug session completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Debug session found issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
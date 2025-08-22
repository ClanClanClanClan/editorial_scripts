"""ScholarOne authentication module extracted from legacy code."""

import os
import time
from typing import Optional, Tuple, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime


class ScholarOneAuthenticator:
    """
    Handles authentication for ScholarOne/ManuscriptCentral platforms.
    
    Supports:
    - Email/password login
    - 2FA verification via email
    - Device verification handling
    - Cookie banner dismissal
    """
    
    def __init__(self, browser_manager, gmail_manager=None):
        """
        Initialize authenticator.
        
        Args:
            browser_manager: SeleniumBrowserManager instance
            gmail_manager: Optional GmailManager for 2FA codes
        """
        self.browser = browser_manager
        self.driver = browser_manager.driver
        self.gmail = gmail_manager
        self.max_login_attempts = 3
        self.journal_configs = {
            'mf': {
                'url': 'https://mc.manuscriptcentral.com/mafi',
                'name': 'Mathematical Finance',
                'email_env': 'MF_EMAIL',
                'password_env': 'MF_PASSWORD'
            },
            'mor': {
                'url': 'https://mc.manuscriptcentral.com/mor',
                'name': 'Mathematics of Operations Research',
                'email_env': 'MOR_EMAIL',
                'password_env': 'MOR_PASSWORD'
            }
        }
    
    def login(self, journal: str) -> bool:
        """
        Login to ScholarOne journal platform.
        
        Args:
            journal: Journal code ('mf', 'mor')
            
        Returns:
            True if login successful, False otherwise
        """
        if journal not in self.journal_configs:
            print(f"❌ Unknown journal: {journal}")
            return False
        
        config = self.journal_configs[journal]
        
        for attempt in range(self.max_login_attempts):
            try:
                print(f"🔐 Login attempt {attempt + 1}/{self.max_login_attempts} for {config['name']}...")
                
                # Navigate to login page
                if not self.browser.navigate_with_retry(config['url']):
                    print("   ❌ Failed to navigate to login page")
                    continue
                
                time.sleep(5)  # Allow page to fully load
                
                # Dismiss cookie banner if present
                self._dismiss_cookie_banner()
                
                # Enter credentials
                if not self._enter_credentials(config['email_env'], config['password_env']):
                    print("   ❌ Failed to enter credentials")
                    continue
                
                # Submit login form
                if not self._submit_login():
                    print("   ❌ Failed to submit login")
                    continue
                
                # Handle 2FA if required
                if self._is_2fa_required():
                    if not self._handle_2fa(journal):
                        print("   ❌ 2FA verification failed")
                        if attempt < self.max_login_attempts - 1:
                            continue
                        return False
                
                # Verify login success
                if self._verify_login_success():
                    print("   ✅ Login successful!")
                    return True
                
            except Exception as e:
                print(f"   ❌ Login attempt {attempt + 1} failed: {e}")
                if attempt < self.max_login_attempts - 1:
                    print("   🔄 Retrying...")
                    continue
        
        return False
    
    def _dismiss_cookie_banner(self) -> bool:
        """Dismiss cookie consent banner if present."""
        cookie_handlers = [
            ("ID", "onetrust-reject-all-handler"),
            ("ID", "onetrust-accept-btn-handler"),
            ("CSS_SELECTOR", "button[id*='cookie-reject']"),
            ("CSS_SELECTOR", "button[id*='cookie-accept']")
        ]
        
        for by_type, selector in cookie_handlers:
            try:
                if by_type == "ID":
                    element = self.driver.find_element(By.ID, selector)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    element.click()
                    time.sleep(1)
                    print("   🍪 Cookie banner dismissed")
                    return True
            except:
                continue
        
        return False
    
    def _enter_credentials(self, email_env: str, password_env: str) -> bool:
        """
        Enter login credentials.
        
        Args:
            email_env: Environment variable name for email
            password_env: Environment variable name for password
            
        Returns:
            True if credentials entered successfully
        """
        try:
            # Get credentials from environment
            email = os.getenv(email_env)
            password = os.getenv(password_env)
            
            if not email or not password:
                print(f"   ❌ Missing credentials: {email_env} or {password_env}")
                return False
            
            # Wait for login form
            userid_field = self.browser.wait_for_element(By.ID, "USERID", timeout=10)
            if not userid_field:
                print("   ❌ Login form not found")
                return False
            
            # Get fields
            userid_field = self.driver.find_element(By.ID, "USERID")
            password_field = self.driver.find_element(By.ID, "PASSWORD")
            
            # Clear and enter email
            userid_field.clear()
            userid_field.send_keys(Keys.CONTROL + "a")
            userid_field.send_keys(Keys.DELETE)
            time.sleep(0.5)
            userid_field.send_keys(email)
            
            # Clear and enter password
            password_field.clear()
            password_field.send_keys(Keys.CONTROL + "a")
            password_field.send_keys(Keys.DELETE)
            time.sleep(0.5)
            password_field.send_keys(password)
            
            print(f"   ✅ Credentials entered for {email}")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to enter credentials: {e}")
            return False
    
    def _submit_login(self) -> bool:
        """Submit the login form."""
        try:
            # Find login button
            login_selectors = [
                (By.ID, "logInButton"),
                (By.ID, "LOGIN_BTN"),
                (By.NAME, "login"),
                (By.XPATH, "//input[@type='submit' and @value='Log In']")
            ]
            
            for by_type, selector in login_selectors:
                try:
                    button = self.driver.find_element(by_type, selector)
                    button.click()
                    print("   ⏳ Login submitted, waiting for response...")
                    time.sleep(5)
                    return True
                except:
                    continue
            
            print("   ❌ Login button not found")
            return False
            
        except Exception as e:
            print(f"   ❌ Failed to submit login: {e}")
            return False
    
    def _is_2fa_required(self) -> bool:
        """Check if 2FA verification is required."""
        try:
            # Check for 2FA field
            self.driver.find_element(By.ID, "TOKEN_VALUE")
            print("   🔐 2FA verification required")
            return True
        except:
            return False
    
    def _handle_2fa(self, journal: str) -> bool:
        """
        Handle 2FA verification.
        
        Args:
            journal: Journal code for Gmail filtering
            
        Returns:
            True if 2FA successful
        """
        try:
            login_timestamp = time.time()
            print(f"   ⏰ 2FA timestamp: {datetime.fromtimestamp(login_timestamp).strftime('%H:%M:%S')}")
            
            # Get verification code
            code = self._get_verification_code(journal, login_timestamp)
            
            if not code:
                # Fallback to manual entry
                print("   💡 Automated code retrieval failed")
                try:
                    code = input("   📱 Enter 6-digit code from email: ").strip()
                    if not self._validate_code(code):
                        return False
                except EOFError:
                    print("   ❌ No input provided")
                    return False
            
            # Enter and submit code
            if not self._enter_verification_code(code):
                return False
            
            # Handle device verification if needed
            self._handle_device_verification()
            
            # Verify 2FA success
            return self._verify_2fa_success()
            
        except Exception as e:
            print(f"   ❌ 2FA handling failed: {e}")
            return False
    
    def _get_verification_code(self, journal: str, timestamp: float) -> Optional[str]:
        """
        Get verification code from Gmail.
        
        Args:
            journal: Journal code
            timestamp: Login timestamp for filtering
            
        Returns:
            6-digit verification code or None
        """
        if not self.gmail:
            return None
        
        attempts = 3
        for attempt in range(attempts):
            try:
                print(f"   📧 Gmail attempt {attempt + 1}/{attempts}...")
                
                # Wait for email to arrive
                time.sleep(10 if attempt == 0 else 5)
                
                # Fetch code from Gmail
                code = self.gmail.fetch_verification_code(
                    journal=journal,
                    start_timestamp=timestamp,
                    max_wait=30
                )
                
                if self._validate_code(code):
                    print(f"   ✅ Found verification code: {code[:3]}***")
                    return code
                    
            except Exception as e:
                print(f"   ⚠️ Gmail attempt {attempt + 1} failed: {e}")
        
        return None
    
    def _validate_code(self, code: str) -> bool:
        """Validate verification code format."""
        if not code:
            return False
        return len(code) == 6 and code.isdigit()
    
    def _enter_verification_code(self, code: str) -> bool:
        """Enter verification code in 2FA field."""
        try:
            # Wait for field to be clickable
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "TOKEN_VALUE"))
            )
            
            token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
            token_field.clear()
            token_field.send_keys(code)
            
            # Submit code
            verify_btn = self.driver.find_element(By.ID, "VERIFY_BTN")
            verify_btn.click()
            
            print("   ⏳ Verification code submitted")
            time.sleep(8)
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to enter verification code: {e}")
            
            # Try JavaScript fallback
            try:
                self.driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                self.driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                print("   ✅ Used JavaScript fallback")
                time.sleep(8)
                return True
            except:
                return False
    
    def _handle_device_verification(self):
        """Handle device verification modal if present."""
        try:
            modal = self.driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   📱 Handling device verification...")
                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                time.sleep(3)
        except:
            pass
    
    def _verify_2fa_success(self) -> bool:
        """Verify 2FA was successful."""
        try:
            # Check if still on 2FA page
            self.driver.find_element(By.ID, "TOKEN_VALUE")
            print("   ❌ Still on 2FA page")
            return False
        except:
            print("   ✅ 2FA successful")
            return True
    
    def _verify_login_success(self) -> bool:
        """Verify login was successful."""
        try:
            # Wait for page to load
            time.sleep(3)
            
            # Check for logout link or other indicators
            login_indicators = [
                (By.LINK_TEXT, "Log Out"),
                (By.LINK_TEXT, "Logout"),
                (By.PARTIAL_LINK_TEXT, "Log"),
                (By.XPATH, "//a[contains(text(), 'Associate Editor')]"),
                (By.XPATH, "//a[contains(@href, 'logout')]")
            ]
            
            for by_type, selector in login_indicators:
                try:
                    self.driver.find_element(by_type, selector)
                    return True
                except:
                    continue
            
            # Check URL
            current_url = self.driver.current_url
            if 'login' not in current_url.lower():
                return True
            
            return False
            
        except Exception as e:
            print(f"   ⚠️ Login verification error: {e}")
            return False
    
    def logout(self) -> bool:
        """Logout from the platform."""
        try:
            logout_link = self.driver.find_element(By.LINK_TEXT, "Log Out")
            logout_link.click()
            time.sleep(2)
            print("   ✅ Logged out successfully")
            return True
        except Exception as e:
            print(f"   ⚠️ Logout failed: {e}")
            return False
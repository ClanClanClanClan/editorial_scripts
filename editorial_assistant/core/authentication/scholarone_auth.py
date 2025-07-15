"""
ScholarOne Authentication Provider

Handles authentication for ScholarOne Manuscripts platform.
Used by: MF, MOR, MS, RFS, RAPS
"""

import time
import asyncio
from typing import Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

from .base import AuthenticationProvider, AuthenticationResult, AuthStatus


class ScholarOneAuth(AuthenticationProvider):
    """
    ScholarOne authentication provider with 2FA support.
    
    Provides unified authentication for ScholarOne Manuscripts platform
    used by MF, MOR, and other journals with proven 2FA handling.
    """
    
    def __init__(self, journal_code: str, credentials: Dict[str, str], logger=None):
        """
        Initialize ScholarOne authentication provider.
        
        Args:
            journal_code: Journal code (MF, MOR, etc.)
            credentials: Dictionary containing ScholarOne credentials
            logger: Logger instance
        """
        super().__init__(credentials, logger)
        self.journal_code = journal_code.upper()
        
        # ScholarOne journal URLs (from proven legacy system)
        self.journal_urls = {
            'MF': "https://mc.manuscriptcentral.com/mafi",
            'MOR': "https://mc.manuscriptcentral.com/mathor", 
            'MS': "https://mc.manuscriptcentral.com/mnsc",
            'RFS': "https://mc.manuscriptcentral.com/rfs",
            'RAPS': "https://mc.manuscriptcentral.com/raps"
        }
    
    def get_login_url(self) -> str:
        """Get the login URL for the specified ScholarOne journal."""
        return self.journal_urls.get(self.journal_code, self.journal_urls['MF'])
    
    def get_required_credentials(self) -> list:
        """Get required credential fields for ScholarOne authentication."""
        return ['username', 'password']
    
    async def authenticate(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform ScholarOne authentication with 2FA support.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            AuthenticationResult with authentication status
        """
        try:
            self._log_info(f"Starting ScholarOne authentication for {self.journal_code}")
            
            # Navigate to journal login page
            login_url = self.get_login_url()
            self._log_info(f"Navigating to: {login_url}")
            driver.get(login_url)
            time.sleep(2)
            
            # Handle cookies (exact same approach as proven legacy system)
            self._handle_cookie_consent(driver)
            
            # Perform basic login
            basic_auth_result = await self._perform_basic_login(driver)
            
            if basic_auth_result.status != AuthStatus.SUCCESS:
                return basic_auth_result
            
            # Handle 2FA if required
            if basic_auth_result.requires_2fa:
                self._log_info("2FA verification required")
                tfa_result = await self._handle_2fa_verification(driver)
                
                if tfa_result.status != AuthStatus.SUCCESS:
                    return tfa_result
            
            # Verify final authentication
            if self.verify_authentication(driver):
                self._log_info(f"✅ ScholarOne authentication successful for {self.journal_code}")
                return AuthenticationResult(
                    status=AuthStatus.SUCCESS,
                    message=f"ScholarOne authentication successful for {self.journal_code}"
                )
            else:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Authentication verification failed",
                    error_details="Login appeared successful but verification failed"
                )
            
        except Exception as e:
            self._log_error(f"ScholarOne authentication error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"Authentication failed: {str(e)}",
                error_details=str(e)
            )
    
    def _handle_cookie_consent(self, driver: WebDriver) -> None:
        """
        Handle cookie consent banner (exact same as legacy system).
        
        Args:
            driver: Selenium WebDriver instance
        """
        try:
            accept_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed():
                accept_btn.click()
                self._log_info("Accepted cookies")
                time.sleep(1)
        except NoSuchElementException:
            self._log_debug("No cookie accept button found")
        except Exception as e:
            self._log_debug(f"Cookie handling error: {str(e)}")
    
    async def _perform_basic_login(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform basic username/password login.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            AuthenticationResult with login status
        """
        try:
            username = self.credentials.get('username', '')
            password = self.credentials.get('password', '')
            
            if not username or not password:
                return AuthenticationResult(
                    status=AuthStatus.INVALID_CREDENTIALS,
                    message="Missing ScholarOne credentials",
                    error_details="Username or password not provided"
                )
            
            self._log_info("Filling login form...")
            
            # Fill login form (exact same field IDs as legacy system)
            try:
                user_box = driver.find_element(By.ID, "USERID")
                pw_box = driver.find_element(By.ID, "PASSWORD")
                
                user_box.clear()
                user_box.send_keys(username)
                pw_box.clear() 
                pw_box.send_keys(password)
                
                # Submit login (exact same button ID as legacy)
                login_btn = driver.find_element(By.ID, "logInButton")
                login_btn.click()
                time.sleep(4)
                
                self._log_info("Login form submitted")
                
            except NoSuchElementException as e:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Login form elements not found",
                    error_details=f"Could not locate login form: {str(e)}"
                )
            
            # Check if 2FA is required
            requires_2fa = self._check_2fa_required(driver)
            
            return AuthenticationResult(
                status=AuthStatus.SUCCESS,
                message="Basic login successful",
                requires_2fa=requires_2fa
            )
            
        except Exception as e:
            self._log_error(f"Basic login error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"Basic login failed: {str(e)}",
                error_details=str(e)
            )
    
    def _check_2fa_required(self, driver: WebDriver) -> bool:
        """
        Check if 2FA verification is required.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if 2FA is required
        """
        try:
            # Check for verification code input fields (exact same as legacy)
            verification_selectors = [
                (By.ID, "TOKEN_VALUE"),
                (By.ID, "validationCode")
            ]
            
            for selector_type, selector in verification_selectors:
                try:
                    element = driver.find_element(selector_type, selector)
                    if element.is_displayed():
                        self._log_info(f"2FA required: found {selector}")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            self._log_debug(f"2FA check error: {str(e)}")
            return False
    
    async def _handle_2fa_verification(self, driver: WebDriver) -> AuthenticationResult:
        """
        Handle 2FA verification using email code.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            AuthenticationResult with 2FA status
        """
        try:
            # Handle reCAPTCHA if present (exact same as legacy)
            self._handle_recaptcha(driver)
            
            # Find verification code input
            code_input = self._find_verification_input(driver)
            
            if not code_input:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Verification code input not found",
                    error_details="Could not locate 2FA verification input field"
                )
            
            # Get verification code from email
            verification_code = await self._fetch_verification_code()
            
            if not verification_code:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Failed to fetch verification code",
                    error_details="Could not retrieve 2FA code from email"
                )
            
            # Enter verification code
            self._log_info(f"Entering verification code: {verification_code}")
            code_input.clear()
            code_input.send_keys(verification_code)
            code_input.send_keys(Keys.RETURN)
            time.sleep(3)
            
            return AuthenticationResult(
                status=AuthStatus.SUCCESS,
                message="2FA verification successful"
            )
            
        except Exception as e:
            self._log_error(f"2FA verification error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"2FA verification failed: {str(e)}",
                error_details=str(e)
            )
    
    def _handle_recaptcha(self, driver: WebDriver) -> None:
        """
        Handle reCAPTCHA if present (exact same as legacy system).
        
        Args:
            driver: Selenium WebDriver instance
        """
        try:
            recaptcha_iframe = driver.find_element(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]")
            if recaptcha_iframe.is_displayed():
                driver.switch_to.frame(recaptcha_iframe)
                checkbox = driver.find_element(By.ID, "recaptcha-anchor")
                checkbox.click()
                driver.switch_to.default_content()
                self._log_info("Clicked reCAPTCHA checkbox")
                time.sleep(2)
        except NoSuchElementException:
            self._log_debug("No reCAPTCHA present")
        except Exception as e:
            self._log_debug(f"reCAPTCHA handling error: {str(e)}")
    
    def _find_verification_input(self, driver: WebDriver):
        """
        Find verification code input field using multiple strategies.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            WebElement if found, None otherwise
        """
        wait = WebDriverWait(driver, 15)
        
        # Try multiple selectors (exact same as legacy)
        selectors = [
            (By.ID, "TOKEN_VALUE"),
            (By.ID, "validationCode")
        ]
        
        for selector_type, selector in selectors:
            try:
                element = wait.until(
                    lambda d: d.find_element(selector_type, selector) 
                    if self._element_exists_and_visible(d, selector_type, selector) else None
                )
                if element:
                    self._log_debug(f"Found verification input: {selector}")
                    return element
            except TimeoutException:
                continue
        
        return None
    
    def _element_exists_and_visible(self, driver: WebDriver, selector_type, selector: str) -> bool:
        """
        Check if element exists and is visible.
        
        Args:
            driver: Selenium WebDriver instance
            selector_type: Selenium By selector type
            selector: Selector string
            
        Returns:
            True if element exists and is visible
        """
        try:
            element = driver.find_element(selector_type, selector)
            return element.is_displayed()
        except:
            return False
    
    async def _fetch_verification_code(self) -> str:
        """
        Fetch verification code from email using email verification manager.
        
        Returns:
            Verification code string or None if not found
        """
        try:
            # Import email verification manager
            from ...utils.email_verification import get_email_verification_manager
            
            email_manager = get_email_verification_manager()
            
            # Wait for email (exact same timing as legacy)
            self._log_info("Waiting 5 seconds for verification email to arrive...")
            time.sleep(5)
            
            verification_code = email_manager.fetch_verification_code(journal=self.journal_code)
            
            if verification_code:
                self._log_info(f"Retrieved verification code: {verification_code}")
                return verification_code
            else:
                self._log_error("No verification code found in email")
                return None
                
        except ImportError as e:
            self._log_warning(f"Could not import email verification manager: {e}")
            return None
        except Exception as e:
            self._log_error(f"Error fetching verification code: {e}")
            return None
    
    def verify_authentication(self, driver: WebDriver) -> bool:
        """
        Verify that ScholarOne authentication was successful.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if authenticated successfully
        """
        try:
            # Check URL first
            if "login" in driver.current_url.lower():
                return False
            
            # Check for logged-in indicators (exact same as legacy)
            indicators = [
                "Associate Editor Center",
                "Author Center", 
                "Reviewer Center",
                "Logout",
                "Sign Out"
            ]
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            for indicator in indicators:
                if indicator in page_text:
                    self._log_debug(f"Found auth indicator: {indicator}")
                    return True
                    
            return False
            
        except Exception as e:
            self._log_error(f"Authentication verification error: {str(e)}")
            return False
    
    def handle_2fa(self, driver: WebDriver) -> bool:
        """
        Handle two-factor authentication.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if 2FA handled successfully
        """
        try:
            # Use the async method in a sync context
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self._handle_2fa_verification(driver))
            
            loop.close()
            
            return result.status == AuthStatus.SUCCESS
            
        except Exception as e:
            self._log_error(f"2FA handling error: {str(e)}")
            return False
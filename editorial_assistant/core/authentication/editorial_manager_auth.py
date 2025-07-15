"""
Editorial Manager Authentication Provider

Handles authentication for Editorial Manager platform.
Used by: FS, JOTA, MAFE and other Editorial Manager journals
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


class EditorialManagerAuth(AuthenticationProvider):
    """
    Editorial Manager authentication provider.
    
    Provides unified authentication for Editorial Manager platform
    used by FS, JOTA, MAFE and other journals.
    """
    
    def __init__(self, journal_code: str, credentials: Dict[str, str], logger=None):
        """
        Initialize Editorial Manager authentication provider.
        
        Args:
            journal_code: Journal code (FS, JOTA, MAFE, etc.)
            credentials: Dictionary containing Editorial Manager credentials
            logger: Logger instance
        """
        super().__init__(credentials, logger)
        self.journal_code = journal_code.upper()
        
        # Editorial Manager journal URLs
        self.journal_urls = {
            'FS': "https://www.editorialmanager.com/finsto/",
            'JOTA': "https://www.editorialmanager.com/jota/", 
            'MAFE': "https://www.editorialmanager.com/mafe/"
        }
    
    def get_login_url(self) -> str:
        """Get the login URL for the specified Editorial Manager journal."""
        return self.journal_urls.get(self.journal_code, f"https://www.editorialmanager.com/{self.journal_code.lower()}/")
    
    def get_required_credentials(self) -> list:
        """Get required credential fields for Editorial Manager authentication."""
        return ['username', 'password']
    
    async def authenticate(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform Editorial Manager authentication.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            AuthenticationResult with authentication status
        """
        try:
            self._log_info(f"Starting Editorial Manager authentication for {self.journal_code}")
            
            # Navigate to journal login page
            login_url = self.get_login_url()
            self._log_info(f"Navigating to: {login_url}")
            driver.get(login_url)
            time.sleep(3)
            
            # Handle initial page load and redirects
            if not await self._handle_initial_navigation(driver):
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Failed to navigate to login page",
                    error_details="Could not reach Editorial Manager login form"
                )
            
            # Perform login
            auth_result = await self._perform_login(driver)
            
            if auth_result.status == AuthStatus.SUCCESS:
                # Verify authentication
                if self.verify_authentication(driver):
                    self._log_info(f"✅ Editorial Manager authentication successful for {self.journal_code}")
                    return auth_result
                else:
                    return AuthenticationResult(
                        status=AuthStatus.FAILED,
                        message="Authentication verification failed",
                        error_details="Login completed but verification failed"
                    )
            
            return auth_result
            
        except Exception as e:
            self._log_error(f"Editorial Manager authentication error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"Authentication failed: {str(e)}",
                error_details=str(e)
            )
    
    async def _handle_initial_navigation(self, driver: WebDriver) -> bool:
        """
        Handle initial navigation and find login form.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if login form is accessible
        """
        try:
            # Wait for page to load
            time.sleep(2)
            
            # Look for login link if not already on login page
            if 'login' not in driver.current_url.lower():
                login_selectors = [
                    (By.LINK_TEXT, "Login"),
                    (By.PARTIAL_LINK_TEXT, "Login"),
                    (By.LINK_TEXT, "Log In"),
                    (By.PARTIAL_LINK_TEXT, "Log In"),
                    (By.XPATH, "//a[contains(text(), 'Sign In')]"),
                    (By.XPATH, "//a[contains(@href, 'login')]")
                ]
                
                for selector_type, selector in login_selectors:
                    try:
                        login_link = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        login_link.click()
                        self._log_info("Clicked login link")
                        time.sleep(2)
                        break
                    except TimeoutException:
                        continue
            
            # Check if login form is present
            return self._check_login_form_present(driver)
            
        except Exception as e:
            self._log_error(f"Initial navigation error: {str(e)}")
            return False
    
    def _check_login_form_present(self, driver: WebDriver) -> bool:
        """
        Check if login form is present on current page.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if login form is found
        """
        try:
            # Common Editorial Manager login field names/IDs
            username_selectors = [
                (By.NAME, "userId"),
                (By.ID, "userId"), 
                (By.NAME, "username"),
                (By.ID, "username"),
                (By.NAME, "loginId"),
                (By.ID, "loginId")
            ]
            
            for selector_type, selector in username_selectors:
                try:
                    element = driver.find_element(selector_type, selector)
                    if element.is_displayed():
                        self._log_debug(f"Found username field: {selector}")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            self._log_debug(f"Login form check error: {str(e)}")
            return False
    
    async def _perform_login(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform the actual login process.
        
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
                    message="Missing Editorial Manager credentials",
                    error_details="Username or password not provided"
                )
            
            # Find username field
            username_field = self._find_username_field(driver)
            if not username_field:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Username field not found",
                    error_details="Could not locate username input field"
                )
            
            # Find password field  
            password_field = self._find_password_field(driver)
            if not password_field:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Password field not found",
                    error_details="Could not locate password input field"
                )
            
            # Fill credentials
            self._log_info("Filling login credentials...")
            username_field.clear()
            username_field.send_keys(username)
            
            password_field.clear()
            password_field.send_keys(password)
            
            # Submit form
            submit_button = self._find_submit_button(driver)
            if submit_button:
                submit_button.click()
                self._log_info("Submitted login form")
            else:
                # Try pressing Enter on password field
                password_field.send_keys(Keys.RETURN)
                self._log_info("Submitted form with Enter key")
            
            # Wait for login to process
            time.sleep(4)
            
            return AuthenticationResult(
                status=AuthStatus.SUCCESS,
                message="Editorial Manager login successful"
            )
            
        except Exception as e:
            self._log_error(f"Login process error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"Login process failed: {str(e)}",
                error_details=str(e)
            )
    
    def _find_username_field(self, driver: WebDriver):
        """Find username input field using multiple strategies."""
        selectors = [
            (By.NAME, "userId"),
            (By.ID, "userId"),
            (By.NAME, "username"), 
            (By.ID, "username"),
            (By.NAME, "loginId"),
            (By.ID, "loginId"),
            (By.XPATH, "//input[@type='text' and contains(@name, 'user')]"),
            (By.XPATH, "//input[@type='email']")
        ]
        
        return self._find_element_by_selectors(driver, selectors)
    
    def _find_password_field(self, driver: WebDriver):
        """Find password input field using multiple strategies."""
        selectors = [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.XPATH, "//input[@type='password']")
        ]
        
        return self._find_element_by_selectors(driver, selectors)
    
    def _find_submit_button(self, driver: WebDriver):
        """Find submit button using multiple strategies."""
        selectors = [
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.NAME, "submit"),
            (By.ID, "submit"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Sign In')]"),
            (By.XPATH, "//input[@value='Login']"),
            (By.XPATH, "//input[@value='Sign In']")
        ]
        
        return self._find_element_by_selectors(driver, selectors)
    
    def _find_element_by_selectors(self, driver: WebDriver, selectors: list):
        """
        Find element using multiple selector strategies.
        
        Args:
            driver: Selenium WebDriver instance
            selectors: List of (By, selector) tuples to try
            
        Returns:
            WebElement if found, None otherwise
        """
        for selector_type, selector in selectors:
            try:
                element = driver.find_element(selector_type, selector)
                if element.is_displayed():
                    return element
            except NoSuchElementException:
                continue
        return None
    
    def verify_authentication(self, driver: WebDriver) -> bool:
        """
        Verify that Editorial Manager authentication was successful.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if authenticated successfully
        """
        try:
            # Check URL is not login page
            current_url = driver.current_url
            if 'login' in current_url.lower():
                return False
            
            # Check for logged-in indicators
            page_source = driver.page_source.lower()
            
            logged_in_indicators = [
                'logout',
                'sign out',
                'dashboard',
                'main menu',
                'welcome',
                'author dashboard',
                'reviewer dashboard',
                'submit new manuscript',
                'manuscripts in submission',
                'manuscripts in review'
            ]
            
            for indicator in logged_in_indicators:
                if indicator in page_source:
                    self._log_debug(f"Found auth indicator: {indicator}")
                    return True
            
            # Check for error indicators
            error_indicators = [
                'invalid login',
                'incorrect password',
                'login failed',
                'authentication failed'
            ]
            
            for error in error_indicators:
                if error in page_source:
                    self._log_error(f"Found error indicator: {error}")
                    return False
            
            # If no clear indicators, assume success if not on login page
            return 'editorialmanager.com' in current_url
            
        except Exception as e:
            self._log_error(f"Authentication verification error: {str(e)}")
            return False
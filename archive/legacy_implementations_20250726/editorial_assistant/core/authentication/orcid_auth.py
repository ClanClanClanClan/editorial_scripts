"""
ORCID Authentication Provider

Handles authentication for SIAM journals using ORCID SSO.
Used by: SICON, SIFIN, NACO
"""

import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import AuthenticationProvider, AuthenticationResult, AuthStatus


class ORCIDAuth(AuthenticationProvider):
    """
    ORCID authentication provider for SIAM journals.

    Provides unified authentication for SICON, SIFIN, and NACO
    using ORCID Single Sign-On with CloudFlare bypass capabilities.
    """

    def __init__(self, journal_code: str, credentials: dict[str, str], logger=None):
        """
        Initialize ORCID authentication provider.

        Args:
            journal_code: Journal code (SICON, SIFIN, NACO)
            credentials: Dictionary containing ORCID credentials
            logger: Logger instance
        """
        super().__init__(credentials, logger)
        self.journal_code = journal_code.upper()

        # SIAM journal URLs
        self.journal_urls = {
            "SICON": "https://www.editorialmanager.com/siamjco/",
            "SIFIN": "https://www.editorialmanager.com/siamjfm/",
            "NACO": "https://www.editorialmanager.com/naco/",
        }

    def get_login_url(self) -> str:
        """Get the login URL for the specified SIAM journal."""
        return self.journal_urls.get(self.journal_code, self.journal_urls["SICON"])

    def get_required_credentials(self) -> list:
        """Get required credential fields for ORCID authentication."""
        return ["username", "password"]

    async def authenticate(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform ORCID authentication with CloudFlare bypass.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            AuthenticationResult with authentication status
        """
        try:
            self._log_info(f"Starting ORCID authentication for {self.journal_code}")

            # Navigate to journal login page
            login_url = self.get_login_url()
            self._log_info(f"Navigating to: {login_url}")
            driver.get(login_url)
            time.sleep(3)

            # Handle CloudFlare check
            if not await self._handle_cloudflare(driver):
                return AuthenticationResult(
                    status=AuthStatus.BLOCKED,
                    message="CloudFlare verification failed",
                    error_details="Unable to bypass CloudFlare protection",
                )

            # Find and click ORCID login button
            if not self._click_orcid_button(driver):
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="ORCID login button not found",
                    error_details="Could not locate ORCID authentication button",
                )

            # Perform ORCID login
            auth_result = await self._perform_orcid_login(driver)

            if auth_result.status == AuthStatus.SUCCESS:
                # Verify we're back on the journal site
                if self.verify_authentication(driver):
                    self._log_info(f"✅ ORCID authentication successful for {self.journal_code}")
                    return auth_result
                else:
                    return AuthenticationResult(
                        status=AuthStatus.FAILED,
                        message="Authentication verification failed",
                        error_details="Logged into ORCID but not redirected to journal",
                    )

            return auth_result

        except Exception as e:
            self._log_error(f"ORCID authentication error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"Authentication failed: {str(e)}",
                error_details=str(e),
            )

    async def _handle_cloudflare(self, driver: WebDriver) -> bool:
        """
        Handle CloudFlare verification if present.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if CloudFlare handled successfully or not present
        """
        try:
            # Wait for page to load
            time.sleep(2)

            # Check for CloudFlare challenge
            page_source = driver.page_source.lower()

            if "checking your browser" in page_source or "cloudflare" in page_source:
                self._log_info("CloudFlare challenge detected, waiting...")

                # Wait up to 30 seconds for CloudFlare to complete
                for i in range(30):
                    time.sleep(1)
                    current_source = driver.page_source.lower()

                    if "checking your browser" not in current_source:
                        self._log_info("CloudFlare challenge completed")
                        return True

                self._log_error("CloudFlare challenge timeout")
                return False

            return True

        except Exception as e:
            self._log_error(f"CloudFlare handling error: {str(e)}")
            return False

    def _click_orcid_button(self, driver: WebDriver) -> bool:
        """
        Find and click the ORCID login button.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if ORCID button clicked successfully
        """
        try:
            self._log_info("Looking for ORCID login button...")

            # Multiple strategies to find ORCID button
            orcid_selectors = [
                (By.XPATH, "//button[contains(text(), 'ORCID')]"),
                (By.XPATH, "//a[contains(text(), 'ORCID')]"),
                (By.XPATH, "//input[@value='ORCID' or contains(@value, 'orcid')]"),
                (By.CSS_SELECTOR, "button[title*='ORCID'], a[title*='ORCID']"),
                (By.XPATH, "//*[contains(@class, 'orcid') or contains(@id, 'orcid')]"),
                (By.PARTIAL_LINK_TEXT, "ORCID"),
                (By.PARTIAL_LINK_TEXT, "Sign in with ORCID"),
            ]

            wait = WebDriverWait(driver, 10)

            for selector_type, selector in orcid_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((selector_type, selector)))

                    self._log_info(f"Found ORCID button: {element.tag_name}")
                    element.click()
                    time.sleep(2)
                    return True

                except TimeoutException:
                    continue
                except Exception as e:
                    self._log_debug(f"ORCID button selector failed: {str(e)}")
                    continue

            self._log_error("No ORCID login button found")
            return False

        except Exception as e:
            self._log_error(f"Error clicking ORCID button: {str(e)}")
            return False

    async def _perform_orcid_login(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform the actual ORCID login process.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            AuthenticationResult with login status
        """
        try:
            self._log_info("Performing ORCID login...")

            # Wait for ORCID login page
            time.sleep(3)

            # Handle potential new window/tab
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                self._log_info("Switched to ORCID login window")

            # Fill ORCID credentials
            username = self.credentials.get("username", "")
            password = self.credentials.get("password", "")

            if not username or not password:
                return AuthenticationResult(
                    status=AuthStatus.INVALID_CREDENTIALS,
                    message="Missing ORCID credentials",
                    error_details="Username or password not provided",
                )

            # Find and fill username field
            username_selectors = [
                "#username",
                '[name="userId"]',
                '[id="userId"]',
                'input[type="email"]',
            ]
            username_field = self._find_element_by_selectors(driver, username_selectors)

            if not username_field:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Username field not found",
                    error_details="Could not locate ORCID username input field",
                )

            username_field.clear()
            username_field.send_keys(username)
            self._log_info("Filled username field")

            # Find and fill password field
            password_selectors = ["#password", '[name="password"]', '[type="password"]']
            password_field = self._find_element_by_selectors(driver, password_selectors)

            if not password_field:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Password field not found",
                    error_details="Could not locate ORCID password input field",
                )

            password_field.clear()
            password_field.send_keys(password)
            self._log_info("Filled password field")

            # Submit form
            submit_selectors = [
                "#signin-button",
                'button[type="submit"]',
                'input[type="submit"]',
                'button[id*="signin"]',
                'button[class*="signin"]',
            ]

            submit_button = self._find_element_by_selectors(driver, submit_selectors)

            if not submit_button:
                return AuthenticationResult(
                    status=AuthStatus.FAILED,
                    message="Submit button not found",
                    error_details="Could not locate ORCID login submit button",
                )

            submit_button.click()
            self._log_info("Submitted ORCID login form")

            # Wait for login to complete
            time.sleep(5)

            # Check for authorization page
            if "authorize" in driver.current_url.lower():
                self._log_info("ORCID authorization page detected")

                # Click authorize button
                auth_selectors = [
                    'button[name="user_oauth_approval"]',
                    "#authorize",
                    'button[value="true"]',
                    'input[value="Authorize"]',
                ]

                auth_button = self._find_element_by_selectors(driver, auth_selectors)
                if auth_button:
                    auth_button.click()
                    self._log_info("Clicked ORCID authorization button")
                    time.sleep(3)

            # Wait for redirect back to journal site
            max_wait = 30
            for i in range(max_wait):
                current_url = driver.current_url
                if any(
                    journal in current_url
                    for journal in ["editorialmanager.com", "manuscriptcentral.com"]
                ):
                    self._log_info("Successfully redirected back to journal site")
                    return AuthenticationResult(
                        status=AuthStatus.SUCCESS, message="ORCID authentication successful"
                    )
                time.sleep(1)

            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message="Redirect timeout",
                error_details="Did not redirect back to journal site after ORCID login",
            )

        except Exception as e:
            self._log_error(f"ORCID login error: {str(e)}")
            return AuthenticationResult(
                status=AuthStatus.FAILED,
                message=f"ORCID login failed: {str(e)}",
                error_details=str(e),
            )

    def _find_element_by_selectors(self, driver: WebDriver, selectors: list):
        """
        Find element using multiple CSS selectors.

        Args:
            driver: Selenium WebDriver instance
            selectors: List of CSS selectors to try

        Returns:
            WebElement if found, None otherwise
        """
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    return element
            except NoSuchElementException:
                continue
        return None

    def verify_authentication(self, driver: WebDriver) -> bool:
        """
        Verify that ORCID authentication was successful.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if authenticated successfully
        """
        try:
            # Check URL contains journal domain
            current_url = driver.current_url
            if "editorialmanager.com" not in current_url:
                return False

            # Check for logged-in indicators
            page_source = driver.page_source.lower()

            logged_in_indicators = [
                "logout",
                "sign out",
                "welcome",
                "dashboard",
                "main menu",
                "author dashboard",
                "reviewer dashboard",
            ]

            return any(indicator in page_source for indicator in logged_in_indicators)

        except Exception as e:
            self._log_error(f"Authentication verification error: {str(e)}")
            return False

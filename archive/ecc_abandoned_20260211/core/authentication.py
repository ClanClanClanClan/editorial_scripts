"""Authentication module for journal platform login.

Handles various authentication methods including:
- Username/password login
- Two-factor authentication (2FA)
- ORCID OAuth
- Session management
- Credential storage and retrieval
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By

from .browser_manager import BrowserManager
from .error_handling import ExtractorError, SafeExecutor
from .logging_system import ExtractorLogger, LogCategory
from .retry_strategies import RetryConfigs, retry


class AuthMethod(Enum):
    """Authentication method types."""

    USERNAME_PASSWORD = "username_password"
    ORCID = "orcid"
    GMAIL_2FA = "gmail_2fa"
    SMS_2FA = "sms_2fa"
    APP_2FA = "app_2fa"


@dataclass
class Credentials:
    """Credential storage for authentication."""

    username: str
    password: str
    orcid_id: str | None = None
    orcid_password: str | None = None
    gmail_address: str | None = None
    backup_codes: list | None = None

    @classmethod
    def from_env(cls, prefix: str) -> "Credentials":
        """
        Load credentials from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., "MF", "MOR")

        Returns:
            Credentials instance
        """
        return cls(
            username=os.getenv(f"{prefix}_USERNAME", ""),
            password=os.getenv(f"{prefix}_PASSWORD", ""),
            orcid_id=os.getenv(f"{prefix}_ORCID_ID"),
            orcid_password=os.getenv(f"{prefix}_ORCID_PASSWORD"),
            gmail_address=os.getenv(f"{prefix}_GMAIL"),
        )

    def is_valid(self) -> bool:
        """Check if minimum credentials are present."""
        return bool(self.username and self.password)


class TwoFactorHandler(ABC):
    """Abstract base for 2FA handlers."""

    @abstractmethod
    def get_verification_code(self) -> str | None:
        """Get the 2FA verification code."""
        pass

    @abstractmethod
    def submit_code(self, code: str, browser: BrowserManager) -> bool:
        """Submit the verification code."""
        pass


class Gmail2FAHandler(TwoFactorHandler):
    """Handler for Gmail-based 2FA."""

    def __init__(self, gmail_address: str, logger: ExtractorLogger | None = None):
        """
        Initialize Gmail 2FA handler.

        Args:
            gmail_address: Gmail address for receiving codes
            logger: Logger instance
        """
        self.gmail_address = gmail_address
        self.logger = logger or ExtractorLogger("gmail_2fa")
        self._verification_code = None

    def get_verification_code(self) -> str | None:
        """
        Get verification code from Gmail.

        Returns:
            Verification code or None
        """
        self.logger.info("Retrieving 2FA code from Gmail", LogCategory.AUTH)

        # Import Gmail handler if available
        try:
            from core.gmail_verification import get_latest_verification_code

            code = get_latest_verification_code(
                sender="manuscriptcentral.com", subject_pattern="verification code", max_wait=60
            )

            if code:
                self._verification_code = code
                self.logger.success(f"Retrieved 2FA code: {code}", LogCategory.AUTH)
                return code
            else:
                self.logger.error("No verification code found in Gmail")
                return None

        except ImportError:
            self.logger.warning("Gmail integration not available, using manual input")
            # Fallback to manual input
            code = input("Enter 2FA code from email: ").strip()
            return code if code else None

    def submit_code(self, code: str, browser: BrowserManager) -> bool:
        """
        Submit verification code to the platform.

        Args:
            code: Verification code
            browser: Browser manager instance

        Returns:
            True if submission successful
        """
        try:
            # Look for verification code input field
            code_input = browser.wait_for_element(
                By.XPATH,
                "//input[@type='text' and (contains(@name, 'code') or contains(@id, 'verification'))]",
                timeout=5,
            )

            code_input.clear()
            code_input.send_keys(code)

            # Submit the code
            submit_button = browser.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Submit')] | //input[@type='submit']"
            )

            browser.safe_click(submit_button)

            # Wait for redirect or success message
            time.sleep(3)

            self.logger.success("2FA code submitted successfully", LogCategory.AUTH)
            return True

        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Failed to submit 2FA code: {e}")
            return False


class AuthenticationManager:
    """Manages authentication for journal platforms."""

    def __init__(
        self,
        browser: BrowserManager,
        logger: ExtractorLogger | None = None,
        safe_executor: SafeExecutor | None = None,
    ):
        """
        Initialize authentication manager.

        Args:
            browser: Browser manager instance
            logger: Logger instance
            safe_executor: Safe executor for error handling
        """
        self.browser = browser
        self.logger = logger or ExtractorLogger("auth_manager")
        self.safe_executor = safe_executor or SafeExecutor(self.logger.logger)
        self.is_authenticated = False
        self.session_data: dict[str, Any] = {}

    @retry(config=RetryConfigs.AUTH)
    def login_scholarone(
        self,
        credentials: Credentials,
        login_url: str,
        two_fa_handler: TwoFactorHandler | None = None,
    ) -> bool:
        """
        Login to ScholarOne/ManuscriptCentral platform.

        Args:
            credentials: Login credentials
            login_url: Platform login URL
            two_fa_handler: Optional 2FA handler

        Returns:
            True if login successful
        """
        self.logger.enter_context("scholarone_login")

        try:
            # Navigate to login page
            self.browser.navigate_to(login_url)

            # Handle cookie banner if present
            self._dismiss_cookie_banner()

            # Find and fill username field
            username_field = self.browser.wait_for_element(By.ID, "USERID", timeout=10)
            username_field.clear()
            username_field.send_keys(credentials.username)

            # Find and fill password field
            password_field = self.browser.driver.find_element(By.ID, "PASSWORD")
            password_field.clear()
            password_field.send_keys(credentials.password)

            # Click login button
            login_button = self.browser.driver.find_element(
                By.XPATH, "//input[@type='submit' and @value='Log In']"
            )
            self.browser.safe_click(login_button)

            # Wait for login to process
            time.sleep(3)

            # Check if 2FA is required
            if self._is_2fa_required():
                if two_fa_handler:
                    code = two_fa_handler.get_verification_code()
                    if code:
                        two_fa_handler.submit_code(code, self.browser)
                    else:
                        raise ExtractorError("Failed to get 2FA code")
                else:
                    self.logger.warning("2FA required but no handler provided")
                    return False

            # Verify login success
            if self._verify_login_success():
                self.is_authenticated = True
                self._store_session_data()
                self.logger.auth_success("ScholarOne login successful")
                return True
            else:
                self.logger.error("Login verification failed")
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

        finally:
            self.logger.exit_context(success=self.is_authenticated)

    def login_orcid(self, credentials: Credentials, platform_url: str) -> bool:
        """
        Login using ORCID authentication.

        Args:
            credentials: ORCID credentials
            platform_url: Platform URL that uses ORCID

        Returns:
            True if login successful
        """
        self.logger.enter_context("orcid_login")

        try:
            # Navigate to platform
            self.browser.navigate_to(platform_url)

            # Look for ORCID login button
            orcid_button = self.browser.wait_for_element(
                By.XPATH,
                "//a[contains(@href, 'orcid.org')] | //button[contains(text(), 'ORCID')]",
                timeout=10,
            )

            self.browser.safe_click(orcid_button)

            # Switch to ORCID window/tab if opened
            if len(self.browser.driver.window_handles) > 1:
                self.browser.switch_to_popup()

            # Fill ORCID credentials
            orcid_field = self.browser.wait_for_element(By.ID, "username", timeout=10)
            orcid_field.clear()
            orcid_field.send_keys(credentials.orcid_id or credentials.username)

            password_field = self.browser.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(credentials.orcid_password or credentials.password)

            # Submit ORCID login
            submit_button = self.browser.driver.find_element(By.ID, "signin-button")
            self.browser.safe_click(submit_button)

            # Handle authorization if needed
            time.sleep(2)
            self._handle_orcid_authorization()

            # Return to main window
            if len(self.browser.driver.window_handles) > 1:
                self.browser.close_popup_and_return()

            # Verify login
            if self._verify_login_success():
                self.is_authenticated = True
                self.logger.auth_success("ORCID login successful")
                return True

            return False

        except Exception as e:
            self.logger.error(f"ORCID login failed: {e}")
            return False

        finally:
            self.logger.exit_context(success=self.is_authenticated)

    def _dismiss_cookie_banner(self):
        """Dismiss cookie consent banner if present."""
        try:
            # Look for common cookie banner patterns
            cookie_buttons = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'I Agree')]",
                "//button[contains(@class, 'cookie-accept')]",
                "//div[@id='cookie-banner']//button",
            ]

            for xpath in cookie_buttons:
                try:
                    button = self.browser.driver.find_element(By.XPATH, xpath)
                    if button.is_displayed():
                        self.browser.safe_click(button)
                        self.logger.info("Dismissed cookie banner")
                        time.sleep(1)
                        break
                except NoSuchElementException:
                    continue

        except Exception:
            # Cookie banner dismissal is not critical
            pass

    def _is_2fa_required(self) -> bool:
        """
        Check if 2FA is required.

        Returns:
            True if 2FA page is detected
        """
        try:
            # Look for 2FA indicators
            indicators = [
                "verification code",
                "two-factor",
                "2FA",
                "verify your identity",
                "enter the code",
            ]

            page_text = self.browser.driver.page_source.lower()

            for indicator in indicators:
                if indicator.lower() in page_text:
                    self.logger.info("2FA required for login", LogCategory.AUTH)
                    return True

            return False

        except Exception:
            return False

    def _verify_login_success(self) -> bool:
        """
        Verify that login was successful.

        Returns:
            True if logged in successfully
        """
        try:
            # Check for logout link/button (indicates logged in)
            logout_indicators = [
                "//a[contains(text(), 'Log Out')]",
                "//a[contains(text(), 'Logout')]",
                "//button[contains(text(), 'Sign Out')]",
                "//a[contains(@href, 'logout')]",
            ]

            for xpath in logout_indicators:
                try:
                    element = self.browser.driver.find_element(By.XPATH, xpath)
                    if element:
                        return True
                except NoSuchElementException:
                    continue

            # Check URL for success indicators
            current_url = self.browser.driver.current_url
            if any(indicator in current_url for indicator in ["home", "dashboard", "main"]):
                return True

            # Check for error messages
            error_indicators = [
                "invalid password",
                "login failed",
                "authentication error",
                "incorrect username",
            ]

            page_text = self.browser.driver.page_source.lower()
            for error in error_indicators:
                if error in page_text:
                    self.logger.error(f"Login error detected: {error}")
                    return False

            # Default to success if no errors found
            return True

        except Exception as e:
            self.logger.error(f"Failed to verify login: {e}")
            return False

    def _handle_orcid_authorization(self):
        """Handle ORCID authorization page if present."""
        try:
            # Look for authorize button
            auth_button = self.browser.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Authorize')] | //input[@value='Authorize']"
            )

            if auth_button:
                self.browser.safe_click(auth_button)
                self.logger.info("ORCID authorization granted")
                time.sleep(2)

        except NoSuchElementException:
            # No authorization needed
            pass

    def _store_session_data(self):
        """Store session data for later use."""
        try:
            self.session_data = {
                "cookies": self.browser.driver.get_cookies(),
                "url": self.browser.driver.current_url,
                "timestamp": time.time(),
            }
            self.logger.info("Session data stored")
        except Exception as e:
            self.logger.warning(f"Failed to store session data: {e}")

    def restore_session(self) -> bool:
        """
        Restore a previous session using stored cookies.

        Returns:
            True if session restored successfully
        """
        if not self.session_data.get("cookies"):
            return False

        try:
            # Navigate to the domain
            if "url" in self.session_data:
                self.browser.navigate_to(self.session_data["url"])

            # Add cookies
            for cookie in self.session_data["cookies"]:
                try:
                    self.browser.driver.add_cookie(cookie)
                except Exception:
                    continue

            # Refresh to apply cookies
            self.browser.driver.refresh()

            # Verify session is valid
            if self._verify_login_success():
                self.is_authenticated = True
                self.logger.success("Session restored successfully")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to restore session: {e}")
            return False

    def logout(self) -> bool:
        """
        Logout from the platform.

        Returns:
            True if logout successful
        """
        try:
            # Find and click logout link
            logout_link = self.browser.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Log Out')] | //a[contains(text(), 'Logout')]"
            )

            self.browser.safe_click(logout_link)

            self.is_authenticated = False
            self.session_data.clear()

            self.logger.success("Logged out successfully")
            return True

        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return False

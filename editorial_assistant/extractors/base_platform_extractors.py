"""Base platform extractors for different journal platforms."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from editorial_assistant.core.base_extractor import BaseExtractor
from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.utils.email_verification import EmailVerificationManager


class EmailBasedExtractor(BaseExtractor, ABC):
    """Base class for email-based journal extractors."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        self.email_manager = EmailVerificationManager()
        
    @abstractmethod
    def extract_from_emails(self) -> List[Dict[str, Any]]:
        """Extract manuscript data from email communications."""
        pass
    
    def _login(self) -> None:
        """Email-based extractors don't need traditional login."""
        pass
    
    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscripts from email communications."""
        return self.extract_from_emails()


class SIAMExtractor(BaseExtractor, ABC):
    """Base class for SIAM journal extractors using ORCID authentication."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        
    def _handle_orcid_authentication(self) -> bool:
        """Handle ORCID authentication flow."""
        try:
            # Get ORCID credentials from environment
            orcid_user = self.journal.credentials.get('username_env')
            orcid_pass = self.journal.credentials.get('password_env')
            
            if not orcid_user or not orcid_pass:
                raise Exception("ORCID credentials not found in environment variables")
            
            # Remove cookie banners on ORCID page
            self._dismiss_cookie_modal()
            
            # Wait for username field
            username_field = self._wait_for_element_by_id("username-input", timeout=15)
            if not username_field:
                username_field = self._wait_for_element_by_id("userId", timeout=5)
            
            # Wait for password field
            password_field = self._wait_for_element_by_id("password", timeout=10)
            
            if not (username_field and password_field):
                raise Exception("Could not find ORCID login fields")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(orcid_user)
            
            password_field.clear()
            password_field.send_keys(orcid_pass)
            
            # Find and click sign in button
            sign_in_button = self._wait_for_element_by_xpath("//button[contains(text(), 'Sign in')]", timeout=10)
            if not sign_in_button:
                sign_in_button = self._wait_for_element_by_xpath("//button[@type='submit']", timeout=5)
            
            if not sign_in_button:
                raise Exception("Could not find ORCID sign in button")
            
            sign_in_button.click()
            logging.info(f"[{self.journal.code}] ORCID credentials submitted")
            
            return True
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] ORCID authentication failed: {e}")
            return False
    
    def _dismiss_cookie_modal(self) -> None:
        """Dismiss ORCID cookie modal if present."""
        btn_xpaths = [
            "//button[contains(translate(., 'AUTORISER', 'autoriser'), 'autoriser tous les cookies')]",
            "//button[contains(translate(., 'TOUT REFUSER', 'tout refuser'), 'tout refuser')]",
            "//button[contains(translate(., 'ACCEPTER', 'accepter'), 'accepter')]",
            "//button[contains(.,'Accept all cookies')]",
            "//button[contains(.,'Refuse all')]"
        ]
        
        for xpath in btn_xpaths:
            try:
                button = self._wait_for_element_by_xpath(xpath, timeout=2)
                if button and button.is_displayed() and button.is_enabled():
                    button.click()
                    logging.info(f"[{self.journal.code}] Cookie modal dismissed")
                    return
            except Exception:
                continue


class EditorialManagerExtractor(BaseExtractor, ABC):
    """Base class for Editorial Manager journal extractors."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        
    def _login(self) -> None:
        """Login to Editorial Manager platform."""
        try:
            # Navigate to login page
            self.driver.get(self.journal.url)
            self._wait_for_page_load()
            
            # Dismiss cookie banners
            self._dismiss_cookie_banner()
            
            # Check if already logged in
            if self._is_logged_in():
                logging.info(f"[{self.journal.code}] Already logged in")
                return
            
            # Handle iframe-based login if needed
            if self._login_in_iframe():
                return
            
            # Standard login
            self._standard_login()
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Login failed: {e}")
            raise
    
    def _login_in_iframe(self) -> bool:
        """Try to login within iframe if present."""
        try:
            # Find iframes
            iframes = self.driver.find_elements("tag name", "iframe")
            
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    
                    # Check if login fields are present
                    username_field = self._wait_for_element_by_id("username", timeout=2)
                    password_field = self._wait_for_element_by_id("passwordTextbox", timeout=2)
                    
                    if username_field and password_field:
                        # Found login fields in iframe
                        self._fill_login_fields(username_field, password_field)
                        
                        # Find and click login button
                        login_button = self._wait_for_element_by_name("editorLogin", timeout=5)
                        if not login_button:
                            login_button = self._wait_for_element_by_xpath("//input[@value='Editor Login']", timeout=5)
                        
                        if login_button:
                            login_button.click()
                            logging.info(f"[{self.journal.code}] Logged in via iframe")
                            
                            # Switch back to main frame
                            self.driver.switch_to.default_content()
                            return True
                    
                    # Switch back to main frame
                    self.driver.switch_to.default_content()
                    
                except Exception:
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _standard_login(self) -> None:
        """Standard login flow for Editorial Manager."""
        # Get platform-specific selectors
        platform_config = self.journal.platform_config
        username_selector = platform_config.get('login_selectors', {}).get('username', 'input[id="username"]')
        password_selector = platform_config.get('login_selectors', {}).get('password', 'input[id="password"]')
        submit_selector = platform_config.get('login_selectors', {}).get('submit', 'button[type="submit"]')
        
        # Find login fields
        username_field = self._wait_for_element_by_css_selector(username_selector, timeout=10)
        password_field = self._wait_for_element_by_css_selector(password_selector, timeout=10)
        
        if not (username_field and password_field):
            raise Exception("Login fields not found")
        
        # Fill credentials
        self._fill_login_fields(username_field, password_field)
        
        # Find and click submit button
        submit_button = self._wait_for_element_by_css_selector(submit_selector, timeout=10)
        if not submit_button:
            raise Exception("Submit button not found")
        
        submit_button.click()
        logging.info(f"[{self.journal.code}] Login submitted")
    
    def _fill_login_fields(self, username_field, password_field) -> None:
        """Fill login fields with credentials."""
        username = self.journal.credentials.get('username_env')
        password = self.journal.credentials.get('password_env')
        
        if not username or not password:
            raise Exception("Credentials not found in environment variables")
        
        username_field.clear()
        username_field.send_keys(username)
        
        password_field.clear()
        password_field.send_keys(password)
    
    def _dismiss_cookie_banner(self) -> None:
        """Dismiss cookie consent banners."""
        keywords = [
            "Accept all cookies",
            "Accept cookies",
            "Accept",
            "Got it",
            "Agree",
        ]
        
        try:
            # Try by button text
            buttons = self.driver.find_elements("tag name", "button") + self.driver.find_elements("tag name", "input")
            for btn in buttons:
                try:
                    text = (btn.text or btn.get_attribute("value") or "").strip()
                    if not btn.is_displayed() or not btn.is_enabled():
                        continue
                    if any(k.lower() in text.lower() for k in keywords):
                        btn.click()
                        logging.info(f"[{self.journal.code}] Cookie consent accepted")
                        return
                except Exception:
                    continue
        except Exception:
            pass
    
    def _is_logged_in(self) -> bool:
        """Check if already logged in."""
        try:
            # Look for associate editor dashboard elements
            dashboard_indicators = [
                "Associate Editor",
                "aries-accordion-item",
                "editor.main.menu"
            ]
            
            page_source = self.driver.page_source
            return any(indicator in page_source for indicator in dashboard_indicators)
            
        except Exception:
            return False


class MSPExtractor(BaseExtractor, ABC):
    """Base class for MSP (Mathematical Sciences Publishers) journal extractors."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        
    def _login(self) -> None:
        """Login to MSP platform."""
        try:
            # Navigate to login page
            self.driver.get(self.journal.url)
            self._wait_for_page_load()
            
            # Check if already logged in by looking for Mine link
            if self._is_logged_in():
                logging.info(f"[{self.journal.code}] Already logged in")
                return
            
            # Find login fields
            username_field = self._wait_for_element_by_id("login", timeout=12)
            password_field = self._wait_for_element_by_name("password", timeout=10)
            
            if not (username_field and password_field):
                raise Exception("Login fields not found")
            
            # Get credentials
            username = self.journal.credentials.get('username_env')
            password = self.journal.credentials.get('password_env')
            
            if not username or not password:
                raise Exception("Credentials not found in environment variables")
            
            # Fill credentials
            username_field.clear()
            username_field.send_keys(username)
            
            password_field.clear()
            password_field.send_keys(password)
            
            # Find and click login button
            login_button = self._wait_for_element_by_name("signin", timeout=10)
            if not login_button:
                raise Exception("Login button not found")
            
            login_button.click()
            logging.info(f"[{self.journal.code}] Login submitted")
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Login failed: {e}")
            raise
    
    def _is_logged_in(self) -> bool:
        """Check if already logged in by looking for Mine link."""
        try:
            # Try different selectors for the Mine link
            mine_selectors = [
                ("link text", "Mine"),
                ("partial link text", "Mine"),
                ("xpath", "//a[contains(text(), 'Mine')]"),
                ("xpath", "//a[contains(@href, 'mine')]"),
                ("css selector", "a[href*='mine']"),
            ]
            
            for by, selector in mine_selectors:
                try:
                    element = self._wait_for_element(by, selector, timeout=2)
                    if element and element.is_displayed():
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _find_mine_link(self) -> Optional[Any]:
        """Find the Mine link using multiple selectors."""
        selectors = [
            ("link text", "Mine"),
            ("partial link text", "Mine"),
            ("xpath", "//a[contains(text(), 'Mine')]"),
            ("xpath", "//a[contains(@href, 'mine')]"),
            ("css selector", "a[href*='mine']"),
        ]
        
        for by, selector in selectors:
            try:
                element = self._wait_for_element(by, selector, timeout=2)
                if element and element.is_displayed():
                    return element
            except Exception:
                continue
        
        # Broader search if specific selectors fail
        try:
            all_links = self.driver.find_elements("tag name", "a")
            for link in all_links:
                try:
                    text = link.text.strip().lower()
                    href = link.get_attribute("href") or ""
                    if ("mine" in text or "mine" in href.lower()) and link.is_displayed():
                        return link
                except:
                    continue
        except:
            pass
        
        return None

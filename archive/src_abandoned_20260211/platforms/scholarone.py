"""Base extractor for ScholarOne (Manuscript Central) journals."""

import re
import time
from abc import abstractmethod
from datetime import UTC, datetime
from typing import Any

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from src.core.base_extractor import BaseExtractor
from src.core.data_models import Document, DocumentType, RefereeStatus


class ScholarOneExtractor(BaseExtractor):
    """Base extractor for ScholarOne platform journals (MF, MOR)."""

    def __init__(self, journal_code: str, headless: bool = False):
        super().__init__(journal_code, headless)
        self.base_url = f"https://mc.manuscriptcentral.com/{self._get_journal_suffix()}"
        self._2fa_required = False

    @abstractmethod
    def _get_journal_suffix(self) -> str:
        """Get the journal-specific URL suffix (e.g., 'mafi' for MF)."""
        pass

    @abstractmethod
    def _get_manuscript_pattern(self) -> str:
        """Get the journal-specific manuscript ID pattern."""
        pass

    def login(self) -> bool:
        """Common ScholarOne login process."""
        try:
            self.logger.info("Logging in to ScholarOne...")
            self.driver.get(self.base_url)
            time.sleep(3)

            # Handle cookie banner
            self._dismiss_cookie_banner()

            # Enter credentials
            email_field = self.browser_manager.wait_for_element(By.ID, "USERID")
            if not email_field:
                raise Exception("Could not find email field")

            email_field.clear()
            email_field.send_keys(self.credentials["email"])

            password_field = self.driver.find_element(By.ID, "PASSWORD")
            password_field.clear()
            password_field.send_keys(self.credentials["password"])

            # Capture timestamp BEFORE clicking login (timezone-aware)
            login_click_time = datetime.now(UTC)
            self.logger.info(f"Login button clicked at: {login_click_time}")

            # Click login using JavaScript (more reliable)
            self.driver.execute_script("document.getElementById('logInButton').click();")
            time.sleep(3)

            # Handle 2FA if needed
            if self._requires_2fa():
                self._2fa_required = True
                if not self._handle_2fa(login_click_time):
                    return False

            # Verify login success
            if "login" in self.driver.current_url.lower():
                self.add_error("Still on login page after authentication")
                return False

            self.logger.info("Login successful")
            return True

        except Exception as e:
            self.add_error(f"Login failed: {e}")
            return False

    def _dismiss_cookie_banner(self):
        """Dismiss cookie banner if present."""
        try:
            reject_button = self.driver.find_element(By.ID, "onetrust-reject-all-handler")
            self.browser_manager.safe_click(reject_button)
            time.sleep(1)
            self.logger.debug("Dismissed cookie banner")
        except Exception:
            pass

    def _requires_2fa(self) -> bool:
        """Check if 2FA is required."""
        try:
            self.driver.find_element(By.ID, "TOKEN_VALUE")
            return True
        except Exception:
            return False

    def _handle_2fa(self, login_click_time: datetime) -> bool:
        """Handle 2FA verification."""
        self.logger.info("2FA required, fetching verification code...")

        try:
            # Try multiple Gmail verification methods
            code = None

            # Method 1: Try direct import from core
            try:
                import sys
                from pathlib import Path

                core_path = Path(__file__).parent.parent.parent / "core"
                if str(core_path) not in sys.path:
                    sys.path.insert(0, str(core_path))

                from gmail_verification_wrapper import fetch_latest_verification_code

                self.logger.info(
                    f"Using gmail_verification_wrapper for 2FA (codes after {login_click_time})"
                )

                # Wait longer to ensure the email is sent and we skip old codes
                self.logger.info("Waiting for verification email to be sent...")
                time.sleep(10)

                code = fetch_latest_verification_code(
                    self.journal_code,
                    max_wait=60,  # Increased wait time
                    poll_interval=3,
                    start_timestamp=login_click_time,  # Only accept codes sent AFTER login click
                )
            except Exception as e:
                self.logger.debug(f"Direct import failed: {e}")

            # Method 2: Try Gmail Manager
            if not code:
                try:
                    self.logger.info("Trying GmailManager for 2FA code retrieval...")
                    from src.core.gmail_manager import GmailManager

                    gmail = GmailManager()
                    if gmail.service:
                        self.logger.info(
                            f"Gmail service connected, waiting up to 120s for verification email after {login_click_time}"
                        )
                        code = gmail.get_verification_code(
                            journal=self.journal_code,
                            start_time=login_click_time,  # Use login click time
                            wait_time=120,  # Increased from 60s to 120s for ScholarOne emails
                        )
                        if code:
                            self.logger.info("✅ Successfully retrieved 2FA code via Gmail API")
                        else:
                            self.logger.warning("❌ No 2FA code found via Gmail API")
                    else:
                        self.logger.warning("Gmail service not available")
                except Exception as e:
                    self.logger.warning(f"GmailManager failed: {e}")
                    self.logger.debug("Will fall back to manual entry")

            # Method 3: Manual entry for testing
            if not code and not self.headless:
                self.logger.warning("No 2FA code found automatically")
                self.logger.info("Manual entry required - please check your email")

                # Give user time to check email and enter code manually
                self.logger.info("You have 60 seconds to manually enter the 2FA code...")
                time.sleep(60)

                # Check if code was entered
                try:
                    token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                    entered_code = token_field.get_attribute("value")
                    if entered_code and len(entered_code) >= 6:
                        self.logger.info("Manual code entry detected")
                        code = entered_code
                    else:
                        self.add_error("No 2FA code entered manually")
                        return False
                except Exception:
                    self.add_error("Could not check manual 2FA entry")
                    return False
            elif not code:
                self.add_error("Could not retrieve 2FA code from Gmail")
                return False

            # Enter code (if not already entered manually)
            token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
            if not token_field.get_attribute("value"):
                self.logger.info(f"Entering 2FA code: {code[:3]}***")
                # Make sure field is interactable
                token_field.click()
                token_field.clear()
                token_field.send_keys(code)

            # Submit - ScholarOne uses VERIFY_BTN for 2FA (it's an <a> tag, not <input>)
            try:
                verify_button = self.wait.until(
                    EC.presence_of_element_located((By.ID, "VERIFY_BTN"))
                )
                self.logger.info(f"Found verify button: tag={verify_button.tag_name}")
                self.browser_manager.safe_click(verify_button)
            except Exception as e:
                self.logger.error(f"Failed to click verify button: {e}")
                # Try alternative method
                self.driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            time.sleep(5)

            # Check for verification error modal
            try:
                error_modal = self.driver.find_element(
                    By.XPATH, "//h3[contains(text(),'Verification Error')]"
                )
                if error_modal.is_displayed():
                    self.logger.warning(
                        "Verification error detected - code might be incorrect or expired"
                    )
                    # Try to close the error modal
                    try:
                        close_btn = self.driver.find_element(By.XPATH, "//button[text()='Close']")
                        close_btn.click()
                        time.sleep(1)
                    except Exception:
                        pass
                    return False
            except NoSuchElementException:
                # No error modal is good
                pass

            # Wait a bit longer for page to load
            time.sleep(5)

            # Check for success modal and close it
            try:
                success_modal = self.driver.find_element(
                    By.XPATH, "//h3[contains(text(),'Success')]"
                )
                if success_modal.is_displayed():
                    self.logger.info("Success modal detected - closing it")
                    try:
                        close_btn = self.driver.find_element(
                            By.XPATH,
                            "//button[contains(text(),'Close') or contains(@class,'close')]",
                        )
                        close_btn.click()
                        time.sleep(2)
                    except Exception:
                        pass
            except NoSuchElementException:
                pass

            # Verify we're past 2FA
            if self._requires_2fa():
                self.add_error("Still on 2FA page after code submission")
                return False

            self.logger.info("2FA successful")
            return True

        except Exception as e:
            self.add_error(f"2FA handling failed: {e}")
            return False

    def navigate_to_ae_center(self) -> bool:
        """Navigate to Associate Editor Center."""
        try:
            # Wait for main page to load
            time.sleep(3)

            # Find and click AE center link
            ae_link = self.browser_manager.wait_for_element(
                By.LINK_TEXT, "Associate Editor Center", timeout=15
            )

            if not ae_link:
                # Try partial link text
                ae_link = self.browser_manager.wait_for_element(
                    By.PARTIAL_LINK_TEXT, "Associate Editor", timeout=5
                )

            if not ae_link:
                self.add_error("Could not find Associate Editor Center link")
                return False

            self.browser_manager.safe_click(ae_link)
            time.sleep(3)

            self.logger.info("Navigated to Associate Editor Center")
            return True

        except Exception as e:
            self.add_error(f"Failed to navigate to AE Center: {e}")
            return False

    def get_manuscript_categories(self) -> list[dict[str, Any]]:
        """Get manuscript categories with counts."""
        categories = []

        try:
            # Find all links on the page
            links = self.driver.find_elements(By.TAG_NAME, "a")

            for link in links:
                text = link.text.strip()

                # Look for pattern "Category Name (count)"
                match = re.search(r"^(.+?)\s*\((\d+)\)$", text)
                if match:
                    name = match.group(1).strip()
                    count = int(match.group(2))

                    if count > 0 and self._is_manuscript_category(name):
                        categories.append({"name": name, "count": count, "element": link})
                        self.logger.info(f"Found category: {name} ({count})")

        except Exception as e:
            self.add_error(f"Failed to get categories: {e}")

        return categories

    def _is_manuscript_category(self, name: str) -> bool:
        """Check if category name is manuscript-related."""
        keywords = [
            "manuscript",
            "review",
            "decision",
            "revision",
            "awaiting",
            "pending",
            "submitted",
            "score",
            "overdue",
            "selection",
            "invitation",
            "assignment",
            "recommendation",
        ]
        return any(keyword in name.lower() for keyword in keywords)

    def extract_manuscript_id(self, text: str) -> str | None:
        """Extract manuscript ID from text."""
        pattern = self._get_manuscript_pattern()
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def extract_referee_emails_from_popups(self) -> dict[str, str]:
        """Extract referee emails from popup windows."""
        emails = {}
        main_window = self.driver.current_window_handle

        # Find all email popup links
        popup_links = self.driver.find_elements(By.XPATH, "//a[contains(@href,'mailpopup')]")

        for i, link in enumerate(popup_links):
            try:
                # Get referee name from the row
                row = link.find_element(By.XPATH, "./ancestor::tr")
                name_elem = row.find_element(By.CLASS_NAME, "largebluelink")
                referee_name = name_elem.text.strip()

                # Click to open popup
                self.browser_manager.safe_click(link)
                time.sleep(2)

                # Switch to popup
                for window in self.driver.window_handles:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break

                # Extract email from popup
                body_text = self.driver.find_element(By.TAG_NAME, "body").text

                # Find email pattern
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", body_text)
                if email_match:
                    email = email_match.group(0)
                    emails[referee_name] = email
                    self.logger.debug(f"Found email for {referee_name}: {email}")

                # Close popup
                self.driver.close()
                self.driver.switch_to.window(main_window)

            except Exception as e:
                self.logger.error(f"Failed to extract email from popup {i+1}: {e}")
                # Make sure we're back on main window
                if self.driver.current_window_handle != main_window:
                    self.driver.switch_to.window(main_window)

        return emails

    def parse_referee_status(self, status_text: str) -> RefereeStatus:
        """Parse referee status from text."""
        status_lower = status_text.lower()

        if "agreed" in status_lower or "accepted" in status_lower:
            return RefereeStatus.AGREED
        elif "declined" in status_lower:
            return RefereeStatus.DECLINED
        elif "completed" in status_lower or "submitted" in status_lower:
            return RefereeStatus.COMPLETED
        elif "overdue" in status_lower:
            return RefereeStatus.OVERDUE
        elif "unavailable" in status_lower:
            return RefereeStatus.UNAVAILABLE
        elif "invited" in status_lower or "pending" in status_lower:
            return RefereeStatus.INVITED
        else:
            return RefereeStatus.UNKNOWN

    def extract_document_links(self) -> list[Document]:
        """Extract document links from the page."""
        documents = []

        try:
            # Look for PDF links
            pdf_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href,'DOWNLOAD_FILE') and contains(text(),'PDF')]"
            )
            for link in pdf_links:
                doc = Document(
                    type=DocumentType.MANUSCRIPT,
                    url=link.get_attribute("href"),
                    filename=None,  # Will be set during download
                )
                documents.append(doc)

            # Look for cover letter links
            cover_links = self.driver.find_elements(
                By.XPATH, "//a[contains(text(),'Cover Letter')]"
            )
            for link in cover_links:
                doc = Document(type=DocumentType.COVER_LETTER, url=link.get_attribute("href"))
                documents.append(doc)

            # Look for supplementary materials
            supp_links = self.driver.find_elements(By.XPATH, "//a[contains(text(),'Supplement')]")
            for link in supp_links:
                doc = Document(type=DocumentType.SUPPLEMENTARY, url=link.get_attribute("href"))
                documents.append(doc)

        except Exception as e:
            self.add_warning(f"Failed to extract document links: {e}")

        return documents

    def navigate_to_manuscript_details(self, manuscript_link) -> bool:
        """Navigate to manuscript details page."""
        try:
            self.browser_manager.safe_click(manuscript_link)
            time.sleep(5)
            return True
        except Exception as e:
            self.add_error(f"Failed to navigate to manuscript: {e}")
            return False

    def navigate_next_document(self) -> bool:
        """Navigate to next document."""
        try:
            next_btn = self.driver.find_element(
                By.XPATH,
                "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]/img[@alt='Next Document']/..",
            )
            self.browser_manager.safe_click(next_btn)
            time.sleep(5)
            return True
        except Exception:
            return False

    def navigate_previous_document(self) -> bool:
        """Navigate to previous document."""
        try:
            prev_btn = self.driver.find_element(
                By.XPATH,
                "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]/img[@alt='Previous Document']/..",
            )
            self.browser_manager.safe_click(prev_btn)
            time.sleep(5)
            return True
        except Exception:
            return False

"""
Legacy Integration Mixin

This module contains proven working methods from legacy code,
integrated into the new professional architecture.

Based on analysis of:
- legacy_20250710_165846/complete_stable_mf_extractor.py
- legacy_20250710_165846/complete_stable_mor_extractor.py
- legacy_20250710_165846/foolproof_extractor.py
"""

import os
import time
from pathlib import Path
from typing import Any

import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from ..utils.session_manager import session_manager
from .exceptions import LoginError


class LegacyIntegrationMixin:
    """
    Mixin class containing proven working methods from legacy code.

    This class provides battle-tested implementations for:
    - ScholarOne authentication with 2FA
    - Checkbox clicking strategies
    - PDF download mechanisms
    - Error handling and recovery
    """

    def legacy_login_scholarone(self, driver: WebDriver, journal_code: str) -> bool:
        """
        Proven ScholarOne login with 2FA support.

        Based on complete_stable_*_extractor.py login methods that achieve
        90%+ reliability across MF and MOR journals.

        Args:
            driver: Selenium WebDriver instance
            journal_code: Journal code (e.g., 'MF', 'MOR')

        Returns:
            bool: True if login successful, False otherwise
        """
        session_manager.add_learning(f"Starting proven legacy login for {journal_code}")

        try:
            # Get journal URL
            journal_urls = {
                "MF": "https://mc.manuscriptcentral.com/mafi",
                "MOR": "https://mc.manuscriptcentral.com/mathor",
                "MS": "https://mc.manuscriptcentral.com/mnsc",
                "RFS": "https://mc.manuscriptcentral.com/rfs",
                "RAPS": "https://mc.manuscriptcentral.com/raps",
            }

            url = journal_urls.get(journal_code)
            if not url:
                raise LoginError(f"Unknown journal code: {journal_code}")

            self.logger.info(f"Navigating to {journal_code} dashboard: {url}")
            driver.get(url)
            time.sleep(2)

            # Handle cookies (exact same approach as working system)
            try:
                accept_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if accept_btn.is_displayed():
                    accept_btn.click()
                    self.logger.info("Accepted cookies.")
                    time.sleep(1)
            except Exception:
                self.logger.debug("No cookie accept button found.")

            # Get credentials (exact same env vars as legacy system)
            user_env = f"{journal_code}_USER"
            pass_env = f"{journal_code}_PASS"

            # Try journal-specific credentials first
            user = os.environ.get(user_env)
            password = os.environ.get(pass_env)

            # Fallback to MF credentials for other journals (proven working)
            if not user or not password:
                user = os.environ.get("MF_USER")
                password = os.environ.get("MF_PASS")

            if not user or not password:
                raise LoginError(
                    f"No credentials found for {journal_code}. Set {user_env} and {pass_env} environment variables."
                )

            # Fill login form (exact same field IDs as legacy)
            self.logger.info("Filling login form...")
            user_box = driver.find_element(By.ID, "USERID")
            pw_box = driver.find_element(By.ID, "PASSWORD")

            user_box.clear()
            user_box.send_keys(user)
            pw_box.clear()
            pw_box.send_keys(password)

            # Submit login (exact same button ID as legacy)
            login_btn = driver.find_element(By.ID, "logInButton")
            login_btn.click()
            time.sleep(4)

            # Handle verification (exact same approach as working system)
            success = self._handle_2fa_verification(driver, journal_code)
            if not success:
                return False

            # Verify login success
            if self._verify_scholarone_login_success(driver):
                self.logger.info(f"✅ {journal_code} login successful")
                session_manager.add_learning(
                    f"Successful login to {journal_code} using proven legacy method"
                )
                return True
            else:
                self.logger.error(f"❌ {journal_code} login verification failed")
                return False

        except Exception as e:
            self.logger.error(f"❌ {journal_code} login failed: {e}")
            session_manager.add_learning(f"Login failed for {journal_code}: {str(e)}")
            return False

    def _handle_2fa_verification(self, driver: WebDriver, journal_code: str) -> bool:
        """
        Handle 2FA verification using exact legacy approach.

        This method replicates the proven 2FA handling from legacy extractors
        that successfully handles email verification codes.
        """
        wait = WebDriverWait(driver, 15)
        code_input = None

        try:
            # Check for reCAPTCHA (exact same as working system)
            try:
                recaptcha_iframe = driver.find_element(
                    By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]"
                )
                if recaptcha_iframe.is_displayed():
                    driver.switch_to.frame(recaptcha_iframe)
                    checkbox = driver.find_element(By.ID, "recaptcha-anchor")
                    checkbox.click()
                    driver.switch_to.default_content()
                    self.logger.info("Clicked reCAPTCHA checkbox.")
                    time.sleep(2)
            except Exception:
                self.logger.debug("No reCAPTCHA present.")

            # Check for verification code (exact same as working system)
            try:
                code_input = wait.until(
                    lambda d: d.find_element(By.ID, "TOKEN_VALUE")
                    if self._element_exists_and_visible(d, "TOKEN_VALUE")
                    else None
                )
                self.logger.debug("Found and visible: TOKEN_VALUE")
            except TimeoutException:
                try:
                    code_input = wait.until(
                        lambda d: d.find_element(By.ID, "validationCode")
                        if self._element_exists_and_visible(d, "validationCode")
                        else None
                    )
                    self.logger.debug("Found and visible: validationCode")
                except TimeoutException:
                    self.logger.debug("No visible verification input appeared within 15s.")

            if code_input:
                self.logger.info("Verification prompt visible. Fetching code from email...")

                # Import exact same email function as legacy
                verification_code = self._fetch_verification_code_legacy(journal_code)

                if verification_code:
                    self.logger.debug(f"Verification code fetched: '{verification_code}'")
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    self.logger.info("Submitted verification code.")
                    time.sleep(3)
                    return True
                else:
                    self.logger.error("Failed to fetch verification code from email.")
                    return False
            else:
                # No 2FA required
                self.logger.info("No 2FA verification required.")
                return True

        except Exception as e:
            self.logger.error(f"Verification handling error: {e}")
            return False

    def _element_exists_and_visible(self, driver: WebDriver, element_id: str) -> bool:
        """Check if element exists and is visible."""
        try:
            element = driver.find_element(By.ID, element_id)
            return element.is_displayed()
        except:
            return False

    def _fetch_verification_code_legacy(self, journal_code: str) -> str | None:
        """
        Fetch verification code using legacy email utilities.

        This method attempts to import and use the exact same email
        verification code that works in legacy extractors.
        """
        try:
            # Use the new email verification manager
            from ..utils.email_verification import get_email_verification_manager

            email_manager = get_email_verification_manager()

            # Wait for email (exact same timing as legacy)
            self.logger.info("Waiting 5 seconds for verification email to arrive...")
            time.sleep(5)

            verification_code = email_manager.fetch_verification_code(journal=journal_code)

            return verification_code

        except ImportError as e:
            self.logger.warning(f"Could not import email verification manager: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching verification code: {e}")
            return None

    def _verify_scholarone_login_success(self, driver: WebDriver) -> bool:
        """
        Verify ScholarOne login was successful.

        Uses exact same verification logic as legacy system.
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
                "Sign Out",
            ]

            page_text = driver.find_element(By.TAG_NAME, "body").text

            for indicator in indicators:
                if indicator in page_text:
                    return True

            return False

        except Exception:
            return False

    def legacy_click_checkbox(self, driver: WebDriver, manuscript_id: str) -> bool:
        """
        Proven checkbox clicking strategy.

        Based on exact working implementation from legacy extractors
        that successfully clicks ScholarOne manuscript checkboxes.

        Args:
            driver: Selenium WebDriver instance
            manuscript_id: Manuscript ID to find and click

        Returns:
            bool: True if checkbox clicked successfully
        """
        session_manager.add_learning(f"Attempting proven checkbox click for {manuscript_id}")

        try:
            # Dismiss overlays first (from new architecture)
            if hasattr(self, "browser_manager"):
                self.browser_manager.dismiss_overlays(driver)

            # Find rows (exact same approach as legacy)
            rows = driver.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                if manuscript_id in row.text:
                    # Find checkbox using exact legacy selector
                    checkboxes = row.find_elements(
                        By.XPATH, ".//img[contains(@src, 'check_off.gif')]"
                    )

                    if checkboxes:
                        checkbox = checkboxes[0]

                        # Scroll into view (exact same as legacy)
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", checkbox
                        )
                        time.sleep(1)

                        # Click with exact same timing as legacy
                        checkbox.click()
                        time.sleep(3)

                        # Wait for page load (from new architecture)
                        if hasattr(self, "_wait_for_page_load"):
                            self._wait_for_page_load()
                        else:
                            time.sleep(2)

                        self.logger.info(f"✅ Successfully clicked checkbox for {manuscript_id}")
                        session_manager.add_learning(
                            f"Successfully clicked checkbox for {manuscript_id} using legacy method"
                        )
                        return True

            self.logger.warning(f"❌ No checkbox found for {manuscript_id}")
            return False

        except Exception as e:
            self.logger.error(f"❌ Error clicking checkbox for {manuscript_id}: {e}")
            session_manager.add_learning(f"Checkbox click failed for {manuscript_id}: {str(e)}")
            return False

    def legacy_download_pdfs(
        self, driver: WebDriver, manuscript_id: str, download_dir: Path
    ) -> dict[str, Any]:
        """
        Proven PDF download with multiple strategies.

        Based on exact working implementation from complete_stable_*_extractor.py
        that successfully downloads manuscript PDFs and referee reports.

        Args:
            driver: Selenium WebDriver instance
            manuscript_id: Manuscript ID for naming files
            download_dir: Directory to save PDFs

        Returns:
            Dict containing PDF info and downloaded files
        """
        session_manager.add_learning(f"Starting proven PDF download for {manuscript_id}")

        pdf_info = {
            "manuscript_pdf_url": "",
            "manuscript_pdf_file": "",
            "referee_reports": [],
            "additional_files": [],
            "text_reviews": [],
        }

        try:
            # Ensure download directory exists
            download_dir.mkdir(parents=True, exist_ok=True)

            # 1. Get manuscript PDF via "view submission" and tabs
            manuscript_pdf = self._get_manuscript_pdf_legacy(driver, manuscript_id, download_dir)
            if manuscript_pdf:
                pdf_info["manuscript_pdf_url"] = manuscript_pdf["url"]
                pdf_info["manuscript_pdf_file"] = manuscript_pdf["file"]
                self.logger.info(f"✅ Manuscript PDF: {manuscript_pdf['file']}")

            # 2. Get referee reports via "view review" links
            referee_reports = self._get_referee_reports_legacy(driver, manuscript_id, download_dir)
            pdf_info["referee_reports"] = referee_reports["pdf_reports"]
            pdf_info["text_reviews"] = referee_reports["text_reviews"]

            self.logger.info(
                f"✅ Found {len(pdf_info['referee_reports'])} PDF reports + {len(pdf_info['text_reviews'])} text reviews"
            )

            session_manager.add_learning(
                f"Successfully downloaded PDFs for {manuscript_id}: {len(pdf_info['referee_reports'])} reports"
            )
            return pdf_info

        except Exception as e:
            self.logger.error(f"❌ PDF discovery error for {manuscript_id}: {e}")
            session_manager.add_learning(f"PDF download failed for {manuscript_id}: {str(e)}")
            return pdf_info

    def _get_manuscript_pdf_legacy(
        self, driver: WebDriver, manuscript_id: str, download_dir: Path
    ) -> dict[str, str] | None:
        """
        Get manuscript PDF using legacy tab navigation strategy.

        This replicates the exact working approach from legacy extractors.
        """
        self.logger.info(f"🔍 Looking for manuscript PDF tabs for {manuscript_id}")

        try:
            original_windows = driver.window_handles

            # Try PDF, Original Files, HTML tabs (exact same order as legacy)
            for tab_name in ["PDF", "Original Files", "HTML"]:
                try:
                    # Look for tab link (exact same XPath as legacy)
                    tab_links = driver.find_elements(
                        By.XPATH,
                        f"//a[contains(text(), '{tab_name}') or contains(text(), '{tab_name.lower()}')]",
                    )

                    for tab_link in tab_links:
                        try:
                            # Skip if this link is too long (exact same logic as legacy)
                            link_text = tab_link.text.strip()
                            if len(link_text) > 20:
                                continue

                            self.logger.info(f"🔍 Trying {tab_name} tab: '{link_text}'")

                            # Click the tab
                            tab_link.click()
                            time.sleep(2)

                            # Check for new window
                            new_windows = driver.window_handles
                            if len(new_windows) > len(original_windows):
                                # Switch to new window
                                new_window = [w for w in new_windows if w not in original_windows][
                                    0
                                ]
                                driver.switch_to.window(new_window)
                                self.logger.info(f"✅ Opened {tab_name} tab in new window")

                                # Get PDF URL from new window
                                current_url = driver.current_url
                                self.logger.info(f"📄 {tab_name} window URL: {current_url}")

                                # Check if this is a direct PDF or download URL (exact same logic as legacy)
                                if ".pdf" in current_url.lower() or "DOWNLOAD=TRUE" in current_url:
                                    pdf_file = self._download_direct_pdf_legacy(
                                        current_url,
                                        download_dir / f"{manuscript_id}_manuscript.pdf",
                                    )

                                    # Close window and return result
                                    driver.close()
                                    driver.switch_to.window(original_windows[0])

                                    if pdf_file:
                                        return {"url": current_url, "file": str(pdf_file)}
                                else:
                                    # Look for PDF links in this window (exact same as legacy)
                                    pdf_links = driver.find_elements(
                                        By.XPATH,
                                        "//a[contains(@href, '.pdf') or contains(@href, 'DOWNLOAD=TRUE')]",
                                    )

                                    for pdf_link in pdf_links:
                                        href = pdf_link.get_attribute("href")
                                        if href and (
                                            ".pdf" in href.lower() or "DOWNLOAD=TRUE" in href
                                        ):
                                            pdf_file = self._download_direct_pdf_legacy(
                                                href,
                                                download_dir / f"{manuscript_id}_manuscript.pdf",
                                            )

                                            # Close window and return result
                                            driver.close()
                                            driver.switch_to.window(original_windows[0])

                                            if pdf_file:
                                                return {"url": href, "file": str(pdf_file)}

                                # Close window if no PDF found
                                driver.close()
                                driver.switch_to.window(original_windows[0])

                        except Exception as tab_error:
                            self.logger.warning(f"Error with {tab_name} tab: {tab_error}")
                            # Make sure we're back on original window
                            try:
                                if len(driver.window_handles) > 1:
                                    driver.switch_to.window(original_windows[0])
                            except:
                                pass
                            continue

                except Exception as selector_error:
                    self.logger.warning(f"Error finding {tab_name} tab: {selector_error}")
                    continue

            self.logger.warning("❌ No manuscript PDF found in any tab")
            return None

        except Exception as e:
            self.logger.error(f"❌ Error getting manuscript PDF: {e}")
            # Make sure we're back on original window
            try:
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[0])
            except:
                pass
            return None

    def _get_referee_reports_legacy(
        self, driver: WebDriver, manuscript_id: str, download_dir: Path
    ) -> dict[str, list]:
        """
        Get referee reports using legacy "view review" link strategy.
        """
        self.logger.info(f"🔍 Looking for referee 'view review' links for {manuscript_id}")

        reports = {"pdf_reports": [], "text_reviews": []}

        try:
            original_windows = driver.window_handles

            # Find "view review" links (exact same text as legacy)
            review_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "view review")

            for i, link in enumerate(review_links):
                try:
                    self.logger.info(f"📄 Clicking review link {i+1}")

                    # Click to open review
                    link.click()
                    time.sleep(2)

                    # Handle new window/tab
                    new_windows = driver.window_handles
                    if len(new_windows) > len(original_windows):
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        driver.switch_to.window(new_window)

                        current_url = driver.current_url

                        # Check if this is a PDF URL
                        if ".pdf" in current_url.lower() or "DOWNLOAD=TRUE" in current_url:
                            # Download PDF report
                            pdf_file = self._download_direct_pdf_legacy(
                                current_url, download_dir / f"{manuscript_id}_referee_{i+1}.pdf"
                            )
                            if pdf_file:
                                reports["pdf_reports"].append(str(pdf_file))
                        else:
                            # Extract text review
                            review_text = self._extract_review_content_legacy(driver)
                            if review_text:
                                text_file = (
                                    download_dir / f"{manuscript_id}_referee_{i+1}_review.txt"
                                )
                                with open(text_file, "w", encoding="utf-8") as f:
                                    f.write(review_text)
                                reports["text_reviews"].append(str(text_file))

                        # Close window
                        driver.close()
                        driver.switch_to.window(original_windows[0])
                        time.sleep(1)

                except Exception as e:
                    self.logger.error(f"Error processing review link {i+1}: {e}")
                    # Make sure we're back to original window
                    try:
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(original_windows[0])
                    except:
                        pass
                    continue

            return reports

        except Exception as e:
            self.logger.error(f"Error finding referee reports: {e}")
            return reports

    def _download_direct_pdf_legacy(self, url: str, filepath: Path) -> Path | None:
        """
        Download PDF directly from URL using legacy approach.
        """
        try:
            self.logger.info(f"📥 Downloading PDF: {url}")

            # Use requests to download (exact same as legacy)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            # Save file
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify file was created and has content
            if filepath.exists() and filepath.stat().st_size > 0:
                self.logger.info(
                    f"✅ Downloaded PDF: {filepath.name} ({filepath.stat().st_size} bytes)"
                )
                return filepath
            else:
                self.logger.warning(f"❌ Downloaded file is empty or missing: {filepath}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Error downloading PDF from {url}: {e}")
            return None

    def _extract_review_content_legacy(self, driver: WebDriver) -> str:
        """
        Extract review content using legacy approach.
        """
        try:
            # Get page text (exact same as legacy)
            page_text = driver.find_element(By.TAG_NAME, "body").text

            # Clean up text (exact same patterns as legacy)
            lines = page_text.split("\n")

            # Remove common headers/footers (exact same patterns as legacy)
            skip_patterns = [r"^Page \d+", r"^ScholarOne", r"^\s*$"]

            import re

            cleaned_lines = []
            for line in lines:
                if not any(re.match(pattern, line) for pattern in skip_patterns):
                    cleaned_lines.append(line)

            return "\n".join(cleaned_lines)

        except Exception:
            return ""

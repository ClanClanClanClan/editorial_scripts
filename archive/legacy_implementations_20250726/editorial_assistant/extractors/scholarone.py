"""
ScholarOne platform extractor implementation.

This module implements the extractor for ScholarOne Manuscripts platform,
used by journals like MF, MOR, MS, RFS, and RAPS.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..core.base_extractor import BaseExtractor
from ..core.data_models import (
    Manuscript,
    ManuscriptStatus,
    Referee,
    RefereeDates,
    RefereeReport,
    RefereeStatus,
)
from ..core.exceptions import LoginError, NavigationError, RefereeDataError
from ..core.legacy_integration import LegacyIntegrationMixin
from ..utils.config_loader import ConfigLoader
from ..utils.session_manager import session_manager


class ScholarOneExtractor(BaseExtractor, LegacyIntegrationMixin):
    """Extractor for ScholarOne Manuscripts platform with proven legacy methods."""

    def __init__(self, journal_code: str, **kwargs):
        """
        Initialize ScholarOne extractor.

        Args:
            journal_code: Journal code (e.g., 'MF', 'MOR')
            **kwargs: Additional arguments passed to base class
        """
        # Load journal configuration
        config_loader = ConfigLoader()
        journal = config_loader.get_journal(journal_code)

        super().__init__(journal, **kwargs)

        # Platform-specific configuration
        self.platform_config = config_loader.get_platform_config("scholarone")
        self.verification_required = False

    def _login(self) -> None:
        """Login to ScholarOne platform using proven legacy method."""
        session_manager.add_learning(
            f"Starting enhanced login for {self.journal.name} using legacy integration"
        )

        # Use proven legacy login method
        success = self.legacy_login_scholarone(self.driver, self.journal.code)

        if not success:
            raise LoginError(f"Login failed for {self.journal.name} using proven legacy method")

        session_manager.add_learning(f"Successfully logged into {self.journal.name}")

    def _handle_2fa_if_needed(self) -> None:
        """Handle 2FA verification if required."""
        try:
            # Check for verification code input
            code_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "TOKEN_VALUE"))
            )

            if code_input.is_displayed():
                self.logger.info("2FA verification required")

                # Import email utilities
                try:
                    import sys
                    from pathlib import Path

                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core.email_utils import fetch_latest_verification_code

                    # Wait for email
                    self.logger.info("Waiting for verification email...")
                    time.sleep(10)

                    verification_code = fetch_latest_verification_code(journal=self.journal.code)

                    if verification_code:
                        code_input.clear()
                        code_input.send_keys(verification_code)
                        code_input.send_keys(Keys.RETURN)
                        time.sleep(3)
                        self.logger.info(f"Verification code submitted: {verification_code}")
                    else:
                        self.logger.warning("No verification code found in email")

                except ImportError:
                    self.logger.warning("Email utilities not available for 2FA")

        except TimeoutException:
            # No 2FA required
            pass

    def _verify_login_success(self) -> bool:
        """Verify login was successful."""
        try:
            # Check URL
            if "login" in self.driver.current_url.lower():
                return False

            # Check for logged-in indicators
            indicators = [
                "Associate Editor Center",
                "Author Center",
                "Reviewer Center",
                "Logout",
                "Sign Out",
            ]

            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            for indicator in indicators:
                if indicator in page_text:
                    return True

            return False

        except Exception:
            return False

    def _navigate_to_manuscripts(self) -> None:
        """Navigate to manuscripts list."""
        self.logger.info("Navigating to manuscripts")

        try:
            # Click Associate Editor Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            self._wait_for_page_load()

            # Navigate to first configured category
            if self.journal.categories:
                category = self.journal.categories[0]
                self.logger.info(f"Navigating to category: {category}")

                category_link = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, category))
                )
                category_link.click()
                self._wait_for_page_load()
            else:
                raise NavigationError("No categories configured for journal")

        except TimeoutException:
            raise NavigationError("Navigation timed out")
        except Exception as e:
            raise NavigationError(f"Navigation failed: {str(e)}")

    def _extract_manuscripts(self) -> list[Manuscript]:
        """Extract manuscripts from current page."""
        self.logger.info("Extracting manuscripts")
        manuscripts = []

        try:
            # Get page source
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Find manuscript IDs using pattern
            pattern = self.journal.patterns.get("manuscript_id", r"\w+-\d{4}-\d{4}")
            manuscript_ids = set()

            # Search in all text
            for text in soup.stripped_strings:
                matches = re.findall(pattern, text)
                manuscript_ids.update(matches)

            # Create manuscript objects
            for manuscript_id in manuscript_ids:
                manuscript = Manuscript(
                    manuscript_id=manuscript_id,
                    title="",  # Will be filled in _process_manuscript
                    status=ManuscriptStatus.AWAITING_REVIEWER_SCORES,
                    journal_code=self.journal.code,
                )
                manuscripts.append(manuscript)

            self.logger.info(f"Found {len(manuscripts)} manuscripts")
            return manuscripts

        except Exception as e:
            self.logger.error(f"Error extracting manuscripts: {e}")
            return []

    def _process_manuscript(self, manuscript: Manuscript) -> None:
        """Process a single manuscript."""
        self.logger.info(f"Processing manuscript: {manuscript.manuscript_id}")

        try:
            # Click on manuscript
            if not self._click_manuscript(manuscript.manuscript_id):
                raise RefereeDataError(f"Could not click on {manuscript.manuscript_id}")

            # Extract manuscript details
            self._extract_manuscript_details(manuscript)

            # Extract referees
            referees = self._extract_referees()
            manuscript.referees = referees

            # Extract PDFs
            pdf_path = self._extract_manuscript_pdf(manuscript.manuscript_id)
            if pdf_path:
                manuscript.pdf_path = pdf_path

            # Extract referee reports
            self._extract_referee_reports(manuscript)

            # Navigate back
            self._navigate_back()

        except Exception as e:
            self.logger.error(f"Error processing {manuscript.manuscript_id}: {e}")
            self.errors.append(f"Failed to process {manuscript.manuscript_id}: {str(e)}")

    def _click_manuscript(self, manuscript_id: str) -> bool:
        """Click on manuscript checkbox using proven legacy method."""
        # Use proven legacy checkbox clicking strategy
        return self.legacy_click_checkbox(self.driver, manuscript_id)

    def _extract_manuscript_details(self, manuscript: Manuscript) -> None:
        """Extract manuscript title and other details."""
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract title
            title_patterns = [
                r"Title:\s*([^\n]+)",
                r"Manuscript Title:\s*([^\n]+)",
                r"<b>Title:</b>\s*([^<]+)",
            ]

            page_text = soup.get_text()
            for pattern in title_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    manuscript.title = match.group(1).strip()
                    break

            if not manuscript.title:
                manuscript.title = f"Manuscript {manuscript.manuscript_id}"

        except Exception as e:
            self.logger.error(f"Error extracting manuscript details: {e}")

    def _extract_referees(self) -> list[Referee]:
        """Extract referee information."""
        referees = []

        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Find reviewer table
            reviewer_sections = soup.find_all(
                ["table", "div"], class_=re.compile("reviewer|referee", re.I)
            )

            if not reviewer_sections:
                # Try finding by text
                for table in soup.find_all("table"):
                    if "Reviewer List" in table.get_text():
                        reviewer_sections = [table]
                        break

            for section in reviewer_sections:
                # Find reviewer rows
                rows = section.find_all("tr")

                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    # Extract referee data
                    referee_data = self._parse_referee_row(cells)
                    if referee_data:
                        referee = self._create_referee_from_data(referee_data)
                        referees.append(referee)

            self.logger.info(f"Extracted {len(referees)} referees")
            return referees

        except Exception as e:
            self.logger.error(f"Error extracting referees: {e}")
            return []

    def _parse_referee_row(self, cells: list) -> dict[str, Any] | None:
        """Parse a single referee row."""
        try:
            # Get cell texts
            texts = [cell.get_text(strip=True) for cell in cells]

            # Skip header rows
            if any(header in texts[0].lower() for header in ["reviewer", "name", "referee"]):
                return None

            data = {
                "raw_name": texts[0] if len(texts) > 0 else "",
                "status": texts[1] if len(texts) > 1 else "",
                "dates_text": " ".join(texts[2:]) if len(texts) > 2 else "",
            }

            # Parse name and institution
            name, institution = self._parse_name_institution(data["raw_name"])
            data["name"] = name
            data["institution"] = institution

            # Parse dates
            data["dates"] = self._parse_dates(data["dates_text"])

            # Parse status
            data["referee_status"] = self._parse_status(data["status"])

            return data

        except Exception as e:
            self.logger.debug(f"Error parsing referee row: {e}")
            return None

    def _parse_name_institution(self, raw_text: str) -> tuple:
        """Parse referee name and institution."""
        # Clean text
        text = raw_text.strip()

        # Patterns for name extraction
        patterns = [
            r"^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z][a-z]|University|College|Institute|School)",
            r"^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?:\s*\([A-Z0-9]+\))",
            r"^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)$",
        ]

        name = text
        institution = None

        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                name = match.group(1).strip()
                # Get remaining text as institution
                institution = text[len(name) :].strip()
                break

        # Clean up institution
        if institution:
            institution = re.sub(r"^\s*[-,]\s*", "", institution)
            institution = institution.strip()
            if not institution:
                institution = None

        return name, institution

    def _parse_dates(self, dates_text: str) -> RefereeDates:
        """Parse dates from text."""
        dates = RefereeDates()

        # Date patterns
        date_patterns = {
            "invited": r"Invited[:\s]+(\d{1,2}-\w{3}-\d{4})",
            "agreed": r"Agreed[:\s]+(\d{1,2}-\w{3}-\d{4})",
            "declined": r"Declined[:\s]+(\d{1,2}-\w{3}-\d{4})",
            "due": r"Due[:\s]+(\d{1,2}-\w{3}-\d{4})",
            "completed": r"Completed[:\s]+(\d{1,2}-\w{3}-\d{4})",
        }

        for field, pattern in date_patterns.items():
            match = re.search(pattern, dates_text, re.IGNORECASE)
            if match:
                try:
                    date_obj = datetime.strptime(match.group(1), "%d-%b-%Y").date()
                    setattr(dates, field, date_obj)
                except:
                    pass

        return dates

    def _parse_status(self, status_text: str) -> RefereeStatus:
        """Parse referee status."""
        status_lower = status_text.lower()

        if "agreed" in status_lower:
            return RefereeStatus.AGREED
        elif "declined" in status_lower:
            return RefereeStatus.DECLINED
        elif "completed" in status_lower:
            return RefereeStatus.COMPLETED
        elif "invited" in status_lower:
            return RefereeStatus.INVITED
        elif "overdue" in status_lower:
            return RefereeStatus.OVERDUE
        else:
            return RefereeStatus.UNKNOWN

    def _create_referee_from_data(self, data: dict[str, Any]) -> Referee:
        """Create Referee object from parsed data."""
        return Referee(
            name=data["name"],
            institution=data.get("institution"),
            status=data.get("referee_status", RefereeStatus.UNKNOWN),
            dates=data.get("dates", RefereeDates()),
            raw_data=data,
        )

    def _extract_manuscript_pdf(self, manuscript_id: str) -> Path | None:
        """Extract manuscript PDF using proven legacy method."""
        try:
            # Use proven legacy PDF download method
            download_dir = self.output_dir / "pdfs"
            pdf_info = self.legacy_download_pdfs(self.driver, manuscript_id, download_dir)

            if pdf_info.get("manuscript_pdf_file"):
                return Path(pdf_info["manuscript_pdf_file"])

            return None

        except Exception as e:
            self.logger.error(f"Error extracting manuscript PDF: {e}")
            return None

    def _extract_referee_reports(self, manuscript: Manuscript) -> None:
        """Extract referee reports if available."""
        try:
            # Look for "view review" links
            review_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "view review")

            for i, link in enumerate(review_links):
                try:
                    # Click to open review
                    link.click()
                    time.sleep(2)

                    # Handle new window/tab
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[-1])

                    # Extract review content
                    review_text = self._extract_review_content()

                    # Try to match with referee
                    if i < len(manuscript.referees):
                        referee = manuscript.referees[i]
                        referee.report = RefereeReport(
                            text_content=review_text, submitted_date=datetime.now()
                        )

                    # Close window/tab
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])

                except Exception as e:
                    self.logger.error(f"Error extracting referee report: {e}")

        except Exception as e:
            self.logger.error(f"Error finding referee reports: {e}")

    def _extract_review_content(self) -> str:
        """Extract review content from current page."""
        try:
            # Get page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Clean up text
            lines = page_text.split("\n")

            # Remove common headers/footers
            skip_patterns = [r"^Page \d+", r"^ScholarOne", r"^\s*$"]

            cleaned_lines = []
            for line in lines:
                if not any(re.match(pattern, line) for pattern in skip_patterns):
                    cleaned_lines.append(line)

            return "\n".join(cleaned_lines)

        except Exception:
            return ""

    def _navigate_back(self) -> None:
        """Navigate back to manuscript list."""
        try:
            self.driver.back()
            time.sleep(2)
            self._wait_for_page_load()
        except:
            # If back fails, re-navigate
            self._navigate_to_manuscripts()

    def _wait_for_page_load(self) -> None:
        """Wait for page to fully load."""
        try:
            # Wait for jQuery if available
            self.driver.execute_script(
                """
                if (typeof jQuery !== 'undefined') {
                    return jQuery.active == 0;
                }
                return true;
            """
            )

            # Additional wait
            time.sleep(1)

        except:
            time.sleep(2)

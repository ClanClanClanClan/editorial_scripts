"""Nonlinear Analysis (NACO) journal extractor."""

import logging
import re
import time
from typing import Any

from bs4 import BeautifulSoup
from selenium.common.exceptions import ElementClickInterceptedException

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.base_platform_extractors import MSPExtractor


class NACOExtractor(MSPExtractor):
    """NACO extractor using MSP (Mathematical Sciences Publishers) platform."""

    def __init__(self, journal: JournalConfig):
        super().__init__(journal)

    def extract_manuscripts(self) -> list[dict[str, Any]]:
        """Extract manuscripts from NACO dashboard."""
        try:
            # Login to NACO
            self._login()
            time.sleep(1.5)

            # Navigate to Mine page
            mine_link = self._find_mine_link()
            if not mine_link:
                raise Exception("Mine link not found")

            # Click Mine link with retry logic
            self._click_mine_link_with_retry(mine_link)

            # Wait for Mine page to load
            time.sleep(2.0)

            # Parse manuscripts from page
            manuscripts = self._parse_manuscripts_from_mine_page()

            logging.info(f"[{self.journal.code}] Extracted {len(manuscripts)} manuscripts")
            return manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Manuscript extraction failed: {e}")
            self._save_debug_html("extraction_failed")
            return []

    def _click_mine_link_with_retry(self, mine_link) -> None:
        """Click Mine link with retry logic for headless mode."""
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", mine_link)

            # Try to click with retries
            for attempt in range(5):
                if mine_link.is_displayed() and mine_link.is_enabled():
                    try:
                        mine_link.click()
                        logging.info(
                            f"[{self.journal.code}] Clicked 'Mine' link on attempt {attempt + 1}"
                        )
                        return
                    except ElementClickInterceptedException:
                        time.sleep(0.8)
                else:
                    time.sleep(0.8)

            # If clicking failed, try JavaScript click
            logging.warning(f"[{self.journal.code}] Normal click failed, trying JavaScript click")
            self.driver.execute_script("arguments[0].click();", mine_link)

        except Exception as e:
            logging.error(f"[{self.journal.code}] Failed to click Mine link: {e}")
            raise

    def _parse_manuscripts_from_mine_page(self) -> list[dict[str, Any]]:
        """Parse manuscripts from the Mine page."""
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            articles = soup.find_all("article", class_="JournalView-Listing")

            # Save page for debugging
            self._save_debug_html("mine_page")

            if not articles:
                logging.info(f"[{self.journal.code}] No articles assigned (empty AE queue)")
                return []

            manuscripts = []

            for article in articles:
                try:
                    # Check if this is the user's AE block
                    name_span = article.find("span", {"data-tooltip": "Associate Editor"})
                    if not name_span or "Possamaï" not in name_span.text:
                        continue  # Not the user's AE block

                    # Check for "no articles" message
                    h2 = article.find("h2")
                    if h2 and "no articles" in h2.text.lower():
                        continue  # No manuscripts assigned

                    # Extract manuscript details
                    manuscript_data = self._parse_manuscript_from_article(article)
                    if manuscript_data:
                        manuscripts.append(manuscript_data)

                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to parse article: {e}")
                    continue

            return manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Failed to parse Mine page: {e}")
            return []

    def _parse_manuscript_from_article(self, article) -> dict[str, Any] | None:
        """Extract manuscript data from an article element."""
        try:
            manuscript_data = {
                "Manuscript #": "",
                "Title": "",
                "Contact Author": "",
                "Current Stage": "",
                "Submission Date": "",
                "Referees": [],
            }

            # Extract manuscript ID from links or spans
            id_links = article.find_all("a", href=True)
            for link in id_links:
                href = link.get("href", "")
                text = link.text.strip()

                # Look for NACO manuscript ID pattern
                if "NACO-" in text.upper() or "manuscript" in href.lower():
                    manuscript_data["Manuscript #"] = text.upper()
                    break

                # Try to extract from href if not found in text
                if not manuscript_data["Manuscript #"]:
                    match = re.search(r"id=(\d+)", href)
                    if match:
                        manuscript_data["Manuscript #"] = f"NACO-{match.group(1)}"

            # Extract title - usually in h3 or strong tags
            title_elements = article.find_all(["h3", "strong", "b"])
            for element in title_elements:
                text = element.text.strip()
                if text and len(text) > 10 and not text.startswith("Associate"):
                    manuscript_data["Title"] = text
                    break

            # Extract author information - often in italics or specific spans
            author_elements = article.find_all(["i", "em", "span"])
            for element in author_elements:
                text = element.text.strip()
                if text and ("by " in text.lower() or "@" in text):
                    # Clean up author name
                    author = text.replace("by ", "").replace("By ", "").strip()
                    if author:
                        manuscript_data["Contact Author"] = author
                        break

            # Extract current stage from status indicators
            status_elements = article.find_all(["span", "div"])
            for element in status_elements:
                text = element.text.strip().lower()
                if any(
                    keyword in text
                    for keyword in ["under review", "awaiting", "assigned", "pending"]
                ):
                    manuscript_data["Current Stage"] = element.text.strip()
                    break

            # Extract submission date
            date_elements = article.find_all(["span", "div", "small"])
            for element in date_elements:
                text = element.text.strip()
                if any(keyword in text.lower() for keyword in ["submitted", "received", "date"]):
                    date_match = re.search(
                        r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}", text
                    )
                    if date_match:
                        manuscript_data["Submission Date"] = date_match.group(0)
                        break

            # Extract referee information from nested elements
            referee_elements = article.find_all(["ul", "ol", "div"])
            for element in referee_elements:
                if "referee" in element.text.lower() or "reviewer" in element.text.lower():
                    referees = self._extract_referees_from_element(element)
                    if referees:
                        manuscript_data["Referees"] = referees
                        break

            # Only return if we have at least a manuscript ID or title
            if manuscript_data["Manuscript #"] or manuscript_data["Title"]:
                logging.debug(
                    f"[{self.journal.code}] Parsed manuscript: {manuscript_data['Manuscript #']} - {manuscript_data['Title']}"
                )
                return manuscript_data

            return None

        except Exception as e:
            logging.error(f"[{self.journal.code}] Error parsing manuscript from article: {e}")
            return None

    def _extract_referees_from_element(self, element) -> list[dict[str, Any]]:
        """Extract referee information from a container element."""
        referees = []

        try:
            # Look for referee entries in list items or divs
            referee_items = element.find_all(["li", "div", "p"])

            for item in referee_items:
                text = item.text.strip()
                if not text or len(text) < 5:
                    continue

                # Extract email addresses
                email_matches = re.findall(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text
                )

                if email_matches:
                    # Try to extract name (usually before the email)
                    name_part = text.split("@")[0] if "@" in text else text
                    name = re.sub(r"[^\w\s]", "", name_part).strip()

                    # Determine status from keywords
                    status = "Contacted"
                    if any(
                        keyword in text.lower() for keyword in ["accepted", "agreed", "confirmed"]
                    ):
                        status = "Accepted"
                    elif any(
                        keyword in text.lower() for keyword in ["declined", "rejected", "refused"]
                    ):
                        status = "Declined"

                    referee = {
                        "Referee Name": name,
                        "Referee Email": email_matches[0],
                        "Status": status,
                        "Contacted Date": "",
                        "Due Date": "",
                    }

                    # Try to extract dates
                    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", text)
                    if date_matches:
                        referee["Contacted Date"] = date_matches[0]

                    referees.append(referee)

        except Exception as e:
            logging.warning(f"[{self.journal.code}] Error extracting referees: {e}")

        return referees

    def _save_debug_html(self, suffix: str) -> None:
        """Save page HTML for debugging purposes."""
        try:
            filename = f"naco_debug_{suffix}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logging.debug(f"[{self.journal.code}] Debug HTML saved: {filename}")
        except Exception as e:
            logging.warning(f"[{self.journal.code}] Failed to save debug HTML: {e}")

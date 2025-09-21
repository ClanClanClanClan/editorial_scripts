"""Journal of Optimization Theory and Applications (JOTA) extractor."""

import logging
import re
from datetime import datetime
from typing import Any

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.base_platform_extractors import EditorialManagerExtractor
from editorial_assistant.utils.email_verification import EmailVerificationManager


class JOTAExtractor(EditorialManagerExtractor):
    """JOTA extractor with both web scraping and email capabilities."""

    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        self.email_manager = EmailVerificationManager()

    def extract_manuscripts(self) -> list[dict[str, Any]]:
        """Extract manuscripts using both web scraping and email parsing."""
        try:
            # Try web scraping first
            web_manuscripts = self._extract_from_web()

            # Enhance with email data
            email_data = self._extract_from_emails()

            # Merge web and email data
            merged_manuscripts = self._merge_web_and_email_data(web_manuscripts, email_data)

            logging.info(
                f"[{self.journal.code}] Extracted {len(merged_manuscripts)} manuscripts total"
            )
            return merged_manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Manuscript extraction failed: {e}")
            # Fallback to email-only extraction
            return self._extract_from_emails_only()

    def _extract_from_web(self) -> list[dict[str, Any]]:
        """Extract manuscripts from JOTA web interface."""
        try:
            # Login to Editorial Manager
            self._login()

            # Navigate to manuscript list
            manuscripts = self._collect_manuscripts_from_dashboard()

            logging.info(
                f"[{self.journal.code}] Web extraction found {len(manuscripts)} manuscripts"
            )
            return manuscripts

        except Exception as e:
            logging.warning(f"[{self.journal.code}] Web extraction failed: {e}")
            return []

    def _extract_from_emails(self) -> dict[str, Any]:
        """Extract data from JOTA emails to enhance web data."""
        try:
            # Search for JOTA-related emails
            flagged_query = "is:starred subject:(JOTA)"
            weekly_overview_query = 'subject:"JOTA - Weekly Overview Of Your Assignments"'

            # Fetch flagged emails (acceptance + invitation)
            flagged_emails = self.email_manager.search_emails(flagged_query)
            flagged_data = []

            for email in flagged_emails:
                try:
                    if "Reviewer has agreed to review" in email.get("subject", ""):
                        flagged_data.append(self._parse_acceptance_email(email))
                    elif "Reviewer Invitation for" in email.get("subject", ""):
                        flagged_data.append(self._parse_invitation_email(email))
                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to parse flagged email: {e}")

            # Fetch weekly overview emails
            weekly_emails = self.email_manager.search_emails(weekly_overview_query)
            weekly_data = []

            for email in weekly_emails:
                try:
                    weekly_data.append(self._parse_weekly_overview_email(email))
                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to parse weekly email: {e}")

            return {"flagged_emails": flagged_data, "weekly_overviews": weekly_data}

        except Exception as e:
            logging.error(f"[{self.journal.code}] Email extraction failed: {e}")
            return {"flagged_emails": [], "weekly_overviews": []}

    def _extract_from_emails_only(self) -> list[dict[str, Any]]:
        """Fallback: extract manuscripts from emails only."""
        try:
            email_data = self._extract_from_emails()

            # Convert email data to manuscript format
            manuscripts = []

            # Process weekly overviews to get manuscript list
            for overview in email_data.get("weekly_overviews", []):
                for manuscript in overview.get("manuscripts", []):
                    manuscripts.append(
                        {
                            "Manuscript #": manuscript.get("manuscript_id", ""),
                            "Title": manuscript.get("title", ""),
                            "Contact Author": manuscript.get("authors", ""),
                            "Current Stage": "Under Review",
                            "Referees": [],
                            "Source": "Email Only",
                        }
                    )

            # Enhance with referee data from flagged emails
            self._enhance_with_referee_emails(manuscripts, email_data.get("flagged_emails", []))

            logging.info(
                f"[{self.journal.code}] Email-only extraction found {len(manuscripts)} manuscripts"
            )
            return manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Email-only extraction failed: {e}")
            return []

    def _collect_manuscripts_from_dashboard(self) -> list[dict[str, Any]]:
        """Collect manuscripts from Editorial Manager dashboard."""
        try:
            # Navigate to pending tasks/manuscript list
            platform_config = self.journal.platform_config
            manuscript_list_link = platform_config.get("navigation", {}).get(
                "manuscript_list", 'a[href*="PendingTasks"]'
            )

            manuscript_link = self._wait_for_element_by_css_selector(
                manuscript_list_link, timeout=10
            )
            if manuscript_link:
                manuscript_link.click()
                self._wait_for_page_load()

            # Extract manuscripts from table
            manuscripts = self._extract_manuscripts_from_table()

            return manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Dashboard collection failed: {e}")
            return []

    def _extract_manuscripts_from_table(self) -> list[dict[str, Any]]:
        """Extract manuscripts from Editorial Manager table."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            manuscripts = []

            # Find the main manuscripts table
            table = soup.find("table")
            if not table:
                return []

            seen_ids = set()

            for row in table.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) < 8:  # Minimum expected columns
                    continue

                try:
                    # Extract manuscript data (adjust indices based on JOTA table structure)
                    manuscript_id = tds[1].get_text(strip=True) if len(tds) > 1 else ""

                    if not manuscript_id or manuscript_id in seen_ids:
                        continue

                    seen_ids.add(manuscript_id)

                    title = tds[3].get_text(strip=True) if len(tds) > 3 else ""
                    author = (
                        self._clean_author_name(tds[4].get_text(strip=True)) if len(tds) > 4 else ""
                    )
                    status = tds[7].get_text(strip=True) if len(tds) > 7 else ""

                    # Extract referee information
                    referees = []
                    if len(tds) > 8:
                        referees = self._extract_referees_from_column(tds[8])

                    manuscripts.append(
                        {
                            "Manuscript #": manuscript_id,
                            "Title": title,
                            "Contact Author": author,
                            "Current Stage": self._normalize_status(status),
                            "Referees": referees,
                        }
                    )

                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to parse table row: {e}")
                    continue

            return manuscripts

        except Exception as e:
            logging.error(f"[{self.journal.code}] Table extraction failed: {e}")
            return []

    def _extract_referees_from_column(self, referees_column) -> list[dict[str, Any]]:
        """Extract referee information from the referees column."""
        referees = []

        try:
            # Look for referee details
            reviewer_details = referees_column.find_all("div", class_="reviewerHoverDetails")

            for detail_div in reviewer_details:
                try:
                    # Find associated link
                    prev_link = detail_div.find_previous("a", class_="linkWithFlags")
                    if not prev_link:
                        continue

                    referee_name = prev_link.get_text(strip=True)

                    # Extract status from detail div
                    status_text = ""
                    for status_div in detail_div.find_all("div", class_="rs-headerRow"):
                        cells = status_div.find_all("span", class_="rs-overlay-cell")
                        if len(cells) >= 2:
                            status_text = cells[1].get_text(strip=True)
                        elif len(cells) == 1:
                            status_text = cells[0].get_text(strip=True)

                    status_text = status_text.lower()

                    # Skip declined or completed referees
                    if "declined" in status_text or "complete" in status_text:
                        continue

                    # Include active referees
                    if any(keyword in status_text for keyword in ["agreed", "pending", "invited"]):
                        # Try to get referee email by clicking the link
                        referee_email = self._get_referee_email(prev_link, referee_name)

                        referees.append(
                            {
                                "Referee Name": referee_name,
                                "Referee Email": referee_email,
                                "Status": status_text.capitalize(),
                                "Due Date": "",  # Could be extracted if visible
                            }
                        )

                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to extract referee details: {e}")
                    continue

        except Exception as e:
            logging.warning(f"[{self.journal.code}] Failed to extract referees from column: {e}")

        return referees

    def _get_referee_email(self, link_element, referee_name: str) -> str:
        """Get referee email by following the profile link."""
        try:
            # Find the actual clickable element in the current page
            clickable_elements = self.driver.find_elements("css selector", "a.linkWithFlags")

            target_element = None
            for element in clickable_elements:
                if element.text.strip() == referee_name:
                    target_element = element
                    break

            if not target_element:
                return ""

            # Store current window handle
            original_window = self.driver.current_window_handle

            # Click the link (may open in new window)
            target_element.click()

            # Wait for new window and switch to it
            self._wait_for_new_window(original_window)

            if len(self.driver.window_handles) > 1:
                new_window = [h for h in self.driver.window_handles if h != original_window][0]
                self.driver.switch_to.window(new_window)

                self._wait_for_page_load()

                # Extract email from referee profile
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                # Look for mailto links
                email_link = soup.find("a", href=re.compile(r"mailto:"))
                if email_link:
                    email = email_link.get_text(strip=True)

                    # Close new window and return to original
                    self.driver.close()
                    self.driver.switch_to.window(original_window)

                    return email

                # Close new window and return to original
                self.driver.close()
                self.driver.switch_to.window(original_window)

            return ""

        except Exception as e:
            logging.warning(
                f"[{self.journal.code}] Failed to get referee email for {referee_name}: {e}"
            )

            # Ensure we're back to the original window
            try:
                if len(self.driver.window_handles) > 1:
                    for handle in self.driver.window_handles[1:]:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass

            return ""

    def _parse_acceptance_email(self, email: dict[str, Any]) -> dict[str, Any]:
        """Parse referee acceptance email."""
        subject = email.get("subject", "")
        body = email.get("body", "")
        date = email.get("date")

        # Extract manuscript ID
        ms_id_match = re.search(r"JOTA-D-\d{2}-\d{5}R?\d*", subject)
        manuscript_id = ms_id_match.group(0) if ms_id_match else None

        # Extract referee name
        referee_match = re.search(
            r"([A-Z][a-zA-Z\s\.\-']{2,}),?\s*(Ph\.D\.?|PhD|MD)?\s*has agreed", body, re.IGNORECASE
        )
        referee_name = referee_match.group(1).strip() if referee_match else None

        return {
            "type": "acceptance",
            "manuscript_id": manuscript_id,
            "referee_name": referee_name,
            "date": date.isoformat() if isinstance(date, datetime) else str(date),
            "subject": subject,
            "body": body,
        }

    def _parse_invitation_email(self, email: dict[str, Any]) -> dict[str, Any]:
        """Parse referee invitation email."""
        subject = email.get("subject", "")
        body = email.get("body", "")
        date = email.get("date")

        # Extract manuscript ID
        ms_id_match = re.search(r"JOTA-D-\d{2}-\d{5}R?\d*", subject + " " + body)
        manuscript_id = ms_id_match.group(0) if ms_id_match else None

        # Extract referee name
        referee_match = re.search(
            r"Dear\s+(Prof\.|Dr\.|Mr\.|Ms\.)?\s*([A-Z][a-zA-Z\s\.\-']+),", body
        )
        referee_name = referee_match.group(2).strip() if referee_match else None

        # Extract title
        title_match = re.search(r'for the article "(.+?)"', body, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None

        return {
            "type": "invitation",
            "manuscript_id": manuscript_id,
            "referee_name": referee_name,
            "title": title,
            "date": date.isoformat() if isinstance(date, datetime) else str(date),
            "subject": subject,
            "body": body,
        }

    def _parse_weekly_overview_email(self, email: dict[str, Any]) -> dict[str, Any]:
        """Parse weekly overview email with manuscript statuses."""
        subject = email.get("subject", "")
        body = email.get("body", "")
        date = email.get("date")

        # Extract manuscripts from body
        ms_pattern = re.compile(
            r"(JOTA-D-\d{2}-\d{5}R?\d*)\s+submitted.*?Title:\s*(.+?)\s*Authors:\s*(.+?)(?=(JOTA-D-|$))",
            re.DOTALL,
        )

        manuscripts = []
        for match in ms_pattern.finditer(body):
            manuscript_id = match.group(1).strip()
            title = match.group(2).strip().replace("\n", " ").replace("\r", "")
            authors = match.group(3).strip().replace("\n", " ").replace("\r", "")

            manuscripts.append(
                {
                    "manuscript_id": manuscript_id,
                    "title": title,
                    "authors": authors,
                }
            )

        return {
            "type": "weekly_overview",
            "date": date.isoformat() if isinstance(date, datetime) else str(date),
            "subject": subject,
            "body": body,
            "manuscripts": manuscripts,
        }

    def _merge_web_and_email_data(
        self, web_manuscripts: list[dict[str, Any]], email_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Merge web scraping results with email data."""
        # Start with web manuscripts as base
        merged = {ms["Manuscript #"]: ms for ms in web_manuscripts if ms.get("Manuscript #")}

        # Enhance with email data
        for flagged_email in email_data.get("flagged_emails", []):
            manuscript_id = flagged_email.get("manuscript_id")
            if not manuscript_id:
                continue

            if manuscript_id in merged:
                # Update existing manuscript with email data
                manuscript = merged[manuscript_id]

                if flagged_email.get("type") == "acceptance" and flagged_email.get("referee_name"):
                    # Add or update referee status
                    self._update_referee_status(
                        manuscript, flagged_email["referee_name"], "Accepted"
                    )

                elif flagged_email.get("type") == "invitation" and flagged_email.get(
                    "referee_name"
                ):
                    # Add invited referee
                    self._update_referee_status(
                        manuscript, flagged_email["referee_name"], "Invited"
                    )

        return list(merged.values())

    def _enhance_with_referee_emails(
        self, manuscripts: list[dict[str, Any]], flagged_emails: list[dict[str, Any]]
    ) -> None:
        """Enhance manuscripts with referee data from emails."""
        # Create manuscript lookup
        manuscript_lookup = {ms["Manuscript #"]: ms for ms in manuscripts if ms.get("Manuscript #")}

        for flagged_email in flagged_emails:
            manuscript_id = flagged_email.get("manuscript_id")
            if not manuscript_id or manuscript_id not in manuscript_lookup:
                continue

            manuscript = manuscript_lookup[manuscript_id]
            referee_name = flagged_email.get("referee_name")

            if not referee_name:
                continue

            # Determine status
            status = "Contacted"
            if flagged_email.get("type") == "acceptance":
                status = "Accepted"
            elif flagged_email.get("type") == "invitation":
                status = "Invited"

            # Add or update referee
            self._update_referee_status(manuscript, referee_name, status)

    def _update_referee_status(
        self, manuscript: dict[str, Any], referee_name: str, status: str
    ) -> None:
        """Update or add referee status to manuscript."""
        referees = manuscript.setdefault("Referees", [])

        # Look for existing referee
        for referee in referees:
            if referee.get("Referee Name") == referee_name:
                referee["Status"] = status
                return

        # Add new referee
        referees.append(
            {"Referee Name": referee_name, "Referee Email": "", "Status": status, "Due Date": ""}
        )

    def _clean_author_name(self, raw_name: str) -> str:
        """Clean author name by removing titles and extra text."""
        if not raw_name:
            return ""

        # Remove common titles and suffixes
        name = re.sub(
            r"(Pr\.|Prof\.|Dr\.|Ph\.?D\.?|Professor|,.*)", "", raw_name, flags=re.IGNORECASE
        )
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _normalize_status(self, status: str) -> str:
        """Normalize manuscript status."""
        status_lower = status.lower()

        if "requiring additional reviewer" in status_lower:
            return "Pending Referee Assignments"
        elif "with referees" in status_lower or "under review" in status_lower:
            return "All Referees Assigned"
        else:
            return status

    def _wait_for_new_window(self, original_window: str, timeout: int = 10) -> None:
        """Wait for a new window to open."""
        import time

        for _ in range(timeout):
            if len(self.driver.window_handles) > 1:
                return
            time.sleep(1)

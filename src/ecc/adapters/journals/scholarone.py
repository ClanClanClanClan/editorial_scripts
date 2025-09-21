"""ScholarOne (Manuscript Central) async adapter implementation."""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.orcid_client import ORCIDClient

from src.ecc.adapters.journals.base import AsyncJournalAdapter, JournalConfig
from src.ecc.core.domain.models import (
    Author,
    File,
    Manuscript,
    ManuscriptStatus,
    Referee,
    RefereeStatus,
)


class ScholarOneAdapter(AsyncJournalAdapter):
    """Adapter for ScholarOne journals (MF, MOR)."""

    def __init__(self, config: JournalConfig):
        super().__init__(config)
        self.manuscript_pattern = self._get_manuscript_pattern()

    def _get_manuscript_pattern(self) -> str:
        """Get journal-specific manuscript ID pattern."""
        patterns = {
            "MF": r"MAFI-\d{4}-\d{4}",
            "MOR": r"MOR-\d{4}-\d{4}",
        }
        return patterns.get(self.config.journal_id, r"\w+-\d{4}-\d{4}")

    async def authenticate(self) -> bool:
        """Handle ScholarOne authentication with 2FA support."""
        try:
            self.logger.info("Starting ScholarOne authentication")

            # Navigate to login page
            await self.navigate_with_retry(self.config.url)

            # Get credentials from secure storage (TODO: integrate with Vault)
            credentials = await self._get_credentials()

            # Fill login form
            await self.fill_form_field("#USERID", credentials["username"])
            await self.fill_form_field("#PASSWORD", credentials["password"])

            # Submit login
            await self.click_and_wait("#logInButton", wait_after=3)

            # Check for 2FA
            if await self._requires_2fa():
                await self._handle_2fa()

            # Verify login success
            if await self.page.query_selector("text=Dashboard"):
                self.logger.info("Authentication successful")
                return True
            else:
                self.logger.error("Authentication failed - dashboard not found")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    async def _requires_2fa(self) -> bool:
        """Check if 2FA is required."""
        token_field = await self.page.query_selector("#TOKEN_VALUE")
        return token_field is not None

    async def _handle_2fa(self):
        """Handle 2FA verification."""
        self.logger.info("2FA required, fetching code...")

        code = await self._fetch_2fa_code()

        await self.fill_form_field("#TOKEN_VALUE", code)
        await self.page.press("#TOKEN_VALUE", "Enter")
        await self.page.wait_for_load_state("networkidle")

    async def _fetch_2fa_code(self) -> str:
        """Fetch 2FA code.

        Behavior:
        - If env ECC_GMAIL_2FA_CODE is set to a 6-digit value, return it immediately (test stub path).
        - Otherwise, attempt Gmail API retrieval.
        """
        import os
        import re

        # Stubbed code path for tests/CI
        stub_code = os.getenv("ECC_GMAIL_2FA_CODE")
        if stub_code and re.fullmatch(r"\d{6}", stub_code):
            return stub_code

        try:
            # Defer heavy imports until needed
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
            cred_path = os.getenv("GMAIL_CREDENTIALS_PATH", "config/gmail_credentials.json")
            token_path = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, scopes)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(cred_path, scopes)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            service = build("gmail", "v1", credentials=creds)

            # Search for recent verification email
            query = (
                "from:no-reply@manuscriptcentral.com OR subject:(verification code) newer_than:1d"
            )

            # Poll a few times in case of delay
            for _ in range(6):
                results = (
                    service.users().messages().list(userId="me", q=query, maxResults=5).execute()
                )
                messages = results.get("messages", [])
                if messages:
                    # Use most recent
                    msg_id = messages[0]["id"]
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg_id, format="full")
                        .execute()
                    )
                    # Try subject and snippets
                    subject = ""
                    for header in msg.get("payload", {}).get("headers", []):
                        if header.get("name", "").lower() == "subject":
                            subject = header.get("value", "")
                            break
                    snippet = msg.get("snippet", "")
                    body_text = snippet + "\n" + subject

                    # Look for 6-digit code
                    m = re.search(r"\b(\d{6})\b", body_text)
                    if m:
                        code = m.group(1)
                        self.logger.info("2FA code retrieved from Gmail")
                        return code
                await asyncio.sleep(5)

            self.logger.warning("Gmail 2FA code not found in time - please enter manually")
            # Allow manual entry fallback by waiting a bit
            await asyncio.sleep(20)
            return ""
        except Exception as e:
            self.logger.error(f"2FA retrieval via Gmail failed: {e}")
            # Fallback to manual
            await asyncio.sleep(20)
            return ""

    async def _get_credentials(self) -> dict[str, str]:
        """Get credentials from secure storage."""
        # TODO: Integrate with HashiCorp Vault
        import os

        return {
            "username": os.environ.get(f"{self.config.journal_id}_EMAIL", ""),
            "password": os.environ.get(f"{self.config.journal_id}_PASSWORD", ""),
        }

    async def fetch_manuscripts(self, categories: list[str]) -> list[Manuscript]:
        """Fetch manuscripts from specified categories."""
        manuscripts = []

        try:
            # Navigate to Associate Editor Center
            await self.click_and_wait("text=Associate Editor Center")

            for category in categories:
                try:
                    manuscripts_in_category = await self._fetch_category_manuscripts(category)
                    manuscripts.extend(manuscripts_in_category)
                except Exception as e:
                    self.logger.error(f"Error fetching category {category}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error fetching manuscripts: {e}")

        self.logger.info(f"Fetched {len(manuscripts)} manuscripts total")
        return manuscripts

    async def _fetch_category_manuscripts(self, category: str) -> list[Manuscript]:
        """Fetch manuscripts from a specific category (robust selection)."""
        manuscripts: list[Manuscript] = []

        # Try multiple strategies to click into category
        async def _click_strategy() -> bool:
            # 1) Row that contains category, click numeric link
            rows = await self.page.query_selector_all("tr")
            for row in rows:
                try:
                    text = (await row.inner_text()).strip()
                    if category.lower() in text.lower():
                        # Prefer an anchor containing digits (count)
                        link = await row.query_selector("a:has-text('0')")
                        # If not literal '0', search any digits
                        if not link:
                            anchors = await row.query_selector_all("a")
                            for a in anchors:
                                at = (await a.inner_text()).strip()
                                if re.search(r"\d+", at):
                                    link = a
                                    break
                        if link:
                            await link.click()
                            return True
                        # Fallback: click the row cell with category
                        cell = await row.query_selector(f"td:has-text('{category}')")
                        if cell:
                            await cell.click()
                            return True
                except Exception:
                    continue
            # 2) Direct selector by text
            elem = await self.page.query_selector(f"td:has-text('{category}')")
            if elem:
                await elem.click()
                return True
            return False

        # Snapshot before click if debugging
        if getattr(self, "debug_snapshots", False):
            await self.debug_snapshot(f"before_click_{category.replace(' ', '_')}")

        clicked = await _click_strategy()
        if not clicked:
            self.logger.warning(f"Category not clickable: {category}")
            return manuscripts

        await self.page.wait_for_load_state("networkidle")
        if getattr(self, "debug_snapshots", False):
            await self.debug_snapshot(f"after_click_{category.replace(' ', '_')}")

        # Parse manuscript list on resulting page
        manuscripts = await self._parse_manuscript_list()

        # Return to dashboard
        try:
            await self.page.go_back()
            await self.page.wait_for_load_state("networkidle")
        except Exception:
            pass

        return manuscripts

    async def _parse_manuscript_list(self) -> list[Manuscript]:
        """Parse manuscripts from current page by delegating to pure HTML parser."""
        manuscripts: list[Manuscript] = []
        try:
            html = await self.page.content()
            from src.platforms.scholarone_parsers import parse_manuscript_list_html

            items = parse_manuscript_list_html(html, self.manuscript_pattern)
            for it in items:
                try:
                    status = self._parse_status(it.get("status_text", ""))
                    manuscripts.append(
                        Manuscript(
                            journal_id=self.config.journal_id,
                            external_id=it.get("external_id", ""),
                            title=it.get("title", ""),
                            current_status=status,
                        )
                    )
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"Error parsing manuscript list: {e}")
        if getattr(self, "debug_snapshots", False):
            await self.debug_snapshot("parsed_list")
        return manuscripts

    async def _parse_manuscript_row(self, row) -> Manuscript | None:
        """Parse a single manuscript row (regex-aware ID lookup)."""
        try:
            # Try anchor by href pattern first
            id_elem = await row.query_selector("a[href*='MANUSCRIPT']")
            manuscript_id = None
            if id_elem:
                manuscript_id = (await id_elem.inner_text()).strip()
            else:
                # Fallback: scan anchors for text matching the manuscript pattern
                anchors = await row.query_selector_all("a")
                for a in anchors:
                    txt = (await a.inner_text()).strip()
                    if re.search(self.manuscript_pattern, txt):
                        manuscript_id = txt
                        break
            if not manuscript_id:
                return None

            # Extract title (try next cells, else the anchor title)
            title = ""
            title_elem = await row.query_selector("td:nth-child(2)")
            if title_elem:
                title = (await title_elem.inner_text()).strip()
            elif id_elem:
                # Sometimes the id anchor's following sibling contains title
                sib = await row.query_selector("a[href*='MANUSCRIPT'] >> xpath=../../td[2]")
                if sib:
                    title = (await sib.inner_text()).strip()

            # Extract status (search any td containing known words)
            status_text = ""
            status_elem = await row.query_selector("td:nth-child(3)")
            if status_elem:
                status_text = (await status_elem.inner_text()).strip()
            else:
                tds = await row.query_selector_all("td")
                for td in tds:
                    t = (await td.inner_text()).lower()
                    if any(
                        k in t
                        for k in ["awaiting", "under review", "accepted", "rejected", "revision"]
                    ):
                        status_text = t
                        break
            status = self._parse_status(status_text)

            manuscript = Manuscript(
                journal_id=self.config.journal_id,
                external_id=manuscript_id,
                title=title,
                current_status=status,
            )
            return manuscript
        except Exception as e:
            self.logger.error(f"Error parsing manuscript row: {e}")
            return None

    def _parse_status(self, status_text: str) -> ManuscriptStatus:
        """Parse manuscript status from text."""
        status_text = status_text.lower().strip()

        status_map = {
            "submitted": ManuscriptStatus.SUBMITTED,
            "under review": ManuscriptStatus.UNDER_REVIEW,
            "awaiting": ManuscriptStatus.AWAITING_REFEREE_REPORTS,
            "decision": ManuscriptStatus.AWAITING_DECISION,
            "revision": ManuscriptStatus.REVISION_REQUESTED,
            "accepted": ManuscriptStatus.ACCEPTED,
            "rejected": ManuscriptStatus.REJECTED,
        }

        for key, value in status_map.items():
            if key in status_text:
                return value

        return ManuscriptStatus.SUBMITTED

    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        """Extract detailed information for a specific manuscript."""
        manuscript = Manuscript(
            journal_id=self.config.journal_id,
            external_id=manuscript_id,
        )

        try:
            # Navigate to manuscript details
            await self.click_and_wait(f"text={manuscript_id}")

            # Extract all details in parallel
            await asyncio.gather(
                self._extract_basic_info(manuscript),
                self._extract_authors(manuscript),
                self._extract_referees(manuscript),
                self._extract_metadata(manuscript),
            )

            # Attempt document downloads (PDF, original files)
            await self._download_manuscript_resources(manuscript)

            # Extract audit trail
            await self._extract_audit_trail(manuscript)

            # Compute basic referee performance metrics
            await self._compute_referee_metrics(manuscript)

            # Return to list
            await self.page.go_back()

        except Exception as e:
            self.logger.error(f"Error extracting manuscript details: {e}")

        return manuscript

    async def _extract_basic_info(self, manuscript: Manuscript):
        """Extract basic manuscript information."""
        try:
            # Title
            title_elem = await self.page.query_selector(
                "td:has-text('Title:') >> xpath=.. >> td:last-child"
            )
            if title_elem:
                manuscript.title = await title_elem.inner_text()

            # Abstract (opens a popup via 'Abstract' button)
            abstract_link = await self.page.query_selector(
                "a.msdetailsbuttons:has-text('Abstract')"
            )
            if abstract_link:
                popup = await self.handle_popup_window(abstract_link.click)
                if popup:
                    manuscript.abstract = popup.get("text", "")

            # Keywords
            keywords_elem = await self.page.query_selector(
                "td:has-text('Keywords:') >> xpath=.. >> td:last-child"
            )
            if keywords_elem:
                keywords_text = await keywords_elem.inner_text()
                manuscript.keywords = [k.strip() for k in keywords_text.split(",")]

        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")

    async def _extract_authors(self, manuscript: Manuscript):
        """Extract author information."""
        try:
            author_rows = await self.page.query_selector_all("tr:has(td:has-text('Author'))")

            for row in author_rows:
                author = Author()

                # Name (might be link)
                name_elem = await row.query_selector("a")
                if name_elem:
                    author.name = await name_elem.inner_text()

                    # Try to get email from popup
                    email_data = await self.handle_popup_window(name_elem.click)
                    if email_data:
                        author.email = self._extract_email_from_popup(email_data)

                # Institution
                inst_elem = await row.query_selector("td:nth-child(3)")
                if inst_elem:
                    author.institution = await inst_elem.inner_text()

                manuscript.authors.append(author)

        except Exception as e:
            self.logger.error(f"Error extracting authors: {e}")

    async def _extract_referees(self, manuscript: Manuscript):
        """Extract referee information from Reviewer List table."""
        try:
            # Rows are identified by hidden inputs like XIK_RP_ID0, XIK_RP_ID1, ...
            rows = await self.page.locator("tr:has(input[name^='XIK_RP_ID'])").all()
            if not rows:
                # Fallback: try rows that contain ORDER selects
                rows = await self.page.locator("tr:has(select[name^='ORDER'])").all()

            for row in rows:
                try:
                    referee = Referee()

                    # Name anchor typically contains mailpopup_* in JS
                    name_anchor = (
                        await row.locator("a")
                        .filter(
                            has_text="",
                        )
                        .element_handle()
                    )

                    # Find the first anchor with visible text (name)
                    if not name_anchor:
                        anchors = await row.query_selector_all("a")
                        for a in anchors:
                            txt = (await a.inner_text()).strip()
                            if txt and not txt.lower().endswith("view full history"):
                                name_anchor = a
                                break

                    if name_anchor:
                        try:
                            text = (await name_anchor.inner_text()).strip()
                            referee.name = text
                        except Exception:
                            pass

                        # Try to open popup to extract email
                        try:
                            email_data = await self.handle_popup_window(
                                lambda na=name_anchor: na.click()
                            )
                            if email_data:
                                referee.email = self._extract_email_from_popup(email_data)
                        except Exception:
                            pass

                    # Status is in the 3rd td of the row's direct children
                    status_cell = await row.query_selector("td:nth-child(3)")
                    if status_cell:
                        status_text = (await status_cell.inner_text()).strip()
                        referee.status = self._parse_referee_status(status_text)

                    # Dates (Invited/Agreed/Declined) usually in 4th td
                    dates_cell = await row.query_selector("td:nth-child(4)")
                    if dates_cell:
                        text_block = (await dates_cell.inner_text()).strip()
                        # Simple regex-based parsing
                        import re

                        invited = re.search(r"Invited:\s*(\d{2}-[A-Za-z]{3}-\d{4})", text_block)
                        agreed = re.search(r"Agreed\s*:.*?(\d{2}-[A-Za-z]{3}-\d{4})", text_block)
                        declined = re.search(
                            r"Declined\s*:.*?(\d{2}-[A-Za-z]{3}-\d{4})", text_block
                        )
                        due = re.search(r"Due Date:\s*(\d{2}-[A-Za-z]{3}-\d{4})", text_block)
                        from datetime import datetime

                        fmt = "%d-%b-%Y"
                        try:
                            if invited:
                                referee.invited_date = datetime.strptime(invited.group(1), fmt)
                        except Exception:
                            pass
                        try:
                            if agreed:
                                referee.agreed_date = datetime.strptime(agreed.group(1), fmt)
                        except Exception:
                            pass
                        try:
                            if declined:
                                # Use declined as report_submitted_date? keep for history only
                                pass
                        except Exception:
                            pass
                        try:
                            if due:
                                referee.report_due_date = datetime.strptime(due.group(1), fmt)
                        except Exception:
                            pass

                    manuscript.referees.append(referee)
                except Exception as inner:
                    self.logger.error(f"Referee row parse error: {inner}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting referees: {e}")

    def _parse_referee_status(self, status_text: str) -> RefereeStatus:
        """Parse referee status from text."""
        status_text = status_text.lower().strip()

        if "agreed" in status_text:
            return RefereeStatus.AGREED
        elif "declined" in status_text:
            return RefereeStatus.DECLINED
        elif "submitted" in status_text:
            return RefereeStatus.REPORT_SUBMITTED
        elif "overdue" in status_text:
            return RefereeStatus.OVERDUE
        else:
            return RefereeStatus.INVITED

    async def _extract_metadata(self, manuscript: Manuscript):
        """Extract additional metadata."""
        try:
            # Page count
            pages_elem = await self.page.query_selector(
                "td:has-text('Pages:') >> xpath=.. >> td:last-child"
            )
            if pages_elem:
                pages_text = await pages_elem.inner_text()
                if pages_text.isdigit():
                    manuscript.page_count = int(pages_text)

            # Word count
            words_elem = await self.page.query_selector(
                "td:has-text('Word Count:') >> xpath=.. >> td:last-child"
            )
            if words_elem:
                words_text = await words_elem.inner_text()
                words_text = re.sub(r"[^\d]", "", words_text)
                if words_text:
                    manuscript.word_count = int(words_text)

        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")

    def _extract_email_from_popup(self, popup_data: dict) -> str:
        """Extract email address from popup content."""
        text = popup_data.get("text", "")

        # Look for email pattern
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(email_pattern, text)

        return match.group() if match else ""

    async def enrich_people_with_orcid(self, manuscript: Manuscript) -> None:
        """Enrich authors and referees using ORCID API when possible.

        - Authors: set orcid; update institution/department/country from current affiliation
        - Referees: store enrichment in historical_performance (including 'orcid', 'research_interests', 'publication_count')
        """
        try:
            client = ORCIDClient()

            # Enrich authors
            for a in manuscript.authors:
                try:
                    person = {
                        "name": a.name,
                        "email": a.email,
                        "institution": a.institution or "",
                    }
                    enriched = client.enrich_person_profile(person)
                    if enriched.get("orcid"):
                        a.orcid = enriched.get("orcid")
                    # Current affiliation mapping
                    if enriched.get("current_affiliation"):
                        cur = enriched["current_affiliation"]
                        a.institution = cur.get("organization") or a.institution
                        a.department = cur.get("department") or a.department
                        a.country = cur.get("country") or a.country
                except Exception:
                    continue

            # Enrich referees
            for r in manuscript.referees:
                try:
                    # Skip recent enrichment
                    ttl_days = int(os.getenv("ECC_ENRICH_TTL_DAYS", "14"))
                    hp = r.historical_performance or {}
                    last = hp.get("enrichment_date")
                    if last:
                        from datetime import datetime, timedelta

                        try:
                            ts = datetime.fromisoformat(str(last))
                            if ts + timedelta(days=ttl_days) > datetime.utcnow():
                                continue
                        except Exception:
                            pass
                    person = {
                        "name": r.name,
                        "email": r.email,
                        "institution": r.institution or "",
                    }
                    enriched = client.enrich_person_profile(person)
                    # Stash data in historical_performance JSON
                    hp = r.historical_performance or {}
                    if enriched.get("orcid"):
                        hp["orcid"] = enriched["orcid"]
                    if enriched.get("research_interests"):
                        hp["research_interests"] = enriched["research_interests"]
                    if enriched.get("publication_count") is not None:
                        hp["publication_count"] = enriched["publication_count"]
                    if enriched.get("metrics"):
                        hp["metrics"] = enriched["metrics"]
                    if enriched.get("enrichment_date"):
                        hp["enrichment_date"] = enriched["enrichment_date"]
                    r.historical_performance = hp
                    # Improve affiliation fields
                    if enriched.get("current_affiliation"):
                        cur = enriched["current_affiliation"]
                        r.institution = cur.get("organization") or r.institution
                        r.department = cur.get("department") or r.department
                        r.country = cur.get("country") or r.country
                except Exception:
                    continue
        except Exception as e:
            self.logger.warning(f"ORCID enrichment failed: {e}")

    async def download_manuscript_files(self, manuscript: Manuscript) -> list[Path]:
        """Download all files associated with a manuscript."""
        downloaded_files = []

        try:
            # Navigate to manuscript if not already there
            if manuscript.external_id not in await self.page.content():
                await self.click_and_wait(f"text={manuscript.external_id}")

            # Find download links
            download_links = await self.page.query_selector_all(
                "a[href*='download'], a:has-text('PDF')"
            )

            for link in download_links:
                try:
                    filename = f"{manuscript.external_id}_{await link.inner_text()}.pdf"
                    file_path = await self.download_file(link.click, filename)
                    downloaded_files.append(file_path)

                    # Add to manuscript files
                    manuscript.files.append(
                        File(
                            manuscript_id=manuscript.id,
                            filename=filename,
                            storage_path=str(file_path),
                        )
                    )

                except Exception as e:
                    self.logger.error(f"Error downloading file: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error downloading manuscript files: {e}")

        return downloaded_files

    async def _download_manuscript_resources(self, manuscript: Manuscript) -> None:
        """Download PDF/Original Files via popup windows if possible."""
        try:
            # PDF
            pdf_link = await self.page.query_selector("a.msdetailsbuttons:has-text('PDF')")
            if pdf_link:
                filename = f"{manuscript.external_id}_proof.pdf"
                saved = await self.download_from_popup(
                    pdf_link.click, filename, expected_mime="application/pdf"
                )
                if saved:
                    from src.ecc.core.domain.models import DocumentType, File
                    from src.ecc.infrastructure.storage.utils import (
                        compute_checksum,
                        guess_mime_type,
                    )

                    checksum = compute_checksum(saved)
                    mime = guess_mime_type(saved)
                    size = saved.stat().st_size
                    # Deduplicate by checksum
                    if not any(getattr(f, "checksum", "") == checksum for f in manuscript.files):
                        manuscript.files.append(
                            File(
                                manuscript_id=manuscript.id,
                                document_type=DocumentType.MANUSCRIPT,
                                filename=saved.name,
                                storage_path=str(saved),
                                checksum=checksum,
                                mime_type=mime,
                                size_bytes=size,
                            )
                        )

            # Original Files (save HTML listing as fallback)
            orig_link = await self.page.query_selector(
                "a.msdetailsbuttons:has-text('Original Files')"
            )
            if orig_link:
                # Process the popup and download individual files if possible
                await self._process_original_files_popup(orig_link, manuscript)

        except Exception as e:
            self.logger.warning(f"Resource download encountered issues: {e}")

    async def _process_original_files_popup(self, orig_link, manuscript: Manuscript) -> None:
        """Open the Original Files popup and download each listed attachment."""
        try:
            import os
            import re
            from urllib.parse import urljoin

            from src.ecc.core.domain.models import DocumentType, File

            async with self.context.expect_page() as popup_info:
                await orig_link.click()
            popup_page = await popup_info.value
            await popup_page.wait_for_load_state("networkidle")

            # Collect candidate anchors within popup
            anchors = await popup_page.query_selector_all("a")
            saved_count = 0
            for a in anchors[:50]:  # limit to 50 to avoid runaway
                try:
                    href = await a.get_attribute("href")
                    text = (await a.inner_text()) or ""
                    if not href:
                        continue
                    # Heuristics: include known patterns
                    if not (
                        "DOWNLOAD=TRUE" in href
                        or "mathor?PARAMS" in href
                        or re.search(r"\.(pdf|docx?|zip|xls|xlsx|txt)(?:\?|$)", href, re.I)
                    ):
                        continue

                    abs_url = urljoin(popup_page.url, href)
                    # Fetch via request API to preserve session
                    resp = await popup_page.request.get(abs_url)
                    if resp.status != 200:
                        continue
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                    cdisp = headers.get("content-disposition", "")
                    fname = None
                    m = re.search(r"filename\*=UTF-8''([^\s;]+)", cdisp)
                    if m:
                        fname = m.group(1)
                    else:
                        m = re.search(r'filename="?([^";]+)"?', cdisp)
                        if m:
                            fname = m.group(1)

                    if not fname:
                        # Fallback to link text or last path segment
                        from urllib.parse import urlparse

                        path = urlparse(abs_url).path
                        last = os.path.basename(path) or "file"
                        fname = (text.strip() or last).replace(" ", "_")

                    # Ensure extension reasonable
                    if not re.search(r"\.(pdf|docx?|zip|xls|xlsx|txt)$", fname, re.I):
                        # Inspect content type to assign extension
                        ctype = headers.get("content-type", "").lower()
                        ext = ".bin"
                        if "pdf" in ctype:
                            ext = ".pdf"
                        elif "msword" in ctype or "word" in ctype:
                            ext = ".doc"
                        elif "spreadsheet" in ctype or "excel" in ctype:
                            ext = ".xls"
                        elif "zip" in ctype:
                            ext = ".zip"
                        elif "text" in ctype:
                            ext = ".txt"
                        if not re.search(r"\.[A-Za-z0-9]{2,5}$", fname):
                            fname = fname + ext

                    save_path = self.config.download_dir / f"{manuscript.external_id}_{fname}"
                    self.config.download_dir.mkdir(parents=True, exist_ok=True)
                    body = await resp.body()
                    with open(save_path, "wb") as f:
                        f.write(body)
                    from src.ecc.infrastructure.storage.utils import (
                        compute_checksum,
                        guess_mime_type,
                    )

                    checksum = compute_checksum(save_path)
                    mime = guess_mime_type(save_path)
                    size = save_path.stat().st_size
                    if not any(getattr(f, "checksum", "") == checksum for f in manuscript.files):
                        manuscript.files.append(
                            File(
                                manuscript_id=manuscript.id,
                                document_type=DocumentType.SUPPLEMENTARY,
                                filename=save_path.name,
                                storage_path=str(save_path),
                                checksum=checksum,
                                mime_type=mime,
                                size_bytes=size,
                            )
                        )
                    saved_count += 1
                except Exception:
                    continue

            if saved_count == 0:
                # Save HTML fallback for analysis
                html = await popup_page.content()
                (
                    self.config.download_dir / f"{manuscript.external_id}_original_files.html"
                ).write_text(html)

            await popup_page.close()
        except Exception as e:
            self.logger.warning(f"Original files popup processing failed: {e}")

    async def _compute_referee_metrics(self, manuscript: Manuscript) -> None:
        """Compute simple referee metrics like response time and overdue flags."""
        now = datetime.utcnow()
        for r in manuscript.referees:
            try:
                hp = r.historical_performance or {}
                if r.invited_date and r.agreed_date:
                    delta = (r.agreed_date - r.invited_date).days
                    hp["response_days"] = delta
                if (
                    r.report_due_date
                    and (r.report_submitted_date is None)
                    and r.report_due_date < now
                ):
                    hp["overdue"] = True
                r.historical_performance = hp
            except Exception:
                continue

    async def _navigate_to_audit_trail(self) -> bool:
        """Navigate to the Audit Trail tab using left tab image link."""
        try:
            link = await self.page.query_selector("a:has(img[src*='lefttabs_audit_trail'])")
            if not link:
                # Fallback by text
                link = await self.page.query_selector("a:has-text('Audit Trail')")
            if link:
                await link.click()
                await self.page.wait_for_load_state("networkidle")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed navigating to Audit Trail: {e}")
            return False

    async def _extract_audit_trail(self, manuscript: Manuscript) -> None:
        """Extract audit trail events with pagination and letters metadata."""
        try:
            ok = await self._navigate_to_audit_trail()
            if not ok:
                return

            events_all: list[dict[str, Any]] = []

            select = await self.page.query_selector("select[name='page_select']")
            pages = ["1"]
            if select:
                options = await select.query_selector_all("option")
                pages = [await o.get_attribute("value") or "" for o in options]
                pages = [p for p in pages if p]

            for pval in pages:
                try:
                    if select:
                        await select.select_option(pval)
                        await self.page.wait_for_load_state("networkidle")
                    page_events = await self._parse_audit_page(manuscript)
                    events_all.extend(page_events)
                except Exception as pe:
                    self.logger.warning(f"Audit page {pval} parse issue: {pe}")
                    continue

            # Attach to manuscript metadata
            if not manuscript.metadata:
                manuscript.metadata = {}
            manuscript.metadata["audit_trail"] = events_all

        except Exception as e:
            self.logger.error(f"Audit trail extraction failed: {e}")

    async def _parse_audit_page(self, manuscript: Manuscript) -> list[dict[str, Any]]:
        """Parse the visible audit page via pure parser on page HTML."""
        try:
            html = await self.page.content()
            from src.platforms.scholarone_parsers import parse_audit_trail_html

            return parse_audit_trail_html(html)
        except Exception as e:
            self.logger.warning(f"Audit page parse issue: {e}")
            return []

    async def _download_letter_popup_attachments(
        self, letter_anchor, manuscript: Manuscript
    ) -> None:
        """Open the letter popup and download any attachments it references."""
        try:
            async with self.context.expect_page() as popup_info:
                await letter_anchor.click()
            popup_page = await popup_info.value
            await popup_page.wait_for_load_state("networkidle")

            # Find anchors possibly linking attachments (heuristics similar to Original Files)
            anchors = await popup_page.query_selector_all("a")
            import os
            import re
            from urllib.parse import urljoin, urlparse

            from src.ecc.core.domain.models import DocumentType, File

            saved = 0
            for a in anchors[:50]:
                try:
                    href = await a.get_attribute("href")
                    label = (await a.inner_text()) or ""
                    if not href:
                        continue
                    if not (
                        re.search(r"\.(pdf|docx?|zip|xls|xlsx|txt)(?:\?|$)", href, re.I)
                        or "DOWNLOAD=TRUE" in href
                        or "PARAMS=" in href
                    ):
                        continue
                    abs_url = urljoin(popup_page.url, href)
                    resp = await popup_page.request.get(abs_url)
                    if resp.status != 200:
                        continue
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                    cdisp = headers.get("content-disposition", "")
                    fname = None
                    m = re.search(r"filename\*=UTF-8''([^\s;]+)", cdisp)
                    if m:
                        fname = m.group(1)
                    else:
                        m = re.search(r'filename="?([^";]+)"?', cdisp)
                        if m:
                            fname = m.group(1)
                    if not fname:
                        path = urlparse(abs_url).path
                        last = os.path.basename(path) or "attachment"
                        fname = (label.strip() or last).replace(" ", "_")
                    # Save file
                    body = await resp.body()
                    # Attempt to prefix with external id if we can infer from current page url (not available here), save as is
                    prefix = (
                        manuscript.external_id
                        if getattr(manuscript, "external_id", None)
                        else "letter"
                    )
                    save_path = self.config.download_dir / f"{prefix}_{fname}"
                    with open(save_path, "wb") as f:
                        f.write(body)
                    # Heuristic document type classification
                    doc_type = DocumentType.SUPPLEMENTARY
                    low = f"{label} {fname}".lower()
                    if "report" in low or "review" in low:
                        doc_type = DocumentType.REFEREE_REPORT
                    elif "decision" in low:
                        doc_type = DocumentType.DECISION_LETTER
                    elif "cover" in low:
                        doc_type = DocumentType.COVER_LETTER
                    # Append to manuscript files
                    from src.ecc.infrastructure.storage.utils import (
                        compute_checksum,
                        guess_mime_type,
                    )

                    checksum = compute_checksum(save_path)
                    mime = guess_mime_type(save_path)
                    size = save_path.stat().st_size
                    if not any(getattr(f, "checksum", "") == checksum for f in manuscript.files):
                        manuscript.files.append(
                            File(
                                manuscript_id=manuscript.id,
                                document_type=doc_type,
                                filename=save_path.name,
                                storage_path=str(save_path),
                                checksum=checksum,
                                mime_type=mime,
                                size_bytes=size,
                            )
                        )
                    saved += 1
                except Exception:
                    continue

            await popup_page.close()
        except Exception as e:
            self.logger.warning(f"Letter popup processing failed: {e}")
